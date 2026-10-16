"""Change diagram of unit c6 (kv_cache.hpp page of PR 4956): the test-only fill
reaches a packed K plane through detail::k_vnni_access.

Head lines 1337-1340 (fill_random comment), 1577-1582 (Note [KV block lifetime]
paragraph) and 1772-1781 (fill_storage_slot).
"""
from svg_helpers import C, arrow, cite, figure, fn_cell, lines, marker_defs, rect, text
from base_kv_cache import fit, tag

BASE = ("Updates B3 row 6: the test-only fill path is opened into its three steps "
        "(fill_random, fill_storage_slot, the per-block branch) and the one documented "
        "exception to the typed access rule: the raw plane address from "
        "detail::k_vnni_access::plane, which no production code takes.")

W = 700


def fig():
    fid = "kv_cache-d6"
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    boxes = []
    o.append(text(20, 18, "book::fill_random -> fill_storage_slot: the test-only whole-plane fill",
                  12.5, weight=700))
    o.append(fn_cell(20, 30, 660, 74, "book::fill_random(gen)",
                     ["fills all kv_block data with random values; for testing only; \"the one "
                      "documented exception to the typed packed-V and packed-K",
                      "access rules (Note [VNNI Packed V layout], Note [K VNNI storage]): it "
                      "interprets no coordinates and marks no token complete\"",
                      "for_each_active_slot -> fill_storage_slot<geometry>(kv_storage_offset(slot)"
                      ", dis, gen); the EAGLE storage too when present"],
                     "kv_cache.hpp:1334-1349", "changed"))
    boxes.append(("book::fill_random", "kv_cache.hpp:1334-1349 (comment 1334-1340)"))
    o.append(arrow(fid, "ink", [(350, 104), (350, 122)], C["ink"], 1.2))
    o.append(text(358, 118, "per active slot, and the EAGLE storage", 8.5, fill=C["muted"]))
    o.append(fn_cell(20, 124, 660, 60, "fill_storage_slot<geometry>(offset, distribution, gen)",
                     ["for every KV head and every page: block = kv_block_at_storage<geometry>"
                      "(offset, kv_head, pg), then fill k and v",
                      "private: the body of fill_random"],
                     "kv_cache.hpp:1766-1786", "changed"))
    boxes.append(("fill_storage_slot", "kv_cache.hpp:1766-1786"))
    ty = 200
    o.append(rect(200, ty, 300, 30, "#fff", C["ink"], 1.2, 4))
    o.append(text(350, ty + 19, "if constexpr (k_vnni::layout_on<geometry.head_size>)", 8.5,
                  "middle", True, weight=700))
    o.append(cite(196, ty + 19, "kv_cache.hpp:1772"))
    o.append(arrow(fid, "ink", [(350, 184), (350, ty - 2)], C["ink"], 1.2))
    oy = ty + 52
    o.append(arrow(fid, "vnni", [(300, ty + 30), (300, oy - 2)], C["vnni"], 1.4))
    o.append(text(292, oy - 8, "true", 9, "end", fill=C["vnni"], weight=700))
    o.append(arrow(fid, "rm", [(400, ty + 30), (400, oy - 2)], C["rm"], 1.4))
    o.append(text(408, oy - 8, "false", 9, fill=C["rm"], weight=700))
    o.append(rect(20, oy, 320, 110, C["vnni_fill"], C["vnni"], 1.4, 5))
    o.append(text(28, oy + 16, "packed K plane", 10, mono=True, weight=700))
    o.append(tag(332, oy + 16, "new"))
    vl = ["bf16* k = detail::k_vnni_access::plane(block.k.as_view());",
          "for i in 0 .. page_size * head_size: k[i] = bf16(dist(gen))",
          "the raw plane address: the one route from a view to it,",
          "a friend of k_vnni_view; its users are listed in Note",
          "[K VNNI storage]: store_row / load_row / copy_token,",
          "k_vnni::qk_group, and this fill (the documented exception)"]
    for s in vl:
        fit(s, 8.5, 304, False, "d6 vnni")
    o.append(lines(28, oy + 30, vl, 8.5, 11))
    o.append(cite(336, oy + 106, "kv_cache.hpp:1773-1776, 701-704; tensor/k_vnni.hpp:188-194"))
    boxes += [("detail::k_vnni_access::plane(block.k.as_view())", "kv_cache.hpp:1773; tensor/k_vnni.hpp:188-194"),
              ("the documented exception (Note [K VNNI storage])", "kv_cache.hpp:701-704, 1337-1340")]
    o.append(rect(360, oy, 320, 110, C["rm_fill"], C["rm"], 1.4, 5))
    o.append(text(368, oy + 16, "native K", 10, mono=True, weight=700))
    o.append(tag(672, oy + 16, "unchanged", C["muted"], size=8.5))
    rl = ["for (auto& value : block.k)",
          "  value = static_cast<bf16>(distribution(gen));",
          "the bf16 array is iterated directly (the two removed lines",
          "are this loop, re-indented under the else)"]
    for s in rl:
        fit(s, 8.5, 304, False, "d6 rm")
    o.append(lines(368, oy + 30, rl, 8.5, 11))
    o.append(cite(676, oy + 106, "kv_cache.hpp:1777-1781"))
    boxes.append(("native K: for (auto& value : block.k), the array loop", "kv_cache.hpp:1777-1781; removed lines anchored at 1772"))
    vy = oy + 122
    o.append(rect(20, vy, 660, 30, C["soft"], C["line"], 1, 4))
    o.append(text(28, vy + 19, "then V, unchanged: bf16* v = detail::v_vnni_access::plane(block.v."
                  "as_view()); the same loop over page_size * head_size values", 8.5))
    o.append(cite(676, vy + 26, "kv_cache.hpp:1782-1784"))
    boxes.append(("detail::v_vnni_access::plane (V, unchanged)", "kv_cache.hpp:1782-1784"))
    ny = vy + 44
    o.append(rect(20, ny, 660, 66, "#fff", C["ink"], 1.1, 5))
    o.append(text(28, ny + 16, "Note [KV block lifetime], the paragraph this PR rewrites", 10,
                  weight=700))
    o.append(tag(672, ny + 16, "changed", C["muted"], size=8.5))
    nl = ["\"K and V are separate members: a bf16 array, or a trivially copyable owner "
          "(k_vnni_tensor for packed K, v_vnni_tensor for packed V).",
          "Fill each member separately. SIMD load addresses inside a packed plane come from "
          "the plane's access helper (detail::k_vnni_access,",
          "detail::v_vnni_access). SIMD operations still use compiler intrinsics, but do not "
          "require vector objects in the stored plane.\""]
    for s in nl:
        fit(s, 8.5, 644, False, "d6 note")
    o.append(lines(28, ny + 30, nl, 8.5, 11))
    o.append(cite(676, ny + 62, "kv_cache.hpp:1577-1582"))
    boxes.append(("Note [KV block lifetime] paragraph on the K and V members", "kv_cache.hpp:1577-1582"))
    H = ny + 76
    cap = ("Updates B3 row 6: the test-only fill. fill_random walks every active slot and "
           "calls fill_storage_slot, which walks every KV head and page of the slot. For a "
           "VNNI slot the new branch takes the raw plane address through "
           "detail::k_vnni_access::plane and writes random bf16 over all 8192 values; this "
           "is the one documented exception to the rule that only the typed operations "
           "compute a packed address. For native K the array loop is unchanged under the "
           "else. V keeps its own access helper. The rewritten paragraph of Note [KV block "
           "lifetime] names both kinds of member.")
    legend = [
        ("box", "white box, ink outline: fill_random, fill_storage_slot, the if constexpr "
                "test and the Note paragraph: name in bold monospace, text in sans-serif"),
        ("vnni", "blue: the packed K branch, the raw plane address from "
                 "detail::k_vnni_access::plane; blue text = the 'true' label"),
        ("rm", "orange: the native K branch, the array loop, unchanged; orange text = the "
               "'false' label"),
        ("ctx", "grey box, thin grey outline: the V fill, unchanged"),
        ("arrow", "ink arrow: a call or the next step"),
        ("blue arrow: the layout_on true branch", "arrow", C["vnni"]),
        ("orange arrow: the layout_on false branch", "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = the branch this PR adds; 'changed' = a function or comment "
                     "it changes; 'unchanged' = kept as it was"),
    ]
    return figure(fid, W, H, "The test-only fill reaches a packed plane through detail::k_vnni_access",
                  "".join(o), cap, boxes=boxes, legend=legend)
