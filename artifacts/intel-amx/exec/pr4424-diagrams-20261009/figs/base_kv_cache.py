"""Base diagrams B1-B5 of the PR 4424 page for h/tron/models/kv_cache.hpp.

Exports for the change diagrams (from base_kv_cache import ...):
  worked example: ROWS_EXAMPLE, BLOCKS_EXAMPLE, BLOCK_STATES_EXAMPLE,
    BLOCK_WORDS_EXAMPLE, EXAMPLE, WINDOW_EXAMPLE, vnni_index, row_major_elem
  building blocks: fit, legend_row, bits_legend, example_bits, block_row,
    panel_grid, rm_panel, vnni_panel, state_box, lane_set, lane_block,
    window_table, ops_cell, caller_cell

Every label is an identifier or a comment phrase of the code; every box cites
the line or Note that defines it (head line numbers of kv_cache.hpp, or
<file>:<line> for other files).
"""
import sys

from svg_helpers import (C, arrow, bit_row, block_cell, card_arrow, cite,
                         figure, fn_cell, label_box, legend_chip, lane, line,
                         lines, marker_defs, rect, text, text_width, work_block)

# ---- the worked example of the page (STYLE.md) -----------------------------
# Page 7, storage slot 5 (layer 5), after the K rows of offsets 0..40 were
# saved: block 0 converted (VNNI), block 1 complete and waits for the forward
# end, block 2 holds 9 row-major rows (offsets 32..40), block 3 empty.
ROWS_EXAMPLE = "1" * 16 + "1" * 16 + "1" * 9 + "0" * 7 + "0" * 16
BLOCKS_EXAMPLE = "1000"  # bit 0 at the left
BLOCK_STATES_EXAMPLE = ["vnni", "pend", "rm", "empty"]
# state words: comment phrases of kv_cache.hpp:684-685 ("a complete block may
# wait for its conversion") and 2608-2617 (no row bit set)
BLOCK_WORDS_EXAMPLE = ["VNNI (converted)", "complete, may wait",
                       "9 rows, row-major", "no row bit"]


def vnni_index(token, dim):
    """k_vnni::index(token, dim) (tensor/k_vnni.hpp:132-141)."""
    s, c, dp, t, j = dim // 32, token // 16, (dim % 32) // 2, token % 16, dim % 2
    return (((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j


def row_major_elem(token):
    """Element offset of row_major_row(plane, token) (tensor/k_vnni.hpp:458-472)."""
    c, t = token // 16, token % 16
    return ((t // 4) * 4 + c) * 512 + (t % 4) * 128


EXAMPLE = dict(page=7, slot=5, token=37, dim=70, block=2, t=5, step=2, pair=3,
               j=0, index=vnni_index(37, 70), panel=2 * 4 + 2,
               byte=vnni_index(37, 70) * 2, rm_elem=row_major_elem(37),
               rm_panel=(5 // 4) * 4 + 2, rm_row=5 % 4)
assert EXAMPLE["index"] == 5226 and EXAMPLE["rm_elem"] == 3200

# The fill of the worked example's cell (page 7, slot 5) in B1 and D3a. Not a
# concept colour of svg_helpers.C: a highlight only.
HI_FILL = C["hi_fill"]

# A shared save_k window: 3 workers (main + 2 helpers), 40 items: user A at
# page 7 offsets 0..31 (two whole blocks), user B at page 9 offsets 32..39.
WINDOW_EXAMPLE = dict(
    n_workers=3, n_items=40,
    units=[(0, 16, "page 7, block 0", "set_k_block (whole block)"),
           (16, 32, "page 7, block 1", "set_k_block (whole block)"),
           (32, 40, "page 9, block 2", "set_k_row x 8 (row-major)")])


# ---- small checks and building blocks ----------------------------------------
def fit(s, size, w, mono=False, where=""):
    """Warn on stderr when a string is wider than w px (see the PNG too)."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w}", file=sys.stderr)
    return s


def legend_row(x, y):
    """Block-state legend, two rows."""
    o = []
    cx = x
    for st, lab in [("vnni", "converted block: VNNI layout"),
                    ("pend", "complete, may wait"),
                    ("rm", "row-major rows")]:
        o.append(legend_chip(cx, y, st, lab))
        cx += 32 + 6.2 * len(lab) + 18
    cx = x
    for st, lab in [("empty", "no row bit"),
                    ("hw", "records no row bits (hardware attention)")]:
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


def example_bits(x, y, mark_token=True):
    """k_rows_saved_[5] and k_vnni_blocks_[5] of the worked example, bit 0 at
    the left; the bit row starts at x + 170. Height about 50 px."""
    o = [text(x, y + 10, "k_rows_saved_[5]", 11, mono=True, fill=C["rows"])]
    body, _ = bit_row(x + 170, y, ROWS_EXAMPLE, 9, 1, C["rows_fill"], C["rows"],
                      group=16, group_gap=8)
    o.append(body)
    if mark_token:
        bx = x + 170 + 37 * 10 + 2 * 8 + 4.5
        o.append(line(bx, y + 10, bx, y + 18, C["ink"], 1))
        o.append(text(bx + 4, y + 22, "token 37 = bit 37 (block 2, t = 5)", 8.5,
                      fill=C["muted"]))
    o.append(text(x, y + 40, "k_vnni_blocks_[5]", 11, mono=True, fill=C["blk"]))
    for c in range(4):
        gx = x + 170 + c * 167
        on = BLOCKS_EXAMPLE[c] == "1"
        o.append(rect(gx, y + 30, 12, 12, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(text(gx + 18, y + 40, f"bit {c}", 10, fill=C["muted"]))
    return "".join(o)


def block_row(x, y, w, h, states=BLOCK_STATES_EXAMPLE, words=BLOCK_WORDS_EXAMPLE,
              gap=8, size=11, offsets=True):
    """Four 16-token blocks side by side, each w wide, with the state word under
    it and the offset range; returns svg. Total height h + 40."""
    o = []
    for c in range(4):
        gx = x + c * (w + gap)
        o.append(block_cell(gx, y, w, h, states[c], f"block {c}", size))
        o.append(text(gx + w / 2, y + h + 14, words[c], 10, "middle", fill=C["muted"]))
        if offsets:
            o.append(text(gx, y + h + 28, f"offset {16 * c}", 9, fill=C["muted"]))
            o.append(text(gx + w, y + h + 28, f"{16 * c + 15}", 9, "end",
                          fill=C["muted"]))
    return "".join(o)


def panel_grid(x, y, cw=76, ch=44, gapx=4, gapy=4, states=BLOCK_STATES_EXAMPLE,
               hi_panel=None):
    """The 16 panels (s, c) of one K plane: rows s = 0..3, columns c = 0..3,
    each column coloured by the block state. Returns svg."""
    o = []
    for c in range(4):
        o.append(text(x + c * (cw + gapx) + cw / 2, y - 8, f"c = {c}", 10, "middle",
                      fill=C["muted"]))
    for s in range(4):
        o.append(text(x - 8, y + s * (ch + gapy) + ch / 2 + 4, f"s = {s}", 10, "end",
                      fill=C["muted"]))
        for c in range(4):
            px, py = x + c * (cw + gapx), y + s * (ch + gapy)
            o.append(block_cell(px, py, cw, ch, states[c]))
            n = 4 * s + c
            if hi_panel is not None and n == hi_panel:
                o.append(rect(px + 1, py + 1, cw - 2, ch - 2, "none", C["ink"], 2, 3))
            o.append(text(px + cw / 2, py + 18, f"panel ({s},{c})", 9.5, "middle", True))
            o.append(text(px + cw / 2, py + 34, f"#{n}", 10, "middle", True,
                          fill=C["muted"]))
    return "".join(o)


def rm_panel(x, y, w, h, s, c, saved_until, hi_token=None):
    """One panel (s, c) in the row-major form: 4 token rows of 256 bytes."""
    o = [rect(x, y, w, h, C["rm_fill"], C["rm"], 1.4, 3),
         text(x + w - 6, y + 10, f"panel ({s},{c}) #{4 * s + c}", 8.5, "end", True,
              fill=C["muted"])]
    for r in range(4):
        tok = 16 * c + 4 * s + r
        ry = y + 16 + r * 14
        saved = tok <= saved_until
        hi = tok == hi_token
        if saved:
            o.append(rect(x + 6, ry, w - 12, 12, "#fff", C["rm"], 2 if hi else 0.8, 2))
            o.append(text(x + 10, ry + 9.5, f"offset {tok}: 128 bf16 = 256 B", 8.5,
                          mono=True, weight=700 if hi else None))
            if hi:
                o.append(text(x + w - 10, ry + 9.5, f"token {tok}", 8.5, "end",
                              weight=700))
        else:
            o.append(rect(x + 6, ry, w - 12, 12, C["empty_fill"], C["empty"], 0.8, 2,
                          "3 2"))
            o.append(text(x + 10, ry + 9.5, f"offset {tok}: not saved", 8.5, mono=True,
                          fill=C["muted"]))
    return "".join(o)


def vnni_panel(x, y, w, h, s, c, hi_t=None, hi_dp=None, bar_w=100):
    """One panel (s, c) in the VNNI form: 16 pair rows of 64 bytes; column t
    (one token) and pair row dp can be marked."""
    o = [rect(x, y, w, h, C["vnni_fill"], C["vnni"], 1.4, 3),
         text(x + w - 6, y + 10, f"panel ({s},{c}) #{4 * s + c}", 8.5, "end", True,
              fill=C["muted"])]
    for dp in range(16):
        ry = y + 16 + dp * 3.5
        o.append(rect(x + 6, ry, bar_w, 2.6, C["vnni"], C["vnni"], 0.3, 0))
    cw = bar_w / 16
    if hi_t is not None:
        o.append(rect(x + 6 + hi_t * cw, y + 15, cw, 16 * 3.5 + 1, "#fff", C["ink"],
                      0.9, 0))
    if hi_dp is not None:
        o.append(rect(x + 5, y + 16 + hi_dp * 3.5 - 1.2, bar_w + 2, 5, "none",
                      C["ink"], 1.2, 0))
        if hi_t is not None:
            o.append(rect(x + 6 + hi_t * cw, y + 16 + hi_dp * 3.5 - 0.7, cw, 4,
                          C["ink"], C["ink"], 0.5, 0))
    return "".join(o)


def state_box(x, y, w, h, state, title, sub, ref):
    """A state of the sequencing model: a block cell with two text lines and
    its citation under the box."""
    o = [block_cell(x, y, w, h, state),
         text(x + w / 2, y + 26, title, 11, "middle", weight=700),
         text(x + w / 2, y + 42, sub, 9.5, "middle"),
         cite(x + w - 5, y + h - 4, ref)]
    return "".join(o)


def lane_set(x, y, w, names, lane_h=80, gap=6):
    """Lanes for the interaction model: names = [(label, sub), ...]. Returns
    (svg, x0 where time starts, {label: lane top y})."""
    o, ys = [], {}
    cy = y
    for lab, sub in names:
        s, x0 = lane(x, cy, w, lane_h, lab, sub)
        o.append(s)
        ys[lab] = cy
        cy += lane_h + gap
    return "".join(o), x + 140, ys


def lane_block(x, y, w, h, lines_, fill, stroke, idle=False, size=8.5, ref=None,
               lh=10.5):
    """A lane block with several text lines and an optional citation (a string
    or a list of strings) in grey as the last line(s). Idle = dashed outline,
    white fill."""
    o = [work_block(x, y, w, h, None, fill, stroke, idle)]
    refs = [] if ref is None else ([ref] if isinstance(ref, str) else list(ref))
    n = len(lines_) + len(refs)
    ty = y + h / 2 - (n - 1) * lh / 2 + 3.5
    for s in lines_:
        fit(s, size, w - 4, False, "lane_block")
        o.append(text(x + w / 2, ty, s, size, "middle"))
        ty += lh
    for r in refs:
        fit(r, 8.5, w - 2, True, "lane_block cite")
        o.append(text(x + w / 2, ty, r, 8.5, "middle", True, fill=C["cite"]))
        ty += lh
    return "".join(o)


def window_table(x, y, w=300):
    """The work units of the shared save_k window of the worked example."""
    o = [text(x, y + 12, "k_store_window of the worked example: 3 workers, 40 items",
              10.5, weight=600)]
    ty = y + 28
    for a, b, where, how in WINDOW_EXAMPLE["units"]:
        o.append(rect(x, ty, w, 20, C["unit_fill"], C["unit"], 1, 3))
        o.append(text(x + 6, ty + 14, f"unit items[{a},{b}) {where}: {how}", 9.5,
                      mono=True))
        ty += 24
    o.append(cite(x + w, ty + 8, "common.hpp:1167-1193; model.hpp:3202-3230"))
    return "".join(o)


def caller_cell(x, y, w, h, lines_, ref):
    """A caller box (soft fill) with up to 3 text lines and its citation."""
    o = [rect(x, y, w, h, C["soft"], C["line"], 1, 4)]
    for s in lines_:
        fit(s, 9.5, w - 14, False, "caller_cell")
    o.append(lines(x + 8, y + 17, lines_, 9.5, 12))
    fit(ref, 8.5, w - 8, True, "caller_cell cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def ops_cell(x, y, w, h, lines_, refs):
    """A k_vnni.hpp operations box: mono lines and one or two citation lines."""
    o = [rect(x, y, w, h, "#fff", C["line"], 1, 4)]
    for s in lines_:
        fit(s, 9.5, w - 14, True, "ops_cell")
    o.append(lines(x + 8, y + 16, lines_, 9.5, 11.5, mono=True))
    ry = y + h - 4 - 10 * (len(refs) - 1)
    for r in refs:
        fit(r, 8.5, w - 8, True, "ops_cell cite")
        o.append(cite(x + w - 4, ry, r))
        ry += 10
    return "".join(o)


# ---- B1: data model ------------------------------------------------------------
def b1():
    fid = "kv_cache-b1"
    W, H = 1000, 742
    o = [marker_defs(fid, {"ink": C["ink"], "rows": C["rows"], "blk": C["blk"],
                           "new": C["new"]})]
    boxes = []
    top, colh = 36, 430
    # ---- column 1: book ------------------------------------------------------
    x, w = 20, 300
    o.append(rect(x, top, w, colh, C["soft"], C["ink"], 1.2, 6))
    o.append(text(x + 12, top + 20, "book", 13, mono=True, weight=700))
    o.append(text(x + w - 12, top + 20, "changed", 10, "end", fill=C["new"], weight=700))
    o.append(lines(x + 12, top + 36, ["owns one KV memory allocation; a page is a",
                                      "lightweight reference into it"], 9.5, 12,
                   fill=C["muted"]))
    o.append(cite(x + w - 6, top + colh - 5, "Note [KV Memory Layout] (kv_cache.hpp:56-81)"))
    boxes.append(("book", "Note [KV Memory Layout] (kv_cache.hpp:56-81); struct at "
                  "kv_cache.hpp:940-941; changed: eagle_view_active added at 1082-1087"))
    sy = top + 62
    o.append(text(x + 12, sy, "storage slots: kv_storage_offset", 10, mono=True))
    cx = x + 12
    for lab, cw in [("slot 0", 50), ("slot 1", 50), ("...", 30), ("slot n-1", 62)]:
        o.append(rect(cx, sy + 8, cw, 24, "#fff", C["ink"], 1, 3))
        o.append(text(cx + cw / 2, sy + 24, lab, 9.5, "middle", True))
        cx += cw + 4
    o.append(rect(cx, sy + 8, 52, 24, C["eagle_fill"], C["eagle"], 1.4, 3))
    o.append(text(cx + 26, sy + 24, "EAGLE", 9.5, "middle", True))
    boxes.append(("storage slot (kv_storage_offset)", "common.hpp:239-249; count "
                  "storage_slot_count_ = logical_slot_count() + has_eagle_storage() "
                  "(kv_cache.hpp:1099, 1105)"))
    boxes.append(("EAGLE storage", "kv_cache.hpp:1090-1092 (eagle_storage_offset = "
                  "kv_storage_offset(logical_slot_count()))"))
    o.append(text(x + 12, sy + 46, "count: storage_slot_count_", 9, mono=True))
    o.append(text(x + 12, sy + 58, "= logical_slot_count() + has_eagle_storage()", 9,
                  mono=True))
    o.append(text(x + 12, sy + 70, "EAGLE storage: the extra physical slot at", 9.5,
                  fill=C["muted"]))
    o.append(text(x + 12, sy + 82, "kv_storage_offset(logical_slot_count())", 9,
                  mono=True))
    o.append(cite(x + 12, sy + 94, "kv_cache.hpp:1099, 1105, 1090-1092", "start"))
    py0 = sy + 108
    o.append(text(x + 12, py0, "pages: std::vector<page_t> pages", 10, mono=True))
    o.append(cite(x + w - 12, py0, "kv_cache.hpp:1511"))
    py = py0 + 8
    for lab, hi in [("page 0", False), ("...", False), ("page 7", True),
                    ("page n_pages-1", False)]:
        o.append(rect(x + 12, py, 130, 22, HI_FILL if hi else "#fff", C["ink"],
                      1.6 if hi else 1, 3))
        o.append(text(x + 77, py + 15, lab, 10, "middle", True,
                      weight=700 if hi else None))
        py += 26
    boxes.append(("pages", "kv_cache.hpp:1511 (std::vector<page_t> pages); one page per "
                  "index 0 .. n_pages-1 (kv_cache.hpp:1686-1687)"))
    # arrow page 7 -> the page struct (column 2)
    ay = py0 + 8 + 2 * 26 + 11
    o.append(arrow(fid, "ink", [(x + 142, ay), (338, ay)], C["ink"], 1.4))
    o.append(text(240, ay - 6, "1 book -> n_pages pages", 9.5, "middle", fill=C["ink"],
                  weight=600))
    o.append(cite(240, ay + 12, "kv_cache.hpp:1686-1687", "middle"))
    # eagle_view_active
    ey = py0 + 8 + 4 * 26 + 8
    o.append(rect(x + 12, ey, w - 24, 56, "#fff", C["new"], 1.2, 4))
    o.append(text(x + 20, ey + 16, "book::eagle_view_active()", 10, mono=True, weight=700))
    o.append(text(x + w - 20, ey + 16, "new", 9.5, "end", fill=C["new"], weight=700))
    o.append(text(x + 20, ey + 30, "storage_view_offset_.i != 0: logical slot 0", 9))
    o.append(text(x + 20, ey + 42, "addresses the EAGLE storage", 9))
    o.append(cite(x + w - 16, ey + 52, "kv_cache.hpp:1082-1087"))
    boxes.append(("book::eagle_view_active", "kv_cache.hpp:1082-1087"))
    # kv_slot_id -> k_storage_ref, the arrow labelled with how many (1 slot -> 1 pair)
    ky = ey + 64
    o.append(rect(x + 12, ky, 124, 44, "#fff", C["ink"], 1, 4))
    o.append(text(x + 20, ky + 16, "kv_slot_id", 10, mono=True, weight=700))
    o.append(text(x + 20, ky + 28, "logical slot", 9, fill=C["muted"]))
    o.append(cite(x + 132, ky + 40, "attention_ids.hpp:20-30"))
    o.append(rect(x + 176, ky, 120, 44, "#fff", C["new"], 1.2, 4))
    o.append(text(x + 184, ky + 16, "k_storage_ref", 10, mono=True, weight=700))
    o.append(text(x + 184, ky + 28, "{offset, state_ix}", 9, mono=True))
    o.append(cite(x + 292, ky + 40, "kv_cache.hpp:2137-2148"))
    o.append(arrow(fid, "ink", [(x + 138, ky + 22), (x + 174, ky + 22)], C["ink"], 1.4))
    o.append(text(x + 156, ky + 14, "1 slot", 8.5, "middle", fill=C["ink"], weight=700))
    o.append(text(x + 156, ky + 36, "1 pair", 8.5, "middle", fill=C["ink"], weight=700))
    o.append(text(x + 12, ky + 58, "k_storage_of: 1 slot -> 1 pair (kv_cache.hpp:2149-2155)",
                  8.5, fill=C["ink"]))
    boxes.append(("kv_slot_id", "attention_ids.hpp:20-30 (struct kv_slot_id); "
                  "Note [KV slot retention] (kv_cache.hpp:113-120)"))
    boxes.append(("k_storage_ref", "kv_cache.hpp:2137-2148; k_storage_of at 2149-2155"))
    # ---- column 2: page ------------------------------------------------------
    x, w = 340, 340
    o.append(rect(x, top, w, colh, "#fff", C["ink"], 1.2, 6))
    o.append(text(x + 12, top + 20, "page 7 (page_size = 64 token offsets)", 12,
                  mono=True, weight=700))
    o.append(text(x + w - 12, top + 20, "changed", 10, "end", fill=C["new"], weight=700))
    o.append(cite(x + w - 6, top + colh - 5, "kv_cache.hpp:1940-1942"))
    boxes.append(("page", "kv_cache.hpp:1940-1942 (page_size = 64 at 1942)"))
    # arrow page -> its two new arrays, with the count
    o.append(arrow(fid, "ink", [(x + 30, top + 26), (x + 30, top + 50)], C["ink"], 1.4))
    o.append(text(x + 40, top + 38, "1 page -> layout_t::n_slots + EAGLE_STORAGE_SLOTS_1",
                  9, fill=C["ink"], weight=700))
    o.append(text(x + 40, top + 49, "entries, in each of the two arrays below", 9,
                  fill=C["ink"], weight=700))
    for i, (name, col, fill, ref, src) in enumerate([
            ("k_rows_saved_[layout_t::n_slots + 1]", C["rows"], C["rows_fill"],
             "kv_cache.hpp:2608-2617", "kv_cache.hpp:2608-2617"),
            ("k_vnni_blocks_[layout_t::n_slots + 1]", C["blk"], C["blk_fill"],
             "kv_cache.hpp:2618-2622", "kv_cache.hpp:2618-2622")]):
        yl = top + 68 + i * 78    # row 2 sits 6 px lower: room for the row-1 arrow label
        o.append(text(x + 36, yl, name, 10.5, mono=True, fill=col, weight=700))
        o.append(text(x + w - 12, yl, "new", 10, "end", fill=C["new"], weight=700))
        cy = yl + 8
        cx = x + 36
        for lab in ["0", "1", "5", "...", "n-1"]:
            hi = lab == "5"
            o.append(rect(cx, cy, 44, 28, fill if hi else "#fff", col, 1.6 if hi else 1, 3))
            o.append(text(cx + 22, cy + 18, lab, 10, "middle", True))
            cx += 48
        # the EAGLE entry, named as the code names it (layout_t::n_slots)
        o.append(rect(cx, cy, 50, 28, C["eagle_fill"], C["eagle"], 1.4, 3))
        o.append(text(cx + 25, cy + 18, "n_slots", 10, "middle", True))
        o.append(cite(x + 36, cy + 39, ref, "start"))
        boxes.append((name.split("[")[0], src))
    # arrows entry 5 -> the K planes of slot 5 (column 3); bit c -> block c.
    # The labels sit 6 px above the horizontal segment they run along.
    e5 = x + 36 + 2 * 48 + 22
    r1y = top + 68 + 8 + 28
    o.append(arrow(fid, "rows", [(e5, r1y), (e5, r1y + 28), (698, r1y + 28)],
                   C["rows"], 1.6))
    o.append(text(e5 + 6, r1y + 10, "1 entry -> geometry.n_kv_heads K", 8.5,
                  fill=C["rows"], weight=700))
    o.append(text(e5 + 6, r1y + 20, "planes of slot 5 (one per KV head)", 8.5,
                  fill=C["rows"], weight=700))
    r2y = top + 68 + 78 + 8 + 28
    o.append(arrow(fid, "blk", [(e5, r2y), (e5, r2y + 20), (698, r2y + 20)],
                   C["blk"], 1.6))
    o.append(text(e5 + 6, r2y + 12, "1 bit c -> block c, every KV head", 8.5,
                  fill=C["blk"], weight=700))
    ny = r2y + 36
    notes = [
        "one cell = one state entry = one storage slot;",
        "n_slots = entry layout_t::n_slots, the EAGLE storage [2486]",
        "uint64_t: 64 row bits; uint8_t: 4 block bits;",
        "k_state_ix(slot) picks the entry [2499-2505]; D2 opens the bits",
    ]
    for s in notes:
        fit(s, 9, w - 24, False, "b1 notes")
    o.append(lines(x + 12, ny, notes, 9, 11, fill=C["ink"]))
    boxes.append(("n_slots (entry layout_t::n_slots, the EAGLE storage)",
                  "kv_cache.hpp:2486, 2491-2492 (EAGLE_STORAGE_SLOTS_1)"))
    boxes.append(("EAGLE_STORAGE_SLOTS_1", "kv_cache.hpp:2491-2492"))
    boxes.append(("k_state_ix", "kv_cache.hpp:2499-2505"))
    boxes.append(("page(page&&)", "kv_cache.hpp:1958-1974"))
    ky = ny + 4 * 11 + 2
    o.append(rect(x + 12, ky, w - 24, 46, C["soft"], C["line"], 1, 4))
    o.append(text(x + 20, ky + 15, "kv_saves_[page_size][layout_t::n_slots]", 10,
                  mono=True, weight=700))
    o.append(text(x + 20, ky + 29, "per-token per-slot save counters, unchanged",
                  9, fill=C["muted"]))
    o.append(cite(x + w - 16, ky + 42, "kv_cache.hpp:2603-2606"))
    boxes.append(("kv_saves_", "kv_cache.hpp:2603-2606"))
    # ---- column 3: kv_block --------------------------------------------------
    x, w = 700, 280
    o.append(rect(x, top, w, colh, "#fff", C["ink"], 1.2, 6))
    o.append(text(x + 12, top + 20, "kv_block(slot 5, kv_head h, page 7)", 11,
                  mono=True, weight=700))
    o.append(text(x + w - 12, top + 34, "changed", 10, "end", fill=C["new"], weight=700))
    o.append(text(x + 12, top + 46, "1 (storage slot, page) -> geometry.n_kv_heads", 9,
                  fill=C["ink"], weight=600))
    o.append(text(x + 12, top + 57, "kv_blocks, one per KV head h [1797-1798]", 9,
                  fill=C["ink"], weight=600))
    o.append(cite(x + w - 6, top + colh - 5, "kv_cache.hpp:2982-2985"))
    boxes.append(("kv_block", "kv_cache.hpp:2982-2985 (detail::kv_block, 2984-2985); "
                  "one per (storage slot, KV head, page): kv_cache.hpp:1797-1798"))
    fx, fy, fw, fh = x + 12, top + 70, 256, 228
    for k in (3, 2, 1):
        o.append(rect(fx + 6 * k, fy + 6 * k, fw, fh, "#fff", C["line"], 1, 5))
    o.append(rect(fx, fy, fw, fh, "#fff", C["ink"], 1.2, 5))
    o.append(text(fx + 8, fy + 16, "kv_head 0", 10, mono=True, weight=600))
    o.append(text(fx + 8, fy + 34, "k: k_storage", 10.5, mono=True, weight=700))
    o.append(text(fx + fw - 8, fy + 34, "changed", 9.5, "end", fill=C["new"], weight=700))
    o.append(text(fx + 8, fy + 47, "= k_vnni_tensor<page_size, head_size> (VNNI slot)", 9))
    o.append(text(fx + 8, fy + 59, "| native_k_storage = bf16[page_size * head_size]", 9))
    o.append(cite(fx + fw - 6, fy + 70, "kv_cache.hpp:2986-3002"))
    boxes.append(("k (k_storage)", "kv_cache.hpp:2986-3002 (std::conditional_t at "
                  "2993-2995; static_asserts 2996-3001)"))
    boxes.append(("k_vnni_tensor", "tensor/k_vnni.hpp:201-236"))
    boxes.append(("native_k_storage", "kv_cache.hpp:2990-2992"))
    by = fy + 78
    for c in range(4):
        o.append(block_cell(fx + 8, by, 118, 24, BLOCK_STATES_EXAMPLE[c],
                            f"block {c}: {16 * c}..{16 * c + 15}", 9))
        o.append(text(fx + 132, by + 16, BLOCK_WORDS_EXAMPLE[c], 9))
        by += 28
    o.append(rect(fx + 8, by + 2, fw - 16, 22, C["soft"], C["line"], 1, 4))
    o.append(text(fx + fw / 2, by + 17, "v: v_vnni_tensor<page_size, head_size>", 9.5,
                  "middle", True))
    o.append(cite(fx + fw - 6, fy + fh - 5, "kv_cache.hpp:3003-3015"))
    boxes.append(("v (v_vnni_tensor)", "kv_cache.hpp:3003-3015, unchanged context"))
    o.append(text(fx + 8, fy + fh - 6, "v unchanged; 16 KiB each", 8.5, fill=C["muted"]))
    uy = fy + fh + 18 + 16
    under = [
        ("1 kv_block -> KV_BLOCK_PLANES_2 planes (K, V)", "kv_cache.hpp:822-825"),
        ("k.as_view() -> k_vnni_view: the only route in",
         "tensor/k_vnni.hpp:156-199, 214-227"),
        ("k_vnni::layout_on: TRON_K_VNNI, head_size == 128",
         "tensor/k_vnni.hpp:119-130"),
        ("bits are per slot: all KV heads share entry 5", "kv_cache.hpp:707-709"),
    ]
    for s, r in under:
        # bold sans runs about 10 % wider than text_width estimates: fit to w - 40
        fit(s, 9, w - 40, False, "b1 under")
        o.append(text(x + 12, uy, s, 9, weight=600))
        o.append(cite(x + 12, uy + 10, r, "start"))
        uy += 24
    boxes.append(("k_vnni_view (k.as_view())", "tensor/k_vnni.hpp:156-199; as_view at 214-227"))
    boxes.append(("k_vnni::layout_on", "tensor/k_vnni.hpp:119-130"))
    boxes.append(("KV_BLOCK_PLANES_2", "kv_cache.hpp:822-825"))
    # ---- bottom: the worked example ------------------------------------------
    y0 = top + colh + 16
    o.append(line(20, y0, 980, y0, C["line"]))
    o.append(text(20, y0 + 18, "Worked example of this page: page 7, state entry 5 "
                  "(slot 5), after the K rows of offsets 0..40 were saved. Bit 0 is "
                  "drawn at the left.", 11.5, weight=600))
    o.append(example_bits(20, y0 + 34))
    o.append(cite(20 + 170 + 664, y0 + 68 + 4, "kv_cache.hpp:2608-2622"))
    o.append(text(20, y0 + 110, "block layout", 11, fill=C["muted"]))
    o.append(block_row(190, y0 + 84, 159, 44))
    o.append(text(20, y0 + 174, "legend", 11, fill=C["muted"]))
    o.append(legend_row(90, y0 + 162))
    o.append(bits_legend(90, y0 + 214))
    cap = ("B1, the data model. A book (the unit of KV memory allocation) holds one "
           "storage slot per layer plus one EAGLE storage (EAGLE is a speculation "
           "model with its own extra physical slot), and n_pages pages of 64 token "
           "offsets. One kv_block holds the K and V planes of one (storage slot, KV "
           "head, page). The PR types the K plane of a kv_block (k_storage). It also "
           "adds two atomic bit arrays to the page, with one entry per logical slot "
           "plus one for the EAGLE storage: k_rows_saved_ (one bit per offset) and "
           "k_vnni_blocks_ (one bit per 16-token block). Bit c of a k_vnni_blocks_ "
           "entry names the layout of block c in every KV head's plane of that slot. "
           "A set block bit implies the block's 16 row bits (2620), and D2 opens the "
           "two arrays to the bit level. The bottom band is the worked example reused "
           "on this page.")
    legend = [
        ("box", "white box, ink outline: a data-model entity (the storage slots, the pages, "
                "kv_slot_id, k_storage_ref, the page 7 column, the kv_block column and its "
                "kv_head 0 plane) and the one function drawn, book::eagle_view_active; "
                "name in bold monospace, description in grey sans-serif"),
        ("ctx_ink", "grey fill, ink outline: the book column (the unit of KV memory "
                    "allocation)"),
        ("ctx", "grey box, thin grey outline: a member this PR leaves unchanged (kv_saves_, "
                "v: v_vnni_tensor)"),
        ("lane", "white frame, thin grey outline: the frames stacked behind the kv_head 0 "
                 "plane = the kv_blocks of the other KV heads"),
        ("hi", "pale yellow: page 7, the page of the worked example, in the pages list"),
        ("eagle", "light blue: the EAGLE storage: the extra physical slot of the book, and "
                  "its entry n_slots in each of the two arrays"),
        ("rows", "green: k_rows_saved_: entry 5 of the array, and every row bit set in the "
                 "worked example (offsets 0..40); green text = the array's name and its "
                 "arrow label"),
        ("white box, green outline: the other entries of k_rows_saved_ (0, 1, ..., n-1)",
         "#fff", C["rows"], False, False),
        ("blk", "pink: k_vnni_blocks_: entry 5 of the array, and block bit 0, the one bit "
                "set in the worked example; pink text = the array's name and its arrow "
                "label"),
        ("white box, pink outline: the other entries of k_vnni_blocks_ (0, 1, ..., n-1)",
         "#fff", C["blk"], False, False),
        ("bit_clear", "white square, grey outline: a row bit or a block bit that is clear "
                      "(offsets 41..63, block bits 1..3)"),
        ("vnni", "blue: block 0 of the worked example, converted to the VNNI layout"),
        ("pend", "orange-red dashed: block 1 of the worked example, complete and waiting "
                 "for its conversion"),
        ("rm", "orange: block 2 of the worked example, 9 row-major rows (offsets 32..40)"),
        ("empty", "grey dashed: block 3 of the worked example, no row bit"),
        ("hw", "yellow: a block that records no row bits under hardware attention (a "
               "legend chip only here; B4 draws that state)"),
        ("arrow", "ink arrow: how many of the target one source has: 1 book -> n_pages "
                  "pages, 1 page -> layout_t::n_slots + EAGLE_STORAGE_SLOTS_1 entries, "
                  "1 slot -> 1 pair (k_storage_of)"),
        ("green arrow: entry 5 of k_rows_saved_ -> the K planes of slot 5, one per KV head",
         "arrow", C["rows"]),
        ("pink arrow: bit c of k_vnni_blocks_ entry 5 -> block c of every KV head",
         "arrow", C["blk"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = an array or a function this PR adds; 'changed' = a "
                     "struct or member it changes (book, page, kv_block, the member k)"),
    ]
    return figure(fid, W, H, "Data model: book, page, kv_block and the K layout state",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B2: one block, two layouts -------------------------------------------------
def b2():
    fid = "kv_cache-b2"
    W, H = 1000, 632
    DY = 36   # the two form columns start 36 px lower: room for the key under the headings
    o = [marker_defs(fid, {"pend": C["pend"], "rm": C["rm"], "ink": C["ink"]})]
    boxes = []
    # ---- left: the plane as 16 panels ---------------------------------------
    o.append(text(20, 24, "K plane of one (slot, KV head, page): 16 panels of 1 KiB",
                  12, weight=600))
    # s means a dimension step in the VNNI form and a token group in the
    # row-major form (tensor/k_vnni.hpp:29-30, 441-445): say so once here
    o.append(text(20, 38, "panel (s, c): the s-th 1 KiB piece of block c (16 tokens)", 9,
                  fill=C["muted"]))
    o.append(text(20, 49, "VNNI: s = dimension step | row-major: s = token group "
                  "4 s .. 4 s + 3", 9, fill=C["muted"]))
    o.append(panel_grid(70, 72, hi_panel=None))
    o.append(rect(70 + 2 * 80 - 2, 72 - 2, 80, 4 * 48, "none", C["rm"], 1.6, 4, "5 3"))
    left = [
        "memory order: panel index 4 s + c, byte offset 1024 x (4 s + c)",
        "block c owns panels (s, c), s = 0..3: four 1 KiB pieces, 4 KiB apart",
        "block 2 owns panels #2, #6, #10, #14 (the dashed column)",
        "a block's two layouts use exactly those four panels; no other",
        "block is touched (Note [Row-major tail block])",
        "column colours: the block states of the worked example (B1)",
    ]
    for s in left:
        fit(s, 10, 380, False, "b2 left")
    o.append(lines(20, 284, left, 10, 13))
    o.append(cite(20, 370, "tensor/k_vnni.hpp:24-32, 437-445", "start"))
    boxes.append(("K plane (16 panels)", "tensor/k_vnni.hpp:24-32 (plane layout); "
                  "16 KiB = N_PANELS_16 x PANEL_BYTES_1024 (tensor/k_vnni.hpp:61-117)"))
    boxes.append(("panel (s, c)", "tensor/k_vnni.hpp:29-30"))
    boxes.append(("block c = panels (s, c), s = 0..3",
                  "Note [Row-major tail block] (tensor/k_vnni.hpp:437-445)"))
    ly = 392
    for i, (st, lab) in enumerate([("vnni", "converted block: VNNI layout"),
                                   ("pend", "complete, may wait"),
                                   ("rm", "row-major rows"),
                                   ("empty", "no row bit")]):
        o.append(legend_chip(20 + (i % 2) * 200, ly + (i // 2) * 22, st, lab))
    # ---- middle: the row-major form of block 2 -------------------------------
    mx, mw = 420, 220
    o.append(text(mx, 24, "Row-major form (block bit 2 clear)", 12, weight=600,
                  fill=C["rm"]))
    o.append(text(mx, 40, "the worked example now: 9 rows saved, 32..40", 9.5,
                  fill=C["muted"]))
    # the row index inside a panel is r here; t is the token's index in its
    # block (t = 5 for token 37), as in the VNNI formula on the right
    o.append(lines(mx, 54, ["token row r of panel (s, 2) = token 32 + 4 s + r;",
                            "white row: token 37 (s = 1, r = 1)",
                            "each row: 128 bf16 = 256 B, 4 whole 64-byte lines"],
                   8.5, 10, fill=C["muted"]))
    for s in range(4):
        o.append(rm_panel(mx, 56 + DY + s * 84, mw, 76, s, 2, 40, hi_token=37))
    mf = [
        "row_major_row(plane, 37): c = 2, t = 5",
        "elem = ((t/4)*4 + c)*512 + (t%4)*128",
        "     = (1*4 + 2)*512 + 1*128 = 3200",
        "panel (1, 2) = #6, row r = 1",
        "dimension 70: element 3200 + 70 = 3270",
    ]
    for s in mf:
        fit(s, 9.5, mw, True, "b2 mf")
    o.append(lines(mx, 404 + DY, mf, 9.5, 12, mono=True))
    o.append(cite(mx, 467 + DY, "tensor/k_vnni.hpp:458-472", "start"))
    o.append(lines(mx, 484 + DY, ["store_row_major / load_row_major:",
                                  "4 whole 64-byte lines per token"], 9.5, 12))
    o.append(cite(mx, 509 + DY, "tensor/k_vnni.hpp:474-492", "start"))
    boxes.append(("row-major form of block 2 (row_major_row)",
                  "tensor/k_vnni.hpp:458-472; Note [Row-major tail block] 437-456"))
    boxes.append(("store_row_major / load_row_major", "tensor/k_vnni.hpp:474-492"))
    # ---- right: the VNNI form of block 2 -------------------------------------
    rx, rw = 775, 210
    o.append(text(rx, 24, "VNNI form (block bit 2 set)", 12, weight=600, fill=C["vnni"]))
    o.append(text(rx, 40, "after block_to_vnni (AMX B operand)", 9.5, fill=C["muted"]))
    o.append(lines(rx, 54, ["pair row dp of panel (s, 2) holds dimensions",
                            "32 s + 2 dp and 32 s + 2 dp + 1; column t holds",
                            "token 32 + t; white column: t = 5 = token 37"],
                   8.5, 10, fill=C["muted"]))
    for s in range(4):
        y = 56 + DY + s * 84
        o.append(vnni_panel(rx, y, rw, 76, s, 2, hi_t=5, hi_dp=3 if s == 2 else None))
        o.append(lines(rx + 112, y + 26, ["16 pair rows x 64 B",
                                          "dimensions",
                                          f"{32 * s}..{32 * s + 31}",
                                          "(step s = %d)" % s], 8.5, 11))
    rf = [
        "k_vnni::index(37, 70):",
        "s = 2, c = 2, dp = 3, t = 5, j = 0",
        "(((s*4+c)*16+dp)*16+t)*2+j = 5226",
        "panel (2, 2) = #10, pair row 3,",
        "column 5; byte 10452",
    ]
    for s in rf:
        fit(s, 9.5, rw, True, "b2 rf")
    o.append(lines(rx, 404 + DY, rf, 9.5, 12, mono=True))
    o.append(cite(rx, 467 + DY, "tensor/k_vnni.hpp:24-32, 132-141", "start"))
    o.append(lines(rx, 484 + DY, ["store_row / load_row: 4 scatters or",
                                  "gathers of 16 dwords (64 lines)"], 9.5, 12))
    o.append(cite(rx, 509 + DY, "tensor/k_vnni.hpp:344-381", "start"))
    o.append(text(rx, 526 + DY, "store_block: 64 whole-line stores", 9.5))
    o.append(cite(rx, 539 + DY, "tensor/k_vnni.hpp:382-420", "start"))
    boxes.append(("k_vnni::index (the VNNI form of block 2)", "tensor/k_vnni.hpp:132-141, 24-32"))
    boxes.append(("store_row / load_row", "tensor/k_vnni.hpp:344-381"))
    boxes.append(("store_block", "tensor/k_vnni.hpp:382-420"))
    # ---- arrows between the forms --------------------------------------------
    gx = (mx + mw + rx) / 2
    o.append(arrow(fid, "pend", [(mx + mw + 6, 120 + DY), (rx - 6, 120 + DY)], C["pend"], 1.6))
    o.append(text(gx, 112 + DY, "block_to_vnni", 9.5, "middle", True, fill=C["pend"],
                  weight=700))
    # each arrow between the two data boxes says how many: one block's four
    # panels go to the same four panels
    o.append(lines(gx, 134 + DY, ["1 block (4 panels) ->", "the same 4 panels,",
                                  "in place, 4 KiB, via a", "stack copy of the rows",
                                  "callers:", "k_block_to_vnni_at", "kv_cache.hpp:2225-2234",
                                  "copy_storage_slot", "kv_cache.hpp:2757-2762"],
                   8.5, 10.5, "middle"))
    o.append(cite(gx, 233 + DY, "tensor/k_vnni.hpp:494-509", "middle"))
    o.append(arrow(fid, "rm", [(rx - 6, 250 + DY), (mx + mw + 6, 250 + DY)], C["rm"], 1.6))
    o.append(text(gx, 266 + DY, "block_to_rows", 9.5, "middle", True, fill=C["rm"],
                  weight=700))
    o.append(lines(gx, 280 + DY, ["1 block (4 panels) ->", "the same 4 panels,",
                                  "the inverse, in place", "callers:", "k_forget_row",
                                  "kv_cache.hpp:2571-2582", "copy_storage_slot",
                                  "kv_cache.hpp:2741-2746"], 8.5, 10.5, "middle"))
    o.append(cite(gx, 368 + DY, "tensor/k_vnni.hpp:511-524", "middle"))
    boxes.append(("block_to_vnni", "tensor/k_vnni.hpp:494-509"))
    boxes.append(("block_to_rows", "tensor/k_vnni.hpp:511-524"))
    # ---- bottom: the bit that decides ----------------------------------------
    o.append(line(20, 556 + DY, 980, 556 + DY, C["line"]))
    o.append(text(20, 574 + DY, "Which form block c holds is the page's block bit: "
                  "k_vnni_blocks_[entry] bit c, read with acquire order by "
                  "k_block_is_vnni(state_ix, offset) and k_vnni_blocks(slot).", 10.5))
    o.append(cite(20, 588 + DY, "kv_cache.hpp:2618-2622, 2513-2518, 2126-2135", "start"))
    boxes.append(("k_vnni_blocks_ bit c (the block bit)", "kv_cache.hpp:2618-2622"))
    boxes.append(("k_block_is_vnni", "kv_cache.hpp:2513-2518"))
    cap = ("B2, one 16-token block in its two layouts, drawn for the worked example "
           "(block 2 of the plane of slot 5, page 7). A plane (K for one KV head of "
           "one page, 16 KiB) is 16 panels of 1 KiB, and block c owns the four panels "
           "(s, c), 4 KiB apart. In the row-major form each panel holds four 256-byte "
           "token rows. In the VNNI form (Vector Neural Network Instructions, the AMX "
           "B-operand layout) each panel holds the 16 dimension pairs of one 32-dimension "
           "step for the block's 16 tokens. So dimension 70 of token 37 sits at element "
           "3270 in the row-major form (row start 3200 + 70) and at element 5226 in the "
           "VNNI form.")
    legend = [
        ("vnni", "blue: a panel of a converted block: column c = 0 of the panel grid, and "
                 "the four VNNI-form panels of block 2 at the right; blue text = the VNNI "
                 "form heading"),
        ("vnni_solid", "solid blue bar: one pair row of 64 bytes inside a VNNI panel (16 "
                       "per panel)"),
        ("box", "white column, ink outline: column t = 5 of each VNNI panel, the 16 pair "
                "slots of token 37"),
        ("ink frame: pair row dp = 3 of panel (2, 2), dimensions 70 and 71 of block 2",
         "none", C["ink"], False, False),
        ("solid ink cell: dimension 70 of token 37 in panel (2, 2), element 5226 (pair "
         "row 3, column 5)", C["ink"], C["ink"], False, False),
        ("pend", "orange-red dashed: the panels of block 1, complete and waiting for its "
                 "conversion (column c = 1 of the panel grid); orange-red text = the "
                 "block_to_vnni label"),
        ("rm", "orange: a panel of block 2 in the row-major form: column c = 2 of the panel "
               "grid, and the four row-major panels in the middle; orange text = the "
               "row-major form heading and the block_to_rows label"),
        ("orange dashed frame: the four panels block 2 owns in the panel grid (#2, #6, "
         "#10, #14)", "none", C["rm"], True, False),
        ("white row, orange outline: a saved token row of 256 bytes (offsets 32..40); "
         "token 37 in bold with a heavier outline", "#fff", C["rm"], False, False),
        ("empty", "grey dashed: no row saved: the panels of block 3 (column c = 3), and the "
                  "rows of offsets 41..47"),
        ("orange-red arrow: block_to_vnni, the row-major form -> the VNNI form, in place",
         "arrow", C["pend"]),
        ("orange arrow: block_to_rows, the VNNI form -> the row-major form, the inverse",
         "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "One 16-token block in its row-major and VNNI forms",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B3: function model ----------------------------------------------------------
def b3():
    fid = "kv_cache-b3"
    W, H = 1000, 830
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    cx0, cw0 = 20, 228
    ax0, aw0 = 258, 448
    ox0, ow0 = 716, 264
    CW, CG = 202, 44   # two function cells per row: width, and the labelled gap between
    for x, w, h in [(cx0, cw0, "callers (other files) [thread]"),
                    (ax0, aw0, "page / book API in kv_cache.hpp"),
                    (ox0, ow0, "operation in h/tron/tensor/k_vnni.hpp")]:
        o.append(text(x + w / 2, 22, h, 12, "middle", weight=700))
    RH, GAP = 60, 6
    # rows: caller | up to two function cells (link = the word on the arrow between
    # them, from the code: "calls", "then", "and"; "<-" = the second cell calls
    # the first) | the k_vnni.hpp operation
    rows = [
        dict(caller=["model.hpp store_k_block: a run", "shorter than 16 tokens",
                     "[main or a main helper of the window]"],
             cref="model.hpp:3300-3318",
             api=[("set_k_row", ["stores one token's row into the layout its block",
                                 "holds: store_row_major, or store_row when VNNI"],
                   "kv_cache.hpp:2238-2263", "new", 448)],
             ops=["store_row_major: 4 whole lines", "(block bit clear) | store_row:",
                  "4 scatters of 16 dwords (bit set)"],
             orefs=["tensor/k_vnni.hpp:474-482, 344-362"]),
        dict(caller=["model.hpp store_k_block: a run of", "16 tokens that covers its block",
                     "[any thread of the shared window]"],
             cref="model.hpp:3323-3340",
             api=[("set_k_block", ["16 rows stored at once in the", "VNNI layout; sets no bit"],
                   "kv_cache.hpp:2265-2284", "new", CW),
                  ("note_k_block_saved", ["publishes the 16 row bits, then the",
                                          "block bit, after the last KV head"],
                   "kv_cache.hpp:2192-2200", "new", CW)], link="then",
             ops=["store_block: 64 whole-line", "stores, mask FULL_BLOCK_0XFFFF"],
             orefs=["tensor/k_vnni.hpp:382-420"]),
        dict(caller=["model.hpp save_k_impl: row-recording", "loop after the join [main];",
                     "skipped when cached_operation_uses_hw"],
             cref="model.hpp:3426-3435",
             api=[("note_k_row_saved", ["sets the row bit; true = the block",
                                        "has 16 row bits, no block bit yet"],
                   "kv_cache.hpp:2157-2190", "new", CW),
                  ("k_storage_of", ["logical slot -> {storage offset,",
                                    "state entry} under the current view"],
                   "kv_cache.hpp:2149-2155", "new", CW)], link="then", h=72,
             ops=["offset_bit(offset): the bit of one",
                  "page offset in a k_rows_saved_ word;",
                  "block_bit(c): the bit of one 16-token",
                  "block in a k_vnni_blocks_ byte"],
             orefs=["tensor/k_vnni.hpp:97-105"]),
        dict(caller=["model.hpp convert_pending_k_blocks", "[main, forward end, after",
                     "wait_for_coop_gof]"],
             cref="model.hpp:3173-3180; 1847",
             api=[("k_block_to_vnni_at", ["converts block c of every KV head",
                                          "in place, then block bit (release)"],
                   "kv_cache.hpp:2213-2236", "new", CW),
                  ("k_block_to_vnni", ["logical-slot form: k_storage_of,",
                                       "then k_block_to_vnni_at; tests only"],
                   "kv_cache.hpp:2202-2211", "new", CW)], link="<- calls",
             ops=["block_to_vnni: in place, 4 KiB,", "via a stack copy of the rows"],
             orefs=["tensor/k_vnni.hpp:494-509"]),
        dict(caller=["self_attention.hpp apply_page_tok:", "dense gate + apply_dense_amx_page,",
                     "or the software loop [attention workers]"],
             cref="self_attention.hpp:1924-1937, 2019-2049",
             api=[("k_vnni_blocks", ["the converted-block byte of a slot",
                                     "(acquire): bit c = block c is VNNI"],
                   "kv_cache.hpp:2126-2135", "new", CW),
                  ("k_packed", ["read-only k_vnni_view of one (slot,",
                                "kv_head) plane: the kernel argument"],
                   "kv_cache.hpp:2108-2124", "new", CW)], link="and", h=72,
             ops=["qk_vnni_128x4 (dense page, AMX)",
                  "row_major_row + dotter (bit clear)",
                  "qk_group over the live mask (set)"],
             orefs=["amx_attn_iface.hpp:250-263", "kernels/k_vnni.hpp:59-65"]),
        dict(caller=["full.hpp k_head_fn: the FPGA staging", "of gof::populate [attention",
                     "workers (help_drain_gof) and main]"],
             cref="full.hpp:2747-2770; gof.hpp:78",
             api=[("k_row_if_row_major", ["the row in place (row-major block);",
                                          "an invalid view for a converted one"],
                   "kv_cache.hpp:2332-2349", "new", CW),
                  ("get_k_row", ["loads a token's row from the layout",
                                 "its block holds (set_k_row inverse)"],
                   "kv_cache.hpp:2286-2307", "new", CW)], link="and",
             ops=["row_major_row (in place) |", "load_row: 4 gathers into scratch"],
             orefs=["tensor/k_vnni.hpp:458-472, 364-381"]),
        dict(caller=["full.hpp create_child_at_location,", "extend_leaf_edge,",
                     "invalidate_restored_book [tree lock]"],
             cref="full.hpp:669, 818, 3346",
             api=[("clear_kv_complete_at", ["zeroes kv_saves_[offset] per slot,",
                                            "then calls k_forget_row (new call)"],
                   "kv_cache.hpp:2470-2477", "changed", CW),
                  ("k_forget_row", ["drops bits at and above the offset;",
                                    "the offset's block to rows first"],
                   "kv_cache.hpp:2544-2586", "new", CW)], link="calls",
             ops=["block_to_rows: when the block is", "converted, keeps rows, and the",
                  "storage is readable"],
             orefs=["tensor/k_vnni.hpp:511-524"]),
        dict(caller=["kv_cache.hpp book::append (defrag),", "page-wise [tree lock]"],
             cref="kv_cache.hpp:1361-1395",
             api=[("copy_from", ["copies count tokens from src_page;",
                                 "one k_storage_ref per physical slot"],
                   "kv_cache.hpp:2786-2811", "changed", CW),
                  ("copy_storage_slot", ["copies a slot's K rows, V and bits;",
                                         "a whole page = one owner assignment"],
                   "kv_cache.hpp:2688-2784", "changed", CW)], link="calls",
             ops=["block_to_rows -> load_row |", "store_row_major -> block_to_vnni"],
             orefs=["tensor/k_vnni.hpp:494-524, 364-381,", "474-482"]),
        dict(caller=["row-major slots only: model.hpp:3259,", "self_attention.hpp:1785, 2035,",
                     "full.hpp:2770"],
             cref="model.hpp:3251-3261",
             api=[("page::k", ["row view, 8 overloads; now requires",
                               "!k_vnni::layout_on: row-major only"],
                   "kv_cache.hpp:2040-2106", "changed", CW),
                  ("kv_block::k_view / k_at", ["row-major K views: native K only",
                                               "(packed plane: no contiguous rows)"],
                   "kv_cache.hpp:3017-3038", "changed", CW)], link="calls",
             ops=["(no k_vnni.hpp operation:", "contiguous rows, memcpy)"],
             orefs=["kv_cache.hpp:2260, 2304"]),
    ]
    y = 34
    for r in rows:
        rh = r.get("h", RH)
        o.append(caller_cell(cx0, y, cw0, rh, r["caller"], r["cref"]))
        ax = ax0
        for i, (name, desc, ref, tag, w) in enumerate(r["api"]):
            for d in desc:
                fit(d, 9.5, w - 16, False, f"b3 {name}")
            o.append(fn_cell(ax, y, w, rh, name, desc, ref, tag))
            boxes.append((name, ref))
            if i == 1:
                # the arrow between the two cells, labelled with the call order
                link = r["link"]
                gx0, gx1 = ax - CG + 3, ax - 3
                if link.startswith("<-"):
                    o.append(arrow(fid, "ink", [(gx1, y + rh / 2), (gx0, y + rh / 2)],
                                   C["ink"], 1.2))
                    link = link[3:]
                else:
                    o.append(arrow(fid, "ink", [(gx0, y + rh / 2), (gx1, y + rh / 2)],
                                   C["ink"], 1.2))
                fit(link, 8.5, CG + 10, False, "b3 link")
                o.append(text((gx0 + gx1) / 2, y + rh / 2 - 5, link, 8.5, "middle",
                              fill=C["ink"]))
            ax += w + CG
        o.append(ops_cell(ox0, y, ow0, rh, r["ops"], r["orefs"]))
        o.append(arrow(fid, "ink", [(cx0 + cw0 + 2, y + rh / 2), (ax0 - 2, y + rh / 2)],
                       C["ink"]))
        o.append(arrow(fid, "ink", [(ax0 + aw0 + 2, y + rh / 2), (ox0 - 2, y + rh / 2)],
                       C["ink"]))
        y += rh + GAP
    boxes += [("store_k_block (caller)", "model.hpp:3232-3344"),
              ("save_k_impl (caller)", "model.hpp:3351-3457"),
              ("convert_pending_k_blocks (caller)", "model.hpp:3171-3180"),
              ("apply_page_tok / apply_dense_amx_page (callers)",
               "self_attention.hpp:1850-1872 (apply_page_tok), 1906-1937, 2019-2049; "
               "1749-1787 (apply_dense_amx_page)"),
              ("k_head_fn (caller)", "full.hpp:2747-2770; gof.hpp:78"),
              ("create_child_at_location / extend_leaf_edge / invalidate_restored_book (callers)",
               "full.hpp:654 (create_child_at_location, call at 669), 801 (extend_leaf_edge, "
               "call at 818), 3329 (invalidate_restored_book, call at 3346)"),
              ("book::append (caller)", "kv_cache.hpp:1361-1395"),
              ("store_row_major / store_row", "tensor/k_vnni.hpp:474-482, 344-362"),
              ("store_block", "tensor/k_vnni.hpp:382-420"),
              ("offset_bit / block_bit", "tensor/k_vnni.hpp:97-105"),
              ("block_to_vnni", "tensor/k_vnni.hpp:494-509"),
              ("qk_vnni_128x4", "amx_attn_iface.hpp:250-263"),
              ("qk_group", "kernels/k_vnni.hpp:59-65"),
              ("row_major_row / load_row", "tensor/k_vnni.hpp:458-472, 364-381"),
              ("block_to_rows", "tensor/k_vnni.hpp:511-524")]
    # private helpers band
    y += 2
    o.append(rect(20, y, 960, 178, "#fff", C["new"], 1.4, 4, "5 3"))
    o.append(text(30, y + 15, "private helpers (new) that the rows share", 11, weight=700,
                  fill=C["new"]))
    helpers = [
        ("k_state_ix", ["the state entry of a logical slot: layout_t::n_slots",
                        "for slot 0 under the EAGLE view, slot.i otherwise"],
         "kv_cache.hpp:2499-2505"),
        ("k_block_bits", ["the 16 bits of block c inside a k_rows_saved_ word",
                          "(static_assert: page_size == k_vnni::PAGE_TOKENS_64)"],
         "kv_cache.hpp:2507-2511"),
        ("k_block_is_vnni", ["the block bit of the offset's block, read with an",
                             "acquire load of k_vnni_blocks_[state_ix]"],
         "kv_cache.hpp:2513-2518"),
        ("k_with_storage_geometry", ["calls f with the geometry of the storage slot: the",
                                     "slot's declared geometry, or primary for EAGLE"],
         "kv_cache.hpp:2520-2532"),
        ("k_storage_readable", ["the storage is published (no KV restore in flight)",
                                "and the slot's arena is allocated"],
         "kv_cache.hpp:2534-2542"),
        ("book::eagle_view_active", ["the EAGLE storage view is selected: logical slot 0",
                                     "then addresses the extra physical slot"],
         "kv_cache.hpp:1082-1087"),
    ]
    hw, hh = 310, 60
    for i, (name, desc, ref) in enumerate(helpers):
        hx = 30 + (i % 3) * (hw + 10)
        hy = y + 22 + (i // 3) * (hh + 6)
        for d in desc:
            fit(d, 9.5, hw - 16, False, f"b3 helper {name}")
        o.append(fn_cell(hx, hy, hw, hh, name, desc, ref, None))
        boxes.append((name, ref))
    o.append(text(30, y + 170, "also changed, not drawn: page(page&&) copies the two "
                  "arrays (kv_cache.hpp:1958-1974); book::fill_storage_slot fills a packed "
                  "plane through detail::k_vnni_access, test-only (kv_cache.hpp:1829-1849)",
                  8.5, fill=C["muted"]))
    cap = ("B3, the function model. Each row is one call path: the caller in another "
           "file (with the thread in brackets), the page or book function of "
           "kv_cache.hpp it calls, and the typed operation of h/tron/tensor/k_vnni.hpp "
           "that touches the bytes. Each function cell says in one line what the function "
           "does, cites its definition and tags whether the PR adds (new) or changes it. "
           "The word on the arrow between two cells of a row is their call order: "
           "\"calls\" (the first calls the second), \"then\" (the caller calls the second "
           "after the first) or \"and\" (the caller calls both). In row 4 the arrow "
           "points left: the test-only k_block_to_vnni calls k_block_to_vnni_at, which "
           "the production caller reaches directly [kv_cache.hpp:2208-2211; "
           "model.hpp:3177]. The dashed band lists the new private helpers the rows "
           "share.")
    legend = [
        ("ctx", "grey box, thin grey outline: a caller in another file, with its thread in "
                "brackets (left column)"),
        ("box", "white box, ink outline: a function of kv_cache.hpp (the page / book API "
                "cells, and the private helpers): name in bold monospace, a one-line "
                "description, its citation and its tag"),
        ("lane", "white box, thin grey outline: the k_vnni.hpp operation the API function "
                 "takes (right column)"),
        ("ink dashed frame: the band of the new private helpers the rows share",
         "#fff", C["ink"], True, False),
        ("arrow", "ink arrow: a call: caller -> API function -> k_vnni.hpp operation; the "
                  "word between two API cells says how they relate: calls (the cell at the "
                  "arrow's tail calls the one at its head), then (the caller calls the "
                  "right after the left), and (the caller uses both)"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = a function this PR adds; 'changed' = a function it "
                     "changes"),
    ]
    return figure(fid, W, H, "Function model: callers, page and book API, k_vnni.hpp operations",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B4: sequencing model --------------------------------------------------------
def b4():
    fid = "kv_cache-b4"
    W, H = 1000, 540
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "rm": C["rm"],
                           "hw": C["hw"], "vnni": C["vnni"]})]
    boxes = []
    bw, bh, by = 190, 64, 150
    S = {"s0": 20, "s1": 265, "s2": 510, "s3": 790}
    # state words are the code's: "an incomplete block: row-major rows"
    # (model.hpp:3301), "a complete block may wait for its conversion" (684-685)
    o.append(state_box(S["s0"], by, bw, bh, "empty", "empty",
                       "no row bit", "kv_cache.hpp:2608-2617"))
    o.append(state_box(S["s1"], by, bw, bh, "rm", "incomplete, row-major",
                       "1..15 row bits, block bit clear", "kv_cache.hpp:677-686"))
    o.append(state_box(S["s2"], by, bw, bh, "pend", "complete, may wait",
                       "for its conversion: 16 row bits, bit clear", "kv_cache.hpp:684-685"))
    o.append(state_box(S["s3"], by, bw, bh, "vnni", "converted: VNNI",
                       "16 row bits, block bit set", "kv_cache.hpp:2618-2622"))
    boxes += [("k_rows_saved_ bits all clear: the empty state", "kv_cache.hpp:2608-2617"),
              ("incomplete block: row-major rows (row-major tail block)",
               "kv_cache.hpp:677-686; model.hpp:3301; Note [Row-major tail block] "
               "(tensor/k_vnni.hpp:437-456)"),
              ("complete, may wait for its conversion (16 row bits, block bit clear)",
               "kv_cache.hpp:684-685"),
              ("k_vnni_blocks_ bit set: the converted (VNNI) state", "kv_cache.hpp:2618-2622")]
    # S0 -> S1
    o.append(arrow(fid, "rm", [(S["s0"] + bw, by + 32), (S["s1"] - 2, by + 32)], C["rm"], 1.6))
    o.append(lines(237, 96, ["first row: set_k_row -> store_row_major",
                             "[any thread of the shared window],",
                             "then note_k_row_saved [main]"], 9.5, 12, "middle"))
    o.append(cite(237, 134, "kv_cache.hpp:2246-2258, 2164-2183", "middle"))
    # S1 self loop
    o.append(arrow(fid, "rm", [(S["s1"] + 180, by + bh), (S["s1"] + 180, by + bh + 14),
                               (S["s1"] + 125, by + bh + 14), (S["s1"] + 125, by + bh + 2)],
                   C["rm"], 1.4))
    o.append(text(S["s1"] + 152, by + bh + 36, "rows 2..15: the same path", 9.5, "middle"))
    # S1 -> S2
    o.append(arrow(fid, "pend", [(S["s1"] + bw, by + 32), (S["s2"] - 2, by + 32)],
                   C["pend"], 1.6))
    o.append(lines(482, 96, ["16th row bit: note_k_row_saved", "returns true; main pushes",
                             "{page, k_storage_of, c} onto pending_k_blocks_"], 9.5, 12,
                   "middle"))
    o.append(cite(482, 134, "kv_cache.hpp:2180-2182; model.hpp:3433-3435", "middle"))
    # S2 -> S3
    o.append(arrow(fid, "vnni", [(S["s2"] + bw, by + 32), (S["s3"] - 2, by + 32)],
                   C["vnni"], 1.6))
    o.append(lines(745, 96, ["forward end [main]:", "convert_pending_k_blocks ->",
                             "k_block_to_vnni_at: block_to_vnni per", "KV head, then the block bit (release)"],
                   9.5, 12, "middle"))
    o.append(cite(745, 146, "kv_cache.hpp:2213-2236; model.hpp:1847, 3173-3180", "middle"))
    # S0 -> S3 arc: the whole-block save
    o.append(arrow(fid, "vnni", [(S["s0"] + 60, by), (S["s0"] + 60, 44), (S["s3"] + 95, 44),
                                 (S["s3"] + 95, by - 2)], C["vnni"], 1.6))
    o.append(text(500, 32, "whole-block save of a run of 16 tokens: set_k_block per KV "
                  "head, then note_k_block_saved [any thread of the shared window]; no wait",
                  10, "middle", fill=C["vnni"], weight=600))
    o.append(cite(500, 58, "kv_cache.hpp:2273-2284, 2194-2200; model.hpp:3323-3340", "middle"))
    # S3 self loop: a row saved again
    o.append(arrow(fid, "vnni", [(S["s3"] + 180, by + bh), (S["s3"] + 180, by + bh + 14),
                                 (S["s3"] + 125, by + bh + 14), (S["s3"] + 125, by + bh + 2)],
                   C["vnni"], 1.4))
    o.append(lines(S["s3"] + 115, by + bh + 36, ["a row saved again: set_k_row ->",
                                                 "store_row into the VNNI column;",
                                                 "note_k_row_saved returns false"],
                   9, 11, "middle"))
    # anchored at the right margin: 8 px clear of the orange return line at s3 + 30
    o.append(cite(995, by + bh + 80, "kv_cache.hpp:2252-2254, 2161-2163"))
    # S3 -> S1: clear inside the block
    o.append(arrow(fid, "rm", [(S["s3"] + 30, by + bh), (S["s3"] + 30, 300),
                               (S["s1"] + 40, 300), (S["s1"] + 40, by + bh + 2)],
                   C["rm"], 1.6))
    o.append(lines(565, 316, ["clear_kv_complete_at at an offset inside the block "
                              "(offset % 16 != 0) [token tree, tree lock]: k_forget_row",
                              "runs block_to_rows for every KV head (when "
                              "k_storage_readable), then drops the row bits at and above",
                              "the offset and the block bit; the rows below stay readable"],
                   9.5, 12, "middle"))
    o.append(cite(565, 356, "kv_cache.hpp:2472-2477, 2552-2586", "middle"))
    # S0 -> S4: hardware attention
    s4x, s4y, s4w = 265, 390, 300
    o.append(state_box(s4x, s4y, s4w, bh, "hw", "records no row bits: stays row-major",
                       "hardware-scored operation: no row bit from a short run",
                       "kv_cache.hpp:731-735"))
    boxes.append(("records no row bits: stays row-major (hardware attention)",
                  "Note [Row-major blocks under hardware attention] (kv_cache.hpp:731-735)"))
    o.append(arrow(fid, "hw", [(S["s0"] + 30, by + bh), (S["s0"] + 30, s4y + 32),
                               (s4x - 2, s4y + 32)], C["hw"], 1.6))
    o.append(lines(S["s0"] + 42, 326, ["cached_operation_uses_hw:", "a short run's set_k_row",
                                       "stores the row row-major;", "save_k records no bit",
                                       "and queues nothing"], 9.5, 12))
    o.append(cite(S["s0"] + 42, 390, "model.hpp:3421-3426", "start"))
    o.append(arrow(fid, "hw", [(s4x + s4w - 30, s4y + bh), (s4x + s4w - 30, s4y + bh + 14),
                               (s4x + 200, s4y + bh + 14), (s4x + 200, s4y + bh + 2)],
                   C["hw"], 1.4))
    o.append(text(s4x + s4w - 18, s4y + bh + 13, "every further row of a short run: "
                  "set_k_row row-major, still no bit", 9))
    o.append(lines(585, s4y + 10, ["stays row-major: every reader takes the layout from the",
                                   "clear block bit; k_row_if_row_major returns the row in",
                                   "place for the FPGA staging; copy_from converts nothing.",
                                   "A whole-block save still stores VNNI and sets its bits"],
                   9.5, 12))
    o.append(cite(585, s4y + 62, "kv_cache.hpp:731-735, 750-753, 2332-2349; model.hpp:3340",
                  "start"))
    # notes: drop to empty; page copies
    o.append(rect(20, 478, 540, 50, C["soft"], C["line"], 1, 4))
    o.append(lines(30, 495, ["page copies (copy_storage_slot): a whole page keeps every state "
                             "(owner assignment, bits included);",
                             "any other range goes through row-major rows and re-converts "
                             "blocks whose 16 row bits are set"], 9.5, 12))
    o.append(cite(554, 524, "kv_cache.hpp:2732-2762"))
    o.append(rect(580, 478, 400, 50, C["soft"], C["line"], 1, 4))
    o.append(lines(590, 495, ["any state -> empty: clear_kv_complete_at at or below the",
                              "block's first offset drops the bits; the bytes are left alone"],
                   9.5, 12))
    o.append(cite(974, 524, "kv_cache.hpp:2549-2550"))
    cap = ("B4, the sequencing model: the life of one 16-token block of one storage "
           "slot. Boxes are states (the colours of B1), arrows are the operations of "
           "this PR with the thread in brackets. The upper path is the decode case "
           "(one row per step). The arc over the top is the prefill case (a whole block "
           "at once). The lower path is the hardware-attention policy. Under it save_k "
           "records no row bit for the rows a short run stores, so a block completed "
           "that way never converts. A whole-block save under the same policy still "
           "stores the VNNI layout and sets its bits [kv_cache.hpp:731-735, 750-753; "
           "model.hpp:3340, 3426].")
    legend = [
        ("empty", "grey dashed: the empty state, no row bit"),
        ("rm", "orange: the incomplete state: 1..15 row bits, row-major rows, block bit "
               "clear"),
        ("pend", "orange-red dashed: the complete state that waits for its conversion: 16 "
                 "row bits, block bit clear"),
        ("vnni", "blue: the converted state: 16 row bits, block bit set; blue text = the "
                 "whole-block save over the top"),
        ("hw", "yellow: the hardware-attention state: records no row bits, stays "
               "row-major"),
        ("orange arrow: a row-major transition: the first row, rows 2..15, and the clear "
         "inside a block (k_forget_row)", "arrow", C["rm"]),
        ("orange-red arrow: the 16th row bit: the block becomes complete and main pushes "
         "it onto pending_k_blocks_", "arrow", C["pend"]),
        ("blue arrow: a transition into or within the converted state: the conversion at "
         "the forward end, the whole-block save, a row saved again", "arrow", C["vnni"]),
        ("yellow arrow: the hardware-attention policy: a short run's rows under "
         "cached_operation_uses_hw, no bit recorded", "arrow", C["hw"]),
        ("ctx", "grey box, thin grey outline: a transition no arrow draws: page copies "
                "(copy_storage_slot), and any state -> empty (clear_kv_complete_at at or "
                "below the first offset)"),
        ("font_sans", "sans-serif = prose and, in this figure, the identifiers inside the "
                      "arrow labels and the state boxes (set_k_row, note_k_row_saved, "
                      "cached_operation_uses_hw, k_forget_row, ...)"),
        "font_cite",
    ]
    return figure(fid, W, H, "Sequencing model: the states of one 16-token block",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B5: interaction model -------------------------------------------------------
def b5():
    fid = "kv_cache-b5"
    W, H = 1000, 684
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    # time header. Block x ranges (schematic): minibatch 1 = 150..462, minibatch
    # 2 = 464..556, forward end = 558..798, between passes = 800..988.
    segs = [(150, 462, "minibatch 1: save_k window 1, then its attention jobs"),
            (464, 556, "minibatch 2"),
            (558, 798, "forward end"),
            (800, 994, "between passes (tree lock)")]
    for a, b, lab in segs:
        o.append(line(a, 66, b - 4, 66, C["muted"], 1))
        o.append(line(a, 60, a, 66, C["muted"], 1))
        o.append(line(b - 4, 60, b - 4, 66, C["muted"], 1))
        fit(lab, 9.5, b - a, False, "b5 seg")
        o.append(text((a + b - 4) / 2, 56, lab, 9.5, "middle", weight=600))
    o.append(text(20, 30, "one forward pass of one layer (time runs to the right, "
                  "durations not to scale), then the tree work between passes", 11,
                  weight=600))
    # lane labels: the actor and one 9 px line naming its functions (V1-V8); the
    # file names are in the footer note
    names = [("main thread", None), ("main helpers", None),
             ("attention workers", None), ("token tree", None)]
    LH, BH = 90, 76
    svg, x0, ys = lane_set(10, 100, 984, names, LH, 6)   # frame to x = 994
    o.append(svg)
    for lab, sub in [("main thread", "save_k_impl, run_forward"),
                     ("main helpers", "save_k_impl, run_main_help"),
                     ("attention workers", "apply_page_tok, k_head_fn"),
                     ("token tree", "clear_kv_complete_at")]:
        fit(sub, 9, 130, False, "b5 lane sub")
        o.append(text(18, ys[lab] + LH / 2 + 17, sub, 9, fill=C["muted"]))
    ym, yh, yw, yt = (ys[k] + 7 for k in ["main thread", "main helpers",
                                          "attention workers", "token tree"])
    # ---- the highlight band of minibatch 2 (a tint, no outline: drawn before
    # the blocks so that it never doubles a block border) -----------------------
    o.append(rect(464, ym - 4, 92, (yw + BH + 4) - (ym - 4), C["pend"], "none", 0, 4,
                  extra=' fill-opacity="0.10"'))
    o.append(text(464, 80, "the reader that forces the deferral (tinted band): minibatch "
                  "1's staging gather", 8.5, fill=C["pend"], weight=700))
    o.append(text(464, 91, "reads the block's rows row-major while minibatch 2 saves "
                  "its last rows [kv_cache.hpp:693-700]", 8.5, fill=C["pend"], weight=700))
    # ---- idle blocks first, text last (STYLE trap) ---------------------------
    idle = [
        (yh, 150, 88, ["wait: opened >= W", "(acquire)"], "3385-3389"),
        (ym, 326, 48, ["join", "(acquire)"], "3402-3416"),
        (yh, 390, 72, ["idle: the next", "kernel waits", "for the", "attention", "output"],
         "3107-3109"),
        (yh, 558, 30, ["idle"], None),
        (yh, 588, 210, ["idle"], None),
        (yw, 150, 216, ["wait: upstream_kvs_ready latch", "of the writing minibatches"],
         "common.hpp:1159-1162"),
        (yw, 630, 52, ["exits with", "run()"], "1836"),
        (yt, 150, 648, ["waits: tree work runs between forward passes, with the tree lock held"],
         "kv_cache.hpp:2550-2551, 701-704"),
    ]
    for y, x, w, ls, ref in idle:
        o.append(lane_block(x, y, w, BH, ls, "#fff", C["muted"], True, 8.5, ref))
    # ---- work blocks -----------------------------------------------------------
    # The two FPGA staging blocks are neutral work (soft fill): yellow is the
    # hardware-scored block state of B4, not "FPGA-related work".
    work = [
        # main
        (ym, 150, 88, ["save_k window 1:", "k_store_cut_units", "opened++ (release)"],
         C["soft"], C["ink"], "3380-3384"),
        (ym, 238, 88, ["claim loop (units)", "store_k_block"], C["unit_fill"], C["unit"],
         "3391-3397"),
        (ym, 374, 88, ["note_k_row_saved", "pending_k_blocks_", "mark_k_complete",
                       "count_down"], C["rows_fill"], C["rows"], "3426-3456"),
        (ym, 464, 92, ["save_k window 2:", "store_k_block", "join (acquire)",
                       "note_k_row_saved", "pending_k_blocks_"], C["unit_fill"], C["unit"],
         "3351-3457"),
        (ym, 558, 30, ["run()", "joins"], C["soft"], C["ink"], "1836"),
        (ym, 588, 92, ["wait_for_coop_gof", "[FPGA staging]"], C["soft"], C["ink"], "1840"),
        (ym, 680, 118, ["convert_pending_k_blocks", "-> k_block_to_vnni_at",
                        "block bit (release)"], C["pend_fill"], C["pend"], "1847, 3173"),
        # helpers
        (yh, 238, 100, ["claim loop (units)", "store_k_block:", "set_k_block +",
                        "note_k_block_saved"], C["unit_fill"], C["unit"], "3391-3397"),
        (yh, 338, 52, ["finished++", "(release)"], C["soft"], C["ink"], "3398-3401"),
        (yh, 464, 92, ["claim loop of", "window 2", "(set_k_row rows)"], C["unit_fill"],
         C["unit"], "3391-3397"),
        # workers
        (yw, 366, 96, ["attention jobs:", "k_vnni_blocks,", "k_packed ->",
                       "qk_vnni_128x4 |", "qk_group | dotter"], C["q_fill"], C["q"],
         ["1924-1937,", "2019-2049"]),
        (yw, 464, 92, ["help_drain_gof", "[FPGA staging]:", "k_row_if_row_major",
                       "get_k_row (gather)"], C["soft"], C["ink"],
         ["3570-3576;", "full.hpp:", "2762-2767"]),
        (yw, 558, 70, ["attention jobs", "of minibatch 2"], C["q_fill"], C["q"], "1924-1937"),
        # tree
        (yt, 800, 104, ["clear_kv_complete_at", "-> k_forget_row:", "block_to_rows,",
                        "fetch_and (release)"], C["rm_fill"], C["rm"],
         ["2472-2477,", "2552-2586"]),
        (yt, 904, 84, ["book::append ->", "copy_from ->", "copy_storage_slot",
                       "block_to_rows /", "block_to_vnni"], C["rm_fill"], C["rm"], "2688-2811"),
    ]
    for y, x, w, ls, fill, stroke, ref in work:
        o.append(lane_block(x, y, w, BH, ls, fill, stroke, False, 8.5, ref))
    boxes += [
        ("save_k window (k_store_cut_units, opened, claim loop, join, finished)",
         "model.hpp:3380-3416; batch::k_store_window (common.hpp:1167-1193)"),
        ("note_k_row_saved loop, mark_k_complete, count_down", "model.hpp:3420-3457"),
        ("run() joins the workers", "model.hpp:1822-1836"),
        ("wait_for_coop_gof", "model.hpp:1838-1840, 3583-3592"),
        ("convert_pending_k_blocks -> k_block_to_vnni_at",
         "model.hpp:1842-1847, 3171-3180; kv_cache.hpp:2213-2236"),
        ("finished (helpers: wait for opened, claim loop, finished++)", "model.hpp:3385-3401"),
        ("the helpers are idle while main runs save_k (their next kernel waits for "
         "the attention output)", "Note [Shared block save] (model.hpp:3107-3109)"),
        ("attention jobs read k_vnni_blocks / k_packed after the latch",
         "self_attention.hpp:1924-1937, 2019-2049; kv_cache.hpp:697-699; common.hpp:1159-1162"),
        ("help_drain_gof (k_row_if_row_major / get_k_row)",
         "model.hpp:3570-3576; full.hpp:2762-2767; kv_cache.hpp:693-700"),
        ("run (the attention workers exit when run() joins them)", "model.hpp:1822-1836"),
        ("clear_kv_complete_at -> k_forget_row", "kv_cache.hpp:2472-2477, 2552-2586"),
        ("book::append -> copy_from -> copy_storage_slot", "kv_cache.hpp:1361-1395, 2688-2811"),
        ("tree work between passes under the tree lock", "kv_cache.hpp:2550-2551, 701-704"),
    ]
    # ---- notes under the lanes -------------------------------------------------
    ny = ys["token tree"] + LH + 28
    o.append(text(20, ny, "Why the conversion waits for the forward end", 11, weight=700))
    left = [
        "a grain of 8 tokens may split a 16-token block across minibatch 1 and 2;",
        "the staging gather of minibatch 1 (help_drain_gof) reads the block's rows",
        "row-major while minibatch 2 saves its last rows [kv_cache.hpp:693-700].",
        "The attention workers read a pending page only after every minibatch that",
        "writes it counted upstream_kvs_ready down [kv_cache.hpp:697-699; model.hpp:3455-3456].",
        "After wait_for_coop_gof no reader of the pass is left [model.hpp:1838-1847].",
    ]
    for s in left:
        fit(s, 9.5, 490, False, "b5 left")
    o.append(lines(20, ny + 16, left, 9.5, 12))
    o.append(text(520, ny, "Who publishes the bits, who reads them", 11, weight=700))
    right = [
        "note_k_block_saved: fetch_or acq_rel, then release [kv_cache.hpp:2198-2199]",
        "k_block_to_vnni_at: fetch_or release after the last head [kv_cache.hpp:2234]",
        "readers: k_vnni_blocks, k_block_is_vnni, acquire [kv_cache.hpp:2134, 2516]",
        "k_forget_row, copy_storage_slot: fetch_and / store release under the tree",
        "lock, no reader runs [kv_cache.hpp:2550-2551, 2583-2584, 2780-2783]",
        "helpers: finished++ release; main joins with acquire [model.hpp:3399, 3404]",
        "units may share a block; a writer touches only its own token's bytes: its own",
        "row-major row, its own 64 pair slots, or the whole block alone [2252-2258, 2282-2283]",
    ]
    for s in right:
        fit(s, 9.5, 460, False, "b5 right")
    o.append(lines(520, ny + 16, right, 9.5, 12))
    boxes.append(("a writer touches only its own token's bytes (store_row_major, "
                  "store_row, store_block)", "kv_cache.hpp:2252-2258, 2282-2283; "
                  "tensor/k_vnni.hpp:344-348, 474-482"))
    # legend, two rows
    ly = ny + 122
    o.append(rect(20, ly, 40, 14, "#fff", C["muted"], 1, 2, "4 3"))
    o.append(text(66, ly + 11, "waiting / idle", 10))
    o.append(rect(150, ly, 40, 14, C["soft"], C["ink"], 1.2, 2))
    o.append(text(196, ly + 11, "work (incl. the FPGA staging)", 10))
    chips = [("unit", "K row stores (work units)"), ("rows", "saved-row bits"),
             ("q", "attention jobs"),
             ("pend", "conversion"), ("rm", "tree work on rows")]
    cx, cy = 400, ly
    for i, (key, lab) in enumerate(chips):
        if i == 3:
            cx, cy = 400, ly + 22
        o.append(rect(cx, cy, 22, 14, C[key + "_fill"], C[key], 1.2, 2))
        o.append(text(cx + 27, cy + 11, lab, 10))
        cx += 27 + text_width(lab, 10) + 14
    o.append(text(20, ly + 52, "lane citations without a file name are line numbers of "
                  "model.hpp (main, helpers, workers) or kv_cache.hpp (token tree); "
                  "the full list is under \"Boxes and their sources\".", 9, fill=C["muted"]))
    cap = ("B5, the interaction model: one forward pass of one layer and the tree work "
           "between passes, one lane per actor (the token tree lane is the scheduler's "
           "tree work under the tree lock, not a thread). Both minibatches of the worked "
           "example hold more than k_store_block = 16 items, so both open a shared "
           "window [model.hpp:3189-3200]. The tinted band marks why the "
           "conversion of a block completed row by row waits for the forward end. The "
           "cooperative GOF staging gather (the copy of K rows for the FPGA) of an "
           "earlier minibatch reads the block row-major while a later minibatch saves "
           "its last rows [kv_cache.hpp:693-700]. Clears and page copies run on the "
           "token tree between passes with the tree lock held, so they need no bit "
           "synchronisation beyond it.")
    legend = [
        ("grey dashed outline: waiting or idle: the wait on opened, the join, the "
         "upstream_kvs_ready latch, idle helpers, the token tree during the pass",
         "#fff", C["muted"], True, False),
        ("ctx_ink", "grey fill, ink outline: other work: opening the window, finished++, "
                    "the join of run(), wait_for_coop_gof, and the FPGA staging gather "
                    "(help_drain_gof)"),
        ("unit", "grey-blue: the K row stores of a shared save_k window: the claim loop "
                 "over work units (store_k_block)"),
        ("rows", "green: main records the saved-row bits after the join (note_k_row_saved, "
                 "pending_k_blocks_, mark_k_complete, count_down)"),
        ("q", "purple: the attention jobs of the attention workers (k_vnni_blocks, "
              "k_packed -> qk_vnni_128x4 | qk_group | dotter)"),
        ("pend_solid", "orange-red: the conversion at the forward end "
                       "(convert_pending_k_blocks -> k_block_to_vnni_at, block bit "
                       "release); orange-red text = the note on the tinted band"),
        ("pale orange-red band (the conversion colour at 10 % opacity), no outline: "
         "minibatch 2, where minibatch 1's staging gather reads the block row-major while "
         "the last rows are saved", C["pend"], "none", False, False, 0.10),
        ("rm", "orange: the tree work on rows between passes (clear_kv_complete_at -> "
               "k_forget_row; book::append -> copy_storage_slot)"),
        ("font_sans", "sans-serif = prose and, in this figure, the identifiers inside the "
                      "lane blocks and the notes (store_k_block, note_k_row_saved, "
                      "convert_pending_k_blocks, k_forget_row, ...)"),
        "font_cite",
    ]
    return figure(fid, W, H, "Interaction model: which thread touches the K layout state when",
                  "".join(o), cap, boxes=boxes, legend=legend)
