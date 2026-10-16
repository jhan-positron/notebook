"""Change diagrams of unit m4 (model.hpp): store_k_block, the run store.

Two figures, because one cannot carry the six lead bullets legibly beside the
code:
  d4a = the function's contract, the layout branch (the row-major branch is
        the per-token loop moved out of the marks loop) and how a run of a
        VNNI slot is collected and ended (the four locals, the ending rules,
        the worked example's masks).
  d4b = what a run becomes (set_k_row per token and KV head, or the assert,
        the 16-pointer table, set_k_block per KV head and note_k_block_saved
        with its two fetch_or orders) and where every stored row comes from
        (row_of; k_source_row in place for a bf16 K buffer, conv on the stack
        otherwise).

Every label is an identifier or a comment phrase of h/tron/models/model.hpp
(head line numbers), h/tron/models/kv_cache.hpp or h/tron/tensor/k_vnni.hpp
of the same PR. Facts: facts/model.json (model-function-8, -9, -21, -22,
-23, -25, -26; model-data-18, -19, -20, -34, -40, -41, -42; model-seq-1, -2;
model-rule-8, -12; model-unit-6; the trivial entry t2 of units_model.json).
"""
from svg_helpers import (C, arrow, bit_row, cite, figure, fn_cell, lines,
                         marker_defs, rect, text, text_width)
from base_model import UNITS_EXAMPLE, block_state_box, decision_box

BASE = ("Updates B5. The two figures open B5's 'one run (store_k_block)' box and its "
        "two store arrows. They add how a run is collected and ended, the row-major "
        "branch moved out of the marks loop, the call counts of set_k_row and "
        "set_k_block, the two bits note_k_block_saved publishes with their memory "
        "orders, and the bf16 source-row path (k_source_row in place, or conv on "
        "the stack).")

W = 700


# ---- local helpers (no new primitives outside this module) ------------------
def _w(s, size, mono=False, bold=False):
    return text_width(s, size, mono) * (1.08 if bold else 1.0)


def _fit(s, size, avail, mono, where, bold=False):
    """Abort the render when a string is wider than the room it has."""
    w = _w(s, size, mono, bold)
    if w > avail:
        raise ValueError(f"{where}: '{s}' needs {w:.0f} px, has {avail:.0f} px")


def note_box(x, y, w, h, title, body, ref, stroke=C["ink"], fill="#fff",
             dash=None, tag=None, tag_color=None, title_color=None,
             body_color=None, title_size=10, body_size=9):
    """A box with a mono title line, small sans body lines and a citation in
    the lower-right corner. Height: 44 for one body line, 56 for two, 70 for
    three (the citation needs its own 12 px under the last line)."""
    o = [rect(x, y, w, h, fill, stroke, 1.2, 4, dash)]
    room = w - 16 - (_w(tag, 9, bold=True) + 12 if tag else 0)
    _fit(title, title_size, room, True, "note_box title", bold=True)
    o.append(text(x + 8, y + 14, title, title_size, mono=True, weight=700,
                  fill=title_color))
    for s in body:
        _fit(s, body_size, w - 16, False, "note_box body")
    o.append(lines(x + 8, y + 27, body, body_size, 11, fill=body_color))
    if tag:
        o.append(text(x + w - 8, y + 14, tag, 9, "end",
                      fill=tag_color or C["new"], weight=700))
    _fit(ref, 8.5, w - 8, True, "note_box cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


# ---- D4a: the contract, the layout branch, the run -------------------------
def fig_a():
    fid = "model-d4a"
    H = 542
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "gone": C["gone"], "unit": C["unit"]})]
    boxes = []

    # 1. the function: contract line and callers
    o.append(fn_cell(20, 12, 660, 76,
                     "store_k_block(q_batch, slot, ks, task_begin, task_end)",
                     ["Store the K rows (every KV head) of items[task_begin, task_end) "
                      "into slot  [any thread of the window]",
                      "Marks, saved-row bits of partial runs and credits are not touched "
                      "here: save_k_impl does them after",
                      "every store is done. Called per claimed unit u (shared) or once "
                      "for items[0, n_items) (unshared)."],
                     "model.hpp:3240-3245", tag="new"))
    boxes.append(("store_k_block", "model.hpp:3232-3344 (comment 3232-3239, signature "
                  "3240-3245); callers 3395-3396 (per unit), 3418 (unshared)"))

    # 2. the layout decision
    o.append(decision_box(20, 106, 190, 58, "VNNI slot?",
                          ["k_vnni::layout_on<", "geometry.kv.head_size>"],
                          "model.hpp:3251"))
    boxes.append(("VNNI slot? (k_vnni::layout_on)",
                  "model.hpp:3251; tensor/k_vnni.hpp:119-130"))

    # 3. the row-major branch (no): the loop moved out of the marks loop
    RX, RW = 250, 430
    o.append(note_box(RX, 106, RW, 58,
                      "page::k(slot, kv_head, j).set  per token",
                      ["one row store per (KV item, KV head), the K buffer row in place; "
                       "[main] alone:",
                       "k_store_shared is false for a row-major slot, so the store is "
                       "never shared"],
                      "model.hpp:3252-3261; 3193-3194", tag="moved here (new)"))
    boxes.append(("page::k(slot, kv_head, j).set (row-major slots)",
                  "model.hpp:3252-3261; k_store_shared false at 3193-3194; "
                  "kv_cache.hpp:2088-2096"))
    o.append(arrow(fid, "rm", [(210, 135), (248, 135)], C["rm"], 1.4))
    o.append(text(229, 129, "no", 9, "middle", fill=C["rm"], weight=700))

    # 4. before: the removed copy inside the marks loop
    o.append(note_box(RX, 184, RW, 58,
                      "before: the same loop inside the marks loop of save_k_impl",
                      ["// Update the page first so HW sees the latest K values.",
                       "for (kv_head ...) pg.k<geometry.kv>(slot, kv_head, j).set(kout)  "
                       "-> removed"],
                      "base model.hpp:3099-3104 (removed after head 3446)",
                      stroke=C["gone"], dash="5 3", title_color=C["gone"],
                      body_color=C["gone"]))
    boxes.append(("slice<...>() + page::k(...).set per KV head [before: the per-token K store inside the marks loop, removed]",
                  "model.hpp:3247-3261 (the same store at head, row-major slots); base model.hpp:3099-3104, the eight lines removed after head "
                  "3446 (trivial entry t2)"))
    o.append(arrow(fid, "gone", [(465, 184), (465, 166)], C["gone"], 1.4))
    o.append(text(473, 178, "moved", 9, fill=C["gone"], weight=700))

    # 5. yes: down to the run
    o.append(arrow(fid, "vnni", [(115, 164), (115, 258)], C["vnni"], 1.4))
    o.append(text(123, 215, "yes", 9, fill=C["vnni"], weight=700))

    # 6. the run of a VNNI slot
    UY, UH = 260, 270
    o.append(rect(20, UY, 660, UH, "#fff", C["ink"], 1.2, 6))
    o.append(text(32, UY + 16, "The run: consecutive items in block c of this page",
                  11, mono=True, weight=700))
    o.append(cite(676, UY + 16, "model.hpp:3280-3281; 3270-3299"))
    boxes.append(("The run: consecutive items in block c of this page (store_k_block, "
                  "VNNI slot)", "model.hpp:3280-3281 (the comment); 3270-3299 (the loop)"))
    o.append(text(32, UY + 30, "while (t < task_end): the collect loop (3286-3298), then "
                  "set_k_row x n or set_k_block (3300-3340)", 9, fill=C["muted"]))
    o.append(text(32, UY + 41, "tokens without KV work in between are skipped and do not "
                  "end the run", 9, fill=C["muted"]))

    # 6a. the locals of one run
    LX, LW, LY = 32, 296, UY + 52
    o.append(rect(LX, LY, LW, 82, "#fff", C["ink"], 1.2, 4))
    o.append(text(LX + 8, LY + 14, "run_ix, run_t, present, n", 10, mono=True, weight=700))
    o.append(text(LX + 8 + _w("run_ix, run_t, present, n", 10, True, True) + 8, LY + 14,
                  "the locals of one run", 9, fill=C["muted"]))
    local_rows = [("run_ix[k_store_block]", "token_job_id: the items"),
                  ("run_t[k_store_block]", "uint8_t: j % 16, the lane"),
                  ("present", "__mmask16: one bit per lane"),
                  ("n", "size_t: rows, 1 .. 16")]
    ly = LY + 27
    for nm, ds in local_rows:
        _fit(nm, 9, 128, True, "local name", bold=True)
        _fit(ds, 9, LW - 148, False, "local desc")
        o.append(text(LX + 8, ly, nm, 9, mono=True, weight=600))
        o.append(text(LX + 140, ly, ds, 9))
        ly += 11
    o.append(cite(LX + LW - 4, LY + 78, "model.hpp:3282-3285"))
    boxes.append(("run_ix, run_t, present, n (locals of one run)",
                  "model.hpp:3282-3285; filled at 3295-3298"))
    card = "1 run -> n rows of block c, n = 1 .. 16"
    _fit(card, 9, LW - _w("model.hpp:3286", 8.5, True) - 10, False, "run card", bold=True)
    o.append(text(LX, LY + 98, card, 9, fill=C["ink"], weight=700))
    o.append(cite(LX + LW, LY + 98, "model.hpp:3286"))

    # 6b. how a run ends
    EX, EW, EY = 344, 324, UY + 52
    o.append(note_box(EX, EY, EW, 104, "for (; t < task_end && n < k_store_block; ++t)",
                      ["how a run ends:",
                       "skip:  !token_jobs_do_kv[ix], the run goes on [3288]",
                       "break: another page, &page_of(tok_ix) != &pg [3290]",
                       "break: another block, j / k_store_block != c [3292]",
                       "break: the same offset twice, present & bit [3294]",
                       "stop:  n == k_store_block or t == task_end [3286]",
                       "the item that broke the run starts the next one"],
                      "model.hpp:3286-3294", body_color=C["muted"]))
    boxes.append(("for (; t < task_end && n < k_store_block; ++t): the collect loop (how a run ends)",
                  "model.hpp:3286-3294 (the loop condition and the three break conditions)"))

    # 6c. worked example: the masks of unit 0 and unit 2
    WY = UY + 182
    o.append(text(32, WY, "Worked example: present after the collect loop (bit t = lane "
                  "t = page offset c * 16 + t)", 10, weight=700))
    u0, u2 = UNITS_EXAMPLE[0], UNITS_EXAMPLE[2]
    rows = [
        (u0, "1" * 16, C["vnni_fill"], C["vnni"],
         "0xFFFF, n = 16: whole block (model-d4b, right)"),
        (u2, "1" * 8 + "0" * 8, C["rm_fill"], C["rm"],
         "0x00FF, n = 8: row by row (model-d4b, left)"),
    ]
    ry = WY + 10
    for u, bits, f, s, what in rows:
        lab = (f"unit {u['u']}: {u['user']}, page {u['page']}, block {u['block']}, "
               f"items {u['begin']}..{u['end'] - 1}")
        _fit(lab, 9.5, 236, False, "worked example label")
        o.append(text(32, ry + 11, lab, 9.5))
        svg, xe = bit_row(272, ry + 2, bits, 9, 1, f, s, group=16)
        o.append(svg)
        _fit(what, 8.5, 676 - (xe + 10), False, "worked example result", bold=True)
        o.append(text(xe + 10, ry + 11, what, 8.5, fill=s, weight=600))
        ry += 24
    o.append(text(32, ry + 8, "one call -> one or more runs: a repeated offset ends a run "
                  "and starts the next (unit 2's items 32..39 are one run)", 9,
                  fill=C["muted"]))
    o.append(cite(676, UY + UH - 6, "model.hpp:3294-3298"))
    boxes.append(("present (worked example: unit 0 and unit 2)",
                  "STYLE.md worked example; model.hpp:3295-3298 (bit = 1 << (j % 16))"))

    cap = ("Updates B5: this opens B5's 'one run (store_k_block)' box. Top: the "
           "function's contract and the layout branch. A row-major slot takes the "
           "per-token page::k(...).set loop that the PR moved out of the marks loop "
           "(the dashed red box is the removed copy), on main alone. Bottom: for a "
           "VNNI slot a run is collected into four locals under the ending rules at "
           "the right. In the worked example unit 0 fills its mask (0xFFFF, 16 rows) "
           "and unit 2 fills 8 lanes (0x00FF). They take the two paths of the second "
           "M4 figure below.")
    legend = [
        ("box", "white box, ink outline: store_k_block, the VNNI slot? decision, the per-token "
                "page::k(...).set loop, the run frame with its locals and its ending rules"),
        ("gone", "red dashed box, red text: before, the same per-token store loop inside the "
                 "marks loop of save_k_impl (removed)"),
        ("vnni", "blue squares, blue text: the set bits of present for unit 0 (0xFFFF, a run "
                 "of 16, the whole-block path)"),
        ("rm", "orange squares, orange text: the set bits of present for unit 2 (0x00FF, a "
               "run of 8, the row-by-row path)"),
        ("bit_clear", "white square: a clear bit of present (unit 2's lanes 8..15)"),
        ("blue arrow: yes, a VNNI slot, down to the run", "arrow", C["vnni"]),
        ("orange arrow: no, a row-major slot, to the per-token page::k(...).set loop",
         "arrow", C["rm"]),
        ("red arrow: moved, the removed loop to its place in store_k_block", "arrow",
         C["gone"]),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions"
        "; grey sans-serif = a note or a secondary label (row labels, index "
        "numbers, the one-line notes under a group)"),
        "font_cite",
        ("font_tag", "bold 'new' = store_k_block is added by PR 4424; 'moved here (new)' = "
                     "the row-major store loop moved out of the marks loop"),
    ]
    return figure(fid, W, H, "store_k_block: the layout branch and how a run is collected",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- D4b: what a run becomes, and where its rows come from -----------------
def fig_b():
    fid = "model-d4b"
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "blk": C["blk"]})]
    boxes = []

    # ---- band: the source row of one (token, KV head) ---------------------
    BY = 12
    o.append(rect(20, BY, 660, 170, C["soft"], C["line"], 1, 6))
    o.append(text(32, BY + 15, "the source row of one (token, KV head)", 10.5, weight=700))
    o.append(cite(676, BY + 15, "model.hpp:3247-3250; 3263-3269"))
    # ks[ix]: the roped K rows (not query data): plain ink
    o.append(rect(32, BY + 26, 78, 50, "#fff", C["ink"], 1.2, 3))
    o.append(text(71, BY + 41, "ks[ix]", 10, "middle", True, weight=700))
    o.append(text(71, BY + 53, "kv_width()", 8.5, "middle", True, fill=C["muted"]))
    o.append(cite(106, BY + 72, "model.hpp:3358"))
    boxes.append(("ks[ix] (one K buffer row)", "model.hpp:3354 (parameter), 3358 "
                  "(kv_width() static_assert)"))
    # ks[ix] -> row_of (gap 110 .. 222: room for the two-line how-many label)
    o.append(arrow(fid, "ink", [(110, BY + 50), (220, BY + 50)], C["ink"], 1.4))
    _fit("of head_size values", 9, 104, False, "ks arrow label", bold=True)
    o.append(text(166, BY + 44, "n_kv_heads rows", 9, "middle", fill=C["ink"], weight=700))
    o.append(text(166, BY + 64, "of head_size values", 9, "middle", fill=C["ink"],
                  weight=700))
    # row_of
    o.append(note_box(222, BY + 30, 136, 40, "row_of(ix, kv_head)",
                      ["slice<head_size>(ks[ix])"], "model.hpp:3247-3250",
                      title_size=9.5))
    boxes.append(("row_of", "model.hpp:3247-3250 (lambda in store_k_block, no comment)"))
    o.append(arrow(fid, "ink", [(358, BY + 50), (390, BY + 50)], C["ink"], 1.4))
    o.append(text(374, BY + 44, "1 row", 9, "middle", fill=C["ink"], weight=700))
    # rows_are_bf16?
    o.append(decision_box(392, BY + 22, 110, 56, "rows_are_bf16?",
                          ["kv_elem_t == bf16"], "model.hpp:3263-3265"))
    boxes.append(("rows_are_bf16? (kv_elem_t)", "model.hpp:3263-3265"))
    # yes: k_source_row in place
    o.append(arrow(fid, "ink", [(502, BY + 44), (524, BY + 44)], C["ink"], 1.3))
    o.append(text(513, BY + 38, "yes", 9, "middle", fill=C["ink"], weight=700))
    o.append(note_box(526, BY + 22, 150, 62, "k_source_row(kout)",
                      ["read in place: the row", "view keeps the K", "buffer's flags"],
                      "model.hpp:3309-3311"))
    boxes.append(("k_source_row(kout) (bf16 K buffer, read in place)",
                  "model.hpp:3309-3311, 3330; tensor/k_vnni.hpp:271-280 (the "
                  "view overload keeps the buffer's alignment and DMA flags)"))
    # no: conv on the stack
    o.append(arrow(fid, "ink", [(447, BY + 78), (447, BY + 126), (524, BY + 126)],
                   C["ink"], 1.3))
    o.append(text(454, BY + 119, "no", 9, fill=C["ink"], weight=700))
    o.append(note_box(526, BY + 90, 150, 72, "conv",
                      ["bf16 conv[k_store_block]", "[geometry.kv.head_size]:",
                       "4 KiB, 64-byte aligned;", "view{conv[i]}.set(kout)"],
                      "model.hpp:3266-3269"))
    boxes.append(("conv[k_store_block][geometry.kv.head_size] (bf16 conversion on the stack)",
                  "model.hpp:3266-3269 (alignas(64) bf16 conv[k_store_block]"
                  "[head_size]); converted at 3312-3317 (conv[0], row by row) and "
                  "3331-3335 (conv[i], whole block)"))
    o.append(text(32, BY + 136, "row by row: row = k_source_row(kout), or "
                  "k_source_row<head_size>(conv[0])", 9, fill=C["muted"]))
    o.append(text(32, BY + 148, "whole block: rows[run_t[i]] = kout.data, or conv[i]", 9,
                  fill=C["muted"]))

    # ---- the decision: a shorter run or a run of 16 -------------------------
    T = 204                      # the decision's top; everything below is relative
    o.append(decision_box(255, T, 190, 50, "n < k_store_block?",
                          ["a run shorter than 16?"], "model.hpp:3300"))
    boxes.append(("n < k_store_block? (a shorter run)", "model.hpp:3300; 3321"))
    o.append(arrow(fid, "ink", [(255, T + 25), (175, T + 25), (175, T + 72)], C["ink"], 1.3))
    o.append(text(247, T + 19, "yes", 9, "end", fill=C["ink"], weight=700))
    o.append(text(183, T + 64, "n x n_kv_heads calls", 9, fill=C["ink"], weight=700))
    o.append(arrow(fid, "vnni", [(445, T + 25), (525, T + 25), (525, T + 72)], C["vnni"], 1.4))
    o.append(text(453, T + 19, "no", 9, fill=C["vnni"], weight=700))
    o.append(text(517, T + 64, "n == 16", 9, "end", fill=C["vnni"], weight=700))

    # ---- left column: a shorter run, row by row ------------------------------
    LX, LW = 20, 310
    L0 = T + 74
    o.append(note_box(LX, L0, LW, 56, "set_k_row(slot, kv_head, j, row)",
                      ["per token i < n and KV head; j = c * 16 + run_t[i]",
                       "n x n_kv_heads calls  [any thread of the window]"],
                      "model.hpp:3304-3320"))
    boxes.append(("set_k_row per token and KV head",
                  "model.hpp:3304-3320; kv_cache.hpp:2238-2262"))
    o.append(arrow(fid, "ink", [(175, L0 + 56), (175, L0 + 68)], C["ink"], 1.3))
    o.append(decision_box(80, L0 + 70, 190, 50, "k_block_is_vnni?",
                          ["set_k_row reads the block bit"], "kv_cache.hpp:2252-2258"))
    boxes.append(("k_block_is_vnni? (set_k_row decides)",
                  "kv_cache.hpp:2252-2258 (k_block_is_vnni); model.hpp:3301-3303"))
    o.append(arrow(fid, "rm", [(120, L0 + 120), (120, L0 + 148)], C["rm"], 1.4))
    o.append(text(127, L0 + 138, "no", 9, fill=C["rm"], weight=700))
    o.append(arrow(fid, "vnni", [(230, L0 + 120), (230, L0 + 148)], C["vnni"], 1.4))
    o.append(text(237, L0 + 138, "yes", 9, fill=C["vnni"], weight=700))
    o.append(block_state_box(20, L0 + 150, 150, 62, "rm", "row-major rows",
                             ["store_row_major: 4 whole", "lines, the token's 256 bytes"],
                             "tensor/k_vnni.hpp:474-482"))
    boxes.append(("row-major rows (store_row_major)",
                  "tensor/k_vnni.hpp:474-482; Note [Row-major tail block] 437-456"))
    o.append(block_state_box(180, L0 + 150, 150, 62, "vnni", "a row saved again",
                             ["store_row into the VNNI", "column (4 scatters)"],
                             "tensor/k_vnni.hpp:344-362"))
    boxes.append(("a row saved again (store_row into the VNNI column)",
                  "tensor/k_vnni.hpp:344-362; kv_cache.hpp:2254-2255"))
    o.append(note_box(LX, L0 + 228, LW, 56, "The row's saved bit is the caller's",
                      ["main sets it after the join with note_k_row_saved",
                       "(M6); a run of 16 sets its bits at once (right)"],
                      "kv_cache.hpp:2242-2243; model.hpp:3237-3239"))
    boxes.append(("The row's saved bit is the caller's (note_k_row_saved on main, after "
                  "the join)", "kv_cache.hpp:2242-2243; model.hpp:3237-3239; 3420-3439"))

    # ---- right column: a run of 16, the whole block --------------------------
    RX, RW = 370, 310
    R0 = T + 74
    o.append(note_box(RX, R0, RW, 44, "TRON_ASSERT(present == FULL_BLOCK_0XFFFF)",
                      ["a run of 16 tokens must cover its block"],
                      "model.hpp:3323-3324"))
    boxes.append(("TRON_ASSERT(present == k_vnni::FULL_BLOCK_0XFFFF)",
                  "model.hpp:3323-3324; tensor/k_vnni.hpp:83-84"))
    o.append(arrow(fid, "vnni", [(525, R0 + 44), (525, R0 + 56)], C["vnni"], 1.4))
    R1 = R0 + 58
    o.append(note_box(RX, R1, RW, 56, "rows[k_store_block] = {}",
                      ["const bf16*: rows[run_t[i]] = the row of offset",
                       "c * 16 + run_t[i] (kout.data, or conv[i])"],
                      "model.hpp:3326-3337"))
    boxes.append(("rows (the 16-pointer table of set_k_block)",
                  "model.hpp:3326-3337; kv_cache.hpp:2265-2272"))
    o.append(arrow(fid, "vnni", [(525, R1 + 56), (525, R1 + 68)], C["vnni"], 1.4))
    o.append(text(533, R1 + 65, "16 pointers per KV head", 9, fill=C["vnni"], weight=700))
    R2 = R1 + 70
    o.append(note_box(RX, R2, RW, 56, "set_k_block(slot, kv_head, c, rows)",
                      ["per KV head: store_block writes the 16 rows at once",
                       "(FULL_BLOCK_0XFFFF); n_kv_heads calls"],
                      "model.hpp:3338; kv_cache.hpp:2277-2283",
                      fill=C["vnni_fill"], stroke=C["vnni"]))
    boxes.append(("set_k_block per KV head",
                  "model.hpp:3325-3338; kv_cache.hpp:2265-2284; tensor/k_vnni.hpp:382-399 "
                  "(store_block)"))
    o.append(arrow(fid, "vnni", [(525, R2 + 56), (525, R2 + 68)], C["vnni"], 1.4))
    o.append(text(517, R2 + 65, "1 call after the last KV head", 9, "end", fill=C["vnni"],
                  weight=700))
    # note_k_block_saved: two coloured lines (the two bit sets)
    NY, NH = R2 + 70, 72
    o.append(rect(RX, NY, RW, NH, "#fff", C["ink"], 1.2, 4))
    o.append(text(RX + 8, NY + 14, "note_k_block_saved(slot, c)", 10, mono=True, weight=700))
    o.append(text(RX + 8, NY + 27, "k_rows_saved_ |= the 16 row bits: fetch_or, acq_rel", 9,
                  fill=C["rows"], weight=600))
    o.append(text(RX + 8, NY + 38, "k_vnni_blocks_ |= the block bit: fetch_or, release", 9,
                  fill=C["blk"], weight=600))
    o.append(text(RX + 8, NY + 49, "[any thread of the window]; the block is VNNI at once", 9,
                  fill=C["muted"]))
    o.append(cite(RX + RW - 4, NY + NH - 4, "model.hpp:3340; kv_cache.hpp:2195-2200"))
    boxes.append(("note_k_block_saved (the 16 row bits and the block bit)",
                  "model.hpp:3340; kv_cache.hpp:2192-2200 (fetch_or acq_rel on "
                  "k_rows_saved_, fetch_or release on k_vnni_blocks_)"))
    o.append(arrow(fid, "vnni", [(525, NY + NH), (525, NY + NH + 12)], C["vnni"], 1.4))
    R4 = NY + NH + 14
    o.append(block_state_box(RX, R4, RW, 62, "vnni", "one VNNI block (set_k_block)",
                             ["never queued: note_k_row_saved", "returns false for it later"],
                             "kv_cache.hpp:2265-2266; 2192-2200; 2163"))
    boxes.append(("one VNNI block (set_k_block): the whole-block save (never queued)",
                  "model.hpp:3234-3235 ('stored as one VNNI block (set_k_block)'); "
                  "kv_cache.hpp:2265-2266 ('stored at once in the VNNI layout'); 2192-2200 "
                  "(the bits); 2163 (a row of a converted block returns false)"))

    # ---- worked example ------------------------------------------------------
    WY = R4 + 62 + 22
    o.append(text(20, WY, "Worked example: unit 0 (page 7, block 0, 16 rows) -> "
                  "n_kv_heads set_k_block calls, then one note_k_block_saved call (right);",
                  9.5))
    o.append(text(20, WY + 14, "unit 2 (page 9, block 2, 8 rows) -> 8 x n_kv_heads "
                  "set_k_row calls into row-major rows, the block bit being clear (left).",
                  9.5))
    H = WY + 24
    boxes.append(("set_k_row x n, set_k_block x n_kv_heads (worked example: unit 0 and unit 2)",
                  "STYLE.md worked example; model.hpp:3304-3311 (set_k_row); model.hpp:3325-3340 (set_k_block)"))

    cap = ("Updates B5: this opens B5's two store boxes with their call counts. A run "
           "shorter than 16 makes n x n_kv_heads set_k_row calls. set_k_row picks the "
           "row-major row or the VNNI column from the block bit. A run of 16 passes the "
           "assert, fills the 16-pointer table and makes n_kv_heads set_k_block calls. "
           "Then one note_k_block_saved call publishes the 16 row bits (fetch_or, "
           "acq_rel) and the block bit (fetch_or, release), from whichever thread "
           "claimed the unit. The band at the top is where every stored row comes from: "
           "the K buffer row in place when it is bf16, the 4 KiB stack buffer conv "
           "otherwise.")
    legend = [
        ("box", "white box, ink outline: the source-row steps (ks[ix], row_of, k_source_row, "
                "conv), with rounded corners the three decisions (rows_are_bf16?, "
                "n < k_store_block?, k_block_is_vnni?), set_k_row, the assert, the rows "
                "table, note_k_block_saved and the saved-bit note"),
        ("ctx", "grey band, light grey outline: the source-row band: how the row of one "
                "(token, KV head) reaches the store (ks[ix] -> row_of -> rows_are_bf16? -> "
                "k_source_row or conv)"),
        ("rm", "orange box, orange text: row-major rows, where set_k_row stores when the "
               "block bit is clear (store_row_major)"),
        ("vnni", "blue box, blue text: the VNNI side: a row saved again (store_row), "
                 "set_k_block and the one VNNI block it stores; the run-of-16 labels"),
        ("ink arrow: a step of the source-row band, or of the shorter run (yes, set_k_row, "
         "k_block_is_vnni?); its label says how many", "arrow", C["ink"]),
        ("blue arrow: a run of 16 (n == 16), the whole-block path down the right column, "
         "and yes from k_block_is_vnni? to a row saved again", "arrow", C["vnni"]),
        ("orange arrow: no, the block bit is clear, set_k_row to row-major rows",
         "arrow", C["rm"]),
        ("green text: k_rows_saved_ |= the 16 row bits (fetch_or, acq_rel) in "
         "note_k_block_saved", "text", C["rows"]),
        ("pink text: k_vnni_blocks_ |= the block bit (fetch_or, release) in "
         "note_k_block_saved", "text", C["blk"]),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions"
        "; grey sans-serif = a note or a secondary label (row labels, index "
        "numbers, the one-line notes under a group)"),
        "font_cite",
    ]
    return figure(fid, W, H, "store_k_block: what a run becomes and where its rows come from",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
