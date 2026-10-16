"""Change diagram of unit k1 of the PR 4959 page for h/tron/tensor/k_vnni.hpp:
the constants and bit helpers of the layout state (head lines 87-113).
Line numbers are head lines of PR 4959 (6b081187e1)."""
from svg_helpers import C, arrow, cite, figure, fn_cell, lines, marker_defs, rect, text
from base_k_vnni import _w, bits4, bits64, EX

BASE = ("Updates B2: the bit helpers of B2 are drawn one by one with the worked example's "
        "values (block_bit(2), offset_bit(37), the full mask 0xf), and PANEL_ROWS_4 is "
        "drawn as the 4 token rows that one panel holds in the row-major form.")

W = 700


def fig():
    fid = "k_vnni-d1"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"]})]
    # ---- PANEL_ROWS_4 --------------------------------------------------------------
    o.append(fn_cell(14, 10, 330, 62, "PANEL_ROWS_4",
                     ["A row-major block keeps 4 token rows of",
                      "256 bytes in each of its 4 panels"], "k_vnni.hpp:87-89", "new"))
    boxes.append(("PANEL_ROWS_4", "k_vnni.hpp:87-89"))
    px, py, pw, ph = 360, 12, 240, 64
    o.append(text(px, py - 2, "one panel (PANEL_ELEMS_512 bf16 = 1 KiB) as 4 token rows", 9,
                  fill=C["muted"]))
    for r in range(4):
        o.append(rect(px, py + 4 + r * 15, pw, 15, C["rm_fill"], C["rm"], 1, 0))
        o.append(text(px + 4, py + 15 + r * 15, f"row {r}: HEAD_SIZE_128 bf16 = 256 B", 8.5,
                      mono=True))
    o.append(rect(px, py + 4, pw, 60, "none", C["ink"], 0.9, 0))
    o.append(text(px + pw + 6, py + 36, "= 512 / 128 = 4", 9.5, mono=True, weight=600))
    o.append(cite(px + pw + 6 + 90, py + 60, "k_vnni.hpp:87-89"))
    boxes.append(("one panel as 4 token rows", "k_vnni.hpp:87-89, 408-410"))
    o.append(text(14, 90, "readers: row_major_row divides and takes the remainder by it "
                  "[k_vnni.hpp:436, 438]; the static_assert pins it to 4 [k_vnni.hpp:102-107]",
                  9, fill=C["muted"]))
    # ---- block_bit and the full mask ------------------------------------------------
    y = 108
    o.append(fn_cell(14, y, 330, 62, "block_bit(c)",
                     ["Bit c of a block mask (page::k_vnni_blocks):",
                      "token block c of the page"], "k_vnni.hpp:93-96", "new"))
    boxes.append(("block_bit(c)", "k_vnni.hpp:93-96"))
    o.append(text(px, y + 10, "block_bit(2) = uint8_t(1u << 2) = 0b0100", 9.5, mono=True,
                  weight=600))
    svg, _ = bits4(px, y + 16, 0b0100)
    o.append(svg)
    for c in range(4):
        o.append(text(px + c * 16 + 7, y + 42, str(c), 8.5, "middle", True, fill=C["muted"]))
    o.append(text(px + 80, y + 28, "the worked example's block 2", 9, fill=C["muted"]))
    o.append(text(px, y + 60, "BLOCKS_PER_PAGE_MASK_0XF = 0xf = 0b1111", 9.5, mono=True,
                  weight=600))
    svg, _ = bits4(px, y + 66, 0b1111)
    o.append(svg)
    o.append(text(px + 80, y + 78, "= block_bit(TOKEN_BLOCKS_4) - 1 (assert 108-109)",
                  9, fill=C["muted"]))
    o.append(cite(px + 320, y + 94, "k_vnni.hpp:90-92, 108-109"))
    boxes.append(("BLOCKS_PER_PAGE_MASK_0XF", "k_vnni.hpp:90-92"))
    o.append(text(14, y + 80, "readers: k_block_is_vnni 2549, note_k_row_saved 2229,",
                  9, fill=C["muted"]))
    o.append(text(14, y + 91, "note_k_block_saved 2246, k_block_to_vnni_at 2265, the", 9,
                  fill=C["muted"]))
    o.append(text(14, y + 102, "loop of apply_page_tok 2008; the mask: k_layout_dense 1918", 9,
                  fill=C["muted"]))
    o.append(text(14, y + 114, "[kv_cache.hpp; self_attention.hpp]", 8.5, mono=True,
                  fill=C["cite"]))
    # ---- offset_bit -------------------------------------------------------------------
    y = 236
    o.append(fn_cell(14, y, 330, 62, "offset_bit(offset)",
                     ["Bit `offset` of a page-offset mask (the saved",
                      "rows of a page): the row at that page offset"], "k_vnni.hpp:97-101", "new"))
    boxes.append(("offset_bit(offset)", "k_vnni.hpp:97-101"))
    o.append(text(14, y + 80, f"offset_bit({EX['token']}) = uint64_t{{1}} << {EX['token']}: "
                  "the worked example's token, one square per page offset, bit 0 first", 9.5,
                  mono=True, weight=600))
    svg, xe = bits64(14, y + 88, 1 << EX["token"], cell=9, gap=1)
    o.append(svg)
    for c in range(4):
        o.append(text(14 + c * (16 * 10 + 8) + 80, y + 110, f"block {c}", 8.5, "middle",
                      fill=C["muted"]))
    o.append(text(14, y + 128, "offset_bit(offset) - 1 = the bits below the offset, and "
                  "block_bit(c) - 1 = the blocks below block c:", 9, fill=C["ink"]))
    o.append(text(14, y + 139, "k_forget_row keeps those and drops the rest (fetch_and) "
                  "[kv_cache.hpp:2585-2586, 2614-2615]", 9, fill=C["ink"]))
    o.append(text(14, y + 152, "readers: note_k_row_saved 2222 (the bit to set), k_forget_row "
                  "2585, copy_storage_slot 2744 (the range of a copy),", 9, fill=C["muted"]))
    o.append(text(14, y + 163, "the loop of apply_page_tok 2009 (live |= offset_bit(i))", 9,
                  fill=C["muted"]))
    o.append(text(14, y + 175, "[kv_cache.hpp; self_attention.hpp]", 8.5, mono=True,
                  fill=C["cite"]))
    # ---- the static_asserts ---------------------------------------------------------------
    y = 426
    o.append(rect(14, y, 672, 50, C["soft"], C["ink"], 1.2, 4))
    sl = ["static_assert: every constant's name states its value, now with PANEL_ROWS_4 == 4 "
          "(lines 102-107);",
          "BLOCKS_PER_PAGE_MASK_0XF == block_bit(TOKEN_BLOCKS_4) - 1, \"one bit per token "
          "block\" (lines 108-109)"]
    for s in sl:
        _w(s, 9.5, 656, where="k1 asserts")
    o.append(lines(22, y + 18, sl, 9.5, 14))
    o.append(cite(682, y + 46, "k_vnni.hpp:102-113"))
    boxes.append(("static_assert (the constants' names state their values)", "k_vnni.hpp:102-113"))
    H = y + 62
    cap = ("Updates B2: the four names this unit adds, each with the worked example's "
           "value. PANEL_ROWS_4 is the 4 token rows a panel holds in the row-major form. "
           "block_bit(2) is the bit of the worked example's block, and "
           "BLOCKS_PER_PAGE_MASK_0XF the mask with every block set (the AMX gate compares "
           "against it). offset_bit(37) is the bit of the worked example's token in the "
           "saved-row word. The grey lines under each helper name its readers in "
           "kv_cache.hpp and self_attention.hpp with their call-site lines.")
    legend = [
        ("box", "white box, ink outline: the three new names as function cells (name in "
                "bold monospace, what it is in sans-serif, its definition)"),
        ("rm", "orange: the 4 token rows of one panel in the row-major form (PANEL_ROWS_4)"),
        ("blk", "pink square: a set bit of a block mask (block_bit(2); the full mask)"),
        ("rows", "green square: the set bit of a page-offset mask (offset_bit(37))"),
        ("bit_clear", "white square: a clear bit"),
        ("ink frame: the outline of the panel drawn as 4 rows", "none", C["ink"], False, False),
        ("ctx_ink", "grey box, ink outline: the two static_asserts"),
        ("font_mono", "monospace = the names, the formulas and the values"),
        ("font_sans", "sans-serif = what each name is, and the readers (grey)"),
        ("font_cite", "small grey monospace = the lines that define a cell or a drawing "
                      "(file:line)"),
        ("font_tag", "bold 'new' = added by this PR (every cell)"),
    ]
    return figure(fid, W, H, "The constants and bit helpers of the layout state",
                  "".join(o), cap, boxes=boxes, legend=legend)
