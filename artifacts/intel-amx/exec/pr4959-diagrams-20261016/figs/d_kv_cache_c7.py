"""Change diagram D7 of the PR 4959 page for h/tron/models/kv_cache.hpp:
unit c7, "set_k_block stores whole blocks only: the present mask is removed"
(head lines 2309-2328, changed).

Every label and citation comes from the head files (kv_cache.hpp at
6b081187e1; the removed parameter from the base b39765ec29). Line numbers are
head line numbers of kv_cache.hpp unless another file is named.
"""
from svg_helpers import (C, arrow, bit_row, block_cell, card_arrow, cite,
                         figure, fn_cell, lines, marker_defs, rect, text)
from base_kv_cache import caller_cell, fit, state_box

BASE = ("Updates B3 row 2 and B4: the set_k_block cell of the function model loses "
        "its present mask (a run of 2..15 tokens no longer takes a masked block save; "
        "it goes row by row into the row-major tail block), so the arc over the top "
        "of B4 is the only block save left: 16 native rows in, 64 whole-line stores "
        "out, then note_k_block_saved publishes the bits.")

W = 700


def fig():
    fid = "kv_cache-d7"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"],
                           "gone": C["gone"]})]
    o.append(text(16, 16, "set_k_block: the present mask of PR 4958 is removed; only a "
                  "whole 16-token block is stored at once", 11.5, weight=700))

    # ---- A: before / after -------------------------------------------------------
    ay = 30
    o.append(rect(16, ay, 330, 84, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(24, ay + 15, "before (PR 4958): set_k_block(slot, kv_head, c,", 9.5,
                  mono=True, fill=C["gone"], weight=600))
    o.append(text(24, ay + 27, "    __mmask16 present, rows)", 9.5, mono=True,
                  fill=C["gone"], weight=600))
    o.append(lines(24, ay + 42, ["store_block(..., c, present, rows): bit t of present",
                                 "said that rows[t] is the row of offset c * 16 + t;",
                                 "a run of 2..15 tokens took this masked save"],
                   8.5, 10, fill=C["gone"]))
    o.append(cite(342, ay + 80, "kv_cache.hpp:2324, 2326 (base lines)"))
    boxes.append(("set_k_block with __mmask16 present (before, removed)",
                  "base lines of the diff at head kv_cache.hpp:2321-2327 (the signature "
                  "without present at 2321-2324)"))
    o.append(arrow(fid, "ink", [(348, ay + 42), (366, ay + 42)], C["ink"], 1.4))
    o.append(fn_cell(368, ay, 316, 84, "set_k_block(slot, kv_head, c, rows)",
                     ["K rows of the 16 tokens of one block of this page,",
                      "stored at once in the VNNI layout; the caller records",
                      "the block with note_k_block_saved after the last head"],
                     "kv_cache.hpp:2309-2328", "changed"))
    boxes.append(("set_k_block", "kv_cache.hpp:2309-2328 (comment 2309-2316)"))
    # the body
    by = ay + 92
    o.append(rect(368, by, 316, 66, C["soft"], C["line"], 1, 4))
    body = ["TRON_ASSERT_LT(c, page_size / k_vnni::BLOCK_TOKENS_16);",
            "store_block(kv_block<geometry>(slot, kv_head)",
            "    .k.as_view(), c, k_vnni::FULL_BLOCK_0XFFFF, rows);"]
    for s in body:
        fit(s, 8.5, 300, True, "d7 body")
    o.append(lines(376, by + 14, body, 8.5, 11, mono=True))
    o.append(text(376, by + 48, "FULL_BLOCK_0XFFFF: the 16 lanes of one token block, all "
                  "present", 8.5, fill=C["muted"]))
    o.append(cite(680, by + 62, "kv_cache.hpp:2325-2327; tensor/k_vnni.hpp:80"))
    boxes.append(("the body: TRON_ASSERT_LT(c, ...) and store_block(..., "
                  "k_vnni::FULL_BLOCK_0XFFFF, rows)", "kv_cache.hpp:2325-2327; "
                  "FULL_BLOCK_0XFFFF tensor/k_vnni.hpp:80"))
    # the comment's facts, left
    o.append(rect(16, by, 330, 66, C["soft"], C["line"], 1, 4))
    cf = ["bit-identical to set_k_row per token of a complete block",
          "(store_block); only the write pattern differs;",
          "rows[t] (128 bf16) is the row of offset c * 16 + t, a native",
          "source row in dimension order, not packed storage"]
    for s in cf:
        fit(s, 8.5, 314, False, "d7 comment facts")
    o.append(lines(24, by + 13, cf, 8.5, 10.5))
    o.append(cite(342, by + 62, "kv_cache.hpp:2311-2316"))
    boxes.append(("rows[k_vnni::BLOCK_TOKENS_16] (the 16 native source rows, bit-identical "
                  "to set_k_row per token)", "kv_cache.hpp:2311-2316, 2324"))

    # ---- B: the caller decides by run length --------------------------------------
    cy = by + 66 + 22
    o.append(text(16, cy, "B. the caller store_k_block [any thread of the window]: a run "
                  "of n tokens of one block", 11, weight=700))
    o.append(cite(684, cy, "model.hpp:3238-3338"))
    boxes.append(("store_k_block (caller): the run and the two branches",
                  "model.hpp:3238-3338; the branch 3297-3333"))
    dy = cy + 10
    o.append(rect(16, dy, 668, 26, "#fff", C["ink"], 1.2, 4))
    o.append(text(24, dy + 17, "the run: consecutive items in block c of this page; n tokens, "
                  "present |= bit per token [model.hpp:3280-3296]", 9.5, mono=True))
    boxes.append(("the run (consecutive items in block c of this page)",
                  "model.hpp:3280-3296"))
    # two branches
    ly, lh = dy + 44, 96
    o.append(arrow(fid, "rm", [(180, dy + 26), (180, ly - 2)], C["rm"], 1.6))
    o.append(text(188, dy + 38, "n < k_store_block (1..15 tokens)", 9, mono=True,
                  fill=C["rm"], weight=700))
    o.append(arrow(fid, "vnni", [(520, dy + 26), (520, ly - 2)], C["vnni"], 1.6))
    o.append(text(528, dy + 38, "n == 16", 9, mono=True, fill=C["vnni"], weight=700))
    o.append(rect(16, ly, 330, lh, C["rm_fill"], C["rm"], 1.3, 4))
    o.append(text(24, ly + 15, "row by row: set_k_row per token and KV head", 10,
                  weight=700))
    rl = ["an incomplete block: row-major rows (Note [Row-major",
          "tail block]), or the VNNI column when the block is",
          "complete already (a row saved again); set_k_row decides",
          "(unit C6). No block save, no bits here; the saved-row bits",
          "are recorded after the join (note_k_row_saved, unit C4)"]
    for s in rl:
        fit(s, 9, 314, False, "d7 row branch")
    o.append(lines(24, ly + 29, rl, 9, 11))
    o.append(cite(342, ly + lh - 4, "model.hpp:3297-3316"))
    boxes.append(("n < k_store_block: set_k_row per token (row-major rows)",
                  "model.hpp:3297-3316"))
    o.append(rect(354, ly, 330, lh, C["vnni_fill"], C["vnni"], 1.3, 4))
    o.append(text(362, ly + 15, "the whole block: the VNNI block save, then the bits", 10,
                  weight=700))
    vl = ["TRON_ASSERT(present == k_vnni::FULL_BLOCK_0XFFFF,",
          "  \"store_k_block: a run of 16 tokens must cover its block\")",
          "for every KV head: rows[run_t[i]] = the source row;",
          "  pg.set_k_block<geometry.kv>(slot, kv_head, c, rows)",
          "then pg.note_k_block_saved(slot, c): 16 row bits + block bit"]
    for s in vl:
        fit(s, 8.5, 314, True, "d7 block branch")
    o.append(lines(362, ly + 29, vl, 8.5, 11, mono=True))
    o.append(cite(680, ly + lh - 4, "model.hpp:3317-3333"))
    boxes.append(("n == 16: TRON_ASSERT(present == k_vnni::FULL_BLOCK_0XFFFF), "
                  "set_k_block per KV head, note_k_block_saved", "model.hpp:3317-3333"))
    # removed middle branch
    gy = ly + lh + 10
    o.append(rect(16, gy, 668, 46, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(24, gy + 14, "removed (PR 4958 behaviour): a run of 2..15 tokens stored "
                  "as a masked block save (set_k_block with present != 0xffff),", 8.5,
                  fill=C["gone"], weight=600))
    o.append(text(24, gy + 26, "and a run of 1 token as a scatter (k_scatter_run_len = 1, "
                  "removed from model.hpp)", 8.5, fill=C["gone"], weight=600))
    o.append(text(24, gy + 38, "both now take the row-by-row branch", 8.5, fill=C["gone"]))
    o.append(cite(680, gy + 42, "model.hpp:3297 (base: if (n == k_scatter_run_len))"))
    boxes.append(("k_scatter_run_len (removed)", "base model.hpp:3140-3141 (the removed "
                  "constant); the removed condition at head model.hpp:3297"))

    # ---- C: one set_k_block call and the B4 arc --------------------------------------
    sy = gy + 46 + 22
    o.append(text(16, sy, "C. one set_k_block call (one KV head), and the B4 arc it makes "
                  "with note_k_block_saved", 11, weight=700))
    # rows -> set_k_block -> panels
    rx, rw, ry0, rh = 16, 150, sy + 12, 11
    o.append(text(rx, ry0 + 8, "rows[k_vnni::BLOCK_TOKENS_16]", 9, mono=True, fill=C["rm"],
                  weight=700))
    for t in range(16):
        yy = ry0 + 14 + t * (rh + 1)
        o.append(rect(rx, yy, rw, rh, C["rm_fill"], C["rm"], 0.8, 1))
        o.append(text(rx + 4, yy + 8.5, f"rows[{t}]: offset {16 * 2 + t}", 8.5, mono=True))
    o.append(cite(rx + rw, ry0 + 14 + 16 * 12 + 10, "kv_cache.hpp:2311-2312, 2324"))
    fx, fw, fy, fh = 230, 220, ry0 + 60, 78
    o.append(fn_cell(fx, fy, fw, fh, "set_k_block",
                     ["stores the 16 rows of block c of one",
                      "KV head at once in the VNNI layout;",
                      "sets no bit"],
                     "kv_cache.hpp:2317-2328", "changed"))
    o.append(card_arrow(fid, "rm", [(rx + rw + 2, fy + 30), (fx - 2, fy + 30)], C["rm"],
                        "16 rows in", label_dy=-6, size=9))
    o.append(text((rx + rw + fx) / 2, fy + 44, "256 B each", 8.5, "middle", fill=C["rm"]))
    px, pw, pch, pgap = 560, 100, 40, 4
    o.append(text(px + pw, ry0 + 8, "block 2: panels (s, 2)", 9, "end", True,
                  fill=C["vnni"], weight=700))
    for s in range(4):
        py = ry0 + 14 + s * (pch + pgap)
        o.append(block_cell(px, py, pw, pch, "vnni"))
        o.append(text(px + pw / 2, py + 17, f"panel ({s},2)", 9.5, "middle", True))
        o.append(text(px + pw / 2, py + 31, f"#{4 * s + 2}", 9, "middle", True,
                      fill=C["muted"]))
    o.append(cite(px + pw, ry0 + 14 + 4 * 44 + 6, "tensor/k_vnni.hpp:403-411"))
    boxes.append(("block 2: panels (s, 2) = #2, #6, #10, #14",
                  "Note [Row-major tail block] (tensor/k_vnni.hpp:403-411); panel (s, c): "
                  "tensor/k_vnni.hpp:29-30"))
    mx = (fx + fw + px) / 2
    o.append(arrow(fid, "vnni", [(fx + fw + 2, fy + 30), (px - 2, fy + 30)], C["vnni"], 1.4))
    o.append(lines(mx, fy + 8, ["1 call -> 64 stores", "of whole 64 B lines"], 9, 11, "middle",
                   fill=C["vnni"], weight=600))
    o.append(text(mx, fy + 46, "4 KiB in all", 8.5, "middle", fill=C["muted"]))
    o.append(lines(mx, fy + 58, ["tensor/k_vnni.hpp:", "347-388"], 8.5, 10, "middle",
                   True, fill=C["cite"]))
    boxes.append(("store_block: 64 stores of whole lines", "tensor/k_vnni.hpp:347-388"))
    # the B4 arc under it
    ey = ry0 + 14 + 16 * 12 + 24
    stw, sth = 140, 56
    o.append(state_box(200, ey, stw, sth, "empty", "empty", "no row saved",
                       "kv_cache.hpp:2639-2648"))
    o.append(state_box(560, ey, stw, sth, "vnni", "converted: VNNI",
                       "16 row bits, bit set", "kv_cache.hpp:2649-2653"))
    o.append(arrow(fid, "vnni", [(200 + stw + 2, ey + 28), (558, ey + 28)], C["vnni"], 1.6))
    o.append(text(450, ey + 20, "the B4 arc: set_k_block per KV head,", 8.5, "middle",
                  fill=C["vnni"], weight=600))
    o.append(text(450, ey + 42, "then note_k_block_saved; no wait", 8.5, "middle",
                  fill=C["vnni"], weight=600))
    boxes.append(("empty -> converted: VNNI (the arc over the top of B4)",
                  "kv_cache.hpp:2639-2653; Note [K VNNI storage] 739-745"))
    o.append(lines(16, ey + sth + 18, ["the worked example's blocks 0 and 1 took this arc in the "
                                       "prefill pass (units [0,16) and [16,32) of the shared "
                                       "window);",
                                       "block 2 did not: its 9-token run went row by row"],
                   8.5, 11, fill=C["muted"]))
    H = ey + sth + 40
    cap = ("Updates B3 row 2 and B4: set_k_block loses the present mask of PR 4958. "
           "The caller store_k_block now has two branches by run length: a run of 1 to "
           "15 tokens goes row by row through set_k_row (the row-major tail block), and "
           "only a run of 16 tokens that covers its block takes set_k_block, after an "
           "assert that the mask is full. The removed middle case (a masked block save "
           "for 2 to 15 tokens) is the dashed red box. Section C is one call: 16 native "
           "rows in, 64 whole-line stores out, then note_k_block_saved, the arc over "
           "the top of B4.")
    legend = [
        ("box", "white box, ink outline: the function cell set_k_block (name in bold "
                "monospace, description in sans-serif) and the run box of store_k_block"),
        ("ctx", "grey box, thin grey outline: the body of set_k_block and the facts of "
                "its comment"),
        ("gone", "red dashed box, red text: before (PR 4958): the signature with "
                 "__mmask16 present, and the removed masked block save of a run of 2..15 "
                 "tokens (k_scatter_run_len)"),
        ("rm", "orange: the row-by-row branch (n < k_store_block), and rows[t], the 16 "
               "native source rows of block 2 that enter set_k_block, 256 B each"),
        ("vnni", "blue: the whole-block branch (n == 16), the four panels (s, 2) of block "
                 "2 in the VNNI layout, and the state converted: VNNI"),
        ("empty", "grey dashed: the state empty (no row saved), the start of the B4 arc"),
        ("arrow", "ink arrow: before -> after of the signature"),
        ("orange arrow: the run of 1..15 tokens -> row by row; the 16 rows -> set_k_block "
         "(16 rows in)", "arrow", C["rm"]),
        ("blue arrow: the run of 16 tokens -> the whole-block branch; set_k_block -> the "
         "four panels (1 call -> 64 whole-line stores); the B4 arc", "arrow", C["vnni"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "grey 'changed' = set_k_block is changed by this PR (the mask removed)"),
    ]
    return figure(fid, W, H, "set_k_block stores whole blocks only: the present mask is "
                  "removed", "".join(o), cap, boxes=boxes, legend=legend)
