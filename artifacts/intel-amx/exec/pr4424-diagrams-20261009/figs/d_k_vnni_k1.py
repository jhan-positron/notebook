"""Change diagram of unit k1 of the PR 4424 k_vnni.hpp page: the layout
constants, the bit helpers and the index map (head lines 57-118, 132-143).

Two figures (one cannot carry the unit legibly at half width):
  k_vnni-d1a  the constants of lines 61-93 drawn on the plane geometry of the
              worked example, and the three static_asserts of lines 106-117
              that relate them (the fourth is in d1b).
  k_vnni-d1b  the page-state masks (FULL_BLOCK_0XFFFF, BLOCKS_PER_PAGE_MASK_0XF,
              block_bit, offset_bit) on the worked example's bits, their
              readers, and index(37, 70) traced to element 5226.
Every fact comes from facts/k_vnni.json or the head file; line numbers are
head lines of h/tron/tensor/k_vnni.hpp unless another file is named.
"""
import sys

from svg_helpers import (C, arrow, bit_row, card_arrow, cite, figure, fn_cell,
                         label_box, line, lines, marker_defs, rect, text,
                         text_width)
from base_k_vnni import (EX, PAGE_7, SLOT_5, KV_HEAD_0, BLOCK_2, ROWS_SAVED_0_40,
                         BLOCK2_ROWS_SAVED, rm_forms, panel_grid, panel_lines,
                         pair_row_dwords)

BASE = ("Updates B1: every count of the plane in B1 (tokens, blocks, steps, pairs, "
        "lines, panels) gets its named constant. The static_assert at lines 106-111 "
        "pins the 12 derived constants. The second figure (d1b) updates B1 and the "
        "first cells of B3: the page-state masks block_bit / offset_bit / "
        "FULL_BLOCK_0XFFFF / BLOCKS_PER_PAGE_MASK_0XF, the n_slots + 1 state entries "
        "of a page, and index(37, 70) = 5226 are drawn on the worked example's bits.")

W = 720

# the worked example's chain through index (k_vnni.hpp:135-140), computed
PANEL = EX["s"] * 4 + EX["c"]                       # 10
PAIR_ROW = PANEL * 16 + EX["dp"]                    # 163
DWORD = PAIR_ROW * 16 + EX["t"]                     # 2613
ELEM = DWORD * 2 + EX["j"]                          # 5226
assert ELEM == EX["index"] == 5226 and DWORD * 4 == EX["byte"] == 10452


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
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
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    o.append(text(20, 16, "the constants of lines 61-93 drawn on the plane of the worked "
                  "example (slot 5, KV head 0, page 7)", 10.5, weight=700))
    o.append(text(20, 30, "every count on the figure is a named constant; the three checks "
                  "at the bottom are static_asserts of lines 106-117", 9.5, fill=C["muted"]))
    # ---- left column, row 1: the plane as its 16 panels -------------------
    o.append(text(20, 50, "plane = PAGE_TOKENS_64 x HEAD_SIZE_128 bf16", 10,
                  weight=600, fill=C["vnni"]))
    o.append(cite(20, 62, "k_vnni.hpp:24-28, 61-62", "start"))
    boxes.append(("plane = PAGE_TOKENS_64 x HEAD_SIZE_128 bf16", "k_vnni.hpp:24-28, 61-62"))
    o.append(text(20, 75, "TOKEN_BLOCKS_4 = 4 token blocks (c) of BLOCK_TOKENS_16", 9.5))
    gx, gy, cw, ch = 20, 94, 36, 30
    o.append(panel_grid(gx, gy, cw, ch, hi=(EX["s"], EX["c"]), block=BLOCK_2))
    boxes.append(("token block 2 (framed): BLOCK_TOKENS_16 tokens", "k_vnni.hpp:30-32, 68-69"))
    _lines(o, 20, 244, [
        "DIM_STEPS_4 = 4 steps (s) x STEP_DIMS_32 dims",
        "N_PANELS_16 = DIM_STEPS_4 x TOKEN_BLOCKS_4 panels",
        "block 2 (framed): BLOCK_TOKENS_16 tokens, offsets 32..47",
        "panel (2,2) #10 (blue): zoomed at the right"], 9.5, 12, 322, where="a left")
    o.append(cite(20, 294, "k_vnni.hpp:68-74, 82", "start"))
    boxes.append(("DIM_STEPS_4 steps of STEP_DIMS_32", "k_vnni.hpp:70-74"))
    boxes.append(("N_PANELS_16 = DIM_STEPS_4 x TOKEN_BLOCKS_4", "k_vnni.hpp:82"))
    # the how-many arrow from the (2,2) #10 cell (centre y = 176) to the zoom
    # of that panel; it starts right of the "s = 2" row label
    cell_y = gy + EX["s"] * (ch + 4) + ch / 2
    o.append(arrow(fid, "vnni", [(212, cell_y), (341, cell_y)], C["vnni"], 1.4))
    o.append(lines(214, cell_y - 34, ["1 panel ->", "STEP_PAIRS_16 pair rows"], 8.5, 10,
                   fill=C["vnni"], weight=600))
    o.append(text(214, cell_y - 12, "[k_vnni.hpp:78-80]", 8.5, mono=True, fill=C["cite"]))
    # ---- right column, row 1: panel #10 in its VNNI form ------------------
    px, py, pw, ph = 345, 94, 140, 128
    o.append(text(px, 50, "panel (2,2) #10, VNNI form (row-major form: bottom left)", 10,
                  weight=600, fill=C["vnni"]))
    o.append(cite(px, 62, "k_vnni.hpp:29-30, 78-82", "start"))
    boxes.append(("panel (2,2) #10, VNNI form", "k_vnni.hpp:29-30, 78-82"))
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
    o.append(cite(px + pw + 10, 177, "k_vnni.hpp:75-82", "start"))
    boxes.append(("STEP_PAIRS_16 pair rows x LINE_BYTES_64 = PANEL_BYTES_1024",
                  "k_vnni.hpp:75-82"))
    # ---- right column, row 2: the pair row and one dword --------------------
    o.append(card_arrow(fid, "vnni", [(415, 226), (415, 258)], C["vnni"],
                        "1 pair row -> ROW_DWORDS_16 dwords", 8, 0, anchor="start"))
    o.append(text(423, 254, "[k_vnni.hpp:66-68, 76-77]", 8.5, mono=True, fill=C["cite"]))
    rx, ry = 345, 262
    o.append(pair_row_dwords(rx, ry, 320, 24, hi_t=EX["t"], base_token=32))
    s = "pair row dp 3 = ROW_DWORDS_16 dwords, 1 per token"
    _w(s, 9.5, 320, where="a pair row title")
    o.append(text(rx, 309, s, 9.5, weight=600, fill=C["vnni"]))
    boxes.append(("pair row dp 3 of panel #10", "k_vnni.hpp:66-67, 75-77"))
    # one dword = PAIR_2 bf16 (k_vnni.hpp:63-65), the two halves
    dx, dy, dw, dh = 345, 318, 240, 28
    o.append(rect(dx, dy, dw / 2, dh, C["vnni_fill"], C["vnni"], 1.2, 0))
    o.append(rect(dx + dw / 2, dy, dw / 2, dh, "#fff", C["vnni"], 1.2, 0))
    o.append(text(dx + dw / 4, dy + 12, "low half, j = 0", 9, "middle"))
    o.append(text(dx + dw / 4, dy + 23, "dim 70 (even)", 9, "middle", True))
    o.append(text(dx + 3 * dw / 4, dy + 12, "high half, j = 1", 9, "middle"))
    o.append(text(dx + 3 * dw / 4, dy + 23, "dim 71 (odd)", 9, "middle", True))
    _lines(o, dx + dw + 10, dy + 11, ["dword 5 = token 37:", "DWORD_BYTES_4 bytes",
                                      "= PAIR_2 bf16"], 9, 10, 100, where="a dword")
    o.append(cite(dx + dw + 10, dy + 42, "k_vnni.hpp:63-65", "start"))
    boxes.append(("dword 5 = token 37: DWORD_BYTES_4 bytes = PAIR_2 bf16",
                  "k_vnni.hpp:75-77, 63-65"))
    _lines(o, dx, 364, [
        "even value << BF16_BITS_16 = the exact fp32",
        "odd value & HIGH_HALF_0XFFFF0000 = an fp32 bit pattern",
        "read only by k_vnni::qk_group's float-query path",
        "(kernels/k_vnni.hpp:109-114); no reader in this file"], 9.5, 12, 350,
        fill=C["ink"], where="a bf16 bits")
    o.append(cite(dx, 414, "k_vnni.hpp:87-90", "start"))
    boxes.append(("BF16_BITS_16, HIGH_HALF_0XFFFF0000", "k_vnni.hpp:87-90"))
    # ---- left column, row 2: the same panel in its row-major form -----------
    # the same panel as the blue cell (2,2) of the grid and the VNNI zoom at the
    # right; no link is drawn: any link from an interior grid cell crosses a
    # neighbour cell or the text block under the grid
    o.append(text(20, 306, "panel (2,2) #10, row-major form", 10, weight=600, fill=C["rm"]))
    o.append(text(20, 317, "the blue cell (2,2) above; its VNNI form is at the top right", 9,
                  fill=C["muted"]))
    o.append(cite(20, 328, "k_vnni.hpp:91-93, 441-445", "start"))
    mx, my = 20, 334
    forms = rm_forms(BLOCK2_ROWS_SAVED)[EX["s"]]       # panel (2,2): token 40 saved
    o.append(panel_lines(mx, my, 140, 128, forms, hi_rows=[0, 1, 2, 3]))
    _lines(o, 170, 346, [
        "PANEL_ROWS_4 = 4 token rows",
        "of HEAD_SIZE_128 bf16 = 256 B",
        "= 4 lines each; token t at",
        "panel (t / 4, c), row t % 4",
        "here: token 40 saved (thick),",
        "41..43 not yet (empty)"], 9.5, 12, 170, where="a rm labels")
    o.append(cite(170, 428, "k_vnni.hpp:91-93, 467-471", "start"))
    boxes.append(("PANEL_ROWS_4 token rows (the row-major form of panel #10)",
                  "k_vnni.hpp:91-93, 467-471"))
    # ---- the checks: static_asserts -----------------------------------------
    o.append(line(20, 470, 700, 470, C["line"]))
    o.append(text(20, 488, "the checks: static_asserts between the constants (lines 106-117)",
                  11, weight=700))
    sub1 = ["12 derived constants pinned to their number: BLOCK_TOKENS_16 == 16, "
            "TOKEN_BLOCKS_4 == 4, STEP_PAIRS_16 == 16,",
            "DIM_STEPS_4 == 4, ROW_ELEMS_32 == 32, ROW_DWORDS_16 == 16, PANEL_ELEMS_512 == 512, "
            "PANEL_BYTES_1024 == 1024,",
            "PANEL_DWORDS_256 == 256, N_PANELS_16 == 16, LANES_16 == 16, PANEL_ROWS_4 == 4",
            "the 6 literals PAGE_TOKENS_64, HEAD_SIZE_128, PAIR_2, DWORD_BYTES_4, "
            "LINE_BYTES_64 and STEP_DIMS_32",
            "are definitions: no static_assert names them"]
    for s in sub1:
        _w(s, 9, 600, where="a check 1")
    o.append(label_box(20, 498, 680, 100, 'static_assert "every constant\'s name states its value"',
                       sub1, "#fff", C["ink"], 10, ref="k_vnni.hpp:106-111"))
    boxes.append(('static_assert "every constant\'s name states its value"', "k_vnni.hpp:106-111"))
    # check 2: same element count, VNNI plane vs row-major plane
    cy = 618
    o.append(text(20, cy, 'static_assert "the VNNI plane is a permutation of the row-major '
                  'plane: same element count"', 10, weight=600))
    o.append(cite(700, cy, "k_vnni.hpp:114-115"))
    boxes.append(('static_assert "the VNNI plane is a permutation of the row-major plane: '
                  'same element count"', "k_vnni.hpp:114-115"))
    o.append(label_box(20, cy + 8, 300, 50, "N_PANELS_16 x PANEL_ELEMS_512",
                       ["16 panels x 512 bf16 = 8192 (the VNNI plane)"],
                       C["vnni_fill"], C["vnni"], 10.5, ref="k_vnni.hpp:79, 82"))
    boxes.append(("N_PANELS_16 x PANEL_ELEMS_512 (the VNNI plane)", "k_vnni.hpp:79, 82"))
    boxes.append(("PAGE_TOKENS_64 x HEAD_SIZE_128 (the row-major plane)", "k_vnni.hpp:61-62"))
    o.append(text(360, cy + 36, "==", 14, "middle", True, weight=700))
    o.append(label_box(400, cy + 8, 300, 50, "PAGE_TOKENS_64 x HEAD_SIZE_128",
                       ["64 tokens x 128 dims = 8192 (the row-major plane)"],
                       C["rm_fill"], C["rm"], 10.5, ref="k_vnni.hpp:61-62"))
    # check 3: the transpose size
    cy = 690
    o.append(text(20, cy, 'static_assert "the block save transposes 16 token rows onto '
                  'the 16 pair rows of a panel"', 10, weight=600))
    o.append(cite(700, cy, "k_vnni.hpp:116-117"))
    boxes.append(('static_assert "the block save transposes 16 token rows onto the 16 '
                  'pair rows of a panel"', "k_vnni.hpp:116-117"))
    o.append(label_box(20, cy + 8, 200, 50, "BLOCK_TOKENS_16", ["token rows of a block"],
                       C["rm_fill"], C["rm"], 10.5, ref="k_vnni.hpp:68"))
    boxes.append(("BLOCK_TOKENS_16 token rows of a block", "k_vnni.hpp:68"))
    boxes.append(("STEP_PAIRS_16 pair rows of a panel", "k_vnni.hpp:73"))
    o.append(text(235, cy + 36, "==", 14, "middle", True, weight=700))
    o.append(label_box(250, cy + 8, 200, 50, "LANES_16", ["LINE_BYTES_64 / DWORD_BYTES_4"],
                       "#fff", C["ink"], 10.5, ref="k_vnni.hpp:85-86, 315"))
    boxes.append(("LANES_16 = LINE_BYTES_64 / DWORD_BYTES_4", "k_vnni.hpp:85-86, 315"))
    o.append(text(465, cy + 36, "==", 14, "middle", True, weight=700))
    o.append(label_box(480, cy + 8, 200, 50, "STEP_PAIRS_16", ["pair rows of a panel"],
                       C["vnni_fill"], C["vnni"], 10.5, ref="k_vnni.hpp:73"))
    H = cy + 66
    cap = ("Updates B1: every count of the plane in B1 is now a named constant of lines "
           "61-93, drawn here on the plane of the worked example (page 7, storage slot 5, "
           "KV head 0). Look at panel #10 in its two forms (the two orange and blue "
           "headings name it): the VNNI form is STEP_PAIRS_16 "
           "pair rows of LINE_BYTES_64 bytes, the row-major form is PANEL_ROWS_4 token rows "
           "of HEAD_SIZE_128 bf16, and both are PANEL_BYTES_1024. The three checks at the "
           "bottom are the static_asserts that tie the constants together. The fourth "
           "static_assert (one bit per token block) is in the next figure.")
    legend = [
        ("vnni", "blue: the VNNI form. Panel (2,2) #10 as the grid cell and as its 16 pair "
                 "rows, dword 5 (token 37) and its low half, and the VNNI-plane boxes of the "
                 "checks (N_PANELS_16 x PANEL_ELEMS_512, STEP_PAIRS_16). Blue headings and "
                 "labels name the VNNI form"),
        ("white box, blue outline: the high half of dword 5 (j = 1, dim 71)",
         "#fff", C["vnni"], False, False),
        ("rm", "orange: the row-major form. The 4 lines of token 40 in panel #10, and the "
               "row-major boxes of the checks (PAGE_TOKENS_64 x HEAD_SIZE_128, "
               "BLOCK_TOKENS_16). The orange heading names the row-major form"),
        ("empty", "grey dashed: no row saved (bytes undefined), the 12 lines of tokens "
                  "41..43 in the row-major form of panel #10"),
        ("lane", "white cell, thin grey outline: a panel of the grid other than (2,2) #10, "
                 "and a dword of pair row dp 3 other than token 37's"),
        ("ink outline, no fill: the frame of token block 2 in the grid, pair row dp 3 of "
         "the VNNI form, the 4 lines of token 40 in the row-major form, and the border of "
         "each zoomed panel", "none", C["ink"], False, False),
        ("box", "white box, ink outline: the static_assert of lines 106-111 and LANES_16. "
                "Name in bold monospace, description in grey sans-serif"),
        ("blue arrow: a how-many arrow, 1 panel -> STEP_PAIRS_16 pair rows and 1 pair row "
         "-> ROW_DWORDS_16 dwords", "arrow", C["vnni"]),
        ("font_mono", "monospace = the constant names in the titles of the check boxes "
                      "(N_PANELS_16 x PANEL_ELEMS_512, PAGE_TOKENS_64 x HEAD_SIZE_128, "
                      "BLOCK_TOKENS_16, LANES_16, STEP_PAIRS_16) and of the static_assert "
                      "box, the panel indexes (s, c) and #n, the dp, token and dim labels, "
                      "and the '==' of the checks"),
        ("font_sans", "sans-serif = the figure title, the drawing titles, the constant "
                      "relations beside the drawings, the half-dword notes and the check "
                      "descriptions"),
        ("font_cite", "small grey monospace = the lines that define a drawing, a constant "
                      "or a check (file:line)"),
    ]
    return figure(fid, W, H, "The layout constants drawn on the plane geometry, and the "
                  "static_asserts that relate them", "".join(o), cap, boxes=boxes,
                  legend=legend)


# ---------------------------------------------------------------------------
# d1b: the page-state masks on the worked example's bits, and the index map


def _fig_b():
    fid = "k_vnni-d1b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rows": C["rows"],
                           "blk": C["blk"]})]
    o.append(text(20, 16, "the masks of lines 83-105 on the page state of the worked "
                  "example (page 7, storage slot 5)", 10.5, weight=700))
    o.append(text(20, 30, "rows 0..40 saved, block 0 converted, block 1 complete and waits; "
                  "the two words are page members (kv_cache.hpp:2484-2488)", 9.5,
                  fill=C["muted"]))
    # ---- k_rows_saved_[5]: 64 bits ----------------------------------------------
    o.append(text(20, 66, "k_rows_saved_[5]", 10, mono=True, weight=600, fill=C["rows"]))
    _lines(o, 20, 79, ["uint64_t: PAGE_TOKENS_64", "bits, one per page offset"], 9, 11, 136,
           fill=C["muted"], where="b rows label")
    o.append(cite(20, 103, "kv_cache.hpp:2616-2617", "start"))
    boxes.append(("k_rows_saved_[5]: PAGE_TOKENS_64 bits",
                  "kv_cache.hpp:2616-2617 (declaration); 2484-2488 (comment)"))
    bits = "".join("1" if i in ROWS_SAVED_0_40 else "0" for i in range(64))
    bx, by, cell, gap, ggap = 160, 56, 7, 1, 8
    body, _ = bit_row(bx, by, bits, cell, gap, C["rows_fill"], C["rows"], group=16,
                      group_gap=ggap)
    o.append(body)

    def bit_x(i):
        return bx + i * (cell + gap) + (i // 16) * ggap

    o.append(rect(bit_x(EX["token"]) - 1, by - 1, cell + 2, cell + 2, "none", C["ink"], 1.6, 1))
    gw = 16 * (cell + gap) - gap                       # 127: the width of one block's bits
    for c, lab in enumerate(["block 0 (bits 0..15)", "block 1 (16..31)", "block 2 (32..47)",
                             "block 3 (48..63)"]):
        _w(lab, 8.5, gw, where="b block labels")
        o.append(text(bit_x(16 * c) + gw / 2, 77, lab, 8.5, "middle",
                      fill=C["rows"] if c == BLOCK_2 else C["muted"]))
    boxes.append(("k_block_bits(2): the 16 bits of block 2", "kv_cache.hpp:2508-2510"))
    # the how-many arrow: 16 row bits -> 1 block bit
    ax = bx + 5
    o.append(card_arrow(fid, "ink", [(ax, 66), (ax, 100)], C["ink"],
                        "BLOCK_TOKENS_16 row bits -> 1 block bit", 6, 7, anchor="start"))
    # bold text renders about 15 % wider than text_width's estimate
    o.append(text(ax + 6 + text_width("BLOCK_TOKENS_16 row bits -> 1 block bit", 9.5) * 1.15 + 8,
                  90, "[kv_cache.hpp:2126-2128]", 8.5, mono=True, fill=C["cite"]))
    # ---- k_vnni_blocks_[5]: 4 bits under the 4 blocks -----------------------------
    o.append(text(20, 114, "k_vnni_blocks_[5]", 10, mono=True, weight=600, fill=C["blk"]))
    _lines(o, 20, 127, ["uint8_t, TOKEN_BLOCKS_4", "bits, one per block"], 9, 11, 136,
           fill=C["muted"], where="b blocks label")
    o.append(cite(20, 151, "kv_cache.hpp:2621-2622", "start"))
    boxes.append(("k_vnni_blocks_[5]: TOKEN_BLOCKS_4 bits",
                  "kv_cache.hpp:2621-2622 (declaration); 2484-2488 (comment)"))
    # block 0 converted = 0b0001; block 1 has its 16 row bits set and its block
    # bit clear: complete, may wait for the forward end (the pend state of the
    # legend); blocks 2 (9 row bits) and 3 (none) are drawn as 'no row saved'
    blocks = "1000"
    for c in range(4):
        on = blocks[c] == "1"
        pend = c == 1
        if on:
            o.append(rect(bit_x(16 * c), 102, gw, 16, C["blk_fill"], C["blk"], 1.2, 2))
        elif pend:
            o.append(rect(bit_x(16 * c), 102, gw, 16, C["pend_fill"], C["pend"], 1.6, 2, "5 3"))
        else:
            o.append(rect(bit_x(16 * c), 102, gw, 16, C["empty_fill"], C["empty"], 1, 2, "3 2"))
        lab = f"bit {c} = 1: converted" if on else (f"bit {c} = 0, waits" if pend else f"bit {c} = 0")
        o.append(text(bit_x(16 * c) + gw / 2, 113, lab, 9, "middle", True))
    boxes.append(("block 1: complete, may wait (16 row bits set, block bit clear)",
                  "kv_cache.hpp:692-701"))
    mask_lines = [
        (136, "k_vnni.hpp:101-105",
         "thick bit 37 = offset_bit(37) = uint64_t{1} << 37; one bit per page offset"),
        (149, "kv_cache.hpp:2508-2510",
         "block 2 = k_block_bits(2) = FULL_BLOCK_0XFFFF << (2 x BLOCK_TOKENS_16)"),
        (162, "k_vnni.hpp:97-100",
         "bit c = block_bit(c) = uint8_t(1u << c); here 0b0001: block 0 converted only"),
        (175, "k_vnni.hpp:94-96",
         "BLOCKS_PER_PAGE_MASK_0XF = 0b1111: all 4 blocks converted (the dense AMX gate)"),
        (188, "kv_cache.hpp:692-701",
         "block 1: 16 row bits set, block bit clear: complete, may wait")]
    for yy, ref, s in mask_lines:
        o.append(text(bx, yy, s, 9.5, fill=C["ink"]))
        cx = bx + text_width(s, 9.5) * 1.08 + 8      # regular text: ~8 % wider than the estimate
        _w(ref, 8.5, 700 - cx, True, "b line cites")
        o.append(text(cx, yy, ref, 8.5, mono=True, fill=C["cite"]))
    # ---- the page's n_slots + 1 entries of both words (data-33, data-7) -------------
    o.append(text(20, 211, "the page's entries of both words: layout_t::n_slots + "
                  "EAGLE_STORAGE_SLOTS_1 (one per storage slot)", 9.5, weight=600))
    ew, eg, ey = 72, 4, 218
    entries = [("[0]", None), ("[1]", None), ("...", None), ("[5]", "ex"), ("...", None),
               ("[n_slots - 1]", None), ("[n_slots]", "eagle")]
    for i, (lab, kind) in enumerate(entries):
        ex_ = bx + i * (ew + eg)
        if kind == "eagle":
            o.append(rect(ex_, ey, ew, 24, C["eagle_fill"], C["eagle"], 1.4, 2))
            o.append(text(ex_ + ew / 2, ey + 10, lab, 9, "middle", True))
            o.append(text(ex_ + ew / 2, ey + 20, "EAGLE", 8.5, "middle", fill=C["eagle"],
                          weight=600))
        else:
            o.append(rect(ex_, ey, ew, 24, C["rows_fill"] if kind else "#fff",
                          C["rows"] if kind else C["line"], 1.4 if kind else 1, 2))
            o.append(text(ex_ + ew / 2, ey + 15, lab, 9, "middle", True))
    o.append(text(20, ey + 15, "slot 5 (this example)", 9, fill=C["rows"], weight=600))
    o.append(cite(20, ey + 27, "kv_cache.hpp:2616-2622", "start"))
    boxes.append(("k_rows_saved_ / k_vnni_blocks_ entries: layout_t::n_slots + "
                  "EAGLE_STORAGE_SLOTS_1", "kv_cache.hpp:2616-2622; 2491-2492"))
    boxes.append(("entry [n_slots]: the EAGLE storage", "kv_cache.hpp:2491-2492; 2486"))
    s_ix = ["k_state_ix(slot) returns entry layout_t::n_slots for slot zero while "
            "book::eagle_view_active",
            "(the EAGLE view maps slot zero onto the EAGLE storage)"]
    for s_ in s_ix:
        _w(s_, 9, 700 - bx, where="b k_state_ix")
    o.append(lines(bx, ey + 36, s_ix, 9, 11, fill=C["ink"]))
    o.append(text(bx, ey + 58, "[kv_cache.hpp:2499-2505, 1082-1087]", 8.5, mono=True,
                  fill=C["cite"]))
    boxes.append(("k_state_ix(slot)", "kv_cache.hpp:2499-2505"))
    # ---- the four names and their readers ------------------------------------------
    D = 94                                            # the entries strip above
    o.append(line(20, 192 + D, 700, 192 + D, C["line"]))
    o.append(text(20, 210 + D, "the four names of this unit and who reads them", 11, weight=700))
    cw, ch = 335, 60
    o.append(fn_cell(20, 220 + D, cw, ch, "offset_bit(offset)",
                     ["Bit `offset` of a page-offset mask (the saved rows",
                      "of a page): the row at that page offset"],
                     "k_vnni.hpp:101-105", "new"))
    boxes.append(("offset_bit(offset)", "k_vnni.hpp:101-105"))
    _lines(o, 22, 291 + D, ["readers: note_k_row_saved kv_cache.hpp:2175, k_forget_row 2554,",
                        "copy_storage_slot 2714; apply_page_tok self_attention.hpp:2025",
                        "(live |= offset_bit(i): one live token per bit)"], 9, 10.5, cw,
           fill=C["muted"], where="b readers offset_bit")
    o.append(fn_cell(365, 220 + D, cw, ch, "block_bit(c)",
                     ["Bit c of a block mask (page::k_vnni_blocks):",
                      "token block c of the page"],
                     "k_vnni.hpp:97-100", "new"))
    boxes.append(("block_bit(c)", "k_vnni.hpp:97-100"))
    _lines(o, 367, 291 + D, ["readers: note_k_row_saved kv_cache.hpp:2182, note_k_block_saved",
                         "2199, k_block_to_vnni_at 2218, k_block_is_vnni 2517, k_forget_row",
                         "2555, copy_storage_slot 2742; apply_page_tok self_attention.hpp:2024"],
           9, 10.5, cw, fill=C["muted"], where="b readers block_bit")
    o.append(label_box(20, 330 + D, cw, ch, "FULL_BLOCK_0XFFFF",
                       ["__mmask16 0xffff: the 16 lanes of one token block,",
                        "all present (new)"], "#fff", C["ink"], 11, ref="k_vnni.hpp:83-84"))
    boxes.append(("FULL_BLOCK_0XFFFF", "k_vnni.hpp:83-84"))
    _lines(o, 22, 401 + D, ["readers: store_block's full-block test (410); passed by",
                        "page::set_k_block (kv_cache.hpp:2282-2283), block_to_vnni (508);",
                        "k_block_bits (kv_cache.hpp:2508-2510); store_k_block model.hpp:3323"],
           9, 10.5, cw, fill=C["muted"], where="b readers full block")
    o.append(label_box(365, 330 + D, cw, ch, "BLOCKS_PER_PAGE_MASK_0XF",
                       ["uint8_t 0xf: the 4 token blocks of a page, one bit",
                        "each; a mask equal to it has every block set (new)"],
                       "#fff", C["ink"], 11, ref="k_vnni.hpp:94-96"))
    boxes.append(("BLOCKS_PER_PAGE_MASK_0XF", "k_vnni.hpp:94-96"))
    _lines(o, 367, 401 + D, ["reader: k_layout_dense, the dense AMX gate:",
                         "page.k_vnni_blocks(slot) == BLOCKS_PER_PAGE_MASK_0XF",
                         "(self_attention.hpp:1925-1927)"], 9, 10.5, cw,
           fill=C["muted"], where="b readers mask")
    o.append(label_box(20, 442 + D, 680, 42,
                       'static_assert "one bit per token block": BLOCKS_PER_PAGE_MASK_0XF == '
                       'block_bit(TOKEN_BLOCKS_4) - 1',
                       ["the 4-bit mask covers exactly the TOKEN_BLOCKS_4 blocks of a page"],
                       "#fff", C["ink"], 11, ref="k_vnni.hpp:112-113"))
    boxes.append(('static_assert "one bit per token block": BLOCKS_PER_PAGE_MASK_0XF == '
                  'block_bit(TOKEN_BLOCKS_4) - 1', "k_vnni.hpp:112-113"))
    # ---- index(token, dim): the chain of the worked example ---------------------
    o.append(line(20, 498 + D, 700, 498 + D, C["line"]))
    o.append(text(20, 516 + D, "k_vnni::index(token, dim): the header formula as code, traced for "
                  "token 37, dim 70 (worked example)", 11, weight=700))
    boxes.append(("k_vnni::index(token, dim)", "k_vnni.hpp:132-141"))
    _lines(o, 20, 533 + D, [
        f"s = 70 / STEP_DIMS_32 = {EX['s']} ; c = 37 / BLOCK_TOKENS_16 = {EX['c']} ; "
        f"dp = (70 % STEP_DIMS_32) / PAIR_2 = {EX['dp']}",
        f"t = 37 % BLOCK_TOKENS_16 = {EX['t']} ; j = 70 % PAIR_2 = {EX['j']}"],
        9.5, 13, 680, mono=True, where="b coords")
    o.append(cite(20, 558 + D, "k_vnni.hpp:135-137", "start"))
    bw, bh, by2 = 145, 64, 575 + D
    chain = [
        (f"panel #{PANEL}", ["s x TOKEN_BLOCKS_4 + c", f"= 2 x 4 + 2 = {PANEL}"],
         "k_vnni.hpp:29-30, 138", f"panel #{PANEL} = s * TOKEN_BLOCKS_4 + c (line 138)"),
        (f"pair row {PAIR_ROW} of 256", [f"{PANEL} x STEP_PAIRS_16", f"+ dp 3 = {PAIR_ROW}"],
         "k_vnni.hpp:75-77, 138",
         f"pair row {PAIR_ROW} of 256 = panel * STEP_PAIRS_16 + dp (line 138)"),
        (f"dword {DWORD} of 4096", [f"{PAIR_ROW} x BLOCK_TOKENS_16", f"+ t 5 = {DWORD}"],
         "k_vnni.hpp:75-77, 138",
         f"dword {DWORD} of 4096 = pair row * BLOCK_TOKENS_16 + t (line 138)"),
        (f"index = {ELEM}", [f"{DWORD} x PAIR_2 + 0 = {ELEM}", f"x 2 B/bf16 = byte {EX['byte']}"],
         "k_vnni.hpp:132-141", f"index = {ELEM} = dword * PAIR_2 + j (lines 138-140)"),
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
    _lines(o, 20, 660 + D, [
        "readers of index: k_vnni_view::at(token, dim) returns data_[index(token, dim)] "
        "(k_vnni.hpp:185), the one production reader;",
        "t_k_vnni_layout.cpp:115-125 STATIC_REQUIRE index(0, 0) == 0 ... index(17, 34) == 2594, "
        "index(63, 127) == 8191;",
        "t_k_vnni_layout.cpp:154, 187: the bytes agree with index() after store_row; "
        "206: after copy_token"], 9.5, 12, 680, fill=C["ink"], where="b readers index")
    H = 696 + D
    cap = ("Updates B1 (and the first cells of B3): the two page-state words of "
           "kv_cache.hpp (k_rows_saved_, k_vnni_blocks_) are drawn with the worked "
           "example's bits (rows 0..40 saved, block 0 converted, block 1 complete and "
           "waiting in the dashed vermillion of the legend). The strip in the middle "
           "shows the page's layout_t::n_slots + EAGLE_STORAGE_SLOTS_1 entries of each "
           "word, with the EAGLE entry that k_state_ix selects for slot zero while the "
           "EAGLE view is active. The four names of "
           "this unit (offset_bit, block_bit, FULL_BLOCK_0XFFFF, BLOCKS_PER_PAGE_MASK_0XF) "
           "say which bits they select and who reads them. The bottom traces "
           "k_vnni::index(37, 70) through its four nested steps to element 5226 (byte "
           "10452), the number B1 prints, and names the readers of index.")
    legend = [
        ("rows", "green: k_rows_saved_[5], a saved-row bit that is set (rows 0..40), and "
                 "entry [5] of the strip (slot 5, this example). Green labels name them"),
        ("bit_clear", "white square: a saved-row bit that is clear, rows 41..63 of "
                      "k_rows_saved_[5]"),
        ("ink outline, no fill: bit 37 of k_rows_saved_[5] = offset_bit(37), the worked "
         "example's token", "none", C["ink"], False, False),
        ("blk", "pink box: a block bit that is set, bit 0 of k_vnni_blocks_[5] (block 0 "
                "converted); pink label = the word k_vnni_blocks_[5]"),
        ("pend", "orange box, orange-red dashed outline (complete, may wait): block 1, its "
                 "16 row bits set and its block bit clear (bit 1 = 0, waits)"),
        ("empty", "grey dashed: a block bit that is clear with the block not complete, "
                  "bits 2 and 3 of k_vnni_blocks_[5]"),
        ("eagle", "light sky-blue box (EAGLE storage): entry [n_slots] of both words, the "
                  "extra physical slot that k_state_ix selects for slot zero while "
                  "book::eagle_view_active; sky-blue label = the word EAGLE"),
        ("lane", "white box, thin grey outline: an entry of the strip other than [5] and "
                 "[n_slots]"),
        ("box", "white box, ink outline: the four names of this unit (offset_bit, "
                "block_bit, FULL_BLOCK_0XFFFF, BLOCKS_PER_PAGE_MASK_0XF) and the "
                "static_assert of lines 112-113. Name in bold monospace, description in "
                "sans-serif"),
        ("vnni", "blue: the four steps of k_vnni::index(37, 70), panel #10, pair row 163, "
                 "dword 2613, index 5226"),
        ("arrow", "ink arrow: a how-many arrow, BLOCK_TOKENS_16 row bits -> 1 block bit"),
        ("blue arrow: one step of index(37, 70). Its label is the multiply-add of that "
         "step (x STEP_PAIRS_16 + dp, x BLOCK_TOKENS_16 + t, x PAIR_2 + j)",
         "arrow", C["vnni"]),
        ("font_mono", "monospace = the two mask names, the bit values, the strip entries, "
                      "the four names of this unit, the static_assert, and the four index "
                      "steps with their values"),
        ("font_sans", "sans-serif = the figure title, the descriptions of the two words, "
                      "the block labels, the mask facts, the how-many labels, the readers "
                      "lists and the notes"),
        ("font_cite", "small grey monospace = the lines that define a word, a name, a check "
                      "or an index step (file:line)"),
        ("font_tag", "bold 'new' = offset_bit and block_bit are added by this PR"),
    ]
    return figure(fid, W, H, "The page-state masks on the worked example's bits, their "
                  "readers, and index(37, 70) traced to element 5226", "".join(o), cap,
                  boxes=boxes, legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
