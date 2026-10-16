"""Change diagrams of unit k2 of the PR 4956 k_vnni.hpp page: the layout gate
k_vnni::layout_on<head_size> (head lines 86-96) and who branches on it.

Two figures:
  k_vnni-d2a: the gate (its two inputs, its answer) and its consumers in
              kv_cache.hpp, one row each;
  k_vnni-d2b: its consumers in model.hpp, self_attention.hpp, full.hpp and
              the tests.
Each row = the consumer's name, one line on what it does, the line of its
branch, and what it does when the gate is true (VNNI slot, blue) and when it
is false (row-major slot, orange). A white cell with a grey dashed outline =
the function does not exist on that side (a requires clause).
Line numbers are head lines of PR 4956 (a5697f86d3).
"""
import sys

from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, line, lines,
                         marker_defs, rect, text, text_width)

BASE = ("Updates B3: the layout_on<head_size> cell of the first band expands into "
        "a two-column table of its consumers in kv_cache.hpp, model.hpp, "
        "self_attention.hpp, full.hpp and the tests, one row per consumer, with what "
        "it does when the gate is true (VNNI slot, blue) and when it is false "
        "(row-major slot, orange).")

W = 700
NX, NW = 8, 244      # the consumer column
TX, TW = 258, 210    # the true column (VNNI slot)
FX, FW = 472, 220    # the false column (row-major slot)
RH, RG = 48, 4       # row height and gap


def _w(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _cell(o, x, y, w, h, lines_, kind, where):
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
    o.append(cite(TX + TW - 4, y + hh - 4, "kv_cache.hpp:697-698; 2566-2568"))
    boxes.append(("layout_on = true: VNNI slot", "kv_cache.hpp:697-698; kv_cache.hpp:2566-2568"))
    o.append(rect(FX, y, FW, hh, C["rm_fill"], C["rm"], 1.4, 3))
    o.append(text(FX + 6, y + 14, "layout_on = false: row-major slot", 10, weight=700,
                  fill=C["rm"]))
    o.append(text(FX + 6, y + 26, "(k is native_k_storage)", 9, mono=True))
    o.append(cite(FX + FW - 4, y + hh - 4, "kv_cache.hpp:697-698; 2565-2568"))
    boxes.append(("layout_on = false: row-major slot", "kv_cache.hpp:697-698; kv_cache.hpp:2565-2568"))
    return y + hh


# ---------------------------------------------------------------------------
# d2a: the gate and its consumers in kv_cache.hpp


def _fig_a():
    fid = "k_vnni-d2a"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    o.append(text(NX, 14, "the layout gate (k_vnni.hpp:86-95, new): two inputs, one "
                  "compile-time answer, and who branches on it", 11, weight=700))
    o.append(label_box(NX, 26, 200, 52, "#ifdef TRON_K_VNNI", [
        "CMake option, default OFF"], "#fff", C["ink"], 10.5,
        ref="k_vnni.hpp:89; kv_cache.hpp:687"))
    boxes.append(("#ifdef TRON_K_VNNI", "k_vnni.hpp:89; kv_cache.hpp:687"))
    o.append(label_box(NX, 86, 200, 52, "head_size == HEAD_SIZE_128", [
        "the slot's storage geometry"], "#fff", C["ink"], 10.5,
        ref="k_vnni.hpp:90-91"))
    boxes.append(("head_size == HEAD_SIZE_128", "k_vnni.hpp:90-91"))
    gx, gy, gw, gh = 240, 26, 250, 88
    gate_sub = ["the layout gate: constexpr bool (new)",
                "true when both inputs hold; #else false",
                "depends on the head size only, not on the",
                "query type or on AMX availability"]
    for s in gate_sub:
        _w(s, 9, gw - 16, where="gate sub")
    o.append(fn_cell(gx, gy, gw, gh, "k_vnni::layout_on<head_size>", gate_sub,
                     "k_vnni.hpp:86-95", "new", size=11))
    boxes.append(("k_vnni::layout_on<head_size>", "k_vnni.hpp:86-95"))
    jx, jy = 224, gy + gh / 2
    o.append(line(208, 112, jx, 112, C["ink"], 1.4))
    o.append(line(jx, 112, jx, jy, C["ink"], 1.4))
    o.append(arrow(fid, "ink", [(208, 52), (jx, 52), (jx, jy), (gx, jy)], C["ink"], 1.4))
    o.append(lines(NX, 152, ["same answer for every reader and writer of a",
                             "slot, on every thread [k_vnni.hpp:86-88]"], 9, 11,
                   fill=C["ink"]))
    hy = 172
    tcx = TX + TW / 2
    o.append(arrow(fid, "vnni", [(tcx, gy + gh), (tcx, hy)], C["vnni"], 1.6))
    o.append(text(tcx + 6, gy + gh + 24, "true", 10, fill=C["vnni"], weight=700))
    fcx = FX + FW / 2
    o.append(arrow(fid, "rm", [(gx + gw, jy), (fcx, jy), (fcx, hy)], C["rm"], 1.6))
    o.append(text(fcx + 6, jy + 44, "false", 10, fill=C["rm"], weight=700))
    y = _col_headers(o, boxes, hy)
    y = _group(o, y + 8, "kv_cache.hpp: kv_block, page and book")
    rows = [
        ("kv_block::k_storage", "the type of kv_block::k: std::conditional_t",
         "kv_cache.hpp:2566-2568",
         ["k_vnni_tensor<page_size, head_size>:", "the typed owner of the plane"],
         ["native_k_storage =", "bf16[page_size * head_size]"]),
        ("kv_block::k_view, k_at", "the row-major K views of one kv_block",
         "kv_cache.hpp:2590-2610; requires 2593, 2606",
         None,
         ["k_view(): the plane as [token][element];", "k_at(i_page): one token's row"]),
        ("page::k (8 overloads)", "the row view of K: one row per token",
         "kv_cache.hpp:1974-2038; requires 1978-2033",
         None,
         ["kv_block(slot, kv_head).k_view(), or", "its row [i_page]"]),
        ("page::k_packed", "read-only packed plane for qk_group",
         "kv_cache.hpp:2041-2051; requires 2044-2045",
         ["k.as_view() on the const owner ->", "k_vnni_view<const bf16, 64, 128>"],
         None),
        ("page::set_k_row / get_k_row", "layout-agnostic K row store and load",
         "kv_cache.hpp:2053-2085; branch 2062, 2079",
         ["store_row / load_row on", "kv_block.k.as_view()"],
         ["std::memcpy to / from", "k_at(i_page).data: one contiguous row"]),
        ("page::copy_storage_slot", "copies count tokens of one slot between pages",
         "kv_cache.hpp:2325-2355; branch 2331",
         ["whole page: dst_block.k = src_block.k;", "else copy_token per token"],
         ["memcpy of count rows from", "k_at(src_begin) to k_at(dst_begin)"]),
        ("book::fill_storage_slot", "the test-only random fill (fill_random body)",
         "kv_cache.hpp:1767-1781; branch 1772",
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
           "kv_block::k_view and k_at) exists for row-major slots only, and page::k_packed "
           "exists for VNNI slots only (a requires clause, a compile-time condition on the "
           "function). So a caller of the wrong layout does not compile. The consumer cells "
           "are the fn_cells of B3.")
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
# d2b: the consumers in model.hpp, self_attention.hpp, full.hpp and the tests


def _fig_b():
    fid = "k_vnni-d2b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(NX, 14, "the consumers of k_vnni::layout_on<head_size> outside "
                  "kv_cache.hpp (the same columns as above)", 11, weight=700))
    y = _col_headers(o, boxes, 24)
    y = _group(o, y + 8, "model.hpp: the K store of save_k")
    y = _row(o, boxes, y, "save_k_impl", "stores every token's K row of one layer",
             "model.hpp:3074-3118; branch 3100",
             ["set_k_row(slot, kv_head, j,", "k_source_row(kout)); a non-bf16 kout is",
              "converted to a bf16 row (3108-3111)"],
             ["page::k(slot, kv_head, j).set(kout)", "per token and KV head (3114)"])
    y = _group(o, y + 2, "self_attention.hpp: scoring one page")
    rows_attn = [
        ("the dense AMX page gate", "the if constexpr around apply_dense_amx_page",
         "self_attention.hpp:1884-1898; branch 1886",
         ["not compiled: a VNNI slot has no row", "view for qk_rowmajor_128x4 to read"],
         ["eligible<activation_scalar>(128, kv_mul):", "a dense page takes the AMX kernel"]),
        ("k_vnni_on (apply_page_tok)", "how the relevant tokens of a page are scored",
         "self_attention.hpp:1909; 1917-1963",
         ["the loop marks live |= 1 << i; after it", "qk_group(k_packed(slot, kv_head), q,",
          "live, s_pages, 64) scores the page"],
         ["keys = page::k(slot, kv_head);", "dotter over keys[i], one token at a time"]),
    ]
    for name, desc, ref, t, f in rows_attn:
        y = _row(o, boxes, y, name, desc, ref, t, f)
    y = _group(o, y + 2, "full.hpp: the FPGA staging callback")
    y = _row(o, boxes, y, "page_info::k_head_fn",
             "the staging callback: one K row per token", "full.hpp:2747-2760; branch 2751",
             ["get_k_row into dest (k_destination_row),", "return dest (the scratch row)"],
             ["return k(slot, kv_head, off).data", "(the row in place)"])
    y = _group(o, y + 2, "tests")
    rows_t = [
        ("exercise_page (t_amx_dispatch_dtype)", "the dense predicate of the fake-AMX test",
         "t_amx_dispatch_dtype.cpp:76, 165-168",
         ["dense = false: the Q pack runs,", "no kernel runs (the file header, 8-13)"],
         ["dense for a full page: one QK,", "one PV kernel call"]),
        ("check_slot (t_llama_unit)", "page K views preserve geometry",
         "t_llama_unit.cpp:1096-1101",
         ["STATIC_REQUIRE_FALSE(page_k_accepts_", "geometry): page::k does not compile"],
         ["the page::k row addressing checks"]),
        ("STATIC_REQUIRE(layout_on<128>)", "page K rows survive store, load and append",
         "t_k_vnni_layout.cpp:356-360",
         ["STATIC_REQUIRE(layout_on<128>)", "under #ifdef TRON_K_VNNI"],
         ["STATIC_REQUIRE_FALSE(layout_on<128>)", "in the other build"]),
    ]
    for name, desc, ref, t, f in rows_t:
        y = _row(o, boxes, y, name, desc, ref, t, f)
    H = int(y) + 2
    cap = ("Updates B3: the layout_on consumers outside kv_cache.hpp, continued from the "
           "table above with the same columns. In model.hpp the gate picks how save_k "
           "stores a row. In self_attention.hpp it removes the dense AMX page path and "
           "picks the software reader: the live mask and one qk_group call for a VNNI "
           "slot, the per-token dotter loop for a row-major slot. In full.hpp it picks how "
           "the FPGA staging reads one K row. The tests check the gate and the two sides. "
           "Look at the orange column: the row-major branches reach K through page::k, the "
           "row view that exists only for row-major slots (row 3 of the table above).")
    legend = [
        ("box", "white box, ink outline: each consumer in model.hpp, self_attention.hpp, "
         "full.hpp and the tests; the name in bold monospace, what it does in sans-serif"),
        ("vnni", "blue box and blue text: layout_on = true, the VNNI slot (k is a "
         "k_vnni_tensor); the column header and what each consumer does there"),
        ("rm", "orange box and orange text: layout_on = false, the row-major slot (k is "
         "native_k_storage); the column header and what each consumer does there"),
        ("ctx", "grey box, thin grey outline: the header of the consumer column, which "
                "says what each consumer cell shows"),
        ("font_mono", "monospace = each consumer's name and the k type in the two column "
                      "headers"),
        ("font_sans", "sans-serif = the figure title, what each consumer does, what it does "
                      "on each side of the gate, the four file headers and the "
                      "column-header words"),
        ("font_cite", "small grey monospace = the lines that define the box and its branch "
         "(file:line)"),
    ]
    return figure(fid, W, H, "The consumers of layout_on in model.hpp, self_attention.hpp, "
                  "full.hpp and the tests", "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [_fig_a(), _fig_b()]
