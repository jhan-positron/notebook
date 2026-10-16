"""Change diagram of unit c3 (kv_cache.hpp page of PR 4956): page::k_packed, the
read-only K plane view for the score reader k_vnni::qk_group.

Head lines 2041-2051.
"""
from svg_helpers import C, arrow, card_arrow, cite, figure, fn_cell, label_box, lines, marker_defs, rect, text
from base_kv_cache import fit, tag, plane_strip

BASE = ("Updates B3 row 2 and B4 row 2: the attention path is opened into what k_packed "
        "requires, what it returns (a read-only k_vnni_view of the plane, from the const "
        "owner) and who consumes it (k_vnni::qk_group in apply_page_tok, and the type "
        "checks of t_llama_unit).")

W = 700


def fig():
    fid = "kv_cache-d3"
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "q": C["q"]})]
    boxes = []
    o.append(text(20, 18, "page::k_packed<geometry>(slot, kv_head): the read-only plane view",
                  12.5, weight=700))
    o.append(fn_cell(20, 30, 660, 86, "k_packed",
                     ["returns kv_block<geometry>(slot, kv_head).k.as_view() from a const page:",
                      "a k_vnni_view<const bf16, page_size, geometry.head_size>; requires "
                      "declares_geometry<geometry>() && layout_on<...>",
                      "\"Internal cache writes take writable views from the block owner "
                      "instead\" (set_k_row, copy_storage_slot: k.as_view() non-const)"],
                     "kv_cache.hpp:2041-2051", "new"))
    boxes.append(("k_packed", "kv_cache.hpp:2041-2051"))
    # what it returns
    vy = 136
    o.append(rect(20, vy, 320, 110, C["vnni_fill"], C["vnni"], 1.4, 5))
    o.append(text(28, vy + 16, "k_vnni_view<const bf16, 64, 128>", 10.5, mono=True, weight=700))
    vl = ["refers to the plane of (slot 5, kv_head 0, page 7);",
          "owns no memory; at(token, dim) reads one value;",
          "no element write, no public pointer access;",
          "the address is reachable only through",
          "detail::k_vnni_access::plane (a friend)"]
    for s in vl:
        fit(s, 9, 304, False, "d3 view")
    o.append(lines(28, vy + 30, vl, 9, 11))
    o.append(plane_strip(28, vy + 88, 304, 12, label=False))
    o.append(cite(336, vy + 106, "tensor/k_vnni.hpp:122-153, 188-194"))
    boxes.append(("k_vnni_view<const bf16, 64, 128>", "tensor/k_vnni.hpp:122-153 (at 136-140, friends 143-146)"))
    boxes.append(("detail::k_vnni_access::plane", "tensor/k_vnni.hpp:188-194"))
    o.append(card_arrow(fid, "vnni", [(180, 118), (180, vy - 2)], C["vnni"],
                        "1 call -> 1 view of 1 plane (16 KiB)", label_dx=10, label_dy=4,
                        anchor="start"))
    # the owner side
    o.append(rect(360, vy, 320, 110, "#fff", C["ink"], 1.1, 5))
    o.append(text(368, vy + 16, "from the owner: k.as_view() const&", 10.5, mono=True,
                  weight=700))
    ol = ["kv_block<geometry>(slot, kv_head) on a const page gives a",
          "const kv_block; its k is a const k_vnni_tensor, and",
          "as_view() const& returns the read-only view.",
          "as_view() on a temporary owner is deleted (= delete):",
          "a view must not outlive its owner (TRON(this_lifetimebound))"]
    for s in ol:
        fit(s, 9, 304, False, "d3 owner")
    o.append(lines(368, vy + 30, ol, 9, 11))
    o.append(cite(676, vy + 106, "tensor/k_vnni.hpp:162-176; kv_cache.hpp:2050"))
    boxes.append(("k.as_view() const&", "tensor/k_vnni.hpp:170-176; kv_cache.hpp:2050"))
    # consumers
    cy = vy + 130
    o.append(text(20, cy + 12, "consumers", 10.5, weight=700))
    o.append(rect(20, cy + 20, 320, 112, C["q_fill"], C["q"], 1.4, 5))
    o.append(text(28, cy + 36, "apply_page_tok -> k_vnni::qk_group", 10.5, mono=True,
                  weight=700))
    ql = ["k_vnni::qk_group<operation_kv_mul>(",
          "    page.k_packed<geometry.kv>(slot, kv_head),",
          "    q.data + kv_head * kv_mul * head_size,",
          "    live, &s_pages[0][0], page::page_size)",
          "only when relevant_k_tokens > 0; the worked example:",
          "4 heads, 41 live tokens of page 7"]
    for s in ql:
        fit(s, 8.5, 304, True, "d3 q")
    o.append(lines(28, cy + 50, ql, 8.5, 11, mono=True))
    o.append(cite(336, cy + 128, "self_attention.hpp:1963-1971"))
    boxes.append(("apply_page_tok -> k_vnni::qk_group", "self_attention.hpp:1963-1971; kernels/k_vnni.hpp:33-38"))
    o.append(arrow(fid, "q", [(180, vy + 110), (180, cy + 18)], C["q"], 1.4))
    o.append(rect(360, cy + 20, 320, 112, C["soft"], C["line"], 1, 5))
    o.append(text(368, cy + 36, "t_llama_unit.cpp: the type rules", 10.5, weight=700))
    tl = ["the AMX kernels reject the view (amx_qk_accepts false);",
          "no construction from a bf16 pointer (either constness);",
          "bf16 -> const bf16 converts, never the reverse;",
          "an owner gives no view of a temporary; no element write;",
          "alignof(k_vnni_tensor) == 64; with TRON_K_VNNI the page",
          "accepts k_packed<one_head> and returns exactly this view type"]
    for s in tl:
        fit(s, 8.5, 304, False, "d3 tests")
    o.append(lines(368, cy + 50, tl, 8.5, 11))
    o.append(cite(676, cy + 128, "t_llama_unit.cpp:433-461"))
    boxes.append(("t_llama_unit type rules for k_packed", "t_llama_unit.cpp:433-461"))
    o.append(arrow(fid, "ink", [(520, vy + 110), (520, cy + 18)], C["ink"], 1.2))
    H = cy + 144
    cap = ("Updates B3 row 2 and B4 row 2: k_packed is the one read route out of the cache "
           "for a VNNI slot. It exists only for a geometry the layout declares and whose "
           "head size is VNNI. It returns the read-only k_vnni_view that the const owner "
           "hands out, so no raw plane pointer leaves the cache. Its one production "
           "consumer is k_vnni::qk_group in apply_page_tok, called once per page with the "
           "live mask of the loop. The type checks of t_llama_unit pin what the view can "
           "and cannot do.")
    legend = [
        ("box", "white box, ink outline: k_packed and the owner route k.as_view() const&: "
                "name in bold monospace, description in sans-serif"),
        ("vnni", "blue: the returned view k_vnni_view<const bf16, 64, 128> and the saved "
                 "token columns of the plane strip inside it"),
        ("hi", "pale yellow: token 37 in the plane strip"),
        ("empty", "grey dashed: a token column with no row saved"),
        ("q", "purple: the consumer on the query side, apply_page_tok -> k_vnni::qk_group"),
        ("ctx", "grey box, thin grey outline: the test that pins the type rules"),
        ("blue arrow: 1 call -> 1 view of 1 plane", "arrow", C["vnni"]),
        ("purple arrow: the view handed to the score reader", "arrow", C["q"]),
        ("arrow", "ink arrow: the view type checked by the test"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = k_packed is added by this PR"),
    ]
    return figure(fid, W, H, "k_packed: the read-only plane view and its consumers",
                  "".join(o), cap, boxes=boxes, legend=legend)
