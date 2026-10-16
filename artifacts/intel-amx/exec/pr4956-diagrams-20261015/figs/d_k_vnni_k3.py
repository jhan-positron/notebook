"""Change diagram D3 of the PR 4956 page for h/tron/tensor/k_vnni.hpp:
unit k3, "The typed owner, its views and the one access route" (head lines
110-195, new data model). Line numbers are head lines of PR 4956 (a5697f86d3).
"""
import sys

from svg_helpers import (C, arrow, figure, label_box, line, lines, marker_defs,
                         rect, text, text_width)
from base_k_vnni import EX, PAGE_7, SLOT_5, KV_HEAD_0

BASE = ("Updates B2: redraws the owner, its two views and the one access route "
        "of lines 110-195 at half width beside the code, adds the worked-example "
        "instance (the K plane of KV head 0, storage slot 5, page 7; at(37, 70) = "
        "data_[5226]). The routes that do not exist (as_view() on a temporary, the "
        "reverse view conversion, a view from a bare pointer) are drawn grey and "
        "dashed with the word deleted.")


def _w(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _box(o, boxes, x, y, w, h, title, sub, fill, stroke, ref, size=11, dash=None,
         reg=None):
    _w(title, size, w - 8, True, f"title {title}")
    for s in sub:
        _w(s, size - 1, w - 8, False, f"sub of {title}")
    o.append(label_box(x, y, w, h, title, sub, fill, stroke, size, ref=ref, dash=dash))
    boxes.append((title, reg or ref))


def fig():
    fid = "k_vnni-d3"
    W = 700
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    o.append(text(16, 14, f"worked example: the plane of KV head {KV_HEAD_0}, slot "
                  f"{SLOT_5}, page {PAGE_7} = kv_block.k; new unless marked 'changed'",
                  10, weight=600))
    r1y, r1h = 24, 62
    _box(o, boxes, 16, r1y, 300, r1h, "detail::kv_block::k", [
        "k_storage = k_vnni_tensor<64, 128> for a VNNI slot",
        "(changed; native_k_storage for a row-major slot)"],
        C["soft"], C["ink"], "kv_cache.hpp:2565-2575")
    _box(o, boxes, 400, r1y, 284, r1h, "page::k_packed(slot, kv_head)", [
        "kv_block.k.as_view() on the const owner ->",
        "the read-only view, handed to k_vnni::qk_group"],
        C["soft"], C["ink"], "kv_cache.hpp:2041-2051")
    r2y, r2h = 124, 96
    o.append(arrow(fid, "ink", [(90, r1y + r1h), (90, r2y)], C["ink"], 1.4))
    o.append(text(98, 102, "1 kv_block -> 1 K plane (k)", 9.5, fill=C["ink"], weight=600))
    o.append(text(98, 114, "[kv_cache.hpp:2575]", 8.5, mono=True, fill=C["cite"]))
    _box(o, boxes, 16, r2y, 330, r2h, "k_vnni_tensor<64, 128>", [
        "1 owner -> Rows * Cols = 8192 bf16 = 16 KiB:",
        "alignas(64) bf16 data_[Rows * Cols], no separate",
        "allocation, no initialization (the DMA allocation",
        "creates the kv_blocks); trivially copyable"],
        C["vnni_fill"], C["vnni"], "k_vnni.hpp:155-185")
    o.append(arrow(fid, "muted", [(346, 150), (380, 150)], C["muted"], 1.4, "4 3"))
    _box(o, boxes, 380, 128, 258, 70, "as_view() && = delete", [
        "and const&& = delete: no view from a",
        "temporary; a view must not outlive its owner"],
        "#fff", C["muted"], "k_vnni.hpp:175-176", dash="5 3")
    o.append(text(386, 193, "deleted", 9, fill=C["muted"], weight=600))
    o.append(arrow(fid, "ink", [(660, r1y + r1h), (660, 284)], C["ink"], 1.4))
    o.append(lines(652, 236, ["1 (slot, kv_head) ->", "1 read-only view"], 9, 11, "end",
                   fill=C["ink"], weight=600))
    o.append(text(652, 259, "[kv_cache.hpp:2047-2050]", 8.5, "end", True, fill=C["cite"]))
    r3y = 284
    o.append(arrow(fid, "vnni", [(90, r2y + r2h), (90, r3y)], C["vnni"], 1.4))
    o.append(lines(98, 236, ["as_view() &: 1 call -> 1 view;",
                             "TRON(this_lifetimebound): the view",
                             "must not outlive the owner"], 9, 11, fill=C["vnni"],
                   weight=600))
    o.append(text(98, 270, "[k_vnni.hpp:163-167]", 8.5, mono=True, fill=C["cite"]))
    o.append(arrow(fid, "vnni", [(300, r2y + r2h), (300, 252), (480, 252), (480, r3y)],
                   C["vnni"], 1.4))
    o.append(text(308, 246, "as_view() const&: 1 call -> 1 read-only view", 9,
                  fill=C["vnni"], weight=600))
    o.append(text(308, 266, "[k_vnni.hpp:169-173]", 8.5, mono=True, fill=C["cite"]))
    r3h = 134
    vw, rx, rw = 270, 416, 268
    _box(o, boxes, 16, r3y, vw, r3h, "k_vnni_view<bf16, 64, 128>", [
        "the writable view (new): T* data_ (private)",
        "at(token, dim): bounds-checked read",
        "-> data_[k_vnni::index(token, dim)]",
        "no element write: rows enter only through",
        "store_row and copy_token",
        "no public pointer access at all"],
        C["vnni_fill"], C["vnni"], "k_vnni.hpp:119-153")
    o.append(text(24, r3y + r3h - 20,
                  f"worked example: at({EX['token']}, {EX['dim']}) = data_[{EX['index']}]",
                  9.5, mono=True, fill=C["vnni"], weight=600))
    _box(o, boxes, rx, r3y, rw, r3h, "k_vnni_view<const bf16, 64, 128>", [
        "the read-only view (new): the same at() reads",
        "built from a writable view by the converting",
        "constructor; requires(is_const_v<T>), so the",
        "reverse direction does not exist",
        "returned by page::k_packed (kv_cache.hpp:",
        "2047-2050); read by k_vnni::qk_group",
        "(kernels/k_vnni.hpp:34) and by load_row (272)"],
        C["vnni_fill"], C["vnni"], "k_vnni.hpp:119-153; 129-133",
        reg="k_vnni.hpp:119-153 (T = const bf16); converting constructor 129-133")
    gx0, gx1 = 16 + vw, rx
    gm = (gx0 + gx1) / 2
    o.append(lines(gm, 300, ["1 writable ->", "1 read-only:", "copies data_"], 8.5, 10,
                   "middle", fill=C["vnni"], weight=600))
    o.append(arrow(fid, "vnni", [(gx0, 330), (gx1 - 4, 330)], C["vnni"], 1.4))
    o.append(text(gm, 344, "[k_vnni.hpp:129-133]", 8.5, "middle", True, fill=C["cite"]))
    o.append(arrow(fid, "muted", [(gx1, 372), (gx0 + 4, 372)], C["muted"], 1.4, "4 3"))
    o.append(lines(gm, 386, ["never the reverse", "(no such constructor)"], 8.5, 10,
                   "middle", fill=C["muted"], weight=600))
    yb0 = r3y + r3h
    r4y, r4h = yb0 + 50, 58
    o.append(arrow(fid, "ink", [(151, yb0), (151, r4y)], C["ink"], 1.4))
    o.append(text(159, yb0 + 28, "1 view -> 1 T* [k_vnni.hpp:189-193]", 9, fill=C["ink"],
                  weight=600))
    o.append(arrow(fid, "ink", [(470, yb0), (470, r4y)], C["ink"], 1.4))
    o.append(text(478, yb0 + 28, "1 view -> 1 T*", 9, fill=C["ink"], weight=600))
    _box(o, boxes, 16, r4y, 668, r4h, "detail::k_vnni_access::plane(view) -> T*", [
        "the one route from a packed K view to its plane address (new): static, "
        "pure, returns k.data_",
        "forward-declared at 110-114 so k_vnni_view can name it as a friend (144)"],
        "#fff", C["ink"], "k_vnni.hpp:187-195")
    o.append(arrow(fid, "muted", [(664, r4y), (664, yb0 + 2)], C["muted"], 1.4, "4 3"))
    o.append(text(656, yb0 + 20, "T* -> view: no", 8.5, "end", fill=C["muted"],
                  weight=600))
    o.append(text(656, yb0 + 31, "(ctor private)", 8.5, "end", fill=C["muted"],
                  weight=600))
    r5y = r4y + r4h + 36
    ch = 64
    grp_y0, grp_y1 = r5y - 18, r5y + 6 + 2 * (ch + 8) - 2
    o.append(rect(10, grp_y0, 680, grp_y1 - grp_y0, "none", C["muted"], 1, 6, "5 4"))
    o.append(arrow(fid, "ink", [(350, r4y + r4h), (350, grp_y0 - 2)], C["ink"], 1.4))
    o.append(text(16, r5y - 6, "who may take the address (the only callers, Note [K VNNI "
                  "storage])", 9, fill=C["ink"], weight=600))
    o.append(text(684, r5y - 6, "[k_vnni.hpp:31-37; kv_cache.hpp:701-703]", 8.5, "end", True,
                  fill=C["cite"]))
    cons = [
        ("the typed operations in this header", [
            "store_row 259 and load_row 276 take plane(view)",
            "first; copy_token goes through them (295-296)"],
         "k_vnni.hpp:31-33, 251-297"),
        ("k_vnni::qk_group", [
            "the AVX-512 score reader; takes the plane of",
            "the read-only view page::k_packed"],
         "kernels/k_vnni.hpp:34, 56"),
        ("book::fill_storage_slot", [
            "the test-only fill_random body, the documented",
            "exception: plane(block.k.as_view()), whole plane"],
         "kv_cache.hpp:1767, 1772-1773"),
        ("the static_assert checks", [
            "T is bf16 or const bf16 (124); Rows == 64, Cols == 128",
            "(126, 160); sizeof 16 KiB, alignof 64 (181-185)"],
         "k_vnni.hpp:116-117, 124-127, 160-161, 181-185"),
    ]
    for i, (name, sub, ref) in enumerate(cons):
        x = 16 + (i % 2) * 338
        y = r5y + 6 + (i // 2) * (ch + 8)
        fill = C["soft"] if i < 3 else "#fff"
        _box(o, boxes, x, y, 330, ch, name, sub, fill, C["ink"], ref, size=10.5)
    H = grp_y1 + 10
    cap = ("Updates B2: the type model of lines 110-195 drawn beside its code, with the "
           "worked example instance (the K plane of KV head 0, storage slot 5, page 7, "
           "whose at(37, 70) reads data_[5226]) and the routes that do not exist drawn "
           "grey and dashed with the word deleted. Look at the arrows out of "
           "k_vnni_tensor: as_view() & and as_view() const& are the only sources of a "
           "view, as_view() on a temporary is deleted, and a writable view converts to a "
           "read-only one but never back. Below, detail::k_vnni_access::plane is the one "
           "route from a view to the address, and the three grey boxes in the dashed "
           "frame are the only callers that may take it; the fourth box lists the "
           "static_assert checks of the unit. The friend declarations of k_vnni_view are "
           "drawn in B2.")
    legend = [
        ("vnni", "blue: the VNNI types of this header, the owner k_vnni_tensor<64, 128> "
                 "and its two views k_vnni_view<bf16, 64, 128> and k_vnni_view<const bf16, "
                 "64, 128>; blue text = the view-making calls and the worked example "
                 "at(37, 70) = data_[5226]"),
        ("ctx_ink", "grey fill, ink outline: the holder and the accessor in kv_cache.hpp "
                    "(detail::kv_block::k, page::k_packed) and the three callers that may "
                    "take the address"),
        ("box", "white box, ink outline: the one access route "
                "detail::k_vnni_access::plane(view) -> T* and the static_assert checks; "
                "name in bold monospace, description in grey sans-serif"),
        ("deleted", "grey dashed box: as_view() && = delete, the view from a temporary "
                    "that the code does not provide (word 'deleted')"),
        ("grey dashed frame: who may take the address, the only three callers of "
         "plane(view), and the checks", "none", C["muted"], True, False),
        ("blue arrow: a view is made: as_view() & and as_view() const& (owner -> view), "
         "and the converting constructor (writable view -> read-only view)",
         "arrow", C["vnni"]),
        ("arrow", "ink arrow: a containment or a call: kv_block -> its K plane, "
                  "k_packed -> the read-only view, view -> T* through plane(view), "
                  "plane(view) -> its callers"),
        ("arrow_muted", "grey dashed arrow, grey label: a route that does not exist: "
                        "as_view() on a temporary, the reverse view conversion ('never the "
                        "reverse'), a view from a bare T* ('T* -> view: no')"),
        ("font_mono", "monospace = the box titles (the holder, the accessor, the owner, the "
                      "two views, the deleted as_view, plane(view), the three callers and the "
                      "static_assert checks box) and the worked example at(37, 70) = "
                      "data_[5226]"),
        ("font_sans", "sans-serif = the header line, the descriptions under a title, the "
                      "how-many labels on the arrows, the grey labels of the routes that do "
                      "not exist, and the line 'who may take the address'"),
        ("font_cite", "small grey monospace = the lines that define a box or an arrow "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "The typed owner, its views and the one access route",
                  "".join(o), cap, boxes=boxes, legend=legend)
