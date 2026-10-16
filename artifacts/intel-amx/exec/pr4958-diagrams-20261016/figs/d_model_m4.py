"""Change diagrams of unit m4 (model.hpp, PR 4958): store_k_block, the run store
(head lines 3193-3293).

Two figures:
  d4a = the function's contract, the layout branch (the row-major branch is
        the per-token loop moved out of the marks loop) and how a run of a
        VNNI slot is collected and ended (the four locals, the ending rules,
        the worked example's present masks).
  d4b = what a run becomes (set_k_row per KV head for a run of one token, or
        the 16-pointer table and set_k_block per KV head with the present mask,
        then store_block's full-line or masked stores) and where every stored
        row comes from (row_of; k_source_row in place for a bf16 K buffer, conv
        on the stack otherwise).

Every label is an identifier or a comment phrase of h/tron/models/model.hpp
(head line numbers of b39765ec29), h/tron/models/kv_cache.hpp or
h/tron/tensor/k_vnni.hpp of the same head.
"""
from svg_helpers import (C, arrow, bit_row, cite, figure, fn_cell, lines,
                         marker_defs, rect, text, text_width)
from base_model import UNITS_EXAMPLE, decision_box, run_box

BASE = ("Updates B5. The two figures open B5's 'one run (store_k_block)' box and its "
        "two store arrows. They add how a run is collected and ended, the row-major "
        "branch moved out of the marks loop, the call counts of set_k_row and "
        "set_k_block, the present mask and the two store patterns of store_block, "
        "and the bf16 source-row path (k_source_row in place, or conv on the stack).")

W = 700


def _w(s, size, mono=False, bold=False):
    return text_width(s, size, mono) * (1.08 if bold else 1.0)


def _fit(s, size, avail, mono, where, bold=False):
    w = _w(s, size, mono, bold)
    if w > avail:
        raise ValueError(f"{where}: '{s}' needs {w:.0f} px, has {avail:.0f} px")


def note_box(x, y, w, h, title, body, ref, stroke=C["ink"], fill="#fff",
             dash=None, tag=None, tag_color=None, title_color=None,
             body_color=None, title_size=10, body_size=9):
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
    H = 566
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "gone": C["gone"]})]
    boxes = []

    o.append(fn_cell(20, 12, 660, 76,
                     "store_k_block(q_batch, slot, ks, task_begin, task_end)",
                     ["Store the K rows (every KV head) of items[task_begin, task_end) "
                      "into slot  [any thread of the window]",
                      "Marks and credits are not touched here: save_k_impl does them "
                      "after every store is done.",
                      "Called per claimed unit u (shared) or once for items[0, n_items) "
                      "(unshared)."],
                     "model.hpp:3193-3205", tag="new"))
    boxes.append(("store_k_block", "model.hpp:3193-3293 (comment 3193-3199, signature "
                  "3200-3205); callers 3344-3345 (per unit), 3367 (unshared)"))

    o.append(decision_box(20, 106, 190, 58, "VNNI slot?",
                          ["k_vnni::layout_on<", "geometry.kv.head_size>"],
                          "model.hpp:3211"))
    boxes.append(("VNNI slot? (k_vnni::layout_on)",
                  "model.hpp:3211; tensor/k_vnni.hpp:94-103"))

    RX, RW = 250, 430
    o.append(note_box(RX, 106, RW, 58,
                      "page::k(slot, kv_head, j).set  per token",
                      ["one row store per (KV item, KV head), the K buffer row in place; "
                       "[main] alone:",
                       "k_store_shared is false for a row-major slot, so the store is "
                       "never shared"],
                      "model.hpp:3212-3221; 3154-3156", tag="moved here (new)"))
    boxes.append(("page::k(slot, kv_head, j).set (row-major slots)",
                  "model.hpp:3212-3221; k_store_shared false at 3154-3156; "
                  "kv_cache.hpp:2015-2029"))
    o.append(arrow(fid, "rm", [(210, 135), (248, 135)], C["rm"], 1.4))
    o.append(text(229, 129, "no", 9, "middle", fill=C["rm"], weight=700))

    o.append(note_box(RX, 184, RW, 58,
                      "before: the same loop inside the marks loop of save_k_impl",
                      ["// Update the page first so HW sees the latest K values.",
                       "for (kv_head ...) set_k_row (VNNI) or pg.k<...>(...).set(kout) -> removed"],
                      "base model.hpp:3096-3116 (removed before head 3376)",
                      stroke=C["gone"], dash="5 3", title_color=C["gone"],
                      body_color=C["gone"]))
    boxes.append(("page::k(...).set and set_k_row per KV head [before: the per-token K store inside the marks loop, removed]",
                  "model.hpp:3207-3221 (the same store at head, row-major slots); base "
                  "model.hpp:3096-3116, the 23 lines removed before head 3376 (unit M6)"))
    o.append(arrow(fid, "gone", [(465, 184), (465, 166)], C["gone"], 1.4))
    o.append(text(473, 178, "moved", 9, fill=C["gone"], weight=700))

    o.append(arrow(fid, "vnni", [(115, 164), (115, 258)], C["vnni"], 1.4))
    o.append(text(123, 215, "yes", 9, fill=C["vnni"], weight=700))

    UY, UH = 260, 294
    o.append(rect(20, UY, 660, UH, "#fff", C["ink"], 1.2, 6))
    o.append(text(32, UY + 16, "The run: consecutive items in block c of this page",
                  11, mono=True, weight=700))
    o.append(cite(676, UY + 16, "model.hpp:3240-3241; 3231-3259"))
    boxes.append(("The run: consecutive items in block c of this page (store_k_block, "
                  "VNNI slot)", "model.hpp:3240-3241 (the comment); 3231-3259 (the loop)"))
    o.append(text(32, UY + 30, "while (t < task_end): the collect loop (3246-3259), then "
                  "set_k_row x n or set_k_block (3260-3289)", 9, fill=C["muted"]))
    o.append(text(32, UY + 41, "tokens without KV work in between are skipped and do not "
                  "end the run", 9, fill=C["muted"]))

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
    o.append(cite(LX + LW - 4, LY + 78, "model.hpp:3242-3245"))
    boxes.append(("run_ix, run_t, present, n (locals of one run)",
                  "model.hpp:3242-3245; filled at 3255-3258"))
    card = "1 run -> n rows of block c, n = 1 .. 16"
    _fit(card, 9, LW - _w("model.hpp:3246", 8.5, True) - 10, False, "run card", bold=True)
    o.append(text(LX, LY + 98, card, 9, fill=C["ink"], weight=700))
    o.append(cite(LX + LW, LY + 98, "model.hpp:3246"))

    EX, EW, EY = 344, 324, UY + 52
    o.append(note_box(EX, EY, EW, 104, "for (; t < task_end && n < k_store_block; ++t)",
                      ["how a run ends:",
                       "skip:  !token_jobs_do_kv[ix], the run goes on [3248]",
                       "break: another page, &page_of(tok_ix) != &pg [3250]",
                       "break: another block, j / k_store_block != c [3252]",
                       "break: the same offset twice, present & bit [3254]",
                       "stop:  n == k_store_block or t == task_end [3246]",
                       "the item that broke the run starts the next one"],
                      "model.hpp:3246-3254", body_color=C["muted"]))
    boxes.append(("for (; t < task_end && n < k_store_block; ++t): the collect loop (how a run ends)",
                  "model.hpp:3246-3254 (the loop condition and the three break conditions)"))

    WY = UY + 182
    o.append(text(32, WY, "Worked example: present after the collect loop (bit t = lane "
                  "t = page offset c * 16 + t)", 10, weight=700))
    u0, u2 = UNITS_EXAMPLE[0], UNITS_EXAMPLE[2]
    rows = [
        (f"unit {u0['u']}: page {u0['page']}, block {u0['block']}, items "
         f"{u0['begin']}..{u0['end'] - 1}", "1" * 16,
         "0xffff, n = 16: a whole block (d4b, right)"),
        (f"unit {u2['u']}: page {u2['page']}, block {u2['block']}, items "
         f"{u2['begin']}..{u2['end'] - 1}", "1" * 9 + "0" * 7,
         "0x01ff, n = 9: a partial block (d4b, right)"),
        ("a decode step: page 7, block 2, offset 41", "0" * 9 + "1" + "0" * 6,
         "0x0200, n = 1: set_k_row (d4b, left)"),
    ]
    ry = WY + 10
    for lab, bits, what in rows:
        _fit(lab, 9.5, 236, False, "worked example label")
        o.append(text(32, ry + 11, lab, 9.5))
        svg, xe = bit_row(272, ry + 2, bits, 9, 1, C["rows_fill"], C["rows"], group=16)
        o.append(svg)
        _fit(what, 8.5, 676 - (xe + 10), False, "worked example result", bold=True)
        o.append(text(xe + 10, ry + 11, what, 8.5, fill=C["rows"], weight=600))
        ry += 24
    o.append(text(32, ry + 8, "one call -> one or more runs: a repeated offset ends a run "
                  "and starts the next (unit 2's items 32..40 are one run)", 9,
                  fill=C["muted"]))
    o.append(cite(676, UY + UH - 6, "model.hpp:3253-3258"))
    boxes.append(("present (worked example: unit 0, unit 2, a decode step)",
                  "STYLE.md worked example; model.hpp:3253-3258 (bit = 1 << (j % 16))"))

    cap = ("Updates B5: this opens B5's 'one run (store_k_block)' box. Top: the "
           "function's contract and the layout branch. A row-major slot takes the "
           "per-token page::k(...).set loop that the PR moved out of the marks loop "
           "(the dashed red box is the removed copy), on main alone. Bottom: for a "
           "VNNI slot a run is collected into four locals under the ending rules at "
           "the right. In the worked example unit 0 fills its mask (0xffff, 16 rows), "
           "unit 2 fills 9 lanes (0x01ff), and a decode step fills one lane (n = 1). "
           "They take the paths of the second M4 figure below.")
    legend = [
        ("box", "white box, ink outline: store_k_block, the VNNI slot? decision, the per-token "
                "page::k(...).set loop, the run frame with its locals and its ending rules"),
        ("gone", "red dashed box, red text: before, the same per-token store loop inside the "
                 "marks loop of save_k_impl (removed)"),
        ("present", "green squares, green text: the set bits of present after the collect "
                    "loop (unit 0: 0xffff; unit 2: 0x01ff; a decode step: one lane)"),
        ("bit_clear", "white square: a clear bit of present (unit 2's lanes 9..15, the "
                      "decode step's other 15 lanes)"),
        ("blue arrow: yes, a VNNI slot, down to the run", "arrow", C["vnni"]),
        ("orange arrow: no, a row-major slot, to the per-token page::k(...).set loop",
         "arrow", C["rm"]),
        ("red arrow: moved, the removed loop to its place in store_k_block", "arrow",
         C["gone"]),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions; grey "
                      "sans-serif = a note"),
        "font_cite",
        ("font_tag", "bold 'new' = store_k_block is added by PR 4958; 'moved here (new)' = "
                     "the row-major store loop moved out of the marks loop"),
    ]
    return figure(fid, W, H, "store_k_block: the layout branch and how a run is collected",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- D4b: what a run becomes, and where its rows come from -----------------
def fig_b():
    fid = "model-d4b"
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    boxes = []

    BY = 12
    o.append(rect(20, BY, 660, 170, C["soft"], C["line"], 1, 6))
    o.append(text(32, BY + 15, "the source row of one (token, KV head)", 10.5, weight=700))
    o.append(cite(676, BY + 15, "model.hpp:3207-3210; 3223-3229"))
    o.append(rect(32, BY + 26, 78, 50, C["rm_fill"], C["rm"], 1.2, 3))
    o.append(text(71, BY + 41, "ks[ix]", 10, "middle", True, weight=700))
    o.append(text(71, BY + 53, "kv_width()", 8.5, "middle", True, fill=C["muted"]))
    o.append(cite(106, BY + 72, "model.hpp:3307"))
    boxes.append(("ks[ix] (one K buffer row)", "model.hpp:3303 (parameter), 3307 "
                  "(kv_width() static_assert)"))
    o.append(arrow(fid, "ink", [(110, BY + 50), (220, BY + 50)], C["ink"], 1.4))
    o.append(text(166, BY + 44, "n_kv_heads rows", 9, "middle", fill=C["ink"], weight=700))
    o.append(text(166, BY + 64, "of head_size values", 9, "middle", fill=C["ink"],
                  weight=700))
    o.append(note_box(222, BY + 30, 136, 40, "row_of(ix, kv_head)",
                      ["slice<head_size>(ks[ix])"], "model.hpp:3207-3210",
                      title_size=9.5))
    boxes.append(("row_of", "model.hpp:3207-3210 (lambda in store_k_block, no comment)"))
    o.append(arrow(fid, "ink", [(358, BY + 50), (390, BY + 50)], C["ink"], 1.4))
    o.append(text(374, BY + 44, "1 row", 9, "middle", fill=C["ink"], weight=700))
    o.append(decision_box(392, BY + 22, 110, 56, "rows_are_bf16?",
                          ["kv_elem_t == bf16"], "model.hpp:3223-3225"))
    boxes.append(("rows_are_bf16? (kv_elem_t)", "model.hpp:3223-3225"))
    o.append(arrow(fid, "ink", [(502, BY + 44), (524, BY + 44)], C["ink"], 1.3))
    o.append(text(513, BY + 38, "yes", 9, "middle", fill=C["ink"], weight=700))
    o.append(note_box(526, BY + 22, 150, 62, "in place",
                      ["set_k_row: k_source_row", "(kout) keeps the flags;",
                       "set_k_block: rows[t]=data"],
                      "model.hpp:3265-3268, 3282"))
    boxes.append(("k_source_row(kout) / rows[run_t[i]] = kout.data (bf16 K buffer, read in place)",
                  "model.hpp:3265-3268 (the row view keeps the K buffer's alignment and "
                  "DMA flags), 3281-3282; tensor/k_vnni.hpp:205-225"))
    o.append(arrow(fid, "ink", [(447, BY + 78), (447, BY + 126), (524, BY + 126)],
                   C["ink"], 1.3))
    o.append(text(454, BY + 119, "no", 9, fill=C["ink"], weight=700))
    o.append(note_box(526, BY + 90, 150, 72, "conv",
                      ["bf16 conv[k_store_block]", "[geometry.kv.head_size]:",
                       "4 KiB, 64-byte aligned;", "view{conv[i]}.set(kout)"],
                      "model.hpp:3226-3229"))
    boxes.append(("conv[k_store_block][geometry.kv.head_size] (bf16 conversion on the stack)",
                  "model.hpp:3226-3229 (alignas(64) bf16 conv[k_store_block]"
                  "[head_size]); converted at 3269-3272 (conv[0], one token) and "
                  "3283-3285 (conv[i], a block)"))
    o.append(text(32, BY + 136, "one token: row = k_source_row(kout), or "
                  "k_source_row<head_size>(conv[0])", 9, fill=C["muted"]))
    o.append(text(32, BY + 148, "a block: rows[run_t[i]] = kout.data, or conv[i]", 9,
                  fill=C["muted"]))

    T = 204
    o.append(decision_box(255, T, 190, 50, "n == k_scatter_run_len?",
                          ["a run of one token?"], "model.hpp:3260"))
    boxes.append(("n == k_scatter_run_len? (a run of one token)", "model.hpp:3260; 3141"))
    o.append(arrow(fid, "ink", [(255, T + 25), (175, T + 25), (175, T + 72)], C["ink"], 1.3))
    o.append(text(247, T + 19, "yes", 9, "end", fill=C["ink"], weight=700))
    o.append(text(183, T + 64, "n_kv_heads calls", 9, fill=C["ink"], weight=700))
    o.append(arrow(fid, "vnni", [(445, T + 25), (525, T + 25), (525, T + 72)], C["vnni"], 1.4))
    o.append(text(453, T + 19, "no", 9, fill=C["vnni"], weight=700))
    o.append(text(517, T + 64, "n = 2 .. 16", 9, "end", fill=C["vnni"], weight=700))

    LX, LW = 20, 310
    L0 = T + 74
    o.append(note_box(LX, L0, LW, 56, "set_k_row(slot, kv_head, j, row)",
                      ["per KV head; j = c * 16 + run_t[0]",
                       "n_kv_heads calls  [any thread of the window]"],
                      "model.hpp:3261-3275"))
    boxes.append(("set_k_row per KV head",
                  "model.hpp:3261-3275; kv_cache.hpp:2061-2076"))
    o.append(arrow(fid, "ink", [(175, L0 + 56), (175, L0 + 68)], C["ink"], 1.3))
    o.append(note_box(LX, L0 + 70, LW, 56, "store_row(plane, i_page, row)",
                      ["the owner's writable view; only this token's",
                       "64 pair slots are written (4 scatters)"],
                      "kv_cache.hpp:2070-2076; tensor/k_vnni.hpp:295"))
    boxes.append(("store_row(plane, i_page, row)",
                  "kv_cache.hpp:2070-2076 (set_k_row calls store_row on k.as_view()); "
                  "tensor/k_vnni.hpp:290-310"))
    o.append(arrow(fid, "ink", [(175, L0 + 126), (175, L0 + 138)], C["ink"], 1.3))
    o.append(run_box(20, L0 + 140, 310, 62, "row", "one token: the scatter",
                     ["4 scatters write 4 bytes into each of the",
                      "token's 64 lines; other tokens untouched"],
                     "tensor/k_vnni.hpp:290-310"))
    boxes.append(("one token: the scatter (store_row)",
                  "tensor/k_vnni.hpp:290-310; kv_cache.hpp:715-719 (Note item 1)"))
    o.append(note_box(LX, L0 + 218, LW, 56, "Other threads may store other tokens",
                      ["of the same plane at the same time: a token's",
                       "store touches its own pair slots only"],
                      "tensor/k_vnni.hpp:290-292"))
    boxes.append(("several threads may store different tokens of one plane at the same "
                  "time", "tensor/k_vnni.hpp:290-292 (the comment of store_row)"))

    RX, RW = 370, 310
    R0 = T + 74
    o.append(note_box(RX, R0, RW, 56, "rows[k_store_block] = {}",
                      ["const bf16*: rows[run_t[i]] = the row of offset",
                       "c * 16 + run_t[i] (kout.data, or conv[i]); absent: null"],
                      "model.hpp:3278-3287"))
    boxes.append(("rows (the 16-pointer table of set_k_block)",
                  "model.hpp:3278-3287; kv_cache.hpp:2084-2094"))
    o.append(arrow(fid, "vnni", [(525, R0 + 56), (525, R0 + 68)], C["vnni"], 1.4))
    o.append(text(533, R0 + 65, "16 pointers per KV head", 9, fill=C["vnni"], weight=700))
    R1 = R0 + 70
    o.append(note_box(RX, R1, RW, 56, "set_k_block(slot, kv_head, c, present, rows)",
                      ["per KV head: store_block on the owner's writable",
                       "view; n_kv_heads calls  [any thread of the window]"],
                      "model.hpp:3288; kv_cache.hpp:2089-2096",
                      fill=C["vnni_fill"], stroke=C["vnni"]))
    boxes.append(("set_k_block per KV head",
                  "model.hpp:3277-3288; kv_cache.hpp:2078-2096"))
    o.append(arrow(fid, "vnni", [(525, R1 + 56), (525, R1 + 68)], C["vnni"], 1.4))
    R2 = R1 + 70
    o.append(note_box(RX, R2, RW, 68, "store_block(dst, c, present, rows)",
                      ["per dimension step s: one 64-byte load per present",
                       "row (zero for an absent one), transpose_16x16_epi32,",
                       "then 16 line stores into panel (s, c)"],
                      "tensor/k_vnni.hpp:342-357", fill=C["vnni_fill"], stroke=C["vnni"]))
    boxes.append(("store_block(dst, c, present, rows)",
                  "tensor/k_vnni.hpp:326-368 (comment 326-340, signature 342-345, the "
                  "step loop 347-367)"))
    o.append(arrow(fid, "vnni", [(445, R2 + 68), (445, R2 + 80)], C["vnni"], 1.4))
    o.append(text(453, R2 + 78, "0xffff", 9, fill=C["vnni"], weight=700))
    o.append(arrow(fid, "vnni", [(605, R2 + 68), (605, R2 + 80)], C["vnni"], 1.4))
    o.append(text(613, R2 + 78, "else", 9, fill=C["vnni"], weight=700))
    R3 = R2 + 82
    o.append(run_box(RX, R3, 150, 62, "full", "a whole block",
                     ["_mm512_storeu_si512 x 16", "per panel: 64 full lines"],
                     "k_vnni.hpp:358-360"))
    boxes.append(("a whole block (store_block, 64 full-line stores)",
                  "tensor/k_vnni.hpp:358-360"))
    o.append(run_box(RX + 160, R3, 150, 62, "part", "a partial block",
                     ["_mm512_mask_storeu_epi32 x 16", "per panel, masked to present"],
                     "k_vnni.hpp:361-364"))
    boxes.append(("a partial block (store_block, 64 masked line stores)",
                  "tensor/k_vnni.hpp:361-364, 326-331"))

    WY = R3 + 62 + 22
    o.append(text(20, WY, "Worked example: unit 0 (page 7, block 0, 16 rows) -> "
                  "n_kv_heads set_k_block calls with present 0xffff (whole lines);", 9.5))
    o.append(text(20, WY + 14, "unit 2 (page 7, block 2, 9 rows) -> n_kv_heads set_k_block "
                  "calls with present 0x01ff (masked lines);", 9.5))
    o.append(text(20, WY + 28, "a decode token (one row) -> n_kv_heads set_k_row calls, the "
                  "scatter.", 9.5))
    H = WY + 38
    boxes.append(("set_k_row x n_kv_heads, set_k_block x n_kv_heads (worked example: a decode token, unit 0 and unit 2)",
                  "STYLE.md worked example; model.hpp:3261-3275 (set_k_row); model.hpp:3277-3288 (set_k_block)"))

    cap = ("Updates B5: this opens B5's two store boxes with their call counts. A run "
           "of one token makes n_kv_heads set_k_row calls, each a store_row scatter of "
           "4 bytes into each of the token's 64 lines. A run of 2 to 16 tokens fills the "
           "16-pointer table and makes n_kv_heads set_k_block calls, each a store_block "
           "that transposes the present rows in registers and writes whole lines (present "
           "0xffff) or masked lines (any other mask), from whichever thread claimed the "
           "unit. The band at the top is where every stored row comes from: the K buffer "
           "row in place when it is bf16, the 4 KiB stack buffer conv otherwise.")
    legend = [
        ("box", "white box, ink outline: the source-row steps (row_of, in place, conv), "
                "with rounded corners the two decisions (rows_are_bf16?, n == "
                "k_scatter_run_len?), set_k_row, store_row, the rows table and the note "
                "on concurrent stores"),
        ("ctx", "grey band, light grey outline: the source-row band: how the row of one "
                "(token, KV head) reaches the store (ks[ix] -> row_of -> rows_are_bf16? -> "
                "in place or conv)"),
        ("rm", "orange: ks[ix], the K buffer row of one token (one native row per KV head, "
               "in dimension order)"),
        ("blue boxes and arrows: the block path: set_k_block and store_block (blue fill), "
         "a whole block (solid blue) and a partial block (blue, dashed outline); the "
         "white box with a blue outline = one token: the scatter; blue text = the "
         "run-of-2..16 labels and the two store patterns", "multi",
         ["vnni", ("#fff", C["vnni"], False, False), (C["vnni_fill"], C["vnni"], True, False),
          ("arrow", C["vnni"])]),
        ("ink arrow: a step of the source-row band, or of the one-token path (yes, "
         "set_k_row, store_row); its label says how many", "arrow", C["ink"]),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions; grey "
                      "sans-serif = a note"),
        "font_cite",
    ]
    return figure(fid, W, H, "store_k_block: what a run becomes and where its rows come from",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
