"""Change diagram of unit m3 (model.hpp page of PR 4959): the row-recording
loop after the join, and the hardware-attention policy. Head lines 3411-3433.
"""
from svg_helpers import C, arrow, block_cell, cite, figure, lines, marker_defs, rect, text
from base_model import bits_strip, block_state_box, fit, note_box, stmt_row

BASE = ("Updates B3 steps 5 and 8 and B5's second decision: the loop body statement by "
        "statement, the gate cached_operation_uses_hw in front of it, and the worked "
        "example's two outcomes as bit strips: the prefill records bits 0..40 and queues "
        "nothing; the decode step that saves offset 47 completes block 2 and queues it.")

W = 700


def fig():
    fid = "model-d3"
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "hw": C["hw"]})]
    boxes = []
    o.append(text(20, 18, "save_k_impl after every store is done: record this pass's rows (main thread)",
                  12, weight=700))
    o.append(text(20 + 520, 18, "new", 9, fill=C["new"], weight=700))
    # gate 1: layout
    o.append(stmt_row(20, 26, 660, 30, "if constexpr (k_vnni::layout_on<geometry.kv.head_size>)",
                      "a row-major slot keeps no bits: the whole block is compiled out", "model.hpp:3413"))
    boxes.append(("if constexpr (k_vnni::layout_on)", "model.hpp:3413"))
    # gate 2: hardware
    gy = 66
    o.append(rect(20, gy, 400, 44, "#fff", C["ink"], 1.6, 10))
    o.append(text(220, gy + 17, "if (!cached_operation_uses_hw(binding.operation))", 10, "middle", True,
                  weight=700))
    o.append(text(220, gy + 32, "does the FPGA score this operation's K? (decided once per model)", 8.5,
                  "middle"))
    o.append(cite(414, gy + 40, "model.hpp:3419; 1529"))
    boxes.append(("cached_operation_uses_hw", "model.hpp:3419; defined at 1528-1531"))
    o.append(arrow(fid, "ink", [(220, 56), (220, gy - 2)], C["ink"]))
    o.append(rect(440, gy, 240, 58, C["hw_fill"], C["hw"], 1.4, 4))
    o.append(text(448, gy + 15, "yes: the loop is skipped", 10, weight=700))
    o.append(lines(448, gy + 28, ["no row bit, no entry: the block stays row-major",
                                  "(Note [Row-major blocks under hardware attention])"], 8.5, 10.5))
    o.append(cite(676, gy + 54, "kv_cache.hpp:763-799"))
    boxes.append(("the loop is skipped under hardware attention", "model.hpp:3414-3419; kv_cache.hpp:763-799"))
    o.append(arrow(fid, "hw", [(420, gy + 22), (438, gy + 22)], C["hw"]))
    # the loop body
    ly = 130
    o.append(text(232, ly - 8, "no: for (token_job_id ix : q_batch->items)", 9.5, weight=600))
    o.append(arrow(fid, "ink", [(220, gy + 44), (220, ly - 2)], C["ink"]))
    o.append(rect(20, ly, 400, 196, C["rows_fill"], C["rows"], 1.4, 5))
    o.append(stmt_row(28, ly + 8, 384, 30, "if (!self.token_jobs_do_kv[ix]) continue;",
                      "a job without KV work this forward has no row", "model.hpp:3422"))
    o.append(stmt_row(28, ly + 42, 384, 42, ["page& pg = page_of(token_jobs[ix]);",
                                             "const size_t j = pg.offset_in_page(tok_ix);"],
                      "the page and the page offset of the token", "model.hpp:3423-3425"))
    o.append(stmt_row(28, ly + 88, 384, 42, ["if (pg.note_k_row_saved<geometry.kv>(slot, j))",
                                             "  pending_k_blocks_.push_back({&pg,",
                                             "    pg.k_storage_of(slot), j / k_store_block});"],
                      "", "model.hpp:3426-3428"))
    o.append(lines(28, ly + 144, ["note_k_row_saved sets bit j (fetch_or when clear) and returns true",
                                  "only when block j / 16 now has all 16 row bits and its block bit",
                                  "is clear; a row of a converted block returns false (no entry);",
                                  "a row saved again into a block that waits returns true again"],
                   8.5, 10.5))
    o.append(cite(414, ly + 192, "kv_cache.hpp:2207-2231"))
    boxes.append(("the loop body (token_jobs_do_kv, page_of, offset_in_page, note_k_row_saved, push_back)",
                  "model.hpp:3420-3430"))
    boxes.append(("note_k_row_saved", "kv_cache.hpp:2207-2231"))
    # the entry
    o.append(arrow(fid, "pend", [(420, ly + 110), (438, ly + 110)], C["pend"]))
    o.append(block_state_box(440, ly + 80, 240, 60, "pend", "complete, may wait",
                             ["one entry {&pg, {offset, state_ix}, c}", "per block completed by short runs"],
                             "model.hpp:3161-3166"))
    boxes.append(("complete, may wait (the queued entry)", "model.hpp:3161-3166; 3427-3428"))
    o.append(note_box(440, ly + 150, 240, 56, "the order",
                      ["after the join (every store visible), before the",
                       "marks loop; main only (q_batch->items order)"],
                      "model.hpp:3394-3433", size=8.5))
    boxes.append(("the order: after the join, before the marks loop", "model.hpp:3394-3433"))
    # worked example strips
    sy = ly + 216
    o.append(text(20, sy, "worked example, k_rows_saved_[5] of page 7 (one square per offset):", 10,
                  weight=700))
    s1, _ = bits_strip(20, sy + 12, 41, w=400, h=10)
    o.append(s1)
    o.append(text(430, sy + 21, "after the prefill: bits 0..40; nothing queued", 8.5))
    o.append(text(430, sy + 31, "(0..31: converted -> false; 32..40: 9 of 16 -> false)",
                  8, fill=C["muted"]))
    s2, _ = bits_strip(20, sy + 40, 47, w=400, h=10, hi=47)
    o.append(s2)
    o.append(text(430, sy + 49, "the step that saves offset 47: bit 47 completes block 2", 8.5))
    o.append(text(430, sy + 59, "-> true -> {&page 7, {slot 5, 5}, 2} queued",
                  8, fill=C["muted"]))
    o.append(text(20, sy + 70, "blocks:", 8.5, fill=C["muted"]))
    bx = 70
    for c, st in enumerate(["vnni", "vnni", "pend", "empty"]):
        o.append(block_cell(bx, sy + 62, 90, 14, st, f"block {c}", 8.5))
        bx += 96
    o.append(text(460, sy + 73, "k_vnni_blocks_[5] = 0b0011 until the forward end", 8.5, fill=C["muted"]))
    boxes.append(("k_rows_saved_[5] / k_vnni_blocks_[5] (worked example)", "kv_cache.hpp:2639-2653"))
    H = sy + 90
    cap = ("Updates B3 (steps 5 and 8) and B5 (the second decision): the row-recording loop "
           "that this PR adds after the stores of save_k_impl. It is compiled only for a "
           "VNNI slot, skipped when the hardware attention scores the operation, and "
           "otherwise calls note_k_row_saved per item and queues the block when that "
           "returns true. The two bit strips show the worked example: the prefill records "
           "bits 0..40 and queues nothing; the decode step that saves offset 47 completes "
           "block 2 and queues it.")
    legend = [
        ("box", "white box, ink outline: one statement of the loop, or the decision"),
        ("rows", "green: the row-recording loop and the set bits of k_rows_saved_[5]"),
        ("bit_clear", "white square: a clear bit of k_rows_saved_[5]"),
        ("hw", "yellow: the hardware-attention branch (the loop is skipped)"),
        ("pend", "orange-red dashed: the queued entry; block 2 in the strip (complete, may wait)"),
        ("vnni", "blue: blocks 0 and 1 (converted by whole-block saves)"),
        ("empty", "grey dashed: block 3 (no row saved)"),
        ("hi", "pale yellow: bit 47, the row that completes block 2"),
        ("ctx", "grey note: the order of the loop among save_k_impl's steps"),
        ("arrow", "ink arrow: the control flow"),
        ("yellow arrow: the skipped branch", "arrow", C["hw"]),
        ("orange-red arrow: push_back", "arrow", C["pend"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR"),
    ]
    return figure(fid, W, H, "The row-recording loop and the hardware-attention policy",
                  "".join(o), cap, boxes=boxes, legend=legend)
