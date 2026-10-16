"""Change diagram of unit c8 of the kv_cache.hpp page (PR 4959):
forgetting rows when a new token takes an offset (clear_kv_complete_at ->
k_forget_row, with k_storage_readable).

Exposes figs() -> [HTML of "kv_cache-d8a", HTML of "kv_cache-d8b"] and BASE.
  d8a: the call path, the helpers, the masks and the three cases per state
       entry, with the memory orders and the thread.
  d8b: the worked example before -> after for three new tokens: offset 46 (a
       decode append, the two-load skip), offset 37 at the default moment
       (block 2 row-major: only the bits drop) and offset 37 after the
       transition (block 2 converted: block_to_rows, then the drops).
Every label is an identifier or a comment phrase of the code; every box cites
the head line that defines it (kv_cache.hpp at 6b081187e1). Line numbers are
head lines of kv_cache.hpp unless a file name is given.
"""
from svg_helpers import (C, arrow, bit_row, block_cell, cite, figure, fn_cell,
                         legend_chip, line, lines, marker_defs, rect, text,
                         text_width)
from base_kv_cache import (BLOCKS_EXAMPLE, BLOCK_STATES_EXAMPLE,
                           BLOCK_WORDS_EXAMPLE, ROWS_EXAMPLE, bits_legend,
                           caller_cell, fit, ops_cell)

BASE = ("Updates B4: the two clear arrows of the sequencing model (converted -> "
        "incomplete, row-major; any state -> empty) are opened into the k_forget_row "
        "procedure that clear_kv_complete_at now calls: its call path and helpers, "
        "its masks and the three cases per state entry (d8a), and the before -> "
        "after of the worked example's bits for a decode append at offset 46 and "
        "a new token at offset 37, before and after block 2 is converted (d8b).")

# ---- the masks of k_forget_row, computed with the code's formulas ------------
# kv_cache.hpp:2584-2587; k_vnni::offset_bit / block_bit tensor/k_vnni.hpp:94-101
BLOCK_TOKENS_16 = 16


def offset_bit(offset):
    return 1 << offset


def block_bit(c):
    return 1 << c


def masks(offset):
    c = offset // BLOCK_TOKENS_16
    rows_below = offset_bit(offset) - 1
    blocks_below = (block_bit(c) - 1) & 0xFF
    block_keeps_rows = offset % BLOCK_TOKENS_16 != 0
    return c, rows_below, blocks_below, block_keeps_rows


def forget(rows, blocks, offset):
    """One state entry of k_forget_row (kv_cache.hpp:2594-2615), with
    k_storage_readable taken as true. Returns (rows, blocks, case)."""
    c, rows_below, blocks_below, keeps = masks(offset)
    if (blocks & ~blocks_below) == 0 and (rows & ~rows_below) == 0:
        return rows, blocks, 1
    case = 2 if (keeps and (blocks & block_bit(c)) != 0) else 3
    return rows & rows_below, blocks & blocks_below, case


def word(bits):
    """Bit string (bit 0 at the left) -> integer."""
    return sum(1 << i for i, b in enumerate(bits) if b == "1")


def bits(n, width):
    return "".join("1" if (n >> i) & 1 else "0" for i in range(width))


ROWS0, BLOCKS0 = word(ROWS_EXAMPLE), word(BLOCKS_EXAMPLE)       # bits 0..45, 0b0011
ROWS1, BLOCKS1 = (1 << 48) - 1, 0b0111                           # after the transition
ROWS_A, BLOCKS_A, CASE_A = forget(ROWS0, BLOCKS0, 46)
ROWS_B, BLOCKS_B, CASE_B = forget(ROWS0, BLOCKS0, 37)
ROWS_C, BLOCKS_C, CASE_C = forget(ROWS1, BLOCKS1, 37)
assert CASE_A == 1 and ROWS_A == ROWS0 and BLOCKS_A == BLOCKS0
assert CASE_B == 3 and ROWS_B == (1 << 37) - 1 and BLOCKS_B == 0b0011
assert CASE_C == 2 and ROWS_C == (1 << 37) - 1 and BLOCKS_C == 0b0011
assert masks(46) == (2, (1 << 46) - 1, 0b0011, True)
assert masks(37) == (2, (1 << 37) - 1, 0b0011, True)

# geometry of the bit rows (the same as D1): cell 6.5, gap 1, group gap 6
CELL, GAP, GGAP = 6.5, 1, 6
PITCH = 16 * (CELL + GAP) + GGAP   # one 16-token block of bits = 126 px
BX = 150                           # x where bit 0 starts
BW = PITCH - 7                     # width of one block cell under its bits


def bit_x(i):
    """Left x of row bit i."""
    return BX + i * (CELL + GAP) + (i // 16) * GGAP


# ---- D8a: the path and the procedure --------------------------------------------
def case_cell(x, y, w, h, title, cond, result, ref, fill, stroke, cond_mono=True):
    """One of the three cases per state entry: title, the condition (mono),
    what happens (sans), citation lower-right."""
    o = [rect(x, y, w, h, fill, stroke, 1.3, 4)]
    fit(title, 10, w - 16, False, "case title")
    o.append(text(x + 8, y + 15, title, 10, weight=700))
    ty = y + 29
    for s in cond:
        fit(s, 9, w - 16, cond_mono, "case cond")
        o.append(text(x + 8, ty, s, 9, mono=cond_mono))
        ty += 11
    ty += 2
    for s in result:
        fit(s, 9, w - 16, False, "case result")
        o.append(text(x + 8, ty, s, 9))
        ty += 11
    fit(ref, 8.5, w - 8, True, "case cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fan_out(fid, name, color, x_from, y_from, y_bus, targets, y_to):
    """A plain stem from (x_from, y_from) down to the bus at y_bus, the bus
    across the targets, and one arrow down from the bus to y_to per target."""
    xs = sorted(targets + [x_from])
    o = [line(x_from, y_from, x_from, y_bus, color, 1.4),
         line(xs[0], y_bus, xs[-1], y_bus, color, 1.4)]
    for tx in targets:
        o.append(arrow(fid, name, [(tx, y_bus), (tx, y_to)], color, 1.4))
    return "".join(o)


def fig_a():
    fid = "kv_cache-d8a"
    W = 700
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "rows": C["rows"],
                           "muted": C["muted"]})]
    boxes = []
    o.append(text(8, 16, "The clear path: clear_kv_complete_at -> k_forget_row "
                  "[token tree, tree lock]", 12, weight=700))

    # ---- row 1: caller -> clear_kv_complete_at -> k_forget_row -------------
    y, RH = 28, 72
    CX, CW = 8, 192
    FX, FW = 212, 224
    GX, GW = 448, 244
    o.append(caller_cell(CX, y, CW, RH,
                         ["full.hpp create_child_at_location,",
                          "extend_leaf_edge,",
                          "invalidate_restored_book",
                          "[token tree, tree lock]"],
                         "full.hpp:669, 818, 3340"))
    boxes.append(("create_child_at_location / extend_leaf_edge / "
                  "invalidate_restored_book (callers)",
                  "full.hpp:654 (call at 669), 801 (call at 818), 3323 (call at 3340)"))
    o.append(arrow(fid, "ink", [(CX + CW + 2, y + RH / 2), (FX - 2, y + RH / 2)],
                   C["ink"], 1.4))
    o.append(fn_cell(FX, y, FW, RH, "clear_kv_complete_at",
                     ["clears the completion state of one offset",
                      "across all slots; then k_forget_row (new call)"],
                     "kv_cache.hpp:2507-2514", "changed"))
    boxes.append(("clear_kv_complete_at", "kv_cache.hpp:2507-2514 (the new call at 2513)"))
    o.append(arrow(fid, "ink", [(FX + FW + 2, y + RH / 2), (GX - 2, y + RH / 2)],
                   C["ink"], 1.4))
    o.append(fn_cell(GX, y, GW, RH, "k_forget_row(offset)",
                     ["drops the saved-row bits at and above the",
                      "offset and their blocks' bits, in every slot"],
                     "kv_cache.hpp:2575-2617", "new"))
    boxes.append(("k_forget_row", "kv_cache.hpp:2575-2617"))

    # ---- row 2: what k_forget_row calls ------------------------------------
    y2, R2 = 128, 100
    HX, HW = 8, 224      # k_storage_readable
    WX, WW = 244, 212    # k_with_storage_geometry
    OX, OW = 468, 224    # block_to_rows (k_vnni.hpp operation)
    o.append(fan_out(fid, "ink", C["ink"], GX + 122, y + RH, 112,
                     [HX + 110, WX + 106, OX + 112], y2 - 2))
    o.append(text(GX + 128, y + RH + 10, "case 2 only (below)", 8.5, fill=C["muted"]))
    for tx, n in [(HX + 110, "case 2: call at 2603"), (WX + 106, "case 2: call at 2604"),
                  (OX + 112, "case 2: call at 2607")]:
        o.append(text(tx + 6, y2 - 6, n, 8.5, fill=C["muted"]))
    R2C = 62   # cell height; the notes under each cell fill the rest of R2
    o.append(fn_cell(HX, y2, HW, R2C, "k_storage_readable",
                     ["the storage is published (no private KV",
                      "restore in flight) and the chunk has memory"],
                     "kv_cache.hpp:2566-2573", "new"))
    o.append(lines(HX + 4, y2 + R2C + 12, ["reclaimable_kv_restore_attempt_ == 0 &&",
                                           "slot_page(storage_offset, pageno()).base"],
                   8.5, 10, mono=True, fill=C["muted"]))
    boxes.append(("k_storage_readable", "kv_cache.hpp:2566-2573; reads "
                  "book::reclaimable_kv_restore_attempt_ (1568) and book::slot_page "
                  "(1718)"))
    o.append(fn_cell(WX, y2, WW, R2C, "k_with_storage_geometry",
                     ["calls the lambda with the geometry of",
                      "the storage slot (primary for EAGLE)"],
                     "kv_cache.hpp:2552-2564", "new (C2)"))
    o.append(lines(WX + 4, y2 + R2C + 12, ["the lambda: 2604-2612, one",
                                           "block_to_rows per KV head"],
                   8.5, 10, fill=C["muted"]))
    boxes.append(("k_with_storage_geometry", "kv_cache.hpp:2552-2564 (unit C2); "
                  "the lambda of k_forget_row at 2604-2612"))
    o.append(ops_cell(OX, y2, OW, R2,
                      ["block_to_rows(kv_block_at_storage",
                       "<geometry>(storage_offset, kv_head)",
                       ".k.as_view(), c): in place, 4 KiB",
                       "per block, every KV head of the slot",
                       "if constexpr layout_on: a row-major",
                       "geometry converts nothing"],
                      ["tensor/k_vnni.hpp:478-491;", "kv_cache.hpp:2604-2612"]))
    boxes.append(("block_to_rows (the lambda of k_forget_row)",
                  "tensor/k_vnni.hpp:478-491; kv_cache.hpp:2604-2612; "
                  "kv_block_at_storage kv_cache.hpp:2689-2697"))

    # ---- the thread rule ------------------------------------------------------
    ty = y2 + R2 + 18
    rule = ["Called with the token tree locked, between forward passes: no reader "
            "runs meanwhile [kv_cache.hpp:2581-2582].",
            "The in-place transposes rely on the same rule as the rest of the tree work: "
            "no forward pass reads the book",
            "while the tree lock is held [kv_cache.hpp:735-738]."]
    for s in rule:
        fit(s, 9.5, 684, False, "rule")
    o.append(lines(8, ty, rule, 9.5, 12))
    boxes.append(("thread rule: token tree locked, between forward passes",
                  "kv_cache.hpp:2581-2582; Note [K VNNI storage] 735-738"))

    # ---- the masks -------------------------------------------------------------
    my, MH = ty + 36, 86
    o.append(rect(8, my, 684, MH, "#fff", C["ink"], 1.2, 4))
    o.append(text(16, my + 15, "k_forget_row(offset): the masks, computed once per call",
                  10.5, weight=700))
    exprs = [(16, my + 30, "c = offset / k_vnni::BLOCK_TOKENS_16"),
             (340, my + 30, "rows_below = k_vnni::offset_bit(offset) - 1"),
             (16, my + 42, "blocks_below = uint8_t(k_vnni::block_bit(c) - 1)"),
             (340, my + 42, "block_keeps_rows = offset % k_vnni::BLOCK_TOKENS_16 != 0")]
    for ex, ey, es in exprs:
        fit(es, 9.5, 688 - ex, True, "masks")
        o.append(text(ex, ey, es, 9.5, mono=True))
    m3 = ["kept: rows_below (the offsets below the token's), blocks_below (the blocks "
          "below c);",
          "block_keeps_rows: the offset is not the first of its block"]
    for s in m3:
        fit(s, 9, 668, False, "m3")
    o.append(lines(16, my + 56, m3, 9, 11, fill=C["ink"]))
    o.append(cite(688, my + MH - 4,
                  "kv_cache.hpp:2584-2587; offset_bit / block_bit: tensor/k_vnni.hpp:94-101"))
    boxes.append(("c, rows_below, blocks_below, block_keeps_rows (the masks)",
                  "kv_cache.hpp:2584-2587; k_vnni::offset_bit / block_bit "
                  "tensor/k_vnni.hpp:94-101"))

    # ---- the loop over state entries (how many) --------------------------------
    ly = my + MH + 22
    o.append(arrow(fid, "rows", [(60, my + MH + 2), (60, ly - 2)], C["rows"], 1.6))
    o.append(text(70, my + MH + 15, "1 call -> k_rows_saved_.size() = layout_t::n_slots + "
                  "EAGLE_STORAGE_SLOTS_1 entries, one per storage slot", 9,
                  fill=C["rows"], weight=700))
    LH = 72
    o.append(rect(8, ly, 684, LH, C["soft"], C["line"], 1, 4))
    o.append(text(16, ly + 15, "for every state entry ix: break, skip, resolve the storage "
                  "slot, load the block byte", 10, weight=700))
    loop = ["eagle = ix == layout_t::n_slots; if (eagle && !book.has_eagle_storage()) break;",
            "if (!eagle && ix >= book.logical_slot_count()) continue;",
            "storage_offset = eagle ? book.eagle_storage_offset() : kv_storage_offset(ix);",
            "converted = k_vnni_blocks_[ix].load(memory_order_acquire);"]
    for s in loop:
        fit(s, 9, 540, True, "loop")
    o.append(lines(16, ly + 30, loop, 9, 11, mono=True))
    o.append(cite(688, ly + LH - 4, "kv_cache.hpp:2588-2595"))
    boxes.append(("the loop over state entries (break at the EAGLE entry, skip "
                  "inactive slots, storage_offset, converted)", "kv_cache.hpp:2588-2595"))

    # ---- the three cases ---------------------------------------------------------
    cy, CH, CWd = ly + LH + 24, 120, 220
    xs = [8, 240, 472]
    o.append(fan_out(fid, "ink", C["ink"], 350, ly + LH, ly + LH + 10,
                     [x + CWd / 2 for x in xs], cy - 2))
    o.append(case_cell(xs[0], cy, CWd, CH, "1. nothing at or above the offset",
                       ["(converted & ~blocks_below) == 0 &&",
                        "(k_rows_saved_[ix].load(acquire)",
                        "   & ~rows_below) == 0"],
                       ["-> continue: two acquire loads, no",
                        "locked read-modify-write (the",
                        "common case of a decode append)"],
                       "kv_cache.hpp:2596-2601", "#fff", C["ink"]))
    boxes.append(("case 1: nothing at or above the offset (continue)",
                  "kv_cache.hpp:2596-2601"))
    o.append(case_cell(xs[1], cy, CWd, CH, "2. the converted block keeps rows",
                       ["block_keeps_rows &&",
                        "(converted & block_bit(c)) != 0 &&",
                        "k_storage_readable(storage_offset)"],
                       ["-> block_to_rows on block c of every",
                        "KV head: geometry.n_kv_heads calls,",
                        "so the rows below the offset stay",
                        "readable; then the drops (below)"],
                       "kv_cache.hpp:2602-2613", C["rm_fill"], C["rm"]))
    boxes.append(("block_keeps_rows && (converted & block_bit(c)) != 0 && "
                  "k_storage_readable: case 2, block_to_rows", "kv_cache.hpp:2602-2613"))
    o.append(case_cell(xs[2], cy, CWd, CH, "3. otherwise: only the bits change",
                       ["bits at or above the offset, but no",
                        "converted block keeping rows, or the",
                        "storage is not readable"],
                       ["blocks above hold no live row; a KV",
                        "restore not yet published or reclaimed",
                        "storage holds no valid bytes: the",
                        "bytes are left alone; then the drops"],
                       "kv_cache.hpp:2580-2581, 750-752", "#fff", C["ink"], False))
    boxes.append(("case 3: otherwise, only the bits change (bytes left alone)",
                  "kv_cache.hpp:2580-2581; Note [K VNNI storage] 750-752"))

    # ---- the drops ----------------------------------------------------------------
    dy, DH = cy + CH + 16, 52
    # case 1 leaves the loop body: a short grey arrow to its outcome text
    o.append(arrow(fid, "muted", [(xs[0] + 20, cy + CH + 2), (xs[0] + 20, cy + CH + 14)],
                   C["muted"], 1.3))
    o.append(text(xs[0] + 28, cy + CH + 13, "continue: nothing dropped, next entry", 9,
                  fill=C["muted"]))
    for x in xs[1:]:
        o.append(arrow(fid, "ink", [(x + CWd / 2, cy + CH + 2), (x + CWd / 2, dy - 2)],
                       C["ink"], 1.4))
    o.append(rect(240, dy, 452, DH, C["soft"], C["line"], 1, 4))
    o.append(text(248, dy + 14, "fetch_and on both arrays, after case 2 or 3 (release "
                  "order)", 10, weight=700))
    o.append(text(248, dy + 27, "blocks.fetch_and(blocks_below, memory_order_release);",
                  9, mono=True))
    o.append(text(248, dy + 38, "k_rows_saved_[ix].fetch_and(rows_below, memory_order_release);",
                  9, mono=True))
    o.append(cite(688, dy + DH - 4, "kv_cache.hpp:2614-2615"))
    boxes.append(("blocks.fetch_and(blocks_below, release); "
                  "k_rows_saved_[ix].fetch_and(rows_below, release)", "kv_cache.hpp:2614-2615"))
    H = dy + DH + 10
    cap = ("Updates B4: the two clear arrows of the sequencing model are opened into "
           "the procedure behind them. clear_kv_complete_at (changed) zeroes the "
           "kv_saves_ counters of the offset and now calls k_forget_row (new), which "
           "the scheduler runs on the token tree with the tree lock held between "
           "forward passes. Look at the masks box: it says what \"at and above the "
           "offset\" means in bits. Then look at the three cases per state entry. "
           "Case 1 is the two-load skip of a decode append. Case 2 is the block_to_rows "
           "path, taken when the offset's converted block keeps rows below it and "
           "k_storage_readable holds. Case 3 is the drop of the bits alone, with "
           "fetch_and in release order.")
    legend = [
        ("box", "white box, ink outline: a function (clear_kv_complete_at, "
         "k_forget_row, k_storage_readable, k_with_storage_geometry), the masks "
         "box, and cases 1 and 3; the name in bold monospace, what it does in "
         "sans-serif"),
        ("ctx", "grey box, thin grey outline: the callers in full.hpp, and the two steps of "
         "k_forget_row that are not a case: the loop over state entries and the fetch_and "
         "drops"),
        ("lane", "white box, thin grey outline: block_to_rows, the k_vnni.hpp operation "
         "case 2 calls once per KV head"),
        ("rm", "orange: case 2, the converted block keeps rows: block_to_rows rewrites "
         "block c row-major before the drops"),
        ("arrow", "ink arrow: a call (caller -> clear_kv_complete_at -> k_forget_row; "
         "k_forget_row -> its three helpers, case 2 only) or a step (the loop -> "
         "the three cases; case 2 or 3 -> the fetch_and drops)"),
        ("green arrow and label: 1 call -> k_rows_saved_.size() state entries, "
         "one per storage slot (how many times the loop body runs)", "arrow",
         C["rows"]),
        ("arrow_muted", "grey arrow: case 1 leaves the loop body (continue: nothing "
         "dropped, next entry)"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = k_forget_row, k_storage_readable and "
         "k_with_storage_geometry (C2) are added by this PR; 'changed' = "
         "clear_kv_complete_at now calls k_forget_row"),
    ]
    return figure(fid, W, H, "The clear path: clear_kv_complete_at, k_forget_row, "
                  "its masks and its three cases per state entry", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- D8b: the worked example, before -> after ------------------------------------
def rows_row(o, y, bits_, label_right=None, mark=None, mark_label=None):
    """k_rows_saved_[5] as 64 bit squares with its label at the left; an
    optional red dashed mark around one bit (the new token's offset)."""
    o.append(text(8, y + 8, "k_rows_saved_[5]", 10.5, mono=True, fill=C["rows"]))
    body, _ = bit_row(BX, y, bits_, CELL, GAP, C["rows_fill"], C["rows"],
                      group=16, group_gap=GGAP)
    o.append(body)
    if mark is not None:
        o.append(rect(bit_x(mark) - 1.5, y - 1.5, CELL + 3, CELL + 3, "none",
                      C["gone"], 1.3, 1, "2 1.5"))
        o.append(text(bit_x(mark) + CELL / 2, y - 4, mark_label, 8.5, "middle",
                      fill=C["gone"], weight=700))
    if label_right:
        o.append(text(654, y + 7, label_right, 9.5, fill=C["muted"]))


def blocks_row(o, y, bits_, label_right=None, dropped=(), dropped_note=None):
    """k_vnni_blocks_[5] as 4 squares under the first bit of each block."""
    o.append(text(8, y + 10, "k_vnni_blocks_[5]", 10.5, mono=True, fill=C["blk"]))
    for c in range(4):
        gx = bit_x(16 * c)
        on = bits_[c] == "1"
        o.append(rect(gx, y, 12, 12, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        if c in dropped:
            o.append(rect(gx - 1.5, y - 1.5, 15, 15, "none", C["gone"], 1.3, 1, "2 1.5"))
            o.append(text(gx + 17, y + 10, dropped_note, 8.5, fill=C["gone"], weight=700))
        else:
            o.append(text(gx + 17, y + 10, f"bit {c}: {'set' if on else 'clear'}", 9,
                          fill=C["muted"]))
    if label_right:
        o.append(text(654, y + 10, label_right, 9.5, fill=C["muted"]))


def bracket(o, x1, x2, y, label, color, anchor="middle", lx=None):
    """A bracket under a bit range with its label 11 px below."""
    o.append(line(x1, y, x2, y, color, 1.4))
    o.append(line(x1, y, x1, y - 3, color, 1.4))
    o.append(line(x2, y, x2, y - 3, color, 1.4))
    if lx is None:
        lx = (x1 + x2) / 2
    o.append(text(lx, y + 11, label, 8.5, anchor, fill=color, weight=700))


def block_cells(o, y, states, words, tags=None, h=40):
    """Four block cells under their bits: 'block c' plus 1-2 word lines inside;
    an optional coloured tag at the top-right of a cell."""
    for c in range(4):
        gx = bit_x(16 * c)
        o.append(block_cell(gx, y, BW, h, states[c]))
        o.append(text(gx + 6, y + 13, f"block {c}", 10, mono=True, weight=600))
        ws = words[c] if isinstance(words[c], (list, tuple)) else [words[c]]
        ty = y + 25
        for s in ws:
            fit(s, 8.5, BW - 10, False, "block words")
            o.append(text(gx + 6, ty, s, 8.5))
            ty += 10
        if tags and tags[c]:
            lab, col = tags[c]
            o.append(text(gx + BW - 4, y + 12, lab, 8.5, "end", fill=col, weight=700))


def fig_b():
    fid = "kv_cache-d8b"
    W, H = 712, 820
    o = [marker_defs(fid, {"rm": C["rm"], "ink": C["ink"]})]
    boxes = []
    o.append(text(8, 16, "Worked example (B1): page 7, entry 5 (slot 5), offsets 0..45 "
                  "saved, blocks 0 and 1 converted", 11.5, weight=700))

    # ---- (a) a decode append at offset 46 -------------------------------------
    ya = 28
    o.append(text(8, ya + 12, "(a) a decode append: the next token takes offset 46 -> "
                  "k_forget_row(46)", 11, weight=700))
    ma = ("c = 2; rows_below = bits 0..45; blocks_below = block_bit(2) - 1 = bits 0, 1 "
          "(0b0011); block_keeps_rows = true (46 % 16 = 14)")
    fit(ma, 9, 684, True, "ma")
    o.append(text(8, ya + 25, ma, 9, mono=True))
    ry = ya + 40
    rows_row(o, ry, bits(ROWS0, 64), "unchanged", 46, "offset 46")
    bracket(o, bit_x(46), bit_x(63) + CELL, ry + CELL + 3,
            "~rows_below = bits 46..63 (the offset and above): all clear", C["rows"],
            "end", bit_x(63) + CELL)
    ky = ry + 32
    blocks_row(o, ky, bits(BLOCKS0, 4), "unchanged")
    bracket(o, bit_x(32), bit_x(48) + 12, ky + 16, "~blocks_below = bits 2, 3: clear",
            C["blk"])
    ra = ky + 42
    res_a = ["-> case 1 of D8a: (converted & ~blocks_below) == 0 and "
             "(k_rows_saved_[5].load(acquire) & ~rows_below) == 0, so the entry",
             "is skipped (continue): two acquire loads, no locked read-modify-write; "
             "the bits and the bytes are unchanged."]
    for s in res_a:
        fit(s, 9.5, 684, False, "res_a")
    o.append(lines(8, ra, res_a, 9.5, 12))
    o.append(cite(692, ra + 24, "kv_cache.hpp:2596-2601"))
    boxes.append(("(a) rows_below, blocks_below, block_keeps_rows of offset 46",
                  "kv_cache.hpp:2584-2587"))
    boxes.append(("(a) case 1: the entry is skipped after two acquire loads",
                  "kv_cache.hpp:2596-2601"))

    # ---- (b) a new token at offset 37, block 2 still row-major ------------------
    yb = ra + 30 + 12
    o.append(line(8, yb - 8, 692, yb - 8, C["line"]))
    o.append(text(8, yb + 12, "(b) a new token takes offset 37 while block 2 is row-major "
                  "(the default moment) -> k_forget_row(37)", 11, weight=700))
    mb = ("c = 2; rows_below = bits 0..36; blocks_below = 0b0011; block_keeps_rows = true "
          "(37 % 16 = 5); converted & block_bit(2) == 0")
    fit(mb, 9, 684, True, "mb")
    o.append(text(8, yb + 25, mb, 9, mono=True))
    rb = yb + 40
    rows_row(o, rb, bits(ROWS0, 64), "before", 37, "offset 37")
    rb2 = rb + 20
    rows_row(o, rb2, bits(ROWS_B, 64), "after")
    o.append(rect(bit_x(37) - 1.5, rb2 - 1.5, bit_x(45) + CELL - bit_x(37) + 3,
                  CELL + 3, "none", C["gone"], 1.2, 1, "3 2"))
    o.append(text(BX, rb2 + 20, "removed: bits 37..45 (fetch_and(rows_below, release)); "
                  "bits 0..36 kept; block bits unchanged (fetch_and(0b0011))", 8.5,
                  fill=C["gone"], weight=700))
    res_b = ["-> case 3 of D8a: the rows at and above 37 have bits, but block 2 is not "
             "converted, so no block_to_rows runs;",
             "the bytes of rows 37..45 are left alone and only the bits change; block 2 "
             "keeps rows 32..36 row-major (5 rows)."]
    for s in res_b:
        fit(s, 9.5, 684, False, "res_b")
    o.append(lines(8, rb2 + 36, res_b, 9.5, 12))
    o.append(cite(692, rb2 + 60, "kv_cache.hpp:2580-2581, 2614-2615"))
    bb = rb2 + 70
    block_cells(o, bb, ["vnni", "vnni", "rm", "empty"],
                [["VNNI, unchanged"], ["VNNI, unchanged"],
                 ["5 rows, row-major", "(rows 32..36 kept)"], ["no row saved"]],
                tags=[None, None, ("bits dropped", C["gone"]), None])
    o.append(text(654, bb + 24, "after", 9.5, fill=C["muted"]))
    boxes.append(("(b) case 3: only the bits change, block 2 stays row-major",
                  "kv_cache.hpp:2580-2581, 2614-2615"))

    # ---- (c) a new token at offset 37 after the transition (block 2 converted) ---
    yc = bb + 40 + 18
    o.append(line(8, yc - 8, 692, yc - 8, C["line"]))
    o.append(text(8, yc + 12, "(c) the same offset 37 after the forward end converted "
                  "block 2 (rows 0..47 saved, 0b0111) -> k_forget_row(37)", 11, weight=700))
    mc = ("c = 2; the same masks; converted & block_bit(2) != 0 and block_keeps_rows: "
          "case 2 when k_storage_readable(storage_offset)")
    fit(mc, 9, 684, True, "mc")
    o.append(text(8, yc + 25, mc, 9, mono=True))
    rc = yc + 40
    rows_row(o, rc, bits(ROWS1, 64), "before", 37, "offset 37")
    kc = rc + 20
    blocks_row(o, kc, bits(BLOCKS1, 4), "before")
    bc = kc + 22
    block_cells(o, bc, ["vnni", "vnni", "vnni", "empty"],
                [["VNNI (whole-block save)"], ["VNNI (whole-block save)"],
                 ["VNNI (converted at", "the forward end)"], ["no row saved"]])
    o.append(text(654, bc + 24, "before", 9.5, fill=C["muted"]))
    # the step: case 2, then the drops
    sy = bc + 40 + 26
    step = ["case 2 of D8a: block_keeps_rows, (converted & block_bit(2)) != 0 and",
            "k_storage_readable(storage_offset) hold -> block_to_rows(plane, c = 2)",
            "on every KV head's plane of slot 5: geometry.n_kv_heads calls, in",
            "place, 4 KiB each; then blocks.fetch_and(0b0011, release) and",
            "k_rows_saved_[5].fetch_and(bits 0..36, release)."]
    for s in step:
        fit(s, 9.5, 500, False, "step")
    o.append(lines(176, sy, step, 9.5, 12))
    o.append(cite(692, sy + 58, "kv_cache.hpp:2602-2615"))
    # the arrow block 2 (before) -> block 2 (after), labelled with how many
    ax = bit_x(32) + 14
    ra2 = sy + 70
    ka2 = ra2 + 30
    ba2 = ka2 + 24
    o.append(arrow(fid, "rm", [(ax, bc + 40 + 2), (ax, bc + 48), (136, bc + 48),
                               (136, ba2 - 8), (ax, ba2 - 8), (ax, ba2 - 2)],
                   C["rm"], 1.6))
    alab = ["block_to_rows:", "1 block c = 2 ->", "geometry.n_kv_heads", "planes, 4 KiB each"]
    for s in alab:
        fit(s, 8.5, 122, False, "alab")
    o.append(lines(8, sy + 10, alab, 8.5, 11, fill=C["rm"], weight=700))
    # after
    rows_row(o, ra2, bits(ROWS_C, 64), "after")
    o.append(rect(bit_x(37) - 1.5, ra2 - 1.5, bit_x(47) + CELL - bit_x(37) + 3,
                  CELL + 3, "none", C["gone"], 1.2, 1, "3 2"))
    o.append(text(BX, ra2 + 20, "removed: bits 37..47 (fetch_and(rows_below, "
                  "release)); bits 0..36 kept", 8.5, fill=C["gone"], weight=700))
    blocks_row(o, ka2, bits(BLOCKS_C, 4), "after", dropped=(2,),
               dropped_note="bit 2: removed")
    block_cells(o, ba2, ["vnni", "vnni", "rm", "empty"],
                [["VNNI, unchanged"], ["VNNI, unchanged"],
                 ["5 rows, row-major", "(rows 32..36 kept)"], ["no row saved"]],
                tags=[None, None, ("new", C["new"]), None])
    o.append(text(654, ba2 + 24, "after", 9.5, fill=C["muted"]))
    ny = ba2 + 40 + 16
    notes = ["(c) is the moment after the step that saved offset 47 and the forward end "
             "that converted block 2 (unit C5); the clear runs between passes,",
             "so a converted block is always the case the clear meets for a complete "
             "block [kv_cache.hpp:2581-2582; model.hpp:1842].",
             "A block above the offset (block 3 here) holds no live row: its bits are "
             "dropped and its bytes are left alone [kv_cache.hpp:2580-2581]."]
    for s in notes:
        fit(s, 9, 684, False, "notes")
    o.append(lines(8, ny, notes, 9, 11))
    boxes += [("k_rows_saved_[5] (before / after)", "kv_cache.hpp:2639-2648"),
              ("k_vnni_blocks_[5] (before / after)", "kv_cache.hpp:2649-2653"),
              ("(b) and (c) rows_below, blocks_below, block_keeps_rows of offset 37",
               "kv_cache.hpp:2584-2587"),
              ("(c) case 2: block_to_rows on block 2 of every KV head, then the drops",
               "kv_cache.hpp:2602-2615; tensor/k_vnni.hpp:478-491"),
              ("blocks above hold no live row: bits dropped, bytes left alone",
               "kv_cache.hpp:2580-2581"),
              ("block 0..3 (16-token blocks, by layout state)",
               "kv_cache.hpp:2174-2176; Note [K VNNI storage] 711-720")]
    # ---- legend ------------------------------------------------------------------
    ly = ny + 44
    o.append(bits_legend(8, ly))
    lx = 8
    for st, lab in [("vnni", "VNNI (converted)"),
                    ("rm", "row-major rows"), ("empty", "no row saved")]:
        o.append(legend_chip(lx, ly + 22, st, lab))
        lx += 32 + text_width(lab, 11) + 16
    o.append(rect(8, ly + 46, 26, 14, "none", C["gone"], 1.3, 1, "3 2"))
    o.append(text(40, ly + 57, "the new token's offset, or a bit dropped by the clear "
                  "(removed)", 11))
    H = ly + 68
    cap = ("Updates B4: the before -> after of the worked example's bits (page 7, state "
           "entry 5) for three new tokens. (a) A decode append at offset 46 finds "
           "nothing at or above the offset in either array and skips the entry after "
           "two acquire loads. (b) A new token at offset 37 while block 2 is still "
           "row-major drops the row bits 37..45 and nothing else: the bytes stay, "
           "block 2 keeps 5 rows. (c) The same offset after the forward end converted "
           "block 2: block_to_rows rewrites block 2 of every KV head's plane row-major "
           "first; then fetch_and drops bits 37..47 and block bit 2.")
    legend = [
        ("rows", "green square: a set bit of k_rows_saved_[5], a saved row at that "
         "offset; green text and bracket = the array's label and the ~rows_below range"),
        ("blk", "pink square: a set bit of k_vnni_blocks_[5] (a converted block); pink "
         "text and bracket = the array's label and the ~blocks_below range"),
        ("bit_clear", "white square: a clear bit of k_rows_saved_[5] or "
         "k_vnni_blocks_[5]"),
        ("vnni", "blue: a converted block (blocks 0 and 1; block 2 before the clear in (c))"),
        ("rm", "orange: row-major rows: block 2 after the clear in (b) and (c), 5 rows "
         "(rows 32..36 kept)"),
        ("empty", "grey dashed: no row saved: block 3"),
        ("red dashed frame: the new token's offset (46 in (a), 37 in (b) and (c)), or a "
         "bit dropped by the clear (row bits 37..45 or 37..47, block bit 2); red text = "
         "the offset label and the word removed", "none", C["gone"], True, False),
        ("orange arrow: block_to_rows, block 2 before -> block 2 after in (c) (1 block "
         "c = 2 -> geometry.n_kv_heads planes, 4 KiB each)", "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = block 2 after (c), rewritten row-major by this clear; "
         "red 'bits dropped' = block 2 after (b), its row bits 37..45 dropped"),
    ]
    return figure(fid, W, H, "Worked example of k_forget_row: a decode append at offset "
                  "46 and a new token at offset 37, before and after block 2 is converted",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
