"""Change diagrams of unit c4 of the kv_cache.hpp page (PR 4959): the two
writers of the K layout state, note_k_row_saved and note_k_block_saved (head
lines 2205-2247, all new). Two figures:
  d4a: note_k_row_saved, the row path, with its four return cases run on the
       worked example.
  d4b: note_k_block_saved, the whole-block path, its next event on the worked
       example, and where the two writers sit on the B4 state strip and the
       lanes of B5.

Every label comes from the head file (kv_cache.hpp at 6b081187e1) or from
model.hpp at the head. Line numbers are head line numbers of kv_cache.hpp
unless another file is named. The worked example is the page's (page 7, state
entry 5, rows 0..45 saved; B1).
"""
from svg_helpers import (C, arrow, bit_row, block_cell, cite, figure, fn_cell,
                         lane, line, lines, marker_defs, rect, text, text_width)
from base_kv_cache import caller_cell, fit, lane_block, state_box

BASE = ("Updates B4 and B5: the two arrows of B4 that write the page's bits get their "
        "functions drawn: note_k_row_saved (the 16th-row arrow and the two "
        "re-save loops, with its four return cases run on the worked example, "
        "part a) and note_k_block_saved (the whole-block arc: both bit sets "
        "published in one place, the row bits first, part b). Part b also places "
        "the two writers on the lanes of B5: note_k_row_saved on the main thread "
        "after the join, note_k_block_saved on any thread of the window.")

# the worked example: page 7, state entry 5 (slot 5), rows 0..45 saved
PAGE, ENTRY = 7, 5
SET_14 = "1" * 14 + "0" * 2        # block 2 now: offsets 32..45
SET_15 = "1" * 15 + "0"            # block 2 after rows 32..46
ALL_16 = "1" * 16
NONE_16 = "0" * 16
W = 700
HDR = [f"worked example (B1): page {PAGE}, state entry {ENTRY} (slot {ENTRY}), "
       "rows 0..45 saved: blocks 0 and 1 stored whole (VNNI), block 2 holds",
       "rows 32..45 (14 row-major rows), block 3 empty. "
       "Bit 16 c of a block is at the left of each bit row."]


def step_box(o, boxes, x, y, w, h, title, code, ref, reg, fill="#fff",
             stroke=C["ink"], dash=None, title_fill=None, src=None):
    """One step inside a function: a bold title, up to 3 mono code lines, a
    citation; `reg` is the register label (a name from the code) and `src`
    its register source when the box cites a call site as well as the
    definition (default: ref)."""
    o.append(rect(x, y, w, h, fill, stroke, 1.2, 4, dash))
    fit(title, 9.5, w - 12, False, f"step {title}")
    o.append(text(x + 6, y + 14, title, 9.5, weight=700, fill=title_fill))
    for s in code:
        fit(s, 9, w - 12, True, f"step {title}")
    o.append(lines(x + 6, y + 27, code, 9, 11, mono=True))
    fit(ref, 8.5, w - 8, True, f"step cite {title}")
    o.append(cite(x + w - 4, y + h - 4, ref))
    boxes.append((reg, src or ref))


def case_row(o, y, label, bits, new_bit, blk_on, fetch, returns, then):
    """One row of the worked-example table of note_k_row_saved."""
    for s in label:
        fit(s, 9, 150, False, "case label")
    o.append(lines(16, y + 10, label, 9, 11))
    body, _ = bit_row(172, y + 4, bits, 9, 1, C["rows_fill"], C["rows"], group=0)
    o.append(body)
    if new_bit is not None:
        o.append(rect(172 + new_bit * 10, y + 4, 9, 9, "none", C["ink"], 1.8, 1))
    o.append(rect(346, y + 3, 11, 11, C["blk_fill"] if blk_on else C["empty_fill"],
                  C["blk"] if blk_on else C["empty"], 1, 1))
    for s in fetch:
        fit(s, 9, 94, True, "case fetch")
    o.append(lines(374, y + 10, fetch, 9, 11, mono=True))
    o.append(text(474, y + 14, returns, 9.5, weight=700,
                  fill=C["pend"] if returns == "true" else C["muted"]))
    for s in then:
        fit(s, 9, 166, False, "case then")
    o.append(lines(520, y + 9, then, 9, 10))


def header(o):
    for s in HDR:
        fit(s, 9.5, 670, False, "header")
    o.append(lines(16, 13, HDR, 9.5, 12, fill=C["muted"]))


# ---- d4a: note_k_row_saved -----------------------------------------------------
def fig_a():
    fid = "kv_cache-d4a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "rows": C["rows"],
                           "blk": C["blk"], "muted": C["muted"], "rm": C["rm"]})]
    header(o)
    ay = 44
    ta = ("A. note_k_row_saved: the row path, one row at a time [main thread of "
          "save_k, after the store]")
    fit(ta, 11, 670, False, "title A")
    o.append(text(16, ay, ta, 11, weight=700))
    CH = 80
    cl = ["model.hpp save_k_impl: the", "row-recording loop after the",
          "store (and the join) [main];", "skipped when",
          "cached_operation_uses_hw"]
    o.append(caller_cell(16, ay + 8, 190, CH, cl, "model.hpp:3419-3428"))
    boxes.append(("save_k_impl: the row-recording loop (caller)",
                  "model.hpp:3419-3428 (inside save_k_impl, model.hpp:3345)"))
    my = ay + 8 + CH / 2
    o.append(arrow(fid, "ink", [(208, my), (294, my)], C["ink"], 1.4))
    o.append(text(251, my - 6, "1 call per item", 9, "middle", fill=C["ink"], weight=600))
    o.append(text(251, my + 13, "with KV work", 9, "middle", fill=C["ink"], weight=600))
    fd = ["sets the row's bit; true = the block has 16 row bits, no block bit yet",
          "uniform-geometry overload forwards to the primary geometry (2232-2237)"]
    for s in fd:
        fit(s, 9.5, 390 - 16, False, "fn A desc")
    o.append(fn_cell(296, ay + 8, 390, CH, "note_k_row_saved(slot, offset)", fd,
                     "kv_cache.hpp:2205-2237", "new"))
    boxes.append(("note_k_row_saved", "kv_cache.hpp:2205-2237 (template 2212-2230, "
                  "uniform-geometry overload 2232-2237)"))
    sy = ay + 8 + CH + 14
    o.append(text(16, sy, "inside, in order (after TRON_ASSERT_LT(offset, page_size), "
                  "2216):", 9, fill=C["muted"]))
    sy += 6
    sw, sh = 154, 68
    sx = [16, 187, 358, 529]
    step_box(o, boxes, sx[0], sy, sw, sh, "row-major slot: exit",
             ["!k_vnni::layout_on:", "return false", "(keeps no bits)"],
             "kv_cache.hpp:2217-2219", "return false (row-major slot exit)",
             C["empty_fill"], C["empty"], "4 3", C["muted"])
    step_box(o, boxes, sx[1], sy, sw, sh, "which entry, block, bit",
             ["ix = k_state_ix(slot)", "c = offset/BLOCK_TOKENS_16", "bit = offset_bit(offset)"],
             "kv_cache.hpp:2220-2222", "k_state_ix(slot), offset / BLOCK_TOKENS_16, "
             "k_vnni::offset_bit(offset)")
    step_box(o, boxes, sx[2], sy, sw, sh, "set the row's bit",
             ["load(relaxed); bit clear", "-> fetch_or(bit, acq_rel)",
              "after = before | bit"],
             "kv_cache.hpp:2224-2226", "k_rows_saved_[ix]: relaxed load, fetch_or "
             "acq_rel when the bit is clear", C["rows_fill"], C["rows"])
    step_box(o, boxes, sx[3], sy, sw, sh, "return value",
             ["(after & k_block_bits(c))", "== k_block_bits(c) &&",
              "block bit clear (acquire)"],
             "kv_cache.hpp:2227-2229", "return: k_block_bits(c) all set and "
             "k_vnni_blocks_[ix] bit c clear")
    for i in range(3):
        o.append(arrow(fid, "ink", [(sx[i] + sw + 2, sy + 31), (sx[i + 1] - 2, sy + 31)],
                       C["ink"], 1.2))
    # outcomes
    oy = sy + sh + 14
    o.append(arrow(fid, "pend", [(sx[3] + 77, sy + sh), (sx[3] + 77, oy)], C["pend"], 1.4))
    o.append(arrow(fid, "muted", [(sx[3] + 16, sy + sh), (sx[3] + 16, sy + sh + 7),
                                  (150, sy + sh + 7), (150, oy)], C["muted"], 1.2))
    o.append(rect(296, oy, 390, 56, C["pend_fill"], C["pend"], 1.2, 4))
    o.append(text(304, oy + 14, "true -> pending_k_blocks_.push_back(...) [main]", 10,
                  mono=True, weight=700, fill=C["pend"]))
    tl = ["{&pg, pg.k_storage_of(slot), j / k_store_block}: 1 push per row that",
          "completes a not-yet-converted block; k_block_to_vnni_at converts it (C5)"]
    for s in tl:
        fit(s, 9, 390 - 16, False, "true box")
    o.append(lines(304, oy + 27, tl, 9, 11))
    o.append(cite(682, oy + 52, "model.hpp:3426-3428, 3161-3166"))
    boxes.append(("pending_k_blocks_.push_back (true)",
                  "model.hpp:3426-3428; struct pending_k_block 3161-3166"))
    o.append(rect(16, oy, 266, 56, "#fff", C["muted"], 1.2, 4))
    o.append(text(24, oy + 14, "false: the row did not complete its block", 10,
                  weight=700, fill=C["muted"]))
    fl = ["(or its block is converted already, 2209-2211);",
          "nothing is queued"]
    for s in fl:
        fit(s, 9, 266 - 16, False, "false box")
    o.append(lines(24, oy + 27, fl, 9, 11))
    o.append(cite(278, oy + 52, "kv_cache.hpp:2206-2211"))
    boxes.append(("false: the row did not complete its block (nothing queued)",
                  "kv_cache.hpp:2206-2211, 2227-2229"))
    # the worked-example table of the four return cases
    ty = oy + 56 + 20
    o.append(text(16, ty, "row saved (worked example)", 9, weight=700))
    o.append(text(172, ty, f"k_rows_saved_[{ENTRY}] bits of block c", 8.5, mono=True,
                  weight=700, fill=C["rows"]))
    o.append(text(351.5, ty - 10, "block", 8.5, "middle", fill=C["blk"], weight=700))
    o.append(text(351.5, ty, "bit c", 8.5, "middle", fill=C["blk"], weight=700))
    o.append(text(374, ty, "fetch_or?", 9, weight=700))
    o.append(text(474, ty, "returns", 9, weight=700))
    o.append(text(520, ty, "then", 9, weight=700))
    o.append(text(172, ty + 12, "bit 16 c at the left; thick outline = the bit this call sets",
                  8.5, fill=C["muted"]))
    ry = ty + 18
    cases = [
        (["offset 46 = block 2, t = 14", "rows 32..45 saved (B1)"], SET_14, 14, False,
         ["bit was clear:", "fetch_or acq_rel"], "false",
         ["nothing queued; the block", "stays incomplete, row-major"]),
        (["offset 47 = block 2, t = 15", "after rows 32..46 were saved"], SET_15, 15,
         False, ["bit was clear:", "fetch_or acq_rel"], "true",
         ["main pushes {&pg,", "k_storage_of(slot), 2} onto", "pending_k_blocks_"]),
        (["offset 40 = block 2, t = 8", "saved again; block 2 may wait"], ALL_16, None,
         False, ["bit already set:", "relaxed load only"], "true",
         ["pushed again; k_block_to_vnni_at", "converts a block once", "(idempotent)"]),
        (["offset 5 = block 0, t = 5", "saved again; block 0 converted"], ALL_16, None,
         True, ["bit already set:", "relaxed load only"], "false",
         ["nothing queued: set_k_row", "wrote the row into the", "VNNI column"]),
    ]
    for i, (lab, bits, nb, blk, fe, ret, th) in enumerate(cases):
        y = ry + i * 40
        o.append(line(16, y, 686, y, C["line"], 0.8))
        case_row(o, y, lab, bits, nb, blk, fe, ret, th)
    o.append(line(16, ry + 4 * 40, 686, ry + 4 * 40, C["line"], 0.8))
    o.append(cite(686, ry + 4 * 40 + 12, "kv_cache.hpp:2209-2211, 2224-2229"))
    boxes.append((f"note_k_row_saved on k_rows_saved_[{ENTRY}] / k_vnni_blocks_[{ENTRY}]: "
                  "the four return cases (table)",
                  "kv_cache.hpp:2205-2215 (comment and signature), 2224-2229"))
    # ---- the fragment of B4 that part a draws: incomplete -> complete ----------
    gy = ry + 4 * 40 + 30
    o.append(text(16, gy, "the B4 fragment of part a: the two states the return value "
                  "tells apart", 10, weight=700))
    sw2, sh2 = 160, 64
    o.append(state_box(16, gy + 8, sw2, sh2, "rm", "incomplete, row-major",
                       "1..15 row bits, bit clear", "kv_cache.hpp:711-720"))
    o.append(state_box(276, gy + 8, sw2, sh2, "pend", "complete, may wait",
                       "16 row bits, bit c clear", "kv_cache.hpp:718-719"))
    o.append(arrow(fid, "pend", [(16 + sw2 + 2, gy + 34), (274, gy + 34)], C["pend"], 1.6))
    o.append(text(226, gy + 28, "true: the 16th row", 8.5, "middle", fill=C["pend"],
                  weight=700))
    o.append(text(226, gy + 48, "(cases 2 and 3)", 8.5, "middle", fill=C["pend"],
                  weight=700))
    o.append(arrow(fid, "rm", [(16 + 150, gy + 8 + sh2), (16 + 150, gy + 8 + sh2 + 12),
                               (16 + 100, gy + 8 + sh2 + 12), (16 + 100, gy + 8 + sh2 + 2)],
                   C["rm"], 1.4))
    o.append(text(16 + 125, gy + 8 + sh2 + 24, "false: rows 1..15 (case 1)", 8.5, "middle",
                  fill=C["rm"]))
    o.append(lines(452, gy + 20, ["false of case 4 (a converted block) and the",
                                  "conversion itself are drawn in part b"], 9, 11,
                   fill=C["muted"]))
    boxes += [("incomplete block: row-major rows (row-major tail block)",
               "kv_cache.hpp:711-720; model.hpp:3298"),
              ("complete, may wait for its conversion", "kv_cache.hpp:718-719")]
    H = gy + 8 + sh2 + 34
    cap = ("Updates B4 (part a): the 16th-row arrow of B4 and the two re-save loops "
           "are note_k_row_saved, the row path. After the store (and after the join, "
           "when the store is shared) the main thread calls note_k_row_saved once per "
           "item with KV work [model.hpp:3419-3426]. The table runs the worked example "
           "(page 7, state entry 5) through the four return cases. Look at which rows "
           "return true and queue the block in pending_k_blocks_. The two state boxes "
           "at the foot are the B4 fragment this function drives.")
    legend = [
        ("box", "white box, ink outline: note_k_row_saved (name in bold monospace, what "
                "it does in sans-serif) and its plain steps 'which entry, block, bit' and "
                "'return value'"),
        ("ctx", "grey box, thin grey outline: the caller save_k_impl (model.hpp), its "
                "row-recording loop after the store and the join"),
        ("empty", "grey dashed: the early exit of a row-major slot (!k_vnni::layout_on "
                  "returns false)"),
        ("rows", "green: k_rows_saved_, the step that sets the row's bit (fetch_or), and a "
                 "saved-row bit that is set (one square per row of block c); the table "
                 "header in green text"),
        ("bit_clear", "white square, grey outline: a bit that is clear (a row bit, or the "
                      "block bit c)"),
        ("ink outline on one bit square: the bit this call sets (cases 1 and 2)",
         "none", C["ink"], False, False),
        ("blk", "pink: the block bit c that is set (case 4, block 0 converted); the "
                "'block bit c' header in pink text"),
        ("pend_solid", "orange-red box: the true return, main pushes the block onto "
                       "pending_k_blocks_; 'true' in the table in orange-red text"),
        ("white box, grey outline: the false return, the row did not complete its block, "
         "nothing queued; 'false' in the table in grey text", "#fff", C["muted"], False,
         False),
        ("rm", "orange: the state 'incomplete, row-major' (1..15 row bits, bit c clear)"),
        ("pend", "orange-red dashed: the state 'complete, may wait' (16 row bits, bit c "
                 "clear)"),
        ("arrow", "ink arrow: the call save_k_impl -> note_k_row_saved (1 per item with "
                  "KV work) and the order of the steps"),
        ("grey arrow: the false return, to the nothing-queued box", "arrow", C["muted"]),
        ("orange-red arrow: the true return (the 16th row), to the push onto "
         "pending_k_blocks_, and incomplete -> complete, may wait (cases 2 and 3)",
         "arrow", C["pend"]),
        ("orange arrow: the false return of rows 1..15 (case 1), the block stays "
         "incomplete, row-major", "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new': note_k_row_saved is added by this PR"),
    ]
    return figure(fid, W, H, "note_k_row_saved: the row path and its four return cases",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- d4b: note_k_block_saved and the B4 strip -------------------------------------
def fig_b():
    fid = "kv_cache-d4b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "pend": C["pend"], "rows": C["rows"],
                           "blk": C["blk"], "rm": C["rm"], "vnni": C["vnni"]})]
    header(o)
    by = 44
    tb = ("B. note_k_block_saved: the whole-block path [any thread of the shared "
          "window]")
    fit(tb, 11, 670, False, "title B")
    o.append(text(16, by, tb, 11, weight=700))
    CH = 80
    cl = ["model.hpp store_k_block: a run", "of 16 tokens covering its block:",
          "set_k_block per KV head, then", "this call [any thread of the",
          "shared window]"]
    o.append(caller_cell(16, by + 8, 190, CH, cl, "model.hpp:3317-3333"))
    boxes.append(("store_k_block: the whole-block run (caller)", "model.hpp:3317-3333"))
    my = by + 8 + CH / 2
    o.append(arrow(fid, "ink", [(208, my), (294, my)], C["ink"], 1.4))
    o.append(text(251, my - 6, "1 call per", 9, "middle", fill=C["ink"], weight=600))
    o.append(text(251, my + 13, "whole-block run", 9, "middle", fill=C["ink"], weight=600))
    fd = ["publishes the 16 row bits, then the block bit, after the last KV head",
          "bits are per slot, not per head: the block bit comes last (742-743)"]
    for s in fd:
        fit(s, 9.5, 390 - 16, False, "fn B desc")
    o.append(fn_cell(296, by + 8, 390, CH, "note_k_block_saved(slot, c)", fd,
                     "kv_cache.hpp:2239-2247", "new"))
    boxes.append(("note_k_block_saved", "kv_cache.hpp:2239-2247"))
    sy = by + 8 + CH + 14
    o.append(text(16, sy, "inside, in order (after TRON_ASSERT_LT(c, page_size / "
                  "k_vnni::BLOCK_TOKENS_16), 2243):", 9, fill=C["muted"]))
    sy += 6
    sw, sh = 204, 68
    sx = [16, 248, 480]
    step_box(o, boxes, sx[0], sy, sw, sh, "which entry",
             ["ix = k_state_ix(slot)", "(the EAGLE entry for slot 0", "under the EAGLE view)"],
             "kv_cache.hpp:2244, 2531-2537", "k_state_ix(slot)",
             src="kv_cache.hpp:2244 (the call); k_state_ix defined at kv_cache.hpp:2531-2537")
    step_box(o, boxes, sx[1], sy, sw, sh, "16 row bits -> set",
             ["k_rows_saved_[ix].fetch_or(", "k_block_bits(c), acq_rel)",
              "the 16 bits of block c"],
             "kv_cache.hpp:2245", "k_rows_saved_[ix].fetch_or(k_block_bits(c), acq_rel)",
             C["rows_fill"], C["rows"])
    step_box(o, boxes, sx[2], sy, sw, sh, "1 block bit -> set, last",
             ["k_vnni_blocks_[ix].fetch_or(", "block_bit(c), release)",
              "bit c: block c holds VNNI"],
             "kv_cache.hpp:2246", "k_vnni_blocks_[ix].fetch_or(block_bit(c), release)",
             C["blk_fill"], C["blk"])
    for i in range(2):
        o.append(arrow(fid, "ink", [(sx[i] + sw + 2, sy + 31), (sx[i + 1] - 2, sy + 31)],
                       C["ink"], 1.2))
        o.append(text((sx[i] + sw + sx[i + 1]) / 2, sy + 25, "then", 8.5, "middle",
                      fill=C["ink"]))
    # worked example of B: block 3 stored whole
    wy = sy + sh + 16
    we = (f"worked example, next event: offsets 48..63 stored whole with set_k_block "
          f"per KV head; note_k_block_saved(slot {ENTRY}, c = 3)")
    fit(we, 9.5, 670, False, "worked B")
    o.append(text(16, wy, we, 9.5, weight=700))
    cy = wy + 8
    o.append(block_cell(16, cy, 26, 14, "empty"))
    o.append(text(48, cy + 11, "block 3 before: no row saved", 9))
    body, _ = bit_row(16, cy + 20, NONE_16, 9, 1, C["rows_fill"], C["rows"], group=0)
    o.append(body)
    o.append(rect(186, cy + 19, 11, 11, C["empty_fill"], C["empty"], 1, 1))
    # the "after" chip sits 12 px further right so that the label clears it
    o.append(arrow(fid, "vnni", [(212, cy + 25), (310, cy + 25)], C["vnni"], 1.6))
    o.append(text(261, cy + 12, "16 row bits acq_rel", 9, "middle", fill=C["vnni"],
                  weight=600))
    o.append(text(261, cy + 40, "then bit 3 release", 9, "middle", fill=C["vnni"],
                  weight=600))
    o.append(block_cell(322, cy, 26, 14, "vnni"))
    o.append(text(354, cy + 11, "block 3 after: converted (VNNI)", 9))
    body, _ = bit_row(322, cy + 20, ALL_16, 9, 1, C["rows_fill"], C["rows"], group=0)
    o.append(body)
    o.append(rect(492, cy + 19, 11, 11, C["blk_fill"], C["blk"], 1, 1))
    nl = ["no wait, no queue entry;", "a set block bit implies the", "16 row bits [2651]"]
    for s in nl:
        fit(s, 9, 170, False, "worked B note")
    o.append(lines(516, cy + 10, nl, 9, 11, fill=C["muted"]))
    o.append(cite(686, cy + 46, "kv_cache.hpp:2245-2246, 2651"))
    boxes.append((f"k_rows_saved_[{ENTRY}] / k_vnni_blocks_[{ENTRY}] after "
                  f"note_k_block_saved(slot {ENTRY}, c = 3) (worked example)",
                  "kv_cache.hpp:2245-2246, 2651"))

    # ---- C: where the two writers sit in B4 --------------------------------------
    y0 = cy + 56
    o.append(line(16, y0 - 4, 686, y0 - 4, C["line"]))
    o.append(text(16, y0 + 10, "where the two writers sit in B4 (the life of one 16-token "
                  "block of one storage slot)", 10.5, weight=700))
    yc = y0 + 50
    cw, ch = 136, 48
    cx = [16, 192, 368, 544]
    states = [("empty", "empty", "no row saved", "kv_cache.hpp:2639-2648",
               "k_rows_saved_ bits all clear: the empty state", None),
              ("rm", "incomplete, row-major", "1..15 row bits", "kv_cache.hpp:711-720",
               "incomplete block: row-major rows (row-major tail block)",
               "kv_cache.hpp:711-720; model.hpp:3298; Note [Row-major tail block] "
               "(tensor/k_vnni.hpp:403-421)"),
              ("pend", "complete, may wait", "16 row bits, bit c clear", "kv_cache.hpp:718-719",
               "complete, may wait for its conversion", None),
              ("vnni", "converted: VNNI", "16 row bits, bit c set", "kv_cache.hpp:2649-2653",
               "k_vnni_blocks_ bit set: the converted (VNNI) state", None)]
    for x, (st, t1, t2, ref, reg, src) in zip(cx, states):
        fit(t1, 10, cw - 6, False, "state title")
        fit(t2, 8.5, cw - 6, False, "state sub")
        o.append(block_cell(x, yc, cw, ch, st))
        o.append(text(x + cw / 2, yc + 17, t1, 10, "middle", weight=700))
        o.append(text(x + cw / 2, yc + 29, t2, 8.5, "middle"))
        o.append(cite(x + cw - 4, yc + ch - 4, ref))
        boxes.append((reg, src or ref))
    # the arc of B: whole-block save, empty -> converted
    o.append(arrow(fid, "vnni", [(56, yc - 2), (56, y0 + 30), (612, y0 + 30), (612, yc - 2)],
                   C["vnni"], 1.6))
    arc = "B: set_k_block per KV head, then note_k_block_saved; no wait, no queue entry"
    fit(arc, 9, 560, False, "arc label")
    o.append(text(340, y0 + 25, arc, 9, "middle", fill=C["vnni"], weight=700))
    # the arrows of A
    am = yc + 24
    for i, (name, col, lab) in enumerate([("rm", C["rm"], "A: false, rows 1..15"),
                                          ("pend", C["pend"], "A: true, the 16th row: queued"),
                                          ("vnni", C["vnni"], "C5 converts, forward end")]):
        o.append(arrow(fid, name, [(cx[i] + cw + 2, am), (cx[i + 1] - 2, am)], col, 1.6))
        fit(lab, 8.5, 150, False, "A arrow label")
        o.append(text((cx[i] + cw + cx[i + 1]) / 2, y0 + 46, lab, 8.5, "middle", fill=col,
                      weight=700))
    under = [(cx[1], "A: rows 2..15 ->", "false, no queue entry", C["rm"]),
             (cx[2], "A: a row saved again ->", "true again (idempotent)", C["pend"]),
             (cx[3], "A: a row saved again ->", "false (VNNI column)", C["vnni"])]
    for x, l1, l2, col in under:
        o.append(text(x + cw / 2, yc + ch + 14, l1, 8.5, "middle", fill=col))
        o.append(text(x + cw / 2, yc + ch + 24, l2, 8.5, "middle", fill=col))

    # ---- D: where the two writers sit in B5 (the save_k window of one minibatch)
    ly = yc + ch + 44
    o.append(line(16, ly - 8, 686, ly - 8, C["line"]))
    o.append(text(16, ly + 6, "where the two writers sit in B5: the shared save_k window of "
                  "one minibatch (the first two lanes of B5)", 10.5, weight=700))
    LH2, BH2 = 56, 48
    y1 = ly + 14
    y2 = y1 + LH2 + 6
    for y, lab, sub in [(y1, "main thread", "save_k_impl"),
                        (y2, "main helpers", "run_main_help")]:
        s, _ = lane(16, y, 670, LH2, lab, sub)
        o.append(s)
    ym, yh = y1 + 4, y2 + 4
    # idle blocks first, then the work blocks (STYLE trap)
    for y, x, w, ls, ref in [(ym, 366, 56, ["join", "(acquire)"], "3395-3409"),
                             (yh, 156, 100, ["wait: opened >= W"], "3378-3382"),
                             (yh, 422, 258, ["idle: the next kernel waits for the "
                                             "attention output"], "3103-3105"),
                             (ym, 572, 108, ["later: forward end,", "the conversion (C5)"],
                              "1840-1842")]:
        o.append(lane_block(x, y, w, BH2, ls, "#fff", C["muted"], True, 8.5, ref))
    for y, x, w, ls, fill, stroke, ref in [
            (ym, 156, 100, ["save_k window:", "k_store_cut_units"], C["soft"], C["ink"],
             "3373-3377"),
            (ym, 256, 110, ["claim loop (units)", "store_k_block"], C["unit_fill"],
             C["unit"], "3384-3389"),
            (ym, 422, 150, ["A: note_k_row_saved", "-> pending_k_blocks_"], C["rows_fill"],
             C["rows"], "3419-3428"),
            (yh, 256, 110, ["claim loop (units):", "set_k_block, then", "B: note_k_block_saved"],
             C["unit_fill"], C["unit"], "3317-3333, 3384-3389"),
            (yh, 366, 56, ["finished++", "(release)"], C["soft"], C["ink"], "3391-3393")]:
        o.append(lane_block(x, y, w, BH2, ls, fill, stroke, False, 8.5, ref))
    o.append(text(16, y2 + LH2 + 14, "lane citations are line numbers of model.hpp; B "
                  "runs on any thread of the window (main or a helper), A on main only",
                  8.5, fill=C["muted"]))
    boxes += [("note_k_row_saved on the main lane (A: after the join)",
               "model.hpp:3419-3428; kv_cache.hpp:2205-2237"),
              ("note_k_block_saved on any lane of the window (B: the claim loop)",
               "model.hpp:3317-3333, 3384-3389; kv_cache.hpp:2239-2247"),
              ("save_k window (k_store_cut_units, claim loop, join, finished++)",
               "model.hpp:3373-3409; batch::k_store_window (common.hpp:1196-1219)")]
    H = y2 + LH2 + 24
    cap = ("Updates B4 and B5 (part b): the arc over the top of B4 is note_k_block_saved, "
           "the whole-block path. Any thread of the shared window calls note_k_block_saved "
           "after the last KV head. Its two fetch_or calls run in a fixed order: the 16 "
           "row bits with acq_rel, then the block bit with release. That order is what "
           "the arc over the B4 strip means. The strip also names the "
           "arrows of part a (A) and the forward-end conversion (C5). The two lanes at "
           "the bottom are the first two lanes of B5: A runs on the main thread after "
           "the join, B inside the claim loop on whichever thread stores the block.")
    legend = [
        ("box", "white box, ink outline: note_k_block_saved (name in bold monospace, what "
                "it does in sans-serif) and its plain step 'which entry' (k_state_ix)"),
        ("ctx", "grey box, thin grey outline: the caller store_k_block (model.hpp), a run "
                "of 16 tokens covering its block, with its thread in brackets"),
        ("rows", "green: k_rows_saved_, the step that sets the 16 row bits of block c, a "
                 "saved-row bit that is set (one square), and the lane block of A "
                 "(note_k_row_saved) on the main thread"),
        ("blk", "pink: k_vnni_blocks_, the step that sets the block bit c last, and the "
                "block bit that is set (one square)"),
        ("bit_clear", "white square, grey outline: a bit that is clear (block 3 before: "
                      "its 16 row bits and its block bit)"),
        ("empty", "grey dashed: the state 'empty', no row saved (block 3 before, and the "
                  "first state of B4)"),
        ("vnni", "blue: the state 'converted: VNNI', 16 row bits and bit c set (block 3 "
                 "after, and the last state of B4)"),
        ("rm", "orange: the state 'incomplete, row-major' (1..15 row bits)"),
        ("pend", "orange-red dashed: the state 'complete, may wait' (16 row bits, bit c "
                 "clear)"),
        ("unit", "grey-blue: the claim loop of the shared save_k window, one unit of "
                 "store_k_block / set_k_block per claim, on the main thread and on a "
                 "helper"),
        ("ctx_ink", "grey work block, ink outline: the window bookkeeping on the lanes, "
                    "k_store_cut_units and finished++ (release)"),
        ("grey dashed lane block: waiting or idle: the join (acquire), wait: opened >= W, "
         "the next kernel's wait, and the later conversion at forward end (C5)",
         "#fff", C["muted"], True, False),
        ("arrow", "ink arrow: the call store_k_block -> note_k_block_saved (1 per "
                  "whole-block run) and 'then', the order of the two fetch_or calls"),
        ("blue arrow and blue text: the whole-block path B, empty -> converted (block 3 "
         "before -> after; the arc over the B4 strip), and C5, the forward-end conversion",
         "arrow", C["vnni"]),
        ("orange arrow and orange text: A returns false for rows 1..15, empty -> "
         "incomplete, row-major", "arrow", C["rm"]),
        ("orange-red arrow and orange-red text: A returns true for the 16th row, "
         "incomplete -> complete, may wait (queued)", "arrow", C["pend"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new': note_k_block_saved is added by this PR"),
    ]
    return figure(fid, W, H, "note_k_block_saved: the whole-block path, and where the two "
                  "writers sit in B4", "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
