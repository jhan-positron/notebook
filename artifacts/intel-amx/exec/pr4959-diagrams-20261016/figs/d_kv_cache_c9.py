"""Change diagrams of unit c9 of the kv_cache.hpp page (PR 4959): page copies
carry the bits with the rows (copy_storage_slot takes a k_storage_ref, copies
a whole page as one owner assignment, moves any other range through row-major
rows, and stores the two bit words once per slot).

Exposes figs() -> [HTML of "kv_cache-d9a", "kv_cache-d9b", "kv_cache-d9c"]
and BASE.
  d9a: the call path book::append -> copy_from -> copy_storage_slot and the
       k_storage_ref pairs copy_from builds (next to the removed signature).
  d9b: copy_storage_slot: the bit formula, the KV head loop with its two copy
       paths, and the release stores.
  d9c: the worked example: the 41 rows of page 7 right after the prefill
       copied to offsets 0..40 of an empty page 9.
Every label is an identifier or a comment phrase of the code; every box cites
the head line or Note that defines it (kv_cache.hpp at 6b081187e1). Line
numbers are head lines of kv_cache.hpp unless a file name is given.
"""
from svg_helpers import (C, arrow, bit_row, block_cell, cite, figure, fn_cell,
                         legend_chip, line, lines, marker_defs, rect, text,
                         text_width)
from base_kv_cache import caller_cell, fit

BASE = ("Updates B4: the 'page copies' note box at the foot of the sequencing "
        "model is opened into the call path with the k_storage_ref pairs (part a), "
        "the two copy paths of copy_storage_slot (a whole page = one owner "
        "assignment per KV head, bits included; any other range = block_to_rows, a "
        "row-by-row copy, block_to_vnni, with the new_saved bit formula and the "
        "release stores, part b), and the worked example copied to an empty page "
        "to show the bits before and after (part c).")

# ---- the worked example of a range copy (figure c) ---------------------------
# A page copy of the 41 saved rows of source page 7 right after the prefill
# pass (slot 5: offsets 0..40 saved, blocks 0 and 1 stored whole, block 2 with
# 9 row-major rows) into an empty page 9 at offset 0 (no row saved, no block
# bit): src_begin = 0, dst_begin = 0, count = 41. Not a whole page: the range
# path runs.
PAGE_SIZE = 64
SRC_SAVED = (1 << 41) - 1
SRC_BLOCKS = 0b0011
DST_SAVED = 0
DST_BLOCKS = 0
SRC_BEGIN, DST_BEGIN, COUNT = 0, 0, 41
W = 700


def _k_block_bits(c):
    """page::k_block_bits (kv_cache.hpp:2539-2543)."""
    return 0xffff << (c * 16)


def _copy_bits():
    """The bit arithmetic of copy_storage_slot (kv_cache.hpp:2732-2747,
    2769-2790) on the example; returns a dict of the results."""
    whole_page = SRC_BEGIN == 0 and DST_BEGIN == 0 and COUNT == PAGE_SIZE
    rng = (1 << 64) - 1 if COUNT == PAGE_SIZE else ((1 << COUNT) - 1) << DST_BEGIN
    new_saved = (DST_SAVED & ~rng) | (((SRC_SAVED >> SRC_BEGIN) << DST_BEGIN) & rng)
    new_blocks = DST_BLOCKS
    dst_end = DST_BEGIN + COUNT
    c_begin = DST_BEGIN // 16
    touched = [c for c in range(c_begin, 4) if c * 16 < dst_end]
    to_rows = [c for c in touched if DST_BLOCKS & (1 << c)]
    loads = [i for i in range(COUNT) if SRC_BLOCKS & (1 << ((SRC_BEGIN + i) // 16))]
    stores = [i for i in range(COUNT) if not SRC_BLOCKS & (1 << ((SRC_BEGIN + i) // 16))]
    to_vnni = [c for c in touched if (new_saved & _k_block_bits(c)) == _k_block_bits(c)]
    for c in to_vnni:
        new_blocks |= 1 << c
    return dict(whole_page=whole_page, rng=rng, new_saved=new_saved,
                new_blocks=new_blocks, touched=touched, to_rows=to_rows,
                loads=loads, stores=stores, to_vnni=to_vnni)


EX = _copy_bits()
assert not EX["whole_page"] and EX["new_saved"] == (1 << 41) - 1
assert EX["touched"] == [0, 1, 2] and EX["to_rows"] == []
assert EX["to_vnni"] == [0, 1] and EX["new_blocks"] == 0b0011
assert len(EX["loads"]) == 32 and len(EX["stores"]) == 9


def bits_str(word):
    """64 row bits as a '0'/'1' string, bit 0 first (bit_row order)."""
    return "".join("1" if word >> i & 1 else "0" for i in range(64))


# ---- local primitives --------------------------------------------------------
def step_box(x, y, w, h, title, sub, ref, fill, stroke, tag=None, mono_sub=False,
             size=10.5):
    """A sequence step: mono title, 1-3 description lines, citation lower
    right, optional tag at the lower left."""
    o = [rect(x, y, w, h, fill, stroke, 1.3, 4)]
    fit(title, size, w - 16, True, "step title")
    o.append(text(x + 8, y + 15, title, size, mono=True, weight=700))
    for s in sub:
        fit(s, 9, w - 16, mono_sub, "step sub")
    o.append(lines(x + 8, y + 29, sub, 9, 11.5, mono=mono_sub))
    if tag:
        col = C["new"] if tag.startswith("new") else (
            C["gone"] if tag.startswith("removed") else C["muted"])
        o.append(text(x + 8, y + h - 5, tag, 9, fill=col, weight=600))
    fit(ref, 8.5, w - 8, True, "step cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def how_many(x, y, s, color, anchor="start", maxw=440):
    """A 'how many' label of an arrow (bold, in the arrow's colour)."""
    fit(s, 9, maxw, False, "how_many")
    return text(x, y, s, 9, anchor, fill=color, weight=700)


def gone_box(x, y, w, h, line1, line2, ref):
    """Removed/old state: dashed red box, two lines, citation on its own line."""
    o = [rect(x, y, w, h, "#fff", C["gone"], 1.2, 4, "5 3")]
    fit(line1, 9, w - 16, True, "gone line1")
    o.append(text(x + 8, y + 14, line1, 9, mono=True, fill=C["gone"], weight=600))
    fit(line2, 9, w - 16, False, "gone line2")
    o.append(text(x + 8, y + 27, line2, 9, fill=C["gone"]))
    fit(ref, 8.5, w - 8, True, "gone cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def b4_note_box(o, boxes, y):
    """The 'page copies' note box of B4, reproduced as the thing parts a and b
    open (the same two sentences and citation as in B4)."""
    boxes.append(("page copies (the B4 note box this unit opens)", "kv_cache.hpp:753 (page copies carry both bit sets with the rows), 2760-2790"))
    return (rect(12, y, 676, 44, C["soft"], C["line"], 1, 4) +
            text(20, y + 14, "B4 note box:", 9, weight=700, fill=C["muted"]) +
            text(92, y + 14, "page copies (copy_storage_slot): a whole page keeps every "
                 "state (owner assignment, bits included);", 9) +
            text(20, y + 27, "any other range goes through row-major rows and re-converts "
                 "blocks whose 16 row bits are set", 9) +
            cite(684, y + 40, "kv_cache.hpp:2760-2790"))


# ---- figure a: the call path and the k_storage_ref pairs -----------------------
def fig_a():
    fid = "kv_cache-d9a"
    o = [marker_defs(fid, {"ink": C["ink"], "new": C["new"]})]
    boxes = []
    o.append(text(12, 18, "A page copy: book::append -> copy_from -> copy_storage_slot "
                  "[token tree, tree lock]", 12, weight=700))
    o.append(cite(12, 31, "kv_cache.hpp:1412-1441, 2814-2839, 2719-2812; thread: "
                  "2581-2582, 735-738", "start"))
    boxes.append(("[token tree, tree lock] (no forward pass reads the book meanwhile)",
                  "Note [K VNNI storage] kv_cache.hpp:735-738; kv_cache.hpp:2581-2582"))
    o.append(b4_note_box(o, boxes, 38))

    # ---- the call path (left column) and the k_storage_ref pairs (right) --------
    LX, LW = 12, 310
    RX, RW = 328, 362
    ax = LX + 40
    y = 94
    o.append(caller_cell(LX, y, LW, 50,
                         ["book::append (defrag), page-wise:",
                          "dst_pg->copy_from(src_pg, src_offset, dst_offset, count)"],
                         "kv_cache.hpp:1412-1441"))
    boxes.append(("book::append (caller)", "kv_cache.hpp:1412-1441; the copy_from call at 1440"))
    o.append(arrow(fid, "ink", [(ax, y + 50), (ax, y + 76)], C["ink"], 1.4))
    o.append(how_many(ax + 8, y + 62, "1 call per (src page, dst page) pair; a dst page",
                      C["ink"]))
    o.append(how_many(ax + 8, y + 73, "copies from at most 2 src pages [1433-1441]", C["ink"]))
    y = 172
    o.append(fn_cell(LX, y, LW, 62, "page::copy_from",
                     ["copies count-many tokens from src_page to this page,",
                      "starting at the given offsets (src_begin, dst_begin)"],
                     "kv_cache.hpp:2814-2839", "changed"))
    boxes.append(("page::copy_from", "kv_cache.hpp:2814-2839 (comment 2814)"))
    CS = 302                                   # where the copy_storage_slot cell sits
    o.append(arrow(fid, "ink", [(ax, y + 62), (ax, CS - 2)], C["ink"], 1.4))
    o.append(how_many(ax + 8, y + 76, "logical_slot_count() + has_eagle_storage() calls,",
                      C["ink"]))
    o.append(how_many(ax + 8, y + 87, "1 per k_storage_ref; then kv_saves_ per token", C["ink"]))
    o.append(cite(ax + 8, y + 98, "kv_cache.hpp:2819-2831; for_each_active_slot 1749-1755",
                  "start"))
    # right column: before (gone) and the two new pairs
    o.append(gone_box(RX, 94, RW, 46,
                      "before: copy_storage_slot(kv_storage_offset storage_offset, ...)",
                      "removed: the physical slot alone, no K layout state entry",
                      "kv_cache.hpp:2722 (base line of the diff)"))
    boxes.append(("copy_storage_slot(kv_storage_offset storage_offset, ...) (before, removed)",
                  "kv_cache.hpp:2722 (base line of the diff at the head signature)"))
    ny, nh = 148, 130
    o.append(rect(RX, ny, RW, nh, "#fff", C["new"], 1.3, 4))
    o.append(text(RX + 8, ny + 15, "k_storage_ref {offset, state_ix}", 10.5, mono=True,
                  weight=700))
    o.append(text(RX + RW - 8, ny + 15, "new", 9.5, "end", fill=C["new"], weight=700))
    pairs = [
        ("k_storage_ref{kv_storage_offset(slot), slot}",
         "every active slot (for_each_active_slot: slot < logical_slot_count())",
         "kv_cache.hpp:2819-2821"),
        ("k_storage_ref{book.eagle_storage_offset(), layout_t::n_slots}",
         "the EAGLE storage, when book.has_eagle_storage()",
         "kv_cache.hpp:2828-2831"),
    ]
    py = ny + 30
    for nm, ds, rf in pairs:
        fit(nm, 9.5, RW - 12, True, "pair name")
        o.append(text(RX + 8, py, nm, 9.5, mono=True, weight=600, fill=C["new"]))
        fit(ds, 9, RW - 16, False, "pair desc")
        o.append(text(RX + 8, py + 12, ds, 9))
        o.append(cite(RX + 8, py + 23, rf, "start"))
        py += 36
    o.append(lines(RX + 8, py + 2, ["built from the physical slot, not through k_storage_of:",
                                    "a page copy moves every physical slot"], 9, 11,
                   fill=C["muted"]))
    o.append(cite(RX + RW - 4, ny + nh - 4, "kv_cache.hpp:2185-2196, 2188-2189"))
    boxes.append(("k_storage_ref (the pair copy_from builds per physical slot)",
                  "kv_cache.hpp:2185-2196; built at 2820 and 2830; why: 2188-2189"))
    boxes.append(("EAGLE storage (eagle_storage_offset, entry layout_t::n_slots)",
                  "kv_cache.hpp:1140-1144; entry 2523, 2528-2529"))
    # the pairs feed copy_storage_slot (part b)
    o.append(arrow(fid, "new", [(RX + 60, ny + nh), (RX + 60, CS - 2)], C["new"], 1.4))
    o.append(how_many(RX + 68, ny + nh + 15, "1 pair -> 1 call", C["new"]))
    o.append(fn_cell(12, CS, 676, 58,
                     "copy_storage_slot<geometry>(k_storage_ref storage, src_page, "
                     "src_begin, dst_begin, count)",
                     ["copies count K/V tokens of one storage slot from src_page; the K "
                      "bits of the copied offsets follow the rows (part b)"],
                     "kv_cache.hpp:2719-2812", "changed"))
    boxes.append(("page::copy_storage_slot (the callee: part b)",
                  "kv_cache.hpp:2719-2812 (comment 2719-2720)"))
    H = CS + 70
    cap = ("Updates B4 (part a): the 'page copies' note box of the sequencing model "
           "(reproduced at the top), opened into the call path. Look at the right column "
           "first. copy_from now "
           "hands one k_storage_ref per physical slot, and the EAGLE storage gets entry "
           "layout_t::n_slots. The removed signature took a storage offset alone. "
           "Every pair is one copy_storage_slot call (part b).")
    legend = [
        ("box", "white box, ink outline: the function cells page::copy_from and "
                "copy_storage_slot (name in bold monospace, description in sans-serif), "
                "and the new k_storage_ref {offset, state_ix} box with the two pairs "
                "copy_from builds"),
        ("ctx", "grey box, thin grey outline: the B4 note box repeated at the top, and the "
                "caller book::append (defrag)"),
        ("gone", "red dashed box, red text: the removed signature "
                 "copy_storage_slot(kv_storage_offset storage_offset, ...), the base line "
                 "of the diff"),
        ("arrow", "ink arrow = a call: book::append -> copy_from -> copy_storage_slot, and "
                  "1 k_storage_ref pair -> 1 copy_storage_slot call; its label says how "
                  "many"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR (the k_storage_ref pairs); 'changed' = "
                     "changed by it (copy_from, copy_storage_slot)"),
    ]
    return figure(fid, W, H, "A page copy (part a): copy_from and the k_storage_ref pairs",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- figure b: copy_storage_slot, the two copy paths ---------------------------
def fig_b():
    fid = "kv_cache-d9b"
    o = [marker_defs(fid, {"ink": C["ink"], "new": C["new"]})]
    boxes = []
    o.append(text(12, 16, "copy_storage_slot: one storage slot, the bits and the two copy "
                  "paths [token tree, tree lock]", 12, weight=700))
    o.append(how_many(12, 30, "from part a: 1 k_storage_ref pair -> 1 call", C["new"]))
    o.append(b4_note_box(o, boxes, 36))
    CS = 90                                    # top of the copy_storage_slot cell
    o.append(fn_cell(12, CS, 676, 60,
                     "copy_storage_slot<geometry>(k_storage_ref storage, src_page, "
                     "src_begin, dst_begin, count)",
                     ["copies count K/V tokens of one storage slot from src_page into this "
                      "page; storage = the storage slot copied and its",
                      "K layout state entry; the K bits of the copied offsets follow the rows "
                      "(storage.offset, storage.state_ix)"],
                     "kv_cache.hpp:2719-2812", "changed"))
    boxes.append(("page::copy_storage_slot", "kv_cache.hpp:2719-2812 (comment 2719-2720)"))
    # VNNI geometry band
    by = CS + 70
    o.append(rect(12, by, 676, 28, C["vnni_fill"], C["vnni"], 1, 3))
    o.append(text(18, by + 12, "VNNI geometry: if constexpr (k_vnni::layout_on<geometry.head_size>)",
                  9.5, mono=True, weight=700))
    o.append(text(18, by + 23, "static_assert(page_size == k_vnni::PAGE_TOKENS_64); "
                  "TRON_ASSERT(count != 0, \"copy_storage_slot: empty range\")", 8.5, mono=True))
    o.append(cite(684, by + 12, "kv_cache.hpp:2735-2737"))
    boxes.append(("k_vnni::layout_on<geometry.head_size> (the VNNI geometry gate)",
                  "tensor/k_vnni.hpp:115-123; used at kv_cache.hpp:2735, 2750, 2808"))
    # step 0: the bits
    sy = by + 36
    o.append(step_box(12, sy, 676, 68,
                      "load both pages' bits (acquire), compute new_saved once per slot",
                      ["src_saved, src_blocks <- src_page->k_rows_saved_[state_ix], "
                       "k_vnni_blocks_[state_ix]; dst_saved, dst_blocks <- this page",
                       "range = count == page_size ? ~uint64_t{} : (offset_bit(count) - 1) "
                       "<< dst_begin",
                       "new_saved = (dst_saved & ~range) | (((src_saved >> src_begin) "
                       "<< dst_begin) & range);  new_blocks = dst_blocks"],
                      "kv_cache.hpp:2729-2748", C["soft"], C["line"], "new",
                      mono_sub=True))
    # the step touches both arrays: neutral box, the two array names in their colours
    o.append(text(596, sy + 15, "k_rows_saved_", 9, "end", True, fill=C["rows"], weight=700))
    o.append(text(680, sy + 15, "k_vnni_blocks_", 9, "end", True, fill=C["blk"], weight=700))
    boxes.append(("src_saved / dst_saved / new_saved (k_rows_saved_ words, acquire loads)",
                  "kv_cache.hpp:2732, 2738-2746"))
    boxes.append(("src_blocks / dst_blocks / new_blocks (k_vnni_blocks_ bytes)",
                  "kv_cache.hpp:2733, 2739-2741, 2747"))
    # the KV head loop frame
    fy = sy + 76
    wy = fy + 58
    STEP_H, STEP_GAP = 58, 16
    steps_end = wy + 18 + 3 * STEP_H + 2 * STEP_GAP
    ey = steps_end + 32
    fh = ey + 40 + 8 - fy
    o.append(rect(12, fy, 676, fh, C["soft"], C["line"], 1, 5))
    o.append(text(20, fy + 14, "for (kv_head < geometry.n_kv_heads)", 10, mono=True,
                  weight=700))
    o.append(cite(684, fy + 14, "kv_cache.hpp:2749, 742-743"))
    o.append(how_many(20, fy + 27, "1 call -> geometry.n_kv_heads KV heads; the bits are per "
                      "slot, shared by every head of the slot", C["ink"], maxw=660))
    boxes.append(("kv_head < geometry.n_kv_heads (the KV head loop)", "kv_cache.hpp:2749"))
    # the fork inside the loop: whole_page (left box) or else (the three steps)
    FL, FR = 129, 490
    o.append(line(350, fy + 34, 350, fy + 42, C["ink"], 1.4))
    o.append(line(FL, fy + 42, FR, fy + 42, C["ink"], 1.4))
    o.append(arrow(fid, "ink", [(FL, fy + 42), (FL, wy - 2)], C["ink"], 1.4))
    o.append(arrow(fid, "ink", [(FR, fy + 42), (FR, wy - 2)], C["ink"], 1.4))
    o.append(text(FL + 8, fy + 52, "whole_page", 9, mono=True, weight=700))
    o.append(text(FR + 8, fy + 52, "else", 9, mono=True, weight=700))
    # left: whole page
    wx, ww, wh = 22, 214, steps_end - wy
    o.append(rect(wx, wy, ww, wh, C["vnni_fill"], C["vnni"], 1.4, 4))
    o.append(text(wx + 8, wy + 15, "whole_page", 10.5, mono=True, weight=700))
    wl1 = ["src_begin == 0 && dst_begin == 0", "&& count == page_size"]
    wl2 = ["dst_block.k = src_block.k", "new_blocks = src_blocks"]
    wl3 = ["1 KV head -> 1 owner assignment:", "the defaulted copy of the trivially",
           "copyable k_vnni_tensor, the whole", "16 KiB plane; every token keeps its",
           "offset, so its column is unchanged"]
    for s in wl1 + wl2:
        fit(s, 9.5, ww - 16, True, "whole page mono")
    for s in wl3:
        fit(s, 9, ww - 16, False, "whole page")
    o.append(lines(wx + 8, wy + 29, wl1, 9, 11, mono=True))
    o.append(lines(wx + 8, wy + 62, wl2, 9.5, 12, mono=True, weight=700))
    o.append(lines(wx + 8, wy + 99, wl3, 9, 11))
    o.append(cite(wx + ww - 4, wy + wh - 4, "kv_cache.hpp:2734, 2760-2762"))
    boxes.append(("whole_page (src_begin == 0 && dst_begin == 0 && count == page_size)",
                  "kv_cache.hpp:2734"))
    boxes.append(("dst_block.k = src_block.k (one owner assignment per KV head)",
                  "kv_cache.hpp:2760-2762; k_vnni_tensor comment tensor/k_vnni.hpp:184-186; "
                  "Note [K VNNI storage] item 5, kv_cache.hpp:839-841"))
    # right: any other range, three steps
    rx, rw = 248, 430
    o.append(text(rx, wy + 12, "else: any other range, in this order", 9.5, weight=700))
    o.append(cite(rx + rw, wy + 12, "kv_cache.hpp:2763-2768, 839-846"))
    boxes.append(("c_begin .. (dst_end - 1) / 16: the destination blocks any other range "
                  "touches", "kv_cache.hpp:2766-2768"))
    st = [
        ("1  block_to_rows(dst_plane, c)",
         ["touched dst blocks c_begin .. (dst_end - 1) / 16 whose dst_blocks bit is",
          "set: back to row-major first; new_blocks &= ~block_bit(c)"],
         "kv_cache.hpp:2769-2774; k_vnni.hpp:478-491", C["rm_fill"], C["rm"]),
        ("2  i < count: load_row | store_row_major",
         ["src block bit set: load_row (4 gathers) | clear: store_row_major",
          "(memcpy), into row_major_row(dst_plane, dst_begin + i)"],
         "kv_cache.hpp:2775-2784; k_vnni.hpp:333-345, 441-449", "#fff", C["ink"]),
        ("3  block_to_vnni(dst_plane, c)",
         ["touched dst blocks with (new_saved & k_block_bits(c)) == k_block_bits(c):",
          "converted at once (no reader runs); new_blocks |= block_bit(c)"],
         "kv_cache.hpp:2785-2790; k_vnni.hpp:461-476", C["vnni_fill"], C["vnni"]),
    ]
    ty = wy + 18
    for i, (title, sub, ref, fill, stroke) in enumerate(st):
        o.append(step_box(rx, ty, rw, STEP_H, title, sub, ref, fill, stroke))
        if i < len(st) - 1:
            # "then": the steps run in this order, one after the other
            o.append(arrow(fid, "ink", [(rx + 24, ty + STEP_H + 1),
                                        (rx + 24, ty + STEP_H + STEP_GAP - 1)], C["ink"], 1.3))
            o.append(text(rx + 32, ty + STEP_H + 11, "then", 8.5, fill=C["ink"]))
        ty += STEP_H + STEP_GAP
    o.append(how_many(rx, steps_end + 12, "1 KV head -> count rows, token by token through "
                      "row-major rows;", C["ink"]))
    o.append(how_many(rx, steps_end + 23, "touched blocks: c_begin = dst_begin / 16 .. "
                      "(dst_end - 1) / 16", C["ink"]))
    boxes.append(("block_to_rows (step 1)", "kv_cache.hpp:2769-2774; tensor/k_vnni.hpp:478-491"))
    boxes.append(("load_row | store_row_major into row_major_row (step 2)",
                  "kv_cache.hpp:2775-2784; tensor/k_vnni.hpp:333-345, 425-437, 441-449"))
    boxes.append(("block_to_vnni (step 3)", "kv_cache.hpp:2785-2790; tensor/k_vnni.hpp:461-476"))
    # row-major geometry and V (inside the loop)
    o.append(rect(22, ey, 322, 40, "#fff", C["muted"], 1, 4))
    o.append(text(30, ey + 14, "else (row-major geometry): memcpy per KV head", 9.5,
                  mono=True, weight=600, fill=C["muted"]))
    o.append(text(30, ey + 27, "count * head_size bf16 from k_at(src_begin); no bits", 9,
                  fill=C["muted"]))
    o.append(cite(340, ey + 36, "kv_cache.hpp:2792-2802"))
    boxes.append(("memcpy per KV head (the row-major geometry, unchanged bytes path)",
                  "kv_cache.hpp:2792-2802"))
    o.append(rect(356, ey, 322, 40, "#fff", C["muted"], 1, 4))
    o.append(text(364, ey + 14, "append_v per token (V, unchanged)", 9.5, mono=True,
                  weight=600, fill=C["muted"]))
    o.append(text(364, ey + 27, "count calls per KV head: copy_token of the V plane", 9,
                  fill=C["muted"]))
    o.append(cite(674, ey + 36, "kv_cache.hpp:2804-2806, 2705-2717"))
    boxes.append(("append_v (V copy, unchanged)", "kv_cache.hpp:2705-2717; call 2804-2806"))
    # after the loop: the release stores
    ry = fy + fh + 10
    o.append(step_box(12, ry, 676, 60, "after the last KV head: 2 release stores",
                      ["k_rows_saved_[state_ix].store(new_saved, release); "
                       "k_vnni_blocks_[state_ix].store(new_blocks, release)",
                       "1 slot -> 2 words stored once; a reader must not see the block bit "
                       "before every head holds the layout"],
                      "kv_cache.hpp:2808-2811, 742-743", C["soft"], C["line"], "new"))
    o.append(text(596, ry + 15, "k_rows_saved_", 9, "end", True, fill=C["rows"], weight=700))
    o.append(text(680, ry + 15, "k_vnni_blocks_", 9, "end", True, fill=C["blk"], weight=700))
    boxes.append(("k_rows_saved_[state_ix] / k_vnni_blocks_[state_ix] release stores",
                  "kv_cache.hpp:2808-2811; why once per slot: 2731, 742-743"))
    # before: copy_token per token for the VNNI geometry
    gy = ry + 68
    o.append(gone_box(12, gy, 676, 48,
                      "before: copy_token(dst_block.k.as_view(), dst_begin + i, "
                      "src_block.k.as_view(), src_begin + i) per token, no bits",
                      "removed: the VNNI geometry copied tokens through their VNNI columns "
                      "(PR 4956); now rows go through row-major rows and the bits follow",
                      "kv_cache.hpp:2776 (base lines of the diff); 839-846"))
    boxes.append(("copy_token per token for the VNNI geometry (before, removed)",
                  "base lines of the diff hunk at head kv_cache.hpp:2775-2784; why: Note "
                  "[K VNNI storage] item 5, kv_cache.hpp:839-846"))
    H = gy + 48 + 10
    cap = ("Updates B4 (part b): the two copy paths of copy_storage_slot. Inside the KV "
           "head loop a whole page is one owner assignment per head with the source's "
           "block bits, and any other range runs the three steps block_to_rows, row "
           "copy, block_to_vnni. new_saved is computed once before the loop. Both words "
           "are stored with release order after the last head. The removed base code "
           "copied every token of a range through its VNNI column with copy_token.")
    legend = [
        ("box", "white box, ink outline: the function cell copy_storage_slot (name in bold "
                "monospace, description in sans-serif), and step 2 of the range path, the "
                "row copy load_row | store_row_major"),
        ("ctx", "grey box, thin grey outline: the B4 note box, and the steps of "
                "copy_storage_slot that belong to neither layout path: the bit loads and "
                "new_saved, the for (kv_head) loop frame, the two release stores"),
        ("vnni", "blue: the VNNI geometry gate k_vnni::layout_on, the whole_page path (one "
                 "owner assignment of the k_vnni_tensor plane per KV head), and step 3, "
                 "block_to_vnni"),
        ("rm", "orange: step 1, block_to_rows (a touched destination block back to "
               "row-major rows)"),
        ("grey outline, grey text: the loop paths this PR leaves unchanged, memcpy per KV "
         "head (row-major geometry) and append_v per token (V)",
         "#fff", C["muted"], False, False),
        ("gone", "red dashed box, red text: the removed loop body of the VNNI geometry, "
                 "copy_token per token (base lines of the diff)"),
        ("green labels: k_rows_saved_, the saved-row word the bit step loads and the "
         "release step stores", "text", C["rows"]),
        ("pink labels: k_vnni_blocks_, the converted-block word the bit step loads and "
         "the release step stores", "text", C["blk"]),
        ("arrow", "ink arrow: the fork of the KV head loop (whole_page | else), and 'then' "
                  "between the three steps of the range path"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR (the bit step, the release stores); "
                     "'changed' = changed by it (copy_storage_slot)"),
    ]
    return figure(fid, W, H, "A page copy (part b): the two paths of copy_storage_slot",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- figure c: the worked example copied to an empty page ---------------------
CELL, GAP, GGAP = 6, 1, 6
PITCH = 16 * (CELL + GAP) + GGAP          # one 16-token block of bits = 118 px
BX = 150                                  # x where bit 0 starts


def bit_x(i):
    """Left x of row bit i."""
    return BX + i * (CELL + GAP) + (i // 16) * GGAP


def page_band(o, y, title, saved, blocks, states, words, ref, bracket=None):
    """One page state: title, the 64 row bits, the 4 block bits, the 4 block
    cells with a word under each. Returns the y under the band."""
    fit(title, 10.5, 676, False, "band title")
    o.append(text(12, y, title, 10.5, weight=700))
    ry = y + 9
    o.append(text(12, ry + 7, "k_rows_saved_[5]", 10, mono=True, fill=C["rows"]))
    body, _ = bit_row(BX, ry, bits_str(saved), CELL, GAP, C["rows_fill"], C["rows"],
                      group=16, group_gap=GGAP)
    o.append(body)
    n_set = bin(saved).count("1")
    o.append(text(bit_x(63) + CELL + 6, ry + 7, f"{n_set} set", 8.5, fill=C["rows"]))
    by = ry + 14
    if bracket:
        a, b, lab = bracket
        xa, xb = bit_x(a), bit_x(b) + CELL
        o.append(line(xa, by + 3, xb, by + 3, C["ink"], 1.2))
        o.append(line(xa, by, xa, by + 3, C["ink"], 1.2))
        o.append(line(xb, by, xb, by + 3, C["ink"], 1.2))
        fit(lab, 8.5, 460, False, "bracket")
        o.append(text((xa + xb) / 2, by + 13, lab, 8.5, "middle", weight=600))
        by += 18
    o.append(text(12, by + 9, "k_vnni_blocks_[5]", 10, mono=True, fill=C["blk"]))
    for c in range(4):
        gx = bit_x(16 * c)
        on = blocks >> c & 1
        o.append(rect(gx, by, 10, 10, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(text(gx + 14, by + 9, f"bit {c}: {'set' if on else 'clear'}", 8.5,
                      fill=C["muted"]))
    cy = by + 16
    bw = PITCH - 7
    for c in range(4):
        gx = bit_x(16 * c)
        o.append(block_cell(gx, cy, bw, 26, states[c], f"block {c}: {16 * c}..{16 * c + 15}", 9))
        fit(words[c], 8.5, bw + 4, False, "band word")
        o.append(text(gx + bw / 2, cy + 38, words[c], 8.5, "middle", fill=C["muted"]))
    o.append(cite(bit_x(63) + CELL, cy + 50, ref))
    return cy + 54


def fig_c():
    fid = "kv_cache-d9c"
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    STYLE = "worked example of B1 (section 1), right after the prefill pass"
    o.append(text(12, 18, "worked example: the 41 rows of page 7 (slot 5, after the "
                  "prefill) copied to an empty page 9", 11, weight=700))
    o.append(text(12, 32, "copy_storage_slot(k_storage_ref{kv_storage_offset(5), 5}, src_page, "
                  "src_begin = 0, dst_begin = 0, count = 41);", 9.5, mono=True))
    o.append(text(12, 44, "whole_page = false (count != page_size): the range path runs, "
                  "even at offset 0", 9.5, mono=True))
    o.append(cite(12, 56, "kv_cache.hpp:2734, 2763; book::append 1433-1441 (count = "
                  "min(page_size - dst_offset, page_size - src_offset, src_end - src_begin))",
                  "start"))
    boxes.append(("copy_storage_slot(k_storage_ref{kv_storage_offset(5), 5}, src_page, 0, "
                  "0, 41): the copy call of the example",
                  "kv_cache.hpp:2721-2726 (copy_storage_slot signature); 1433-1441 "
                  "(book::append page-wise loop); 2820 (the pair)"))
    # ---- source page (the worked example of B1 right after the prefill) --------
    y = page_band(o, 74, "source page 7, slot 5 right after the prefill: offsets 0..40 "
                  "saved, blocks 0 and 1 stored whole",
                  SRC_SAVED, SRC_BLOCKS, ["vnni", "vnni", "rm", "empty"],
                  ["VNNI (whole-block save)", "VNNI (whole-block save)", "9 rows, row-major",
                   "no row saved"], "kv_cache.hpp:2639-2653; " + STYLE,
                  bracket=(0, 40, "src_begin = 0, count = 41: src_saved >> 0, offsets 0..40"))
    boxes.append(("k_rows_saved_[5], k_vnni_blocks_[5] of the source page (the worked "
                  "example of B1 right after the prefill)", "kv_cache.hpp:2639-2653; " + STYLE))
    # ---- destination page before -----------------------------------------------
    y = page_band(o, y + 8, "destination page 9 before: empty, no row saved, no block bit; "
                  "the fresh range starts at dst_begin = 0",
                  DST_SAVED, DST_BLOCKS, ["empty", "empty", "empty", "empty"],
                  ["no row saved", "no row saved", "no row saved", "no row saved"],
                  "kv_cache.hpp:2732-2733, 2738-2741",
                  bracket=(0, 40, "range = offset_bit(41) - 1: offsets 0..40 are "
                           "replaced"))
    boxes.append(("dst_saved = 0, dst_blocks = 0: the destination page before",
                  "kv_cache.hpp:2732-2733 (declared), 2738-2741 (loaded)"))
    # ---- the copy, per KV head ----------------------------------------------------
    cy = y + 6
    rows_ = [
        (C["rm"], "1  block_to_rows: none (dst_blocks = 0: no touched block is converted)",
         "kv_cache.hpp:2769-2774"),
        (C["rm"], "    touched blocks: c_begin = 0 / 16 = 0 .. 2 (c * 16 < dst_end = 41)",
         "kv_cache.hpp:2766-2768"),
        (C["ink"], "2  i = 0..31 (src blocks 0, 1, bits set): load_row x 32 (4 gathers "
                   "each) into row_major_row(dst_plane, i)", "kv_cache.hpp:2775-2779"),
        (C["ink"], "    i = 32..40 (src block 2, bit clear): store_row_major x 9 "
                   "into offsets 32..40", "kv_cache.hpp:2780-2783"),
        (C["vnni"], "3  block_to_vnni(dst_plane, c) for c = 0, 1: new_saved holds "
                    "their 16 bits", "kv_cache.hpp:2785-2790"),
        (C["vnni"], "    c = 2 holds 9 of 16 (offsets 32..40): stays row-major",
         "kv_cache.hpp:2786"),
        (C["muted"], "    then append_v x 41 (V, unchanged); after the last KV head the two "
                     "release stores", "kv_cache.hpp:2804-2811"),
    ]
    bh = 32 + 17 * len(rows_)
    o.append(rect(12, cy, 676, bh, C["soft"], C["line"], 1, 5))
    o.append(text(20, cy + 14, "per KV head (1 call -> geometry.n_kv_heads heads), in this "
                  "order:", 10, weight=700))
    o.append(cite(684, cy + 14, "kv_cache.hpp:2749"))
    ty = cy + 32
    for col, s, rf in rows_:
        fit(s, 9, 530, False, "copy row")
        o.append(text(20, ty, s, 9, fill=col, weight=600 if col != C["muted"] else None))
        o.append(cite(684, ty, rf))
        ty += 17
    boxes.append(("block_to_rows (none), load_row x 32, store_row_major x 9, block_to_vnni "
                  "c = 0, 1 (the three steps on the example)",
                  "kv_cache.hpp:2766-2790; tensor/k_vnni.hpp:333-345, 441-449, 461-476"))
    # ---- destination page after ---------------------------------------------------
    y = page_band(o, cy + bh + 20, "destination page 9 after: new_saved = bits 0..40 (41 rows), "
                  "new_blocks = block_bit(0) | block_bit(1) = 0b0011",
                  EX["new_saved"], EX["new_blocks"], ["vnni", "vnni", "rm", "empty"],
                  ["converted in the copy", "converted in the copy", "9 rows, row-major",
                   "no row saved"],
                  "kv_cache.hpp:2742-2747, 2785-2790, 2808-2811",
                  bracket=(0, 40, "the same 41 rows at the same offsets: dst_begin - "
                           "src_begin = 0"))
    boxes.append(("new_saved, new_blocks of the destination page after (stored with release)",
                  "kv_cache.hpp:2742-2747 (new_saved), 2785-2790 (new_blocks), 2808-2811 "
                  "(the stores)"))
    # ---- the formula and the notes ------------------------------------------------
    fy = y + 4
    o.append(rect(12, fy, 676, 58, C["rows_fill"], C["rows"], 1.2, 4))
    fl = [
        "range     = (offset_bit(41) - 1) << 0                                = bits 0..40",
        "new_saved = (dst_saved & ~range) | (((src_saved >> 0) << 0) & range) = 0 | "
        "bits 0..40 = bits 0..40",
        "new_blocks: dst_blocks = 0, then |= block_bit(c) for c = 0, 1 at step 3        "
        "= 0b0011",
    ]
    for s in fl:
        fit(s, 9, 660, True, "formula")
    o.append(lines(20, fy + 15, fl, 9, 13, mono=True))
    o.append(cite(684, fy + 54, "kv_cache.hpp:2742-2747, 2772, 2788"))
    boxes.append(("new_saved formula on the example", "kv_cache.hpp:2742-2746"))
    ny = fy + 72
    notes = [
        "The source state is B1 five decode steps earlier (offsets 41..45 not yet saved). "
        "Blocks complete after the copy",
        "convert inside the copy [token tree, tree lock]: no forward pass reads",
        "the book, so the forward-end wait of B4 does not apply [kv_cache.hpp:735-738, "
        "2785-2790].",
        "The 32 rows of the converted source blocks are read with load_row (4 gathers each) "
        "and written row-major,",
        "then converted again: a range copy never copies a VNNI column as such, even when "
        "the offsets match [2751-2756].",
        "A whole-page copy (src_begin = 0, dst_begin = 0, count = 64) would instead copy the "
        "owner, bits included,",
        "and skip the three steps [kv_cache.hpp:2760-2762].",
    ]
    for s in notes:
        fit(s, 9, 676, False, "note")
    o.append(lines(12, ny, notes, 9, 12, fill=C["ink"]))
    # legend
    ly = ny + 90
    lx = 12
    for st, lab in [("vnni", "converted block: VNNI layout"),
                    ("rm", "row-major rows"), ("empty", "no row saved")]:
        o.append(legend_chip(lx, ly, st, lab))
        lx += 32 + text_width(lab, 11) + 16
    o.append(rect(12, ly + 22, 10, 10, C["rows_fill"], C["rows"], 1, 1))
    o.append(text(27, ly + 31, "k_rows_saved_ bit set", 10))
    o.append(rect(172, ly + 22, 10, 10, C["blk_fill"], C["blk"], 1, 1))
    o.append(text(187, ly + 31, "k_vnni_blocks_ bit set", 10))
    o.append(rect(337, ly + 22, 10, 10, C["empty_fill"], C["empty"], 1, 1))
    o.append(text(352, ly + 31, "bit clear; bit 0 at the left", 10))
    H = ly + 44
    cap = ("Updates B4 (part c, worked example): the range path of copy_storage_slot run "
           "on the worked example right after the prefill pass, copied to offsets 0..40 "
           "of an empty page 9. Look at the brackets: the 41 source row bits land at the "
           "same offsets of the destination word. Any range that is not a whole page "
           "moves row by row through row-major rows, whatever the alignment "
           "[kv_cache.hpp:2734, 2751-2756]: here 32 load_row calls (4 gathers each) from "
           "the two converted source blocks and 9 memcpy rows from block 2. Destination "
           "blocks 0 and 1 then hold 16 row bits each and are converted in the copy "
           "itself, and block 2 keeps its 9 rows row-major.")
    legend = [
        ("rows", "green: k_rows_saved_[5], a saved-row bit that is set (one square per page "
                 "offset, bit 0 at the left), its label and count, and the new_saved "
                 "formula box"),
        ("blk", "pink: k_vnni_blocks_[5], a converted-block bit that is set (one square per "
                "16-token block), and its label"),
        ("bit_clear", "white square, grey outline: a row bit or a block bit that is clear"),
        ("vnni", "blue: a converted block (source blocks 0 and 1; destination blocks 0 and 1 "
                 "after the copy), and the step 3 lines, block_to_vnni"),
        ("rm", "orange: row-major rows (source block 2, destination block 2 after the copy), "
               "and the step 1 lines, block_to_rows"),
        ("empty", "grey dashed: no row saved (source block 3; every destination block "
                  "before the copy; destination block 3 after it)"),
        ("ctx", "grey box, thin grey outline: the per-KV-head steps of the copy in order; "
                "step 1 lines in orange, step 2 in ink, step 3 in blue"),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Worked example: a range copy carries the bits and re-converts "
                  "the completed destination blocks", "".join(o), cap, boxes=boxes,
                  legend=legend)


def figs():
    return [fig_a(), fig_b(), fig_c()]
