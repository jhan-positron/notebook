"""Change diagram of unit c5 (kv_cache.hpp page of PR 4956): copy_storage_slot copies
a whole page as one owner assignment and any other range token by token.

Head lines 2331-2355 (with the nine removed lines).
"""
from svg_helpers import C, arrow, cite, figure, fn_cell, lines, marker_defs, rect, text
from base_kv_cache import fit, plane_strip, tag

BASE = ("Updates B3 row 4 and B4 row 2: the page-copy path is opened into the two K copy "
        "paths of a VNNI slot (a whole page = one owner assignment; any other range = "
        "copy_token per token), the unchanged row-major memcpy now under the else "
        "branch, and the worked example's two copies.")

W = 700


def fig():
    fid = "kv_cache-d5"
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"], "gone": C["gone"]})]
    boxes = []
    o.append(text(20, 18, "copy_storage_slot<geometry>(offset, src_page, src_begin, dst_begin, "
                  "count): the K copy per KV head", 11.5, weight=700))
    o.append(cite(W - 20, 32, "kv_cache.hpp:2324-2330"))
    boxes.append(("copy_storage_slot", "kv_cache.hpp:2324-2361"))
    # before
    by = 40
    o.append(rect(20, by, 660, 50, "#fff", C["gone"], 1.4, 5, "6 3"))
    o.append(text(28, by + 16, "before: one memcpy of count * head_size * sizeof(bf16) bytes "
                  "per KV head, k_at(src_begin) -> k_at(dst_begin), every slot",
                  9, fill=C["gone"]))
    o.append(tag(672, by + 46, "before (moved to the else branch)", C["gone"], size=8.5))
    o.append(text(28, by + 30, "the nine removed lines are the same memcpy, re-indented under "
                  "the new else (the deletion anchor is head line 2331)", 8.5, fill=C["muted"]))
    o.append(cite(28, by + 46, "base kv_cache.hpp:2173-2181", "start"))
    boxes.append(("before: the unconditional memcpy (removed lines)", "base kv_cache.hpp:2173-2181; anchor at head 2331"))
    # the test
    ty = by + 66
    o.append(rect(200, ty, 300, 30, "#fff", C["ink"], 1.2, 4))
    o.append(text(350, ty + 19, "if constexpr (k_vnni::layout_on<geometry.head_size>)", 8.5,
                  "middle", True, weight=700))
    o.append(cite(196, ty + 19, "kv_cache.hpp:2331"))
    boxes.append(("if constexpr (k_vnni::layout_on<geometry.head_size>) in copy_storage_slot", "kv_cache.hpp:2331"))
    oy = ty + 52
    o.append(arrow(fid, "vnni", [(260, ty + 30), (260, oy - 2)], C["vnni"], 1.4))
    o.append(text(252, oy - 8, "true", 9, "end", fill=C["vnni"], weight=700))
    o.append(arrow(fid, "rm", [(440, ty + 30), (440, oy - 2)], C["rm"], 1.4))
    o.append(text(448, oy - 8, "false", 9, fill=C["rm"], weight=700))
    # VNNI branch
    o.append(rect(20, oy, 420, 160, C["vnni_fill"], C["vnni"], 1.4, 5))
    o.append(text(28, oy + 16, "VNNI slot: src_block / dst_block = the two kv_blocks", 10,
                  mono=True, weight=700))
    o.append(tag(432, oy + 16, "new"))
    o.append(text(28, oy + 30, "\"A token's column depends on its offset in the page. So only a "
                  "whole page copies as one block,", 8.5))
    o.append(text(28, oy + 41, "and any other range goes token by token.\"", 8.5))
    o.append(rect(28, oy + 50, 196, 96, "#fff", C["vnni"], 1.1, 4))
    o.append(text(36, oy + 64, "src_begin == 0 && dst_begin == 0 &&", 8.5, mono=True, weight=700))
    o.append(text(36, oy + 75, "count == page_size", 8.5, mono=True, weight=700))
    o.append(lines(36, oy + 90, ["dst_block.k = src_block.k", "one owner assignment: 16 KiB,",
                                 "k_vnni_tensor is trivially", "copyable (static_assert)"], 8.5, 11))
    o.append(cite(220, oy + 142, "kv_cache.hpp:2337-2338, 2569-2572"))
    o.append(rect(236, oy + 50, 196, 96, "#fff", C["vnni"], 1.1, 4))
    o.append(text(244, oy + 64, "else: for i in 0..count", 8.5, mono=True, weight=700))
    o.append(lines(244, oy + 79, ["copy_token(dst_block.k.as_view(),", "   dst_begin + i,",
                                  "   src_block.k.as_view(), src_begin + i)",
                                  "= load_row + store_row per token;", "the token's new offset "
                                  "decides its", "new column"], 8.5, 11))
    o.append(cite(428, oy + 142, "kv_cache.hpp:2339-2343; k_vnni.hpp:286-297"))
    boxes += [("whole page: dst_block.k = src_block.k", "kv_cache.hpp:2337-2338; k_vnni_tensor trivially copyable 2569-2572"),
              ("other ranges: copy_token per token", "kv_cache.hpp:2339-2343; tensor/k_vnni.hpp:286-297")]
    # row-major branch
    o.append(rect(460, oy, 220, 160, C["rm_fill"], C["rm"], 1.4, 5))
    o.append(text(468, oy + 16, "row-major slot", 10, mono=True, weight=700))
    o.append(tag(672, oy + 16, "unchanged", C["muted"], size=8.5))
    rl = ["\"The .k data is contiguous, so we",
          "can simply memcpy each head.\"",
          "k_size = head_size * sizeof(bf16)",
          "memcpy(k_at(dst_begin).data,",
          "  src k_at(src_begin).data,",
          "  count * k_size)",
          "k_at exists for native K only (C1)"]
    for s in rl:
        fit(s, 8.5, 204, False, "d5 rm")
    o.append(lines(468, oy + 32, rl, 8.5, 11))
    o.append(cite(676, oy + 156, "kv_cache.hpp:2345-2355"))
    boxes.append(("row-major slot: memcpy (else branch)", "kv_cache.hpp:2345-2355"))
    # V unchanged
    vy = oy + 172
    o.append(rect(20, vy, 660, 30, C["soft"], C["line"], 1, 4))
    o.append(text(28, vy + 19, "then, for every slot: \"The .v data is interleaved in token pairs, "
                  "so we copy individual tokens\": append_v per token (unchanged)", 8.5))
    o.append(cite(676, vy + 26, "kv_cache.hpp:2356-2359"))
    boxes.append(("append_v per token (V, unchanged)", "kv_cache.hpp:2305-2322, 2356-2359"))
    # worked example
    wy = vy + 46
    o.append(text(20, wy + 12, "worked example: two copies of the K plane of (slot 5, kv_head 0)",
                  10.5, weight=700))
    o.append(text(20, wy + 30, "page 7 ->", 9, weight=600))
    o.append(plane_strip(80, wy + 20, 260, 14, label=False))
    o.append(text(350, wy + 30, "41 tokens, offsets 0..40 -> page 9, offsets 0..40:", 9))
    o.append(text(350, wy + 42, "count 41 != page_size: 41 copy_token calls", 9, weight=600))
    o.append(plane_strip(80, wy + 52, 260, 14, label=False))
    o.append(text(20, wy + 62, "page 9", 9, weight=600))
    o.append(text(350, wy + 62, "(41 load_row + 41 store_row = 328 gathers and scatters)", 8.5,
                  fill=C["muted"]))
    o.append(plane_strip(80, wy + 84, 260, 14, live=range(64), hi=None, label=False))
    o.append(text(20, wy + 94, "a full page", 9, weight=600))
    o.append(text(350, wy + 94, "64 tokens, offset 0 -> offset 0: one owner assignment of 16 KiB",
                  9, weight=600))
    o.append(text(20, wy + 118, "tests: the partial range (append of 20 tokens into a page that "
                  "holds 5) and the whole page (append of a full page into an empty book)", 8.5))
    o.append(cite(20, wy + 130, "t_k_vnni_layout.cpp:379-436", "start"))
    boxes.append(("the append tests of both copy paths", "t_k_vnni_layout.cpp:379-436"))
    H = wy + 140
    cap = ("Updates B3 row 4 and B4 row 2: how copy_storage_slot copies the K plane of one "
           "KV head. The old unconditional memcpy (red dashed) survives unchanged under the "
           "new else branch for row-major slots. A VNNI slot has two paths: when the range "
           "is the whole page the owner is assigned as one 16 KiB value, because "
           "k_vnni_tensor is trivially copyable; any other range moves token by token with "
           "copy_token, because a token's offset in the page decides its column. The worked "
           "example shows both: 41 tokens of page 7 into page 9, and a full page.")
    legend = [
        ("gone", "red dashed: before: the unconditional memcpy, now the else branch"),
        ("box", "white box, ink outline: the if constexpr test"),
        ("vnni", "blue: the VNNI branch and its two paths, and a saved token column of a "
                 "plane strip; blue text = the 'true' label"),
        ("white box, blue outline: one of the two VNNI copy paths", "#fff", C["vnni"], False,
         False),
        ("hi", "pale yellow: token 37 in the plane strips"),
        ("empty", "grey dashed: a token column with no row saved"),
        ("rm", "orange: the row-major branch (memcpy, unchanged); orange text = the 'false' "
               "label"),
        ("ctx", "grey box, thin grey outline: the V copy, unchanged"),
        ("blue arrow: the layout_on true branch", "arrow", C["vnni"]),
        ("orange arrow: the layout_on false branch", "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = the VNNI branch this PR adds; 'unchanged' = the memcpy "
                     "kept; red 'before' = where the memcpy stood"),
    ]
    return figure(fid, W, H, "copy_storage_slot: a whole page as one owner assignment, other ranges token by token",
                  "".join(o), cap, boxes=boxes, legend=legend)
