"""Change diagram of unit m1 (model.hpp page of PR 4424):
the deferred conversion list and the forward-end conversion.

Head lines 1842-1848 (the call in run_forward) and 3153-3180 (Note [K VNNI
storage] of model.hpp, struct pending_k_block, pending_k_blocks_,
convert_pending_k_blocks). Every label is an identifier or a comment phrase
of the code; every box cites the line or Note that defines it (verified in
facts/model.json: model-data-2, -3, -23, -43, -44, model-function-1, -2,
-19, model-seq-3, -4, -5, -21, -22, -23, model-rule-1, -2).
"""
from svg_helpers import (C, arrow, block_cell, cite, figure, fn_cell, lines,
                         marker_defs, rect, text, text_width)
from base_model import block_state_box, crit_frame, field_row

BASE = ("Updates B1 and B4. The pending_k_block record and the pending_k_blocks_ "
        "list of B1 get their writer (save_k_impl on main, after every store, one "
        "entry per true note_k_row_saved) and their reader (convert_pending_k_blocks "
        "at the forward end, one k_block_to_vnni_at call per entry). The strip at "
        "the bottom is a wall-clock excerpt of B4's forward-end lane: why the "
        "conversion waits until after wait_for_coop_gof (a block split across two "
        "minibatches of one pass).")

FID = "model-d1"
W = 700


def _fit(s, size, w, mono=False, where=""):
    """Warn when a string is wider than the space it must fit (layout check)."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WARNING {FID} {where}: text {tw:.0f} px > {w} px: {s!r}")
    return s


def _tag(x, y, s, col, anchor="end", size=9):
    return text(x, y, s, size, anchor, fill=col, weight=700)


def member_row(x, y, w, h, name, desc, ref):
    """One member of a struct: the declaration (mono, bold), a plain-English
    line, and the citation in the lower-right corner."""
    o = [rect(x, y, w, h, "#fff", C["pend"], 1, 3)]
    o.append(text(x + 6, y + 13, _fit(name, 10, w - 12, True, name), 10, mono=True,
                  weight=600))
    o.append(text(x + 6, y + 25, _fit(desc, 9, w - 12, False, name), 9, fill=C["muted"]))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def stmt_row(x, y, w, h, code, desc, ref):
    """One statement of a function body: 1-2 code lines (mono), a plain-English
    line, and the citation in the lower-right corner."""
    o = [rect(x, y, w, h, "#fff", C["ink"], 1, 3)]
    cs = code if isinstance(code, (list, tuple)) else [code]
    ty = y + 13
    for c in cs:
        o.append(text(x + 6, ty, _fit(c, 9, w - 12, True, "stmt"), 9, mono=True,
                      weight=600))
        ty += 12
    o.append(text(x + 6, ty, _fit(desc, 9, w - 12, False, "stmt desc"), 9,
                  fill=C["muted"]))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fig():
    fid = FID
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "vnni": C["vnni"],
                           "new": C["new"]})]
    boxes = []
    ink, pend, muted = C["ink"], C["pend"], C["muted"]

    # ---- header ---------------------------------------------------------------
    o.append(text(20, 18, "pending_k_blocks_: its record, its writer and its reader",
                  12.5, weight=700))
    o.append(cite(W - 20, 18, "model.hpp:3155-3180; 1842-1848"))

    # ---- A: the data model (a piece of B1) --------------------------------------
    AX, AW = 20, 290
    o.append(rect(AX, 30, AW, 136, C["soft"], ink, 1.2, 6))
    o.append(text(AX + 8, 46, "state (model.hpp)", 11, mono=True, weight=700))
    o.append(cite(AX + AW - 4, 46, "model.hpp:1115"))
    boxes.append(("state (model.hpp)", "model.hpp:1115 (struct state)"))
    o.append(field_row(AX + 12, 56, AW - 24, 56, "pending_k_blocks_",
                       ["std::vector<pending_k_block>: the deferred",
                        "conversion list; filled on the main thread,",
                        "drained once per forward (empty after that)"],
                       "model.hpp:3169", tag="new", stroke=pend, dash="5 3",
                       fill=C["pend_fill"]))
    boxes.append(("pending_k_blocks_", "model.hpp:3169; Note [K VNNI storage] "
                  "(model.hpp:3155-3163); model-data-3"))
    o.append(field_row(AX + 12, 118, AW - 24, 42, "k_store_block",
                       ["= k_vnni::BLOCK_TOKENS_16 (16 tokens): the block",
                        "size of the cut, the store and the recording loop"],
                       "model.hpp:3153", tag="new"))
    boxes.append(("k_store_block", "model.hpp:3153; tensor/k_vnni.hpp:68, 106; used at "
                  "3198 (k_store_shared), 3219 (k_store_cut_units), 3269-3326 "
                  "(store_k_block), 3435 (the recording loop); model-unit-3"))

    PX, PW = 390, 290
    o.append(rect(PX, 30, PW, 158, C["pend_fill"], pend, 1.4, 6, "5 3"))
    o.append(text(PX + 8, 46, "pending_k_block", 11, mono=True, weight=700))
    o.append(_tag(PX + 8 + text_width("pending_k_block", 11, True) * 1.08 + 8, 46, "new",
                  C["new"], "start"))
    o.append(cite(PX + PW - 4, 46, "model.hpp:3164-3168"))
    boxes.append(("pending_k_block", "model.hpp:3164-3168; comment 3155-3163; "
                  "model-data-2"))
    o.append(member_row(PX + 8, 54, PW - 16, 40, "page* pg",
                        "the page of the row: page_of(tok_ix)", "model.hpp:3165; 3431"))
    boxes.append(("page* pg", "model.hpp:3165 (member), 3431-3434 (set from page_of)"))
    o.append(member_row(PX + 8, 98, PW - 16, 40, "page::k_storage_ref storage",
                        "k_storage_of(slot) at the save: {offset, state_ix}",
                        "model.hpp:3166; kv_cache.hpp:2145-2155"))
    boxes.append(("page::k_storage_ref storage", "model.hpp:3166 (member), 3434 "
                  "(k_storage_of at the save); kv_cache.hpp:2145-2155 (the struct and "
                  "k_storage_of); model-data-23"))
    o.append(member_row(PX + 8, 142, PW - 16, 40, "uint32_t block",
                        "= j / k_store_block: block c of the page (0 .. 3)",
                        "model.hpp:3167; 3435"))
    boxes.append(("uint32_t block", "model.hpp:3167 (member), 3435 (j / k_store_block)"))

    # list -> record: how many
    o.append(arrow(fid, "pend", [(AX + AW, 86), (PX - 2, 86)], pend, 1.3))
    o.append(lines(350, 100, ["0..1 per", "KV item;", "<= n_items", "per call"],
                   8.5, 11, "middle", fill=pend, weight=700))
    boxes.append(("0 or 1 entry per KV item; <= n_items per save_k call",
                  "model.hpp:3426-3437 (one push per true note_k_row_saved); "
                  "model-data-43"))

    # worked example entry: the window of B1 queues nothing (blocks 0 and 1
    # of page 7 are whole-block saves, block 2 of page 9 has 8 of 16 rows);
    # the one entry comes from a later minibatch that completes block 2 of
    # page 9 (the first M6 figure)
    o.append(rect(20, 196, 660, 50, "#fff", C["line"], 1, 4))
    o.append(block_cell(28, 208, 64, 26, "pend", "block 2", 9.5))
    o.append(text(100, 214, _fit("worked example: B1's window queues nothing; a later "
                                  "minibatch that saves page 9 offset 47 completes block 2",
                                  9.5, 572, False, "we1"), 9.5))
    o.append(text(100, 229, _fit("-> one entry { pg = &page 9, storage = "
                                  "k_storage_of(slot), block = 2 }",
                                  9.5, 572, True, "we2"), 9.5, mono=True, weight=600))
    o.append(cite(676, 242, "STYLE.md worked example; model.hpp:3434-3435; the first M6 figure"))
    boxes.append(("pending_k_block { &page 9, k_storage_of(slot), 2 } (the worked example "
                  "entry: a later minibatch that completes block 2 of page 9)",
                  "model.hpp:3434-3435 (the push); STYLE.md worked example (unit 2: page 9 "
                  "offsets 32..39, 8 of 16 rows; the window itself queues nothing); the "
                  "later minibatch in the first M6 figure"))

    # ---- B: the writer (left) and the reader (right) ----------------------------
    LX, LW = 20, 290
    RX, RW = 390, 290
    o.append(text(LX, 272, "[main thread] save_k_impl, after the join: the writer", 10.5,
                  weight=700))
    o.append(text(RX, 272, "[main thread] the forward end: the reader", 10.5,
                  weight=700))
    boxes.append(("[main thread] (writer and reader)", "model.hpp:3158-3159 (save_k "
                  "queues them, main thread); 3171-3172 (convert_pending_k_blocks: main "
                  "thread); model-rule-1"))

    # writer, step 1: note_k_row_saved
    y1 = 288
    o.append(rect(LX, y1, LW, 70, "#fff", ink, 1.2, 4))
    o.append(text(LX + 8, y1 + 15, "note_k_row_saved(slot, j) -> true", 10.5, mono=True,
                  weight=600))
    o.append(lines(LX + 8, y1 + 29, [
        _fit("per KV item of q_batch->items, in order, unless", 9, LW - 16),
        _fit("cached_operation_uses_hw(binding.operation); true =", 9, LW - 16),
        _fit("the block's 16 rows are saved now, not converted yet", 9, LW - 16)],
        9, 11.5))
    o.append(cite(LX + LW - 4, y1 + 66, "model.hpp:3426-3433; kv_cache.hpp:2157-2163"))
    boxes.append(("note_k_row_saved(slot, j) -> true", "model.hpp:3426-3433 (the loop); "
                  "kv_cache.hpp:2157-2167 (returns true when the block's 16 rows are "
                  "saved and it is not converted yet); model-seq-3"))
    o.append(arrow(fid, "pend", [(LX + 160, y1 + 70), (LX + 160, y1 + 84)], pend, 1.4))
    o.append(_tag(LX + 168, y1 + 81, "true", pend, "start", 9))

    # writer, step 2: push_back
    y2 = y1 + 86
    o.append(rect(LX, y2, LW, 98, "#fff", pend, 1.4, 4))
    o.append(text(LX + 8, y2 + 15, "pending_k_blocks_.push_back({&pg,", 10, mono=True,
                  weight=600))
    o.append(text(LX + 8, y2 + 29, _fit("  pg.k_storage_of(slot), j / k_store_block})",
                                        10, LW - 16, True, "push2"), 10, mono=True,
                  weight=600))
    o.append(_tag(LX + LW - 8, y2 + 15, "new", C["new"]))
    o.append(lines(LX + 8, y2 + 45, [
        _fit("k_storage_of resolves the slot under the current view", 9, LW - 16),
        _fit("(the EAGLE entry for slot 0 while the EAGLE view is", 9, LW - 16),
        _fit("active); the resolved pair is kept, so a view change", 9, LW - 16),
        _fit("before the forward end cannot redirect the conversion.", 9, LW - 16)],
        9, 11))
    o.append(cite(LX + LW - 4, y2 + 94, "model.hpp:3434-3436; kv_cache.hpp:2137-2144"))
    boxes.append(("pending_k_blocks_.push_back({&pg, pg.k_storage_of(slot), "
                  "j / k_store_block})", "model.hpp:3434-3436; the reason at 3162-3163 "
                  "and kv_cache.hpp:2137-2144; model-seq-4"))

    # writer, note: a row saved again (kv_cache.hpp:2161) queues a block twice
    y3 = y2 + 112
    o.append(rect(LX, y3, LW, 78, "#fff", C["pend"], 1.2, 4))
    o.append(text(LX + 8, y3 + 14, "a row saved again", 9.5, weight=700))
    o.append(text(LX + 8 + text_width("a row saved again", 9.5) * 1.1 + 8, y3 + 14,
                  "(a block queued twice)", 9, fill=muted))
    o.append(lines(LX + 8, y3 + 27, [
        _fit("a row saved again into a complete, unconverted block", 9, LW - 16),
        _fit("makes note_k_row_saved return true again, so the list", 9, LW - 16),
        _fit("may hold one block twice; the second k_block_to_vnni_at", 9, LW - 16),
        _fit("call returns CONVERTED_FALSE and touches no plane.", 9, LW - 16)],
        9, 11))
    o.append(cite(LX + LW - 4, y3 + 74, "kv_cache.hpp:2161-2163; 2219-2223"))
    boxes.append(("a row saved again (a block queued twice)", "kv_cache.hpp:2161-2163 "
                  "(the comment's phrase: true again); 2219-2223 (CONVERTED_FALSE); "
                  "model-data-43, -44"))

    # writer: the storage reference is taken at the save (model.hpp:3162)
    y4 = y3 + 92
    o.append(rect(LX, y4, LW, 120, "#fff", C["line"], 1, 4))
    o.append(text(LX + 8, y4 + 15, "The storage reference is taken at the save", 10,
                  weight=700))
    o.append(rect(LX + 8, y4 + 21, LW - 16, 32, "#fff", ink, 1.1, 3))
    o.append(text(LX + 14, y4 + 33, "at the save [main, after the join]:", 9, weight=600))
    o.append(text(LX + 14, y4 + 46, _fit("k_storage_of(slot) -> { offset, state_ix }",
                                         9, LW - 28, True, "pin1"),
                  9, mono=True, weight=600))
    o.append(arrow(fid, "ink", [(LX + 50, y4 + 53), (LX + 50, y4 + 69)], ink, 1.3))
    o.append(text(LX + 58, y4 + 65, "the same pair, whatever the view is now", 8.5,
                  fill=ink, weight=600))
    o.append(rect(LX + 8, y4 + 71, LW - 16, 32, "#fff", ink, 1.1, 3))
    o.append(text(LX + 14, y4 + 83, "at the forward end [main]:", 9, weight=600))
    o.append(text(LX + 14, y4 + 96, "b.pg->k_block_to_vnni_at(b.storage, b.block)", 9,
                  mono=True, weight=600))
    o.append(cite(LX + LW - 4, y4 + 116, "model.hpp:3162-3163; kv_cache.hpp:2137-2144"))
    boxes.append(("The storage reference is taken at the save", "model.hpp:3162-3163 "
                  "(Note [K VNNI storage]: 'The storage reference is taken at the save, so "
                  "a storage view change cannot redirect the conversion'); "
                  "kv_cache.hpp:2137-2144, 2502-2504 (k_state_ix: the EAGLE entry for "
                  "slot 0 while the EAGLE view is active)"))

    # list -> reader (how many entries)
    o.append(arrow(fid, "pend", [(LX + LW, 322), (RX - 2, 322)], pend, 1.3))
    o.append(text(350, 314, "n entries", 8.5, "middle", fill=pend, weight=700))
    o.append(lines(350, 335, ["the sum over", "the pass's", "save_k calls"],
                   8.5, 10.5, "middle", fill=pend, weight=700))

    # reader: convert_pending_k_blocks
    o.append(fn_cell(RX, 288, RW, 72, "convert_pending_k_blocks",
                     [_fit("Convert the queued blocks (Note [K VNNI storage]).", 9.5,
                           RW - 16),
                      _fit("Main thread, after run() returned, staging drained.", 9.5,
                           RW - 16),
                      _fit("n = the sum over every save_k call of the pass", 9.5,
                           RW - 16)],
                     "model.hpp:3173; call 1847", tag="new"))
    boxes.append(("convert_pending_k_blocks", "model.hpp:3171-3180 (definition and "
                  "comment); 1847 (the call in run_forward); model-function-2"))
    ry = 368
    o.append(stmt_row(RX, ry, RW, 38, "if (pending_k_blocks_.empty()) return;",
                      "an empty list returns at once", "model.hpp:3174"))
    boxes.append(("if (pending_k_blocks_.empty()) return;", "model.hpp:3174"))
    ry += 42
    o.append(stmt_row(RX, ry, RW, 50, ['TRACE_EVENT("model", "convert_k_blocks",',
                                       '    "blocks", pending_k_blocks_.size());'],
                      "a trace event with the block count", "model.hpp:3175"))
    boxes.append(("TRACE_EVENT(\"model\", \"convert_k_blocks\", \"blocks\", "
                  "pending_k_blocks_.size())", "model.hpp:3175"))
    ry += 54
    r3y = ry
    o.append(stmt_row(RX, ry, RW, 50, ["for (pending_k_block const& b : pending_k_blocks_)",
                                       "    b.pg->k_block_to_vnni_at(b.storage, b.block);"],
                      "one call per entry; the bool it returns is discarded",
                      "model.hpp:3176-3178"))
    boxes.append(("for (b : pending_k_blocks_) b.pg->k_block_to_vnni_at(b.storage, "
                  "b.block)", "model.hpp:3176-3178; model-seq-5"))
    ry += 54
    o.append(stmt_row(RX, ry, RW, 38, "pending_k_blocks_.clear();",
                      "the list is empty until the next pass", "model.hpp:3179"))
    boxes.append(("pending_k_blocks_.clear();", "model.hpp:3179"))
    ry += 38

    # r3 -> k_block_to_vnni_at (around the right edge, 1 call per entry)
    ky = ry + 14
    o.append(arrow(fid, "ink", [(RX + RW, r3y + 25), (RX + RW + 12, r3y + 25),
                                (RX + RW + 12, ky + 36), (RX + RW + 2, ky + 36)], ink, 1.3))
    o.append(_tag(RX + RW - 6, ky - 6, "1 call per entry", ink, "end", 8.5))
    o.append(fn_cell(RX, ky, RW, 60, "page::k_block_to_vnni_at(storage, c)",
                     [_fit("converts block c of every KV head in place when its", 9.5,
                           RW - 16),
                      _fit("16 row bits are set and the block bit is clear", 9.5,
                           RW - 16)],
                     "kv_cache.hpp:2214-2236", tag="new", size=11))
    boxes.append(("page::k_block_to_vnni_at(storage, c)", "kv_cache.hpp:2214-2236 "
                  "(the comment is on its wrapper k_block_to_vnni, 2202-2207); "
                  "model-function-19, model-rule-1"))

    # the block before and after one converting call
    by = ky + 66
    o.append(block_state_box(RX, by, 106, 56, "pend", "complete, may wait",
                             ["16 row bits set,", "block bit clear"],
                             "kv_cache.hpp:2159"))
    boxes.append(("k_block_bits(c) all set, block bit clear (complete, may wait: the entry's "
                  "block)", "kv_cache.hpp:2219-2221 (the check); kv_cache.hpp:2159-2161 "
                  "and 2610 (the comments that define the state); 2157-2163 (how it got "
                  "there)"))
    o.append(arrow(fid, "vnni", [(RX + 106, by + 28), (RX + RW - 108, by + 28)], C["vnni"],
                   1.5))
    o.append(text(RX + 145, by + 20, "n_kv_heads", 8.5, "middle", fill=C["vnni"],
                  weight=700))
    o.append(text(RX + 145, by + 42, "planes", 8.5, "middle", fill=C["vnni"], weight=700))
    o.append(block_state_box(RX + RW - 106, by, 106, 56, "vnni", "converted",
                             ["block_to_vnni per", "plane; bit c set"],
                             "kv_cache.hpp:2227"))
    boxes.append(("converted (VNNI block)", "kv_cache.hpp:2227-2234 (block_to_vnni per "
                  "KV head, fetch_or of the block bit with release); model-data-44"))
    o.append(text(RX, by + 72, _fit("1 converting entry -> n_kv_heads planes, block c of "
                                     "each", 8.5, RW), 8.5, fill=muted))
    o.append(text(RX, by + 83, "a 2nd entry -> 0 planes", 8.5, fill=muted))
    o.append(cite(RX + RW - 4, by + 83, "kv_cache.hpp:2219-2230"))

    # ---- C: why the forward end: a block split across two minibatches -------
    # (a wall-clock excerpt of B4's forward-end lane; C2-S4, C2-N9)
    cy = max(y4 + 120, by + 86) + 12
    o.append(rect(20, cy, 660, 212, C["soft"], C["line"], 1, 4))
    o.append(text(28, cy + 15, "Why not in save_k: the reader that can still hold the "
                  "block's rows row-major (a wall-clock excerpt of B4)", 10, weight=700))
    boxes.append(("the reader that can still hold the block's rows row-major (why the "
                  "forward end)", "model.hpp:3160-3162 (Note [K VNNI storage]); 1842-1846 "
                  "(comment at the call); kv_cache.hpp:693-701 (why not in save_k); "
                  "model-rule-2"))
    GX, TX0, LW2, LH2 = 28, 146, 644, 50
    l1, l2 = cy + 24, cy + 80
    for ly, lab, sub in ((l1, "[main]", "worker_ix 0"),
                         (l2, "[attention workers]", "the last pool workers")):
        o.append(rect(GX, ly, LW2, LH2, "#fff", C["line"], 1, 3))
        o.append(text(GX + 6, ly + 20, lab, 9.5, weight=700))
        o.append(text(GX + 6, ly + 32, sub, 8.5, fill=muted))

    def blk2(x0, x1, ly, l1s, l2s=None, fill="#fff", stroke=ink, dash=None, col=None,
             crit=False):
        out = [rect(x0, ly + 6, x1 - x0, 32, fill, stroke, 1.2, 2, dash)]
        mx = (x0 + x1) / 2
        for t_ in (l1s, l2s):
            _fit(t_ or "", 8.5, x1 - x0 - 4, False, "strip block")
        if l2s:
            out.append(text(mx, ly + 19, l1s, 8.5, "middle", fill=col))
            out.append(text(mx, ly + 31, l2s, 8.5, "middle", fill=col))
        else:
            out.append(text(mx, ly + 25, l1s, 8.5, "middle", fill=col))
        if crit:
            out.append(crit_frame(x0, ly + 6, x1 - x0, 32))
        return "".join(out)

    # main: minibatch A saves 8 rows of block 2 (row-major), minibatch B of
    # the same pass completes it (queued), then the forward end
    o.append(blk2(TX0, 266, l1, "minibatch A: save_k", "page 9, offsets 32..39",
                  C["rm_fill"], C["rm"]))
    o.append(blk2(272, 402, l1, "minibatch B: save_k", "offsets 40..47: queued",
                  C["pend_fill"], C["pend"], "5 3"))
    o.append(blk2(408, 464, l1, "run() joins", dash="4 3"))
    o.append(blk2(468, 554, l1, "wait_for_coop_gof", fill=C["soft"], stroke=muted))
    o.append(blk2(558, 676, l1, "convert_pending_k_blocks", fill=C["pend_fill"],
                  stroke=C["pend"], crit=True))
    o.append(text(511, l1 + 47, "stages the GOF tail: reads rows row-major", 8.5, "middle",
                  fill=muted))
    boxes.append(("minibatch A: save_k (page 9, offsets 32..39, row-major) / minibatch B: "
                  "save_k (offsets 40..47: block 2 complete, queued)",
                  "kv_cache.hpp:693-697 (a block may be split across two minibatches of "
                  "one pass); common.hpp:953-956 (grains of at most minibatch_grain_size "
                  "tokens); STYLE.md worked example, continued"))
    boxes.append(("run() joins -> wait_for_coop_gof -> convert_pending_k_blocks (B4's "
                  "forward-end blocks)", "model.hpp:1836-1847; 3578-3592 "
                  "(wait_for_coop_gof drains the GOF tail)"))
    # attention workers: during A's save_k their pending section waits; during
    # B's save_k an idle worker stages A's GOF and reads block 2 row-major
    o.append(blk2(TX0, 266, l2, "pending section waits", "behind A's save_k", dash="4 3"))
    o.append(blk2(272, 402, l2, "help_drain_gof (A's GOF)", "reads block 2 row-major",
                  fill=C["soft"], stroke=ink))
    o.append(blk2(408, 446, l2, "exit", fill=C["soft"], stroke=muted))
    boxes.append(("pending section waits (attention workers, during A's save_k)",
                  "model.hpp:3093-3094; self_attention.hpp:761"))
    boxes.append(("help_drain_gof (stages A's GOF: reads the block's rows row-major)",
                  "kv_cache.hpp:694-697; self_attention.hpp:761"))
    ty = l2 + LH2 + 14
    o.append(lines(28, ty, [
        _fit("grains of 8 tokens (minibatch_grain_size): user B's 16 tokens come as two "
             "grains, so block 2 can be split across", 9, 644),
        _fit("minibatches A and B of one pass. A's credit_gof_save queues A's GOF; its "
             "staging gather (help_drain_gof on an attention", 9, 644),
        _fit("worker, or wait_for_coop_gof on main) reads block 2's rows row-major while "
             "B saves the block's last rows. So the", 9, 644),
        _fit("conversion waits for the forward end, after wait_for_coop_gof: the first "
             "point where no reader of this pass is left.", 9, 644)],
        9, 11))
    o.append(cite(676, cy + 206, "model.hpp:3160-3162; 1840-1847; kv_cache.hpp:693-701; "
                  "common.hpp:953-956"))
    H = cy + 222

    cap = ("Updates B1 and B4: the pending_k_block record and the pending_k_blocks_ list "
           "of B1 get their writer and their reader, and the strip at the bottom is a "
           "wall-clock excerpt of B4's forward-end lane. Look at the left column first. After every row is stored, main "
           "pushes one entry for every true answer of note_k_row_saved. The entry keeps the "
           "k_storage_ref resolved at the save, and a later view change therefore cannot "
           "move the conversion target. Then the right column. convert_pending_k_blocks "
           "drains the list once per forward, one k_block_to_vnni_at call per entry. One "
           "call converts the block's n_kv_heads planes once. A second entry of the same "
           "block converts nothing. The worked example is the window of B1: its two "
           "whole-block saves and its 8-row run queue nothing, and the one entry shown "
           "comes from a later minibatch that completes block 2 of page 9 (unit M6). The "
           "strip shows why the conversion waits for the forward end: when that later "
           "minibatch is in the same pass (a block split across two minibatches, grains "
           "of 8 tokens), the staging gather of the earlier minibatch's GOF reads the "
           "block's rows row-major while the later minibatch saves the block's last rows.")
    legend = [
        ("ctx_ink", "grey fill, ink outline: the state (model.hpp) group that holds the two "
                    "fields of B1, and, in the strip, help_drain_gof: the attention worker's "
                    "block that reads block 2 row-major (A's GOF)"),
        ("ctx", "grey band, light grey outline: the wall-clock strip 'Why not in save_k', "
                "an excerpt of B4 with the lanes [main] and [attention workers]"),
        ("lane", "white box, light grey outline: the worked example (block 2 -> one entry), "
                 "the note on the storage reference, and the two lanes of the strip"),
        ("box", "white box, ink outline: the writer's and the reader's code: note_k_row_saved "
                "(the writer), convert_pending_k_blocks and its four statements (the "
                "reader), page::k_block_to_vnni_at, the two moments of the storage "
                "reference (at the save, at the forward end), and the field k_store_block; "
                "the name in bold monospace, the description in sans-serif"),
        ("orange dashed box, orange-red arrow and label: the deferred conversion list "
         "pending_k_blocks_ and its record pending_k_block, a block that is complete and "
         "may wait (block 2, minibatch B's save_k in the strip), and the list's traffic "
         "(0..1 entry per KV item, 'true' from note_k_row_saved to push_back, n entries "
         "from the writer to the reader)", "multi", ["pend", ("arrow", C["pend"])]),
        ("white box, orange-red outline: the three members of pending_k_block (pg, storage, "
         "block), the push_back that fills the list, and the note on a row saved again (a "
         "block queued twice)", "#fff", C["pend"], False, False),
        ("pend_solid", "orange-red: convert_pending_k_blocks in the strip, the conversion of "
                       "the queued blocks at the forward end"),
        ("rm", "orange: minibatch A's save_k in the strip, the first 8 rows of block 2 "
               "(page 9, offsets 32..39) saved row-major"),
        ("blue box, arrow and label: the converted block after k_block_to_vnni_at "
         "(complete -> converted, n_kv_heads planes)", "multi",
         ["vnni", ("arrow", C["vnni"])]),
        ("idle", "dashed ink outline: waiting in the strip: run() joins on main, and the "
                 "pending section that waits behind A's save_k on the attention workers"),
        ("grey fill, grey outline: the strip's blocks outside this unit's code: "
         "wait_for_coop_gof on main, exit on the attention workers",
         C["soft"], C["muted"], False, False),
        ("crit", "thick red frame: convert_pending_k_blocks in the strip, the serial part of "
                 "main's forward end"),
        ("arrow", "ink arrow: the same {offset, state_ix} pair from the save to the forward "
                  "end, and the for loop -> k_block_to_vnni_at (1 call per entry)"),
        ("font_mono", "monospace = identifiers and values from the code: the fields, the "
                      "members, the functions, the statements and the worked example entry"),
        ("font_sans", "sans-serif = prose: descriptions, the column titles, the lane labels "
                      "and the strip's note"
                      "; grey sans-serif = a note or a secondary label (row labels, index "
                      "numbers, the one-line notes under a group)"),
        "font_cite",
        ("font_tag", "bold 'new' = added by this PR: pending_k_blocks_, k_store_block, "
                     "pending_k_block, push_back, convert_pending_k_blocks, "
                     "k_block_to_vnni_at"),
    ]
    return figure(fid, W, H, "The deferred conversion list: its record, writer and reader",
                  "".join(o), cap, boxes=boxes, legend=legend)
