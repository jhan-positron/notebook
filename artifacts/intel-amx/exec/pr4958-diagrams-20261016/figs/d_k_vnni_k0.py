"""Change diagram of unit k0 of the PR 4958 k_vnni.hpp page: the header
comment names store_block among the typed operations and page::set_k_block
among the page accessors (head lines 2-9, 32-39).
"""
from svg_helpers import C, arrow, cite, figure, label_box, lines, marker_defs, rect, text, text_width
from base_k_vnni import _w

BASE = ("Updates B3: the header's two lists gain the new block save: store_block joins "
        "the typed operations that move rows into the plane, and page::set_k_block joins "
        "the page accessors built on them; the rule on who may compute a packed address "
        "is unchanged.")

W = 700


def fig():
    fid = "k_vnni-d0"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "gone": C["gone"]})]
    o.append(text(20, 18, "the header comment: two lists change, one rule stays", 12, weight=700))
    # before
    o.append(text(20, 42, "before (base 26b86a279a)", 10, weight=700, fill=C["gone"]))
    o.append(rect(20, 48, 320, 62, "#fff", C["gone"], 1.2, 5, "5 3"))
    o.append(text(28, 64, "the vector operations that move whole token", 9.5, fill=C["gone"]))
    o.append(text(28, 76, "rows in and out: store_row, load_row, copy_token", 9.5, mono=True,
                  fill=C["gone"]))
    o.append(text(28, 92, "page accessors: set_k_row, get_k_row, k_packed", 9.5, mono=True,
                  fill=C["gone"]))
    o.append(text(28, 104, "removed", 9, fill=C["gone"], weight=700))
    o.append(cite(336, 106, "base k_vnni.hpp:6, 37"))
    boxes.append(("store_row, load_row, copy_token (the base list)", "base k_vnni.hpp:6"))
    # after
    o.append(text(360, 42, "head b39765ec29", 10, weight=700))
    o.append(rect(360, 48, 320, 62, "#fff", C["ink"], 1.2, 5))
    o.append(text(368, 64, "the vector operations that move whole token", 9.5))
    o.append(text(368, 76, "rows in and out: store_row, load_row,", 9.5, mono=True))
    o.append(text(368, 88, "store_block, copy_token", 9.5, mono=True))
    o.append(text(368, 104, "new", 9, fill=C["new"], weight=700))
    o.append(cite(676, 106, "k_vnni.hpp:5-6"))
    boxes.append(("store_row, load_row, store_block, copy_token", "k_vnni.hpp:5-6"))
    o.append(arrow(fid, "ink", [(340, 79), (356, 79)], C["ink"], 1.4))
    # the accessors
    o.append(rect(360, 122, 320, 62, "#fff", C["ink"], 1.2, 5))
    o.append(text(368, 138, "page accessors built on the typed operations:", 9.5))
    o.append(text(368, 150, "page::set_k_row, page::get_k_row,", 9.5, mono=True))
    o.append(text(368, 162, "page::set_k_block, page::k_packed", 9.5, mono=True))
    o.append(text(368, 178, "new", 9, fill=C["new"], weight=700))
    o.append(cite(676, 180, "k_vnni.hpp:35-37"))
    boxes.append(("page::set_k_row, page::get_k_row, page::set_k_block, page::k_packed",
                  "k_vnni.hpp:36-37"))
    o.append(arrow(fid, "ink", [(340, 153), (356, 153)], C["ink"], 1.4))
    o.append(text(20, 140, "the accessor list of the same paragraph", 9.5, fill=C["muted"]))
    o.append(text(20, 152, "(line 37 at the base, line 36-37 at the head)", 9.5, fill=C["muted"]))
    # the rule, unchanged
    o.append(rect(20, 200, 660, 74, C["soft"], C["line"], 1, 5))
    o.append(text(28, 216, "Who may compute a packed address (unchanged)", 10.5, weight=700))
    rl = ["the typed operations in this header, and the two layout-specific score kernels",
          "(k_vnni::qk_group and amx_attn_h128g4::qk_vnni_128x4), which reach the plane through",
          "detail::k_vnni_access. Cache code, the model, hardware staging and the tests use the",
          "typed operations or the page accessors built on them."]
    for r in rl:
        _w(r, 9.5, 640, where="d0 rule")
    o.append(lines(28, 230, rl, 9.5, 11))
    o.append(cite(676, 270, "k_vnni.hpp:32-39"))
    boxes.append(("Who may compute a packed address", "k_vnni.hpp:32-39"))
    # the other comment edits
    o.append(text(20, 296, "the two other comment edits of this unit:", 10, weight=700))
    el = ["lines 6-8: the sentence on the readers is re-wrapped after the longer list",
          "(the AVX-512 score reader in kernels/k_vnni.hpp, the AMX QK kernel in amx_attn_iface.hpp);",
          "the header still points at Note [K VNNI storage] (kv_cache.hpp) for who writes and",
          "reads the layout: its item 1 now names set_k_block and the sharing with the helpers."]
    for e in el:
        _w(e, 9.5, 660, where="d0 edits")
    o.append(lines(20, 310, el, 9.5, 11, fill=C["ink"]))
    o.append(text(20, 360, "[k_vnni.hpp:6-9; kv_cache.hpp:712-724]", 8.5, mono=True, fill=C["cite"]))
    H = 372
    cap = ("Updates B3: the header comment of the file lists the typed operations and the "
           "page accessors a reader may use. This unit adds store_block to the first list "
           "and page::set_k_block to the second. The rule on who may compute a packed "
           "address (the grey box) does not change: store_block is one of the typed "
           "operations it already covers.")
    legend = [
        ("gone", "red dashed box, red text: the base text of the two lists, before this PR"),
        ("box", "white box, ink outline: the head text of the two lists"),
        ("ctx", "grey box, thin grey outline: the unchanged rule of the header"),
        ("arrow", "ink arrow: base text -> head text of the same list"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = the names this PR adds to a list; red 'removed' = the base "
                     "wording"),
    ]
    return figure(fid, W, H, "The header comment: store_block and page::set_k_block join the "
                  "lists", "".join(o), cap, boxes=boxes, legend=legend)
