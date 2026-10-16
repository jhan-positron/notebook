"""Change diagrams D6a / D6b of the PR 4424 page for h/tron/models/kv_cache.hpp:
unit c6, "The in-place conversion of one block" (head lines 2202-2236, new).
  d6a: the two entry points, k_block_to_vnni_at, and the two acquire checks.
  d6b: the geometry dispatch, the block_to_vnni loop, the release fetch_or of
       the block bit, and the worked example after the forward end.

Every label and citation comes from facts/kv_cache.json (kv_cache-function-11,
-12, -13, -20, -22; kv_cache-data-10, -13, -40, -44; kv_cache-seq-4, -19;
kv_cache-rule-1, -3) or from the head file itself. Line numbers are head line
numbers of kv_cache.hpp unless another file is named.
"""
from svg_helpers import (C, arrow, bit_row, block_cell, cite, figure, fn_cell,
                         label_box, marker_defs, rect, text)
from base_kv_cache import ROWS_EXAMPLE, block_row, caller_cell, fit

BASE = ("Updates B4: expands the 'complete, may wait' -> 'converted: VNNI' arrow "
        "(the forward end) into the steps of k_block_to_vnni_at, drawn for block 1 "
        "of the worked example: the two entry points and the two acquire checks "
        "that make a repeated call harmless (part a), then the block_to_vnni loop "
        "over every KV head under k_with_storage_geometry and the release fetch_or "
        "of the block bit after the last head (part b).")

W = 720


def _blk_bits(o, x, y, bits, hi=None, hi_word=None):
    """Four k_vnni_blocks_ squares, bit 0 at the left; bit `hi` outlined in ink
    with the word `hi_word` after the row. Returns the x after the row."""
    cx = x
    for c in range(4):
        on = bits[c] == "1"
        o.append(rect(cx, y, 12, 12, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        if hi == c:
            o.append(rect(cx - 1.5, y - 1.5, 15, 15, "none", C["ink"], 1.4, 2))
        cx += 16
    if hi_word:
        o.append(text(cx + 4, y + 10, hi_word, 9, fill=C["blk"], weight=600))
        cx += 4 + len(hi_word) * 9 * 0.55
    return cx


def _title(o):
    o.append(text(16, 14, fit("worked example: page 7, state entry 5 (slot 5); block 1 is "
                              "complete and may wait; the forward end converts it", 10.5,
                              688, False, "title"), 10.5, weight=600))


def fig_a():
    fid = "kv_cache-d6a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    _title(o)

    # ---- row A: the two callers -------------------------------------------------
    ay, ah = 24, 54
    o.append(caller_cell(16, ay, 340, ah, [
        "model.hpp convert_pending_k_blocks: 1 call per",
        "pending_k_blocks_ entry [main thread, forward end,",
        "after wait_for_coop_gof]"], "model.hpp:3173-3180; call at 1847"))
    boxes.append(("convert_pending_k_blocks (caller)",
                  "model.hpp:3171-3180; called from run_forward at model.hpp:1847"))
    o.append(caller_cell(392, ay, 312, ah, [
        "tests only: t_llama_unit.cpp:2543,",
        "t_k_vnni_layout.cpp:667,",
        "t_amx_dispatch_dtype.cpp:132 (no production caller)"],
        "t/t_k_vnni_layout.cpp:667"))
    boxes.append(("k_block_to_vnni call sites (tests only)",
                  "t_llama_unit.cpp:2543; t_k_vnni_layout.cpp:667; "
                  "t_amx_dispatch_dtype.cpp:132"))

    # ---- row B: the logical-slot wrapper (right) ------------------------------------
    by, bh = 92, 56
    o.append(fn_cell(392, by, 312, bh, "k_block_to_vnni(slot, c)", [
        "the logical-slot form: k_storage_of(slot), then",
        "k_block_to_vnni_at; returns the same bool"],
        "kv_cache.hpp:2202-2211", None))
    boxes.append(("k_block_to_vnni", "kv_cache.hpp:2202-2211"))
    o.append(arrow(fid, "ink", [(548, ay + ah), (548, by)], C["ink"], 1.4))

    # ---- row C: k_block_to_vnni_at --------------------------------------------------
    cy, ch = 166, 58
    o.append(fn_cell(16, cy, 688, ch, "k_block_to_vnni_at(storage, c)", [
        "convert block c of every KV head of the storage slot from row-major to the "
        "VNNI layout in place",
        "when its 16 rows are saved and it is not converted yet; returns whether it "
        "converted"], "kv_cache.hpp:2213-2236",
        "new; [main thread] only, at a point where no reader of the block runs "
        "(the forward end) [2206-2207]"))
    boxes.append(("k_block_to_vnni_at", "kv_cache.hpp:2213-2236"))
    boxes.append(("Main thread only, at the forward end (thread rule)",
                  "kv_cache.hpp:2206-2207; model.hpp:1842-1847"))
    # caller -> _at (long arrow on the left), with how many
    o.append(arrow(fid, "ink", [(120, ay + ah), (120, cy)], C["ink"], 1.4))
    o.append(text(128, 118, "1 call per pending_k_blocks_ entry", 9, fill=C["ink"],
                  weight=600))
    o.append(cite(128, 130, "model.hpp:3176-3177", "start"))
    # wrapper -> _at, with how many
    o.append(arrow(fid, "ink", [(548, by + bh), (548, cy)], C["ink"], 1.4))
    o.append(text(540, 158, "k_storage_of: 1 slot -> 1 pair {offset, state_ix} "
                  "[2149-2155]", 9, "end", fill=C["ink"], weight=600))
    boxes.append(("k_storage_of (1 slot -> 1 pair)", "kv_cache.hpp:2149-2155"))

    # ---- row D: the two checks ------------------------------------------------------
    gy, gh = 248, 122
    o.append(arrow(fid, "ink", [(120, cy + ch), (120, gy)], C["ink"], 1.4))
    o.append(text(128, 240, "storage_offset, state_ix = the pair; cbit = "
                  "k_vnni::block_bit(c) [2216-2218]", 9, fill=C["ink"], weight=600))
    o.append(rect(16, gy, 452, gh, "#fff", C["ink"], 1.2, 5))
    o.append(text(24, gy + 16, "the two checks (both loads acquire)", 10.5, weight=600))
    o.append(text(24, gy + 34, fit("k_rows_saved_[state_ix].load(acquire) & k_block_bits(c)"
                                   " == k_block_bits(c)", 9, 436, True, "check 1"),
                  9, mono=True))
    o.append(text(24, gy + 50, "worked example: entry 5, bits 16..31 (block 1):", 9,
                  fill=C["muted"]))
    body, bx = bit_row(262, gy + 41, ROWS_EXAMPLE[16:32], 8, 1, C["rows_fill"],
                       C["rows"], group=0)
    o.append(body)
    o.append(text(bx + 6, gy + 50, "all set", 9, fill=C["rows"], weight=600))
    o.append(text(24, gy + 70, fit("k_vnni_blocks_[state_ix].load(acquire) & cbit == 0"
                                   "   (cbit = block_bit(c))", 9, 436, True, "check 2"),
                  9, mono=True))
    o.append(text(24, gy + 86, "worked example: entry 5 = 0b0001, bit 1 (block 1):", 9,
                  fill=C["muted"]))
    _blk_bits(o, 280, gy + 77, "1000", hi=1, hi_word="clear")
    o.append(text(24, gy + 104, "before the checks: TRON_ASSERT_LT(c, page_size / "
                  "k_vnni::BLOCK_TOKENS_16) [2215]", 8.5, fill=C["muted"]))
    o.append(cite(464, gy + gh - 4, "kv_cache.hpp:2216-2223"))
    boxes += [("k_rows_saved_ / k_vnni_blocks_ checks (acquire loads)",
               "kv_cache.hpp:2216-2223"),
              ("k_rows_saved_", "kv_cache.hpp:2608-2617"),
              ("k_vnni_blocks_", "kv_cache.hpp:2618-2622"),
              ("k_block_bits (the 16 bits of block c)", "kv_cache.hpp:2507-2511"),
              ("k_vnni::block_bit (cbit)", "tensor/k_vnni.hpp:97-100")]
    # either check fails -> CONVERTED_FALSE
    o.append(arrow(fid, "muted", [(468, gy + 50), (484, gy + 50)], C["muted"], 1.4))
    o.append(label_box(484, gy + 10, 220, 80, "return CONVERTED_FALSE", [
        "either check fails: row bits not",
        "all set, or block bit already set;",
        "a repeated call is harmless"], "#fff", C["muted"], 10.5,
        ref="kv_cache.hpp:2219-2223, 2495"))
    boxes.append(("CONVERTED_FALSE / CONVERTED_TRUE", "kv_cache.hpp:2495-2497"))
    # both pass -> part b
    o.append(arrow(fid, "ink", [(120, gy + gh), (120, gy + gh + 22)], C["ink"], 1.4))
    o.append(text(128, gy + gh + 16, "both pass: converted = CONVERTED_FALSE so far [2224]; "
                  "the geometry dispatch and the loop: part b", 9, fill=C["ink"],
                  weight=600))
    H = gy + gh + 30
    cap = ("Updates B4 (part a): the arrow from 'complete, may wait' to 'converted: VNNI' "
           "is k_block_to_vnni_at, drawn here step by step for block 1 of the worked "
           "example (page 7, state entry 5). Read it top to bottom: the forward-end "
           "caller and the test-only wrapper that resolves a logical slot first, then "
           "the two acquire checks that return CONVERTED_FALSE when the 16 row bits are "
           "not all set or the block bit is already set (so a repeated call is "
           "harmless). Part b continues with the geometry dispatch.")
    # the figure's own "Colour and font scheme" (STYLE.md): only the styles it uses
    legend = [
        ("ctx", "grey box, thin grey outline: a caller in another file: "
                "convert_pending_k_blocks (model.hpp) and the test callers of "
                "k_block_to_vnni"),
        ("box", "white box, ink outline: the functions k_block_to_vnni and "
                "k_block_to_vnni_at (name in bold monospace, description in sans-serif "
                "under it), and the box of the two acquire checks"),
        ("grey outline: the early return CONVERTED_FALSE when either check fails",
         "#fff", C["muted"], False, False),
        ("rows", "green squares: the 16 k_rows_saved_ bits of block 1 (bits 16..31), "
                 "all set; 'all set' in green"),
        ("blk", "pink square: a k_vnni_blocks_ bit that is set (bit 0, block 0); "
                "'clear' in pink names the bit check 2 reads"),
        ("bit_clear", "white square: a k_vnni_blocks_ bit that is clear (bits 1..3; "
                      "bit 1 = block 1, not converted yet)"),
        ("ink outline around a square: bit 1 (block 1), the bit check 2 reads",
         "none", C["ink"], False, False),
        ("arrow", "ink arrow: a call (caller -> k_block_to_vnni -> k_block_to_vnni_at) "
                  "or the next step; its label says how many"),
        ("arrow_muted", "grey arrow: either check fails -> return CONVERTED_FALSE"),
        "font_mono",
        ("font_sans", "sans-serif = prose: descriptions, labels, captions; the bold line "
                      "'new; [main thread] only, ...' inside k_block_to_vnni_at = this PR "
                      "adds that function, with the thread it runs on"),
        "font_cite",
    ]
    return figure(fid, W, H, "The in-place conversion of one block (part a): entry points "
                  "and the two acquire checks", "".join(o), cap, boxes=boxes,
                  legend=legend)


def fig_b():
    fid = "kv_cache-d6b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "blk": C["blk"]})]
    _title(o)
    o.append(text(16, 30, "from part a: both checks passed; converted = CONVERTED_FALSE so "
                  "far [2224]", 9, fill=C["ink"], weight=600))

    # ---- row E: the geometry dispatch ------------------------------------------------
    wy, wh = 40, 58
    o.append(fn_cell(16, wy, 688, wh, "k_with_storage_geometry(storage_offset, f)", [
        "calls f.template operator()<geometry>() with the geometry of the storage slot: "
        "the slot's",
        "declared geometry, or the primary geometry for the EAGLE storage"],
        "kv_cache.hpp:2520-2532", "new (unit C3)"))
    boxes.append(("k_with_storage_geometry", "kv_cache.hpp:2520-2532"))

    # ---- row F: the lambda, two geometries --------------------------------------------
    ly, lh = 124, 190
    o.append(arrow(fid, "ink", [(120, wy + wh), (120, ly)], C["ink"], 1.4))
    o.append(text(128, 116, "1 call -> f once, with the matching geometry", 9,
                  fill=C["ink"], weight=600))
    o.append(rect(16, ly, 688, lh, "#fff", C["line"], 1, 5))
    o.append(text(24, ly + 16, "the lambda [&]<kv_geometry geometry>(): called once, "
                  "under the slot's geometry", 10.5, weight=600))
    o.append(cite(700, ly + lh - 4, "kv_cache.hpp:2225-2233"))
    boxes.append(("kv_geometry lambda ([&]<kv_geometry geometry>())",
                  "kv_cache.hpp:2225-2233"))
    # left branch: VNNI geometry
    vx, vy, vw, vh = 24, ly + 24, 448, lh - 40
    o.append(rect(vx, vy, vw, vh, "#fff", C["vnni"], 1.2, 4))
    o.append(text(vx + 8, vy + 15, "if constexpr (k_vnni::layout_on<geometry.head_size>)",
                  9.5, mono=True, fill=C["vnni"], weight=600))
    o.append(text(vx + 8, vy + 29, "for (kv_head = 0; kv_head < geometry.n_kv_heads; "
                  "++kv_head)", 9, mono=True))
    o.append(text(vx + 20, vy + 41, fit("block_to_vnni(kv_block_at_storage<geometry>"
                                        "(storage_offset, kv_head)", 9, vw - 28, True,
                                        "loop body"), 9, mono=True))
    o.append(text(vx + 96, vy + 53, ".k.as_view(), c);", 9, mono=True))
    # before -> after of block 1 in KV head h's plane
    cy1 = vy + 62
    o.append(block_cell(vx + 16, cy1, 120, 34, "pend", "block 1", 10))
    o.append(block_cell(vx + 296, cy1, 120, 34, "vnni", "block 1", 10))
    o.append(arrow(fid, "vnni", [(vx + 136, cy1 + 17), (vx + 294, cy1 + 17)],
                   C["vnni"], 1.6))
    gm = vx + 216
    o.append(text(gm, cy1 + 9, "block_to_vnni", 9, "middle", True, fill=C["vnni"],
                  weight=700))
    o.append(text(gm, cy1 + 28, "in place, 4 KiB, via a stack", 8.5, "middle"))
    o.append(text(gm, cy1 + 38, "copy of the rows", 8.5, "middle"))
    o.append(text(vx + 76, cy1 + 48, "complete, may wait", 9.5, "middle", fill=C["pend"]))
    o.append(text(vx + 356, cy1 + 48, "converted: VNNI", 9.5, "middle", fill=C["vnni"]))
    o.append(text(vx + 8, cy1 + 66, fit("1 call -> geometry.n_kv_heads planes: one "
                                        "block_to_vnni per KV head's block 1", 9,
                                        vw - 16, False, "how many"), 9, fill=C["vnni"],
                  weight=600))
    o.append(text(vx + 8, cy1 + 80, "converted = CONVERTED_TRUE", 9.5, mono=True))
    o.append(cite(vx + vw - 4, vy + vh - 4,
                  "kv_cache.hpp:2226-2232; tensor/k_vnni.hpp:494-509"))
    boxes += [("block 1: complete, may wait -> converted: VNNI (per KV head)",
               "kv_cache.hpp:684-685 (may wait for its conversion); 2618-2622 (converted)"),
              ("block_to_vnni", "tensor/k_vnni.hpp:494-509"),
              ("page::kv_block_at_storage", "kv_cache.hpp:2656-2660"),
              ("k_vnni_tensor::as_view", "tensor/k_vnni.hpp:214-227")]
    # right branch: row-major geometry
    rx, rw, rh = 488, 208, 100       # the box is as tall as its text
    o.append(rect(rx, vy, rw, rh, "#fff", C["muted"], 1, 4, "4 3"))
    o.append(text(rx + 8, vy + 15, "row-major geometry", 9.5, mono=True, fill=C["muted"],
                  weight=600))
    for i, s in enumerate(["the if constexpr has no else:",
                           "nothing runs; converted stays",
                           "CONVERTED_FALSE.",
                           "\"A row-major slot never",
                           "converts.\""]):
        o.append(text(rx + 8, vy + 31 + i * 13, s, 9.5, fill=C["muted"]))
    o.append(cite(rx + rw - 4, vy + rh - 4, "kv_cache.hpp:2206-2207, 2226-2232"))
    boxes.append(("geometry without layout_on (a row-major slot): nothing runs",
                  "kv_cache.hpp:2226-2232, 2206-2207"))

    # ---- row G: publish the block bit --------------------------------------------------
    py, ph = 348, 90
    o.append(arrow(fid, "blk", [(120, ly + lh), (120, py)], C["blk"], 1.4))
    o.append(text(128, 340, "after the last KV head: the bits are per slot, not per KV head "
                  "[707-709]", 9, fill=C["blk"], weight=600))
    o.append(rect(16, py, 688, ph, "#fff", C["blk"], 1.2, 5))
    o.append(text(24, py + 16, fit("if (converted) k_vnni_blocks_[state_ix].fetch_or(cbit, "
                                   "std::memory_order_release);", 9.5, 672, True,
                                   "fetch_or"), 9.5, mono=True, weight=600))
    o.append(text(24, py + 36, "worked example: k_vnni_blocks_[5]", 9.5, fill=C["muted"]))
    ex = _blk_bits(o, 210, py + 27, "1000")
    o.append(text(ex + 6, py + 36, "->", 9.5, mono=True))
    ex = _blk_bits(o, ex + 26, py + 27, "1100", hi=1, hi_word="bit 1 set (new)")
    o.append(text(ex + 10, py + 36, "0b0001 -> 0b0011", 9.5, mono=True))
    o.append(text(24, py + 54, "return converted (CONVERTED_TRUE)", 9.5, mono=True))
    o.append(text(24, py + 70, "a reader must not see the block bit before every head holds "
                  "the layout; readers load it with acquire (k_block_is_vnni, k_vnni_blocks)",
                  8.5, fill=C["muted"]))
    o.append(cite(700, py + ph - 4, "kv_cache.hpp:2234-2235"))
    boxes += [("k_vnni_blocks_ fetch_or (release) after the last head",
               "kv_cache.hpp:2234; Note [K VNNI storage] 707-709"),
              ("k_block_is_vnni / k_vnni_blocks (acquire readers)",
               "kv_cache.hpp:2513-2518, 2126-2135")]

    # ---- row H: the worked example after the forward end ------------------------------
    hy = 460
    o.append(text(16, hy, "worked example after the forward end (B1 shows the state "
                  "before: block 1 'complete, may wait')", 10.5, weight=600))
    o.append(block_row(16, hy + 8, 160, 34, ["vnni", "vnni", "rm", "empty"],
                       ["VNNI (converted)", "VNNI (converted), new", "9 rows, row-major",
                        "no row bit"], gap=16, size=10))
    boxes.append(("k_rows_saved_ / k_vnni_blocks_ of the worked example (page 7, slot 5)",
                  "kv_cache.hpp:2608-2622; B1 of this page"))
    H = hy + 8 + 34 + 40
    cap = ("Updates B4 (part b): the rest of k_block_to_vnni_at after both checks pass. "
           "Read it top to bottom: the block_to_vnni loop over every KV head's plane "
           "under the slot's geometry (a row-major slot runs nothing), and the release "
           "fetch_or that publishes block bit 1 after the last head. The bottom row is "
           "the worked example after the forward end: k_vnni_blocks_[5] went from "
           "0b0001 to 0b0011.")
    # the figure's own "Colour and font scheme" (STYLE.md): only the styles it uses
    legend = [
        ("box", "white box, ink outline: the function k_with_storage_geometry (name in "
                "bold monospace, description in sans-serif under it)"),
        ("lane", "white frame, thin grey outline: the lambda [&]<kv_geometry geometry>() "
                 "that k_with_storage_geometry calls once; it holds the two geometry cases"),
        ("white box, blue outline: the if constexpr branch for a VNNI geometry "
         "(k_vnni::layout_on), the block_to_vnni loop; blue text = the VNNI side",
         "#fff", C["vnni"], False, False),
        ("deleted", "grey dashed box: the row-major geometry, where the if constexpr has "
                    "no else and nothing runs"),
        ("white box, pink outline: the release fetch_or of the block bit into "
         "k_vnni_blocks_[state_ix]; pink text = the block bits",
         "#fff", C["blk"], False, False),
        ("pend", "orange-red dashed block: block 1 before block_to_vnni, complete and may "
                 "wait (16 row bits set, block bit clear); orange-red text = the words "
                 "complete, may wait"),
        ("vnni", "blue block: a block in the VNNI layout (block 1 after block_to_vnni; "
                 "blocks 0 and 1 of the worked example after the forward end)"),
        ("rm", "orange block: block 2 of the worked example, 9 rows saved row-major"),
        ("empty", "grey dashed block: block 3 of the worked example, no row bit set"),
        ("blk", "pink square: a k_vnni_blocks_[5] bit that is set (bit 0 before the "
                "fetch_or; bits 0 and 1 after)"),
        ("bit_clear", "white square: a k_vnni_blocks_[5] bit that is clear (bits 1..3 "
                      "before; bits 2..3 after)"),
        ("ink outline around a square: bit 1 (block 1), the bit the fetch_or sets",
         "none", C["ink"], False, False),
        ("arrow", "ink arrow: k_with_storage_geometry calls the lambda f once; its label "
                  "says how many"),
        ("blue arrow: block_to_vnni, block 1 from row-major to the VNNI layout in place",
         "arrow", C["vnni"]),
        ("pink arrow: after the last KV head, to the release fetch_or of the block bit",
         "arrow", C["blk"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new (unit C3)' = k_with_storage_geometry is added by this PR"),
    ]
    return figure(fid, W, H, "The in-place conversion of one block (part b): the loop over "
                  "KV heads and the block bit", "".join(o), cap, boxes=boxes,
                  legend=legend)


def figs():
    return [fig_a(), fig_b()]
