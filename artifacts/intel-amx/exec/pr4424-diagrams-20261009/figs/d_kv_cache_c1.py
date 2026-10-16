"""Change diagram of unit c1 (kv_cache.hpp page of PR 4424):
kv_block::k becomes a typed owner for VNNI slots.

Head lines 2986-3002 (the owner type, its two static_asserts, the member) and
3017-3038 (k_view / k_at constrained to row-major head sizes). Every label is
an identifier or a comment phrase of the code; every box cites the line or
Note that defines it (verified in facts/kv_cache.json).
"""
from svg_helpers import (C, arrow, block_cell, card_arrow, cite, figure,
                         fn_cell, line, lines, marker_defs, rect, text,
                         text_width)
from base_kv_cache import BLOCK_STATES_EXAMPLE, EXAMPLE, fit

BASE = ("Updates B1: the k member of the kv_block card becomes k_storage, a "
        "std::conditional_t that names k_vnni_tensor for a VNNI slot and "
        "native_k_storage for every other head size (and for 128-dimension heads "
        "when TRON_K_VNNI is off), and the row views k_view / k_at exist only on "
        "the row-major branch.")

FID_A, FID_B = "kv_cache-d1a", "kv_cache-d1b"
W = 700


def tag(x, y, s, col, anchor="end", size=9.5):
    return text(x, y, s, size, anchor, fill=col, weight=700)


def fig_a():
    fid = FID_A
    o = [marker_defs(fid, {"ink": C["ink"], "new": C["new"], "vnni": C["vnni"],
                           "rm": C["rm"], "gone": C["gone"]})]
    boxes = []
    # ---- header -----------------------------------------------------------------
    o.append(text(20, 18, "kv_block<page_size, head_size>: the member k, before and after",
                  12.5, weight=700))
    o.append(cite(W - 20, 18, "kv_cache.hpp:2982-2985"))
    boxes.append(("kv_block", "kv_cache.hpp:2982-2985 (one kv_block = the KV cache of one "
                  "KV head in one KV slot, 2983)"))
    # ---- before: one bf16 array for every head size -------------------------------
    bx, by, bw, bh = 20, 30, 660, 56
    o.append(rect(bx, by, bw, bh, "#fff", C["gone"], 1.4, 5, "6 3"))
    o.append(text(bx + 10, by + 17, "alignas(kv_block_alignment) bf16 k[page_size * head_size]",
                  10.5, mono=True, weight=700, fill=C["gone"]))
    o.append(tag(bx + bw - 10, by + 17, "before (removed)", C["gone"]))
    o.append(text(bx + 10, by + 32, "one row-major array for every head size: k is indexed "
                  "as [p * head_size + i], one row of head_size bf16 values per token",
                  9, fill=C["muted"]))
    o.append(text(bx + 10, by + 45, "k_view() and k_at(i_page) had no requires clause",
                  9, fill=C["muted"]))
    o.append(cite(bx + bw - 6, by + bh - 4, "base kv_cache.hpp:2333-2335, 2350-2374"))
    boxes.append(("bf16 k[page_size * head_size] (before, removed)",
                  "base kv_cache.hpp:2333-2335 (member), 2350-2374 (unconstrained k_view / "
                  "k_at); diff hunks -2330,9 and -2347,30"))
    # ---- arrow before -> after ---------------------------------------------------
    o.append(arrow(fid, "new", [(350, by + bh + 2), (350, 102)], C["new"], 1.6))
    o.append(text(358, 98, "PR 4424", 9, fill=C["new"], weight=700))
    # ---- after: k_storage k -------------------------------------------------------
    ax, ay, aw, ah = 20, 104, 660, 62
    o.append(rect(ax, ay, aw, ah, "#fff", C["new"], 1.6, 5))
    o.append(text(ax + 10, ay + 17, "alignas(kv_block_alignment) k_storage k", 10.5,
                  mono=True, weight=700))
    o.append(tag(ax + aw - 10, ay + 17, "changed", C["new"]))
    s1 = ("k_storage = std::conditional_t<k_vnni::layout_on<head_size>, "
          "k_vnni_tensor<page_size, head_size>, native_k_storage>")
    o.append(text(ax + 10, ay + 33, s1, 9.5, mono=True))
    s2 = ("std::conditional_t only names the unselected type, so a row-major geometry "
          "never instantiates the owner")
    fit(s2, 9, aw - 20, False, "d1 after 2")
    o.append(text(ax + 10, ay + 47, s2, 9, fill=C["muted"]))
    o.append(cite(ax + aw - 6, ay + ah - 4, "kv_cache.hpp:2993-2995, 3002"))
    boxes.append(("k (k_storage)", "kv_cache.hpp:2993-2995 (std::conditional_t), 3002 (the "
                  "member); comment 2986-2991"))
    # ---- the selection: two branches ----------------------------------------------
    hy = 198           # the horizontal rail
    lx, rx = 60, 640   # the two vertical drops
    ty = 232           # top of the type boxes
    o.append(line(350, ay + ah, 350, hy, C["new"], 1.4))
    o.append(line(lx, hy, rx, hy, C["new"], 1.4))
    o.append(arrow(fid, "vnni", [(lx, hy), (lx, ty - 2)], C["vnni"], 1.6))
    o.append(arrow(fid, "rm", [(rx, hy), (rx, ty - 2)], C["rm"], 1.6))
    rl = ["1 kv_block -> 1 k of exactly 1 of the 2 named types;",
          "the other type is never instantiated [kv_cache.hpp:2990-2991]"]
    for s in rl:
        fit(s, 9, 330, False, "d1 rail")
    o.append(lines(358, ay + ah + 12, rl, 9, 11, fill=C["new"], weight=700))
    o.append(lines(lx + 8, hy + 12, ["k_vnni::layout_on<head_size> true:",
                                     "TRON_K_VNNI and head_size == 128"],
                   9, 11, fill=C["vnni"], weight=700))
    o.append(lines(rx - 8, hy + 12, ["k_vnni::layout_on<head_size> false:",
                                     "every other head size, or no TRON_K_VNNI"],
                   9, 11, "end", fill=C["rm"], weight=700))
    boxes.append(("k_vnni::layout_on", "tensor/k_vnni.hpp:119-130 (TRON_K_VNNI: head_size == "
                  "HEAD_SIZE_128; otherwise false)"))
    # ---- left type box: k_vnni_tensor (VNNI slot) ---------------------------------
    vx, vw, vh = 20, 320, 130
    o.append(rect(vx, ty, vw, vh, C["vnni_fill"], C["vnni"], 1.4, 5))
    o.append(text(vx + 10, ty + 16, "k_vnni_tensor<page_size, head_size>", 10.5, mono=True,
                  weight=700))
    o.append(tag(vx + vw - 8, ty + 16, "new", C["new"]))
    vl = ["owns one packed K plane (VNNI layout):",
          "alignas(64) bf16 data_[Rows * Cols]  (private)",
          "Rows == 64 and Cols == 128 only",
          "trivial to construct, copy and destroy; copying an",
          "owner copies the plane"]
    for s in vl:
        fit(s, 9, vw - 20, False, "d1 vnni box")
    o.append(lines(vx + 10, ty + 30, vl, 9, 11))
    ex = f"worked example: slot {EXAMPLE['slot']}, kv_head h, page {EXAMPLE['page']} = 16 KiB"
    fit(ex, 9, vw - 20, False, "d1 example")
    o.append(text(vx + 10, ty + 91, ex, 9, fill=C["muted"]))
    for c in range(4):
        o.append(block_cell(vx + 10 + c * 74, ty + 96, 70, 16, BLOCK_STATES_EXAMPLE[c],
                            f"block {c}", 9))
    o.append(cite(vx + vw - 6, ty + vh - 4, "tensor/k_vnni.hpp:201-236"))
    boxes.append(("k_vnni_tensor", "tensor/k_vnni.hpp:201-236 (struct at 210, data_ at 230, "
                  "sizeof / alignof static_assert at 232-236)"))
    # ---- right type box: native_k_storage (row-major slot) ------------------------
    nx, nw, nh = 360, 320, 130
    o.append(rect(nx, ty, nw, nh, C["rm_fill"], C["rm"], 1.4, 5))
    o.append(text(nx + 10, ty + 16, "native_k_storage", 10.5, mono=True, weight=700))
    o.append(tag(nx + nw - 8, ty + 16, "new", C["new"]))
    nl = ["= bf16[page_size * head_size]",
          "one row of head_size bf16 values per token p:",
          "element (p, i) at [p * head_size + i]",
          "every other head size keeps the row-major plane",
          "(the same bytes as the removed array)"]
    for s in nl:
        fit(s, 9, nw - 20, False, "d1 native box")
    o.append(lines(nx + 10, ty + 30, nl, 9, 11))
    # a small picture of contiguous token rows
    for r in range(5):
        o.append(rect(nx + 10, ty + 88 + r * 6, 120, 4, "#fff", C["rm"], 0.8, 1))
    o.append(text(nx + 136, ty + 96, "token rows p = 0 .. page_size - 1,", 8.5))
    o.append(text(nx + 136, ty + 107, "each head_size bf16, contiguous", 8.5))
    o.append(cite(nx + nw - 6, ty + nh - 4, "kv_cache.hpp:2990-2992"))
    boxes.append(("native_k_storage", "kv_cache.hpp:2990-2992"))
    # ---- access: how each branch is reached ----------------------------------------
    fy = ty + vh + 30
    # left: k.as_view()
    o.append(card_arrow(fid, "vnni", [(100, ty + vh), (100, fy - 2)], C["vnni"],
                        "1 owner -> 1 k_vnni_view per call", label_dx=8, label_dy=3,
                        anchor="start"))
    al = ["the only route to a packed plane: k_vnni_view<bf16> from",
          "an owner, k_vnni_view<const bf16> from a const owner"]
    for s in al:
        fit(s, 9.5, 304, False, "d1 as_view")
    o.append(fn_cell(20, fy, 320, 58, "k.as_view()", al, "tensor/k_vnni.hpp:214-227", "new"))
    boxes.append(("k.as_view() -> k_vnni_view", "tensor/k_vnni.hpp:214-227 (as_view); "
                  "k_vnni_view at 156-199"))
    cl = ["as_view() on a temporary is deleted: a view must not",
          "outlive its owner; no data(), no operator[]",
          "[tensor/k_vnni.hpp:156-199, 214-227]",
          "callers in kv_cache.hpp (the K owner only): k_packed 2123,",
          "set_k_row 2253, get_k_row 2297, set_k_block 2282,",
          "k_row_if_row_major 2348, k_block_to_vnni_at 2229,",
          "k_forget_row 2577, copy_storage_slot 2736-2737,",
          "fill_storage_slot 1836"]
    for s in cl:
        fit(s, 9, 320, False, "d1 as_view callers")
    o.append(lines(20, fy + 72, cl, 9, 11, fill=C["muted"]))
    # right: k_view() and k_at(i_page)
    o.append(card_arrow(fid, "rm", [(620, ty + nh), (620, fy - 2)], C["rm"],
                        "1 plane -> 1 view / 1 row per call", label_dx=-8, label_dy=3,
                        anchor="end"))
    kl = ["the row-major K views: native K only; a packed plane",
          "has no contiguous rows (reached through k.as_view())"]
    for s in kl:
        fit(s, 9.5, 304, False, "d1 k_view")
    o.append(fn_cell(360, fy, 320, 58, "k_view()", kl, "kv_cache.hpp:3017-3030", "changed"))
    boxes.append(("kv_block::k_view", "kv_cache.hpp:3017-3030 (comment 3017-3018, the two "
                  "overloads 3019-3030)"))
    ka = ["row i_page of the row-major K view (native K only):",
          "k_view()[i_page], one row of head_size bf16"]
    for s in ka:
        fit(s, 9.5, 304, False, "d1 k_at")
    o.append(fn_cell(360, fy + 66, 320, 58, "k_at(i_page)", ka, "kv_cache.hpp:3032-3038",
                     "changed"))
    boxes.append(("kv_block::k_at", "kv_cache.hpp:3032-3038 (the two overloads 3033-3038); "
                  "callers 2260, 2304, 2769, 2772"))
    kn = ["new constraint on all four overloads:",
          "requires(!k_vnni::layout_on<head_size>) [3021, 3027, 3034, 3038]",
          "k_view callers: page::k 2046, 2052, 2061, 2070",
          "(4 of its 8 overloads; the row overloads call k()), k_at",
          "k_at callers: set_k_row 2260, get_k_row 2304,",
          "copy_storage_slot 2769, 2772"]
    for s in kn:
        fit(s, 9, 320, False, "d1 k_view notes")
    o.append(lines(360, fy + 138, kn, 9, 11, fill=C["muted"]))
    H = fy + 138 + 6 * 11 + 8
    cap = ("Updates B1 (part a): the k member of the kv_block card is no longer one bf16 "
           "array (dashed red, removed); it is k_storage, a std::conditional_t that names "
           "k_vnni_tensor for a VNNI slot and native_k_storage for every other head "
           "size, and for 128-dimension heads when TRON_K_VNNI is off. Follow the two "
           "branches down: the VNNI owner is reached only through "
           "k.as_view(), and the row views k_view / k_at now exist only on the row-major "
           "branch. The worked example's plane (slot 5, kv_head h, page 7, block "
           "colours as in B1) is 16 KiB on either branch. Part b holds the two "
           "static_asserts.")
    legend = [
        ("gone", "red dashed: before, removed by PR 4424: the array "
                 "bf16 k[page_size * head_size] and its tag 'before (removed)'"),
        ("box", "white box, ink outline: the member k_storage k after the PR, and the "
                "access routes k.as_view(), k_view(), k_at(i_page); name in bold "
                "monospace, description in sans-serif"),
        ("vnni", "blue: the VNNI branch, k_vnni::layout_on<head_size> true (its condition "
                 "in blue text), the owner k_vnni_tensor<page_size, head_size>, and "
                 "block 0 of the worked example (converted)"),
        ("rm", "orange: the row-major branch, k_vnni::layout_on<head_size> false (its "
               "condition in orange text), native_k_storage, and block 2 of the worked "
               "example (row-major rows)"),
        ("orange outlined strips: the contiguous token rows p = 0 .. page_size - 1 "
         "drawn inside native_k_storage", "#fff", C["rm"], False, False),
        ("pend", "orange-red dashed: block 1 of the worked example, complete, may wait "
                 "for its conversion"),
        ("empty", "grey dashed: block 3 of the worked example, no row bit set"),
        ("arrow", "ink arrow: PR 4424, the before box -> the after box"),
        ("blue arrows: the layout_on true branch, and k.as_view(), 1 owner -> "
         "1 k_vnni_view per call", "arrow", C["vnni"]),
        ("orange arrows: the layout_on false branch, and k_view() / k_at(i_page), "
         "1 plane -> 1 view / 1 row per call", "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by PR 4424 (k_vnni_tensor, native_k_storage, "
                     "k.as_view()); 'changed' = changed by it (k, k_view(), k_at(i_page)); "
                     "red 'before (removed)' = the removed array"),
    ]
    return figure(fid, W, H, "kv_block::k before and after: the typed owner for VNNI slots",
                  "".join(o), cap, boxes=boxes, legend=legend)


def fig_b():
    """The two static_asserts on k_storage: both choices of the owner type
    must pass them."""
    fid = FID_B
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    sy = 10
    bandh = 204
    o.append(rect(20, sy, 660, bandh, C["soft"], C["ink"], 1.2, 5))
    o.append(text(30, sy + 16, "two static_asserts on k_storage: both choices must pass "
                  "(kv_cache.hpp:2996-3001)", 10.5, weight=700))
    # check 1: trivial -> Note [KV block lifetime]
    c1x, c1y, c1w, c1h = 30, sy + 26, 300, 100
    o.append(rect(c1x, c1y, c1w, c1h, "#fff", C["new"], 1.2, 4))
    o.append(text(c1x + 8, c1y + 15, "static_assert(", 10, mono=True, weight=700))
    t1 = ["std::is_trivially_default_constructible_v<k_storage> &&",
          "std::is_trivially_copyable_v<k_storage> &&",
          "std::is_trivially_destructible_v<k_storage>,"]
    for s in t1:
        fit(s, 8.5, c1w - 16, True, "d1 check 1")
    o.append(lines(c1x + 8, c1y + 28, t1, 8.5, 11, mono=True))
    m1 = ["\"the DMA allocation creates kv_blocks;",
          "see Note [KV block lifetime]\")"]
    o.append(lines(c1x + 8, c1y + 66, m1, 9, 11, fill=C["ink"]))
    o.append(cite(c1x + c1w - 4, c1y + c1h - 4, "kv_cache.hpp:2996-2999"))
    boxes.append(("static_assert: k_storage is trivially default constructible, copyable "
                  "and destructible", "kv_cache.hpp:2996-2999"))
    # Note [KV block lifetime]
    n1x, n1w = 372, 298
    o.append(rect(n1x, c1y, n1w, c1h, "#fff", C["ink"], 1.2, 4))
    o.append(text(n1x + 8, c1y + 15, "Note [KV block lifetime]", 10, mono=True, weight=700))
    nn = ["try_make_unique_dma_for_overwrite gets the memory",
          "through operator new[], and such a call creates the",
          "kv_block arrays; no bytes are written. This works only",
          "while kv_block and its members stay trivial to",
          "construct and to destroy."]
    for s in nn:
        fit(s, 9, n1w - 16, False, "d1 note")
    o.append(lines(n1x + 8, c1y + 30, nn, 9, 11))
    o.append(cite(n1x + n1w - 4, c1y + c1h - 4, "kv_cache.hpp:1622-1645"))
    boxes.append(("Note [KV block lifetime]", "kv_cache.hpp:1622-1645"))
    gx = (c1x + c1w + n1x) / 2
    o.append(arrow(fid, "ink", [(c1x + c1w + 2, c1y + 52), (n1x - 2, c1y + 52)], C["ink"], 1.4))
    o.append(text(gx, c1y + 44, "checks", 8.5, "middle", fill=C["ink"]))
    # check 2: sizeof
    c2y, c2h = c1y + c1h + 8, 58
    o.append(rect(30, c2y, 640, c2h, "#fff", C["new"], 1.2, 4))
    s4 = ("static_assert(sizeof(k_storage) == page_size * head_size * sizeof(bf16), "
          "\"packed K holds the same bytes as native K\")")
    o.append(text(38, c2y + 15, s4, 9, mono=True, weight=700))
    s5 = ["worked example: page_size 64 x head_size 128 x 2 B = 16 KiB on either branch",
          "static_assert(sizeof(k) == sizeof(v)) at kv_cache.hpp:3015 is unchanged context"]
    for s in s5:
        fit(s, 9, 600, False, "d1 check 2 ex")
    o.append(lines(38, c2y + 30, s5, 9, 11))
    o.append(cite(666, c2y + c2h - 4, "kv_cache.hpp:3000-3001"))
    boxes.append(("static_assert: sizeof(k_storage) == page_size * head_size * sizeof(bf16)",
                  "kv_cache.hpp:3000-3001; sizeof(k) == sizeof(v) at 3015 (unchanged)"))
    H = sy + bandh + 10
    cap = ("Updates B1 (part b): the two static_asserts every k_storage choice must pass. "
           "The first checks that the owner stays trivial to construct, copy and destroy, "
           "which Note [KV block lifetime] needs (the DMA allocation creates the "
           "kv_blocks, no bytes written). The second checks that the packed plane holds "
           "the same bytes as native K: 16 KiB for the worked example on either branch.")
    legend = [
        ("ctx_ink", "grey band, ink outline: the group of the two static_asserts on "
                    "k_storage (kv_cache.hpp:2996-3001)"),
        ("box", "white box, ink outline: each static_assert, and Note [KV block lifetime]; "
                "the assert text in bold monospace, its message and the Note's text in "
                "sans-serif"),
        ("arrow", "ink arrow 'checks': the first static_assert checks what "
                  "Note [KV block lifetime] needs"),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "kv_block::k (part b): the two static_asserts on k_storage",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
