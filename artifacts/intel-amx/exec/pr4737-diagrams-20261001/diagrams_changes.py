"""Per-change diagrams D0-D8 of the PR 4737 kv_cache.hpp page (500 px wide)."""
from svg_helpers import (C, arrow, bit_row, block_cell, figure, label_box,
                         line, lines, marker_defs, rect, text)
from diagrams_base import ROWS_EXAMPLE, BLOCKS_EXAMPLE, BLOCK_STATES_EXAMPLE

WD = 500


def d0():
    fid = "d0"
    W, H = WD, 250
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(10, 20, "paragraph of the note (head lines)", 11, weight=600))
    o.append(text(330, 20, "drawn in", 11, weight=600))
    rows = [(["state and the two layouts (672-680)"], "B1, B2"),
            (["writers: save_k, whole-block save (681-705)"], "B4, B5"),
            (["why not in save_k: the staging reader (689-699)"], "B5"),
            (["clear_kv_complete_at, page copies (706-713)"], "B4, D7, D8"),
            (["why 16 saved rows; the dense page (714-721)"], "B2, D1"),
            (["Note [Row-major blocks under hardware", "attention] (723-759)"],
             "B4 lower path, D5, D6"),
            (["consumer items 1-6 reworded (761-803)"], "B3")]
    y = 40
    for left, right in rows:
        h = 20 if len(left) == 1 else 34
        o.append(rect(10, y - 13, 300, h, C["soft"], C["line"], 1, 3))
        o.append(lines(16, y + 1, left, 10.5, 14))
        ay = y - 13 + h / 2
        o.append(arrow(fid, "ink", [(312, ay), (326, ay)], C["ink"]))
        o.append(text(330, ay + 4, right, 10.5, mono=True))
        y += h + 5
    cap = ("D0. The rewritten note is comment text; the base diagrams are its "
           "picture. Each paragraph points at the diagram that draws it.")
    return figure(fid, W, H, "Map from note paragraphs to base diagrams", "".join(o), cap)


def d1():
    fid = "d1"
    W, H = WD, 400
    o = [marker_defs(fid, {"ink": C["ink"], "blk": C["blk"]})]
    # entries
    o.append(text(10, 22, "the two arrays of page 7, one entry per storage slot + E", 11,
                  weight=600))
    for row, (name, col, fill) in enumerate([("k_rows_saved_", C["rows"], C["rows_fill"]),
                                             ("k_vnni_blocks_", C["blk"], C["blk_fill"])]):
        y = 34 + row * 30
        o.append(text(10, y + 15, name, 10, mono=True, fill=col))
        cx = 120
        for lab in ["0", "1", "5", "...", "n-1"]:
            hi = lab == "5"
            o.append(rect(cx, y, 44, 22, fill if hi else "#fff", col, 1.6 if hi else 1, 3))
            o.append(text(cx + 22, y + 15, lab, 10, "middle", True))
            cx += 48
        o.append(rect(cx, y, 36, 22, C["eagle_fill"], C["eagle"], 1.4, 3))
        o.append(text(cx + 18, y + 15, "E", 10, "middle", True))
    o.append(text(400, 49, "64 bits each", 9, fill=C["muted"]))
    o.append(text(400, 79, "4 bits each", 9, fill=C["muted"]))
    # zoom of entry 5
    o.append(text(10, 122, "entry 5, bit 0 at the left", 10.5, weight=600))
    o.append(text(10, 142, "rows", 9.5, mono=True, fill=C["rows"]))
    body, _ = bit_row(70, 133, ROWS_EXAMPLE, 5, 1, C["rows_fill"], C["rows"], group=16,
                      group_gap=8)
    o.append(body)
    o.append(text(10, 164, "blocks", 9.5, mono=True, fill=C["blk"]))
    for c in range(4):
        gx = 70 + c * 103
        on = BLOCKS_EXAMPLE[c] == "1"
        o.append(rect(gx, 155, 10, 10, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(text(gx + 14, 164, f"bit {c}", 9, fill=C["muted"]))
    for c in range(4):
        gx = 70 + c * 103
        o.append(block_cell(gx, 172, 95, 30, BLOCK_STATES_EXAMPLE[c], f"block {c}", 10))
    # bracket k_block_bits(2)
    o.append(line(276, 128, 371, 128, C["rows"], 1.4))
    o.append(line(276, 128, 276, 132, C["rows"], 1.4))
    o.append(line(371, 128, 371, 132, C["rows"], 1.4))
    o.append(text(323, 118, "k_block_bits(2) = 0xFFFF << 32", 9, "middle", True,
                  fill=C["rows"]))
    # k_block_is_vnni annotation
    o.append(arrow(fid, "blk", [(300, 232), (282, 168)], C["blk"], 1.2))
    o.append(lines(302, 236, ["k_block_is_vnni(5, offset 37):",
                              "bit 2 of k_vnni_blocks_[5] is clear",
                              "-> block 2 is row-major"], 9.5, 12, mono=True,
                   fill=C["blk"]))
    o.append(lines(10, 236, ["k_vnni_blocks(slot 5) returns 0b0001;",
                             "the dense gate wants 0b1111",
                             "(BLOCKS_PER_PAGE_MASK_0XF)"], 9.5, 12, mono=True))
    # constants + invariant
    o.append(line(10, 284, 490, 284, C["line"]))
    o.append(lines(10, 302, ["EAGLE_STORAGE_SLOTS_1 = 1: the extra entry E",
                             "BLOCK_COMPLETED_FALSE, CONVERTED_FALSE, CONVERTED_TRUE:",
                             "    named return values of C3 and C4",
                             "invariant: a set block bit implies the block's 16 row bits;",
                             "    the reverse does not hold (block 1 above)",
                             "the move constructor copies both arrays with the page"],
                   10, 15))
    cap = ("D1. The new state of B1, instantiated for the worked example. The 16 bits "
           "of block c are k_block_bits(c); k_block_is_vnni reads bit c of the block "
           "byte; k_vnni_blocks hands the byte to the dense gate.")
    return figure(fid, W, H, "The two bit arrays and their helpers", "".join(o), cap)


def d2():
    fid = "d2"
    W, H = WD, 380
    o = [marker_defs(fid, {"ink": C["ink"], "eagle": C["eagle"]})]

    def panel(x, title, rows, note):
        o.append(text(x, 20, title, 11, weight=600))
        for i, h in enumerate(["logical slot", "storage offset", "state entry"]):
            o.append(text(x + 10 + i * 80, 38, h, 9, fill=C["muted"]))
        y = 46
        for lab, off, ent, eagle in rows:
            cols = [lab, off, ent]
            for i, v in enumerate(cols):
                cx = x + 10 + i * 80
                fill = C["eagle_fill"] if (eagle and i > 0) else "#fff"
                stroke = C["eagle"] if (eagle and i > 0) else C["ink"]
                if v is None:
                    o.append(text(cx + 30, y + 14, "-", 10, "middle", fill=C["muted"]))
                    continue
                o.append(rect(cx, y, 60, 20, fill, stroke, 1, 3))
                o.append(text(cx + 30, y + 14, v, 9.5, "middle", True))
                if i < 2 and cols[i + 1] is not None:
                    o.append(arrow(fid, "ink", [(cx + 62, y + 10), (cx + 78, y + 10)],
                                   C["ink"], 1))
            y += 26
        o.append(lines(x, y + 12, note, 9.5, 12, fill=C["muted"]))

    panel(10, "normal view (storage_view_offset_ = 0)",
          [("0", "0", "0", False), ("1", "1", "1", False), ("5", "5", "5", False),
           ("n-1", "n-1", "n-1", False), (None, "n (EAGLE)", "n", True)],
          ["the EAGLE slot is addressed by no", "logical slot; its entry stays idle"])
    panel(260, "EAGLE view: eagle_view_active()",
          [("0", "n (EAGLE)", "n", True), ("1..n-1", None, None, False)],
          ["logical slots 1..n-1 are not exposed", "(TRON_ASSERT in book::kv_block)"])
    # bottom: the ref and the helpers
    o.append(line(10, 222, 490, 222, C["line"]))
    o.append(rect(10, 232, 200, 40, "#fff", C["ink"], 1.2, 4))
    o.append(text(110, 249, "k_storage_ref", 11, "middle", True, weight=700))
    o.append(text(110, 264, "{ offset, state_ix }", 10, "middle", True))
    o.append(lines(222, 246, ["k_storage_of(slot): ix = k_state_ix(slot);",
                              "offset = ix == n ? eagle_storage_offset() : slot.i",
                              "(a logical slot under the current view)"], 9.5, 12,
                   mono=True))
    o.append(lines(10, 296, ["copy_from builds the pair from the PHYSICAL slot: {offset(slot), slot}",
                             "per active slot, and {eagle_storage_offset(), n} for the EAGLE storage.",
                             "A page copy moves every physical slot, whatever the view."],
                   9.5, 12))
    o.append(lines(10, 342, ["k_with_storage_geometry(offset, f): offset < logical_slot_count()",
                             "-> f with that slot's declared geometry; else f with the primary",
                             "geometry (the EAGLE storage). Used by C4 and C7 to reach the planes."],
                   9.5, 12))
    cap = ("D2. Which state entry and which physical slot a call means. k_state_ix "
           "sends logical slot 0 to entry n while the EAGLE view is active. "
           "k_storage_ref carries offset and entry together, so a view change cannot "
           "redirect a deferred conversion.")
    return figure(fid, W, H, "Slot to state-entry and storage-offset mapping", "".join(o),
                  cap)


def d3():
    fid = "d3"
    W, H = WD, 436
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "rows": C["rows"]})]
    o.append(text(10, 20, "note_k_row_saved(slot 5, offset 31): the 16th row of block 1",
                  11, weight=600))
    o.append(text(10, 44, "before", 9.5, fill=C["muted"]))
    b1, _ = bit_row(60, 34, "1" * 15 + "0", 10, 1, C["rows_fill"], C["rows"], group=0)
    o.append(b1)
    o.append(text(240, 44, "offsets 16..31; bit 31 clear", 9.5, fill=C["muted"]))
    o.append(arrow(fid, "rows", [(140, 50), (140, 66)], C["rows"], 1.4))
    o.append(text(150, 62, "saved.fetch_or(offset_bit(31), acq_rel)  [only when the bit was clear]",
                  9.5, mono=True))
    o.append(text(10, 84, "after", 9.5, fill=C["muted"]))
    b2, _ = bit_row(60, 74, "1" * 16, 10, 1, C["rows_fill"], C["rows"], group=0)
    o.append(b2)
    o.append(rect(10, 98, 300, 44, C["soft"], C["line"], 1, 4))
    o.append(lines(18, 114, ["(after & k_block_bits(1)) == k_block_bits(1)   yes",
                             "k_vnni_blocks_[5] & block_bit(1) == 0            yes"],
                   9.5, 14, mono=True))
    o.append(arrow(fid, "pend", [(312, 120), (332, 120)], C["pend"], 1.6))
    o.append(label_box(336, 100, 154, 40, "return true", ["block 1 is complete, waits"],
                       C["pend_fill"], C["pend"], 10.5, True, 4, "5 3"))
    o.append(arrow(fid, "pend", [(413, 142), (413, 158)], C["pend"], 1.4))
    o.append(rect(200, 160, 290, 48, "#fff", C["pend"], 1.2, 4))
    o.append(lines(208, 173, ["caller: save_k's row-recording loop (main thread)",
                              "pending_k_blocks_.push_back(",
                              "    {&page 7, k_storage_of(slot 5), block 1})"],
                   9.5, 12, mono=True))
    o.append(block_cell(10, 152, 180, 44, "pend", "block 1: complete, waits", 10))
    # other outcomes
    o.append(line(10, 212, 490, 212, C["line"]))
    o.append(text(10, 230, "other outcomes", 11, weight=600))
    rows = [("row-major slot (head_size != 128)", "false; no bits are kept"),
            ("a row of a complete, waiting block saved again", "true again (the conversion is idempotent)"),
            ("a row of a converted block (block bit set)", "false (set_k_row wrote the VNNI column)"),
            ("a row of a block with other rows missing", "false (bit set, block not complete)")]
    y = 246
    for a, b in rows:
        o.append(text(10, y, a, 9.5))
        o.append(arrow(fid, "ink", [(262, y - 4), (276, y - 4)], C["ink"], 1))
        o.append(text(280, y, b, 9.5, mono=True))
        y += 16
    # whole-block save
    o.append(line(10, 318, 490, 318, C["line"]))
    o.append(text(10, 336, "note_k_block_saved(slot, c): after the last KV head of a whole-block save",
                  11, weight=600))
    o.append(text(10, 358, "rows", 9.5, mono=True, fill=C["rows"]))
    b3, _ = bit_row(60, 348, "1" * 16, 10, 1, C["rows_fill"], C["rows"], group=0)
    o.append(b3)
    o.append(text(240, 358, "|= k_block_bits(c)  [acq_rel]", 9.5, mono=True))
    o.append(text(10, 382, "block", 9.5, mono=True, fill=C["blk"]))
    o.append(rect(60, 372, 10, 10, C["blk_fill"], C["blk"], 1, 1))
    o.append(text(80, 382, "|= block_bit(c)  [release]", 9.5, mono=True))
    o.append(arrow(fid, "ink", [(290, 380), (310, 380)], C["ink"], 1.2))
    o.append(block_cell(316, 366, 174, 30, "vnni", "converted at once", 10))
    o.append(lines(10, 408, ["any thread of a shared window may do this (fetch_or); readers see",
                             "the block bit only after every head holds the layout"], 9, 12,
                   fill=C["muted"]))
    cap = ("D3. The two writers of the bits (B4's transitions into 'complete, waits' and "
           "into 'converted'). The return value of note_k_row_saved is what makes the "
           "main thread queue a block.")
    return figure(fid, W, H, "Recording saved rows and whole-block saves", "".join(o), cap)


def d4():
    fid = "d4"
    W, H = WD, 490
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "gone": C["gone"]})]
    o.append(label_box(10, 10, 480, 36, "k_block_to_vnni(slot, c)  =  k_block_to_vnni_at(k_storage_of(slot), c)",
                       [], "#fff", C["ink"], 10.5))
    o.append(arrow(fid, "ink", [(250, 48), (250, 62)], C["ink"], 1.4))
    o.append(rect(10, 64, 320, 44, C["soft"], C["ink"], 1.2, 4))
    o.append(lines(18, 82, ["k_rows_saved_[ix] holds all 16 bits of block c",
                            "and k_vnni_blocks_[ix] bit c is clear?"], 10, 14))
    o.append(arrow(fid, "gone", [(332, 86), (352, 86)], C["gone"], 1.4))
    o.append(label_box(354, 58, 136, 56, "no: return false", ["nothing to do; a repeat", "call is harmless"],
                       "#fff", C["gone"], 10, False, 4))
    o.append(text(258, 124, "yes", 10, fill=C["muted"]))
    o.append(arrow(fid, "ink", [(250, 110), (250, 128)], C["ink"], 1.4))
    o.append(rect(10, 130, 480, 40, "#fff", C["ink"], 1.2, 4))
    o.append(lines(18, 146, ["k_with_storage_geometry(storage.offset): the slot's geometry, or the",
                             "primary one for the EAGLE storage; layout_on<head_size> false -> no change"],
                   10, 14))
    o.append(arrow(fid, "ink", [(250, 172), (250, 188)], C["ink"], 1.4))
    o.append(rect(10, 190, 480, 176, "#fff", C["vnni"], 1.4, 4))
    o.append(text(18, 208, "for kv_head = 0 .. n_kv_heads - 1:", 10.5, mono=True, weight=600))
    o.append(text(18, 224, "k_vnni::block_to_vnni(plane(storage.offset, kv_head), c)", 10, mono=True))
    # stack of planes (before), front plane = the last KV head
    o.append(text(30, 244, "before: block 1 complete, waits (in every plane)", 9, fill=C["muted"]))
    for h in range(6):
        px, py = 30 + h * 8, 250 + h * 8
        o.append(rect(px, py, 180, 40, "#fff", C["line"], 1, 3))
    px, py = 30 + 5 * 8, 250 + 5 * 8
    for c, st in enumerate(["vnni", "pend", "rm", "empty"]):
        o.append(block_cell(px + 6 + c * 42, py + 8, 38, 24, st, f"{c}", 9))
    o.append(text(30, 344, "planes of KV heads 0 .. n-1 (front: the last head)", 9, fill=C["muted"]))
    o.append(arrow(fid, "vnni", [(258, 310), (294, 310)], C["vnni"], 1.6))
    o.append(text(390, 284, "after: block 1 VNNI in every plane", 9, "middle", fill=C["muted"]))
    o.append(rect(300, 290, 180, 40, "#fff", C["line"], 1, 3))
    for c, st in enumerate(["vnni", "vnni", "rm", "empty"]):
        o.append(block_cell(306 + c * 42, 298, 38, 24, st, f"{c}", 9))
    o.append(lines(300, 344, ["per plane: 16 rows to the stack, then",
                              "store_block fills the 4 panels (B2)"], 9, 11))
    o.append(arrow(fid, "ink", [(250, 368), (250, 384)], C["ink"], 1.4))
    o.append(rect(10, 386, 480, 40, C["blk_fill"], C["blk"], 1.2, 4))
    o.append(lines(18, 402, ["k_vnni_blocks_[ix].fetch_or(block_bit(c), release); return true",
                             "one bit per slot covers every KV head, so it is set after the last head"],
                   10, 14, mono=False))
    o.append(lines(10, 446, ["main thread only, at the forward end (B5): no reader of the block runs.",
                             "Callers: convert_pending_k_blocks in model.hpp, and tests.",
                             "copy_storage_slot (C8) calls the k_vnni.hpp kernel directly instead."],
                   9.5, 13, fill=C["muted"]))
    cap = ("D4. The 'complete, waits' to 'converted' transition of B4. The check at the "
           "top makes the conversion idempotent; the bit is published only after every "
           "KV head's plane holds the VNNI form.")
    return figure(fid, W, H, "In-place conversion of one block", "".join(o), cap)


def d5():
    fid = "d5"
    W, H = WD, 350
    o = [marker_defs(fid, {"ink": C["ink"]})]
    x0, x1, x2 = 10, 140, 315
    w1 = w2 = 175
    o.append(rect(x1, 10, w1, 30, C["vnni_fill"], C["vnni"], 1.2, 4))
    o.append(text(x1 + w1 / 2, 29, "block bit set: VNNI", 10.5, "middle", weight=600))
    o.append(rect(x2, 10, w2, 30, C["rm_fill"], C["rm"], 1.2, 4))
    o.append(text(x2 + w2 / 2, 29, "block bit clear: row-major", 10.5, "middle", weight=600))
    rows = [("set_k_row", "changed",
             ["scatter_row: 4 bytes into", "each of 64 lines"],
             ["memcpy 256 B to row_ptr:", "4 whole lines"]),
            ("get_k_row", "changed",
             ["gather_row: 64 lines", "into the caller's row"],
             ["memcpy 256 B from row_ptr:", "4 lines"]),
            ("k_row_if_row_major", "new",
             ["nullptr: the caller falls", "back to get_k_row"],
             ["pointer into the block:", "no copy at all"])]
    y = 48
    for name, tag, a, b in rows:
        o.append(rect(x0, y, 124, 56, C["soft"], C["line"], 1, 4))
        o.append(text(x0 + 8, y + 24, name, 10.5, mono=True, weight=600))
        o.append(text(x0 + 8, y + 42, tag, 9.5, fill=C["new"] if tag == "new" else C["muted"]))
        o.append(rect(x1, y, w1, 56, "#fff", C["vnni"], 1, 4))
        o.append(lines(x1 + 8, y + 24, a, 10, 14))
        o.append(rect(x2, y, w2, 56, "#fff", C["rm"], 1, 4))
        o.append(lines(x2 + 8, y + 24, b, 10, 14))
        y += 64
    o.append(lines(10, y + 14, ["the branch reads k_block_is_vnni(k_state_ix(slot), i_page) once per call",
                                "head_size != 128 (row-major slot): kv_block.k_at(i_page) memcpy as before;",
                                "k_row_if_row_major is not compiled for such a slot (requires clause)"],
                   9.5, 13))
    o.append(line(10, y + 60, 490, y + 60, C["line"]))
    o.append(lines(10, y + 78, ["callers: set_k_row <- model.hpp store_k_block, runs shorter than 16 tokens (C6)",
                                "get_k_row, k_row_if_row_major <- full.hpp k_head_fn (FPGA staging), tests",
                                "the row's saved bit is NOT set here: that is note_k_row_saved (C3)"],
                   9.5, 13))
    cap = ("D5. The row accessors of B3 rows 1 and 6 now branch on the block bit. The "
           "right column is the new path: 4 lines per token instead of 64, and no copy "
           "for the staging read.")
    return figure(fid, W, H, "Row accessors follow the block's layout", "".join(o), cap)


def d6():
    fid = "d6"
    W, H = WD, 330
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    for col, (title, sub) in enumerate([("before: base 30c4ac82cb", "store_k_block in model.hpp"),
                                        ("after: head bb32a80774", "store_k_block in model.hpp")]):
        x = 10 + col * 250
        o.append(text(x, 20, title, 11, weight=600))
        o.append(text(x, 34, sub, 9.5, fill=C["muted"]))
        o.append(label_box(x, 44, 230, 36, "a run of n tokens in block c", [], C["soft"],
                           C["ink"], 10.5, False, 4))
        o.append(arrow(fid, "ink", [(x + 40, 82), (x + 40, 98)], C["ink"], 1.2))
        o.append(arrow(fid, "ink", [(x + 150, 82), (x + 150, 98)], C["ink"], 1.2))
        if col == 0:
            o.append(text(x + 48, 94, "n == 1", 9.5, "start", True))
            o.append(text(x + 158, 94, "n >= 2", 9.5, "start", True))
            o.append(rect(x, 100, 108, 70, "#fff", C["vnni"], 1.2, 4))
            o.append(lines(x + 6, 116, ["set_k_row", "= scatter_row,", "64 lines per", "token"],
                           9.5, 13, mono=True))
            o.append(rect(x + 116, 100, 114, 70, "#fff", C["vnni"], 1.2, 4))
            o.append(lines(x + 122, 116, ["set_k_block(c,", "present, rows):", "a PARTIAL block",
                                          "allowed (mask)"], 9.5, 13, mono=True))
            o.append(lines(x, 196, ["every K byte of a VNNI slot was written",
                                    "in the VNNI layout, however short the run;",
                                    "decode paid 64 lines per token (issue #4500)"],
                           9.5, 13, fill=C["muted"]))
        else:
            o.append(text(x + 48, 94, "n < 16", 9.5, "start", True))
            o.append(text(x + 158, 94, "n == 16", 9.5, "start", True))
            o.append(rect(x, 100, 108, 70, "#fff", C["rm"], 1.2, 4))
            o.append(lines(x + 6, 116, ["set_k_row per", "row: memcpy to", "the row-major",
                                        "form (C5)"], 9.5, 13, mono=True))
            o.append(rect(x + 116, 100, 114, 70, "#fff", C["vnni"], 1.2, 4))
            o.append(lines(x + 122, 116, ["assert present ==", "FULL_BLOCK_0XFFFF;",
                                          "set_k_block(c, rows);", "note_k_block_saved"],
                           9.5, 13, mono=True))
            o.append(lines(x, 196, ["set_k_block lost its `present` parameter:",
                                    "it always passes FULL_BLOCK_0XFFFF to",
                                    "k_vnni::store_block. Row bits of short",
                                    "runs are set later by save_k's",
                                    "row-recording loop (C3)"],
                           9.5, 12, fill=C["muted"]))
    o.append(line(10, 256, 490, 256, C["line"]))
    o.append(lines(10, 274, ["kv_cache.hpp side of this change: the signature and the comment of",
                             "set_k_block (B3 row 2). The decision itself lives in model.hpp and is",
                             "shown here because it explains why the mask could go."],
                   9.5, 13))
    cap = ("D6. Before and after for the whole-block save. Partial blocks no longer go "
           "through set_k_block; they take set_k_row into the row-major form.")
    return figure(fid, W, H, "set_k_block: whole blocks only", "".join(o), cap)


def d7():
    fid = "d7"
    W, H = WD, 470
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "gone": C["gone"]})]
    o.append(text(10, 20, "page 7 later: all 64 rows saved and converted; offset 37 "
                  "gets a new token", 10.5, weight=600))
    o.append(text(10, 44, "before", 9.5, fill=C["muted"]))
    body, _ = bit_row(60, 34, "1" * 64, 5, 1, C["rows_fill"], C["rows"], group=16, group_gap=8)
    o.append(body)
    for c in range(4):
        gx = 60 + c * 103
        o.append(rect(gx, 44, 8, 8, C["blk_fill"], C["blk"], 1, 1))
        o.append(block_cell(gx, 56, 95, 22, "vnni", f"block {c}", 9))
    # offset 37 marker
    ox = 60 + 2 * 103 + 5 * 6
    o.append(arrow(fid, "gone", [(ox + 2, 100), (ox + 2, 82)], C["gone"], 1.4))
    o.append(text(ox + 8, 104, "offset 37 = block 2, row 5", 9.5, mono=True, fill=C["gone"]))
    # masks
    o.append(rect(10, 116, 480, 70, C["soft"], C["line"], 1, 4))
    o.append(lines(18, 132, ["rows_below   = offset_bit(37) - 1      = bits 0..36 kept, 37..63 dropped",
                             "blocks_below = block_bit(2) - 1        = blocks 0, 1 kept, 2, 3 dropped",
                             "block_keeps_rows = 37 % 16 != 0        = true (rows 32..36 stay live)",
                             "for every state entry ix: logical slots, then E if has_eagle_storage()"],
                   9.5, 14, mono=True))
    # steps
    steps = [("1", "nothing at or above 37 in this entry? (converted & ~blocks_below) == 0 and",
              "(rows & ~rows_below) == 0 -> continue (two loads, no locked RMW: decode append)"),
             ("2", "block 2 converted, keeps rows, k_storage_readable(offset) -> for every KV head:",
              "k_vnni::block_to_rows(plane, 2): rows 32..36 become readable row-major again"),
             ("3", "blocks.fetch_and(blocks_below, release); rows.fetch_and(rows_below, release):",
              "block 3's bits go too; its bytes (and block 2's rows 37..47) are left alone")]
    y = 200
    for n, a, b in steps:
        o.append(rect(10, y, 20, 30, "#fff", C["ink"], 1, 10))
        o.append(text(20, y + 20, n, 11, "middle", weight=700))
        o.append(lines(38, y + 12, [a, b], 9.5, 13))
        y += 40
    # after
    o.append(text(10, 338, "after", 9.5, fill=C["muted"]))
    body, _ = bit_row(60, 328, "1" * 37 + "0" * 27, 5, 1, C["rows_fill"], C["rows"], group=16,
                      group_gap=8)
    o.append(body)
    for c, st in enumerate(["vnni", "vnni", "rm", "empty"]):
        gx = 60 + c * 103
        on = c < 2
        o.append(rect(gx, 338, 8, 8, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(block_cell(gx, 350, 95, 22, st, f"block {c}", 9))
    o.append(text(60 + 2 * 103 + 47, 386, "rows 32..36 row-major", 8.5, "middle", fill=C["muted"]))
    o.append(text(60 + 3 * 103 + 47, 386, "bits dropped, bytes left", 8.5, "middle", fill=C["muted"]))
    o.append(line(10, 398, 490, 398, C["line"]))
    o.append(lines(10, 416, ["k_storage_readable(offset) = no reclaimable KV restore in flight and the slot's",
                             "arena is allocated; when false, only the bits change (the bytes are not valid).",
                             "Runs with the token tree locked, between forward passes: no reader meanwhile.",
                             "Caller: clear_kv_complete_at, which also zeroes kv_saves_ for the offset."],
                   9.5, 13))
    cap = ("D7. The clear path of B4 (the 'converted' to 'partial' arrow and the drop "
           "note) for one offset. Step 2 is the only byte traffic; steps 1 and 3 are "
           "bit arithmetic on the two arrays of D1.")
    return figure(fid, W, H, "k_forget_row: a new token takes offset 37", "".join(o), cap)


def d8():
    fid = "d8"
    W, H = WD, 520
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "rm": C["rm"], "vnni": C["vnni"]})]
    px = 440 / 64  # px per offset

    def strip(y, label, states, saved_bits, blocks_bits, words):
        o.append(lines(10, y + 10, label.split(" "), 9.5, 12, mono=True))
        body, _ = bit_row(60, y - 2, saved_bits, 5, 1, C["rows_fill"], C["rows"], group=16,
                          group_gap=8)
        o.append(body)
        for c in range(4):
            gx = 60 + c * 103
            on = blocks_bits[c] == "1"
            o.append(rect(gx, y + 8, 8, 8, C["blk_fill"] if on else C["empty_fill"],
                          C["blk"] if on else C["empty"], 1, 1))
            o.append(block_cell(gx, y + 20, 95, 22, states[c], f"block {c}", 9))
            if words[c]:
                o.append(text(gx + 47, y + 54, words[c], 8, "middle", fill=C["muted"]))

    def bracket(y, b, e, color, label):
        x1 = 60 + (b // 16) * 103 + (b % 16) * 6
        x2 = 60 + ((e - 1) // 16) * 103 + ((e - 1) % 16) * 6 + 5
        o.append(line(x1, y, x2, y, color, 1.6))
        o.append(line(x1, y, x1, y + 5, color, 1.6))
        o.append(line(x2, y, x2, y + 5, color, 1.6))
        o.append(text((x1 + x2) / 2, y - 4, label, 9, "middle", True, fill=color))

    o.append(text(10, 18, "copy_storage_slot(storage, src, src_begin 20, dst_begin 8, count 30)",
                  10.5, weight=600))
    strip(50, "src", ["vnni", "vnni", "rm", "empty"], "1" * 41 + "0" * 23, "1100",
          ["", "", "rows 32..40", ""])
    bracket(44, 20, 50, C["pend"], "source range [20, 50)")
    strip(130, "dst before", ["vnni", "rm", "empty", "empty"], "1" * 21 + "0" * 43, "1000",
          ["", "rows 16..20", "", ""])
    bracket(124, 8, 38, C["pend"], "destination range [8, 38)")
    steps = [("1", "destination blocks the range touches: c = 0, 1, 2. Block 0 is converted ->",
              "k_vnni::block_to_rows(dst, 0); new_blocks &= ~block_bit(0)"),
             ("2", "row by row, i = 0..29: source offset 20+i in a converted block (20..31) ->",
              "gather_row into row_ptr(dst, 8+i); else memcpy from row_ptr(src) (32..49, bits or not)"),
             ("3", "new_saved = (dst_saved & ~range) | (((src_saved >> 20) << 8) & range) = bits 0..28;",
              "block 0 has its 16 bits -> block_to_vnni(dst, 0), bit set; blocks 1, 2 stay row-major"),
             ("4", "after the last KV head: k_rows_saved_[ix].store(new_saved), k_vnni_blocks_[ix]",
              ".store(new_blocks), both release. Bits computed once per slot, not per head")]
    y = 204
    for n, a, b in steps:
        o.append(rect(10, y, 20, 30, "#fff", C["ink"], 1, 10))
        o.append(text(20, y + 20, n, 11, "middle", weight=700))
        o.append(lines(38, y + 12, [a, b], 9.3, 13))
        y += 40
    strip(380, "dst after", ["vnni", "rm", "empty", "empty"], "1" * 29 + "0" * 35, "1000",
          ["re-converted", "rows 16..28", "rows copied, bits clear", "untouched"])
    o.append(line(10, 452, 490, 452, C["line"]))
    o.append(lines(10, 470, ["whole page (src_begin = dst_begin = 0, count = 64): one memcpy of the plane;",
                             "new_blocks = src_blocks, new_saved = src_saved: the layout travels with the bytes.",
                             "copy_from calls this per active slot with {offset(slot), slot} and once more",
                             "with {eagle_storage_offset(), n} when the book has EAGLE storage (C2)."],
                   9.3, 13))
    cap = ("D8. A partial page copy with the bits of D1. Every row crosses through the "
           "row-major form (B2, left side), so a source row from a converted block is "
           "gathered and one from a row-major block is copied; destination blocks are "
           "un-converted first and re-converted when complete.")
    return figure(fid, W, H, "copy_storage_slot: rows and bits travel together", "".join(o), cap)
