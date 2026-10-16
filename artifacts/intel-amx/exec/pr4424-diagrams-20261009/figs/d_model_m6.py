"""Change diagrams of unit m6 (model.hpp): after the join, the row-recording
loop of save_k_impl (head lines 3420-3439).

Updates B3: step 6 of main's lane ("record the rows (VNNI slot)") is one box
in B3. Figure d6a expands it into the per-item loop, the check that
page::note_k_row_saved makes between the two bit sets of the page
(k_rows_saved_ and k_vnni_blocks_) and its answers; figure d6b shows the
order change against steps 7 and 8 (the marks loop and the latch count_down):
every K row of the minibatch is stored before the first mark_k_complete,
where the base stored each token's row inside the marks loop.

Every label is an identifier or a comment phrase of model.hpp (head line
numbers), kv_cache.hpp or h/tron/tensor/k_vnni.hpp of the same PR. Facts come
from facts/model.json (verified claims) and the cited lines.
"""
from svg_helpers import (C, arrow, bit_row, card_arrow, cite, figure, fn_cell,
                         line, lines, marker_defs, rect, text, text_width)
from base_model import (CRIT, CRIT_SW, MAIN_FILL, UNITS_EXAMPLE, block_state_box,
                        crit_frame, decision_box, step_box)

BASE = ("Updates B3. The first figure expands step 6 of main's lane (record the "
        "rows) into the per-item loop, the check note_k_row_saved makes between "
        "k_rows_saved_ and k_vnni_blocks_, and its answers (false for a whole-block "
        "run, false for an incomplete block, true for the row that completes a "
        "block, true again for a row saved again). The second figure sets the loop "
        "against steps 7 and 8: every K row is stored before the first "
        "mark_k_complete, where the base stored each token's row inside the marks "
        "loop.")

FID_A = "model-d6a"
FID_B = "model-d6b"
W = 700
RED = C["gone"]


def _fit(s, size, maxw, mono=False, where=""):
    """Abort when a string is wider than the space it must fit (checked at
    render time, before the PNG is looked at)."""
    w = text_width(s, size, mono)
    if w > maxw:
        raise ValueError(f"{where}: '{s}' is {w:.0f} px wide, room {maxw} px")


def note_box(x, y, w, h, title, body, ref, stroke=C["ink"], fill="#fff",
             dash=None, tag=None, size=9, title_size=10, title_mono=True, sw=1.2):
    """A box with a title line (mono by default), small sans body lines, an
    optional tag ('new' / 'removed' / 'unchanged') and a citation. sw=CRIT_SW
    marks a cell on the critical path: its own thin (dashed when waiting)
    outline under a solid thick red crit_frame, as in B3 and B4."""
    crit = sw == CRIT_SW
    o = [rect(x, y, w, h, fill, stroke, 1.2 if crit else sw, 4, dash)]
    if crit:
        o.append(crit_frame(x, y, w, h))
    _fit(title, title_size, w - 16, title_mono, "note_box title")
    o.append(text(x + 8, y + 14, title, title_size, mono=title_mono, weight=700))
    for s in body:
        _fit(s, size, w - 16, False, "note_box body")
    o.append(lines(x + 8, y + 27, body, size, 11))
    if tag:
        col = C["new"] if tag.startswith("new") else (
            RED if tag.startswith("removed") else C["muted"])
        side_by_side = 8 + text_width(tag, 8.5) * 1.1 + 8 + text_width(ref, 8.5, True) + 4 <= w
        o.append(text(x + 8, y + h - 5 if side_by_side else y + h - 17, tag, 8.5, fill=col,
                      weight=700))
    _fit(ref, 8.5, w - 8, True, "note_box cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def _lab(x, y, s, col=C["ink"], anchor="middle", size=9):
    return text(x, y, s, size, anchor, fill=col, weight=700)


# ---- the worked example of the bit rows ------------------------------------
# page 7: user A's two whole blocks (offsets 0..31); page 9: user B's 8 rows
# (offsets 32..39); then one later minibatch (of this pass or a later one)
# saves page 9 offsets 40..47 (the extension B5's note names).
assert UNITS_EXAMPLE[0]["page"] == 7 and UNITS_EXAMPLE[1]["page"] == 7
assert UNITS_EXAMPLE[2]["page"] == 9 and UNITS_EXAMPLE[2]["offsets"] == "32..39"
ROWS_PAGE7 = "1" * 32 + "0" * 32          # bits 0..31 set (note_k_block_saved)
BLOCKS_PAGE7 = "1100"                     # k_vnni_blocks_ bits 0 and 1 set
ROWS_PAGE9 = "0" * 32 + "1" * 8 + "0" * 24    # bits 32..39 set by this loop
BLOCKS_PAGE9 = "0000"
ROWS_PAGE9_LATER = "0" * 32 + "1" * 16 + "0" * 16   # bits 32..47 set
BLOCKS_PAGE9_LATER = "0000"               # the block bit follows the conversion

BIT_X = 120          # where the 64-bit row starts
BIT_CELL, BIT_GAP, BIT_GROUP_GAP = 6.5, 1, 6
BLK_X = 636          # where the 4 block bits start


def bits_line(y, rows, blocks, left):
    """One example row: the left label, the 64 row bits and the 4 block bits."""
    o = [text(15, y + 7, left, 9, weight=600)]
    svg, _ = bit_row(BIT_X, y, rows, BIT_CELL, BIT_GAP, C["rows_fill"], C["rows"],
                     group=16, group_gap=BIT_GROUP_GAP)
    o.append(svg)
    svg, _ = bit_row(BLK_X, y, blocks, 8, 1, C["blk_fill"], C["blk"], group=0)
    o.append(svg)
    return "".join(o)


# ---- figure a: the loop, the check, the answers ----------------------------
def fig_a():
    fid = FID_A
    H = 712
    o = [marker_defs(fid, {"ink": C["ink"], "hw": C["hw"], "vnni": C["vnni"],
                           "rm": C["rm"], "pend": C["pend"]})]
    boxes = []

    # ---- the step of B3 this figure expands --------------------------------
    o.append(step_box(15, 12, 670, 46, "record the rows (VNNI slot): B3 step 6, expanded",
                      ["[main, worker_ix 0]: after the join (shared), or after main's own "
                       "store_k_block(items[0, n_items)) (unshared)"],
                      "model.hpp:3404-3419; 3420-3439", num=6, sw=CRIT_SW))
    boxes.append(("note_k_row_saved loop (step 6: record the rows, VNNI slot)", "model.hpp:3420-3439; the join "
                  "3404-3416, the unshared store 3417-3419"))

    # ---- the two gates --------------------------------------------------------
    GY = 72
    o.append(decision_box(15, GY, 200, 68, "VNNI slot?",
                          ["if constexpr (k_vnni::", "layout_on<geometry.kv.head_size>)",
                           "no: compiled out, no bits"], "model.hpp:3420"))
    boxes.append(("VNNI slot? (k_vnni::layout_on)", "model.hpp:3420; tensor/k_vnni.hpp:119-130"))
    o.append(decision_box(250, GY, 200, 68, "hardware-scored?",
                          ["if (!cached_operation_uses_hw(", "binding.operation))",
                           "decided once per model"], "model.hpp:3426; 1531-1533"))
    boxes.append(("hardware-scored? (cached_operation_uses_hw)",
                  "model.hpp:3426; 1530-1533; kv_cache.hpp:731-732"))
    o.append(block_state_box(485, GY, 200, 68, "hw", "stays row-major",
                             ["no row bit, nothing queued, no", "conversion; a whole-block save",
                              "still set its bits in store_k_block"],
                             "model.hpp:3423-3425; 3340"))
    boxes.append(("stays row-major (hardware attention)",
                  "model.hpp:3423-3425; kv_cache.hpp:729-735 (Note [Row-major blocks under "
                  "hardware attention]); whole-block bits: model.hpp:3340"))
    o.append(arrow(fid, "ink", [(215, GY + 34), (248, GY + 34)], C["ink"], 1.3))
    o.append(_lab(231, GY + 28, "yes"))
    o.append(arrow(fid, "hw", [(450, GY + 34), (483, GY + 34)], C["hw"], 1.4))
    o.append(_lab(466, GY + 28, "yes", C["hw"]))
    o.append(arrow(fid, "ink", [(350, GY + 68), (350, 154)], C["ink"], 1.3))
    o.append(_lab(358, GY + 80, "no", anchor="start"))

    # ---- the per-item loop ------------------------------------------------------
    LY = 156
    o.append(rect(15, LY, 670, 112, "#fff", C["ink"], 1.2, 5))
    o.append(text(23, LY + 15, "for (token_job_id ix : q_batch->items)", 10.5, mono=True,
                  weight=700))
    o.append(text(23 + text_width("for (token_job_id ix : q_batch->items)", 10.5, True) + 10,
                  LY + 15, "[main], in items order, one minibatch", 9.5, fill=C["muted"]))
    o.append(cite(681, LY + 15, "model.hpp:3427-3437"))
    boxes.append(("for (token_job_id ix : q_batch->items)", "model.hpp:3427; items at "
                  "common.hpp:1084-1085"))
    cy, ch = LY + 26, 60
    cells = [
        (25, 140, "token_jobs_do_kv[ix]", ["0: continue (no KV work)"], "model.hpp:3429",
         "token_jobs_do_kv[ix] (skip)", "model.hpp:3429; 1160"),
        (175, 180, "page_of, offset_in_page", ["pg = page_of(tok_ix)",
                                               "j = pg.offset_in_page(tok_ix)"],
         "model.hpp:3430-3432", "page_of(tok_ix), offset_in_page (tok_ix = token_jobs[ix])",
         "model.hpp:3430-3432; 1773; kv_cache.hpp:2031"),
        (365, 150, "note_k_row_saved", ["sets bit j; true = block c",
                                        "complete, may wait"], "model.hpp:3433",
         "pg.note_k_row_saved<geometry.kv>(slot, j)", "model.hpp:3433; kv_cache.hpp:2167"),
        (525, 150, "push_back", ["true: pending_k_blocks_", "gets {&pg, storage, c}"],
         "model.hpp:3434-3435", "pending_k_blocks_.push_back",
         "model.hpp:3434-3435; the list 3169"),
    ]
    for x, w, t, s, ref, label, src in cells:
        o.append(note_box(x, cy, w, ch, t, s, ref, title_size=9.5))
        boxes.append((label, src))
    for x0, x1 in ((165, 175), (355, 365), (515, 525)):
        o.append(arrow(fid, "ink", [(x0, cy + 30), (x1 - 1, cy + 30)], C["ink"], 1.2))
    o.append(text(25, LY + 104, "1 item -> 1 token_id (token_jobs) -> 1 page (page_of) + 1 "
                  "offset j (offset_in_page); block c = j / k_store_block; 0 or 1 push per item",
                  8.5, fill=C["ink"], weight=600))
    _fit("1 item -> 1 token_id (token_jobs) -> 1 page (page_of) + 1 offset j "
         "(offset_in_page); block c = j / k_store_block; 0 or 1 push per item", 8.5, 650,
         False, "loop cardinality")

    # ---- the check: note_k_row_saved -------------------------------------------
    FY = 284
    o.append(fn_cell(15, FY, 670, 58, "page::note_k_row_saved<geometry.kv>(slot, j)",
                     ["sets bit j of k_rows_saved_[ix] (fetch_or, acq_rel; skipped when the "
                      "bit is set already); returns true when block",
                      "c = j / 16 now has all 16 row bits (k_block_bits(c)) and the "
                      "k_vnni_blocks_[ix] bit of c is clear (acquire load)"],
                     "kv_cache.hpp:2167-2183; comment 2157-2163", tag="new"))
    boxes.append(("page::note_k_row_saved", "kv_cache.hpp:2157-2167 (comment and signature); kv_cache.hpp:2168-2183 "
                  "(body); kv_cache.hpp:2508-2510 (k_block_bits)"))
    for s in ("sets bit j of k_rows_saved_[ix] (fetch_or, acq_rel; skipped when the bit is "
              "set already); returns true when block",
              "c = j / 16 now has all 16 row bits (k_block_bits(c)) and the k_vnni_blocks_[ix]"
              " bit of c is clear (acquire load)"):
        _fit(s, 9.5, 650, False, "note_k_row_saved desc")

    # ---- the answers -----------------------------------------------------------
    AY = 368
    o.append(block_state_box(15, AY, 205, 64, "vnni", "false: a row of a converted block",
                             ["whole-block run: store_k_block set its",
                              "16 row bits and the block bit already"],
                             "model.hpp:3340; kv_cache.hpp:2163", size=9.5))
    boxes.append(("k_vnni_blocks_ bit set -> false: a row of a converted block (a whole-block run)",
                  "kv_cache.hpp:2180-2182 (the k_vnni_blocks_ test); kv_cache.hpp:2162-2163 (comment); kv_cache.hpp:2195-2200 (note_k_block_saved, called at "
                  "model.hpp:3340)"))
    o.append(block_state_box(240, AY, 205, 64, "rm", "false: an incomplete block",
                             ["fewer than 16 rows: the bit is set,",
                              "nothing queued, waits for a later minibatch"],
                             "model.hpp:3301; kv_cache.hpp:2157-2160", size=9.5))
    boxes.append(("k_block_bits test fails -> false: an incomplete block (fewer than 16 rows)",
                  "kv_cache.hpp:2180 (the k_block_bits test); kv_cache.hpp:2157-2160 "
                  "(comment); the phrase at model.hpp:3301"))
    o.append(block_state_box(465, AY, 220, 64, "pend", "true: complete, may wait",
                             ["pending_k_blocks_.push_back({&pg,",
                              "pg.k_storage_of(slot), j / k_store_block})"],
                             "kv_cache.hpp:2159-2161; model.hpp:3434", size=9.5))
    boxes.append(("pending_k_blocks_.push_back -> true: complete, may wait",
                  "kv_cache.hpp:2159-2161 and 2610 (the comments that define the state); "
                  "model.hpp:3433-3436 (the push); pending_k_block 3164-3168"))
    for x, name, col, lab in ((117, "vnni", C["vnni"], "false"), (342, "rm", C["rm"], "false"),
                              (575, "pend", C["pend"], "true")):
        o.append(arrow(fid, name, [(x, FY + 58), (x, AY - 2)], col, 1.4))
        o.append(_lab(x + 7, FY + 58 + 17, lab, col, anchor="start"))

    # ---- the second true, the storage reference, the list ----------------------
    EY = 452
    o.append(note_box(15, EY, 215, 76, "a row saved again",
                      ["into a block that waits for its",
                       "conversion: true again -> queued",
                       "twice; k_block_to_vnni_at converts",
                       "once (CONVERTED_FALSE the 2nd time)"],
                      "kv_cache.hpp:2161-2163; 2219-2223", stroke=C["pend"]))
    boxes.append(("a row saved again (true again, queued twice, converted once)",
                  "kv_cache.hpp:2161-2163; k_block_to_vnni_at 2219-2223"))
    o.append(fn_cell(250, EY, 215, 76, "pg.k_storage_of(slot)",
                     ["resolves the logical slot under the",
                      "current view: offset and state index"],
                     "kv_cache.hpp:2150-2155; 2141-2143", tag="new"))
    boxes.append(("pg.k_storage_of(slot) (k_storage_ref)", "kv_cache.hpp:2137-2155; why: "
                  "2141-2143 and model.hpp:3162-3163"))
    o.append(note_box(485, EY, 200, 76, "pending_k_blocks_",
                      ["std::vector<pending_k_block>, main",
                       "only; convert_pending_k_blocks",
                       "[main, forward end]: 1 k_block_to_",
                       "vnni_at call per entry"],
                      "model.hpp:3169; 3173-3180", stroke=C["pend"], fill=C["pend_fill"],
                      dash="5 3"))
    boxes.append(("pending_k_blocks_ (the deferred conversion list)",
                  "model.hpp:3169; drained at 3173-3180 from run_forward 1847"))
    o.append(card_arrow(fid, "pend", [(575, AY + 64), (575, EY - 2)], C["pend"],
                        "0 or 1 per item; at most n_items per call", label_dx=-8,
                        label_dy=4, size=9, anchor="end"))
    _fit("0 or 1 per item; at most n_items per call", 9, 330, False, "push arrow label")

    # ---- the worked example as bit rows -----------------------------------------
    XY = 552
    o.append(line(15, XY - 14, 685, XY - 14, C["line"]))
    o.append(text(15, XY, "Worked example (B1's window, then one later minibatch): what the "
                  "loop returns per item", 10, weight=700))
    hy = XY + 16
    o.append(text(15, hy, "k_rows_saved_[ix]", 8.5, mono=True, fill=C["muted"]))
    for c in range(4):
        gx = BIT_X + c * (16 * (BIT_CELL + BIT_GAP) + BIT_GROUP_GAP)
        o.append(text(gx + 8 * (BIT_CELL + BIT_GAP) - 0.5, hy, f"block {c}", 8.5, "middle",
                      fill=C["muted"]))
    o.append(text(685, hy, "k_vnni_blocks_[ix]", 8.5, "end", True, fill=C["muted"]))
    boxes.append(("k_rows_saved_[ix], k_vnni_blocks_[ix] (ix = k_state_ix(slot))",
                  "kv_cache.hpp:2608-2622; 2173"))
    r1 = XY + 32
    o.append(text(15, r1, "page 7 (user A, offsets 0..31, two whole blocks): 32 x false; "
                  "the bits came from note_k_block_saved in store_k_block", 9))
    o.append(bits_line(r1 + 5, ROWS_PAGE7, BLOCKS_PAGE7, "page 7"))
    r2 = r1 + 32
    o.append(text(15, r2, "page 9 (user B, offsets 32..39, a run of 8): this loop sets bits "
                  "32..39 (fetch_or); 8 x false (8 of 16 rows)", 9))
    o.append(bits_line(r2 + 5, ROWS_PAGE9, BLOCKS_PAGE9, "page 9"))
    r3 = r2 + 32
    o.append(text(15, r3, "page 9, a later minibatch saves offsets 40..47 (as B5's note "
                  "says): offsets 40..46 -> false; offset 47 completes block 2 -> true:", 9))
    o.append(text(15, r3 + 11, "1 push {&page 9, k_storage_of(slot), 2}; the forward end "
                  "converts it and only then sets k_vnni_blocks_ bit 2", 9))
    o.append(bits_line(r3 + 16, ROWS_PAGE9_LATER, BLOCKS_PAGE9_LATER, "page 9"))
    for s in ("page 7 (user A, offsets 0..31, two whole blocks): 32 x false; the bits came "
              "from note_k_block_saved in store_k_block",
              "page 9, a later minibatch saves offsets 40..47 (as B5's note says): offsets "
              "40..46 -> false; offset 47 completes block 2 -> true:"):
        _fit(s, 9, 670, False, "example text")
    o.append(cite(685, r3 + 34, "STYLE.md worked example; kv_cache.hpp:2177-2182; 2234"))
    boxes.append(("k_rows_saved_, k_vnni_blocks_ (worked example rows: page 7, page 9, the later minibatch)",
                  "STYLE.md worked example; kv_cache.hpp:2176-2182 (saved and the return rule); kv_cache.hpp:2234 (the block "
                  "bit after the conversion)"))
    o.append(text(15, H - 8, "green = k_rows_saved_ bit set, purple = k_vnni_blocks_ bit set, "
                  "grey dashed = clear; box colours as B5; [...] = the thread.", 9,
                  fill=C["muted"]))

    cap = ("Updates B3: step 6 of main's lane, expanded. The loop runs on main after the "
           "join (or after main's own store of an unshared save), only for a VNNI slot and "
           "only when the hardware attention does not score the operation. For every item "
           "with KV work it calls note_k_row_saved. That call sets the row's bit and "
           "compares the block's 16 row bits with its converted-block bit. Look at the "
           "three answers and the worked example: the 32 rows of the whole blocks and the "
           "8 rows of the incomplete block return false (nothing queued), and only the "
           "later row that completes block 2 of page 9 pushes one pending_k_block, with "
           "the storage reference resolved at the save. The slot-5 example of the "
           "kv_cache.hpp and k_vnni.hpp pages (page 7, bits 0..40 set, block 1 complete "
           "and waiting) is a different history of page 7: its rows arrived through "
           "short runs, not through this window's two whole-block saves.")
    legend = [
        ("box", "white box, ink outline: step 6, the decisions VNNI slot? and hardware-scored?, "
                "the loop frame and its four cells, note_k_row_saved and pg.k_storage_of; "
                "the name in bold monospace, its description in sans-serif"),
        ("solid ink badge: the B3 step number (step 6)", C["ink"], C["ink"], False, False),
        ("crit", "thick solid red frame: step 6 runs on main's serial part (the critical "
                 "path of B4)"),
        ("arrow", "ink arrow: the yes and no answers of the decisions, and the step from one "
                  "loop cell to the next"),
        ("yellow box and arrow: hardware-scored? yes -> stays row-major (no row bit, nothing "
         "queued)", "multi", ["hw", ("arrow", C["hw"])]),
        ("blue box and arrow: note_k_row_saved -> false, a row of a converted block (a "
         "whole-block run set its 16 row bits and the block bit already)", "multi",
         ["vnni", ("arrow", C["vnni"])]),
        ("orange box and arrow: note_k_row_saved -> false, an incomplete block (fewer than "
         "16 rows, nothing queued)", "multi", ["rm", ("arrow", C["rm"])]),
        ("orange-red dashed box, white box with orange-red outline, and orange-red arrow: "
         "note_k_row_saved -> true, complete, may wait; the push into pending_k_blocks_ "
         "(0 or 1 per item); a row saved again into a waiting block (true again, queued "
         "twice, converted once)", "multi",
         ["pend", ("#fff", C["pend"], False, False), ("arrow", C["pend"])]),
        ("bit squares of the worked example: green = a k_rows_saved_[ix] bit that is set "
         "(one per page offset), pink = a k_vnni_blocks_[ix] bit that is set (one per "
         "16-token block), white with grey outline = clear", "multi",
         ["rows", "blk", "bit_clear"]),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions"
        "; grey sans-serif = a note or a secondary label (row labels, index "
        "numbers, the one-line notes under a group)"),
        "font_cite",
        ("font_tag", "bold 'new' = added by this PR (note_k_row_saved, pg.k_storage_of)"),
    ]
    return figure(fid, W, H, "The row-recording loop after the join", "".join(o), cap,
                  boxes=boxes, legend=legend)


# ---- figure b: the order, before and at the head -----------------------------
def fig_b():
    fid = FID_B
    H = 362
    o = [marker_defs(fid, {"ink": C["ink"], "gone": RED, "new": C["new"]})]
    boxes = []
    o.append(text(15, 16, "Where the K store sits relative to the marks: before (base) and at "
                  "the head (B3 steps 3-8 in one row)", 11, weight=600))

    # ---- before -----------------------------------------------------------------
    BY = 28
    o.append(rect(15, BY, 670, 124, "#fff", RED, 1.3, 5, "5 3"))
    o.append(text(23, BY + 15, "before (base main be0d5565b3): [main] alone, one token at a "
                  "time, in q_batch->items order", 10, fill=RED, weight=700))
    o.append(cite(681, BY + 15, "base model.hpp:3095-3108"))
    boxes.append(("mark_k_complete loop [before: the marks loop with the K store inside it]",
                  "model.hpp:3440-3453 (the marks loop at head); base model.hpp:3095-3108 (the removed store, diff hunk @@ -3095,14 +3444,6 @@)"))
    by = BY + 26
    o.append(note_box(23, by, 230, 68, "pg.k(slot, kv_head, j).set",
                      ["x n_kv_heads: the K store of token ix,",
                       "inside the marks loop, before its mark"],
                      "base model.hpp:3098-3105", stroke=RED, dash="5 3", tag="removed"))
    boxes.append(("pg.k(slot, kv_head, j).set x n_kv_heads (removed)",
                  "base model.hpp:3098-3105 (the 8 lines removed after head line 3446); "
                  "now store_k_block, model.hpp:3252-3261 and 3300-3340"))
    o.append(note_box(293, by, 200, 68, "mark_k_complete(slot, j)",
                      ["counts the (offset, slot) save; true",
                       "when K and V are both in (count 2);",
                       "then credit_gof_save (hardware slot)"],
                      "kv_cache.hpp:2449", fill=MAIN_FILL, tag="unchanged"))
    boxes.append(("mark_k_complete, credit_gof_save", "kv_cache.hpp:2449-2453 ('Returns true "
                  "if this was the completing save (count reached 2)'); model.hpp:3447-3451; "
                  "3550 (credit_gof_save)"))
    o.append(note_box(533, by, 152, 68, "count_down",
                      ["upstream_kvs_ready[slot]", "per downstream minibatch"],
                      "model.hpp:3455-3456", fill=MAIN_FILL, tag="unchanged"))
    boxes.append(("upstream_kvs_ready[slot].count_down()", "model.hpp:3454-3456"))
    o.append(arrow(fid, "gone", [(253, by + 34), (291, by + 34)], RED, 1.3))
    o.append(arrow(fid, "ink", [(493, by + 34), (531, by + 34)], C["ink"], 1.3))
    # the loop back: token ix + 1
    o.append(line(393, by + 68, 393, by + 78, RED, 1.2))
    o.append(line(393, by + 78, 138, by + 78, RED, 1.2))
    o.append(arrow(fid, "gone", [(138, by + 78), (138, by + 70)], RED, 1.2))
    o.append(text(265, by + 90, "next token: store, mark, credit, store, mark, ... (n tokens)",
                  8.5, "middle", fill=RED, weight=600))
    _fit("next token: store, mark, credit, store, mark, ... (n tokens)", 8.5, 480, False,
         "loop-back label")

    # ---- at the head ------------------------------------------------------------
    HY = 166
    o.append(rect(15, HY, 670, 162, "#fff", C["new"], 1.3, 5))
    o.append(text(23, HY + 15, "at the head (PR 4424): every K row of the minibatch is stored "
                  "before the first mark_k_complete", 10, fill=C["new"], weight=700))
    o.append(cite(681, HY + 15, "model.hpp:3137-3143"))
    boxes.append(("at the head: stores, join, record, marks, count_down",
                  "model.hpp:3137-3143 (Note [Shared block save]); 3391-3456"))
    # the threads, as bracketed names over the cells they run
    ty = HY + 30
    o.append(line(23, ty, 163, ty, C["ink"], 1))
    o.append(text(93, ty - 3, "[any thread of the window]", 8.5, "middle", weight=700))
    o.append(line(173, ty, 685, ty, C["ink"], 1))
    o.append(text(429, ty - 3, "[main, worker_ix 0]", 8.5, "middle", weight=700))
    boxes.append(("worker_ix 0 [main] / [any thread of the window]",
                  "model.hpp:3346-3356 (comment and signature); model.hpp:3133-3135; model.hpp:3142-3143"))
    hy = HY + 40
    o.append(note_box(23, hy, 140, 82, "store_k_block",
                      ["per unit u: set_k_block", "(16 rows) or set_k_row",
                       "(a shorter run)"],
                      "model.hpp:3391-3397; 3418", tag="new"))
    boxes.append(("store_k_block per unit", "model.hpp:3391-3397 (shared), 3417-3419 "
                  "(unshared); definition 3232-3344"))
    o.append(note_box(173, hy, 110, 82, "join",
                      ["finished >=", "n_helpers", "(acquire)"],
                      "model.hpp:3402-3416", dash="5 3", tag="new", sw=CRIT_SW))
    boxes.append(("join (finished.load(acquire) >= n_helpers)", "model.hpp:3402-3416"))
    o.append(note_box(293, hy, 130, 82, "record the rows",
                      ["note_k_row_saved per", "KV item; true -> push", "(M6 figure 1)"],
                      "model.hpp:3420-3439", tag="new", sw=CRIT_SW))
    boxes.append(("record the rows (this unit)", "model.hpp:3420-3439"))
    o.append(note_box(433, hy, 120, 82, "mark_k_complete",
                      ["+ credit_gof_save:", "the per-token marks", "and GOF credits"],
                      "model.hpp:3440-3453", fill=MAIN_FILL, tag="unchanged"))
    boxes.append(("mark_k_complete, credit_gof_save (the per-token completion marks and "
                  "GOF credits)", "model.hpp:3440-3453; model.hpp:3142-3143"))
    o.append(note_box(563, hy, 122, 82, "count_down",
                      ["upstream_kvs_ready", "[slot].count_down()", "per downstream"],
                      "model.hpp:3455-3456", fill=MAIN_FILL, tag="unchanged"))
    for x0, x1 in ((163, 173), (283, 293), (423, 433), (553, 563)):
        o.append(arrow(fid, "ink", [(x0, hy + 41), (x1 - 1, hy + 41)], C["ink"], 1.2))
    o.append(text(23, HY + 138, "every unit is stored once main leaves the join; every row "
                  "store happens-before the latch count_down (main's acquire on finished)",
                  8.5, fill=C["ink"], weight=600))
    o.append(text(23, HY + 152, "the marks and GOF credits stay on main, after the join, in "
                  "q_batch->items order, one token at a time [model.hpp:3136-3143]", 8.5,
                  fill=C["muted"]))
    for s in ("every unit is stored once main leaves the join; every row store happens-before "
              "the latch count_down (main's acquire on finished)",
              "the marks and GOF credits stay on main, after the join, in q_batch->items "
              "order, one token at a time [model.hpp:3136-3143]"):
        _fit(s, 8.5, 660, False, "head note")
    o.append(text(15, H - 18, "red dashed = removed base code; dashed = a wait; thick red "
                  "frame = main's serial part (the critical path of B4);", 9, fill=C["muted"]))
    o.append(text(15, H - 6, "bold new = added; grey = unchanged context; [...] = the thread that "
                  "runs the cell.", 9, fill=C["muted"]))

    cap = ("Updates B3: the same row-recording loop placed against steps 7 and 8 of main's "
           "lane, with the base's order above it. Before the PR, main stored each token's "
           "K row inside the marks loop (store, mark, credit, next token). At the head every "
           "K row of the minibatch is stored first, by any thread of the window. Then main "
           "joins, records the rows, marks and credits the tokens one at a time, and counts "
           "the downstream latches down. The red dashed cell is the removed per-token store "
           "(8 base lines after head line 3446).")
    legend = [
        ("gone", "red dashed: before (base main be0d5565b3), the frame of the base order and "
                 "the removed per-token store pg.k(slot, kv_head, j).set"),
        ("red arrow and red label: the base order, the removed store -> mark_k_complete, "
         "and the loop back to the next token ('next token: store, mark, credit, ...')",
         "arrow", RED),
        ("box", "white box, ink outline: the frame of the head order and its new cells "
                "store_k_block and record the rows; the name in bold monospace, its "
                "description in sans-serif"),
        ("idle", "dashed ink outline: the join, main waits for finished >= n_helpers"),
        ("crit", "thick solid red frame: the join and record the rows, main's serial part "
                 "(the critical path of B4)"),
        ("ctx_ink", "grey fill, ink outline: the unchanged context cells mark_k_complete and "
                    "count_down, before and at the head"),
        ("arrow", "ink arrow: the step from one cell to the next (mark -> count_down before; "
                  "store -> join -> record -> mark -> count_down at the head)"),
        ("thin ink line over the cells: the span of the thread named above it ([any thread "
         "of the window], [main, worker_ix 0])", "line", C["ink"]),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions"
        "; grey sans-serif = a note or a secondary label (row labels, index "
        "numbers, the one-line notes under a group)"),
        "font_cite",
        ("font_tag", "bold 'new' = added by this PR; red 'removed' = the base store the PR "
                     "removes; grey 'unchanged' = context the PR keeps"),
    ]
    return figure(fid, W, H, "The order of the store, the record loop and the marks",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
