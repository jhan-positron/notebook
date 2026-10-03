"""Base diagrams B1-B5 of the PR 4737 kv_cache.hpp page."""
from svg_helpers import (C, arrow, bit_row, block_cell, figure, label_box,
                         legend_chip, line, lines, marker_defs, rect, text)

# The one worked example used by every diagram of the page:
# page 7, storage slot 5 (layer 5), after the K rows of offsets 0..40 were
# saved. Block 0 is converted, block 1 is complete and waits, block 2 holds
# 9 row-major rows (32..40), block 3 is empty.
ROWS_EXAMPLE = "1" * 16 + "1" * 16 + "1" * 9 + "0" * 7 + "0" * 16
BLOCKS_EXAMPLE = "1000"  # bit 0 at the left
BLOCK_STATES_EXAMPLE = ["vnni", "pend", "rm", "empty"]
BLOCK_WORDS_EXAMPLE = ["VNNI (converted)", "complete, waits", "9 rows, row-major",
                       "no row saved"]


def legend_row(x, y):
    o = []
    cx = x
    for st, lab in [("vnni", "converted block: VNNI layout"),
                    ("pend", "complete, not converted"),
                    ("rm", "row-major rows")]:
        o.append(legend_chip(cx, y, st, lab))
        cx += 32 + 6.2 * len(lab) + 18
    cx = x
    for st, lab in [("empty", "no row saved"),
                    ("hw", "row-major, no bits (hardware attention)")]:
        o.append(legend_chip(cx, y + 24, st, lab))
        cx += 32 + 6.2 * len(lab) + 18
    return "".join(o)


def bits_legend(x, y):
    o = [rect(x, y + 2, 10, 10, C["rows_fill"], C["rows"], 1, 1),
         text(x + 15, y + 11, "k_rows_saved_ bit set", 11),
         rect(x + 160, y + 2, 10, 10, C["blk_fill"], C["blk"], 1, 1),
         text(x + 175, y + 11, "k_vnni_blocks_ bit set", 11),
         rect(x + 325, y + 2, 10, 10, C["empty_fill"], C["empty"], 1, 1),
         text(x + 340, y + 11, "bit clear", 11)]
    return "".join(o)


def b1():
    fid = "b1"
    W, H = 1000, 684
    o = [marker_defs(fid, {"ink": C["ink"], "blk": C["blk"], "rows": C["rows"]})]
    # ---- column 1: book ----------------------------------------------------
    o.append(rect(20, 30, 280, 344, C["soft"], C["ink"], 1.2, 6))
    o.append(text(160, 52, "book (one KV memory allocation)", 13, "middle", True, weight=700))
    o.append(lines(160, 68, ["K and V of one run of consecutive tokens (up to",
                             "n_pages x 64) for all layers. The tree owns many books."],
                   9.5, 12, "middle", fill=C["muted"]))
    o.append(text(32, 104, "storage slots, one per layer:", 11))
    xs = 32
    for lab in ["slot 0", "slot 1", "...", "slot n-1"]:
        o.append(rect(xs, 112, 50, 24, "#fff", C["ink"], 1, 3))
        o.append(text(xs + 25, 128, lab, 10, "middle", True))
        xs += 54
    o.append(rect(xs, 112, 46, 24, C["eagle_fill"], C["eagle"], 1.4, 3))
    o.append(text(xs + 23, 128, "EAGLE", 10, "middle", True))
    o.append(lines(32, 156, ["EAGLE: an extra physical slot at offset",
                             "n_slots (only with EAGLE support)"], 11, 14,
                   fill=C["muted"]))
    o.append(text(32, 198, "pages, 64 token offsets each:", 11))
    py = 206
    for lab, hi in [("page 0", False), ("...", False), ("page 7", True),
                    ("page n_pages-1", False)]:
        o.append(rect(32, py, 130, 22, "#FFF4D6" if hi else "#fff", C["ink"],
                      1.6 if hi else 1, 3))
        o.append(text(97, py + 15, lab, 10, "middle", True,
                      weight=700 if hi else None))
        py += 26
    o.append(lines(32, 326, ["kv_block(slot, kv_head, pg): the K and V",
                             "planes of one slot, KV head and page",
                             "(book.kv_block, 16 KiB + 16 KiB)"], 11, 14,
                   fill=C["muted"]))
    # arrow page 7 -> page struct
    o.append(arrow(fid, "ink", [(162, 269), (330, 269)], C["ink"]))
    o.append(text(246, 262, "the page struct", 10, "middle", fill=C["muted"]))
    # ---- column 2: page ----------------------------------------------------
    o.append(rect(330, 30, 310, 344, "#fff", C["ink"], 1.2, 6))
    o.append(text(485, 52, "page 7 (64 token offsets)", 13, "middle", True,
                  weight=700))
    o.append(rect(342, 64, 286, 40, C["soft"], C["line"], 1, 4))
    o.append(text(352, 80, "kv_saves_[64][n_slots]", 11, mono=True))
    o.append(text(352, 95, "K/V completion counters per offset (unchanged)", 10,
                  fill=C["muted"]))
    # k_rows_saved_ and k_vnni_blocks_: one cell per state entry (storage slot)
    for row, (name, col, fill, yl) in enumerate([
            ("k_rows_saved_[n_slots + 1]", C["rows"], C["rows_fill"], 126),
            ("k_vnni_blocks_[n_slots + 1]", C["blk"], C["blk_fill"], 206)]):
        o.append(text(342, yl, name, 11, mono=True, fill=col, weight=700))
        o.append(text(628, yl, "new", 10, "end", fill=C["new"], weight=700))
        cy = yl + 8
        cx = 342
        for lab in ["0", "1", "5", "...", "n-1"]:
            hi = lab == "5"
            o.append(rect(cx, cy, 46, 28, fill if hi else "#fff", col, 1.6 if hi else 1, 3))
            o.append(text(cx + 23, cy + 18, lab, 10, "middle", True))
            cx += 50
        o.append(rect(cx, cy, 36, 28, C["eagle_fill"], C["eagle"], 1.4, 3))
        o.append(text(cx + 18, cy + 18, "E", 10, "middle", True))
    o.append(lines(342, 284, ["one cell = one entry = one storage slot (layer)",
                              "k_rows_saved_: 64-bit word, bit o = row o is saved",
                              "k_vnni_blocks_: one byte, bit c = block c is VNNI",
                              "entry E = n_slots: the EAGLE storage (change C2)",
                              "copied with the page by the move constructor (C1)"],
                   10, 14, fill=C["muted"]))
    # arrows: from entry 5 to the K planes of slot 5 in page 7 (one per KV head)
    o.append(arrow(fid, "rows", [(465, 164), (465, 186), (694, 186)], C["rows"], 1.6))
    o.append(text(472, 181, "entry 5 -> the K planes of slot 5", 9, fill=C["rows"]))
    o.append(arrow(fid, "blk", [(465, 244), (465, 266), (694, 266)], C["blk"], 1.6))
    o.append(text(472, 261, "bit c -> layout of block c, all heads", 8.5, fill=C["blk"]))
    # ---- column 3: the kv_blocks of slot 5 in page 7, one per KV head ----------
    o.append(rect(670, 30, 310, 344, "#fff", C["ink"], 1.2, 6))
    o.append(text(825, 52, "kv_block(slot 5, kv_head h, page 7)", 12, "middle",
                  True, weight=700))
    o.append(lines(825, 66, ["one per KV head h = 0 .. n_kv_heads-1 (front: h = 0)",
                             "entry 5 of page 7 describes block c in every one"],
                   9.5, 12, "middle", fill=C["muted"]))
    fx, fy, fw, fh = 694, 100, 256, 228
    for k in (3, 2, 1):
        o.append(rect(fx + 6 * k, fy + 6 * k, fw, fh, "#fff", C["line"], 1, 5))
    o.append(rect(fx, fy, fw, fh, "#fff", C["ink"], 1.2, 5))
    o.append(text(fx + 8, fy + 16, "kv_head 0", 10, mono=True, weight=600))
    o.append(text(fx + 8, fy + 32, "K plane: 64 tokens x 128 dims = 16 KiB", 9.5))
    by = fy + 40
    for c in range(4):
        o.append(block_cell(fx + 8, by, 150, 32, BLOCK_STATES_EXAMPLE[c],
                            f"block {c}: {16*c}..{16*c+15}", 9.5))
        o.append(text(fx + 166, by + 20, BLOCK_WORDS_EXAMPLE[c], 9))
        by += 36
    o.append(rect(fx + 8, by + 2, fw - 16, 22, C["soft"], C["line"], 1, 4))
    o.append(text(fx + fw / 2, by + 17, "V plane: 16 KiB (unchanged by this PR)", 9.5,
                  "middle"))
    o.append(lines(682, 352, ["the n_kv_heads K planes of slot 5 in page 7 share one state",
                              "entry (5): the bits are per slot, not per KV head"], 9.5, 12,
                   fill=C["muted"]))
    # ---- bottom: the worked example ----------------------------------------
    o.append(line(20, 398, 980, 398, C["line"]))
    o.append(text(20, 418, "Worked example used on this page: page 7, state entry 5 "
                  "(slot 5) after the K rows of offsets 0..40 were saved. Bit 0 is "
                  "drawn at the left.", 12, weight=600))
    o.append(text(20, 454, "k_rows_saved_[5]", 11, mono=True, fill=C["rows"]))
    body, _ = bit_row(190, 444, ROWS_EXAMPLE, 9, 1, C["rows_fill"], C["rows"],
                      group=16, group_gap=8)
    o.append(body)
    o.append(text(20, 484, "k_vnni_blocks_[5]", 11, mono=True, fill=C["blk"]))
    for c in range(4):
        gx = 190 + c * 167
        on = BLOCKS_EXAMPLE[c] == "1"
        o.append(rect(gx, 472, 12, 12, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(text(gx + 18, 482, f"bit {c}", 10, fill=C["muted"]))
    o.append(text(20, 526, "block layout", 11, fill=C["muted"]))
    for c in range(4):
        gx = 190 + c * 167
        o.append(block_cell(gx, 498, 159, 46, BLOCK_STATES_EXAMPLE[c],
                            f"block {c}", 11))
        o.append(text(gx + 79, 536, BLOCK_WORDS_EXAMPLE[c], 10, "middle",
                      fill=C["muted"]))
    for c in range(4):
        gx = 190 + c * 167
        o.append(text(gx, 562, f"offset {16*c}", 9, fill=C["muted"]))
        o.append(text(gx + 159, 562, f"{16*c+15}", 9, "end", fill=C["muted"]))
    o.append(text(20, 601, "legend", 11, fill=C["muted"]))
    o.append(legend_row(90, 589))
    o.append(bits_legend(90, 642))
    cap = ("B1, data model. A book is the unit of KV memory allocation: the K and V of one "
           "run of consecutive tokens, up to n_pages pages of 64, for all layers. The "
           "token tree owns many books. A book holds one storage slot per layer, an optional "
           "EAGLE slot, and pages of 64 token offsets. The page struct gains two "
           "arrays, one entry per storage slot plus one for the EAGLE storage: "
           "k_rows_saved_ (64 bits, one per offset) and k_vnni_blocks_ (4 bits, one "
           "per 16-token block). Bit c of k_vnni_blocks_ names the layout of block c "
           "of the slot's K plane in that page, for every KV head of the slot.")
    return figure(fid, W, H, "Data model of the K layout state", "".join(o), cap)


def b2():
    fid = "b2"
    W, H = 1000, 480
    o = [marker_defs(fid, {"pend": C["pend"], "rm": C["rm"], "ink": C["ink"]})]
    # ---- left: the plane as 16 panels --------------------------------------
    o.append(text(20, 24, "K plane of one (slot, KV head, page): 16 panels of 1 KiB",
                  12, weight=600))
    for c in range(4):
        o.append(text(70 + c * 82 + 39, 48, f"block c={c}", 10, "middle",
                      fill=C["muted"]))
    for s in range(4):
        o.append(text(64, 56 + s * 50 + 28, f"step s={s}", 10, "end",
                      fill=C["muted"]))
        for c in range(4):
            x, y = 70 + c * 82, 56 + s * 50
            hi = c == 2
            o.append(rect(x, y, 78, 46, C["rm_fill"] if hi else "#fff",
                          C["rm"] if hi else C["line"], 1.4 if hi else 1, 3))
            o.append(text(x + 39, y + 20, f"panel ({s},{c})", 10, "middle", True))
            o.append(text(x + 39, y + 36, f"#{4*s+c}", 10, "middle", True,
                          fill=C["muted"]))
    o.append(lines(20, 276, ["memory order: panel index 4 s + c,",
                             "byte offset 1 KiB x (4 s + c).",
                             "block 2 owns panels #2, #6, #10, #14:",
                             "four 1 KiB pieces, 4 KiB apart.",
                             "A block's two layouts use exactly these",
                             "four panels; no other block is touched."],
                   11, 15))
    # ---- middle: row-major form ---------------------------------------------
    mx, mw = 430, 220
    o.append(text(mx, 24, "Row-major form (block bit 2 clear)", 12, weight=600,
                  fill=C["rm"]))
    o.append(text(mx, 40, "block 2 = offsets 32..47", 10, fill=C["muted"]))
    for s in range(4):
        y = 56 + s * 80
        o.append(rect(mx, y, mw, 72, C["rm_fill"], C["rm"], 1.4, 3))
        o.append(text(mx + mw - 6, y + 11, f"panel ({s},2) #{4*s+2}", 9, "end",
                      True, fill=C["muted"]))
        for r in range(4):
            tok = 32 + 4 * s + r
            ry = y + 14 + r * 14
            o.append(rect(mx + 6, ry, mw - 12, 12, "#fff", C["rm"], 0.8, 2))
            o.append(text(mx + 12, ry + 9.5, f"offset {tok}: 128 bf16 = 256 B",
                          9, mono=True))
    o.append(lines(mx, 392, ["row_ptr(plane, token), t = token % 16:",
                             "panel (t / 4, c), row t % 4, i.e.",
                             "plane + ((t/4)*4 + c)*512 + (t%4)*128",
                             "(bf16 elements)"], 10, 13, mono=True))
    # ---- right: VNNI form ----------------------------------------------------
    rx, rw = 780, 200
    o.append(text(rx, 24, "VNNI form (block bit 2 set)", 12, weight=600,
                  fill=C["vnni"]))
    o.append(text(rx, 40, "the AMX B-operand layout", 10, fill=C["muted"]))
    for s in range(4):
        y = 56 + s * 80
        o.append(rect(rx, y, rw, 72, C["vnni_fill"], C["vnni"], 1.4, 3))
        o.append(text(rx + rw - 6, y + 11, f"panel ({s},2) #{4*s+2}", 9, "end",
                      True, fill=C["muted"]))
        for dp in range(16):
            ry = y + 14 + dp * 3.5
            o.append(rect(rx + 6, ry, 110, 2.6, C["vnni"], C["vnni"], 0.3, 0))
        o.append(lines(rx + 122, y + 26, ["16 rows x 64 B", f"dims {32*s}..{32*s+31}",
                                          "row dp = pair dp", "of tokens 32..47"],
                       8.5, 11, fill=C["ink"]))
    o.append(lines(rx, 392, ["plane[(((s*4 + c)*16 + dp)*16", "    + t)*2 + j]",
                             "= K[16 c + t][32 s + 2 dp + j]"], 10, 13, mono=True))
    # ---- arrows between the forms ------------------------------------------
    o.append(arrow(fid, "pend", [(mx + mw + 8, 170), (rx - 8, 170)], C["pend"], 1.6))
    o.append(text((mx + mw + rx) / 2, 162, "block_to_vnni", 10, "middle", True,
                  fill=C["pend"]))
    o.append(arrow(fid, "rm", [(rx - 8, 230), (mx + mw + 8, 230)], C["rm"], 1.6))
    o.append(text((mx + mw + rx) / 2, 246, "block_to_rows", 10, "middle", True,
                  fill=C["rm"]))
    o.append(lines((mx + mw + rx) / 2, 290, ["both in k_vnni.hpp,", "in place, 4 KiB",
                                             "via a stack copy"], 9, 12, "middle",
                   fill=C["muted"]))
    cap = ("B2, one block, two layouts in the same bytes. The K plane is 16 panels of "
           "1 KiB. Block c owns the four panels (s, c), s = 0..3. In the row-major "
           "form each panel holds four 256-byte token rows (row_ptr). In the VNNI "
           "form each panel holds the 16 dimension pairs of one 32-dimension step for "
           "the block's 16 tokens. block_to_vnni and block_to_rows (k_vnni.hpp) convert "
           "a block in place; the page's block bit records which form the block holds.")
    return figure(fid, W, H, "One 16-token block in its row-major and VNNI forms",
                  "".join(o), cap)


def b3():
    fid = "b3"
    W, H = 1000, 780
    o = [marker_defs(fid, {"ink": C["ink"]})]
    cols = [(20, 290), (360, 320), (740, 240)]
    heads = ["callers (other files)", "page / book API in kv_cache.hpp",
             "kernels in k_vnni.hpp"]
    for (x, w), h in zip(cols, heads):
        o.append(text(x + w / 2, 24, h, 12, "middle", weight=700))
    rows = [
        (["model.hpp save_k / store_k_block:", "a run shorter than 16 tokens (main)"],
         "set_k_row", "changed: follows the block bit",
         ["stores one token's K row in the layout its block holds"],
         ["scatter_row  |  row_ptr + memcpy"]),
        (["model.hpp store_k_block: a run of 16", "tokens (main, or a shared-window helper)"],
         "set_k_block + note_k_block_saved", "changed + new",
         ["set_k_block: 16 rows stored as one VNNI block",
          "note_k_block_saved: publishes the 16 row bits + block bit"],
         ["store_block"]),
        (["model.hpp save_k, row-recording loop (main,", "skipped for hardware-scored operations)"],
         "note_k_row_saved, k_storage_of", "new",
         ["note_k_row_saved: sets the row's bit, true = block complete",
          "k_storage_of: logical slot -> (storage offset, state entry)"],
         ["offset_bit, block_bit"]),
        (["model.hpp convert_pending_k_blocks", "(main, forward end)"],
         "k_block_to_vnni_at", "new",
         ["converts a complete block to VNNI in place (all KV heads),",
          "then sets its block bit"],
         ["block_to_vnni"]),
        (["self_attention.hpp software loop and", "dense gate k_layout_dense (workers)"],
         "k_vnni_blocks, k_vnni_plane", "new, unchanged",
         ["k_vnni_blocks: the 4 block bits of a slot (dense gate)",
          "k_vnni_plane: pointer to the 16 KiB K plane of a KV head"],
         ["row_ptr (dotter rows), qk_group"]),
        (["full.hpp k_head_fn: FPGA staging", "gof::populate (workers and main)"],
         "k_row_if_row_major, get_k_row", "new, changed",
         ["k_row_if_row_major: row pointer in place, nullptr if VNNI",
          "get_k_row: copies one row out (gather or memcpy by layout)"],
         ["row_ptr  |  gather_row"]),
        (["a new token takes a page offset", "(scheduler thread, tree lock)"],
         "clear_kv_complete_at -> k_forget_row", "changed -> new",
         ["drops the bits at and above a reassigned offset, after",
          "converting that offset's block back to row-major if needed"],
         ["block_to_rows"]),
        (["append / defrag page copy", "(scheduler thread, tree lock)"],
         "copy_from -> copy_storage_slot", "changed",
         ["copies a token range between pages, rows and bits together,",
          "via row-major rows (un-convert, copy, re-convert)"],
         ["block_to_rows, gather_row,", "row_ptr, block_to_vnni"]),
    ]
    y = 40
    RH = 66
    for caller, name, tag, desc, kern in rows:
        (x0, w0), (x1, w1), (x2, w2) = cols
        o.append(rect(x0, y, w0, RH, C["soft"], C["line"], 1, 4))
        o.append(lines(x0 + 8, y + 28, caller, 11, 15))
        o.append(rect(x1, y, w1, RH, "#fff", C["ink"], 1.2, 4))
        o.append(text(x1 + 8, y + 17, name, 11.5, mono=True, weight=600))
        o.append(lines(x1 + 8, y + 32, desc, 9.5, 12))
        o.append(text(x1 + 8, y + 59, tag, 9.5,
                      fill=C["new"] if tag.startswith("new") else C["muted"]))
        o.append(rect(x2, y, w2, RH, "#fff", C["line"], 1, 4))
        o.append(lines(x2 + 8, y + 37 if len(kern) == 1 else y + 30, kern, 10.5, 14,
                       mono=True))
        o.append(arrow(fid, "ink", [(x0 + w0 + 4, y + RH / 2), (x1 - 4, y + RH / 2)],
                       C["ink"]))
        o.append(arrow(fid, "ink", [(x1 + w1 + 4, y + RH / 2), (x2 - 4, y + RH / 2)],
                       C["ink"]))
        y += RH + 8
    # private helper band
    o.append(rect(360, y + 6, 320, 118, "#fff", C["new"], 1.4, 4, "5 3"))
    o.append(text(520, y + 24, "private helpers, new", 11, "middle", weight=700,
                  fill=C["new"]))
    o.append(lines(372, y + 42, ["k_state_ix: logical slot -> state entry (C2)",
                                 "k_block_bits: the 16-bit row mask of block c",
                                 "k_block_is_vnni: block bit of an offset's block",
                                 "k_with_storage_geometry: f with the slot's geometry",
                                 "k_storage_readable: bytes may be touched now",
                                 "book::eagle_view_active: the EAGLE view is on"],
                   9.5, 13, mono=True))
    o.append(lines(20, y + 30, ["used by the rows above:",
                                "which state entry (C2), which 16 bits (C1),",
                                "is the block converted (C1), which geometry",
                                "has the storage slot (C2), may its bytes be",
                                "touched now (C7)"], 11, 15, fill=C["muted"]))
    o.append(lines(740, y + 30, ["constants and bit helpers:",
                                 "BLOCK_TOKENS_16, PAGE_TOKENS_64,",
                                 "FULL_BLOCK_0XFFFF,",
                                 "BLOCKS_PER_PAGE_MASK_0XF,",
                                 "block_bit(c), offset_bit(o)"], 10.5, 15,
                   mono=True, fill=C["muted"]))
    cap = ("B3, function model. Each row is one call path: the caller in another file, "
           "the page (or book) function in kv_cache.hpp it calls, and the k_vnni.hpp "
           "kernel that touches the bytes. Each API cell names the function, says in one "
           "line what it does, and tags whether this PR adds or changes it. The dashed band "
           "lists the new private helpers that the rows share. Change ids (C1, C2, C7) refer "
           "to section 2. The row-recording loop of save_k is defined in the glossary.")
    return figure(fid, W, H, "Function model: callers, page API, kernels", "".join(o),
                  cap)


def b4():
    fid = "b4"
    W, H = 1000, 470
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "rm": C["rm"],
                           "hw": C["hw"], "vnni": C["vnni"]})]
    bw, bh, by = 190, 64, 130
    S = {"s0": 20, "s1": 270, "s2": 520, "s3": 790}
    o.append(block_cell(S["s0"], by, bw, bh, "empty"))
    o.append(lines(S["s0"] + bw / 2, by + 26, ["empty", "no row bit; bytes undefined"],
                   11, 15, "middle"))
    o.append(block_cell(S["s1"], by, bw, bh, "rm"))
    o.append(lines(S["s1"] + bw / 2, by + 26, ["partial, row-major",
                                               "1..15 row bits, block bit clear"],
                   11, 15, "middle"))
    o.append(block_cell(S["s2"], by, bw, bh, "pend"))
    o.append(lines(S["s2"] + bw / 2, by + 26, ["complete, waits",
                                               "16 row bits, block bit clear"],
                   11, 15, "middle"))
    o.append(block_cell(S["s3"], by, bw, bh, "vnni"))
    o.append(lines(S["s3"] + bw / 2, by + 26, ["converted: VNNI",
                                               "16 row bits, block bit set"],
                   11, 15, "middle"))
    # S0 -> S1
    o.append(arrow(fid, "rm", [(S["s0"] + bw, by + 32), (S["s1"] - 2, by + 32)],
                   C["rm"], 1.6))
    o.append(lines(215, 98, ["first row: set_k_row (memcpy)", "+ note_k_row_saved [main]"],
                   10, 12, "middle"))
    # S1 self loop, under the box, right half
    o.append(arrow(fid, "rm", [(S["s1"] + 170, by + bh), (S["s1"] + 170, by + bh + 14),
                               (S["s1"] + 100, by + bh + 14), (S["s1"] + 100, by + bh + 2)],
                   C["rm"], 1.4))
    o.append(text(S["s1"] + 135, by + bh + 28, "rows 2..15: the same path", 10, "middle"))
    # S1 -> S2
    o.append(arrow(fid, "pend", [(S["s1"] + bw, by + 32), (S["s2"] - 2, by + 32)],
                   C["pend"], 1.6))
    o.append(lines(490, 92, ["16th row bit lands: note_k_row_saved", "returns true; main pushes the block",
                             "onto pending_k_blocks_"], 10, 12, "middle"))
    # S2 -> S3
    o.append(arrow(fid, "vnni", [(S["s2"] + bw, by + 32), (S["s3"] - 2, by + 32)],
                   C["vnni"], 1.6))
    o.append(lines(750, 92, ["forward end (main):", "convert_pending_k_blocks ->",
                             "k_block_to_vnni_at"], 10, 12, "middle"))
    # S0 -> S3 arc (whole-block save)
    o.append(arrow(fid, "vnni", [(S["s0"] + 60, by), (S["s0"] + 60, 40), (S["s3"] + 95, 40),
                                 (S["s3"] + 95, by - 2)], C["vnni"], 1.6))
    o.append(text(500, 34, "whole-block save of a run of 16 tokens: set_k_block + "
                  "note_k_block_saved [main or shared-window helper]; no wait",
                  10.5, "middle", fill=C["vnni"]))
    # S3 self loop (row saved again), under the box, right half
    o.append(arrow(fid, "vnni", [(S["s3"] + bw - 20, by + bh), (S["s3"] + bw - 20, by + bh + 14),
                                 (S["s3"] + 90, by + bh + 14), (S["s3"] + 90, by + bh + 2)],
                   C["vnni"], 1.4))
    o.append(lines(S["s3"] + 130, by + bh + 28, ["a row saved again:", "set_k_row scatters into",
                                                 "the VNNI column"], 9.5, 11, "middle"))
    # S3 -> S1 (clear inside the block): leaves S3 at its left part, enters S1 at its left part
    o.append(arrow(fid, "rm", [(S["s3"] + 30, by + bh), (S["s3"] + 30, 262),
                               (S["s1"] + 40, 262), (S["s1"] + 40, by + bh + 2)],
                   C["rm"], 1.6))
    o.append(lines(565, 278, ["clear_kv_complete_at at an offset inside the block "
                              "[scheduler thread, tree lock]: block_to_rows for every KV head,",
                              "then the bits at and above the offset are dropped; the "
                              "rows below stay readable"], 10, 12, "middle"))
    # S0 -> S4 (hardware attention)
    s4x, s4y, s4w = 270, 340, 300
    o.append(block_cell(s4x, s4y, s4w, bh, "hw"))
    o.append(lines(s4x + s4w / 2, s4y + 26, ["row-major, unrecorded",
                                             "hardware-scored operation: no bit, ever"],
                   11, 15, "middle"))
    o.append(arrow(fid, "hw", [(S["s0"] + 30, by + bh), (S["s0"] + 30, s4y + 32),
                               (s4x - 2, s4y + 32)], C["hw"], 1.6))
    o.append(lines(S["s0"] + 42, 318, ["cached_operation_uses_hw:", "set_k_row stores the row,",
                                       "save_k records no bit and", "queues nothing"],
                   10, 12))
    o.append(arrow(fid, "hw", [(s4x + s4w - 40, s4y + bh), (s4x + s4w - 40, s4y + bh + 14),
                               (s4x + 40, s4y + bh + 14), (s4x + 40, s4y + bh + 2)],
                   C["hw"], 1.4))
    o.append(lines(600, s4y + 20, ["stays row-major: every reader takes the layout from",
                                   "the clear block bit; the FPGA staging reads the row in",
                                   "place; copy_from copies the rows and converts nothing",
                                   "(no row bit can complete a block)"], 10, 12))
    # drop note
    o.append(rect(600, 410, 380, 46, C["soft"], C["line"], 1, 4))
    o.append(lines(610, 428, ["any state -> empty: clear_kv_complete_at at or below the",
                              "block's first offset drops the bits; the bytes are left alone"],
                   10, 12))
    cap = ("B4, sequencing model: the life of one 16-token block of one storage slot. "
           "Boxes are states (the colours of B1); arrows are the operations of this PR, "
           "with the thread in brackets. The lower path is the hardware-attention policy: "
           "no bit is ever recorded, so the block never converts.")
    return figure(fid, W, H, "State machine of one 16-token block", "".join(o), cap)

