"""Change diagram of unit c4 (kv_cache.hpp page of PR 4956): set_k_row / get_k_row,
the layout-agnostic row accessors (four overloads).

Head lines 2053-2107.
"""
from svg_helpers import C, arrow, cite, figure, fn_cell, lines, marker_defs, rect, text
from base_kv_cache import fit, tag

BASE = ("Updates B3 rows 1, 3 and 5 and B4: the three call paths through set_k_row / "
        "get_k_row are redrawn as one decision tree: the caller's typed row, the "
        "geometry overload's compile-time layout test, the two k_vnni.hpp operations "
        "or the memcpy, and the uniform overloads that forward to the primary geometry.")

W = 700


def op_box(x, y, w, h, title, body, ref, fill, stroke):
    o = [rect(x, y, w, h, fill, stroke, 1.4, 5), text(x + 8, y + 16, title, 10, mono=True,
                                                     weight=700)]
    for s in body:
        fit(s, 8.5, w - 16, False, "d4 op")
    o.append(lines(x + 8, y + 30, body, 8.5, 11))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def fig():
    fid = "kv_cache-d4"
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    boxes = []
    o.append(text(20, 18, "set_k_row / get_k_row: one token's K row in and out of any slot's "
                  "layout", 12.5, weight=700))
    # callers
    cy = 30
    callers = [
        ("save_k_impl [main]", ["k_source_row(kout) for a bf16 row;", "other types: convert to bf16 first"], "model.hpp:3100-3112",
         "set_k_row<geometry.kv>"),
        ("page_info::k_head_fn", ["k_destination_row<hw_kv.head_size>(dest):", "the staging's "
                                  "scratch row for one token"], "full.hpp:2751-2756",
         "get_k_row<hw_kv>"),
        ("tests", ["t_k_vnni_layout: every token in and out;", "t_llama_unit, t_amx_dispatch_dtype"],
         "t_k_vnni_layout.cpp:362-377",
         "set_k_row / get_k_row"),
    ]
    for i, (t, body, ref, via) in enumerate(callers):
        x = 20 + i * 224
        o.append(rect(x, cy, 212, 70, C["soft"], C["line"], 1, 4))
        o.append(text(x + 8, cy + 15, t, 9.5, weight=700))
        for s in body:
            fit(s, 8.5, 196, False, "d4 caller")
        o.append(lines(x + 8, cy + 28, body, 8.5, 11))
        fit(ref, 8.5, 204, True, "d4 caller cite")
        o.append(cite(x + 208, cy + 66, ref))
        o.append(text(x + 106, cy + 82, "via " + via, 8.5, "middle", True, fill=C["ink"]))
        o.append(arrow(fid, "ink", [(x + 106, cy + 86), (x + 106, cy + 100)], C["ink"], 1.2))
    boxes += [("save_k_impl (caller)", "model.hpp:3074, 3100-3112"),
              ("page_info::k_head_fn (caller)", "full.hpp:2747-2756"),
              ("set_k_row / get_k_row in the tests (callers)", "t_k_vnni_layout.cpp:362-377; t_llama_unit.cpp:485-489; t_amx_dispatch_dtype.cpp:110")]
    # the typed row
    ry = cy + 102
    o.append(rect(20, ry, 660, 50, C["rm_fill"], C["rm"], 1.4, 5))
    o.append(text(28, ry + 16, "const_k_row_view<head_size, Aligned, Dma> row  |  "
                  "k_row_view<head_size, Aligned, Dma> row", 9.5, mono=True, weight=700))
    o.append(text(28, ry + 31, "one token's head_size bf16 values in dimension order, with the "
                  "caller's Aligned / Dma flags; \"the row may be unaligned\"", 8.5))
    o.append(cite(676, ry + 46, "tensor/k_vnni.hpp:197-204; kv_cache.hpp:2053, 2070"))
    boxes.append(("const_k_row_view / k_row_view (the transfer row)", "tensor/k_vnni.hpp:197-204"))
    # the geometry overloads
    gy = ry + 66
    o.append(arrow(fid, "ink", [(350, ry + 50), (350, gy - 2)], C["ink"], 1.2))
    o.append(fn_cell(20, gy, 320, 80, "set_k_row<geometry, Aligned, Dma>",
                     ["requires(book_t::declares_geometry<geometry>())",
                      "TRON_ASSERT_LT(i_page, page_size), then the",
                      "if constexpr below"], "kv_cache.hpp:2053-2068", "new"))
    o.append(fn_cell(360, gy, 320, 80, "get_k_row<geometry, Aligned, Dma> const",
                     ["the inverse of set_k_row; the same requires,",
                      "the same assert, the same if constexpr", ""],
                     "kv_cache.hpp:2070-2085", "new"))
    boxes += [("set_k_row<geometry, Aligned, Dma>", "kv_cache.hpp:2053-2068"),
              ("get_k_row<geometry, Aligned, Dma>", "kv_cache.hpp:2070-2085")]
    # the branch
    by = gy + 96
    o.append(rect(200, by, 300, 30, "#fff", C["ink"], 1.2, 4))
    o.append(text(350, by + 19, "if constexpr (k_vnni::layout_on<geometry.head_size>)", 8.5,
                  "middle", True, weight=700))
    o.append(cite(350, by + 42, "kv_cache.hpp:2062, 2079", "middle"))
    boxes.append(("if constexpr (k_vnni::layout_on<geometry.head_size>)", "kv_cache.hpp:2062, 2079"))
    o.append(arrow(fid, "ink", [(180, gy + 80), (180, by + 15), (198, by + 15)], C["ink"], 1.2))
    o.append(arrow(fid, "ink", [(520, gy + 80), (520, by + 15), (502, by + 15)], C["ink"], 1.2))
    oy = by + 56
    o.append(arrow(fid, "vnni", [(300, by + 30), (300, oy - 2)], C["vnni"], 1.4))
    o.append(text(292, oy - 8, "true", 9, "end", fill=C["vnni"], weight=700))
    o.append(arrow(fid, "rm", [(400, by + 30), (400, oy - 2)], C["rm"], 1.4))
    o.append(text(408, oy - 8, "false", 9, fill=C["rm"], weight=700))
    o.append(op_box(20, oy, 320, 106, "VNNI slot",
                    ["set: store_row(kv_block<geometry>(slot, kv_head).k.as_view(),",
                     "       i_page, row): 4 scatters into the token's column",
                     "get: load_row(kv_block<geometry>(slot, kv_head).k.as_view(),",
                     "       i_page, row): 4 gathers out of the column",
                     "the owner is reached through k.as_view() (writable from a",
                     "non-const block, read-only from a const block)"],
                    "kv_cache.hpp:2063, 2080; tensor/k_vnni.hpp:251-284", C["vnni_fill"],
                    C["vnni"]))
    o.append(op_box(360, oy, 320, 106, "row-major slot",
                    ["set: std::memcpy(kv_block<geometry>(slot, kv_head).k_at(i_page)",
                     "       .data, row.data, geometry.head_size * sizeof(bf16))",
                     "get: std::memcpy(row.data, ...k_at(i_page).data, the same size)",
                     "256 bytes for a 128-dimension head: the contiguous row",
                     "(k_at exists for native K only, unit C1)", ""],
                    "kv_cache.hpp:2064-2066, 2081-2083", C["rm_fill"], C["rm"]))
    boxes += [("VNNI branch: store_row / load_row", "kv_cache.hpp:2063, 2080; tensor/k_vnni.hpp:251-284"),
              ("row-major branch: std::memcpy through k_at", "kv_cache.hpp:2064-2066, 2081-2083")]
    # uniform overloads
    uy = oy + 122
    o.append(rect(20, uy, 660, 60, "#fff", C["ink"], 1.1, 5, "5 3"))
    o.append(text(28, uy + 16, "uniform-geometry overloads: set_k_row / get_k_row<Aligned, Dma>, "
                  "requires(uniform_geometry)", 9.5, mono=True, weight=700))
    o.append(text(28, uy + 32, "forward to set_k_row<layout_t::primary_geometry>(...) / "
                  "get_k_row<layout_t::primary_geometry>(...); the row type uses the "
                  "page's head_size", 8.5))
    o.append(text(28, uy + 44, "callers: the tests (page->set_k_row(SLOT_0, 0, tok, ...)), "
                  "t_llama_unit's k_output helper", 8.5))
    o.append(tag(672, uy + 16, "new"))
    o.append(cite(676, uy + 56, "kv_cache.hpp:2087-2107; t_k_vnni_layout.cpp:369, 373"))
    boxes.append(("set_k_row / get_k_row (uniform-geometry overloads)", "kv_cache.hpp:2087-2107"))
    H = uy + 72
    cap = ("Updates B3 rows 1, 3 and 5 and B4: the decision tree of the two row accessors. "
           "A caller hands over one token's row as a typed view with its own alignment and "
           "DMA flags. The geometry overload asserts the page offset and branches at "
           "compile time on the slot's head size: a VNNI slot takes store_row or load_row "
           "through the owner's view, a row-major slot keeps the 256-byte memcpy through "
           "k_at. The uniform-geometry overloads forward to the primary geometry. The "
           "three callers are save_k, the FPGA staging callback and the tests.")
    legend = [
        ("ctx", "grey box, thin grey outline: a caller (save_k_impl, k_head_fn, the tests)"),
        ("rm", "orange: the transfer row (const_k_row_view / k_row_view) and the row-major "
               "branch (std::memcpy through k_at); orange text = the 'false' branch label"),
        ("box", "white box, ink outline: the two geometry overloads and the if constexpr "
                "test: name in bold monospace, description in sans-serif"),
        ("ink dashed frame: the two uniform-geometry overloads that forward to the primary "
         "geometry", "#fff", C["ink"], True, False),
        ("vnni", "blue: the VNNI branch (store_row / load_row through k.as_view()); blue "
                 "text = the 'true' branch label"),
        ("arrow", "ink arrow: a call: caller -> the row -> the overload -> the test"),
        ("blue arrow: the layout_on true branch", "arrow", C["vnni"]),
        ("orange arrow: the layout_on false branch", "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR (all four overloads)"),
    ]
    return figure(fid, W, H, "set_k_row / get_k_row: the decision tree of the row accessors",
                  "".join(o), cap, boxes=boxes, legend=legend)
