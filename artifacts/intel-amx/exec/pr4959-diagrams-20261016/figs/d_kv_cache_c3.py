"""Change diagram of unit c3 of the kv_cache.hpp page (PR 4959): the read view
k_vnni_blocks, the converted-block byte of a slot, and who reads it.

Exposes fig() -> the HTML of figure "kv_cache-d3" and BASE.
Every label is an identifier or a comment phrase of the code; every box
cites the line or Note that defines it. Line numbers are head lines of
kv_cache.hpp (6b081187e1) unless a file name is given.
"""
from svg_helpers import (C, arrow, block_cell, cite, figure, fn_cell, legend_chip,
                         line, lines, marker_defs, rect, text, text_width)
from base_kv_cache import BLOCK_STATES_EXAMPLE, EXAMPLE, fit

BASE = ("Updates B3: the apply_page_tok row of the function model, drawn as the read "
        "path of the new k_vnni_blocks: the byte it returns, the two readers in "
        "self_attention.hpp that take the dense AMX kernel or the software loop from "
        "it, and the unchanged k_packed beside it as context.")


def reader_cell(x, y, w, h, lines_, refs):
    """A readers box (soft fill, like caller_cell of B3) with several text
    lines and one or two citation lines in the lower-right corner."""
    o = [rect(x, y, w, h, C["soft"], C["line"], 1, 4)]
    for s in lines_:
        fit(s, 9.5, w - 14, False, "reader_cell")
    o.append(lines(x + 8, y + 17, lines_, 9.5, 12))
    ry = y + h - 4 - 10 * (len(refs) - 1)
    for r in refs:
        fit(r, 8.5, w - 8, True, "reader_cell cite")
        o.append(cite(x + w - 4, ry, r))
        ry += 10
    return "".join(o)


def view_box(x, y, w, h, title_lines, sub, ref, fill, stroke):
    """A data box for a returned view or word: 1-2 mono title lines, sans
    sub-lines, citation lower-right."""
    o = [rect(x, y, w, h, fill, stroke, 1.4, 5)]
    ty = y + 15
    for i, t in enumerate(title_lines):
        fit(t, 10.5 if i == 0 else 9.5, w - 8, True, "view_box title")
        o.append(text(x + w / 2, ty, t, 10.5 if i == 0 else 9.5, "middle", True,
                      weight=700))
        ty += 13 if i == 0 else 12
    for s in sub:
        fit(s, 9, w - 10, False, "view_box sub")
        o.append(text(x + w / 2, ty, s, 9, "middle"))
        ty += 11.5
    fit(ref, 8.5, w - 8, True, "view_box cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def gap_label(x, y, items, color, maxw):
    """A 'how many' label of 2-3 short lines under a horizontal arrow."""
    o = []
    for i, s in enumerate(items):
        fit(s, 8.5, maxw, False, "gap_label")
        o.append(text(x, y + i * 10.5, s, 8.5, "middle", fill=color, weight=700))
    return "".join(o)


def fig():
    fid = "kv_cache-d3"
    W, H = 720, 652
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "blk": C["blk"],
                           "muted": C["muted"]})]
    boxes = []
    # columns
    FX, FW = 12, 218          # page accessor (fn_cell)
    VX, VW = 296, 194         # what it returns (data box)
    RX, RW = 512, 196         # readers
    GX = (FX + FW + VX) / 2   # centre of the labelled gap
    GW = VX - (FX + FW) - 6   # width available to the gap label
    o.append(text(12, 18, "The read view k_vnni_blocks: which blocks of a page hold the "
                  "VNNI layout", 12, weight=700))
    for x, w, h in [(FX, FW, "page accessor (kv_cache.hpp)"), (VX, VW, "what it returns"),
                    (RX, RW, "readers [attention workers]")]:
        fit(h, 10, w, False, "header")
        o.append(text(x + w / 2, 36, h, 10, "middle", weight=600, fill=C["muted"]))

    # ---- band: VNNI slot -----------------------------------------------------
    by = 44
    o.append(rect(12, by, 696, 18, C["vnni_fill"], C["vnni"], 1, 3))
    o.append(text(18, by + 13, "VNNI slot: k_vnni::layout_on<head_size> (TRON_K_VNNI, "
                  "head_size == 128)", 10, mono=True, weight=700))
    o.append(cite(704, by + 13, "tensor/k_vnni.hpp:115-123"))
    boxes.append(("k_vnni::layout_on<head_size> (the layout gate: TRON_K_VNNI and "
                  "head_size == 128)", "tensor/k_vnni.hpp:115-123"))
    # row 1: k_vnni_blocks (new)
    y = 68
    o.append(fn_cell(FX, y, FW, 64, "k_vnni_blocks(slot)",
                     ["the blocks of this page that hold the",
                      "VNNI layout for slot: one bit per block"],
                     "kv_cache.hpp:2174-2183", "new"))
    boxes.append(("page::k_vnni_blocks", "kv_cache.hpp:2174-2183"))
    o.append(arrow(fid, "blk", [(FX + FW + 2, y + 32), (VX - 2, y + 32)], C["blk"], 1.6))
    o.append(gap_label(GX, y + 46, ["1 slot ->", "1 byte,", "acquire"], C["blk"], GW))
    o.append(view_box(VX, y, VW, 88,
                      ["k_vnni_blocks_", "[k_state_ix(slot)]"],
                      ["uint8_t, load(memory_order_acquire):",
                       "TOKEN_BLOCKS_4 = 4 bits, bit c =",
                       "page offsets 16 c .. 16 c + 15"],
                      "kv_cache.hpp:2649-2653, 2531-2537", C["blk_fill"], C["blk"]))
    boxes.append(("k_vnni_blocks_[k_state_ix(slot)] (one byte per state entry, 4 block bits)",
                  "kv_cache.hpp:2649-2653; k_state_ix 2531-2537; TOKEN_BLOCKS_4 and "
                  "block_bit tensor/k_vnni.hpp:69, 94-96"))
    o.append(arrow(fid, "ink", [(VX + VW + 2, y + 44), (RX - 2, y + 44)], C["ink"], 1.4))
    o.append(reader_cell(RX, y, RW, 100,
                         ["k_layout_dense: the byte ==",
                          "BLOCKS_PER_PAGE_MASK_0XF (all 4",
                          "bits): the dense path's third gate",
                          "software loop: block_bit(i / 16)",
                          "set -> live, else row_major_row"],
                         ["self_attention.hpp:1915-1928,", "2003-2017"]))
    boxes.append(("k_layout_dense (== BLOCKS_PER_PAGE_MASK_0XF: the third gate of the "
                  "dense AMX path)", "self_attention.hpp:1915-1928; mask "
                  "tensor/k_vnni.hpp:90-92"))
    boxes.append(("block test of the software loop (block_bit(i / BLOCK_TOKENS_16))",
                  "self_attention.hpp:2003-2017"))
    # the removed line at the top of the excerpt
    gy = y + 100 + 8
    o.append(rect(FX, gy, 696, 34, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(FX + 8, gy + 14, "removed line at the top of the excerpt: the old one-line "
                  "comment of set_k_row (\"Store one token's K row in the slot's K layout\")",
                  9, fill=C["gone"], weight=600))
    o.append(text(FX + 8, gy + 27, "its replacement is the three-line comment at 2285-2287 "
                  "(unit C6): the row's saved bit is the caller's", 9, fill=C["gone"]))
    o.append(cite(FX + 696 - 4, gy + 30, "kv_cache.hpp:2285-2287"))
    boxes.append(("the old comment of set_k_row (removed; replaced at 2285-2287)",
                  "kv_cache.hpp:2285-2291 (the head comment of set_k_row)"))

    # row 2: k_packed (unchanged context)
    y = gy + 34 + 16
    o.append(fn_cell(FX, y, FW, 64, "k_packed(slot, kv_head)",
                     ["this page's packed K plane for one KV",
                      "head of one slot, read-only (PR 4956)"],
                     "kv_cache.hpp:2161-2172", "unchanged"))
    boxes.append(("page::k_packed", "kv_cache.hpp:2161-2172"))
    o.append(arrow(fid, "muted", [(FX + FW + 2, y + 32), (VX - 2, y + 32)], C["muted"], 1.4))
    o.append(gap_label(GX, y + 46, ["1 (slot,", "kv_head)", "-> 1 plane"], C["muted"], GW))
    o.append(view_box(VX, y, VW, 92,
                      ["k_vnni_view<const bf16,", "page_size, head_size>"],
                      ["k.as_view() const: the 16 KiB plane",
                       "at(token, dim) only; no element",
                       "write; row_major_row reads a tail row"],
                      "tensor/k_vnni.hpp:152-182, 193-205", C["soft"], C["line"]))
    boxes.append(("k_vnni_view<const bf16, page_size, geometry.head_size> (k.as_view())",
                  "tensor/k_vnni.hpp:152-182; as_view at 193-205"))
    o.append(arrow(fid, "muted", [(VX + VW + 2, y + 46), (RX - 2, y + 46)], C["muted"], 1.4))
    o.append(reader_cell(RX, y, RW, 100,
                         ["AMX path apply_dense_amx_page:",
                          "qk_vnni_128x4 (its B operand)",
                          "software loop: row_major_row +",
                          "dotter (bit clear); qk_group over",
                          "the live mask (bit set)"],
                         ["self_attention.hpp:1927-1928,", "2005-2016, 2029-2032"]))
    boxes.append(("qk_vnni_128x4(pg.k_packed(slot, kv_head), ...) in apply_dense_amx_page",
                  "self_attention.hpp:1742 (apply_dense_amx_page); amx_attn_iface.hpp:250-263"))
    boxes.append(("row_major_row(*plane, i) + dotter (row-major tail rows of the software loop)",
                  "self_attention.hpp:2011-2016; tensor/k_vnni.hpp:425-437"))
    boxes.append(("k_vnni::qk_group over the live mask (the AVX-512 reader of VNNI blocks)",
                  "self_attention.hpp:2029-2032; kernels/k_vnni.hpp:24-38"))

    # ---- worked example ---------------------------------------------------------
    sy = y + 100 + 14
    o.append(line(12, sy, 708, sy, C["line"]))
    o.append(text(12, sy + 18, f"worked example (B1): page {EXAMPLE['page']}, slot "
                  f"{EXAMPLE['slot']}: k_vnni_blocks(slot {EXAMPLE['slot']}) returns "
                  "0b0011, bits 2 and 3 clear", 11, weight=600))
    ex2 = ("k_layout_dense: 0b0011 != BLOCKS_PER_PAGE_MASK_0XF (all 4 bits), so the "
           "software loop reads the page, block by block:")
    fit(ex2, 9.5, 696, False, "example line 2")
    o.append(text(12, sy + 33, ex2, 9.5))
    bw, bh, gap, bx0, byy = 166, 34, 6, 19, sy + 42
    words = [["bit set: live |= offset_bit(i),", "scored by qk_group"],
             ["bit set: live |= offset_bit(i),", "scored by qk_group"],
             ["bit clear: row_major_row + dotter", "(14 rows, 32..45)"],
             ["no row saved: no token", "of block 3 is relevant"]]
    for c in range(4):
        gx = bx0 + c * (bw + gap)
        o.append(block_cell(gx, byy, bw, bh, BLOCK_STATES_EXAMPLE[c], f"block {c}", 11))
        for i, s in enumerate(words[c]):
            fit(s, 9, bw, False, "example words")
            o.append(text(gx + bw / 2, byy + bh + 13 + i * 11, s, 9, "middle"))
        o.append(text(gx, byy + bh + 38, f"offset {16 * c}", 8.5, fill=C["muted"]))
        o.append(text(gx + bw, byy + bh + 38, f"{16 * c + 15}", 8.5, "end", fill=C["muted"]))
    o.append(cite(708, byy + bh + 52, "self_attention.hpp:1915-1928, 2003-2017, 2029-2032; "
                  "kv_cache.hpp:819-828"))
    boxes.append(("k_vnni_blocks(slot 5) = 0b0011: the four blocks of page 7 read by "
                  "their bit (worked example)", "kv_cache.hpp:2174-2183 (k_vnni_blocks); "
                  "819-828 (consumer item 3); self_attention.hpp:2003-2032"))
    # legend
    ly = byy + bh + 62
    cx = 12
    for st, lab in [("vnni", "converted block: VNNI layout"),
                    ("rm", "row-major rows"), ("empty", "no row saved")]:
        o.append(legend_chip(cx, ly, st, lab))
        cx += 32 + text_width(lab, 11) + 16
    # notes
    ny = ly + 32
    notes = [
        "[attention workers] read a pending page only after every minibatch that writes "
        "it counted its latch down [kv_cache.hpp:731-733].",
        "the acquire load in k_vnni_blocks pairs with the release fetch_or in "
        "note_k_block_saved and k_block_to_vnni_at [2182, 2246, 2281].",
        "the byte is read after the dense predicate, at the first relevant token: a page "
        "nothing is relevant for",
        "is never asked [self_attention.hpp:1912-1914, 2004-2007].",
    ]
    for s in notes:
        fit(s, 9, 696, False, "notes")
    o.append(lines(12, ny, notes, 9, 12, fill=C["ink"]))
    cap = ("Updates B3: the apply_page_tok row of the function model, drawn as the read "
           "path of k_vnni_blocks. The attention workers get the converted-block byte "
           "of a slot with an acquire load. That byte picks the dense AMX kernel (all 4 "
           "bits set, the third gate k_layout_dense) or the software loop, where a "
           "token of a converted block goes into the live mask of qk_group and a token "
           "of a row-major block is scored by the dotter through row_major_row. The "
           "unchanged k_packed of PR 4956 hands the plane to both readers. The worked "
           "example shows the byte of slot 5, page 7 (0b0011) failing the dense gate, "
           "so blocks 0 and 1 are scored by qk_group and block 2 row by row.")
    legend = [
        ("box", "white box, ink outline: the page accessors k_vnni_blocks (new) and "
                "k_packed (unchanged); name in bold monospace, description in sans-serif"),
        ("ctx", "grey box, thin grey outline: the readers in self_attention.hpp of what "
                "each accessor returns (right column), and the unchanged plane view "
                "k_vnni_view that k_packed returns"),
        ("vnni", "blue: the VNNI slot band, and blocks 0 and 1 of the worked example "
                 "(converted: VNNI layout)"),
        ("blk", "pink: the byte k_vnni_blocks_[k_state_ix(slot)] that k_vnni_blocks "
                "returns"),
        ("rm", "orange: block 2 of the worked example (row-major rows)"),
        ("empty", "grey dashed: block 3 of the worked example (no row saved)"),
        ("gone", "red dashed, red text: the removed line at the top of the excerpt, the "
                 "old one-line comment of set_k_row"),
        ("pink arrow and its how-many label: k_vnni_blocks -> the k_vnni_blocks_ byte, "
         "1 slot -> 1 byte (acquire load)", "arrow", C["blk"]),
        ("arrow", "ink arrow: the returned byte, read by the attention workers"),
        ("arrow_muted", "grey arrow and grey label: the unchanged k_packed path, "
                        "1 (slot, kv_head) -> 1 plane, read by both readers"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = k_vnni_blocks, added by this PR; grey 'unchanged' = "
                     "k_packed, context from PR 4956"),
    ]
    return figure(fid, W, H, "The read view k_vnni_blocks and its two readers",
                  "".join(o), cap, boxes=boxes, legend=legend)
