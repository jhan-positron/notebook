"""D2 of the PR 4424 kv_cache.hpp page: unit c2, the K layout state (two bit
arrays per page, their helpers and named values), drawn as a zoom of B1's
page column for state entry 5 of the worked example.

Every label is an identifier or a comment phrase of the code; every box cites
the head line that defines it (facts/kv_cache.json, verified).
"""
from svg_helpers import (C, arrow, bit_row, block_cell, cite, figure, fn_cell,
                         line, lines, marker_defs, rect, text, text_width)
from base_kv_cache import (BLOCKS_EXAMPLE, BLOCK_STATES_EXAMPLE,
                           BLOCK_WORDS_EXAMPLE, ROWS_EXAMPLE, bits_legend, fit)

BASE = ("Updates B1: the page column's two new arrays are opened to the bit level "
        "for state entry 5 of the worked example, with the helpers k_block_bits and "
        "k_block_is_vnni, the named values, who sets, drops, carries and reads the "
        "bits, and the move constructor's relaxed copy.")

# geometry of the entry-5 zoom: 64 row bits, cell 6.5 px, gap 1, group gap 6
CELL, GAP, GGAP = 6.5, 1, 6
PITCH = 16 * (CELL + GAP) + GGAP          # one 16-token block of bits = 126 px
BX = 150                                  # x where bit 0 starts


def bit_x(i):
    """Left x of row bit i."""
    return BX + i * (CELL + GAP) + (i // 16) * GGAP


def fig():
    fid = "kv_cache-d2"
    W, H = 700, 778
    o = [marker_defs(fid, {"ink": C["ink"], "new": C["new"], "rows": C["rows"],
                           "blk": C["blk"]})]
    boxes = []

    # ---- 1. the page box of B1 with its two new arrays -----------------------
    x, y, w, h = 10, 10, 680, 200
    o.append(rect(x, y, w, h, "#fff", C["ink"], 1.2, 6))
    o.append(text(x + 12, y + 20, "page 7 (page_size = 64 token offsets)", 12,
                  mono=True, weight=700))
    o.append(text(x + w - 12, y + 20, "changed", 10, "end", fill=C["new"], weight=700))
    o.append(cite(x + w - 6, y + h - 5, "kv_cache.hpp:1940-1942"))
    boxes.append(("page", "kv_cache.hpp:1940-1942 (page_size = 64 at 1942)"))
    o.append(arrow(fid, "ink", [(x + 30, y + 26), (x + 30, y + 50)], C["ink"], 1.4))
    o.append(text(x + 40, y + 38, "1 page -> layout_t::n_slots + EAGLE_STORAGE_SLOTS_1",
                  9, fill=C["ink"], weight=700))
    o.append(text(x + 40, y + 49, "entries, in each of the two arrays below", 9,
                  fill=C["ink"], weight=700))
    o.append(cite(x + w - 12, y + 49, "kv_cache.hpp:2616-2617, 2621-2622"))
    arrays = [
        ("k_rows_saved_[layout_t::n_slots + 1]", C["rows"], C["rows_fill"],
         "kv_cache.hpp:2608-2617",
         ["uint64_t: 1 entry -> page_size = 64 row bits,",
          "bit offset = that row is saved (offset_bit)"],
         "kv_cache.hpp:2509; tensor/k_vnni.hpp:103-105"),
        ("k_vnni_blocks_[layout_t::n_slots + 1]", C["blk"], C["blk_fill"],
         "kv_cache.hpp:2618-2622",
         ["uint8_t: 1 entry -> TOKEN_BLOCKS_4 = 4 block bits,",
          "bit c = block c holds VNNI (block_bit)"],
         "tensor/k_vnni.hpp:94-100"),
    ]
    e5 = {}
    for i, (name, col, fill, ref, note, nref) in enumerate(arrays):
        yl = y + 68 + i * 70
        o.append(text(x + 36, yl, name, 10.5, mono=True, fill=col, weight=700))
        o.append(text(x + 36 + text_width(name, 10.5, True) + 10, yl, "new", 10,
                      fill=C["new"], weight=700))
        cy = yl + 8
        cx = x + 36
        for lab in ["0", "1", "5", "...", "n-1"]:
            hi = lab == "5"
            o.append(rect(cx, cy, 44, 28, fill if hi else "#fff", col, 1.6 if hi else 1, 3))
            o.append(text(cx + 22, cy + 18, lab, 10, "middle", True))
            if hi:
                e5[i] = (cx + 22, cy + 28)
            cx += 48
        # the EAGLE entry, named as the code names it (layout_t::n_slots)
        o.append(rect(cx, cy, 50, 28, C["eagle_fill"], C["eagle"], 1.4, 3))
        o.append(text(cx + 25, cy + 18, "n_slots", 10, "middle", True))
        o.append(cite(x + 36, cy + 39, ref, "start"))
        for s in note:
            fit(s, 9, 300, False, "d2 array note")
        o.append(lines(cx + 60, cy + 10, note, 9, 12, fill=C["ink"], weight=600))
        o.append(cite(cx + 60, cy + 36, nref, "start"))
        boxes.append((name.split("[")[0], ref))
    boxes.append(("n_slots (entry layout_t::n_slots = the EAGLE storage)",
                  "kv_cache.hpp:2486, 2491-2492 (EAGLE_STORAGE_SLOTS_1 = 1)"))

    # ---- 2. entry 5 of the worked example, bit by bit --------------------------
    zy = 228
    o.append(text(10, zy, "state entry 5 (storage slot 5) of the worked example: page 7, "
                  "offsets 0..40 saved; bit 0 at the left", 10.5, weight=600))
    # k_block_bits(2) bracket over block 2
    bx2, bx2e = bit_x(32), bit_x(47) + CELL
    by = zy + 22
    o.append(line(bx2, by, bx2e, by, C["rows"], 1.4))
    o.append(line(bx2, by, bx2, by + 4, C["rows"], 1.4))
    o.append(line(bx2e, by, bx2e, by + 4, C["rows"], 1.4))
    o.append(text((bx2 + bx2e) / 2, by - 4, "k_block_bits(2) = FULL_BLOCK_0XFFFF << 32",
                  9, "middle", True, fill=C["rows"], weight=700))
    # row bits
    ry = zy + 28
    o.append(text(10, ry + 8, "k_rows_saved_[5]", 10.5, mono=True, fill=C["rows"]))
    body, _ = bit_row(BX, ry, ROWS_EXAMPLE, CELL, GAP, C["rows_fill"], C["rows"],
                      group=16, group_gap=GGAP)
    o.append(body)
    for c in range(4):
        o.append(text(bit_x(16 * c), ry + 19, f"offset {16 * c}", 8.5, fill=C["muted"]))
        o.append(text(bit_x(16 * c + 15) + CELL, ry + 19, f"{16 * c + 15}", 8.5, "end",
                      fill=C["muted"]))
    # token 37 marker
    tx = bit_x(37) + CELL / 2
    o.append(line(tx, ry + CELL + 1, tx, ry + 24, C["ink"], 1))
    o.append(text(tx + 4, ry + 32, "token 37 = bit 37 (block 2, t = 5): set", 8.5,
                  fill=C["muted"]))
    # block bits
    ky = ry + 46
    o.append(text(10, ky + 10, "k_vnni_blocks_[5]", 10.5, mono=True, fill=C["blk"]))
    for c in range(4):
        gx = bit_x(16 * c)
        on = BLOCKS_EXAMPLE[c] == "1"
        o.append(rect(gx, ky, 12, 12, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(text(gx + 17, ky + 10, f"bit {c}: {'set' if on else 'clear'}", 9,
                      fill=C["muted"]))
    # invariant arrow: block bit 0 -> its 16 row bits
    ix, mx = bit_x(0) + 6, bit_x(6)
    o.append(arrow(fid, "blk", [(ix, ky - 1), (ix, ky - 6), (mx, ky - 6),
                                (mx, ry + CELL + 3)], C["blk"], 1.4))
    o.append(text(mx + 6, ry + 32, "1 block bit -> BLOCK_TOKENS_16 = 16 row bits", 8.5,
                  fill=C["blk"], weight=700))
    ny = ky + 26
    o.append(lines(BX, ny, ["a set block bit implies the block's 16 row bits;",
                            "not the reverse: block 1 waits, block bit clear"], 9, 11,
                   fill=C["ink"]))
    o.append(cite(BX, ny + 22, "kv_cache.hpp:2620, 684-685", "start"))
    # block cells
    cy = ny + 30
    bw = PITCH - 7
    for c in range(4):
        gx = bit_x(16 * c)
        o.append(block_cell(gx, cy, bw, 34, BLOCK_STATES_EXAMPLE[c], f"block {c}", 11))
        o.append(text(gx + bw / 2, cy + 48, BLOCK_WORDS_EXAMPLE[c], 10, "middle",
                      fill=C["muted"]))
    o.append(cite(bit_x(63) + CELL, cy + 62, "kv_cache.hpp:2608-2622; 2126-2128"))
    boxes.append(("k_rows_saved_[5], k_vnni_blocks_[5] (worked example)",
                  "kv_cache.hpp:2608-2622; worked example of B1 (section 1)"))
    boxes.append(("block 0..3 (16-token blocks, by layout state)",
                  "kv_cache.hpp:2126-2128; states Note [K VNNI storage] 682-686"))
    # k_block_is_vnni(5, 37) reads bit 2: a short arrow from the note to the bit
    kx = bit_x(32)
    o.append(arrow(fid, "blk", [(kx + 40, ny + 16), (kx + 6, ky + 13)], C["blk"], 1.2))
    o.append(text(kx + 46, ny + 19, "k_block_is_vnni(5, 37) reads bit 2: clear", 9,
                  mono=True, fill=C["blk"], weight=600))
    # legend
    ly = cy + 72
    o.append(bits_legend(10, ly))
    lx = 10
    for st, lab in [("vnni", "VNNI (converted)"), ("pend", "complete, may wait"),
                    ("rm", "row-major rows"), ("empty", "no row bit")]:
        o.append(block_cell(lx, ly + 22, 26, 14, st))
        o.append(text(lx + 32, ly + 33, lab, 11))
        lx += 32 + text_width(lab, 11) + 16

    # ---- 3. helpers, named values, who touches the bits, the move -------------
    sy = ly + 54
    lw, rx, rw = 335, 360, 330
    # left column: the two helpers
    o.append(fn_cell(10, sy, lw, 62, "k_block_bits(c)",
                     ["The 16 bits of block c (one bit per page offset:",
                      "static_assert page_size == k_vnni::PAGE_TOKENS_64)"],
                     "kv_cache.hpp:2507-2511", "new"))
    boxes.append(("k_block_bits", "kv_cache.hpp:2507-2511"))
    o.append(fn_cell(10, sy + 70, lw, 84, "k_block_is_vnni(state_ix, offset)",
                     ["Whether offset's 16-token block holds the VNNI layout:",
                      "k_vnni_blocks_[state_ix].load(acquire) & block_bit(c)"],
                     "kv_cache.hpp:2513-2518", "new"))
    o.append(lines(18, sy + 70 + 57, ["worked example (arrow in the zoom): k_block_is_vnni(5, 37),",
                                      "c = 37 / BLOCK_TOKENS_16 = 2, bit 2 clear -> false"],
                   9, 11, fill=C["blk"]))
    boxes.append(("k_block_is_vnni", "kv_cache.hpp:2513-2518"))
    # named values
    vy = sy + 162
    o.append(rect(10, vy, lw, 116, C["soft"], C["line"], 1, 4))
    o.append(text(18, vy + 15, "named values (static constexpr)", 10.5, weight=700))
    o.append(text(18 + 230, vy + 15, "new", 9.5, fill=C["new"], weight=700))
    vals = [("EAGLE_STORAGE_SLOTS_1 = 1",
             "one entry beyond the logical slots: the EAGLE storage (n_slots)"),
            ("BLOCK_COMPLETED_FALSE = false",
             "note_k_row_saved: the row did not complete its block"),
            ("CONVERTED_FALSE / CONVERTED_TRUE",
             "k_block_to_vnni_at: whether the block was converted")]
    ty = vy + 32
    for nm, ds in vals:
        o.append(text(18, ty, nm, 9.5, mono=True, weight=600))
        fit(ds, 9, lw - 16, False, "d2 named value")
        o.append(text(18, ty + 11, ds, 9, fill=C["muted"]))
        ty += 26
    o.append(cite(10 + lw - 4, vy + 116 - 4, "kv_cache.hpp:2491-2497"))
    boxes.append(("EAGLE_STORAGE_SLOTS_1, BLOCK_COMPLETED_FALSE, CONVERTED_FALSE, "
                  "CONVERTED_TRUE", "kv_cache.hpp:2491-2497"))
    # right column: who touches the bits
    o.append(rect(rx, sy, rw, 172, "#fff", C["ink"], 1.2, 4))
    o.append(text(rx + 8, sy + 15, "set by / dropped by / carried by / read by [thread]",
                  10.5, weight=700))
    rows_ = [
        ("set", C["rows"], ["row bit: save_k [main thread]; not for the rows of a",
                            "hardware-scored operation"]),
        ("set", C["blk"], ["16 row bits + block bit: full-block save [any thread",
                           "of a shared window], fetch_or"]),
        ("set", C["blk"], ["block bit: the forward-end conversion [main thread]"]),
        ("drop", C["gone"], ["both: clear_kv_complete_at [token tree, tree lock]"]),
        ("carry", C["ink"], ["both: page copies (copy_storage_slot)"]),
        ("read", C["ink"], ["block bit: k_block_is_vnni, k_vnni_blocks (acquire)"]),
    ]
    ty = sy + 32
    for verb, col, ls in rows_:
        o.append(text(rx + 8, ty, verb, 9.5, weight=700, fill=col))
        for s in ls:
            fit(s, 9.5, rw - 50, False, "d2 who")
        o.append(lines(rx + 44, ty, ls, 9.5, 11.5))
        ty += 11.5 * len(ls) + 5
    o.append(cite(rx + rw - 4, sy + 172 - 4,
                  "kv_cache.hpp:2608-2620; 2206-2207; 2550-2551; 709-711"))
    boxes.append(("set by / dropped by / carried by (the member comment)",
                  "kv_cache.hpp:2611-2615 (member comment 2608-2620); threads: 2206-2207 "
                  "(conversion), 2550-2551 (clear), 709-711 (any thread of a shared window)"))
    # the move constructor
    my = sy + 180
    o.append(fn_cell(rx, my, rw, 90, "page(page&& other)",
                     ["copies both arrays entry by entry: load(relaxed) ->",
                      "store(relaxed), as for kv_saves_ [single-threaded]"],
                     "kv_cache.hpp:1968-1973", "changed"))
    o.append(lines(rx + 8, my + 57, ["for l < k_rows_saved_.size(): other.k_rows_saved_[l],",
                                     "other.k_vnni_blocks_[l] -> this page: 2 words per entry"],
                   9, 11, fill=C["ink"]))
    boxes.append(("page(page&&)", "kv_cache.hpp:1958-1974 (single-threaded: comment 1958-1959)"))

    cap = ("Updates B1: the two new arrays of the page column, opened to the bit level "
           "for state entry 5 of the worked example (page 7, slot 5, offsets 0..40 "
           "saved). Look at the bracket over block 2 (k_block_bits(2)). Look at the "
           "short arrow from the bit-0 square up to its 16 row bits: a set block bit "
           "implies them, and block 1 shows that the reverse does not hold. Look at the "
           "acquire load of k_block_is_vnni(5, 37), which finds bit 2 clear. The lower "
           "boxes list the named values, who sets, drops, carries and reads the bits "
           "(thread in brackets), and the move constructor's relaxed copy of both "
           "arrays.")
    legend = [
        ("box", "white box, ink outline: page 7, the helpers k_block_bits and "
                "k_block_is_vnni, the 'set by / dropped by / carried by / read by' "
                "table, the move constructor page(page&&)"),
        ("ctx", "grey box, thin grey outline: the named values (static constexpr) "
                "EAGLE_STORAGE_SLOTS_1, BLOCK_COMPLETED_FALSE, CONVERTED_FALSE / "
                "CONVERTED_TRUE"),
        ("rows", "green: a set bit of k_rows_saved_ (one square per page offset; "
                 "offsets 0..40 of entry 5 are set), and entry 5 of the k_rows_saved_ "
                 "array"),
        ("white, green outline: the other entries of the k_rows_saved_ array "
         "(0, 1, ..., n-1)", "#fff", C["rows"], False, False),
        ("blk", "pink: a set bit of k_vnni_blocks_ (bit 0 of entry 5: block 0 holds "
                "VNNI), and entry 5 of the k_vnni_blocks_ array"),
        ("white, pink outline: the other entries of the k_vnni_blocks_ array "
         "(0, 1, ..., n-1)", "#fff", C["blk"], False, False),
        ("eagle", "light blue: entry layout_t::n_slots of each array, the EAGLE "
                  "storage slot"),
        ("bit_clear", "white square: a bit that is clear (row bits 41..63, block "
                      "bits 1..3)"),
        ("vnni", "blue: block 0 holds the VNNI layout (converted; block bit 0 set)"),
        ("pend", "orange-red dashed: block 1 is complete but not converted (16 row bits "
                 "set, block bit 1 clear)"),
        ("rm", "orange: block 2 holds row-major rows (offsets 32..40 saved, block "
               "bit 2 clear)"),
        ("empty", "grey dashed: block 3 has no row bit (no row saved, bytes "
                  "undefined)"),
        ("red label: the verb 'drop' in the table; clear_kv_complete_at clears "
         "both bit words of an entry", "text", C["gone"]),
        ("arrow", "ink arrow: 1 page -> layout_t::n_slots + EAGLE_STORAGE_SLOTS_1 "
                  "entries in each of the two arrays"),
        ("pink arrow: block bit 0 implies its 16 row bits; k_block_is_vnni(5, 37) "
         "reads bit 2", "arrow", C["blk"]),
        "font_mono",
        "font_sans",
        "font_cite",
        ("font_tag", "bold 'new' = added by this PR (the two arrays, k_block_bits, "
                     "k_block_is_vnni, the named values); 'changed' = changed by it "
                     "(page, the move constructor page(page&&))"),
    ]
    return figure(fid, W, H, "The K layout state: two bit arrays per page and their "
                  "constants", "".join(o), cap, boxes=boxes, legend=legend)
