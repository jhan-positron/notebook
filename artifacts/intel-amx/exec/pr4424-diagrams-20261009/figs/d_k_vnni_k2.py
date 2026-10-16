"""Change diagram of unit k2 of the k_vnni.hpp page: the layout gate
k_vnni::layout_on<head_size> (head lines 119-131) and who branches on it.

Two figures, because one table of every consumer does not fit a legible
half-width column:
  k_vnni-d2a: the gate (its two inputs, its answer) and its consumers in
              kv_cache.hpp (page, kv_block, book), one row each;
  k_vnni-d2b: its consumers in model.hpp, self_attention.hpp and full.hpp.
Each row = the consumer's name, one line on what it does, the line of its
branch, and what it does when the gate is true (VNNI slot, blue) and when it
is false (row-major slot, orange). A white cell with a grey (C['muted'])
dashed outline = the function does not exist on that side (a requires
clause); C['empty'] stays reserved for 'no row saved'.

Facts: facts/k_vnni.json (k_vnni-data-19, k_vnni-function-3,
k_vnni-sequencing-37, k_vnni-glossary-2) and the cited lines of the worktree
at head 9d5c7a389b. Line numbers are head line numbers.
"""
import sys

from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, line, lines,
                         marker_defs, rect, text, text_width)

BASE = ("Updates B3: the layout_on<head_size> cell of the first band expands into "
        "a two-column table of its consumers in kv_cache.hpp, model.hpp, "
        "self_attention.hpp and full.hpp, one row per consumer, with what it does "
        "when the gate is true (VNNI slot, blue) and when it is false (row-major "
        "slot, orange).")

W = 700
NX, NW = 8, 244      # the consumer column: a B3 fn_cell (name, description, cite)
TX, TW = 258, 210    # the true column (VNNI slot)
FX, FW = 472, 220    # the false column (row-major slot)
RH, RG = 48, 4       # row height (fn_cell: name, one line, cite) and gap


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _cell(o, x, y, w, h, lines_, kind, where):
    """One branch cell: lines_ = what the consumer does on that side, or None
    when the function does not exist on that side (requires clause)."""
    if lines_ is None:
        o.append(rect(x, y, w, h, "#fff", C["muted"], 1, 3, "4 3"))
        req = "requires(!layout_on)" if kind == "vnni" else "requires(layout_on)"
        o.append(lines(x + 6, y + 21, ["does not exist:", req], 9, 11, fill=C["muted"]))
        return
    o.append(rect(x, y, w, h, C[kind + "_fill"], C[kind], 1, 3))
    n = len(lines_)
    y0 = y + h / 2 - (n - 1) * 5.5 + 3.5
    for s in lines_:
        _w(s, 9, w - 10, where=f"{where} {kind}")
    o.append(lines(x + 6, y0, lines_, 9, 11))


def _row(o, boxes, y, name, desc, ref, t, f):
    """One consumer row: a B3-style fn_cell (name, what it does, its branch
    line) and the two branch cells."""
    _w(name, 10.5, NW - 16, True, f"name {name}")
    _w(desc, 8.5, NW - 16, False, f"desc {name}")
    _w(ref, 8.5, NW - 8, True, f"cite {name}")
    o.append(fn_cell(NX, y, NW, RH, name, desc, ref, size=10.5))
    boxes.append((name, ref))
    _cell(o, TX, y, TW, RH, t, "vnni", name)
    _cell(o, FX, y, FW, RH, f, "rm", name)
    return y + RH + RG


def _group(o, y, s):
    _w(s, 10.5, W - 16, where="group")
    o.append(text(NX, y + 12, s, 10.5, weight=700))
    return y + 18


def _col_headers(o, boxes, y):
    """The three column headers; the two branch headers cite the type pick of
    kv_block::k_storage that names the two slot kinds."""
    hh = 42
    o.append(rect(NX, y, NW, hh, C["soft"], C["line"], 1, 3))
    o.append(text(NX + 6, y + 14, "consumer: name, what it does,", 9.5, weight=600))
    o.append(text(NX + 6, y + 26, "its definition, then its branch line", 9.5, weight=600))
    o.append(text(NX + 6, y + 38, "(the layout_on cell of B3, first band)", 8.5,
                  fill=C["muted"]))
    o.append(rect(TX, y, TW, hh, C["vnni_fill"], C["vnni"], 1.4, 3))
    o.append(text(TX + 6, y + 14, "layout_on = true: VNNI slot", 10, weight=700,
                  fill=C["vnni"]))
    o.append(text(TX + 6, y + 26, "(k is a k_vnni_tensor)", 9, mono=True))
    o.append(cite(TX + TW - 4, y + hh - 4, "kv_cache.hpp:664; 2993-2995"))
    boxes.append(("layout_on = true: VNNI slot", "kv_cache.hpp:664; kv_cache.hpp:2993-2995"))
    o.append(rect(FX, y, FW, hh, C["rm_fill"], C["rm"], 1.4, 3))
    o.append(text(FX + 6, y + 14, "layout_on = false: row-major slot", 10, weight=700,
                  fill=C["rm"]))
    o.append(text(FX + 6, y + 26, "(k is native_k_storage)", 9, mono=True))
    o.append(cite(FX + FW - 4, y + hh - 4, "kv_cache.hpp:664; 2993-2995"))
    boxes.append(("layout_on = false: row-major slot", "kv_cache.hpp:664; kv_cache.hpp:2993-2995"))
    return y + hh


# ---------------------------------------------------------------------------
# d2a: the gate and its consumers in kv_cache.hpp


def _fig_a():
    fid = "k_vnni-d2a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    o.append(text(NX, 14, "the layout gate (k_vnni.hpp:119-131, new): two inputs, one "
                  "compile-time answer, and who branches on it", 11, weight=700))
    # the two inputs
    o.append(label_box(NX, 26, 200, 52, "#ifdef TRON_K_VNNI", [
        "CMake option, default OFF"], "#fff", C["ink"], 10.5,
        ref="k_vnni.hpp:124; kv_cache.hpp:653"))
    boxes.append(("#ifdef TRON_K_VNNI", "k_vnni.hpp:124; kv_cache.hpp:653"))
    o.append(label_box(NX, 86, 200, 52, "head_size == HEAD_SIZE_128", [
        "the slot's storage geometry"], "#fff", C["ink"], 10.5,
        ref="k_vnni.hpp:125-126"))
    boxes.append(("head_size == HEAD_SIZE_128", "k_vnni.hpp:125-126"))
    # the gate
    gx, gy, gw, gh = 240, 26, 250, 88
    gate_sub = ["the layout gate: constexpr bool (new)",
                "true when both inputs hold; #else false",
                "a property of the storage geometry, not of",
                "the query type or of the AMX availability"]
    for s in gate_sub:
        _w(s, 9, gw - 16, where="gate sub")
    _w("k_vnni::layout_on<head_size>", 11, gw - 16, True, "gate title")
    # a B3-style fn_cell: name, description lines, the 'new' tag, citation
    o.append(fn_cell(gx, gy, gw, gh, "k_vnni::layout_on<head_size>", gate_sub,
                     "k_vnni.hpp:119-130", "new", size=11))
    boxes.append(("k_vnni::layout_on<head_size>", "k_vnni.hpp:119-130"))
    # inputs -> gate (the two lines join before the gate)
    jx, jy = 224, gy + gh / 2
    o.append(line(208, 112, jx, 112, C["ink"], 1.4))
    o.append(line(jx, 112, jx, jy, C["ink"], 1.4))
    o.append(arrow(fid, "ink", [(208, 52), (jx, 52), (jx, jy), (gx, jy)], C["ink"], 1.4))
    # the note under the inputs
    o.append(lines(NX, 152, ["same answer for every reader and writer of a",
                             "slot, on every thread [k_vnni.hpp:121-123]"], 9, 11,
                   fill=C["ink"]))
    # gate -> the two column headers
    hy = 172
    tcx = TX + TW / 2
    o.append(arrow(fid, "vnni", [(tcx, gy + gh), (tcx, hy)], C["vnni"], 1.6))
    o.append(text(tcx + 6, gy + gh + 24, "true", 10, fill=C["vnni"], weight=700))
    fcx = FX + FW / 2
    o.append(arrow(fid, "rm", [(gx + gw, jy), (fcx, jy), (fcx, hy)], C["rm"], 1.6))
    o.append(text(fcx + 6, jy + 44, "false", 10, fill=C["rm"], weight=700))
    y = _col_headers(o, boxes, hy)
    # the consumers in kv_cache.hpp
    y = _group(o, y + 8, "kv_cache.hpp: page, kv_block and book")
    rows = [
        ("kv_block::k_storage", "the type of kv_block::k: std::conditional_t",
         "kv_cache.hpp:2993-2995",
         ["k_vnni_tensor<page_size, head_size>:", "the typed owner of the plane"],
         ["native_k_storage =", "bf16[page_size * head_size]"]),
        ("page::k, kv_block::k_view, k_at", "the row-major K views: one row per token",
         "kv_cache.hpp:2045-2100, 3021-3038",
         None,
         ["k_view(): the plane as [token][element];", "k_at(i_page): one token's row"]),
        ("page::k_packed, k_vnni_blocks", "read-only packed plane; converted-block bits",
         "kv_cache.hpp:2120, 2133; requires 2117, 2130",
         ["k.as_view() -> k_vnni_view<const bf16>;", "k_vnni_blocks_[k_state_ix].load(acquire)"],
         None),
        ("set_k_block, k_row_if_row_major", "page: 16 rows at once; one row in place",
         "kv_cache.hpp:2277, 2341; requires 2274, 2338",
         ["store_block with FULL_BLOCK_0XFFFF;", "row_major_row(..) or an invalid view"],
         None),
        ("page::set_k_row / get_k_row", "layout-agnostic K row store and load",
         "kv_cache.hpp:2247-2262, 2291-2306",
         ["converted block: store_row / load_row;", "else store_row_major / load_row_major"],
         ["std::memcpy to / from", "k_at(i_page).data: one contiguous row"]),
        ("page::note_k_row_saved", "records that a page offset's K row is saved",
         "kv_cache.hpp:2167; branch 2169",
         ["k_rows_saved_ |= offset_bit", "(fetch_or, acq_rel); returns true when",
          "16 rows are saved and not converted"],
         ["returns BLOCK_COMPLETED_FALSE:", "a row-major slot keeps no bits"]),
        ("page::k_block_to_vnni_at", "converts block c of every KV head in place",
         "kv_cache.hpp:2214-2226",
         ["block_to_vnni per KV head, then", "k_vnni_blocks_ |= block_bit (release)"],
         ["returns CONVERTED_FALSE:", "a row-major slot never converts"]),
        ("page::k_forget_row", "drops the K bits of an offset and above",
         "kv_cache.hpp:2552-2574",
         ["block_to_rows per KV head of a converted", "block that keeps rows below the offset"],
         ["empty branch: a row-major slot", "keeps no bits"]),
        ("page::copy_storage_slot", "copies count tokens of one slot between pages",
         "kv_cache.hpp:2691-2705, 2720, 2780",
         ["whole page: dst_block.k = src_block.k;", "else per token through row-major rows,",
          "then the K bits (release)"],
         ["memcpy of count rows from", "k_at(src_begin) to k_at(dst_begin)"]),
        ("book::fill_storage_slot", "the test-only random fill (fill_random body)",
         "kv_cache.hpp:1830-1835",
         ["k_vnni_access::plane(block.k.as_view()):", "every element of the plane"],
         ["for (auto& value : block.k)"]),
    ]
    for name, desc, ref, t, f in rows:
        y = _row(o, boxes, y, name, desc, ref, t, f)
    H = int(y) + 2
    cap = ("Updates B3: the layout_on<head_size> cell of the first band, expanded. "
           "Two inputs (the CMake option TRON_K_VNNI and a 128-dimension head) give one "
           "compile-time answer, and the table lists what each consumer in kv_cache.hpp "
           "does when the answer is true (VNNI slot, blue) and when it is false "
           "(row-major slot, orange). Look at the three grey dashed cells: page::k (with "
           "kv_block::k_view and k_at) exists for row-major slots only, and page::k_packed, "
           "k_vnni_blocks, set_k_block and k_row_if_row_major exist for VNNI slots only (a "
           "requires clause, a compile-time condition on the function). So a caller of the "
           "wrong layout does not compile. The consumer cells are the fn_cells of B3.")
    legend = [
        ("box", "white box, ink outline: the two inputs (#ifdef TRON_K_VNNI, head_size == "
         "HEAD_SIZE_128), the gate k_vnni::layout_on<head_size> and each consumer in "
         "kv_cache.hpp; the name in bold monospace, what it does in sans-serif"),
        ("vnni", "blue box and blue text: layout_on = true, the VNNI slot (k is a "
         "k_vnni_tensor); the column header and what each consumer does there"),
        ("rm", "orange box and orange text: layout_on = false, the row-major slot (k is "
         "native_k_storage); the column header and what each consumer does there"),
        ("deleted", "white cell, grey dashed outline: the function does not exist on that "
         "side (a requires clause on layout_on)"),
        ("ctx", "grey box, thin grey outline: the header of the consumer column, which "
                "says what each consumer cell shows"),
        ("arrow", "ink arrow: the two inputs join and enter the gate"),
        ("blue arrow: the gate's true answer -> the VNNI slot column", "arrow", C["vnni"]),
        ("orange arrow: the gate's false answer -> the row-major slot column", "arrow", C["rm"]),
        ("font_mono", "monospace = the two inputs, the gate, each consumer's name, and the "
                      "k type in the two column headers"),
        ("font_sans", "sans-serif = the figure title, what each consumer does, what it does "
                      "on each side of the gate, the true and false labels, the "
                      "column-header words, the group header and the note under the "
                      "inputs"),
        ("font_cite", "small grey monospace = the lines that define the box and its branch "
         "(file:line)"),
        ("font_tag", "bold 'new' = the gate k_vnni::layout_on is added by this PR"),
    ]
    return figure(fid, W, H, "The layout gate layout_on and its consumers in kv_cache.hpp",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# d2b: the consumers in model.hpp, self_attention.hpp and full.hpp


def _fig_b():
    fid = "k_vnni-d2b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(NX, 14, "the consumers of k_vnni::layout_on<head_size> outside "
                  "kv_cache.hpp (the same columns as above)", 11, weight=700))
    y = _col_headers(o, boxes, 24)
    y = _group(o, y + 8, "model.hpp: the K store of save_k")
    rows_model = [
        ("k_store_shared", "whether the K store is shared with the helpers",
         "model.hpp:3192; branch 3193",
         ["n_workers > 1, <= helper_windows.size(),", "items.size() > k_store_block",
          "[main and every helper]: the same answer"],
         ["returns false: no shared window"]),
        ("store_k_block", "stores the K rows of a run of items",
         "model.hpp:3241-3251",
         ["16-token run: set_k_block +", "note_k_block_saved; shorter: set_k_row"],
         ["page::k(slot, kv_head, j).set(row)", "per token and KV head"]),
        ("save_k_impl", "after every store: records this pass's rows",
         "model.hpp:3352, 3420",
         ["note_k_row_saved per row, true ->", "pending_k_blocks_; not when",
          "cached_operation_uses_hw"],
         ["no row recording"]),
    ]
    for name, desc, ref, t, f in rows_model:
        y = _row(o, boxes, y, name, desc, ref, t, f)
    y = _group(o, y + 2, "self_attention.hpp: scoring one page")
    rows_attn = [
        ("packed_amx_query", "packs the token's Q group for the AMX kernel",
         "self_attention.hpp:1690-1707",
         ["pack_q_rows_128x4: Q as the A operand", "(rows) of qk_vnni_128x4"],
         ["pack_q_group_128x4: Q as the B operand", "of qk_rowmajor_128x4"]),
        ("apply_dense_amx_page", "QK for the whole page in one kernel call",
         "self_attention.hpp:1749-1781",
         ["qk_vnni_128x4(k_packed(slot, kv_head),", "q_packed, s_pages): K is the B operand"],
         ["qk_rowmajor_128x4(k(slot, kv_head),", "q_packed, s_pages): K is the A operand"]),
        ("k_layout_dense (apply_page_tok)", "the third gate of the dense AMX path",
         "self_attention.hpp:1924; branch 1925",
         ["k_vnni_blocks(slot) ==", "BLOCKS_PER_PAGE_MASK_0XF (all 4 blocks)"],
         ["true: a row-major slot keeps", "no layout state"]),
        ("k_vnni_on (apply_page_tok)", "how the relevant tokens of a page are scored",
         "self_attention.hpp:1962",
         ["VNNI block: live |= offset_bit, then", "qk_group(*plane, live); row-major tail",
          "block: row_major_row -> dotter"],
         ["keys = page::k(slot, kv_head);", "dotter over keys[i], one token at a time"]),
    ]
    for name, desc, ref, t, f in rows_attn:
        y = _row(o, boxes, y, name, desc, ref, t, f)
    y = _group(o, y + 2, "full.hpp: the FPGA staging (scheduler)")
    y = _row(o, boxes, y, "page_info::k_head_fn",
             "the FPGA staging callback: one K row per token", "full.hpp:2747-2751",
             ["k_row_if_row_major: the row in place;", "else get_k_row into dest",
              "(k_destination_row)"],
             ["k(slot, kv_head, off).data"])
    H = int(y) + 2
    cap = ("Updates B3: the layout_on consumers outside kv_cache.hpp, continued from the "
           "table above with the same columns. In model.hpp the gate decides whether the "
           "K store is shared with the helpers, and how store_k_block stores a run. In "
           "self_attention.hpp it picks the Q packing, the AMX kernel, the dense-page "
           "check and the software reader. In full.hpp it picks how the FPGA staging "
           "reads one K row. Look at the orange column: the row-major branches reach K "
           "through page::k, the row view that exists only for row-major slots (row 2 of "
           "the table above).")
    legend = [
        ("box", "white box, ink outline: each consumer in model.hpp, self_attention.hpp and "
         "full.hpp; the name in bold monospace, what it does in sans-serif"),
        ("vnni", "blue box and blue text: layout_on = true, the VNNI slot (k is a "
         "k_vnni_tensor); the column header and what each consumer does there"),
        ("rm", "orange box and orange text: layout_on = false, the row-major slot (k is "
         "native_k_storage); the column header and what each consumer does there"),
        ("ctx", "grey box, thin grey outline: the header of the consumer column, which "
                "says what each consumer cell shows"),
        ("font_mono", "monospace = each consumer's name and the k type in the two column "
                      "headers"),
        ("font_sans", "sans-serif = the figure title, what each consumer does, what it does "
                      "on each side of the gate, the three file headers and the "
                      "column-header words"),
        ("font_cite", "small grey monospace = the lines that define the box and its branch "
         "(file:line)"),
    ]
    return figure(fid, W, H, "The consumers of layout_on in model.hpp, self_attention.hpp "
                  "and full.hpp", "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
