"""Change diagram of unit k2 of the PR 4958 k_vnni.hpp page:
detail::transpose_16x16_epi32, the in-place 16 x 16 transpose of dword lanes
in four stages (head lines 257-287). The grids come from a simulation of the
four stages (base_k_vnni.transpose_sim), run at import time.
"""
from svg_helpers import C, arrow, cite, figure, fn_cell, lines, marker_defs, rect, text
from base_k_vnni import EX, STAGES, TRACK, _w

BASE = ("Updates B2: the one arrow 'transpose_16x16_epi32' between B2's two grids is "
        "opened into its four stages; after each stage the grid shows where token 37's "
        "row (orange) and pair dp 3 (blue) have moved, until the row is a column and the "
        "pair is a row.")

W = 700
CELL = 7
GRID = 16 * CELL


def stage_grid(x, y, state, track):
    """One 16 x 16 grid after a stage: a cell is coloured by its source: input
    register 5 (token 37's row) orange, input lane 3 (pair dp 3) blue, both =
    the tracked dword, solid blue with an ink outline."""
    o = []
    for r in range(16):
        for c in range(16):
            src_reg, src_lane = state[r][c]
            if src_reg == EX["t"] and src_lane == EX["dp"]:
                fill, stroke = C["vnni"], C["ink"]
            elif src_reg == EX["t"]:
                fill, stroke = C["rm_fill"], C["rm"]
            elif src_lane == EX["dp"]:
                fill, stroke = C["vnni_fill"], C["vnni"]
            else:
                fill, stroke = "#fff", C["line"]
            o.append(rect(x + c * CELL, y + r * CELL, CELL, CELL, fill, stroke, 0.4, 0))
    o.append(rect(x, y, GRID, GRID, "none", C["ink"], 0.8, 0))
    reg, lane_ = track
    o.append(text(x - 3, y + reg * CELL + CELL - 1, str(reg), 8.5, "end", True, fill=C["ink"],
                  weight=600))
    o.append(text(x + lane_ * CELL + CELL / 2, y - 2, str(lane_), 8.5, "middle", True,
                  fill=C["ink"], weight=600))
    return "".join(o)


def fig():
    fid = "k_vnni-d2"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    desc = ["In-place transpose of a 16 x 16 matrix of 32-bit lanes: on return r[i] holds "
            "lane i of every input register",
            "(input register t in lane t). Four stages of two-register shuffles, 64 shuffles "
            "in all."]
    for d in desc:
        _w(d, 9.5, 644, where="d2 desc")
    o.append(fn_cell(20, 8, 660, 64, "transpose_16x16_epi32(__m512i (&r)[LANES_16])", desc,
                     "k_vnni.hpp:257-287", "new"))
    boxes.append(("transpose_16x16_epi32(__m512i (&r)[LANES_16])", "k_vnni.hpp:257-287"))
    o.append(text(20, 88, "the four stages, each as the 16 x 16 grid of dwords after it "
                  "(row = register, column = lane), from a simulation of lines 267-286", 9.5,
                  weight=700))
    o.append(text(20, 100, "orange = a dword that came from input register 5 (token 37's row "
                  "of step 2); blue = a dword that came from input lane 3 (pair dp 3)", 9,
                  fill=C["muted"]))
    stages = [
        ("1", "_mm512_unpacklo_epi32 /", "_mm512_unpackhi_epi32", "of r[2i], r[2i+1]",
         "interleaves dwords of two", "neighbour registers (16 ops)", "k_vnni.hpp:267-270"),
        ("2", "_mm512_unpacklo_epi64 /", "_mm512_unpackhi_epi64", "of t[4i], t[4i+2] and",
         "t[4i+1], t[4i+3]: qword", "pairs (16 ops)", "k_vnni.hpp:271-276"),
        ("3", "_mm512_shuffle_i32x4", "(0x88 even / 0xdd odd", "128-bit quarters) of r[i],",
         "r[i+4] and r[i+8],", "r[i+12] (16 ops)", "k_vnni.hpp:277-282"),
        ("4", "_mm512_shuffle_i32x4", "(0x88 / 0xdd) of t[i],", "t[i+8]: the halves",
         "(16 ops); r[i] lane t =", "input register t, lane i", "k_vnni.hpp:283-286"),
    ]
    x0, gy = 44, 136
    colw = 166
    for i, (n, a, b, c, d, e, ref) in enumerate(stages):
        x = x0 + i * colw
        o.append(text(x, gy - 16, f"after stage {n}", 10, weight=700))
        o.append(stage_grid(x, gy, STAGES[i], TRACK[i]))
        reg, lane_ = TRACK[i]
        o.append(text(x + GRID / 2, gy + GRID + 12, f"tracked dword: r[{reg}] lane {lane_}", 8.5,
                      "middle", True, fill=C["vnni"], weight=600))
        for sline in (a, b, c, d, e):
            _w(sline, 8.5, colw - 10, True if sline.startswith("_mm") else False, "d2 stage")
        o.append(lines(x, gy + GRID + 26, [a, b, c, d, e], 8.5, 10.5, mono=False))
        o.append(text(x, gy + GRID + 84, f"[{ref}]", 8.5, mono=True, fill=C["cite"]))
        boxes.append((f"stage {n}: {a} {b}", ref))
        if i < 3:
            o.append(arrow(fid, "ink", [(x + GRID + 4, gy + GRID / 2), (x + colw - 4, gy + GRID / 2)],
                           C["ink"], 1.2))
    # before the first stage: a note on the input
    iy = gy + GRID + 100
    o.append(rect(20, iy, 660, 70, C["soft"], C["line"], 1, 5))
    il = ["input (line 350-354 of store_block): r[t] = the 16 dwords of token 32 + t at step s "
          "(lane dp = pair dp); the tracked dword",
          "is dims 70, 71 of token 37: r[5] lane 3. Output: r[dp] = pair row dp of the panel, "
          "the token in lane t: r[3] lane 5.",
          "The selectors: EVEN_QUARTERS_0X88 takes the even 128-bit quarters of both inputs, "
          "ODD_QUARTERS_0XDD the odd ones",
          "(lines 262-265). The simulation that drew the grids checks that r[i] lane t == input "
          "register t, lane i, for all 256 dwords."]
    for s in il:
        _w(s, 9, 644, where="d2 input")
    o.append(lines(28, iy + 14, il, 9, 11))
    o.append(cite(676, iy + 66, "k_vnni.hpp:257-265, 350-355"))
    boxes.append(("EVEN_QUARTERS_0X88, ODD_QUARTERS_0XDD (the selectors)", "k_vnni.hpp:262-265"))
    H = int(iy + 82)
    cap = ("Updates B2: the four stages of transpose_16x16_epi32, each drawn as the 16 x "
           "16 grid of dwords after it, from a simulation of the code. Follow the orange "
           "cells: token 37's row (input register 5) is spread by the unpack stages and "
           "gathered by the shuffle stages until it is column 5 of every register. Follow "
           "the blue cells: pair dp 3 (input lane 3) ends as register 3, the pair row the "
           "store writes. The tracked dword moves r[5] lane 3 -> r[7] lane 1 -> r[3] lane "
           "9 -> r[3] lane 5.")
    legend = [
        ("box", "white box, ink outline: the function cell; name in bold monospace, what it "
                "does in sans-serif"),
        ("rm", "orange cell: a dword that came from input register 5 (token 37's row)"),
        ("vnni", "blue cell: a dword that came from input lane 3 (pair dp 3); blue text = the "
                 "tracked dword's place after each stage"),
        ("solid blue cell, ink outline: the tracked dword, dims 70, 71 of token 37 "
         "(register 5, lane 3 of the input)", C["vnni"], C["ink"], False, False),
        ("lane", "white cell, thin grey outline: any other dword"),
        ("ink frame: a grid's outline", "none", C["ink"], False, False),
        ("ctx", "grey box, thin grey outline: the input and output of the transpose and the "
                "selectors"),
        ("arrow", "ink arrow: one stage to the next"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = transpose_16x16_epi32 is added by this PR"),
    ]
    return figure(fid, W, H, "transpose_16x16_epi32: the four stages on the worked example",
                  "".join(o), cap, boxes=boxes, legend=legend)
