"""Change diagram of unit c1 (kv_cache.hpp page of PR 4956):
kv_block::k becomes a typed owner for VNNI slots.

Head lines 2562-2575 (the owner type, its two static_asserts, the member) and
2590-2610 (k_view / k_at constrained to row-major head sizes).
"""
from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, line, lines,
                         marker_defs, rect, text)
from base_kv_cache import EXAMPLE, fit, plane_strip, tag

BASE = ("Updates B1: the k member of the kv_block card becomes k_storage, a "
        "std::conditional_t that names k_vnni_tensor for a VNNI slot and "
        "native_k_storage for every other head size (and for 128-dimension heads when "
        "TRON_K_VNNI is off); the row views k_view / k_at exist only on the row-major "
        "branch.")

FID_A, FID_B = "kv_cache-d1a", "kv_cache-d1b"
W = 700


def fig_a():
    fid = FID_A
    o = [marker_defs(fid, {"ink": C["ink"], "new": C["new"], "vnni": C["vnni"],
                           "rm": C["rm"], "gone": C["gone"]})]
    boxes = []
    o.append(text(20, 18, "kv_block<page_size, head_size>: the member k, before and after",
                  12.5, weight=700))
    o.append(cite(W - 20, 18, "kv_cache.hpp:2558-2561"))
    boxes.append(("kv_block", "kv_cache.hpp:2558-2561 (one kv_block = the KV cache of one "
                  "KV head in one KV slot, 2559)"))
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
    o.append(cite(bx + bw - 6, by + bh - 4, "base kv_cache.hpp:2388-2390, 2405-2428"))
    boxes.append(("bf16 k[page_size * head_size] (before, removed)",
                  "base kv_cache.hpp:2388-2390 (member), 2405-2428 (unconstrained k_view / "
                  "k_at); deletion anchors at head 2562, 2593, 2599, 2606, 2610"))
    o.append(arrow(fid, "new", [(350, by + bh + 2), (350, 102)], C["new"], 1.6))
    o.append(text(358, 98, "PR 4956", 9, fill=C["new"], weight=700))
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
    o.append(cite(ax + aw - 6, ay + ah - 4, "kv_cache.hpp:2566-2568, 2575"))
    boxes.append(("k (k_storage)", "kv_cache.hpp:2566-2568 (std::conditional_t), 2575 (the "
                  "member); comment 2562-2564"))
    hy = 198
    lx, rx = 60, 640
    ty = 232
    o.append(line(350, ay + ah, 350, hy, C["new"], 1.4))
    o.append(line(lx, hy, rx, hy, C["new"], 1.4))
    o.append(arrow(fid, "vnni", [(lx, hy), (lx, ty - 2)], C["vnni"], 1.6))
    o.append(arrow(fid, "rm", [(rx, hy), (rx, ty - 2)], C["rm"], 1.6))
    rl = ["1 kv_block -> 1 k of exactly 1 of the 2 named types;",
          "the other type is never instantiated"]
    for s in rl:
        fit(s, 9, 330, False, "d1 rail")
    o.append(lines(358, ay + ah + 12, rl, 9, 11, fill=C["new"], weight=700))
    o.append(lines(lx + 8, hy + 12, ["k_vnni::layout_on<head_size> true:",
                                     "TRON_K_VNNI and head_size == 128"],
                   9, 11, fill=C["vnni"], weight=700))
    o.append(lines(rx - 8, hy + 12, ["k_vnni::layout_on<head_size> false:",
                                     "every other head size, or no TRON_K_VNNI"],
                   9, 11, "end", fill=C["rm"], weight=700))
    boxes.append(("k_vnni::layout_on", "tensor/k_vnni.hpp:86-95 (TRON_K_VNNI: head_size == "
                  "HEAD_SIZE_128; otherwise false)"))
    vx, vw, vh = 20, 320, 128
    o.append(rect(vx, ty, vw, vh, C["vnni_fill"], C["vnni"], 1.4, 5))
    o.append(text(vx + 10, ty + 16, "k_vnni_tensor<page_size, head_size>", 10.5, mono=True,
                  weight=700))
    o.append(tag(vx + vw - 8, ty + 16, "new"))
    vl = ["owns one VNNI packed K plane:",
          "alignas(64) bf16 data_[Rows * Cols]  (private)",
          "Rows == 64 and Cols == 128 only",
          "trivially copyable: copying an owner copies the plane",
          "(copy_storage_slot: dst_block.k = src_block.k)"]
    for s in vl:
        fit(s, 9, vw - 20, False, "d1 vnni box")
    o.append(lines(vx + 10, ty + 30, vl, 9, 11))
    ex = f"worked example: slot {EXAMPLE['slot']}, kv_head 0, page {EXAMPLE['page']}: 16 KiB"
    o.append(text(vx + 10, ty + 92, ex, 9, fill=C["muted"]))
    o.append(plane_strip(vx + 10, ty + 98, vw - 20, 14, label=False))
    o.append(cite(vx + vw - 6, ty + vh - 4, "tensor/k_vnni.hpp:155-181"))
    boxes.append(("k_vnni_tensor", "tensor/k_vnni.hpp:155-181 (struct at 159, data_ at 180, "
                  "sizeof / alignof static_assert at 182-186)"))
    nx, nw, nh = 360, 320, 128
    o.append(rect(nx, ty, nw, nh, C["rm_fill"], C["rm"], 1.4, 5))
    o.append(text(nx + 10, ty + 16, "native_k_storage", 10.5, mono=True, weight=700))
    o.append(tag(nx + nw - 8, ty + 16, "new"))
    nl = ["= bf16[page_size * head_size]",
          "one row of head_size bf16 values per token p:",
          "element (p, i) at [p * head_size + i]",
          "every other head size keeps the row-major plane",
          "(the same bytes as the removed array)"]
    for s in nl:
        fit(s, 9, nw - 20, False, "d1 native box")
    o.append(lines(nx + 10, ty + 30, nl, 9, 11))
    for r in range(5):
        o.append(rect(nx + 10, ty + 88 + r * 6, 120, 4, "#fff", C["rm"], 0.8, 1))
    o.append(text(nx + 136, ty + 96, "token rows p = 0 .. page_size - 1,", 8.5))
    o.append(text(nx + 136, ty + 107, "each head_size bf16, contiguous", 8.5))
    o.append(cite(nx + nw - 6, ty + nh - 4, "kv_cache.hpp:2565"))
    boxes.append(("native_k_storage", "kv_cache.hpp:2565"))
    fy = ty + vh + 30
    o.append(card_arrow(fid, "vnni", [(100, ty + vh), (100, fy - 2)], C["vnni"],
                        "1 owner -> 1 k_vnni_view per call", label_dx=8, label_dy=3,
                        anchor="start"))
    al = ["the only route to a packed plane: k_vnni_view<bf16> from",
          "an owner, k_vnni_view<const bf16> from a const owner"]
    for s in al:
        fit(s, 9.5, 304, False, "d1 as_view")
    o.append(fn_cell(20, fy, 320, 58, "k.as_view()", al, "tensor/k_vnni.hpp:162-176", "new"))
    boxes.append(("k.as_view() -> k_vnni_view", "tensor/k_vnni.hpp:162-176 (as_view); "
                  "k_vnni_view at 122-153"))
    cl = ["as_view() on a temporary is deleted: a view must not",
          "outlive its owner; no data(), no operator[]",
          "[tensor/k_vnni.hpp:119-121, 175-176]",
          "callers in kv_cache.hpp (the K owner only): k_packed 2050,",
          "set_k_row 2063, get_k_row 2080, copy_storage_slot 2341,",
          "fill_storage_slot 1773"]
    for s in cl:
        fit(s, 9, 320, False, "d1 as_view callers")
    o.append(lines(20, fy + 72, cl, 9, 11, fill=C["muted"]))
    o.append(card_arrow(fid, "rm", [(620, ty + nh), (620, fy - 2)], C["rm"],
                        "1 plane -> 1 view / 1 row per call", label_dx=-8, label_dy=3,
                        anchor="end"))
    kl = ["the row-major K views: native K only; a packed plane",
          "has no contiguous rows (reached through k.as_view())"]
    for s in kl:
        fit(s, 9.5, 304, False, "d1 k_view")
    o.append(fn_cell(360, fy, 320, 58, "k_view()", kl, "kv_cache.hpp:2590-2602", "changed"))
    boxes.append(("kv_block::k_view", "kv_cache.hpp:2590-2602 (comment 2590, the two "
                  "overloads 2591-2602)"))
    ka = ["row i_page of the row-major K view (native K only):",
          "k_view()[i_page], one row of head_size bf16"]
    for s in ka:
        fit(s, 9.5, 304, False, "d1 k_at")
    o.append(fn_cell(360, fy + 66, 320, 58, "k_at(i_page)", ka, "kv_cache.hpp:2604-2610",
                     "changed"))
    boxes.append(("kv_block::k_at", "kv_cache.hpp:2604-2610 (the two overloads); callers "
                  "2065, 2082, 2350, 2353"))
    kn = ["new constraint on all four overloads:",
          "requires(!k_vnni::layout_on<head_size>) [2593, 2599, 2606, 2610]",
          "k_view callers: page::k 1979, 1985, 1994, 2003",
          "(4 of its 8 overloads; the row overloads call k())",
          "k_at callers: set_k_row 2065, get_k_row 2082,",
          "copy_storage_slot 2350, 2353 (row-major branches)"]
    for s in kn:
        fit(s, 9, 320, False, "d1 k_view notes")
    o.append(lines(360, fy + 138, kn, 9, 11, fill=C["muted"]))
    H = fy + 138 + 6 * 11 + 8
    cap = ("Updates B1 (part a): the k member of the kv_block card is no longer one bf16 "
           "array (dashed red, removed); it is k_storage, a std::conditional_t that names "
           "k_vnni_tensor for a VNNI slot and native_k_storage for every other head size, "
           "and for 128-dimension heads when TRON_K_VNNI is off. Follow the two branches "
           "down: the VNNI owner is reached only through k.as_view(), and the row views "
           "k_view / k_at now exist only on the row-major branch. The worked example's "
           "plane (slot 5, kv_head 0, page 7; offsets 0..40 saved) is 16 KiB on either "
           "branch. Part b holds the two static_asserts.")
    legend = [
        ("gone", "red dashed: before, removed by PR 4956: the array "
                 "bf16 k[page_size * head_size] and its tag 'before (removed)'"),
        ("box", "white box, ink outline: the member k_storage k after the PR, and the "
                "access routes k.as_view(), k_view(), k_at(i_page); name in bold "
                "monospace, description in sans-serif"),
        ("vnni", "blue: the VNNI branch, k_vnni::layout_on<head_size> true (its condition "
                 "in blue text), the owner k_vnni_tensor<page_size, head_size>, and a saved "
                 "token column of the worked example's plane strip"),
        ("hi", "pale yellow: token 37 in the plane strip"),
        ("empty", "grey dashed: a token column with no row saved (offsets 41..63)"),
        ("rm", "orange: the row-major branch, k_vnni::layout_on<head_size> false (its "
               "condition in orange text) and native_k_storage"),
        ("orange outlined strips: the contiguous token rows p = 0 .. page_size - 1 "
         "drawn inside native_k_storage", "#fff", C["rm"], False, False),
        ("arrow", "ink arrow: PR 4956, the before box -> the after box"),
        ("blue arrows: the layout_on true branch, and k.as_view(), 1 owner -> "
         "1 k_vnni_view per call", "arrow", C["vnni"]),
        ("orange arrows: the layout_on false branch, and k_view() / k_at(i_page), "
         "1 plane -> 1 view / 1 row per call", "arrow", C["rm"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by PR 4956 (k_vnni_tensor, native_k_storage, "
                     "k.as_view()); 'changed' = changed by it (k, k_view(), k_at(i_page)); "
                     "red 'before (removed)' = the removed array"),
    ]
    return figure(fid, W, H, "kv_block::k before and after: the typed owner for VNNI slots",
                  "".join(o), cap, boxes=boxes, legend=legend)


def fig_b():
    fid = FID_B
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    sy = 10
    bandh = 204
    o.append(rect(20, sy, 660, bandh, C["soft"], C["ink"], 1.2, 5))
    o.append(text(30, sy + 16, "two static_asserts on k_storage: both choices must pass "
                  "(kv_cache.hpp:2569-2574)", 10.5, weight=700))
    c1x, c1y, c1w, c1h = 30, sy + 26, 300, 100
    o.append(rect(c1x, c1y, c1w, c1h, "#fff", C["new"], 1.2, 4))
    o.append(text(c1x + 8, c1y + 15, "static_assert(", 10, mono=True, weight=700))
    t1 = ["std::is_trivially_default_constructible_v<k_storage> &&",
          "std::is_trivially_copyable_v<k_storage> &&",
          "std::is_trivially_destructible_v<k_storage>,"]
    for s in t1:
        fit(s, 8.5, c1w - 16, True, "d1 check 1")
    o.append(lines(c1x + 8, c1y + 28, t1, 8.5, 11, mono=True))
    o.append(lines(c1x + 8, c1y + 66, ["\"the DMA allocation creates kv_blocks;",
                                       "see Note [KV block lifetime]\")"], 9, 11, fill=C["ink"]))
    o.append(cite(c1x + c1w - 4, c1y + c1h - 4, "kv_cache.hpp:2569-2572"))
    boxes.append(("static_assert: k_storage is trivially default constructible, copyable "
                  "and destructible", "kv_cache.hpp:2569-2572"))
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
    o.append(cite(n1x + n1w - 4, c1y + c1h - 4, "kv_cache.hpp:1559-1582"))
    boxes.append(("Note [KV block lifetime]", "kv_cache.hpp:1559-1582"))
    gx = (c1x + c1w + n1x) / 2
    o.append(arrow(fid, "ink", [(c1x + c1w + 2, c1y + 52), (n1x - 2, c1y + 52)], C["ink"], 1.4))
    o.append(text(gx, c1y + 44, "checks", 8.5, "middle", fill=C["ink"]))
    c2y, c2h = c1y + c1h + 8, 58
    o.append(rect(30, c2y, 640, c2h, "#fff", C["new"], 1.2, 4))
    s4 = ("static_assert(sizeof(k_storage) == page_size * head_size * sizeof(bf16), "
          "\"packed K holds the same bytes as native K\")")
    o.append(text(38, c2y + 15, s4, 9, mono=True, weight=700))
    s5 = ["worked example: page_size 64 x head_size 128 x 2 B = 16 KiB on either branch",
          "static_assert(sizeof(k) == sizeof(v)) at kv_cache.hpp:2588 is unchanged context"]
    for s in s5:
        fit(s, 9, 600, False, "d1 check 2 ex")
    o.append(lines(38, c2y + 30, s5, 9, 11))
    o.append(cite(666, c2y + c2h - 4, "kv_cache.hpp:2573-2574"))
    boxes.append(("static_assert: sizeof(k_storage) == page_size * head_size * sizeof(bf16)",
                  "kv_cache.hpp:2573-2574; sizeof(k) == sizeof(v) at 2588 (unchanged)"))
    H = sy + bandh + 10
    cap = ("Updates B1 (part b): the two static_asserts every k_storage choice must pass. "
           "The first checks that the owner stays trivial to construct, copy and destroy, "
           "which Note [KV block lifetime] needs (the DMA allocation creates the kv_blocks, "
           "no bytes written). The second checks that the packed plane holds the same "
           "bytes as native K: 16 KiB for the worked example on either branch.")
    legend = [
        ("ctx_ink", "grey band, ink outline: the group of the two static_asserts on "
                    "k_storage (kv_cache.hpp:2569-2574)"),
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
