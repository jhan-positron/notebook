"""Change diagram of unit c4 of the kv_cache.hpp page (PR 4424):
read views by layout: page::k for row-major slots, k_packed and
k_vnni_blocks for VNNI slots.

Exposes fig() -> the HTML of figure "kv_cache-d4" and BASE.
Every label is an identifier or a comment phrase of the code; every box
cites the line or Note that defines it. Line numbers are head lines of
kv_cache.hpp unless a file name is given.
"""
from svg_helpers import (C, arrow, block_cell, cite, figure, fn_cell, legend_chip,
                         line, lines, marker_defs, rect, text, text_width)
from base_kv_cache import BLOCK_STATES_EXAMPLE, EXAMPLE, fit

BASE = ("Updates B3: the apply_page_tok row and the row-major-only row of the "
        "function model, drawn as three read paths: page::k now exists for "
        "row-major slots only, and the new k_packed and k_vnni_blocks hand the "
        "attention workers the VNNI plane and the block bits that pick the dense "
        "AMX kernel or the software loop.")


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
    fid = "kv_cache-d4"
    W, H = 720, 636
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "blk": C["blk"]})]
    boxes = []
    # columns
    FX, FW = 12, 218          # page accessor (fn_cell)
    VX, VW = 296, 194         # what it returns (data box)
    RX, RW = 512, 196         # readers
    GX = (FX + FW + VX) / 2   # centre of the labelled gap
    GW = VX - (FX + FW) - 6   # width available to the gap label
    o.append(text(12, 18, "Read views of K: the slot's layout gate decides which page "
                  "accessors exist", 12, weight=700))
    for x, w, h in [(FX, FW, "page accessor (kv_cache.hpp)"), (VX, VW, "what it returns"),
                    (RX, RW, "readers [attention workers]")]:
        fit(h, 10, w, False, "header")
        o.append(text(x + w / 2, 36, h, 10, "middle", weight=600, fill=C["muted"]))

    # ---- band A: row-major slot ---------------------------------------------
    by = 44
    o.append(rect(12, by, 696, 18, C["rm_fill"], C["rm"], 1, 3))
    o.append(text(18, by + 13, "row-major slot: !k_vnni::layout_on<head_size>", 10,
                  mono=True, weight=700))
    o.append(cite(704, by + 13, "tensor/k_vnni.hpp:119-130"))
    boxes.append(("k_vnni::layout_on<head_size> (the layout gate: TRON_K_VNNI and "
                  "head_size == 128)", "tensor/k_vnni.hpp:119-130"))
    # row 1: page::k
    y = 68
    o.append(fn_cell(FX, y, FW, 64, "page::k (8 overloads)",
                     ["the row view: one contiguous row per",
                      "token; now requires !k_vnni::layout_on"],
                     "kv_cache.hpp:2040-2106", "changed"))
    boxes.append(("page::k (8 overloads, now requires !k_vnni::layout_on)",
                  "kv_cache.hpp:2040-2106; the constraint at 2045, 2051, 2057, 2066, "
                  "2077, 2084, 2090, 2100"))
    o.append(arrow(fid, "rm", [(FX + FW + 2, y + 32), (VX - 2, y + 32)], C["rm"], 1.6))
    o.append(gap_label(GX, y + 46, ["1 (slot,", "kv_head)", "-> 1 view"], C["rm"], GW))
    o.append(view_box(VX, y, VW, 78, ["kv_block::k_view()"],
                      ["page_size = 64 rows x head_size bf16",
                       "native K only: a packed plane",
                       "has no contiguous rows"],
                      "kv_cache.hpp:3017-3038", C["rm_fill"], C["rm"]))
    boxes.append(("kv_block::k_view (the row-major K view, native K only)",
                  "kv_cache.hpp:3017-3038; one plane = page_size x head_size bf16 "
                  "(kv_cache.hpp:822-825)"))
    o.append(arrow(fid, "ink", [(VX + VW + 2, y + 39), (RX - 2, y + 39)], C["ink"], 1.4))
    o.append(reader_cell(RX, y, RW, 78,
                         ["AMX path apply_dense_amx_page:",
                          "qk_rowmajor_128x4 (its A operand)",
                          "software loop: keys[i] -> dotter",
                          "also model.hpp:3259, full.hpp:2770"],
                         ["self_attention.hpp:1785, 2036"]))
    boxes.append(("qk_rowmajor_128x4(pg.k(slot, kv_head), ...) in apply_dense_amx_page",
                  "self_attention.hpp:1784-1787; amx_attn_iface.hpp:230-239 (the kernel's "
                  "comment and declaration)"))
    boxes.append(("keys[i] -> dotter (the row-major software loop)",
                  "self_attention.hpp:2035-2039"))
    # the removed state: k() for every slot
    gy = y + 64 + 6
    o.append(rect(FX, gy, FW, 44, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(FX + 8, gy + 14, "before: k() existed for every slot", 9.5,
                  fill=C["gone"], weight=600))
    o.append(text(FX + 8, gy + 27, "removed for VNNI slots (consumer item 6)", 9,
                  fill=C["gone"]))
    o.append(cite(FX + FW - 4, gy + 40, "kv_cache.hpp:2041-2042, 811-815"))
    boxes.append(("k() for every slot (before: requires(layout_t::uniform_geometry) only)",
                  "the base lines of the diff hunk at kv_cache.hpp:2040-2106; the head "
                  "comment 2041-2042 and consumer item 6 (kv_cache.hpp:811-815)"))

    # ---- band B: VNNI slot ---------------------------------------------------
    by = 192
    o.append(rect(12, by, 696, 18, C["vnni_fill"], C["vnni"], 1, 3))
    o.append(text(18, by + 13, "VNNI slot: k_vnni::layout_on<head_size> (TRON_K_VNNI, "
                  "head_size == 128)", 10, mono=True, weight=700))
    o.append(cite(704, by + 13, "tensor/k_vnni.hpp:119-130"))
    # row 2: k_packed
    y = 216
    o.append(fn_cell(FX, y, FW, 64, "k_packed(slot, kv_head)",
                     ["this page's packed K plane for one KV",
                      "head of one slot, read-only"],
                     "kv_cache.hpp:2108-2124", "new"))
    boxes.append(("page::k_packed", "kv_cache.hpp:2108-2124"))
    o.append(arrow(fid, "vnni", [(FX + FW + 2, y + 32), (VX - 2, y + 32)], C["vnni"], 1.6))
    o.append(gap_label(GX, y + 46, ["1 (slot,", "kv_head)", "-> 1 plane"], C["vnni"], GW))
    o.append(view_box(VX, y, VW, 92,
                      ["k_vnni_view<const bf16,", "page_size, head_size>"],
                      ["k.as_view() const: the 16 KiB plane",
                       "at(token, dim) only; no data(),",
                       "no operator[], no element write"],
                      "tensor/k_vnni.hpp:156-199, 214-227", C["vnni_fill"], C["vnni"]))
    boxes.append(("k_vnni_view<const bf16, page_size, geometry.head_size> (k.as_view())",
                  "tensor/k_vnni.hpp:156-199; as_view at 214-227; 16 KiB plane "
                  "(tensor/k_vnni.hpp:21-24)"))
    o.append(arrow(fid, "ink", [(VX + VW + 2, y + 46), (RX - 2, y + 46)], C["ink"], 1.4))
    o.append(reader_cell(RX, y, RW, 100,
                         ["AMX path apply_dense_amx_page:",
                          "qk_vnni_128x4 (its B operand)",
                          "software loop: row_major_row +",
                          "dotter (bit clear); qk_group over",
                          "the live mask (bit set)"],
                         ["self_attention.hpp:1782,", "2022-2033, 2042-2049"]))
    boxes.append(("qk_vnni_128x4(pg.k_packed(slot, kv_head), ...) in apply_dense_amx_page",
                  "self_attention.hpp:1781-1783; amx_attn_iface.hpp:250-263"))
    boxes.append(("row_major_row(*plane, i) + dotter (row-major tail rows of the software loop)",
                  "self_attention.hpp:2026-2033; tensor/k_vnni.hpp:458-472"))
    boxes.append(("k_vnni::qk_group over the live mask (the AVX-512 reader of VNNI blocks)",
                  "self_attention.hpp:2042-2049; kernels/k_vnni.hpp:59-65"))
    # row 3: k_vnni_blocks
    y = 330
    o.append(fn_cell(FX, y, FW, 64, "k_vnni_blocks(slot)",
                     ["the blocks of this page that hold the",
                      "VNNI layout for slot: one bit per block"],
                     "kv_cache.hpp:2126-2135", "new"))
    boxes.append(("page::k_vnni_blocks", "kv_cache.hpp:2126-2135"))
    o.append(arrow(fid, "blk", [(FX + FW + 2, y + 32), (VX - 2, y + 32)], C["blk"], 1.6))
    o.append(gap_label(GX, y + 46, ["1 slot ->", "1 byte,", "acquire"], C["blk"], GW))
    o.append(view_box(VX, y, VW, 88,
                      ["k_vnni_blocks_", "[k_state_ix(slot)]"],
                      ["uint8_t, load(memory_order_acquire):",
                       "TOKEN_BLOCKS_4 = 4 bits, bit c =",
                       "page offsets 16 c .. 16 c + 15"],
                      "kv_cache.hpp:2618-2622, 2499-2505", C["blk_fill"], C["blk"]))
    boxes.append(("k_vnni_blocks_[k_state_ix(slot)] (one byte per state entry, 4 block bits)",
                  "kv_cache.hpp:2618-2622; k_state_ix 2499-2505; TOKEN_BLOCKS_4 and "
                  "block_bit tensor/k_vnni.hpp:94-100"))
    o.append(arrow(fid, "ink", [(VX + VW + 2, y + 44), (RX - 2, y + 44)], C["ink"], 1.4))
    o.append(reader_cell(RX, y, RW, 100,
                         ["k_layout_dense: the byte ==",
                          "BLOCKS_PER_PAGE_MASK_0XF (all 4",
                          "bits): the dense path's third gate",
                          "software loop: block_bit(i / 16)",
                          "set -> live, else row_major_row"],
                         ["self_attention.hpp:1924-1935,", "2021-2026"]))
    boxes.append(("k_layout_dense (== BLOCKS_PER_PAGE_MASK_0XF: the third gate of the "
                  "dense AMX path)", "self_attention.hpp:1924-1935; mask "
                  "tensor/k_vnni.hpp:94-96"))
    boxes.append(("block test of the software loop (block_bit(i / BLOCK_TOKENS_16))",
                  "self_attention.hpp:2021-2026"))

    # ---- worked example ---------------------------------------------------------
    sy = 442
    o.append(line(12, sy, 708, sy, C["line"]))
    o.append(text(12, sy + 18, f"worked example (B1): page {EXAMPLE['page']}, slot "
                  f"{EXAMPLE['slot']}: k_vnni_blocks(slot {EXAMPLE['slot']}) returns "
                  "block_bit(0) only, bits 1..3 clear", 11, weight=600))
    ex2 = ("k_layout_dense: block_bit(0) != BLOCKS_PER_PAGE_MASK_0XF (all 4 bits), so "
           "the software loop reads the page, block by block:")
    fit(ex2, 9.5, 696, False, "example line 2")
    o.append(text(12, sy + 33, ex2, 9.5))
    bw, bh, gap, bx0, byy = 166, 34, 6, 19, sy + 42
    words = [["bit set: live |= offset_bit(i),", "scored by qk_group"],
             ["bit clear: row_major_row + dotter", "(complete, may wait)"],
             ["bit clear: row_major_row + dotter", "(9 rows, 32..40)"],
             ["no row bit", ""]]
    for c in range(4):
        gx = bx0 + c * (bw + gap)
        o.append(block_cell(gx, byy, bw, bh, BLOCK_STATES_EXAMPLE[c], f"block {c}", 11))
        for i, s in enumerate(words[c]):
            fit(s, 9, bw, False, "example words")
            o.append(text(gx + bw / 2, byy + bh + 13 + i * 11, s, 9, "middle"))
        o.append(text(gx, byy + bh + 38, f"offset {16 * c}", 8.5, fill=C["muted"]))
        o.append(text(gx + bw, byy + bh + 38, f"{16 * c + 15}", 8.5, "end", fill=C["muted"]))
    o.append(cite(708, byy + bh + 52, "self_attention.hpp:1924-1935, 2019-2033, 2042-2049; "
                  "kv_cache.hpp:785-792"))
    boxes.append(("k_vnni_blocks(slot 5) = block_bit(0): the four blocks of page 7 read by "
                  "their bit (worked example)", "kv_cache.hpp:2126-2135 (k_vnni_blocks); "
                  "785-792 (consumer item 3); self_attention.hpp:2019-2049"))
    # legend
    ly = byy + bh + 62
    cx = 12
    for st, lab in [("vnni", "converted block: VNNI layout"), ("pend", "complete, may wait"),
                    ("rm", "row-major rows"), ("empty", "no row bit")]:
        o.append(legend_chip(cx, ly, st, lab))
        cx += 32 + text_width(lab, 11) + 16
    # notes
    ny = ly + 32
    notes = [
        "[attention workers] read a pending page only after every minibatch that writes "
        "it counted its latch down [kv_cache.hpp:697-699].",
        "acquire load in k_vnni_blocks pairs with release fetch_or in "
        "note_k_block_saved and k_block_to_vnni_at [kv_cache.hpp:2134, 2199, 2234].",
    ]
    for s in notes:
        fit(s, 9, 696, False, "notes")
    o.append(lines(12, ny, notes, 9, 12, fill=C["ink"]))
    cap = ("Updates B3: the apply_page_tok row and the row-major-only row of the "
           "function model, drawn as three read paths with the layout gate "
           "k_vnni::layout_on<head_size> as the band that decides which exist. "
           "The row view page::k (8 overloads) now requires a row-major slot (the "
           "dashed red box is the removed case). For a VNNI slot the attention "
           "workers get the read-only plane from k_packed and the converted-block "
           "byte from k_vnni_blocks (an acquire load). That byte picks the "
           "dense AMX kernel (all 4 bits set) or the software loop. The worked example "
           "shows the byte of slot 5, page 7 (block_bit(0) only) failing the dense "
           "gate, so block 0 is scored by qk_group and blocks 1 and 2 row by row.")
    legend = [
        ("box", "white box, ink outline: the page accessors page::k, k_packed, "
         "k_vnni_blocks; name in bold monospace, description in sans-serif"),
        ("ctx", "grey box, thin grey outline: the readers in self_attention.hpp of what "
         "each accessor returns (right column)"),
        ("rm", "orange: the row-major slot band, the row view kv_block::k_view(), "
         "block 2 of the worked example (row-major rows)"),
        ("vnni", "blue: the VNNI slot band, the returned k_vnni_view plane, block 0 "
         "of the worked example (converted: VNNI layout)"),
        ("blk", "pink: the byte k_vnni_blocks_[k_state_ix(slot)] that k_vnni_blocks "
         "returns"),
        ("pend", "orange-red dashed: block 1 of the worked example (complete, may wait)"),
        ("empty", "grey dashed: block 3 of the worked example (no row bit)"),
        ("gone", "red dashed, red text: before, k() existed for every slot (removed "
         "for VNNI slots)"),
        ("orange arrow and its how-many label: page::k -> kv_block::k_view(), "
         "1 (slot, kv_head) -> 1 view", "arrow", C["rm"]),
        ("blue arrow and its how-many label: k_packed -> k_vnni_view, "
         "1 (slot, kv_head) -> 1 plane", "arrow", C["vnni"]),
        ("pink arrow and its how-many label: k_vnni_blocks -> the k_vnni_blocks_ byte, "
         "1 slot -> 1 byte (acquire load)", "arrow", C["blk"]),
        ("arrow", "ink arrow: the returned view or byte, read by the attention workers"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = k_packed and k_vnni_blocks, added by this PR; "
         "grey 'changed' = page::k, changed by it"),
    ]
    return figure(fid, W, H, "Read views of K by layout: page::k, k_packed, k_vnni_blocks",
                  "".join(o), cap, boxes=boxes, legend=legend)
