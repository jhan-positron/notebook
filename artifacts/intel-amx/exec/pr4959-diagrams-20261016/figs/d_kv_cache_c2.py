"""Change diagrams of unit c2 (kv_cache.hpp, PR 4959): which state entry and
which storage slot a call means (book::eagle_view_active, k_state_ix,
k_storage_ref / k_storage_of, k_with_storage_geometry). Two figures: d2a = the
map a call follows under each storage view; d2b = who builds, keeps and takes
the pair, and the geometry of a storage slot.

Updates B1: B1 draws one arrow kv_slot_id -> k_storage_ref and the box
book::eagle_view_active; these figures expand them.

Every label is an identifier or a comment phrase of kv_cache.hpp (head line
numbers at 6b081187e1) or of model.hpp / common.hpp / attention_ids.hpp.
"""
from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, lines,
                         marker_defs, rect, text)
from base_kv_cache import EXAMPLE, HI_FILL, fit

BASE = ("Updates B1: expands B1's kv_slot_id -> k_storage_ref arrow and its "
        "book::eagle_view_active box into the logical slot -> state entry -> "
        "storage slot map that k_state_ix and k_storage_of compute under the "
        "primary view and under the EAGLE view, and adds who builds, keeps and "
        "takes the pair and the geometry choice of k_with_storage_geometry.")

W = 720

# ---- the cell columns of one panel (offset inside the panel, width) ----------
# columns: slot 0 | slot 5 | ... | slot n-1 | n_slots (the EAGLE entry / storage)
COLS = [(0, 36), (38, 36), (76, 18), (96, 46), (144, 46)]
PANEL_W = 340
PANEL_H = 294
CELL_H = 26
CELLS_X = 8          # cells start at panel x + 8
LABEL_X = 202        # the right-hand label column starts at panel x + 202
LABEL_W = PANEL_W - LABEL_X - 6


def note_box(x, y, w, h, title, body, ref, stroke=C["ink"], fill="#fff",
             dash=None, tag=None, size=9):
    """A box with a mono title line, small sans body lines and a citation.
    Height: 46 for one body line, 56 for two, 70 for three."""
    o = [rect(x, y, w, h, fill, stroke, 1.2, 4, dash)]
    fit(title, 10, w - 16 - (30 if tag else 0), True, "note_box title")
    o.append(text(x + 8, y + 14, title, 10, mono=True, weight=700))
    for s in body:
        fit(s, size, w - 16, False, "note_box body")
    o.append(lines(x + 8, y + 27, body, size, 11))
    if tag:
        o.append(text(x + w - 8, y + 14, tag, 9, "end", fill=C["new"], weight=700))
    fit(ref, 8.5, w - 8, True, "note_box cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def cell(x, y, w, label, hi=False, eagle=False, dashed=False):
    """One slot / entry cell in the B1 style: ink outline, the worked example
    (slot 5) filled, the EAGLE column in the EAGLE colours, dashed = this view
    does not reach it through k_state_ix."""
    if eagle:
        fill, stroke = C["eagle_fill"], C["eagle"]
    elif hi:
        fill, stroke = HI_FILL, C["ink"]
    else:
        fill, stroke = "#fff", C["ink"]
    if dashed:
        fill, stroke = C["empty_fill"], C["empty"]
    o = [rect(x, y, w, CELL_H, fill, stroke, 1.6 if hi and not dashed else 1, 3,
              "3 2" if dashed else None)]
    fit(label, 9.5, w, True, "cell")
    o.append(text(x + w / 2, y + 17, label, 9.5, "middle", True,
                  fill=C["muted"] if dashed else None, weight=700 if hi else None))
    return "".join(o)


def cell_row(px, y, labels, hi_col, eagle_col, dashed_cols):
    """labels[i] for column i (None = no cell)."""
    o = []
    for i, (dx, w) in enumerate(COLS):
        if labels[i] is None:
            continue
        o.append(cell(px + CELLS_X + dx, y, w, labels[i], hi=(i == hi_col),
                      eagle=(i == eagle_col), dashed=(i in dashed_cols)))
    return "".join(o)


def col_cx(px, i):
    dx, w = COLS[i]
    return px + CELLS_X + dx + w / 2


def side_text(px, yc, items, color=C["ink"]):
    """The right-hand label column: items = [(string, size, mono, weight)],
    vertically centred on yc, 10 px per line. A mono 8.5 line is a citation."""
    n = len(items)
    y = yc - (n - 1) * 5 + 3.5
    o = []
    for s, size, mono, weight in items:
        fit(s, size, LABEL_W, mono, "side_text")
        if size == 8.5 and mono:
            o.append(cite(px + LABEL_X, y, s, "start"))
        else:
            o.append(text(px + LABEL_X, y, s, size, mono=mono, weight=weight,
                          fill=color if weight else C["ink"]))
        y += 10
    return "".join(o)


def panel(fid, px, top, eagle_view):
    """One storage view: three rows of cells and the arrows of k_state_ix and
    k_storage_of between them. Returns svg."""
    o = []
    y1, y2, y3 = top + 32, top + 122, top + 212
    o.append(rect(px, top, PANEL_W, PANEL_H, C["soft"], C["line"], 1, 4))
    # row 1: logical slots
    o.append(cell_row(px, y1, ["slot 0", "slot 5", "...", "slot n-1", None], 1, -1, []))
    o.append(side_text(px, y1 + 13, [("logical slot", 9, False, 600),
                                     ("kv_slot_id", 9, True, None),
                                     ("attention_ids.hpp:23", 8.5, True, None)]))
    # row 2: state entries
    dashed = [0] if eagle_view else [4]
    o.append(cell_row(px, y2, ["0", "5", "...", "n-1", "n_slots"], 1, 4, dashed))
    o.append(side_text(px, y2 + 13, [("state entry ix", 9, False, 600),
                                     ("k_rows_saved_[ix]", 8.5, True, None),
                                     ("k_vnni_blocks_[ix]", 8.5, True, None),
                                     ("kv_cache.hpp:2639-2653", 8.5, True, None)]))
    # row 3: storage slots
    o.append(cell_row(px, y3, ["slot 0", "slot 5", "...", "slot n-1", "EAGLE"], 1, 4,
                      dashed))
    o.append(side_text(px, y3 + 13, [("storage slot", 9, False, 600),
                                     ("kv_storage_offset", 8.5, True, None),
                                     ("common.hpp:242", 8.5, True, None)]))
    # arrows row 1 -> row 2 (k_state_ix) and row 2 -> row 3 (k_storage_of)
    plain_cols = [1, 3] if eagle_view else [0, 1, 3]
    for i in plain_cols:
        cx = col_cx(px, i)
        o.append(arrow(fid, "ink", [(cx, y1 + CELL_H + 1), (cx, y2 - 2)], C["ink"], 1.4))
        o.append(arrow(fid, "ink", [(cx, y2 + CELL_H + 1), (cx, y3 - 2)], C["ink"], 1.4))
    if eagle_view:
        # slot 0 -> n_slots: leaves the top centre of the slot 0 cell (so that
        # it visibly comes from slot 0), runs over the top of row 1 and drops
        # into the n_slots entry; it crosses no cell and no arrow
        cx0, cxe = col_cx(px, 0), col_cx(px, 4)
        o.append(arrow(fid, "eagle", [(cx0, y1 - 1), (cx0, top + 22), (cxe, top + 22),
                                      (cxe, y2 - 2)], C["eagle"], 1.6))
        o.append(text(cx0 + 10, top + 13, "slot 0 -> n_slots", 8.5, fill=C["eagle"],
                      weight=700))
        o.append(arrow(fid, "eagle", [(cxe, y2 + CELL_H + 1), (cxe, y3 - 2)], C["eagle"],
                       1.6))
    # the how-many labels of the two arrow zones, in the label column
    o.append(side_text(px, y1 + CELL_H + 32, [
        ("k_state_ix", 9, True, 700),
        ("1 slot -> 1 entry", 9, False, 700),
        ("ix = slot.i (slot != 0)" if eagle_view else "ix = slot.i", 8.5, True, None)]))
    o.append(side_text(px, y2 + CELL_H + 32, [
        ("k_storage_of", 9, True, 700),
        ("1 ix -> 1 offset", 9, False, 700),
        ("eagle_storage_offset()" if eagle_view else "kv_storage_offset(slot.i)",
         8.5, True, None)]))
    # the worked example: what k_storage_of returns in this view
    ey = y3 + CELL_H + 18
    if eagle_view:
        ex = ["k_storage_of(slot 5) = {kv_storage_offset(5), 5}",
              "k_storage_of(slot 0) = {book.eagle_storage_offset(),",
              "                        layout_t::n_slots}"]
    else:
        ex = ["k_storage_of(slot 5) = {kv_storage_offset(5), 5}",
              "k_storage_of(slot 0) = {kv_storage_offset(0), 0}",
              "n_slots and EAGLE: not reached through k_state_ix here"]
    for s in ex:
        fit(s, 9, PANEL_W - 16, True, "panel example")
    o.append(lines(px + 8, ey, ex, 9, 12, mono=True))
    return "".join(o)


# ---- d2a: the view, the map, the two functions ----------------------------------
def fig_a():
    fid = "kv_cache-d2a"
    H = 610
    assert EXAMPLE["slot"] == 5
    o = [marker_defs(fid, {"ink": C["ink"], "eagle": C["eagle"]})]
    boxes = []
    o.append(text(15, 18, "Which state entry and which storage slot a call means: one "
                  "logical slot under the two storage views", 11.5, weight=600))
    # ---- A: the view -----------------------------------------------------------
    o.append(fn_cell(150, 30, 420, 62, "book::eagle_view_active()",
                     ["whether the EAGLE storage view is selected (set_storage_view):",
                      "storage_view_offset_.i != 0 (member at kv_cache.hpp:1557)"],
                     "kv_cache.hpp:1135-1138", "new"))
    boxes.append(("book::eagle_view_active", "kv_cache.hpp:1135-1138"))
    boxes.append(("storage_view_offset_", "kv_cache.hpp:1557"))
    o.append(arrow(fid, "ink", [(250, 93), (250, 106)], C["ink"], 1.4))
    o.append(text(243, 103, "== false", 9, "end", mono=True))
    o.append(arrow(fid, "eagle", [(470, 93), (470, 106)], C["eagle"], 1.4))
    o.append(text(477, 103, "== true", 9, mono=True, fill=C["eagle"]))
    LX, RX = 15, 365
    o.append(label_box(LX, 108, PANEL_W, 58, "primary view: eagle_view_active() == false",
                       ["reset_storage_view: storage_view_offset_ =",
                        "kv_storage_offset(0)"], "#fff", C["ink"], 11,
                       ref="kv_cache.hpp:1130-1133"))
    o.append(label_box(RX, 108, PANEL_W, 58, "EAGLE view: eagle_view_active() == true",
                       ["set_storage_view(book.eagle_storage_offset()):",
                        "logical slot 0 addresses the extra physical slot"],
                       C["eagle_fill"], C["eagle"], 11, ref="kv_cache.hpp:1120-1128"))
    boxes.append(("reset_storage_view (the primary view)", "kv_cache.hpp:1130-1133"))
    boxes.append(("set_storage_view (the EAGLE view)", "kv_cache.hpp:1120-1128"))
    # ---- B: the two panels -------------------------------------------------------
    PT = 166
    o.append(panel(fid, LX, PT, False))
    o.append(panel(fid, RX, PT, True))
    boxes += [("logical slot (kv_slot_id)", "attention_ids.hpp:23"),
              ("state entry ix (k_rows_saved_[ix], k_vnni_blocks_[ix])",
               "kv_cache.hpp:2531-2537 (k_state_ix: the state entry of a logical slot); "
               "the arrays kv_cache.hpp:2639-2653"),
              ("n_slots (the EAGLE entry layout_t::n_slots, EAGLE_STORAGE_SLOTS_1)",
               "kv_cache.hpp:2523, 2528-2529"),
              ("storage slot (kv_storage_offset)", "h/tron/models/common.hpp:242"),
              ("EAGLE storage (eagle_storage_offset = "
               "kv_storage_offset(logical_slot_count()))", "kv_cache.hpp:1140-1144")]
    o.append(lines(15, PT + PANEL_H + 12, [
        "dashed cells: not reached through k_state_ix in that view;",
        "copy_from and k_forget_row still visit every physical slot "
        "[kv_cache.hpp:2819-2831, 2588-2593]"], 8.5, 10, fill=C["muted"]))
    # ---- C: the two new functions -----------------------------------------------
    FY = PT + PANEL_H + 34
    o.append(fn_cell(LX, FY, PANEL_W, 58, "k_state_ix(slot)",
                     ["the state entry of a logical slot: layout_t::n_slots",
                      "for slot 0 while book.eagle_view_active(), slot.i otherwise"],
                     "kv_cache.hpp:2531-2537", "new"))
    o.append(text(LX + 8, FY + 70, "asserts slot.i < book.logical_slot_count() [2535]", 8.5,
                  fill=C["muted"]))
    o.append(fn_cell(RX, FY, PANEL_W, 58, "k_storage_of(slot)",
                     ["resolves a logical slot under the current view into",
                      "{offset, state_ix}; EAGLE: eagle_storage_offset(), n_slots"],
                     "kv_cache.hpp:2197-2203", "new"))
    o.append(text(RX + 8, FY + 70, "the pair's own box: part b [2185-2196]", 8.5,
                  fill=C["muted"]))
    boxes.append(("k_state_ix", "kv_cache.hpp:2531-2537"))
    boxes.append(("k_storage_of", "kv_cache.hpp:2197-2203"))
    o.append(lines(15, FY + 58 + 29, [
        "k_state_ix callers: k_vnni_blocks 2182, k_storage_of 2199, note_k_row_saved 2220, "
        "note_k_block_saved 2244, set_k_row 2298,",
        "get_k_row 2341, k_row_if_row_major 2382 (line numbers of kv_cache.hpp); "
        "k_storage_of callers: save_k_impl model.hpp:3427, k_block_to_vnni 2257"],
        8.5, 11, fill=C["muted"]))
    cap = ("Updates B1: the arrow kv_slot_id -> k_storage_ref and the box "
           "book::eagle_view_active of B1, expanded into the map a call follows under "
           "each storage view. In the primary view (left) the worked example's slot 5 "
           "goes to state entry 5 and storage slot 5, and slot 0 goes to entry 0 and "
           "storage slot 0. In the EAGLE view (right) k_state_ix sends logical slot 0 "
           "to entry layout_t::n_slots and k_storage_of sends it to the EAGLE "
           "storage, while slot 5 is unchanged. The two cells under the two halves are "
           "the new functions that compute the map. Part b shows who builds, keeps and "
           "takes the pair.")
    legend = [
        ("box", "white box, ink outline: the function cells book::eagle_view_active, "
                "k_state_ix and k_storage_of, the primary view box, and every slot or "
                "entry cell that view reaches; name in bold monospace, description in "
                "sans-serif"),
        ("hi", "pale yellow: the worked example's slot 5: its logical slot, state entry and "
               "storage slot, in both views"),
        ("eagle", "light blue: the EAGLE view box (set_storage_view), the state entry "
                  "n_slots and the EAGLE storage slot that view reaches"),
        ("ctx", "grey panel, thin grey outline: the cells one view reaches, drawn under "
                "that view's box"),
        ("empty", "grey dashed cell: a state entry or storage slot not reached through "
                  "k_state_ix in that view (n_slots and EAGLE in the primary view, "
                  "slot 0 in the EAGLE view)"),
        ("arrow", "ink arrow: the == false branch into the primary view, and the "
                  "k_state_ix / k_storage_of steps between the cell rows, one per "
                  "reached column"),
        ("light blue arrow: the == true branch into the EAGLE view, and the slot 0 -> "
         "n_slots -> EAGLE storage path of that view; its labels == true and "
         "slot 0 -> n_slots in the same light blue", "arrow", C["eagle"]),
        ("font_mono", "monospace = an identifier or a value from the code: the cell "
                      "labels, kv_slot_id, k_rows_saved_[ix], the k_storage_of examples"),
        ("font_sans", "sans-serif = prose: the row labels, the how-many labels, the "
                      "descriptions, and the grey notes under the panels"),
        ("font_cite", "small grey monospace = the line that defines the box or the row "
                      "(file:line)"),
        ("font_tag", "bold 'new' = added by this PR: book::eagle_view_active, "
                     "k_state_ix, k_storage_of"),
    ]
    return figure(fid, W, H, "Which state entry and which storage slot a call means: "
                  "the map under each storage view", "".join(o), cap, boxes=boxes,
                  legend=legend)


# ---- d2b: who builds, keeps and takes the pair; the geometry of a storage slot ---
def fig_b():
    fid = "kv_cache-d2b"
    H = 456
    o = [marker_defs(fid, {"ink": C["ink"], "eagle": C["eagle"]})]
    boxes = []
    o.append(text(15, 18, "k_storage_ref: the pair is built two ways, kept across the pass, "
                  "and taken as one argument", 11.5, weight=600))
    BW, BH = 330, 56
    LX, RX = 15, 375
    # builders
    o.append(note_box(LX, 30, BW, BH, "k_storage_of(slot) [main, in save_k_impl]",
                      ["from the logical slot under the current view, at the save:",
                       "pending_k_blocks_.push_back({&pg, pg.k_storage_of(slot), ...})"],
                      "model.hpp:3426-3428; kv_cache.hpp:2197-2203"))
    o.append(note_box(RX, 30, BW, BH, "copy_from [tree lock]",
                      ["from the physical slot: {kv_storage_offset(slot), slot} per",
                       "active slot; {book.eagle_storage_offset(), layout_t::n_slots}"],
                      "kv_cache.hpp:2819-2821, 2828-2831"))
    boxes.append(("save_k_impl push of the resolved pair",
                  "model.hpp:3426-3428 (inside save_k_impl, model.hpp:3345)"))
    boxes.append(("copy_from builds the pair from the physical slot",
                  "kv_cache.hpp:2814-2821, 2828-2831"))
    # the pair, with the keeper at its left and the logical-slot form at its right
    RY, RH = 120, 84
    rx, rw = 270, 180
    o.append(rect(rx, RY, rw, RH, "#fff", C["new"], 1.4, 5))
    o.append(text(rx + 8, RY + 16, "k_storage_ref", 10.5, mono=True, weight=700))
    o.append(text(rx + rw - 8, RY + 16, "new", 9, "end", fill=C["new"], weight=700))
    o.append(text(rx + 8, RY + 32, "kv_storage_offset offset;", 9, mono=True))
    o.append(text(rx + 8, RY + 44, "size_t state_ix;", 9, mono=True))
    o.append(text(rx + 8, RY + 60, "one argument of the conversion", 9, fill=C["muted"]))
    o.append(text(rx + 8, RY + 71, "and of the page copy", 9, fill=C["muted"]))
    o.append(cite(rx + rw - 4, RY + RH - 4, "kv_cache.hpp:2193-2196"))
    boxes.append(("k_storage_ref", "kv_cache.hpp:2185-2196"))
    keep = ["pending_k_block {pg, storage, block} keeps",
            "the pair resolved at the save [main] until",
            "convert_pending_k_blocks at the forward end",
            "[main]: a storage view change in between",
            "cannot redirect the conversion"]
    o.append(rect(LX, RY, 240, RH, C["soft"], C["line"], 1, 4))
    for s in keep:
        fit(s, 9, 224, False, "keep")
    o.append(lines(LX + 8, RY + 13, keep, 9, 11))
    o.append(cite(LX + 240 - 4, RY + RH - 4, "model.hpp:3161-3166; kv_cache.hpp:2189-2191"))
    boxes.append(("pending_k_block / pending_k_blocks_ (keeps the resolved pair)",
                  "model.hpp:3161-3166"))
    o.append(note_box(465, RY, 240, RH, "k_block_to_vnni(slot, c)",
                      ["the logical-slot form (tests only):",
                       "k_block_to_vnni_at(k_storage_of(slot), c)",
                       "main thread, at the forward end"],
                      "kv_cache.hpp:2249-2258", tag="new"))
    boxes.append(("k_block_to_vnni (logical-slot form)", "kv_cache.hpp:2249-2258"))
    # takers
    TY = 236
    o.append(note_box(LX, TY, BW, BH, "k_block_to_vnni_at(storage, c) [main, forward end]",
                      ["converts block c of every KV head of storage.offset in place,",
                       "then sets block bit c of k_vnni_blocks_[storage.state_ix]"],
                      "kv_cache.hpp:2260-2283"))
    o.append(note_box(RX, TY, BW, BH, "copy_storage_slot(storage, ...) [tree lock]",
                      ["copies count K/V tokens of one storage slot from src_page;",
                       "the K bits of the copied offsets follow the rows"],
                      "kv_cache.hpp:2719-2812"))
    boxes.append(("k_block_to_vnni_at (takes the pair)", "kv_cache.hpp:2260-2283"))
    boxes.append(("copy_storage_slot (takes the pair)", "kv_cache.hpp:2719-2812"))
    # arrows builders -> pair -> takers, each labelled with how many
    bl, br = LX + BW / 2, RX + BW / 2          # builder / taker centres (180, 540)
    pl, pr = rx + 60, rx + rw - 60              # entry points on the pair box (330, 390)
    o.append(arrow(fid, "ink", [(bl, 30 + BH + 1), (bl, 104), (pl, 104), (pl, RY - 2)],
                   C["ink"], 1.4))
    o.append(text((bl + pl) / 2, 100, "1 slot -> 1 pair", 9.5, "middle", weight=700))
    o.append(arrow(fid, "ink", [(br, 30 + BH + 1), (br, 104), (pr, 104), (pr, RY - 2)],
                   C["ink"], 1.4))
    o.append(text((br + pr) / 2, 100, "1 physical slot -> 1 pair", 9.5, "middle",
                  weight=700))
    o.append(arrow(fid, "ink", [(pl, RY + RH + 1), (pl, 220), (bl, 220), (bl, TY - 2)],
                   C["ink"], 1.4))
    o.append(text((bl + pl) / 2, 216, "1 pair = 1 argument", 9.5, "middle", weight=700))
    o.append(arrow(fid, "ink", [(pr, RY + RH + 1), (pr, 220), (br, 220), (br, TY - 2)],
                   C["ink"], 1.4))
    o.append(text((br + pr) / 2, 216, "1 pair = 1 argument", 9.5, "middle", weight=700))
    # ---- the geometry of a storage slot -------------------------------------------
    GY = TY + BH + 40
    o.append(text(15, GY - 10, "the geometry of a storage slot", 10.5, weight=600))
    o.append(fn_cell(15, GY, PANEL_W, 60, "k_with_storage_geometry(storage_offset, f)",
                     ["calls f.template operator()<geometry>() with the geometry",
                      "of the storage slot at storage_offset (the two cases, right)"],
                     "kv_cache.hpp:2552-2564", "new"))
    boxes.append(("k_with_storage_geometry", "kv_cache.hpp:2552-2564"))
    ox, ow = 395, 310
    o.append(note_box(ox, GY, ow, 46, "storage_offset.i < book.logical_slot_count()",
                      ["book.for_each_active_slot: kv_slot_specs[slot].geometry"],
                      "kv_cache.hpp:2557-2560, 1749-1755"))
    o.append(note_box(ox, GY + 52, ow, 46, "else: the EAGLE storage",
                      ["layout_t::primary_geometry"], "kv_cache.hpp:2561-2563, 905",
                      C["eagle"], C["eagle_fill"]))
    boxes.append(("book::for_each_active_slot", "kv_cache.hpp:1749-1755"))
    boxes.append(("layout_t::primary_geometry", "kv_cache.hpp:905"))
    o.append(arrow(fid, "ink", [(15 + PANEL_W + 2, GY + 24), (ox - 2, GY + 23)], C["ink"],
                   1.4))
    o.append(arrow(fid, "eagle", [(15 + PANEL_W + 2, GY + 40), (ox - 2, GY + 75)],
                   C["eagle"], 1.4))
    o.append(text(ox, GY - 10, "1 call -> f invoked once, with the matching geometry", 8.5,
                  fill=C["ink"], weight=600))
    o.append(text(15, GY + 98 + 14, "callers: k_block_to_vnni_at [main, forward end] "
                  "kv_cache.hpp:2272; k_forget_row [tree lock] kv_cache.hpp:2604", 8.5,
                  fill=C["muted"]))
    boxes.append(("k_forget_row (caller)", "kv_cache.hpp:2583 (k_forget_row); the call at 2604"))
    cap = ("Updates B1 (part b): the k_storage_ref box of B1 with the paths that build, "
           "keep and take it (the helper band of B3). k_storage_of builds the pair from "
           "the logical slot at the save, and copy_from builds it from the physical "
           "slot. pending_k_block keeps the resolved pair until the forward end. So a "
           "storage view change in between cannot redirect the conversion. The lower band is "
           "k_with_storage_geometry, which runs a template lambda with the geometry of "
           "a storage slot: the declared one, or the primary geometry for the EAGLE "
           "storage.")
    legend = [
        ("box", "white box, ink outline: the builders k_storage_of and copy_from, the "
                "pair k_storage_ref, the takers k_block_to_vnni_at and "
                "copy_storage_slot, k_block_to_vnni, k_with_storage_geometry and its "
                "declared-geometry case; name in bold monospace, description in "
                "sans-serif"),
        ("eagle", "light blue: the else case of k_with_storage_geometry (the EAGLE storage "
                  "slot gets layout_t::primary_geometry)"),
        ("ctx", "grey box, thin grey outline: the pending_k_block note (model.hpp), the "
                "holder of the pair between the save and the forward end"),
        ("arrow", "ink arrow: a builder -> the pair and the pair -> a taker, each "
                  "labelled with how many; k_with_storage_geometry -> the "
                  "declared-geometry case"),
        ("light blue arrow: k_with_storage_geometry -> the EAGLE storage case", "arrow",
         C["eagle"]),
        ("font_mono", "monospace = an identifier or a value from the code: the box "
                      "names with the thread in brackets, the members offset and "
                      "state_ix"),
        ("font_sans", "sans-serif = prose: the descriptions, the how-many labels, the "
                      "pending_k_block note, the callers line"),
        ("font_cite", "small grey monospace = the lines that define the box (file:line)"),
        ("font_tag", "bold 'new' = added by this PR: k_storage_ref, k_block_to_vnni, "
                     "k_with_storage_geometry"),
    ]
    return figure(fid, W, H, "k_storage_ref: who builds, keeps and takes the pair; the "
                  "geometry of a storage slot", "".join(o), cap, boxes=boxes,
                  legend=legend)


def figs():
    return [fig_a(), fig_b()]
