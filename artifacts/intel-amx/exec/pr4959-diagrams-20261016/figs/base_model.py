"""Base diagrams B1-B5 of the PR 4959 page for h/tron/models/model.hpp (key "model").

Worked example (STYLE.md, the same on all three pages): page 7, storage slot 5
(state entry 5), KV head 0, a VNNI slot, CPU attention. The prefill pass saved
offsets 0..40 through the shared window of PR 4958 (units [0,16) [16,32)
[32,41)): units 0 and 1 were whole-block saves, unit 2 (9 tokens) went row by
row into the row-major form of block 2. Decode steps then save offsets 41, 42,
... one per step. The step that saves offset 47 completes block 2:
note_k_row_saved returns true, save_k queues {&page 7, {slot 5, 5}, block 2},
and the forward end converts it (convert_pending_k_blocks).

Every label is an identifier or a comment phrase of the code; every box cites
the line or Note that defines it (head line numbers of model.hpp at
6b081187e1, or <file>:<line> for other files).

Exports for the change diagrams (from base_model import ...):
  constants: EXAMPLE, BLOCK_STATE_NAMES
  building blocks: fit, tag, field_row, fn_box, step_box, stmt_row, note_box,
    block_state_box, bits_strip, page_strip, lanes_grid, crit_frame, CRIT_SW
"""
import sys

from svg_helpers import (C, arrow, block_cell, card_arrow, cite, figure, fn_cell, lane,
                         line, lines, marker_defs, rect, text, text_width, work_block)

# ---- the worked example ----------------------------------------------------
EXAMPLE = dict(page=7, slot=5, state_ix=5, kv_head=0, token=37, block=2, lane=5,
               prefill_items=41, units=[(0, 16), (16, 32), (32, 41)],
               rows_after_prefill="bits 0..40", blocks_after_prefill="0b0011",
               completing_offset=47, blocks_after_convert="0b0111")

# The block states, named the same on all three pages (STYLE.md item 1).
BLOCK_STATE_NAMES = {
    "empty": "no row saved",
    "rm": "row-major rows",
    "pend": "complete, may wait",
    "vnni": "converted: VNNI layout",
    "hw": "row-major, no bits (hardware attention)",
}

# The critical path of a wall-clock-lanes figure: thick solid red frame.
CRIT = C["crit"]
CRIT_SW = 2.6


def crit_frame(x, y, w, h):
    return rect(x, y, w, h, "none", CRIT, CRIT_SW, 2)


def fit(s, size, w, mono=False, where=""):
    """Warn on stderr when a string is wider than w px (see the PNG too)."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w}", file=sys.stderr)
    return s


def tag(x, y, s, col=None, anchor="end", size=9.5):
    return text(x, y, s, size, anchor, fill=col or C["new"], weight=700)


# ---- building blocks -----------------------------------------------------------
def field_row(x, y, w, h, name, desc, ref, tag_=None, fill="#fff", stroke=C["ink"],
              dash=None, name_size=10, desc_size=9):
    """One field of a data box: name (mono, bold), its citation at the right of
    the same line, then up to two description lines; an optional tag."""
    o = [rect(x, y, w, h, fill, stroke, 1.1, 3, dash)]
    fit(name, name_size, w - 12, True, f"field_row name {name}")
    o.append(text(x + 6, y + 13, name, name_size, mono=True, weight=600))
    o.append(cite(x + w - 4, y + h - 4, ref))
    ds = desc if isinstance(desc, (list, tuple)) else [desc]
    for s in ds:
        fit(s, desc_size, w - 12, False, f"field_row {name}")
    o.append(lines(x + 6, y + 25, ds, desc_size, 11))
    if tag_:
        col = C["new"] if tag_.startswith("new") else (
            C["gone"] if tag_.startswith("removed") else C["muted"])
        nx = x + 6 + text_width(name, name_size, True) * 1.08 + 8
        o.append(text(nx, y + 13, tag_, 8.5, fill=col, weight=700))
    return "".join(o)


def fn_box(x, y, w, h, name, desc, ref, tag_=None, fill="#fff", stroke=C["ink"]):
    """fn_cell with a width check of its lines."""
    ds = desc if isinstance(desc, (list, tuple)) else [desc]
    for s in ds:
        fit(s, 9.5, w - 14, False, f"fn_box {name}")
    fit(name, 11.5, w - 14, True, f"fn_box name {name}")
    return fn_cell(x, y, w, h, name, ds, ref, tag=tag_, fill=fill, stroke=stroke)


def step_box(x, y, w, h, title, sub, ref, fill="#fff", stroke=C["ink"], dash=None,
             num=None, title_size=10.5, sub_size=9, crit=False):
    """A protocol step: optional step number, a title (mono, bold), sub lines,
    and the citation in the lower-right corner. dash = a waiting step; crit =
    a step on the critical path (thick solid red frame over the box)."""
    o = [rect(x, y, w, h, fill, stroke, 1.3 if dash else 1.2, 4, dash)]
    if crit:
        o.append(crit_frame(x, y, w, h))
    tx = x + 8
    if num is not None:
        o.append(rect(x + 8, y + 5, 40, 14, C["ink"], C["ink"], 1, 3))
        o.append(text(x + 28, y + 15.5, f"step {num}", 8.5, "middle", fill="#fff",
                      weight=700))
        tx = x + 54
    fit(title, title_size, w - (tx - x) - 6, True, f"step {title}")
    o.append(text(tx, y + 15, title, title_size, mono=True, weight=600))
    for s in sub:
        fit(s, sub_size, w - 14, False, f"step sub {title}")
    o.append(lines(x + 8, y + 29, sub, sub_size, 11.5))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def stmt_row(x, y, w, h, code, desc, ref, stroke=C["ink"], fill="#fff", dash=None):
    """One statement of a function body: 1-2 code lines (mono), a plain-English
    line, and the citation in the lower-right corner."""
    o = [rect(x, y, w, h, fill, stroke, 1, 3, dash)]
    cs = code if isinstance(code, (list, tuple)) else [code]
    ty = y + 13
    for c_ in cs:
        fit(c_, 9, w - 12, True, "stmt")
        o.append(text(x + 6, ty, c_, 9, mono=True, weight=600))
        ty += 12
    if desc:
        fit(desc, 9, w - 12, False, "stmt desc")
        o.append(text(x + 6, ty, desc, 9, fill=C["muted"]))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def note_box(x, y, w, h, title, body, ref, stroke=C["line"], fill=None, dash=None,
             title_mono=False, size=9):
    """A context note (grey by default): a bold title and plain lines."""
    o = [rect(x, y, w, h, fill or C["soft"], stroke, 1, 4, dash)]
    o.append(text(x + 8, y + 15, title, 10.5, mono=title_mono, weight=700))
    for s in body:
        fit(s, size, w - 14, False, f"note {title}")
    o.append(lines(x + 8, y + 29, body, size, 11))
    if ref:
        o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def block_state_box(x, y, w, h, state, title, sub, ref, size=10.5):
    """A 16-token block drawn by its layout state (block_cell colours) with a
    title, sub lines and a citation."""
    o = [block_cell(x, y, w, h, state)]
    fit(title, size, w - 8, True, f"block_state {title}")
    o.append(text(x + w / 2, y + 15, title, size, "middle", True, weight=600))
    for s in sub:
        fit(s, 9, w - 8, False, f"block_state sub {title}")
    o.append(lines(x + w / 2, y + 29, sub, 9, 11, "middle"))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def bits_strip(x, y, n_set, w=320, h=10, hi=None, label=None):
    """k_rows_saved_ of one state entry as 64 squares (bits 0..n_set-1 set),
    grouped by 16; an optional highlighted bit."""
    cell = (w - 3 * 6) / 64
    o = []
    cx = x
    for i in range(64):
        if i > 0 and i % 16 == 0:
            cx += 6
        on = i < n_set
        if hi is not None and i == hi:
            o.append(rect(cx, y, cell, h, C["hi_fill"], C["ink"], 1.2, 1))
        elif on:
            o.append(rect(cx, y, cell, h, C["rows_fill"], C["rows"], 0.8, 1))
        else:
            o.append(rect(cx, y, cell, h, "#fff", C["empty"], 0.8, 1))
        cx += cell
    if label:
        o.append(text(x, y - 3, label, 8.5, mono=True, fill=C["muted"]))
    return "".join(o), cx


def page_strip(x, y, states, w=320, h=22, labels=True, hi_token=None):
    """One page as its 4 blocks drawn by state: states = ['vnni', 'vnni',
    'rm', 'empty']. An optional token outlined in the worked example's cell."""
    bw = (w - 3 * 6) / 4
    o = []
    for c, st in enumerate(states):
        bx = x + c * (bw + 6)
        o.append(block_cell(bx, y, bw, h, st, f"block {c}", 9.5))
        if hi_token is not None and hi_token // 16 == c:
            t = hi_token % 16
            tx = bx + (t + 0.5) * bw / 16
            o.append(rect(tx - 3, y + h + 2, 6, 6, C["hi_fill"], C["ink"], 1, 1))
    if labels:
        for c in range(4):
            o.append(text(x + c * (bw + 6), y + h + 10 + (8 if hi_token is not None else 0),
                          f"{16 * c}", 8.5, "start", True, fill=C["muted"]))
        o.append(text(x + w, y + h + 10 + (8 if hi_token is not None else 0), "63", 8.5,
                      "end", True, fill=C["muted"]))
    return "".join(o)


def lanes_grid(x, y, w, labels, lane_h=56, gap=6):
    """Wall-clock lanes: labels = [(label, sub), ...]. Returns (svg, lane_ys,
    time_x0) where time_x0 is where the time axis starts (140 px gutter)."""
    o = []
    ys = []
    x0 = x + 140
    for i, (lab, sub) in enumerate(labels):
        ly = y + i * (lane_h + gap)
        svg, x0 = lane(x, ly, w, lane_h, lab, sub)
        o.append(svg)
        ys.append(ly)
    return "".join(o), ys, x0


# ---- B1: data model --------------------------------------------------------
def b1():
    fid = "model-b1"
    W, H = 1000, 704
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "muted": C["muted"]})]
    boxes = []
    AX, AW = 20, 290
    BX, BW = 350, 300
    CX, CW = 690, 290

    # column A: state (model.hpp)
    o.append(rect(AX, 40, AW, 356, C["soft"], C["ink"], 1.2, 6))
    o.append(text(AX + 8, 56, "state (model.hpp)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, 56, "model.hpp:1115"))
    boxes.append(("state (model.hpp)", "model.hpp:1115 (struct state); the members cited on each row"))
    rx, rw = AX + 12, AW - 24
    o.append(field_row(rx, 66, rw, 54, "token_jobs / token_jobs_do_kv",
                       ["job -> token_id; 1 = the job needs KV work this",
                        "forward (its K row is saved), 0 = skipped"],
                       "model.hpp:1157-1158"))
    boxes.append(("token_jobs / token_jobs_do_kv", "model.hpp:1157-1158"))
    o.append(field_row(rx, 126, rw, 54, "attention_operation_uses_hw",
                       ["one byte per attention operation, decided once",
                        "per model; read by cached_operation_uses_hw"],
                       "model.hpp:1248; 1529", fill=C["hw_fill"], stroke=C["hw"]))
    boxes.append(("attention_operation_uses_hw / cached_operation_uses_hw",
                  "model.hpp:1248 (member), 1529 (reader)"))
    o.append(field_row(rx, 186, rw, 54, "k_store_block",
                       ["= k_vnni::BLOCK_TOKENS_16 (16 tokens): the size of",
                        "one block save; a shorter run goes row by row"],
                       "model.hpp:3149-3150"))
    boxes.append(("k_store_block", "model.hpp:3149-3150"))
    o.append(field_row(rx, 246, rw, 68, "pending_k_blocks_",
                       ["std::vector<pending_k_block>: the blocks this pass",
                        "completed through runs shorter than a block, for",
                        "the operations the hardware attention does not score"],
                       "model.hpp:3152-3166", tag_="new", fill=C["pend_fill"],
                       stroke=C["pend"], dash="5 3"))
    boxes.append(("pending_k_blocks_", "model.hpp:3166 (member); comment 3152-3160"))
    o.append(field_row(rx, 320, rw, 68, "convert_pending_k_blocks()",
                       ["main thread, at the forward end: k_block_to_vnni_at",
                        "per entry, then clear; a 'convert_k_blocks' trace",
                        "event carries the entry count"],
                       "model.hpp:3168-3177", tag_="new"))
    boxes.append(("convert_pending_k_blocks", "model.hpp:3168-3177"))

    # column A below: the batch
    by = 410
    o.append(rect(AX, by, AW, 162, C["soft"], C["ink"], 1.2, 6))
    o.append(text(AX + 8, by + 16, "batch (one minibatch)", 11.5, mono=True, weight=700))
    o.append(cite(AX + AW - 4, by + 16, "common.hpp:1019"))
    boxes.append(("batch", "common.hpp:1019 (struct batch)"))
    o.append(field_row(rx, by + 26, rw, 54, "items",
                       ["std::vector<token_job_id>: the token jobs of the",
                        "minibatch in order (41 in the example's prefill)"],
                       "common.hpp:1111"))
    boxes.append(("items", "common.hpp:1111"))
    o.append(field_row(rx, by + 86, rw, 54, "k_store_window",
                       ["k_store_window_t: the shared K store window of PR",
                        "4958 (units, claim counter, join); context here"],
                       "common.hpp:1196-1219", fill=C["unit_fill"], stroke=C["unit"]))
    boxes.append(("k_store_window", "common.hpp:1196-1219"))
    o.append(text(AX + 8, by + 154, "1 forward pass -> several minibatches; 1 minibatch -> n_items items",
                  8.5, fill=C["muted"]))

    # column B: pending_k_block
    py = 40
    o.append(rect(BX, py, BW, 150, C["pend_fill"], C["pend"], 1.4, 6, "5 3"))
    o.append(text(BX + 8, py + 16, "pending_k_block", 11.5, mono=True, weight=700))
    o.append(tag(BX + 8 + text_width("pending_k_block", 11.5, True) * 1.08 + 8, py + 16,
                 "new", anchor="start", size=9))
    o.append(cite(BX + BW - 4, py + 16, "model.hpp:3161-3165"))
    boxes.append(("pending_k_block", "model.hpp:3161-3165"))
    o.append(lines(BX + 8, py + 32, ["page* pg", "typename page::k_storage_ref storage",
                                     "uint32_t block"], 9.5, 12, mono=True))
    o.append(lines(BX + 8, py + 72,
                   ["one entry = one 16-token block whose 16th row this pass",
                    "saved through a run shorter than a block; pushed by",
                    "save_k_impl on the main thread after the join; the storage",
                    "reference is taken at the save (k_storage_of), so a view",
                    "change before the forward end cannot redirect it"],
                   9, 11, fill=C["muted"]))
    o.append(arrow(fid, "pend", [(AX + AW, 270), (BX - 2, 172)], C["pend"]))
    o.append(text(BX + 2, 206, "1 pass -> 0..n entries", 9.5, fill=C["pend"], weight=600))

    # column B: the worked example entry
    ey = 212
    o.append(rect(BX, ey, BW, 98, C["hi_fill"], C["ink"], 1.2, 6))
    o.append(text(BX + 8, ey + 16, "worked example: the one entry of the pass", 10.5,
                  weight=700))
    o.append(lines(BX + 8, ey + 32,
                   ["{ pg = &page 7,",
                    "  storage = { offset = slot 5, state_ix = 5 },",
                    "  block = 47 / k_store_block = 2 }"], 9.5, 12, mono=True))
    o.append(text(BX + 8, ey + 78, "pushed by the decode step that saves offset 47",
                  9, fill=C["muted"]))
    o.append(cite(BX + BW - 4, ey + 94, "model.hpp:3426-3428"))
    boxes.append(("pending_k_blocks_.push_back (the worked example's entry)",
                  "model.hpp:3426-3428 (push_back of {&pg, pg.k_storage_of(slot), j / k_store_block})"))

    # column B: k_storage_ref
    ky = 326
    o.append(rect(BX, ky, BW, 86, "#fff", C["ink"], 1.2, 6))
    o.append(text(BX + 8, ky + 16, "page::k_storage_ref", 11.5, mono=True, weight=700))
    o.append(cite(BX + BW - 4, ky + 16, "kv_cache.hpp:2193-2196"))
    boxes.append(("page::k_storage_ref", "kv_cache.hpp:2193-2196"))
    o.append(lines(BX + 8, ky + 32, ["kv_storage_offset offset", "size_t state_ix"], 9.5, 12,
                   mono=True))
    o.append(lines(BX + 8, ky + 60,
                   ["the storage slot copied or converted, and the index of its",
                    "K layout state entry (the EAGLE entry for the EAGLE storage)"],
                   9, 11, fill=C["muted"]))
    o.append(arrow(fid, "ink", [(BX + 150, py + 150), (BX + 150, ey - 2)], C["ink"]))
    o.append(text(BX + 158, py + 160, "1 entry -> 1 page,", 8.5, fill=C["ink"], weight=600))
    o.append(text(BX + 158, py + 170, "1 k_storage_ref, 1 block index", 8.5, fill=C["ink"],
                  weight=600))
    o.append(arrow(fid, "ink", [(BX + 150, ey + 98), (BX + 150, ky - 2)], C["ink"]))
    o.append(text(BX + 158, ky - 7, "k_storage_of(slot 5) = {slot 5, 5}", 8.5, fill=C["ink"],
                  weight=600))

    # column C: the page
    o.append(rect(CX, 40, CW, 376, "#fff", C["ink"], 1.2, 6))
    o.append(text(CX + 8, 56, "page (64 token offsets)", 11.5, mono=True, weight=700))
    o.append(cite(CX + CW - 4, 56, "kv_cache.hpp:1994"))
    boxes.append(("page", "kv_cache.hpp:1994 (struct page); page_of at model.hpp:1771; "
                  "offset_in_page at kv_cache.hpp:2085"))
    o.append(text(CX + 10, 76, "1 page -> 4 blocks of 16 offsets (page_size / BLOCK_TOKENS_16)",
                  8, fill=C["muted"]))
    o.append(page_strip(CX + 10, 84, ["vnni", "vnni", "pend", "empty"], w=CW - 20,
                        hi_token=47))
    o.append(text(CX + 10, 136, "worked example after the step that saves offset 47:",
                  9, fill=C["muted"]))
    o.append(text(CX + 10, 148, "blocks 0, 1 converted; block 2 complete, may wait; block 3 empty",
                  8.5, fill=C["muted"]))
    o.append(field_row(CX + 12, 158, CW - 24, 54, "k_rows_saved_[5]",
                       ["one bit per page offset per storage slot;",
                        "bits 0..47 set after the step (note_k_row_saved)"],
                       "kv_cache.hpp:2639-2648", fill=C["rows_fill"], stroke=C["rows"]))
    boxes.append(("k_rows_saved_", "kv_cache.hpp:2639-2648"))
    s, _ = bits_strip(CX + 20, 217, 48, w=CW - 40, h=8, hi=47)
    o.append(s)
    o.append(field_row(CX + 12, 232, CW - 24, 54, "k_vnni_blocks_[5]",
                       ["one bit per block per storage slot: 0b0011 before",
                        "the forward end, 0b0111 after block 2 converts"],
                       "kv_cache.hpp:2649-2653", fill=C["blk_fill"], stroke=C["blk"]))
    boxes.append(("k_vnni_blocks_", "kv_cache.hpp:2649-2653"))
    o.append(field_row(CX + 12, 292, CW - 24, 54, "note_k_row_saved(slot, offset)",
                       ["sets the row bit; true when the row's block now has",
                        "all 16 rows saved and is not converted (queued)"],
                       "kv_cache.hpp:2207-2231", tag_="new", name_size=9.5))
    boxes.append(("note_k_row_saved", "kv_cache.hpp:2207-2231"))
    o.append(field_row(CX + 12, 352, CW - 24, 54, "note_k_block_saved(slot, c)",
                       ["after a whole-block save: the 16 row bits and the",
                        "block bit at once (set_k_block wrote VNNI)"],
                       "kv_cache.hpp:2240-2247", tag_="new", name_size=9.5))
    boxes.append(("note_k_block_saved", "kv_cache.hpp:2240-2247"))
    o.append(arrow(fid, "muted", [(BX + BW, ey + 40), (CX - 2, ey + 40)], C["muted"]))

    # bottom: the two KV-row stores of the page the model calls
    sy = 584
    o.append(text(BX, sy + 12, "the page's K row stores that store_k_block calls", 10.5,
                  weight=700))
    o.append(fn_box(BX, sy + 20, 300, 64, "page::set_k_row",
                    ["one token's row in the layout of the slot and of",
                     "the token's block: store_row_major into a row-major",
                     "block, store_row into a converted block"],
                    "kv_cache.hpp:2286-2291", tag_="changed"))
    boxes.append(("page::set_k_row", "kv_cache.hpp:2286-2291"))
    o.append(fn_box(CX, sy + 20, CW, 64, "page::set_k_block",
                    ["the 16 rows of one whole block stored at once in",
                     "the VNNI layout (store_block, FULL_BLOCK_0XFFFF);",
                     "the caller records it with note_k_block_saved"],
                    "kv_cache.hpp:2309-2321", tag_="changed"))
    boxes.append(("page::set_k_block", "kv_cache.hpp:2309-2321"))
    o.append(note_box(AX, sy + 20, AW, 64, "block states used on this page",
                      ["no row saved / row-major rows / complete, may wait /",
                       "converted: VNNI layout / row-major, no bits (hardware",
                       "attention): kv_cache.hpp Note [K VNNI storage]"],
                      "kv_cache.hpp:685-711"))
    boxes.append(("block states (Note [K VNNI storage])", "kv_cache.hpp:685-711"))
    ly = sy + 96
    items = [("vnni", "converted: VNNI layout"), ("rm", "row-major rows"),
             ("pend", "complete, may wait"), ("hw", "row-major, no bits (hardware attention)"),
             ("empty", "no row saved")]
    cx = AX
    for st, lab in items:
        o.append(block_cell(cx, ly, 26, 14, st))
        o.append(text(cx + 32, ly + 11, lab, 10))
        cx += 32 + text_width(lab, 10) + 18

    cap = ("The data model of the K store in model.hpp after PR 4959. The state keeps the "
           "deferred conversion list pending_k_blocks_ (one entry per block that a run "
           "shorter than a block completed in this pass). An entry names a page, a "
           "k_storage_ref and a block index. The page keeps two bit sets per storage "
           "slot. The worked example shows page 7 of storage slot 5 right after the "
           "decode step that saved offset 47: block 2 is complete and waits for the "
           "forward end.")
    legend = [
        ("ctx_ink", "grey box, ink outline: a struct of the model (state, batch) with its fields inside"),
        ("box", "white box, ink outline: a field, a function or the page: name in bold monospace, description in sans-serif"),
        ("pend", "orange-red dashed: the deferred conversion list and its entry type; block 2 of the page strip (complete, may wait)"),
        ("vnni", "blue: blocks 0 and 1 of the page strip (converted: VNNI layout)"),
        ("empty", "grey dashed: block 3 (no row saved); a clear bit of k_rows_saved_"),
        ("bit_clear", "white square: a clear bit of k_rows_saved_[5] (offsets 48..63)"),
        ("rows", "green: k_rows_saved_ and its set bits"),
        ("blk", "pink: k_vnni_blocks_"),
        ("hw", "yellow: the hardware-attention flag attention_operation_uses_hw"),
        ("unit", "grey-blue: the shared K store window of PR 4958 (context)"),
        ("hi", "pale yellow: the worked example's entry, and bit 47 / offset 47 of page 7"),
        ("rm", "orange: a block of row-major rows (legend row only)"),
        ("orange-red arrow: save_k pushes entries", "arrow", C["pend"]),
        ("arrow", "ink arrow: what one entry refers to"),
        ("arrow_muted", "grey arrow: the page an entry names"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR; 'changed' = changed by it"),
    ]
    return figure(fid, W, H, "Data model of the K store: state, pending list, page",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B2: function model ----------------------------------------------------
def b2():
    fid = "model-b2"
    W, H = 1000, 600
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "muted": C["muted"]})]
    boxes = []
    # row 1: the forward end
    o.append(text(20, 20, "row 1: the forward end (main thread, run_forward)", 11, weight=700))
    r1 = 28
    o.append(fn_box(20, r1, 150, 58, "run_forward",
                    ["one forward pass: every", "layer for this step"],
                    "model.hpp:1780", fill=C["soft"], stroke=C["line"]))
    boxes.append(("run_forward", "model.hpp:1780"))
    o.append(fn_box(190, r1, 170, 58, "plugin_state.run",
                    ["runs the layers; joins its", "workers before it returns"],
                    "model.hpp:1834", fill=C["soft"], stroke=C["line"]))
    boxes.append(("plugin_state.run", "model.hpp:1834; the obligation at 1820-1828"))
    o.append(fn_box(380, r1, 190, 58, "wait_for_coop_gof",
                    ["drains the cooperative GOF", "staging queue and submits"],
                    "model.hpp:3577", fill=C["hw_fill"], stroke=C["hw"]))
    boxes.append(("wait_for_coop_gof", "model.hpp:3572-3577"))
    o.append(fn_box(590, r1, 190, 58, "convert_pending_k_blocks",
                    ["converts the queued blocks, then", "clears the list (main thread)"],
                    "model.hpp:3170", tag_="new", fill=C["pend_fill"], stroke=C["pend"]))
    boxes.append(("convert_pending_k_blocks", "model.hpp:3168-3177"))
    o.append(fn_box(800, r1, 180, 58, "page::k_block_to_vnni_at",
                    ["block_to_vnni per KV head: 16", "rows saved, not converted"],
                    "kv_cache.hpp:2261", tag_="new"))
    boxes.append(("page::k_block_to_vnni_at", "kv_cache.hpp:2249-2261"))
    for x1, x2 in ((170, 188), (360, 378), (570, 588), (780, 798)):
        o.append(arrow(fid, "ink", [(x1, r1 + 29), (x2, r1 + 29)], C["ink"]))
    o.append(text(20, r1 + 72, "1 pass -> 1 call; 1 call -> 1 k_block_to_vnni_at per entry; "
                  "1 entry -> n_kv_heads block_to_vnni (tensor/k_vnni.hpp:466)", 8.5,
                  fill=C["muted"]))

    # row 2: save_k
    o.append(text(20, 130, "rows 2 and 3: the K store of one minibatch, the page functions it "
                  "calls and the tensor operations behind them", 11, weight=700))
    r2 = 138
    o.append(fn_box(20, r2, 170, 70, "run() / run_main_help",
                    ["generated plugin: run() calls", "save_k with worker 0, run_main_",
                     "help with its worker_ix (PR 4958)"],
                    "TronCpp.hs:3002; 2940", fill=C["soft"], stroke=C["line"]))
    boxes.append(("run() / run_main_help (generated)", "TronCpp.hs:3002 (main side), 2940 (helper side), 1364"))
    o.append(fn_box(210, r2, 150, 70, "save_k",
                    ["two overloads; both call", "save_k_impl with worker_ix",
                     "and n_workers"],
                    "model.hpp:3459; 3470"))
    boxes.append(("save_k", "model.hpp:3452-3459 and 3469-3470"))
    o.append(fn_box(380, r2, 200, 70, "save_k_impl",
                    ["stores the rows (shared window or", "alone), records the rows, queues",
                     "completed blocks, marks the tokens"],
                    "model.hpp:3345", tag_="changed"))
    boxes.append(("save_k_impl", "model.hpp:3339-3345"))
    o.append(arrow(fid, "ink", [(190, r2 + 35), (208, r2 + 35)], C["ink"]))
    o.append(arrow(fid, "ink", [(360, r2 + 35), (378, r2 + 35)], C["ink"]))
    # what save_k_impl calls
    cy = 230
    o.append(fn_box(20, cy, 180, 70, "k_store_shared",
                    ["the sharing decision, the", "same on every thread (PR 4958)"],
                    "model.hpp:3189", fill=C["soft"], stroke=C["line"]))
    boxes.append(("k_store_shared", "model.hpp:3186-3189"))
    o.append(fn_box(220, cy, 180, 70, "k_store_cut_units",
                    ["cuts the items into work units", "(main only, PR 4958)"],
                    "model.hpp:3201", fill=C["soft"], stroke=C["line"]))
    boxes.append(("k_store_cut_units", "model.hpp:3199-3201"))
    o.append(fn_box(420, cy, 200, 70, "store_k_block",
                    ["stores the K rows of items", "[task_begin, task_end): a whole",
                     "block at once, else row by row"],
                    "model.hpp:3238", tag_="changed"))
    boxes.append(("store_k_block", "model.hpp:3229-3238"))
    o.append(fn_box(640, cy, 170, 70, "the row-recording loop",
                    ["note_k_row_saved per item;", "queues a completed block",
                     "(main; not under hw attention)"],
                    "model.hpp:3413-3432", tag_="new"))
    boxes.append(("the row-recording loop", "model.hpp:3413-3432 (Note [K VNNI storage]: record this pass's rows)"))
    o.append(fn_box(830, cy, 150, 70, "the marks loop",
                    ["mark_k_complete per token,", "GOF credits, the latch"],
                    "model.hpp:3433-3449", fill=C["soft"], stroke=C["line"]))
    boxes.append(("the marks loop (mark_k_complete, credit_gof_save, upstream_kvs_ready)",
                  "model.hpp:3433-3449; kv_cache.hpp mark_k_complete"))
    for x in (110, 310, 520, 725, 905):
        o.append(arrow(fid, "ink", [(480, r2 + 70), (480, r2 + 80), (x, r2 + 80), (x, cy - 2)],
                       C["ink"]))
    o.append(text(600, r2 + 76, "in this order, left to right", 8.5, fill=C["muted"]))

    # row 3: the page API the two loops call
    r3 = 334
    o.append(fn_box(20, r3, 185, 70, "page::set_k_row",
                    ["one row in the layout of the", "token's block: store_row_major",
                     "or store_row (k_block_is_vnni)"],
                    "kv_cache.hpp:2291", tag_="changed"))
    boxes.append(("page::set_k_row", "kv_cache.hpp:2286-2291"))
    o.append(fn_box(225, r3, 185, 70, "page::set_k_block",
                    ["16 rows of one whole block in", "the VNNI layout (store_block,",
                     "FULL_BLOCK_0XFFFF); no mask"],
                    "kv_cache.hpp:2321", tag_="changed"))
    boxes.append(("page::set_k_block", "kv_cache.hpp:2309-2321"))
    o.append(fn_box(430, r3, 185, 70, "page::note_k_block_saved",
                    ["the 16 row bits and the block", "bit of a whole-block save,",
                     "after the last KV head"],
                    "kv_cache.hpp:2242", tag_="new"))
    boxes.append(("page::note_k_block_saved", "kv_cache.hpp:2240-2242"))
    o.append(fn_box(620, r3, 170, 70, "page::note_k_row_saved",
                    ["sets one row bit; true when", "the block is complete and",
                     "not converted yet"],
                    "kv_cache.hpp:2215", tag_="new"))
    boxes.append(("page::note_k_row_saved", "kv_cache.hpp:2207-2215"))
    o.append(fn_box(800, r3, 180, 70, "cached_operation_uses_hw",
                    ["does the FPGA score this", "operation's K? decided",
                     "once per model"],
                    "model.hpp:1529", fill=C["hw_fill"], stroke=C["hw"]))
    boxes.append(("cached_operation_uses_hw", "model.hpp:1528-1531"))
    # arrows from store_k_block to the three page stores, from the loop to note_k_row_saved
    o.append(arrow(fid, "ink", [(470, cy + 70), (470, cy + 80), (112, cy + 80), (112, r3 - 2)],
                   C["ink"]))
    o.append(arrow(fid, "ink", [(500, cy + 70), (500, cy + 80), (317, cy + 80), (317, r3 - 2)],
                   C["ink"]))
    o.append(arrow(fid, "ink", [(560, cy + 70), (560, cy + 80), (522, cy + 80), (522, r3 - 2)],
                   C["ink"]))
    o.append(arrow(fid, "ink", [(722, cy + 70), (722, r3 - 2)], C["ink"]))
    o.append(arrow(fid, "ink", [(780, cy + 70), (780, cy + 80), (905, cy + 80), (905, r3 - 2)],
                   C["ink"]))
    # tensor ops
    r4 = 428
    o.append(fn_box(20, r4, 185, 58, "store_row_major",
                    ["one memcpy of 128 bf16 = 4 whole", "lines into the row-major block"],
                    "k_vnni.hpp:445", fill=C["rm_fill"], stroke=C["rm"]))
    boxes.append(("store_row_major", "k_vnni.hpp:442-445"))
    o.append(fn_box(225, r4, 185, 58, "store_row",
                    ["4 scatters into the token's VNNI", "column (a row saved again only)"],
                    "k_vnni.hpp:316", fill=C["vnni_fill"], stroke=C["vnni"]))
    boxes.append(("store_row", "k_vnni.hpp:313-316"))
    o.append(fn_box(430, r4, 185, 58, "store_block",
                    ["16 rows transposed in registers,", "16 whole-line stores per panel"],
                    "k_vnni.hpp:363", fill=C["vnni_fill"], stroke=C["vnni"]))
    boxes.append(("store_block", "k_vnni.hpp:348-363"))
    o.append(fn_box(635, r4, 180, 58, "block_to_vnni",
                    ["16 load_row_major to the stack,", "then store_block in place"],
                    "k_vnni.hpp:466", fill=C["pend_fill"], stroke=C["pend"]))
    boxes.append(("block_to_vnni", "k_vnni.hpp:462-466"))
    o.append(arrow(fid, "ink", [(80, r3 + 70), (80, r4 - 2)], C["ink"]))
    o.append(arrow(fid, "ink", [(160, r3 + 70), (160, r3 + 80), (300, r3 + 80), (300, r4 - 2)],
                   C["ink"]))
    o.append(arrow(fid, "ink", [(317, r3 + 70), (317, r3 + 80), (522, r3 + 80), (522, r4 - 2)],
                   C["ink"]))
    o.append(arrow(fid, "pend", [(890, r1 + 58), (890, r1 + 68), (990, r1 + 68), (990, r4 + 29),
                                 (817, r4 + 29)], C["pend"]))
    o.append(text(980, r4 + 72, "k_block_to_vnni_at -> block_to_vnni, n_kv_heads calls", 8.5,
                  "end", fill=C["pend"], weight=600))
    o.append(note_box(20, 508, 960, 80, "who runs what",
                      ["Row 1 runs on the main thread once per forward pass, after the plugin joined its "
                       "workers and the staging drained.",
                       "Row 2 runs once per (layer, minibatch): every worker of a shared window stores "
                       "units; only main records rows, queues blocks and marks tokens.",
                       "Row 3: set_k_row and set_k_block may run on any thread of the window (disjoint "
                       "rows); note_k_block_saved publishes a block from the thread that stored it;",
                       "note_k_row_saved and cached_operation_uses_hw run on main."],
                      "model.hpp:3079-3146 (Note [Shared block save]); 3152-3160"))
    boxes.append(("who runs what (Note [Shared block save])", "model.hpp:3079-3146; 3152-3160"))
    cap = ("The function model: who calls what. Row 1 is the forward end, where the queued "
           "blocks convert. Row 2 is save_k_impl and its five parts in call order. Row 3 "
           "is the page API and the tensor operations behind it. Every cell says in one "
           "line what the function does and cites its definition. Cells in grey are "
           "unchanged context, yellow cells belong to the hardware attention, orange-red "
           "cells are the conversion.")
    legend = [
        ("box", "white box, ink outline: a function this PR adds or changes (name, one-line description, citation)"),
        ("ctx", "grey box, thin grey outline: an unchanged caller or callee (context)"),
        ("pend_solid", "orange-red: the conversion (convert_pending_k_blocks, block_to_vnni)"),
        ("hw", "yellow: the hardware attention (wait_for_coop_gof drains the FPGA staging; cached_operation_uses_hw)"),
        ("rm", "orange: store_row_major writes a row-major row"),
        ("vnni", "blue: store_row and store_block write the VNNI layout"),
        ("arrow", "ink arrow: a call"),
        ("orange-red arrow: k_block_to_vnni_at calls block_to_vnni per KV head", "arrow", C["pend"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR (in kv_cache.hpp where marked); 'changed' = changed by it"),
    ]
    return figure(fid, W, H, "Function model of save_k and the forward end", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- B3: sequencing model --------------------------------------------------
def b3():
    fid = "model-b3"
    W, H = 1000, 620
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "muted": C["muted"]})]
    boxes = []
    LX, LW = 20, 470   # left column: the prefill pass
    RX, RW = 510, 470  # right column: the completing decode step and the forward end
    o.append(text(LX, 20, "the prefill pass: 41 items of one user at page 7 offsets 0..40 "
                  "(layer 5, slot 5)", 11, weight=700))
    o.append(text(RX, 20, "the decode step that saves offset 47, and its forward end", 11,
                  weight=700))
    y = 30
    o.append(step_box(LX, y, LW, 56, "save_k_impl: the shared window opens (PR 4958)",
                      ["k_store_shared true (41 items > 16, 3 workers); k_store_cut_units:",
                       "unit_start = [0, 16, 32, 41] -> 3 units, one per block of page 7"],
                      "model.hpp:3369-3377", num=1))
    boxes.append(("save_k_impl: the shared window opens", "model.hpp:3369-3377; k_store_cut_units at 3201"))
    y += 64
    o.append(step_box(LX, y, LW, 72, "units 0 and 1: store_k_block, a run of 16",
                      ["present == FULL_BLOCK_0XFFFF; per KV head: set_k_block(slot, kv_head, c,",
                       "rows) -> store_block; then note_k_block_saved(slot, c): bits 0..15 / 16..31",
                       "and block bits 0 and 1 (any thread of the window may do this)"],
                      "model.hpp:3316-3333", num=2, fill=C["vnni_fill"], stroke=C["vnni"]))
    boxes.append(("units 0 and 1: a run of 16 (set_k_block, note_k_block_saved)", "model.hpp:3316-3333"))
    y += 80
    o.append(step_box(LX, y, LW, 72, "unit 2: store_k_block, a run of 9 (n < k_store_block)",
                      ["offsets 32..40: per (token, KV head) set_k_row -> block 2 is not converted",
                       "-> store_row_major: 4 whole 64-byte lines into the row-major form of",
                       "block 2; no bit is set here (the recording is main's, after the join)"],
                      "model.hpp:3297-3315", num=3, fill=C["rm_fill"], stroke=C["rm"]))
    boxes.append(("unit 2: a run of 9 (set_k_row -> store_row_major)",
                  "model.hpp:3297-3315; kv_cache.hpp:2291-2301"))
    y += 80
    o.append(step_box(LX, y, LW, 44, "main joins the helpers (finished == n_helpers)",
                      ["every unit is stored; every row store happens-before the next steps"],
                      "model.hpp:3394-3409", num=4))
    boxes.append(("main joins the helpers (finished == n_helpers)", "model.hpp:3394-3409"))
    y += 52
    o.append(step_box(LX, y, LW, 84, "the row-recording loop (main; not under hardware attention)",
                      ["for every item: note_k_row_saved(slot 5, j): offsets 0..31 return false",
                       "(their blocks are converted), offsets 32..40 set bits 32..40 and return",
                       "false (block 2 has 9 of 16 rows). Nothing is queued.",
                       "state: k_rows_saved_[5] = bits 0..40, k_vnni_blocks_[5] = 0b0011"],
                      "model.hpp:3413-3432", num=5, fill=C["rows_fill"], stroke=C["rows"]))
    boxes.append(("the row-recording loop (note_k_row_saved per item)", "model.hpp:3413-3432"))
    y += 92
    o.append(step_box(LX, y, LW, 44, "the marks loop and the downstream latch",
                      ["mark_k_complete per token, GOF credits, upstream_kvs_ready count_down"],
                      "model.hpp:3433-3449", num=6, fill=C["soft"], stroke=C["line"]))
    boxes.append(("the marks loop and the downstream latch", "model.hpp:3433-3449"))
    y += 52
    o.append(page_strip(LX + 60, y + 6, ["vnni", "vnni", "rm", "empty"], w=350, hi_token=37))
    o.append(text(LX, y + 20, "page 7:", 9.5, weight=700))
    o.append(text(LX, y + 56, "after the pass: block 2 holds 9 row-major rows (32..40); token 37 "
                  "(the small square) is at row_major_row", 8.5, fill=C["muted"]))
    y += 70
    o.append(note_box(LX, y, LW, 60, "decode steps for offsets 41..46 (one token per user per step)",
                      ["each step: not shared (8 items <= 16); n = 1 < 16 -> set_k_row ->",
                       "store_row_major; note_k_row_saved sets the bit and returns false;",
                       "block 2 grows row by row and stays row-major"],
                      "model.hpp:3297-3315; 3426"))
    boxes.append(("decode steps for offsets 41..46 (set_k_row, note_k_row_saved)", "model.hpp:3297-3315; 3419-3426"))

    # right column
    y = 30
    o.append(step_box(RX, y, RW, 56, "store_k_block: the run of 1 (offset 47)",
                      ["n = 1 < k_store_block: set_k_row(slot 5, kv_head, 47, row) per KV head ->",
                       "k_block_is_vnni false -> store_row_major: the 16th row of block 2"],
                      "model.hpp:3297-3315", num=7, fill=C["rm_fill"], stroke=C["rm"]))
    boxes.append(("store_k_block: the run of 1 (offset 47) -> set_k_row", "model.hpp:3297-3315"))
    y += 64
    o.append(step_box(RX, y, RW, 84, "the row-recording loop: note_k_row_saved(slot 5, 47) -> true",
                      ["before = bits 0..46; after = bits 0..47; (after & k_block_bits(2)) ==",
                       "k_block_bits(2) and block bit 2 clear -> true -> push_back",
                       "{&page 7, k_storage_of(slot 5) = {slot 5, 5}, 47 / 16 = 2}",
                       "state: k_rows_saved_[5] = bits 0..47, k_vnni_blocks_[5] still 0b0011"],
                      "model.hpp:3426-3428", num=8, fill=C["pend_fill"], stroke=C["pend"],
                      dash="5 3"))
    boxes.append(("note_k_row_saved(slot 5, 47) -> true: the entry is queued",
                  "model.hpp:3426-3428; kv_cache.hpp:2215-2231"))
    y += 92
    o.append(page_strip(RX + 60, y + 6, ["vnni", "vnni", "pend", "empty"], w=350, hi_token=47))
    o.append(text(RX, y + 20, "page 7:", 9.5, weight=700))
    o.append(text(RX, y + 56, "block 2: complete, may wait (16 rows saved, block bit clear); "
                  "readers still see row-major rows", 8.5, fill=C["muted"]))
    y += 70
    o.append(step_box(RX, y, RW, 70, "the rest of the pass: later layers, the attention, the staging",
                      ["save_k of the other layers queues their block 2 too (one entry per layer);",
                       "the cooperative GOF staging gather of an earlier minibatch may still read",
                       "block rows row-major (help_drain_gof on the attention workers)"],
                      "model.hpp:3152-3160; 3564", num=9, fill=C["hw_fill"], stroke=C["hw"]))
    boxes.append(("the cooperative GOF staging gather (help_drain_gof)", "model.hpp:3564; 3152-3160"))
    y += 78
    o.append(step_box(RX, y, RW, 44, "plugin_state.run returns; wait_for_coop_gof drains the staging",
                      ["no reader of a completed K block is left (the comment at 1840-1841)"],
                      "model.hpp:1834-1842", num=10, fill=C["soft"], stroke=C["line"]))
    boxes.append(("plugin_state.run returns; wait_for_coop_gof", "model.hpp:1834-1842"))
    y += 52
    o.append(step_box(RX, y, RW, 84, "convert_pending_k_blocks (main thread, the forward end)",
                      ["TRACE_EVENT 'convert_k_blocks' with the entry count; per entry:",
                       "page 7 -> k_block_to_vnni_at({slot 5, 5}, 2): 16 rows saved and bit clear ->",
                       "block_to_vnni(plane, 2) for every KV head (16 load_row_major to the stack,",
                       "store_block FULL_BLOCK_0XFFFF) -> block bit 2 set (release); list cleared"],
                      "model.hpp:3170-3177", num=11, fill=C["pend_fill"], stroke=C["pend"],
                      crit=True))
    boxes.append(("convert_pending_k_blocks", "model.hpp:3168-3177; kv_cache.hpp:2261-2283; k_vnni.hpp:466"))
    y += 92
    o.append(page_strip(RX + 60, y + 6, ["vnni", "vnni", "vnni", "empty"], w=350, hi_token=37))
    o.append(text(RX, y + 20, "page 7:", 9.5, weight=700))
    o.append(text(RX, y + 56, "k_vnni_blocks_[5] = 0b0111: token 37 now sits at k_vnni::index(37, 70) "
                  "= 5226;", 8.5, fill=C["muted"]))
    o.append(text(RX, y + 67, "the next pass may read block 2 with qk_group, and the AMX kernel once "
                  "block 3 converts too (0b1111)", 8.5, fill=C["muted"]))
    y += 80
    o.append(note_box(RX, y, RW, 48, "the hardware-attention variant of step 8",
                      ["cached_operation_uses_hw true: the loop is skipped; no bit for offsets",
                       "32..47, no entry; block 2 stays row-major (yellow in B5)"],
                      "model.hpp:3419; kv_cache.hpp:763-799", stroke=C["hw"], fill=C["hw_fill"]))
    boxes.append(("the hardware-attention variant (Note [Row-major blocks under hardware attention])",
                  "model.hpp:3419; kv_cache.hpp:763-799"))
    # the step order lines
    for X in (LX, RX):
        o.append(line(X + 28, 30, X + 28, 30, C["muted"]))
    cap = ("The sequencing model: the life of block 2 of page 7 from the prefill pass to the "
           "forward end that converts it (worked example). Left: the prefill pass stores two "
           "whole blocks and nine row-major rows, records the rows after the join and queues "
           "nothing. Right: the decode step that saves offset 47 completes the block, queues "
           "one entry, and the forward end converts it after the staging drained. The thick "
           "red frame is the serial main-thread step the PR adds to the forward end.")
    legend = [
        ("box", "white box, ink outline: a step of save_k_impl: the title in bold monospace, what happens in sans-serif"),
        ("vnni", "blue: a whole-block save and the converted blocks of the page strips"),
        ("rm", "orange: a run shorter than a block stored row-major, and the row-major block of the strips"),
        ("rows", "green: the row-recording loop (k_rows_saved_ bits)"),
        ("pend", "orange-red dashed: the queued entry and the block that waits (complete, may wait)"),
        ("pend_solid", "orange-red solid: the conversion at the forward end"),
        ("crit", "thick solid red frame: the serial main-thread step added to the forward end"),
        ("hw", "yellow: the FPGA staging and the hardware-attention variant"),
        ("ctx", "grey box: unchanged steps (the marks loop, run() returning, the decode steps)"),
        ("empty", "grey dashed: block 3 (no row saved)"),
        ("hi", "pale yellow square: token 37 or offset 47 in the page strips"),
        ("ink badge: the step number", C["ink"], C["ink"], False, False),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Sequencing model: the life of one block through the pass",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B4: interaction model (wall-clock lanes) ------------------------------
def b4():
    fid = "model-b4"
    W, H = 1000, 430
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"]})]
    boxes = []
    o.append(text(20, 18, "one decode forward pass (schematic: durations not to scale, "
                  "interleaving schematic)", 11, weight=700))
    labels = [("[main]", "worker_ix 0"), ("[main helpers]", "worker_ix 1 .. n-1"),
              ("[attention workers]", "the pool's last workers"),
              ("[forward end]", "main, after run()")]
    g, ys, x0 = lanes_grid(20, 30, 960, labels)
    o.append(g)
    boxes.append(("[main], [main helpers], [attention workers]",
                  "model.hpp:1800-1812 (the plugin's run owns the workers); TronCpp.hs:1364"))
    # idle blocks first, text last
    L = 36
    # main lane: layers
    xs = x0 + 10
    for i in range(3):
        o.append(work_block(xs, ys[0] + 10, 70, L, f"layer {i + 1}", C["soft"], C["ink"]))
        xs += 74
    o.append(work_block(xs, ys[0] + 10, 60, L, "...", C["soft"], C["ink"]))
    xs += 64
    o.append(work_block(xs, ys[0] + 10, 70, L, "layer 36", C["soft"], C["ink"]))
    xs += 74
    o.append(work_block(xs, ys[0] + 10, 56, L, "", "#fff", C["ink"], idle=True))
    o.append(text(xs + 28, ys[0] + 31, "join", 9, "middle"))
    main_end = xs + 56
    # inside a layer: save_k with the recording loop (small)
    o.append(rect(x0 + 10, ys[0] + 48, 70, 6, C["rows_fill"], C["rows"], 0.8, 1))
    o.append(text(x0 + 84, ys[0] + 53, "save_k: store, then the row-recording loop (main only)", 8,
                  fill=C["rows"], weight=600))
    # helpers lane
    xs = x0 + 10
    for i in range(3):
        o.append(work_block(xs, ys[1] + 10, 70, L, "kernels", C["soft"], C["ink"]))
        xs += 74
    o.append(work_block(xs, ys[1] + 10, 60, L, "...", C["soft"], C["ink"]))
    xs += 64
    o.append(work_block(xs, ys[1] + 10, 70, L, "kernels", C["soft"], C["ink"]))
    o.append(text(x0 + 10, ys[1] + 53, "a decode step has 8 items <= 16: the K store is not shared "
                  "(k_store_shared false)", 8, fill=C["muted"]))
    # attention workers lane
    xs = x0 + 10
    for i in range(3):
        o.append(work_block(xs, ys[2] + 10, 48, L, "attn", C["q_fill"], C["q"]))
        o.append(work_block(xs + 48, ys[2] + 10, 22, L, "", C["hw_fill"], C["hw"]))
        xs += 74
    o.append(work_block(xs, ys[2] + 10, 60, L, "...", C["soft"], C["ink"]))
    xs += 64
    o.append(work_block(xs, ys[2] + 10, 48, L, "attn", C["q_fill"], C["q"]))
    o.append(work_block(xs + 48, ys[2] + 10, 22, L, "", C["hw_fill"], C["hw"]))
    o.append(text(x0 + 10, ys[2] + 53, "yellow: help_drain_gof, the cooperative GOF staging gather: "
                  "it reads a block's rows row-major (model.hpp:3564)", 8, fill=C["muted"]))
    boxes.append(("help_drain_gof (the cooperative GOF staging gather)", "model.hpp:3560-3564"))
    # forward end lane
    fx = main_end + 4
    o.append(work_block(fx, ys[3] + 10, 90, L, "", "#fff", C["ink"], idle=True))
    o.append(text(fx + 45, ys[3] + 31, "wait_for_coop_gof", 8.5, "middle"))
    boxes.append(("wait_for_coop_gof", "model.hpp:3572-3577; called at 1838"))
    cx = fx + 94
    o.append(work_block(cx, ys[3] + 10, 110, L, "", C["pend_fill"], C["pend"]))
    o.append(crit_frame(cx, ys[3] + 10, 110, L))
    o.append(text(cx + 55, ys[3] + 27, "convert_pending_", 8.5, "middle", True, weight=600))
    o.append(text(cx + 55, ys[3] + 38, "k_blocks", 8.5, "middle", True, weight=600))
    boxes.append(("convert_pending_k_blocks", "model.hpp:3168-3177; called at 1842"))
    lx = cx + 114
    o.append(work_block(lx, ys[3] + 10, 90, L, "logits", C["soft"], C["ink"]))
    boxes.append(("logits (run_logits, the listener notifications)", "model.hpp:1845-1849"))
    o.append(text(fx, ys[3] + 53, "main thread: the conversion runs after the staging drained, "
                  "before the logits", 8, fill=C["muted"]))
    # annotation: the cost
    ay = ys[3] + 62 + 10
    o.append(rect(20, ay + 8, 960, 86, C["soft"], C["line"], 1, 4))
    o.append(text(28, ay + 23, "what the red frame costs (measured, the PR body)", 10.5, weight=700))
    o.append(lines(28, ay + 38,
                   ["PR #4959 body, Performance, trace pr4trace-20261015 (qwen3-4b, 8 users, prompt "
                    "1,024 tokens, CPU attention): the convert_k_blocks span runs on the forward thread "
                    "once every 16 decode steps",
                    "and converts 288 blocks (8 users x 36 layers) each time: 1.08 to 1.16 ms per run "
                    "at tp2, 1.17 to 1.20 ms at tp4, 3.7 to 4.2 us per block; 9 to 13 % of the pass it "
                    "runs in, 0.6 to 0.8 % of decode time",
                    "averaged over the 16 steps. The other 15 decode steps queue nothing (the list is "
                    "empty: convert_pending_k_blocks returns at once, model.hpp:3171)."],
                   8.5, 11))
    o.append(cite(976, ay + 90, "model.hpp:3170-3177; PR #4959 body"))
    boxes.append(("the measured cost of convert_k_blocks (trace pr4trace-20261015)",
                  "PR #4959 body, Performance; model.hpp:3172 (the trace event)"))
    o.append(text(20, ay + 112, "why not earlier: a block split across two minibatches of one pass "
                  "(grains of 8 tokens) is read row-major by the staging gather of the earlier "
                  "minibatch", 8.5, fill=C["muted"]))
    o.append(text(20, ay + 123, "while the later minibatch saves its last rows "
                  "(model.hpp:3152-3160; kv_cache.hpp:723-738).", 8.5, fill=C["muted"]))
    boxes.append(("why the conversion is at the forward end (Note [K VNNI storage])",
                  "model.hpp:3152-3160; kv_cache.hpp:723-738"))
    cap = ("The interaction model as wall-clock lanes: which thread touches a completed block "
           "when, over one decode forward pass. Solid blocks are work, dashed outlines are "
           "waiting. The attention workers drain the FPGA staging in their idle time and may "
           "read a block's rows row-major, so the conversion (the thick red frame, main's "
           "serial addition) runs only at the forward end, after wait_for_coop_gof. "
           "Durations are schematic. The one measured number is quoted with its source.")
    legend = [
        ("lane", "thin grey frame: one lane per thread (threads are lanes, never colours)"),
        ("ctx_ink", "grey block, ink outline: unchanged work (a layer, a kernel, the logits)"),
        ("idle", "ink dashed: waiting (the join, wait_for_coop_gof)"),
        ("q", "violet: the attention work of the workers"),
        ("hw", "yellow: help_drain_gof, the FPGA staging gather in the workers' idle time"),
        ("rows", "green bar: the row-recording loop inside save_k (main only)"),
        ("pend_solid", "orange-red: convert_pending_k_blocks"),
        ("crit", "thick solid red frame: the serial main-thread work this PR adds (its cost in the box below)"),
        ("ctx", "grey note: the measured cost and why the conversion is at the forward end"),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Threads over one decode pass and the forward end (wall-clock lanes)",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B5: decision model ----------------------------------------------------
def b5():
    fid = "model-b5"
    W, H = 1000, 640
    o = [marker_defs(fid, {"ink": C["ink"], "gone": C["gone"], "pend": C["pend"]})]
    boxes = []
    o.append(text(20, 20, "one run of store_k_block: n consecutive items of one 16-token block c of "
                  "one page (n <= 16, offsets distinct)", 11, weight=700))
    boxes.append(("one run (store_k_block)", "model.hpp:3276-3296 (the run loop)"))
    # decision 1
    dx, dy = 20, 30
    o.append(rect(dx, dy, 300, 48, "#fff", C["ink"], 1.6, 10))
    o.append(text(dx + 150, dy + 18, "n < k_store_block ?", 11, "middle", weight=700))
    o.append(text(dx + 150, dy + 33, "(a run shorter than 16 tokens)", 9, "middle", mono=True))
    o.append(cite(dx + 294, dy + 44, "model.hpp:3297"))
    boxes.append(("n < k_store_block", "model.hpp:3297"))
    # yes branch: row by row
    yx, yy = 20, 110
    o.append(text(dx + 160, yy - 8, "yes: row by row (set_k_row decides)", 9.5, "start",
                  weight=600))
    o.append(arrow(fid, "ink", [(dx + 150, dy + 48), (dx + 150, yy - 2)], C["ink"]))
    o.append(block_state_box(yx, yy, 300, 76, "rm", "row-major rows",
                             ["block bit clear -> store_row_major: 4 whole lines",
                              "per token into the block's own row-major form;",
                              "no bit here; the recording is main's, after the join"],
                             "kv_cache.hpp:2297-2300"))
    boxes.append(("row-major rows (store_row_major)", "kv_cache.hpp:2297-2300; k_vnni.hpp:445"))
    o.append(block_state_box(yx, yy + 90, 300, 64, "vnni", "a row saved again: store_row",
                             ["block bit set already -> the VNNI column of",
                              "the token (4 scatters); the bit stays set"],
                             "kv_cache.hpp:2297-2298"))
    boxes.append(("a row saved again (store_row into a converted block)",
                  "kv_cache.hpp:2297-2298; model.hpp:3298-3300"))
    # no branch: whole block
    nx, ny = 350, 110
    o.append(text(nx + 160, ny - 8, "no: n == 16, the whole block", 9.5, "start", weight=600))
    o.append(arrow(fid, "ink", [(dx + 300, dy + 24), (nx + 150, dy + 24), (nx + 150, ny - 2)],
                   C["ink"]))
    o.append(block_state_box(nx, ny, 300, 90, "vnni", "converted: VNNI layout",
                             ["TRON_ASSERT(present == FULL_BLOCK_0XFFFF);",
                              "per KV head set_k_block(slot, kv_head, c, rows)",
                              "-> store_block; then note_k_block_saved(slot, c):",
                              "the 16 row bits and the block bit (any thread)"],
                             "model.hpp:3316-3333"))
    boxes.append(("converted: VNNI layout (set_k_block, note_k_block_saved)",
                  "model.hpp:3316-3333; kv_cache.hpp:2242"))
    # removed branches
    gx, gy = 680, 110
    o.append(text(gx + 150, gy - 8, "removed (the base, PR 4958)", 9.5, "middle", weight=600,
                  fill=C["gone"]))
    o.append(rect(gx, gy, 300, 60, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(gx + 8, gy + 15, "n == k_scatter_run_len (1 token)", 10, mono=True, weight=600,
                  fill=C["gone"]))
    o.append(lines(gx + 8, gy + 29, ["set_k_row -> store_row: a 4-scatter write into the",
                                     "token's VNNI column, in every block"], 9, 11))
    o.append(text(gx + 8, gy + 55, "removed", 9, fill=C["gone"], weight=700))
    o.append(cite(gx + 294, gy + 56, "base model.hpp:3141, 3260"))
    boxes.append(("k_scatter_run_len (removed)", "base model.hpp:3140-3141, 3260 (removed at head 3151, 3297)"))
    o.append(rect(gx, gy + 70, 300, 60, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(gx + 8, gy + 85, "2 .. 15 tokens: set_k_block(..., present, rows)", 10, mono=True,
                  weight=600, fill=C["gone"]))
    o.append(lines(gx + 8, gy + 99, ["a partial block save with masked line stores;",
                                     "the absent lanes were left unwritten"], 9, 11))
    o.append(text(gx + 8, gy + 125, "removed", 9, fill=C["gone"], weight=700))
    o.append(cite(gx + 294, gy + 126, "base model.hpp:3288"))
    boxes.append(("the partial block save with a present mask (removed)",
                  "base model.hpp:3288 (set_k_block with present); head kv_cache.hpp:2321-2328 takes no mask"))

    # after the join, on main
    jy = 300
    o.append(line(20, jy - 14, 980, jy - 14, C["line"]))
    o.append(text(20, jy, "after the join, on the main thread (save_k_impl): the row-recording "
                  "loop and the forward end", 11, weight=700))
    o.append(rect(20, jy + 10, 300, 48, "#fff", C["ink"], 1.6, 10))
    o.append(text(170, jy + 28, "cached_operation_uses_hw ?", 11, "middle", weight=700))
    o.append(text(170, jy + 43, "(does the FPGA score this operation's K)", 9, "middle", mono=True))
    o.append(cite(314, jy + 54, "model.hpp:3419"))
    boxes.append(("cached_operation_uses_hw", "model.hpp:3419; defined at 1529"))
    # no -> record
    ry = jy + 90
    o.append(text(180, ry - 8, "no: record this pass's rows", 9.5, "start", weight=600))
    o.append(arrow(fid, "ink", [(170, jy + 58), (170, ry - 2)], C["ink"]))
    o.append(rect(20, ry, 300, 70, C["rows_fill"], C["rows"], 1.4, 4))
    o.append(text(28, ry + 15, "note_k_row_saved(slot, j) per item", 10, mono=True, weight=600))
    o.append(lines(28, ry + 29, ["sets bit j; returns true when block j / 16 now has",
                                 "all 16 row bits and its block bit is clear; a row of",
                                 "a converted block returns false"], 9, 11))
    o.append(cite(314, ry + 66, "model.hpp:3426; kv_cache.hpp:2215"))
    boxes.append(("note_k_row_saved(slot, j) per item", "model.hpp:3426; kv_cache.hpp:2207-2231"))
    o.append(text(345, ry + 30, "true ->", 9.5, weight=600))
    o.append(arrow(fid, "pend", [(320, ry + 35), (388, ry + 35)], C["pend"]))
    o.append(block_state_box(390, ry, 260, 70, "pend", "complete, may wait",
                             ["pending_k_blocks_.push_back({&pg,",
                              "pg.k_storage_of(slot), j / k_store_block});",
                              "readers still see row-major rows"],
                             "model.hpp:3427-3428"))
    boxes.append(("complete, may wait (pending_k_blocks_.push_back)", "model.hpp:3427-3428; kv_cache.hpp:716-718"))
    o.append(arrow(fid, "pend", [(650, ry + 35), (718, ry + 35)], C["pend"]))
    o.append(text(684, ry + 27, "forward end", 8.5, "middle", fill=C["pend"], weight=600))
    o.append(block_state_box(720, ry, 260, 70, "vnni", "converted: VNNI layout",
                             ["convert_pending_k_blocks -> k_block_to_vnni_at",
                              "-> block_to_vnni per KV head; block bit set;",
                              "the AMX kernel may read the page at 0b1111"],
                             "model.hpp:3170-3177"))
    boxes.append(("converted at the forward end (convert_pending_k_blocks)",
                  "model.hpp:3168-3177; kv_cache.hpp:2261-2283"))
    # yes -> hardware
    hy = ry + 100
    o.append(text(170, hy - 8, "yes: no row bit, no entry (the loop is skipped)", 9.5, "middle",
                  weight=600))
    o.append(arrow(fid, "ink", [(20, jy + 34), (10, jy + 34), (10, hy + 35), (18, hy + 35)],
                   C["ink"]))
    o.append(block_state_box(20, hy, 300, 70, "hw", "row-major, no bits (hardware attention)",
                             ["the rows of a short run stay row-major for good:",
                              "the staging reads them in place (k_row_if_row_major),",
                              "a tail token is scored by the row-major dotter"],
                             "kv_cache.hpp:763-799", size=9.5))
    boxes.append(("row-major, no bits (hardware attention)",
                  "kv_cache.hpp:763-799 (Note [Row-major blocks under hardware attention]); model.hpp:3414-3419"))
    o.append(note_box(390, hy, 590, 70, "whole-block saves are not affected by the flag",
                      ["note_k_block_saved runs inside store_k_block on any thread, before the join and",
                       "regardless of cached_operation_uses_hw: a page the hardware does not cover yet is",
                       "dense for the AMX kernel only through whole-block saves (prefill)"],
                      "model.hpp:3333; kv_cache.hpp:786-790"))
    boxes.append(("whole-block saves are not affected by the flag", "model.hpp:3333; kv_cache.hpp:786-790"))
    # legend of block states
    ly = hy + 90
    o.append(text(20, ly + 11, "block states:", 10, weight=700))
    cx = 110
    for st, lab in (("vnni", "converted: VNNI layout"), ("rm", "row-major rows"),
                    ("pend", "complete, may wait"), ("hw", "row-major, no bits (hardware attention)")):
        o.append(block_cell(cx, ly, 26, 14, st))
        o.append(text(cx + 32, ly + 11, lab, 10))
        cx += 32 + text_width(lab, 10) + 18
    cap = ("The decision model: what one run of consecutive tokens becomes in the page. A run "
           "of 16 is one VNNI block save with its bits set at once. A shorter run is stored "
           "row by row into the block's row-major form (or into the VNNI column when the "
           "block was converted already). After the join, main records the rows unless the "
           "hardware attention scores the operation; a block completed that way waits for "
           "the forward end. The two red dashed boxes are the base's branches this PR removes: "
           "the one-token scatter and the masked partial block save.")
    legend = [
        ("box", "white box, ink outline: a decision (bold question) or a function"),
        ("vnni", "blue: a block in the VNNI layout (whole-block save, a row saved again, the conversion's result)"),
        ("rm", "orange: row-major rows of an incomplete block"),
        ("pend", "orange-red dashed: a complete block that waits for the forward end"),
        ("rows", "green: the row-recording loop (note_k_row_saved)"),
        ("hw", "yellow: the rows of a hardware-scored operation (no bits, no conversion)"),
        ("gone", "red dashed: the base's branches this PR removes"),
        ("ctx", "grey note: context"),
        ("arrow", "ink arrow: a branch of a decision"),
        ("orange-red arrow: a block queued, then converted", "arrow", C["pend"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "red 'removed' = removed by this PR"),
    ]
    return figure(fid, W, H, "Decision model of the K store of one run", "".join(o), cap,
                  boxes=boxes, legend=legend)
