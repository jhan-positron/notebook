"""Change diagram of unit m6 (model.hpp, PR 4958): the marks loop loses the
per-token K store (head lines 3369-3385; the 23 removed base lines 3096-3116
are anchored before head 3376).

Updates B3: the order of the store, the join and the marks on main's lane,
set against the base's order: before the PR, main stored each token's K row
(set_k_row for a VNNI slot, page::k(...).set for a row-major slot) inside the
marks loop; at the head every K row of the minibatch is stored first, by any
thread of the window, then main joins, marks and credits the tokens and
counts the downstream latches down.
"""
from svg_helpers import (C, arrow, cite, figure, line, lines, marker_defs,
                         rect, text, text_width)
from base_model import CRIT_SW, MAIN_FILL, crit_frame

BASE = ("Updates B3. Steps 3 to 7 of main's lane are set in one row against the "
        "base's order: before the PR, the marks loop held the per-token K store "
        "(set_k_row for a VNNI slot, page::k(...).set for a row-major slot) before "
        "each token's mark; at the head every K row is stored first (store_k_block, "
        "any thread of the window), then main joins, marks, credits and counts the "
        "latches down.")

FID = "model-d6"
W = 700
RED = C["gone"]


def _fit(s, size, maxw, mono=False, where=""):
    w = text_width(s, size, mono)
    if w > maxw:
        raise ValueError(f"{where}: '{s}' is {w:.0f} px wide, room {maxw} px")


def note_box(x, y, w, h, title, body, ref, stroke=C["ink"], fill="#fff",
             dash=None, tag=None, size=9, title_size=10, title_mono=True, sw=1.2):
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


def fig():
    fid = FID
    H = 452
    o = [marker_defs(fid, {"ink": C["ink"], "gone": RED})]
    boxes = []
    o.append(text(15, 16, "Where the K store sits relative to the marks: before (base) and at "
                  "the head (B3 steps 3-7 in one row)", 11, weight=600))

    BY = 28
    o.append(rect(15, BY, 670, 150, "#fff", RED, 1.3, 5, "5 3"))
    o.append(text(23, BY + 15, "before (base 26b86a279a): [main] alone, one token at a time, "
                  "in q_batch->items order", 10, fill=RED, weight=700))
    o.append(cite(681, BY + 15, "base model.hpp:3088-3124"))
    boxes.append(("mark_k_complete loop [before: the marks loop with the K store inside it]",
                  "model.hpp:3369-3382 (the marks loop at head); base model.hpp:3088-3124 "
                  "(the loop with the store, 23 lines removed before head 3376)"))
    by = BY + 26
    o.append(note_box(23, by, 250, 94, "set_k_row / pg.k(...).set x n_kv_heads",
                      ["the K store of token ix inside the marks",
                       "loop, before its mark: set_k_row (VNNI slot,",
                       "with a bf16 conversion on the stack for other",
                       "activation types) or page::k(...).set (row-",
                       "major slot); 'Update the page first so HW",
                       "sees the latest K values.'"],
                      "base model.hpp:3096-3116", stroke=RED, dash="5 3", tag="removed"))
    boxes.append(("set_k_row / pg.k(...).set x n_kv_heads (removed)",
                  "base model.hpp:3096-3116 (the 23 lines removed before head line 3376); "
                  "now store_k_block, model.hpp:3212-3221 and 3260-3289"))
    o.append(note_box(313, by, 200, 94, "mark_k_complete(slot, j)",
                      ["counts the (offset, slot) save; true",
                       "when K and V are both in (count 2);",
                       "then credit_gof_save (hardware slot)"],
                      "kv_cache.hpp:2236-2240", fill=MAIN_FILL, tag="unchanged"))
    boxes.append(("mark_k_complete, credit_gof_save", "kv_cache.hpp:2236-2240 ('Returns true "
                  "if this was the completing save (count reached 2)'); model.hpp:3376-3381; "
                  "3480 (credit_gof_save)"))
    o.append(note_box(545, by, 140, 94, "count_down",
                      ["upstream_kvs_ready[slot]", "per downstream minibatch"],
                      "model.hpp:3383-3385", fill=MAIN_FILL, tag="unchanged"))
    boxes.append(("upstream_kvs_ready[slot].count_down()", "model.hpp:3383-3385"))
    o.append(arrow(fid, "gone", [(273, by + 47), (311, by + 47)], RED, 1.3))
    o.append(arrow(fid, "ink", [(513, by + 47), (543, by + 47)], C["ink"], 1.3))
    o.append(line(413, by + 94, 413, by + 104, RED, 1.2))
    o.append(line(413, by + 104, 148, by + 104, RED, 1.2))
    o.append(arrow(fid, "gone", [(148, by + 104), (148, by + 96)], RED, 1.2))
    o.append(text(280, by + 116, "next token: store, mark, credit, store, mark, ... (n tokens)",
                  8.5, "middle", fill=RED, weight=600))

    HY = 192
    o.append(rect(15, HY, 670, 162, "#fff", C["new"], 1.3, 5))
    o.append(text(23, HY + 15, "at the head (PR 4958): every K row of the minibatch is stored "
                  "before the first mark_k_complete", 10, fill=C["new"], weight=700))
    o.append(cite(681, HY + 15, "model.hpp:3121-3128"))
    boxes.append(("at the head: stores, join, marks, count_down",
                  "model.hpp:3121-3128 (Note [Shared block save]); 3340-3385"))
    ty = HY + 30
    o.append(line(23, ty, 163, ty, C["ink"], 1))
    o.append(text(93, ty - 3, "[any thread of the window]", 8.5, "middle", weight=700))
    o.append(line(173, ty, 685, ty, C["ink"], 1))
    o.append(text(429, ty - 3, "[main, worker_ix 0]", 8.5, "middle", weight=700))
    boxes.append(("worker_ix 0 [main] / [any thread of the window]",
                  "model.hpp:3295-3305 (comment and signature); 3118-3120; 3127-3128"))
    hy = HY + 40
    o.append(note_box(23, hy, 140, 82, "store_k_block",
                      ["per unit u: set_k_block", "(2..16 rows) or set_k_row",
                       "(one row)"],
                      "model.hpp:3340-3346; 3367", tag="new"))
    boxes.append(("store_k_block per unit", "model.hpp:3340-3346 (shared), 3366-3368 "
                  "(unshared); definition 3193-3293"))
    o.append(note_box(173, hy, 110, 82, "join",
                      ["finished >=", "n_helpers", "(acquire)"],
                      "model.hpp:3351-3365", dash="5 3", tag="new", sw=CRIT_SW))
    boxes.append(("join (finished.load(acquire) >= n_helpers)", "model.hpp:3351-3365"))
    o.append(note_box(293, hy, 130, 82, "'WK roped' log",
                      ["log_intermediate per", "token, as before;", "no store any more"],
                      "model.hpp:3369-3375", fill=MAIN_FILL, tag="unchanged", sw=CRIT_SW))
    boxes.append(("log_intermediate 'WK roped' (the marks loop, per token)",
                  "model.hpp:3369-3375; 1277 (log_intermediate)"))
    o.append(note_box(433, hy, 120, 82, "mark_k_complete",
                      ["+ credit_gof_save:", "the per-token marks", "and GOF credits"],
                      "model.hpp:3376-3381", fill=MAIN_FILL, tag="unchanged", sw=CRIT_SW))
    boxes.append(("mark_k_complete, credit_gof_save (the per-token completion marks and "
                  "GOF credits)", "model.hpp:3376-3381; model.hpp:3127-3128"))
    o.append(note_box(563, hy, 122, 82, "count_down",
                      ["upstream_kvs_ready", "[slot].count_down()", "per downstream"],
                      "model.hpp:3383-3385", fill=MAIN_FILL, tag="unchanged", sw=CRIT_SW))
    for x0, x1 in ((163, 173), (283, 293), (423, 433), (553, 563)):
        o.append(arrow(fid, "ink", [(x0, hy + 41), (x1 - 1, hy + 41)], C["ink"], 1.2))
    o.append(text(23, HY + 138, "every unit is stored once main leaves the join; every row "
                  "store happens-before the latch count_down (main's acquire on finished)",
                  8.5, fill=C["ink"], weight=600))
    o.append(text(23, HY + 152, "the marks and GOF credits stay on main, after the join, in "
                  "q_batch->items order, one token at a time [model.hpp:3121-3128]", 8.5,
                  fill=C["muted"]))
    for s in ("every unit is stored once main leaves the join; every row store happens-before "
              "the latch count_down (main's acquire on finished)",
              "the marks and GOF credits stay on main, after the join, in q_batch->items "
              "order, one token at a time [model.hpp:3121-3128]"):
        _fit(s, 8.5, 660, False, "head note")
    ny = HY + 162 + 14
    o.append(rect(15, ny, 670, 36, MAIN_FILL, C["line"], 1, 4))
    o.append(lines(23, ny + 14, ["the base comment 'Update the page first so HW sees the latest "
                                 "K values.' moved up, reworded: 'Update the pages first. That",
                                 "way HW sees the latest K values.' (head 3324, before the "
                                 "window); the loop keeps its per-token comment on the GOF credit"],
                   8.5, 11))
    o.append(cite(681, ny + 32, "model.hpp:3324; 3377-3378"))
    boxes.append(("'Update the pages first. That way HW sees the latest K values.'",
                  "model.hpp:3324 (head; the base phrase was at base model.hpp:3096)"))
    o.append(text(15, H - 18, "red dashed = removed base code; dashed = a wait; thick red "
                  "frame = main's serial part (the critical path of B4);", 9, fill=C["muted"]))
    o.append(text(15, H - 6, "bold new = added; grey = unchanged context; [...] = the thread that "
                  "runs the cell.", 9, fill=C["muted"]))

    cap = ("Updates B3: steps 3 to 7 of main's lane placed against the base's order. "
           "Before the PR, main stored each token's K row inside the marks loop (store, "
           "mark, credit, next token), with the VNNI scatter set_k_row or the row-major "
           "page::k(...).set. At the head every K row of the minibatch is stored first, by "
           "any thread of the window. Then main joins, logs and marks the tokens, credits "
           "the GOFs one at a time, and counts the downstream latches down. The red dashed "
           "cell is the removed per-token store (23 base lines before head line 3376).")
    legend = [
        ("gone", "red dashed: before (base 26b86a279a), the frame of the base order and "
                 "the removed per-token store set_k_row / pg.k(...).set"),
        ("red arrow and red label: the base order, the removed store -> mark_k_complete, "
         "and the loop back to the next token ('next token: store, mark, credit, ...')",
         "arrow", RED),
        ("box", "white box, ink outline: the frame of the head order and its new cell "
                "store_k_block; the name in bold monospace, its description in sans-serif"),
        ("idle", "dashed ink outline: the join, main waits for finished >= n_helpers"),
        ("crit", "thick solid red frame: the join, the log, the marks and the count_down: "
                 "main's serial part (the critical path of B4)"),
        ("ctx_ink", "grey fill, ink outline: the unchanged context cells 'WK roped' log, "
                    "mark_k_complete and count_down, before and at the head"),
        ("ctx", "grey band, light grey outline: the note on the moved comment"),
        ("arrow", "ink arrow: the step from one cell to the next (mark -> count_down before; "
                  "store -> join -> log -> mark -> count_down at the head)"),
        ("thin ink line over the cells: the span of the thread named above it ([any thread "
         "of the window], [main, worker_ix 0])", "line", C["ink"]),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions; grey "
                      "sans-serif = a note"),
        "font_cite",
        ("font_tag", "bold 'new' = added by this PR; red 'removed' = the base store the PR "
                     "removes; grey 'unchanged' = context the PR keeps"),
    ]
    return figure(fid, W, H, "The order of the store, the join and the marks",
                  "".join(o), cap, boxes=boxes, legend=legend)
