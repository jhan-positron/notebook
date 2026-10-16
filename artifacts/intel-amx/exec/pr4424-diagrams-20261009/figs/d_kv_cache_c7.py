"""Change diagrams D7a / D7b of the PR 4424 page for h/tron/models/kv_cache.hpp:
unit c7, "Row accessors follow the block's layout: set_k_row, get_k_row,
k_row_if_row_major" (head lines 2238-2263 and 2286-2349, new).
  d7a: the callers, the typed row, the three accessors, the compile-time slot
       test and the block-bit read.
  d7b: the two paths (row-major tail block, VNNI column) and the worked
       example.

Every label and citation comes from facts/kv_cache.json (kv_cache-data-24,
-46; kv_cache-function-14, -16, -17, -19, -21, -29; kv_cache-seq-2, -29, -30;
kv_cache-rule-14) or from the head files themselves. Line numbers without a
file name are head line numbers of kv_cache.hpp.
"""
import sys

from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, line,
                         lines, marker_defs, rect, text, text_width)
from base_kv_cache import (BLOCKS_EXAMPLE, EXAMPLE, block_row, caller_cell,
                           vnni_index)

BASE = ("Updates B3: rows 1 and 6 (set_k_row; k_row_if_row_major and get_k_row) "
        "are redrawn as one decision tree: the caller's typed row, the compile-time "
        "slot test and the acquire load of the block bit in k_block_is_vnni (part "
        "a), then the two k_vnni.hpp operations each function can take, with the "
        "worked example's block 2 (row-major, i_page 37) and block 0 (converted, "
        "i_page 5) (part b).")

W = 700
INDEX_5_70 = vnni_index(5, 70)          # k_vnni::index(5, 70) = 4202
assert INDEX_5_70 == 4202 and EXAMPLE["rm_elem"] == 3200


def _w(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _op_cell(o, boxes, x, y, w, h, name, body, ref, fill, stroke):
    """One k_vnni.hpp operation taken by one accessor: name line (mono, bold),
    up to 3 plain lines, citation."""
    _w(name, 10, w - 14, True, f"op {name}")
    for s in body:
        _w(s, 9, w - 14, False, f"op body {name}")
    o.append(rect(x, y, w, h, fill, stroke, 1.2, 4))
    o.append(text(x + 7, y + 14, name, 10, mono=True, weight=700))
    o.append(lines(x + 7, y + 27, body, 9, 11))
    o.append(cite(x + w - 4, y + h - 4, ref))
    boxes.append((name, ref))


def fig_a():
    fid = "kv_cache-d7a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"],
                           "muted": C["muted"]})]
    o.append(text(8, 13, "the three row accessors of a VNNI slot: one shape, one block-bit "
                  "read, two paths (new unless marked)", 10.5, weight=600))

    # ---- row 1: the callers (other files) [thread] ------------------------------
    cy, ch = 22, 110
    cw = 338
    caller_a = ["model.hpp store_k_block: a run shorter than 16",
                "tokens -> set_k_row per token and KV head; 'set_k_row",
                "decides' [main or a main helper of the window]",
                "1 run of n < 16 tokens -> n x n_kv_heads set_k_row calls",
                "[model.hpp:3304-3311]"]
    caller_b = ["full.hpp k_head_fn (FPGA staging, gof::populate):",
                "k_row_if_row_major first; row.valid() false ->",
                "get_k_row into dest [attention workers (help_drain_gof), main]",
                "1 GOF -> gof_tokens = 4 tokens x n_kv_heads k_head_fn calls;",
                "set_position then copies the rows into the staging buffer,",
                "bytes unchanged [gof.cpp:206-219; gof.hpp:34]"]
    for s in caller_a + caller_b:
        _w(s, 9.5, cw - 14, False, "caller")
    o.append(caller_cell(8, cy, cw, ch, caller_a, "model.hpp:3300-3318"))
    o.append(caller_cell(354, cy, cw, ch, caller_b, "full.hpp:2747-2770"))
    o.append(text(16, cy + ch - 18, "row-major slots keep page::k(...).set [model.hpp:3259]",
                  8.5, fill=C["muted"]))
    before = "before: page::k(slot, kv_head, off).data [full.hpp base 2747-2752]"
    _w(before, 8.5, cw - 16, False, "before line")
    o.append(text(362, cy + ch - 18, before, 8.5, fill=C["gone"]))
    boxes.append(("store_k_block (caller)", "model.hpp:3232-3344; the row loop 3300-3318"))
    boxes.append(("k_head_fn (caller)", "full.hpp:2747-2770; gof.hpp:58-78"))
    boxes.append(("gof::populate (1 GOF -> gof_tokens x n_kv_heads k_head_fn calls, then "
                  "set_position)", "gof.cpp:206-219; gof_tokens = 4 at gof.hpp:34"))

    # ---- row 2: the typed transfer row -------------------------------------------
    ry, rh = cy + ch + 28, 62
    o.append(arrow(fid, "ink", [(100, cy + ch), (100, ry)], C["ink"], 1.4))
    o.append(text(108, cy + ch + 13, "1 call -> 1 row in: k_source_row(kout)", 9,
                  fill=C["ink"], weight=600))
    o.append(text(108, cy + ch + 24, "[model.hpp:3310-3311]", 8.5, mono=True, fill=C["cite"]))
    o.append(arrow(fid, "ink", [(600, cy + ch), (600, ry)], C["ink"], 1.4))
    o.append(text(592, cy + ch + 13, "1 call -> 1 row out: k_destination_row(dest)", 9,
                  "end", fill=C["ink"], weight=600))
    o.append(text(592, cy + ch + 24, "[full.hpp:2765-2766]", 8.5, "end", True,
                  fill=C["cite"]))
    rt = "const_k_row_view<head_size, Aligned, Dma> (in) / k_row_view<head_size, Aligned, Dma> (out)"
    _w(rt, 10, W - 24, True, "row view title")
    rs = ["one token's head_size = 128 bf16 in dimension order (256 B), never packed storage; "
          "the caller's Aligned and Dma",
          "flags travel with the row: the packed store reads it with unaligned loads, the "
          "packed load writes it with unaligned stores"]
    for s in rs:
        _w(s, 9, W - 24, False, "row view sub")
    o.append(label_box(8, ry, W - 16, rh, rt, rs, "#fff", C["ink"], 10,
                       ref="tensor/k_vnni.hpp:249-258; kv_cache.hpp:2241-2242, 2287"))
    boxes.append(("const_k_row_view / k_row_view",
                  "tensor/k_vnni.hpp:249-258; the unaligned-access notes at "
                  "kv_cache.hpp:2241-2242 and 2287"))

    # ---- row 3: the three accessors; the typed row fans out to all three -----------
    fy, fh, fw, fg = ry + rh + 34, 64, 224, 6
    fns = [
        ("set_k_row", ["layout-agnostic K row store: the token's",
                       "row into the layout its block holds"], "kv_cache.hpp:2238-2263"),
        ("get_k_row", ["layout-agnostic K row load, the inverse of",
                       "set_k_row, into a writable typed row"], "kv_cache.hpp:2286-2307"),
        ("k_row_if_row_major", ["the token's row in place when its block is",
                                "row-major; an invalid view when converted"],
         "kv_cache.hpp:2332-2349"),
    ]
    fxs = []
    for i, (name, desc, ref) in enumerate(fns):
        x = 8 + i * (fw + fg)
        fxs.append(x + fw / 2)
        for d in desc:
            _w(d, 9, fw - 16, False, f"fn {name}")
        o.append(fn_cell(x, fy, fw, fh, name, desc, ref, "new", size=11))
        boxes.append((name, ref))
    bar = ry + rh + 18
    o.append(line(350, ry + rh, 350, bar, C["ink"], 1.4))
    o.append(line(fxs[0], bar, fxs[2], bar, C["ink"], 1.4))
    for cx in fxs:
        o.append(arrow(fid, "ink", [(cx, bar), (cx, fy - 2)], C["ink"], 1.4))
    o.append(text(358, ry + rh + 11, "1 row per call, to each of the three", 9,
                  fill=C["ink"], weight=600))

    # ---- row 4: the compile-time slot test (a bus under the three cells) -----------
    by = fy + fh + 14
    for cx in fxs:
        o.append(line(cx, fy + fh, cx, by, C["ink"], 1.2))
    o.append(line(fxs[0], by, 640, by, C["ink"], 1.2))
    ky, kh = by + 30, 72
    o.append(arrow(fid, "ink", [(198, by), (198, ky)], C["ink"], 1.4))
    o.append(text(206, by + 12, "if constexpr (k_vnni::layout_on<geometry.head_size>)", 8.5,
                  mono=True, fill=C["ink"], weight=700))
    o.append(text(206, by + 23, "[kv_cache.hpp:2252, 2296; requires clause 2338-2339]", 8.5,
                  mono=True, fill=C["cite"]))
    o.append(arrow(fid, "muted", [(640, by), (640, ky - 8)], C["muted"], 1.4))
    o.append(text(648, by + 14, "else", 9, fill=C["muted"], weight=600))
    # the block-bit read
    kt = "k_block_is_vnni(k_state_ix(slot), i_page)"
    ks = ["acquire load of k_vnni_blocks_[state_ix]; bit c = i_page / 16",
          "k_state_ix: slot.i, or layout_t::n_slots for slot 0 (EAGLE view)",
          "one load per call; none of the three writes a bit"]
    _w(kt, 10.5, 372, True, "check title")
    for s in ks:
        _w(s, 9.5, 372, False, "check sub")
    o.append(label_box(8, ky, 380, kh, kt, ks, "#fff", C["ink"], 10.5,
                       ref="kv_cache.hpp:2513-2518, 2499-2505"))
    boxes.append(("k_block_is_vnni", "kv_cache.hpp:2513-2518"))
    boxes.append(("k_state_ix", "kv_cache.hpp:2499-2505"))
    # the row-major slot (else branch)
    gx, gw = 410, 280
    gt = "else: a row-major slot (compile time)"
    gs = ["set_k_row / get_k_row: std::memcpy of head_size *",
          "sizeof(bf16) through kv_block::k_at(i_page)",
          "k_row_if_row_major: not compiled for such a slot",
          "(requires k_vnni::layout_on<geometry.head_size>)"]
    _w(gt, 10, gw - 14, True, "grey title")
    for s in gs:
        _w(s, 9, gw - 14, False, "grey sub")
    o.append(rect(gx, ky - 8, gw, kh + 8, C["soft"], C["muted"], 1.2, 4))
    o.append(text(gx + 7, ky + 6, gt, 10, mono=True, weight=700))
    o.append(lines(gx + 7, ky + 19, gs, 9, 11))
    o.append(cite(gx + gw - 4, ky + kh - 4, "kv_cache.hpp:2259-2261, 2303-2305, 2338-2339"))
    boxes.append(("row-major slot: memcpy through kv_block::k_at",
                  "kv_cache.hpp:2259-2261, 2303-2305 (k_at: 3032-3038); "
                  "k_row_if_row_major's requires clause 2338-2339"))
    # the two outcomes of the one acquire load, side by side under its box
    ey = ky + kh
    o.append(arrow(fid, "rm", [(60, ey), (60, ey + 24)], C["rm"], 1.6))
    o.append(text(68, ey + 19, "false: block bit clear -> part b, orange", 9.5,
                  fill=C["rm"], weight=700))
    o.append(arrow(fid, "vnni", [(290, ey), (290, ey + 24)], C["vnni"], 1.6))
    o.append(text(298, ey + 19, "true: block bit set -> part b, blue", 9.5,
                  fill=C["vnni"], weight=700))
    H = ey + 32
    cap = ("Updates B3 (part a): rows 1 and 6 of the function model (set_k_row; "
           "k_row_if_row_major and get_k_row) drawn as one decision tree beside their "
           "code. Read it top down: the caller hands one typed 256-byte row, and the "
           "slot test is decided at compile time. Then, for a VNNI slot, every call "
           "makes one acquire load of the block bit in k_block_is_vnni and takes the "
           "orange path (part b: 4 whole lines, or the row in place) or the blue path "
           "(64 lines, or an invalid view that sends the caller to get_k_row). A "
           "row-major slot takes neither path: set_k_row and get_k_row memcpy through "
           "kv_block::k_at without any load [kv_cache.hpp:2259-2261, 2303-2305].")
    legend = [
        ("ctx", "grey box, thin grey outline: a caller in another file, store_k_block "
                "(model.hpp) and k_head_fn (full.hpp)"),
        ("box", "white box, ink outline: the typed row const_k_row_view / k_row_view, the "
                "three accessors set_k_row, get_k_row, k_row_if_row_major, and the block-bit "
                "read k_block_is_vnni; name in bold monospace, description under it"),
        ("grey box, darker grey outline: the else branch, a row-major slot decided at "
         "compile time (set_k_row / get_k_row memcpy through kv_block::k_at)",
         C["soft"], C["muted"], False, False),
        ("arrow", "ink arrow: one row per call, caller -> typed row -> each of the three "
                  "accessors; the slot test if constexpr (...) -> k_block_is_vnni"),
        ("arrow_muted", "grey arrow: else, the row-major slot (compile time)"),
        ("orange arrow and orange label: false, block bit clear -> the row-major path "
         "of part b", "arrow", C["rm"]),
        ("blue arrow and blue label: true, block bit set -> the VNNI path of part b",
         "arrow", C["vnni"]),
        ("red text: before, the base code of the caller k_head_fn, "
         "page::k(slot, kv_head, off).data", "text", C["gone"]),
        ("font_mono", "monospace = a name or a value from the code: the accessors, the "
                      "row view types, the slot test, k_block_is_vnni"),
        ("font_sans", "sans-serif = prose: the callers' lines, the descriptions, the "
                      "arrow labels"),
        ("font_cite", "small grey monospace = the lines that define the box "
                      "(kv_cache.hpp:2238-2263, model.hpp:3300-3318, ...)"),
        ("font_tag", "bold 'new' = the three accessors are added by this PR"),
    ]
    return figure(fid, W, H, "Row accessors follow the block's layout (part a): the typed "
                  "row, the slot test and the block-bit read", "".join(o), cap,
                  boxes=boxes, legend=legend)


def fig_b():
    fid = "kv_cache-d7b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"]})]
    o.append(text(8, 13, "from part a: the block bit of the token's block, read with "
                  "acquire order by k_block_is_vnni", 10.5, weight=600))
    # ---- row 5: the two paths --------------------------------------------------------
    hy, hh = 44, 22
    lx, rx, colw = 8, 356, 336
    o.append(text(lx, hy - 8, "false: block bit clear", 9.5, fill=C["rm"], weight=700))
    o.append(text(rx, hy - 8, "true: block bit set", 9.5, fill=C["vnni"], weight=700))
    o.append(rect(lx, hy, colw, hh, C["rm_fill"], C["rm"], 1.2, 4))
    o.append(text(lx + colw / 2, hy + 15, "row-major tail block: 4 whole 64-byte lines per token",
                  10, "middle", weight=600))
    o.append(rect(rx, hy, colw, hh, C["vnni_fill"], C["vnni"], 1.2, 4))
    o.append(text(rx + colw / 2, hy + 15, "VNNI column: the token's 64 pair slots, 64 lines",
                  10, "middle", weight=600))
    boxes.append(("row-major tail block (block bit clear)",
                  "Note [Row-major tail block] (tensor/k_vnni.hpp:437-456); kv_cache.hpp:720-724"))
    boxes.append(("VNNI column (block bit set)",
                  "tensor/k_vnni.hpp:30-32, 344-348; kv_cache.hpp:2163 (\"the VNNI column\")"))
    oy, oh, og = hy + hh + 6, 70, 6
    left_ops = [
        ("set_k_row -> store_row_major(plane, i_page, row)",
         ["memcpy of 256 B to row_major_row(plane, i_page): 4 whole 64-byte",
          "lines, the same lines the row-major layout's store writes"],
         "tensor/k_vnni.hpp:474-482; kv_cache.hpp:2247-2257"),
        ("get_k_row -> load_row_major(plane, i_page, row)",
         ["memcpy of 256 B from row_major_row(plane, i_page) into the",
          "caller's row: 4 lines (the inverse of store_row_major)"],
         "tensor/k_vnni.hpp:484-492; kv_cache.hpp:2291-2301"),
        ("k_row_if_row_major -> row_major_row(plane, i_page)",
         ["the row in place, no copy: a typed row view of head_size",
          "contiguous bf16 inside the block's own panels, valid as",
          "long as no writer touches the block"],
         "tensor/k_vnni.hpp:458-472; kv_cache.hpp:2341-2348, 2332-2336"),
    ]
    right_ops = [
        ("set_k_row -> store_row(plane, i_page, row)",
         ["4 scatters of 16 dwords (one dimension pair each), one per",
          "dimension step: 4 bytes into each of 64 lines; only this",
          "token's 64 pair slots are written"],
         "tensor/k_vnni.hpp:344-362; kv_cache.hpp:2247-2255"),
        ("get_k_row -> load_row(plane, i_page, row)",
         ["4 gathers of 16 dwords out of the token's VNNI column into",
          "the caller's row (the inverse of store_row); the row is",
          "written with unaligned stores"],
         "tensor/k_vnni.hpp:364-381; kv_cache.hpp:2291-2299"),
        ("k_row_if_row_major -> k_row_view<head_size>{}",
         ["an invalid view (row.valid() false): a token's values are",
          "not contiguous in a converted block; the caller gathers",
          "that row with get_k_row instead"],
         "kv_cache.hpp:2345-2346, 811-813; full.hpp:2764-2766"),
    ]
    for i, (name, body, ref) in enumerate(left_ops):
        _op_cell(o, boxes, lx, oy + i * (oh + og), colw, oh, name, body, ref, "#fff", C["rm"])
    for i, (name, body, ref) in enumerate(right_ops):
        _op_cell(o, boxes, rx, oy + i * (oh + og), colw, oh, name, body, ref, "#fff",
                 C["vnni"])
    oend = oy + 3 * oh + 2 * og

    # ---- row 6: the worked example ------------------------------------------------------
    wy = oend + 12
    o.append(line(8, wy, W - 8, wy, C["line"]))
    o.append(text(8, wy + 16, "worked example: page 7, state entry 5 (slot 5), "
                  "k_vnni_blocks_[5] = 0b0001; the path of two page offsets", 10.5,
                  weight=600))
    bw, bg, bh = 160, 8, 26
    bity = wy + 24
    o.append(text(8, bity + 10, "k_vnni_blocks_[5]", 9.5, mono=True, fill=C["blk"]))
    for c in range(4):
        gx0 = 8 + c * (bw + bg)
        on = BLOCKS_EXAMPLE[c] == "1"
        o.append(rect(gx0 + bw - 58, bity, 11, 11, C["blk_fill"] if on else C["empty_fill"],
                      C["blk"] if on else C["empty"], 1, 1))
        o.append(text(gx0 + bw - 43, bity + 9.5, f"bit {c} = {BLOCKS_EXAMPLE[c]}", 9,
                      mono=True, fill=C["muted"]))
    rowy = bity + 18
    o.append(block_row(8, rowy, bw, bh, gap=bg, size=10))
    boxes.append(("k_vnni_blocks_[5] (worked example)", "kv_cache.hpp:2618-2622"))
    boxes.append(("block 0..3 of the worked example", "kv_cache.hpp:2126-2128; B1"))
    iy = rowy + bh + 42
    ex0 = ["i_page 5: bit 0 set ->", "column 5 of panels (s, 0),",
           "s = 0..3: 64 lines, 4 B each;", f"k_vnni::index(5, 70) = {INDEX_5_70}"]
    ex2 = ["i_page 37: bit 2 clear ->", f"row_major_row(plane, 37) =",
           f"element {EXAMPLE['rm_elem']}: panel (1,2) #6,", "row 1: 4 whole lines, 256 B"]
    for s in ex0 + ex2:
        _w(s, 9, bw, True, "example line")
    o.append(lines(8, iy, ex0, 9, 11, mono=True, fill=C["vnni"], weight=600))
    o.append(lines(8 + 2 * (bw + bg), iy, ex2, 9, 11, mono=True, fill=C["rm"], weight=600))
    o.append(cite(8 + 2 * (bw + bg), iy + 4 * 11 + 2,
                  "tensor/k_vnni.hpp:30-31, 132-141, 458-472", "start"))
    o.append(lines(8 + (bw + bg), iy, ["bit 1 clear: a row saved", "again goes row-major",
                                       "(the block may still wait)"], 9, 11, fill=C["muted"]))
    o.append(lines(8 + 3 * (bw + bg), iy, ["bit 3 clear: the first", "row goes row-major"],
                   9, 11, fill=C["muted"]))

    # ---- notes ----------------------------------------------------------------------------
    ny = iy + 4 * 11 + 22
    notes = [
        "none of the three writes a bit: the saved-row bit is the caller's (note_k_row_saved, "
        "C5) [kv_cache.hpp:2242-2243]",
        "the uniform-geometry forms of set_k_row / get_k_row forward to "
        "layout_t::primary_geometry [kv_cache.hpp:2309-2330]",
    ]
    for s in notes:
        _w(s, 9.5, W - 16, False, "note")
    o.append(lines(8, ny, notes, 9.5, 12))
    boxes.append(("uniform-geometry forms of set_k_row / get_k_row", "kv_cache.hpp:2309-2330"))
    H = ny + 12 + 8
    cap = ("Updates B3 (part b): the two paths of the three accessors, one column per "
           "value of the block bit read in part a. The orange column is the row-major "
           "tail block: 4 whole lines per token, or the row in place. The blue column "
           "is the VNNI column: 64 lines per token, or an invalid view that sends the "
           "caller to get_k_row. The worked example at the bottom shows page offset 37 "
           "taking the orange path (block 2, bit clear) and page offset 5 taking the "
           "blue path (block 0, converted).")
    legend = [
        ("rm", "orange: the row-major tail block (block bit clear): the left column's "
               "header and block 2 of the worked example, 9 rows row-major; orange text = "
               "the path of i_page 37 under block 2"),
        ("white box, orange outline: the k_vnni.hpp operation each accessor takes on the "
         "orange path: store_row_major, load_row_major, row_major_row",
         "#fff", C["rm"], False, False),
        ("vnni", "blue: the VNNI column (block bit set): the right column's header and "
                 "block 0 of the worked example, converted; blue text = the path of "
                 "i_page 5 under block 0"),
        ("white box, blue outline: the k_vnni.hpp operation each accessor takes on the "
         "blue path: store_row, load_row, the invalid k_row_view<head_size>{}",
         "#fff", C["vnni"], False, False),
        ("pend", "orange-red dashed: block 1 of the worked example, complete, may wait "
                 "(16 row bits set, bit 1 clear)"),
        ("empty", "grey dashed: block 3 of the worked example, no row bit"),
        ("blk", "pink square: k_vnni_blocks_[5] bit 0 = 1, the converted-block bit of "
                "block 0; pink text = the label k_vnni_blocks_[5]"),
        ("bit_clear", "white square, grey outline: k_vnni_blocks_[5] bits 1, 2, 3 = 0, a "
                      "converted-block bit that is clear"),
        ("font_mono", "monospace = a name or a value from the code: the operation names, "
                      "block 0..3, the bits, the lines of the two page offsets"),
        ("font_sans", "sans-serif = prose: the column headers, the operation descriptions, "
                      "the state words, the notes"),
        ("font_cite", "small grey monospace = the lines that define the box "
                      "(tensor/k_vnni.hpp:474-482; kv_cache.hpp:2247-2257, ...)"),
    ]
    return figure(fid, W, H, "Row accessors follow the block's layout (part b): the two "
                  "paths and the worked example", "".join(o), cap, boxes=boxes,
                  legend=legend)


def figs():
    return [fig_a(), fig_b()]
