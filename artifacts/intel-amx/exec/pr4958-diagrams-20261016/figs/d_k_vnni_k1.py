"""Change diagram of unit k1 of the PR 4958 k_vnni.hpp page: the constants
FULL_BLOCK_0XFFFF and LANES_16 and the two static_asserts (head lines 76-79,
84-92).
"""
from svg_helpers import C, arrow, cite, figure, label_box, line, lines, marker_defs, rect, text
from base_k_vnni import _w, present_bits, PRESENT_UNIT2

BASE = ("Updates B1 and B2: FULL_BLOCK_0XFFFF is the present mask with every one of B1's "
        "16 token lanes set, LANES_16 is the dword count of one 64-byte line, and the new "
        "static_assert pins the square that B2's transpose relies on: 16 token rows onto "
        "16 pair rows.")

W = 700


def fig():
    fid = "k_vnni-d1"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 18, "two constants and two static_asserts for the block save", 12,
                  weight=700))
    # FULL_BLOCK_0XFFFF
    o.append(rect(20, 30, 320, 108, "#fff", C["ink"], 1.2, 5))
    o.append(text(28, 46, "FULL_BLOCK_0XFFFF (__mmask16)", 10.5, mono=True, weight=700))
    o.append(text(28, 60, "The 16 lanes of one token block, all present.", 9.5, fill=C["muted"]))
    svg, xe = present_bits(28, 66, 0xffff, 11, 1)
    o.append(svg)
    o.append(text(28 + 5, 88, "t = 0", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(28 + 15 * 12 + 5, 88, "t = 15", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(28, 104, "present == FULL_BLOCK_0XFFFF selects the", 9.5))
    o.append(text(28, 116, "whole-line branch of store_block (line 357)", 9.5))
    o.append(text(28, 133, "new", 9, fill=C["new"], weight=700))
    o.append(cite(336, 134, "k_vnni.hpp:76-77"))
    boxes.append(("FULL_BLOCK_0XFFFF", "k_vnni.hpp:76-77"))
    # the worked example's partial mask beside it
    o.append(rect(360, 30, 320, 108, "#fff", C["ink"], 1.2, 5))
    o.append(text(368, 46, "a partial present: unit 2 = 0x01ff", 10.5, weight=700))
    o.append(text(368, 60, "9 lanes set (tokens 32..40), 7 clear", 9.5, fill=C["muted"]))
    svg, xe = present_bits(368, 66, PRESENT_UNIT2, 11, 1)
    o.append(svg)
    o.append(text(368 + 5, 88, "t = 0", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(368 + 8 * 12 + 5, 88, "t = 8", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(368 + 15 * 12 + 5, 88, "t = 15", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(368, 104, "present != FULL_BLOCK_0XFFFF: the masked", 9.5))
    o.append(text(368, 116, "branch, lanes 9..15 never written (line 361)", 9.5))
    o.append(cite(676, 134, "k_vnni.hpp:357, 361-365; model.hpp:3245-3257"))
    boxes.append(("a partial present: unit 2 = 0x01ff", "k_vnni.hpp:344, 361-365"))
    # LANES_16
    o.append(rect(20, 152, 320, 100, "#fff", C["ink"], 1.2, 5))
    o.append(text(28, 168, "LANES_16 = LINE_BYTES_64 / DWORD_BYTES_4", 10.5, mono=True,
                  weight=700))
    o.append(text(28, 182, "32-bit lanes of one 512-bit register", 9.5, fill=C["muted"]))
    o.append(text(28, 194, "(the transpose below is LANES x LANES)", 9.5, fill=C["muted"]))
    # one 64-byte line as 16 dwords
    lw = 16
    for i in range(16):
        o.append(rect(28 + i * lw, 202, lw, 12, C["vnni_fill"], C["vnni"], 0.8, 0))
    o.append(text(28 + 8 * lw, 226, "64 B = 16 dwords of 4 B = 16 lanes", 9, "middle"))
    o.append(text(28, 247, "new", 9, fill=C["new"], weight=700))
    o.append(cite(336, 248, "k_vnni.hpp:78-79, 62, 64"))
    boxes.append(("LANES_16 = LINE_BYTES_64 / DWORD_BYTES_4", "k_vnni.hpp:78-79"))
    # the static_asserts
    o.append(rect(360, 152, 320, 100, "#fff", C["ink"], 1.2, 5))
    o.append(text(368, 168, "static_assert (lines 84-88): LANES_16 == 16", 10, mono=True,
                  weight=700))
    o.append(text(368, 182, "joins 'every constant's name states its value'", 9.5,
                  fill=C["muted"]))
    o.append(text(368, 202, "static_assert (lines 91-92):", 10, mono=True, weight=700))
    o.append(text(368, 215, "BLOCK_TOKENS_16 == LANES_16 && STEP_PAIRS_16 == LANES_16", 9,
                  mono=True))
    o.append(text(368, 228, "'the block save transposes 16 token rows onto", 9, fill=C["muted"]))
    o.append(text(368, 239, "the 16 pair rows of a panel'", 9, fill=C["muted"]))
    o.append(text(368, 247, "new", 9, fill=C["new"], weight=700))
    o.append(cite(676, 248, "k_vnni.hpp:84-92"))
    boxes.append(("static_assert (lines 84-88): LANES_16 == 16", "k_vnni.hpp:84-88"))
    boxes.append(("static_assert (lines 91-92): BLOCK_TOKENS_16 == LANES_16 && STEP_PAIRS_16 == LANES_16",
                  "k_vnni.hpp:91-92"))
    # the square
    sy = 270
    o.append(text(20, sy + 10, "the square the second static_assert pins: 16 token rows x 16 "
                  "pairs = 16 registers x 16 lanes", 10, weight=700))
    cell = 9
    gx1, gy = 110, sy + 44
    for r in range(16):
        for c in range(16):
            o.append(rect(gx1 + c * cell, gy + r * cell, cell, cell, C["rm_fill"], C["rm"], 0.4, 0))
    o.append(rect(gx1, gy, 16 * cell, 16 * cell, "none", C["ink"], 0.8, 0))
    o.append(text(gx1 + 8 * cell, gy - 16, "columns: STEP_PAIRS_16 pairs", 8.5, "middle", True,
                  fill=C["muted"]))
    o.append(text(gx1 + 8 * cell, gy - 5, "rows: BLOCK_TOKENS_16 tokens", 8.5, "middle", True,
                  fill=C["muted"]))
    o.append(text(gx1 + 8 * cell, gy + 16 * cell + 12, "r[t]: register t = token lane t", 9,
                  "middle"))
    gx2 = 430
    for r in range(16):
        for c in range(16):
            o.append(rect(gx2 + c * cell, gy + r * cell, cell, cell, C["vnni_fill"], C["vnni"], 0.4, 0))
    o.append(rect(gx2, gy, 16 * cell, 16 * cell, "none", C["ink"], 0.8, 0))
    o.append(text(gx2 + 8 * cell, gy - 16, "columns: LANES_16 token lanes", 8.5, "middle", True,
                  fill=C["muted"]))
    o.append(text(gx2 + 8 * cell, gy - 5, "rows: STEP_PAIRS_16 pair rows", 8.5, "middle", True,
                  fill=C["muted"]))
    o.append(text(gx2 + 8 * cell, gy + 16 * cell + 12, "r[dp]: register dp = pair row dp", 9,
                  "middle"))
    o.append(arrow(fid, "ink", [(gx1 + 16 * cell + 30, gy + 8 * cell), (gx2 - 30, gy + 8 * cell)],
                   C["ink"], 1.4))
    mx = (gx1 + 16 * cell + 30 + gx2 - 30) / 2
    o.append(text(mx, gy + 8 * cell - 8, "transpose", 9, "middle", weight=600))
    o.append(text(mx, gy + 8 * cell + 16, "16 x 16", 9, "middle", mono=True))
    o.append(text(20, gy + 16 * cell + 30, "the square is square only because the three "
                  "constants are equal: a 64-byte line holds one pair of 16 tokens, and a step "
                  "has 16 pairs", 9, fill=C["ink"]))
    o.append(text(20, gy + 16 * cell + 42, "[k_vnni.hpp:63-68, 91-92, 257-259]", 8.5, mono=True,
                  fill=C["cite"]))
    H = int(gy + 16 * cell + 52)
    cap = ("Updates B1 and B2: FULL_BLOCK_0XFFFF names the present mask of a full block "
           "(every lane of B1's 16 token lanes set), which store_block compares against to "
           "choose whole-line stores; the worked example's unit 2 carries 0x01ff instead. "
           "LANES_16 names the 16 dword lanes of one 64-byte line, the width of B2's "
           "register grid. The new static_assert states why the grid is square: "
           "BLOCK_TOKENS_16, STEP_PAIRS_16 and LANES_16 are all 16, so the 16 token rows "
           "of a step transpose onto the 16 pair rows of a panel.")
    legend = [
        ("box", "white box, ink outline: one constant or static_assert of the unit; name in "
                "bold monospace, its comment in grey sans-serif"),
        ("present", "green: a set bit of a present mask (all 16 of FULL_BLOCK_0XFFFF, the 9 of "
                    "unit 2)"),
        ("empty", "grey dashed: a clear bit of the partial mask 0x01ff (lanes 9..15)"),
        ("vnni", "blue: the 16 dwords of one 64-byte line (LANES_16) and the r[dp] square "
                 "after the transpose"),
        ("rm", "orange: the r[t] square before the transpose (16 token rows in dimension "
               "order)"),
        ("ink frame: the outline of each square", "none", C["ink"], False, False),
        ("arrow", "ink arrow: the transpose between the two squares"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR"),
    ]
    return figure(fid, W, H, "The constants FULL_BLOCK_0XFFFF and LANES_16 and the two "
                  "static_asserts", "".join(o), cap, boxes=boxes, legend=legend)
