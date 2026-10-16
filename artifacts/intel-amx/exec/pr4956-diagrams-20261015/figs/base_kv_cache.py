"""Base diagrams B1-B5 of the PR 4956 page for h/tron/models/kv_cache.hpp.

Exports for the change diagrams (from base_kv_cache import ...):
  worked example: EXAMPLE, LIVE_TOKENS, vnni_index, rm_elem
  building blocks: fit, plane_strip, panel_grid, rm_rows, caller_cell, ops_cell,
    lane_set, lane_block, nx_box (does not exist), tag

Every label is an identifier or a comment phrase of the code; every box cites
the line or Note that defines it (head line numbers of kv_cache.hpp at
a5697f86d3, or <file>:<line> for other files).
"""
import sys

from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, label_box,
                         lane, line, lines, marker_defs, rect, text, text_width,
                         work_block)

# ---- the worked example of the page (STYLE.md) -----------------------------
# Page 7, storage slot 5, KV head 0, a VNNI slot; the K rows of offsets 0..40
# are saved; token 37 = block c 2, lane t 5; dimension 70 = step s 2, pair dp 3,
# j 0.
LIVE_TOKENS = list(range(0, 41))


def vnni_index(token, dim):
    """k_vnni::index(token, dim) (tensor/k_vnni.hpp:97-106)."""
    s, c, dp, t, j = dim // 32, token // 16, (dim % 32) // 2, token % 16, dim % 2
    return (((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j


def rm_elem(token, dim, head_size=128):
    """Element index of K[token][dim] in native K: [p * head_size + i]
    (kv_cache.hpp:2562-2565)."""
    return token * head_size + dim


EXAMPLE = dict(page=7, slot=5, kv_head=0, token=37, dim=70, block=2, t=5, step=2,
               pair=3, j=0, index=vnni_index(37, 70), panel=2 * 4 + 2,
               byte=vnni_index(37, 70) * 2, rm_index=rm_elem(37, 70),
               rm_byte=rm_elem(37, 70) * 2, live=LIVE_TOKENS, kv_mul=4)
assert EXAMPLE["index"] == 5226 and EXAMPLE["rm_index"] == 4806


def fit(s, size, w, mono=False, where=""):
    """Warn on stderr when a string is wider than w px (see the PNG too)."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' {tw:.0f} > {w}", file=sys.stderr)
    return s


def tag(x, y, s, col=None, anchor="end", size=9.5):
    return text(x, y, s, size, anchor, fill=col or C["new"], weight=700)


# ---- building blocks -----------------------------------------------------------
def plane_strip(x, y, w, h, live=LIVE_TOKENS, hi=37, label=True):
    """One K plane as 64 token columns (page offsets 0..63): blue = the row is
    saved, grey dashed = no row saved, the worked example's token outlined."""
    cw = w / 64
    o = []
    for t in range(64):
        on = t in live
        o.append(rect(x + t * cw, y, cw, h, C["vnni_fill"] if on else C["empty_fill"],
                      C["vnni"] if on else C["empty"], 0.6, 0, None if on else "2 2"))
    if hi is not None:
        o.append(rect(x + hi * cw, y, cw, h, C["hi_fill"], C["ink"], 1.4, 0))
    if label:
        for t in (0, 16, 32, 48, 63):
            o.append(text(x + t * cw + cw / 2, y + h + 10, str(t), 8.5, "middle", True,
                          fill=C["muted"]))
    return "".join(o)


def panel_grid(x, y, cw=70, ch=40, gapx=4, gapy=4, hi_panel=None, block=None):
    """The 16 panels (s, c) of one VNNI plane: rows s = 0..3 (dimension step),
    columns c = 0..3 (token block), panel index 4 s + c."""
    o = []
    for c in range(4):
        o.append(text(x + c * (cw + gapx) + cw / 2, y - 8, f"c = {c}", 9.5, "middle",
                      fill=C["muted"]))
    for s in range(4):
        o.append(text(x - 8, y + s * (ch + gapy) + ch / 2 + 4, f"s = {s}", 9.5, "end",
                      fill=C["muted"]))
        for c in range(4):
            px, py = x + c * (cw + gapx), y + s * (ch + gapy)
            n = 4 * s + c
            on = hi_panel is not None and n == hi_panel
            o.append(rect(px, py, cw, ch, C["vnni_fill"], C["vnni"], 1.8 if on else 1, 3))
            if on:
                o.append(rect(px + 1.5, py + 1.5, cw - 3, ch - 3, "none", C["ink"], 1.6, 2))
            o.append(text(px + cw / 2, py + 16, f"({s},{c})", 9.5, "middle", True))
            o.append(text(px + cw / 2, py + 30, f"#{n}", 9, "middle", True,
                          fill=C["muted"]))
    if block is not None:
        bx = x + block * (cw + gapx) - 3
        o.append(rect(bx, y - 3, cw + 6, 4 * ch + 3 * gapy + 6, "none", C["ink"], 1.2, 4,
                      "4 3"))
    return "".join(o)


def rm_rows(x, y, w, h, hi=37, n=64):
    """Native K: 64 token rows of 256 bytes, top row = page offset 0."""
    rh = h / n
    o = []
    for p in range(n):
        on = p == hi
        o.append(rect(x, y + p * rh, w, rh, C["hi_fill"] if on else C["rm_fill"],
                      C["ink"] if on else C["rm"], 1.2 if on else 0.4, 0))
    return "".join(o)


def caller_cell(x, y, w, h, lines_, ref):
    """A caller box (soft fill) with up to 3 text lines and its citation."""
    o = [rect(x, y, w, h, C["soft"], C["line"], 1, 4)]
    for s in lines_:
        fit(s, 9.5, w - 14, False, "caller_cell")
    o.append(lines(x + 8, y + 17, lines_, 9.5, 12))
    fit(ref, 8.5, w - 8, True, "caller_cell cite")
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def ops_cell(x, y, w, h, lines_, refs, fill="#fff", stroke=None):
    """A k_vnni.hpp operations box: mono lines and one or two citation lines."""
    o = [rect(x, y, w, h, fill, stroke or C["line"], 1, 4)]
    for s in lines_:
        fit(s, 9.5, w - 14, True, "ops_cell")
    o.append(lines(x + 8, y + 16, lines_, 9.5, 11.5, mono=True))
    ry = y + h - 4 - 10 * (len(refs) - 1)
    for r in refs:
        fit(r, 8.5, w - 8, True, "ops_cell cite")
        o.append(cite(x + w - 4, ry, r))
        ry += 10
    return "".join(o)


def nx_box(x, y, w, h, title, sub, ref):
    """'does not exist': a function or route the code does not provide
    (white box, grey dashed outline)."""
    o = [rect(x, y, w, h, "#fff", C["muted"], 1.2, 4, "5 3"),
         text(x + 8, y + 16, title, 10.5, mono=True, weight=700, fill=C["muted"])]
    ty = y + 30
    for s in sub:
        fit(s, 9, w - 16, False, "nx_box")
        o.append(text(x + 8, ty, s, 9, fill=C["muted"]))
        ty += 11.5
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def lane_set(x, y, w, names, lane_h=80, gap=6):
    o, ys = [], {}
    cy = y
    for lab, sub in names:
        s, x0 = lane(x, cy, w, lane_h, lab, sub)
        o.append(s)
        ys[lab] = cy
        cy += lane_h + gap
    return "".join(o), x + 140, ys


def lane_block(x, y, w, h, lines_, fill, stroke, idle=False, size=8.5, ref=None,
               lh=10.5):
    o = [work_block(x, y, w, h, None, fill, stroke, idle)]
    refs = [] if ref is None else ([ref] if isinstance(ref, str) else list(ref))
    n = len(lines_) + len(refs)
    ty = y + h / 2 - (n - 1) * lh / 2 + 3.5
    for s in lines_:
        fit(s, size, w - 4, False, "lane_block")
        o.append(text(x + w / 2, ty, s, size, "middle"))
        ty += lh
    for r in refs:
        fit(r, 8.5, w - 2, True, "lane_block cite")
        o.append(text(x + w / 2, ty, r, 8.5, "middle", True, fill=C["cite"]))
        ty += lh
    return "".join(o)


# ---- B1: data model -----------------------------------------------------------
def b1():
    fid = "kv_cache-b1"
    W, H = 1000, 660
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    boxes = []
    top, colh = 36, 440
    # ---- column 1: book -------------------------------------------------------
    x, w = 20, 300
    o.append(rect(x, top, w, colh, C["soft"], C["ink"], 1.2, 6))
    o.append(text(x + 12, top + 20, "book", 13, mono=True, weight=700))
    o.append(tag(x + w - 12, top + 20, "changed", C["muted"]))
    o.append(lines(x + 12, top + 36, ["owns one KV memory allocation; a page is a",
                                      "lightweight reference into it"], 9.5, 12,
                   fill=C["muted"]))
    o.append(cite(x + w - 6, top + colh - 5, "Note [KV Memory Layout] (kv_cache.hpp:58)"))
    boxes.append(("book", "kv_cache.hpp:882-883 (struct book); Note [KV Memory Layout] "
                  "kv_cache.hpp:58; changed: fill_storage_slot 1766-1786"))
    sy = top + 62
    o.append(text(x + 12, sy, "storage slots: kv_storage_offset", 10, mono=True))
    cx = x + 12
    for lab, cw in [("slot 0", 50), ("slot 1", 50), ("...", 30), ("slot n-1", 62)]:
        o.append(rect(cx, sy + 8, cw, 24, "#fff", C["ink"], 1, 3))
        o.append(text(cx + cw / 2, sy + 24, lab, 9.5, "middle", True))
        cx += cw + 4
    o.append(rect(cx, sy + 8, 52, 24, C["eagle_fill"], C["eagle"], 1.4, 3))
    o.append(text(cx + 26, sy + 24, "EAGLE", 9.5, "middle", True))
    boxes.append(("storage slot (kv_storage_offset)", "common.hpp:240; count "
                  "storage_slot_count_ kv_cache.hpp:1449, 1036"))
    boxes.append(("EAGLE storage", "kv_cache.hpp:1027-1030 (eagle_storage_offset = "
                  "kv_storage_offset(logical_slot_count()))"))
    o.append(text(x + 12, sy + 46, "count: storage_slot_count_", 9, mono=True))
    o.append(text(x + 12, sy + 58, "= logical_slot_count() + has_eagle_storage()", 9,
                  mono=True))
    o.append(cite(x + 12, sy + 70, "kv_cache.hpp:1036, 1041-1047", "start"))
    o.append(text(x + 12, sy + 84, "EAGLE storage: the extra physical slot at", 9.5,
                  fill=C["muted"]))
    o.append(text(x + 12, sy + 96, "kv_storage_offset(logical_slot_count())", 9,
                  mono=True))
    o.append(cite(x + 12, sy + 108, "kv_cache.hpp:1027-1030", "start"))
    py0 = sy + 126
    o.append(text(x + 12, py0, "pages: std::vector<page_t> pages", 10, mono=True))
    o.append(cite(x + w - 12, py0, "kv_cache.hpp:1448"))
    py = py0 + 8
    for lab, hi in [("page 0", False), ("...", False), ("page 7", True),
                    ("page n_pages-1", False)]:
        o.append(rect(x + 12, py, 130, 22, C["hi_fill"] if hi else "#fff", C["ink"],
                      1.6 if hi else 1, 3))
        o.append(text(x + 77, py + 15, lab, 10, "middle", True,
                      weight=700 if hi else None))
        py += 26
    boxes.append(("pages", "kv_cache.hpp:1448 (std::vector<page_t> pages); one page per "
                  "index 0 .. n_pages-1 (kv_cache.hpp:1623-1624)"))
    ay = py0 + 8 + 2 * 26 + 11
    o.append(arrow(fid, "ink", [(x + 142, ay), (338, ay)], C["ink"], 1.4))
    o.append(text(240, ay - 6, "1 book -> n_pages pages", 9.5, "middle", fill=C["ink"],
                  weight=600))
    o.append(cite(240, ay + 12, "kv_cache.hpp:1623-1624", "middle"))
    ky = py0 + 8 + 4 * 26 + 10
    o.append(rect(x + 12, ky, w - 24, 70, "#fff", C["ink"], 1, 4))
    o.append(text(x + 20, ky + 15, "book::kv_block(slot, kv_head, pg)", 10, mono=True,
                  weight=700))
    o.append(text(x + 20, ky + 29, "the kv_block of one (slot, KV head, page):", 9))
    o.append(text(x + 20, ky + 42, "blocks[(slot.i * n_kv_heads + kv_head) * n_pages + pg]",
                  8.5, mono=True))
    o.append(text(x + 20, ky + 55, "1 (slot, kv_head, pg) -> 1 kv_block", 9, weight=600))
    o.append(cite(x + w - 16, ky + 66, "kv_cache.hpp:1668-1697"))
    boxes.append(("book::kv_block(slot, kv_head, pg)", "kv_cache.hpp:1668-1697 (the "
                  "uniform layout's index formula at 1686)"))
    # ---- column 2: page ------------------------------------------------------
    x, w = 340, 320
    o.append(rect(x, top, w, colh, "#fff", C["ink"], 1.2, 6))
    o.append(text(x + 12, top + 20, "page 7 (page_size = 64 token offsets)", 12,
                  mono=True, weight=700))
    o.append(tag(x + w - 12, top + 34, "changed", C["muted"]))
    o.append(cite(x + w - 6, top + colh - 5, "kv_cache.hpp:1880-1882"))
    boxes.append(("page", "kv_cache.hpp:1880-1882 (page_size = 64 at 1882)"))
    o.append(text(x + 12, top + 50, "a lightweight reference to a section of the book;", 9.5,
                  fill=C["muted"]))
    o.append(text(x + 12, top + 62, "attention proceeds page by page", 9.5, fill=C["muted"]))
    o.append(rect(x + 12, top + 74, w - 24, 44, C["soft"], C["line"], 1, 4))
    o.append(text(x + 20, top + 89, "kv_saves_[page_size][layout_t::n_slots]", 10,
                  mono=True, weight=700))
    o.append(text(x + 20, top + 103, "per-token per-slot save counters, unchanged", 9,
                  fill=C["muted"]))
    o.append(cite(x + w - 16, top + 114, "kv_cache.hpp:2255-2258"))
    boxes.append(("kv_saves_", "kv_cache.hpp:2255-2258 (unchanged context)"))
    o.append(text(x + 12, top + 138, "the K accessors of a page (section 2)", 10, weight=600))
    acc = [("k(slot, kv_head[, i_page])", "row-major slots only", "1974-2039", "changed",
            C["rm"]),
           ("k_packed<geometry>(slot, kv_head)", "VNNI slots only: read-only view",
            "2041-2051", "new", C["vnni"]),
           ("set_k_row / get_k_row", "every slot: one token's row", "2053-2107", "new",
            C["ink"]),
           ("copy_storage_slot", "page copies: append and defrag", "2324-2361", "changed",
            C["ink"])]
    ay2 = top + 148
    for name, desc, ref, tg, col in acc:
        o.append(rect(x + 12, ay2, w - 24, 38, "#fff", col, 1.2, 4))
        o.append(text(x + 20, ay2 + 14, name, 9.5, mono=True, weight=700))
        o.append(tag(x + w - 20, ay2 + 14, tg, C["new"] if tg == "new" else C["muted"], size=9))
        o.append(text(x + 20, ay2 + 28, desc, 9, fill=C["muted"]))
        o.append(cite(x + w - 16, ay2 + 34, f"kv_cache.hpp:{ref}"))
        boxes.append((name.split("(")[0].split(" /")[0], f"kv_cache.hpp:{ref}"))
        ay2 += 42
    o.append(text(x + 12, ay2 + 12, "page::kv_block(slot, kv_head): the page's kv_block", 9,
                  mono=False))
    o.append(text(x + 12, ay2 + 24, "1 page -> layout_t::n_slots x n_kv_heads kv_blocks", 9,
                  weight=600))
    o.append(cite(x + 12, ay2 + 36, "kv_cache.hpp:2282-2292", "start"))
    boxes.append(("page::kv_block(slot, kv_head)", "kv_cache.hpp:2282-2292"))
    o.append(arrow(fid, "ink", [(x + w, top + 200), (678, top + 200)], C["ink"], 1.4))
    # ---- column 3: kv_block --------------------------------------------------
    x, w = 680, 300
    o.append(rect(x, top, w, colh, "#fff", C["ink"], 1.2, 6))
    o.append(text(x + 12, top + 20, "kv_block(slot 5, kv_head 0, page 7)", 11,
                  mono=True, weight=700))
    o.append(tag(x + w - 12, top + 34, "changed", C["muted"]))
    o.append(text(x + 12, top + 46, "the KV cache for one KV head in one KV slot", 9,
                  fill=C["muted"]))
    o.append(cite(x + w - 6, top + colh - 5, "kv_cache.hpp:2558-2561"))
    boxes.append(("kv_block", "kv_cache.hpp:2558-2561 (detail::kv_block); one per (storage "
                  "slot, KV head, page): kv_cache.hpp:1686"))
    fx, fy, fw, fh = x + 12, top + 56, 276, 268
    for k in (3, 2, 1):
        o.append(rect(fx + 5 * k, fy + 5 * k, fw, fh, "#fff", C["line"], 1, 5))
    o.append(rect(fx, fy, fw, fh, "#fff", C["ink"], 1.2, 5))
    o.append(text(fx + 8, fy + 16, "1 kv_block -> KV_BLOCK_PLANES_2 planes (K, V)", 9,
                  weight=600))
    o.append(cite(fx + fw - 6, fy + fh - 5, "kv_cache.hpp:751"))
    boxes.append(("KV_BLOCK_PLANES_2", "kv_cache.hpp:751"))
    # the K plane
    o.append(rect(fx + 8, fy + 24, fw - 16, 112, C["vnni_fill"], C["vnni"], 1.4, 4))
    o.append(text(fx + 16, fy + 40, "k: k_storage", 10.5, mono=True, weight=700))
    o.append(tag(fx + fw - 14, fy + 40, "changed", C["muted"], size=9))
    kl = ["= k_vnni_tensor<page_size, head_size>",
          "  when k_vnni::layout_on<head_size> (VNNI slot)",
          "| native_k_storage: bf16[page_size * head_size]",
          "  otherwise (row-major slot)",
          "64 tokens x 128 bf16 = 16 KiB on either branch"]
    for s in kl:
        fit(s, 8.5, fw - 32, True, "b1 k")
    o.append(lines(fx + 16, fy + 54, kl, 8.5, 11, mono=True))
    o.append(plane_strip(fx + 16, fy + 112, fw - 32, 14, label=False))
    o.append(cite(fx + fw - 14, fy + 133, "kv_cache.hpp:2562-2575"))
    boxes.append(("k (k_storage)", "kv_cache.hpp:2562-2575 (std::conditional_t at "
                  "2566-2568; static_asserts 2569-2574; the member 2575)"))
    boxes.append(("k_vnni_tensor", "tensor/k_vnni.hpp:155-181"))
    boxes.append(("native_k_storage", "kv_cache.hpp:2565"))
    boxes.append(("k_vnni::layout_on", "tensor/k_vnni.hpp:86-95"))
    # the V plane
    o.append(rect(fx + 8, fy + 144, fw - 16, 40, C["soft"], C["line"], 1, 4))
    o.append(text(fx + 16, fy + 160, "v: v_vnni_tensor<page_size, head_size>", 9.5,
                  mono=True, weight=700))
    o.append(text(fx + 16, fy + 174, "the VNNI-packed V plane, unchanged", 9,
                  fill=C["muted"]))
    o.append(cite(fx + fw - 14, fy + 181, "kv_cache.hpp:2576-2585"))
    boxes.append(("v (v_vnni_tensor)", "kv_cache.hpp:2576-2585, unchanged context"))
    under = [("static_assert(sizeof(k) == sizeof(v))", "kv_cache.hpp:2588"),
             ("k.as_view() -> k_vnni_view: the only route in", "tensor/k_vnni.hpp:162-176")]
    uy = fy + 200
    for s, r in under:
        fit(s, 9, fw - 20, False, "b1 under")
        o.append(text(fx + 8, uy, s, 9, weight=600))
        o.append(cite(fx + 8, uy + 10, r, "start"))
        uy += 24
    boxes.append(("k_vnni_view (k.as_view())", "tensor/k_vnni.hpp:122-153; as_view at 162-176"))
    # ---- bottom: the worked example strip ---------------------------------------
    y0 = top + colh + 18
    o.append(line(20, y0, 980, y0, C["line"]))
    o.append(text(20, y0 + 18, "Worked example of this page: page 7, storage slot 5, KV "
                  "head 0 (a VNNI slot). The K rows of page offsets 0..40 are saved, one "
                  "set_k_row per token.", 11, weight=600))
    o.append(plane_strip(20, y0 + 30, 640, 28))
    o.append(text(670, y0 + 42, "blue column = the token's K row is saved (64 pair slots)", 9))
    o.append(text(670, y0 + 54, "grey dashed = no row saved; outlined = token 37", 9))
    o.append(text(20, y0 + 84, "the layout is chosen once, at compile time: "
                  "k_vnni::layout_on<head_size> = TRON_K_VNNI and head_size == 128; every "
                  "reader and writer of a slot sees the same layout", 9.5))
    o.append(cite(20, y0 + 98, "Note [K VNNI storage] kv_cache.hpp:687-695; tensor/k_vnni.hpp:86-95",
                  "start"))
    boxes.append(("Note [K VNNI storage]", "kv_cache.hpp:685-746"))
    cap = ("B1, the data model. A book (the unit of KV memory allocation) holds one "
           "storage slot per layer plus one EAGLE storage (EAGLE is a speculation model "
           "with its own extra physical slot) and n_pages pages of 64 token offsets. One "
           "kv_block holds the K and V planes of one (storage slot, KV head, page). PR "
           "4956 types the K plane of a kv_block: k_storage is k_vnni_tensor for a VNNI "
           "slot and the bf16 array native_k_storage otherwise. The page gains the "
           "accessors listed in its column. The strip at the bottom is the worked "
           "example reused on this page.")
    legend = [
        ("box", "white box, ink outline: a data-model entity (the storage slots, the pages, "
                "the page 7 column, the kv_block column) and the functions drawn "
                "(book::kv_block, set_k_row / get_k_row, copy_storage_slot)"),
        ("ctx_ink", "grey fill, ink outline: the book column"),
        ("ctx", "grey box, thin grey outline: a member this PR leaves unchanged (kv_saves_, "
                "v: v_vnni_tensor)"),
        ("lane", "white frame, thin grey outline: the frames stacked behind the kv_head 0 "
                 "block = the kv_blocks of the other KV heads"),
        ("hi", "pale yellow: page 7 in the pages list, and token 37 in the plane strips"),
        ("eagle", "light blue: the EAGLE storage, the extra physical slot of the book"),
        ("vnni", "blue: the K plane k: k_storage, and a saved token column of the plane "
                 "strip (offsets 0..40)"),
        ("white box, blue outline: the accessor k_packed, VNNI slots only",
         "#fff", C["vnni"], False, False),
        ("white box, orange outline: the accessor page::k, row-major slots only",
         "#fff", C["rm"], False, False),
        ("empty", "grey dashed: a token column whose row is not saved (offsets 41..63)"),
        ("arrow", "ink arrow: how many of the target one source has: 1 book -> n_pages "
                  "pages; 1 page -> layout_t::n_slots x n_kv_heads kv_blocks"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = an accessor this PR adds; 'changed' = a struct or member "
                     "it changes (book, page, kv_block, k, page::k, copy_storage_slot)"),
    ]
    return figure(fid, W, H, "Data model: book, page, kv_block and the typed K plane",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B2: one K plane, two layouts ----------------------------------------------
def b2():
    fid = "kv_cache-b2"
    W, H = 1000, 626
    o = [marker_defs(fid, {"ink": C["ink"], "rm": C["rm"], "vnni": C["vnni"]})]
    boxes = []
    o.append(text(20, 22, "One K plane of kv_block(slot 5, kv_head 0, page 7): 64 tokens x "
                  "128 bf16 = 16 KiB, in one of two layouts", 12.5, weight=700))
    o.append(text(20, 38, "k_storage = std::conditional_t<k_vnni::layout_on<head_size>, "
                  "k_vnni_tensor<page_size, head_size>, native_k_storage>", 9.5, mono=True))
    o.append(cite(20, 50, "kv_cache.hpp:2566-2568", "start"))
    # ---- left: native K ----------------------------------------------------------
    lx = 20
    o.append(text(lx, 76, "native_k_storage (row-major slot)", 12, weight=700, fill=C["rm"]))
    o.append(text(lx, 90, "k_vnni::layout_on<head_size> false: every head size but 128, or "
                  "no TRON_K_VNNI", 9, fill=C["muted"]))
    o.append(rm_rows(lx, 100, 300, 256))
    o.append(text(lx + 304, 110, "offset 0", 8.5, fill=C["muted"]))
    o.append(text(lx + 304, 100 + 37 * 4 + 7, "offset 37", 8.5, weight=700))
    o.append(text(lx + 304, 354, "offset 63", 8.5, fill=C["muted"]))
    o.append(text(lx + 150, 370, "one row of head_size bf16 per token: 256 bytes", 9,
                  "middle"))
    ml = ["element (p, i) at [p * head_size + i]",
          "token 37, dimension 70: 37 * 128 + 70 = 4806",
          "byte 9612; the row of token 37 = bytes 9472..9727",
          "4 whole 64-byte lines per token"]
    for s in ml:
        fit(s, 9.5, 380, True, "b2 left")
    o.append(lines(lx, 390, ml, 9.5, 12, mono=True))
    o.append(cite(lx, 442, "kv_cache.hpp:2562-2565", "start"))
    boxes.append(("native_k_storage (row-major plane)", "kv_cache.hpp:2562-2565"))
    o.append(text(lx, 466, "accessors of this layout", 10, weight=600))
    la = [("page::k(slot, kv_head[, i_page])", "the row view / one token's row", "1974-2039"),
          ("kv_block::k_view / k_at(i_page)", "the plane view / row i_page", "2590-2610"),
          ("set_k_row / get_k_row", "std::memcpy of 256 bytes into / out of k_at", "2065, 2082"),
          ("copy_storage_slot", "memcpy of count * 256 bytes per KV head", "2346-2354")]
    yy = 474
    for name, desc, ref in la:
        o.append(rect(lx, yy, 380, 26, "#fff", C["rm"], 1.1, 3))
        o.append(text(lx + 6, yy + 11, name, 9, mono=True, weight=700))
        o.append(text(lx + 6, yy + 22, desc, 8.5, fill=C["muted"]))
        o.append(cite(lx + 376, yy + 22, f"kv_cache.hpp:{ref}"))
        yy += 30
    boxes += [("page::k", "kv_cache.hpp:1974-2039"), ("kv_block::k_view / k_at", "kv_cache.hpp:2590-2610"),
              ("set_k_row / get_k_row (row-major branch: std::memcpy)", "kv_cache.hpp:2065-2066, 2082-2083"),
              ("copy_storage_slot (row-major branch: memcpy)", "kv_cache.hpp:2346-2354")]
    # ---- middle: the same bytes -----------------------------------------------------
    mx = 440
    o.append(rect(mx, 150, 120, 120, C["soft"], C["ink"], 1.2, 6))
    o.append(lines(mx + 60, 172, ["the same", "16 KiB", "", "static_assert", "sizeof(k_storage)",
                                  "== page_size *", "head_size *", "sizeof(bf16)"], 9.5,
                   12, "middle"))
    o.append(cite(mx + 116, 266, "kv_cache.hpp:2573-2574"))
    boxes.append(("sizeof(k_storage) == page_size * head_size * sizeof(bf16)",
                  "kv_cache.hpp:2573-2574"))
    o.append(arrow(fid, "rm", [(mx - 2, 210), (lx + 304 + 56, 210)], C["rm"], 1.4))
    o.append(arrow(fid, "vnni", [(mx + 122, 210), (598, 210)], C["vnni"], 1.4))
    o.append(text(mx + 60, 300, "a permutation of", 9, "middle"))
    o.append(text(mx + 60, 311, "the same values", 9, "middle"))
    o.append(cite(mx + 60, 323, "tensor/k_vnni.hpp:83-84", "middle"))
    # ---- right: VNNI plane -------------------------------------------------------------
    rx = 600
    o.append(text(rx, 76, "k_vnni_tensor (VNNI slot)", 12, weight=700, fill=C["vnni"]))
    o.append(text(rx, 90, "k_vnni::layout_on<head_size> true: TRON_K_VNNI and head_size == 128",
                  9, fill=C["muted"]))
    o.append(panel_grid(rx + 40, 112, 76, 44, 4, 4, hi_panel=10, block=2))
    o.append(text(rx + 40 + 2 * 80 + 38, 318, "dashed frame: block c = 2 (tokens 32..47)", 8.5,
                  "middle", fill=C["muted"]))
    rl = ["16 panels of 1 KiB; panel (s, c) = 16 pair rows of 64 B",
          "pair row dp holds dimensions 32 s + 2 dp, + 1 of 16 tokens",
          "token 37 = (c 2, t 5); dimension 70 = (s 2, dp 3, j 0)",
          "k_vnni::index(37, 70) = (((2*4+2)*16+3)*16+5)*2+0 = 5226",
          "byte 10452, panel #10, pair row 3, column 5"]
    for s in rl:
        fit(s, 9.5, 380, True, "b2 right")
    o.append(lines(rx, 330, rl, 9.5, 12, mono=True))
    o.append(cite(rx, 394, "tensor/k_vnni.hpp:21-31, 97-106", "start"))
    boxes += [("k_vnni_tensor (VNNI plane, 16 panels)", "tensor/k_vnni.hpp:155-181; plane layout 21-31"),
              ("panel (s, c)", "tensor/k_vnni.hpp:26-28"),
              ("k_vnni::index", "tensor/k_vnni.hpp:97-106")]
    o.append(text(rx, 420, "a token's values are not contiguous: 64 pair slots, 64 lines apart",
                  9.5))
    o.append(cite(rx, 432, "kv_cache.hpp:737-739", "start"))
    o.append(text(rx, 466, "accessors of this layout", 10, weight=600))
    ra = [("page::k_packed<geometry>(slot, kv_head)", "read-only k_vnni_view for qk_group",
           "2041-2051"),
          ("set_k_row / get_k_row", "store_row / load_row: 4 scatters or gathers", "2063, 2080"),
          ("copy_storage_slot", "dst_block.k = src_block.k, or copy_token per token",
           "2337-2343")]
    yy = 474
    for name, desc, ref in ra:
        o.append(rect(rx, yy, 380, 26, "#fff", C["vnni"], 1.1, 3))
        o.append(text(rx + 6, yy + 11, name, 9, mono=True, weight=700))
        o.append(text(rx + 6, yy + 22, desc, 8.5, fill=C["muted"]))
        o.append(cite(rx + 376, yy + 22, f"kv_cache.hpp:{ref}"))
        yy += 30
    o.append(nx_box(rx, yy, 380, 38, "page::k, kv_block::k_view, k_at: do not exist",
                    ["requires(!layout_on) on every overload"],
                    "kv_cache.hpp:1978, 2593"))
    boxes += [("page::k_packed", "kv_cache.hpp:2041-2051"),
              ("set_k_row / get_k_row (VNNI branch: store_row / load_row)", "kv_cache.hpp:2062-2063, 2079-2080"),
              ("copy_storage_slot (VNNI branch)", "kv_cache.hpp:2331-2344"),
              ("page::k / k_view / k_at do not exist for a VNNI slot", "kv_cache.hpp:1978, 2593; Note [K VNNI storage] item 6 at 737-739")]
    cap = ("B2, one K plane in its two layouts, drawn for the worked example (kv_block of "
           "slot 5, KV head 0, page 7). The left side is native K: one 256-byte row per "
           "token, dimension 70 of token 37 at element 4806. The right side is the VNNI "
           "plane (Vector Neural Network Instructions, the AMX B-operand layout): 16 "
           "panels of 1 KiB, one per (dimension step s, token block c), and the same value "
           "at element 5226 in panel #10. The layout is a compile-time choice of the slot "
           "(k_vnni::layout_on), so a binary never holds both for one head size. Under "
           "each layout are the page accessors that reach it.")
    legend = [
        ("rm", "orange: native K: the 64 token rows of 256 bytes; orange text = its heading"),
        ("white box, orange outline: an accessor of the row-major layout", "#fff", C["rm"],
         False, False),
        ("vnni", "blue: the VNNI plane: its 16 panels; blue text = its heading"),
        ("white box, blue outline: an accessor of the VNNI layout", "#fff", C["vnni"],
         False, False),
        ("hi", "pale yellow: token 37's row in native K"),
        ("thick ink frame inside a panel: panel (2, 2) = #10, the panel of token 37's "
         "dimension 70", "none", C["ink"], False, False),
        ("ink dashed frame: block c = 2, the four panels that hold tokens 32..47",
         "none", C["ink"], True, False),
        ("deleted", "grey dashed box: page::k, k_view and k_at do not exist for a VNNI slot"),
        ("ctx_ink", "grey fill, ink outline: the static_assert that both layouts hold the "
                    "same 16 KiB"),
        ("orange arrow: the same bytes seen as native K", "arrow", C["rm"]),
        ("blue arrow: the same bytes seen as the VNNI plane", "arrow", C["vnni"]),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "One K plane, two layouts in the same 16 KiB",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B3: function model ------------------------------------------------------------
def b3():
    fid = "kv_cache-b3"
    W, H = 1000, 760
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    cx0, cw0 = 20, 236
    ax0, aw0 = 268, 440
    ox0, ow0 = 720, 260
    CW, CG = 198, 44
    for x, w, h in [(cx0, cw0, "callers (other files) [thread]"),
                    (ax0, aw0, "page / book API in kv_cache.hpp"),
                    (ox0, ow0, "operation in h/tron/tensor/k_vnni.hpp")]:
        o.append(text(x + w / 2, 22, h, 12, "middle", weight=700))
    RH, GAP = 62, 8
    rows = [
        dict(caller=["model.hpp save_k_impl: one token's", "K row per KV head, then",
                     "mark_k_complete [main thread]"],
             cref="model.hpp:3097-3118",
             api=[("set_k_row", ["if constexpr layout_on: store_row, else",
                                 "std::memcpy 256 B; the row may be unaligned"],
                   "kv_cache.hpp:2053-2068", "new", aw0)],
             ops=["store_row: 4 scatters of 16 dwords", "into the token's column; it takes a",
                  "k_vnni_view only and checks no layout"],
             orefs=["tensor/k_vnni.hpp:251-267"]),
        dict(caller=["self_attention.hpp apply_page_tok:", "the loop marks live tokens, then",
                     "scores them [attention workers]"],
             cref="self_attention.hpp:1953-1971",
             api=[("k_packed", ["the read-only K plane view for the",
                                "score reader k_vnni::qk_group"],
                   "kv_cache.hpp:2041-2051", "new", aw0)],
             ops=["k_vnni::qk_group(k_page, q, live, s,", "s_stride) reads the plane through",
                  "detail::k_vnni_access::plane"],
             orefs=["kernels/k_vnni.hpp:33-38; k_vnni.hpp:188-194"]),
        dict(caller=["full.hpp page_info::k_head_fn:", "the FPGA staging of gof::populate",
                     "[attention workers; main at forward end]"],
             cref="full.hpp:2747-2760; gof.cpp:211",
             api=[("get_k_row", ["if constexpr layout_on: load_row, else",
                                 "std::memcpy 256 B; the row may be unaligned"],
                   "kv_cache.hpp:2070-2085", "new", aw0)],
             ops=["load_row: 4 gathers of 16 dwords", "into the caller's row; it takes a",
                  "k_vnni_view only and checks no layout"],
             orefs=["tensor/k_vnni.hpp:269-284"]),
        dict(caller=["kv_cache.hpp book::append (defrag)", "-> copy_from, page-wise",
                     "[scheduler, tree_lock held]"],
             cref="kv_cache.hpp:1298-1332; full.hpp:1257-1259",
             api=[("copy_storage_slot", ["copies count tokens of one storage slot",
                                         "from src_page: K per layout, V per token"],
                   "kv_cache.hpp:2324-2361", "changed", aw0)],
             ops=["whole page: dst_block.k = src_block.k", "(the owner is trivially copyable) |",
                  "other ranges: copy_token per token"],
             orefs=["tensor/k_vnni.hpp:286-297; kv_cache.hpp:2569-2572"]),
        dict(caller=["t_k_vnni_layout.cpp, t_llama_unit.cpp,", "t_amx_dispatch_dtype.cpp:",
                     "the layout-agnostic accessors [tests]"],
             cref="t_k_vnni_layout.cpp:353-437",
             api=[("set_k_row / get_k_row", ["uniform-geometry overloads: forward to",
                                             "layout_t::primary_geometry"],
                   "kv_cache.hpp:2087-2107", "new", aw0)],
             ops=["store_row / load_row for a VNNI slot;", "no k_vnni.hpp operation for a",
                  "row-major slot (memcpy in kv_cache.hpp)"],
             orefs=["tensor/k_vnni.hpp:251-284"]),
        dict(caller=["book::fill_random: random bf16 in", "every kv_block, for testing only",
                     "[tests]"],
             cref="kv_cache.hpp:1334-1349",
             api=[("fill_storage_slot", ["fills every kv_block of one storage slot;",
                                         "a packed K plane through k_vnni_access"],
                   "kv_cache.hpp:1766-1786", "changed", aw0)],
             ops=["detail::k_vnni_access::plane(k.as_view()):", "the one route to the raw",
                  "plane address (documented exception)"],
             orefs=["tensor/k_vnni.hpp:188-194; kv_cache.hpp:701-704"]),
        dict(caller=["row-major slots only: model.hpp:3114,", "self_attention.hpp:1956,",
                     "full.hpp:2758"],
             cref="model.hpp:3113-3115",
             api=[("page::k", ["row view / one row; 8 overloads,",
                               "now require !k_vnni::layout_on"],
                   "kv_cache.hpp:1974-2039", "changed", CW),
                  ("kv_block::k_view / k_at", ["native K only: a packed plane has",
                                               "no contiguous rows"],
                   "kv_cache.hpp:2590-2610", "changed", CW)], link="calls",
             ops=["(no k_vnni.hpp operation:", "contiguous rows)"],
             orefs=["kv_cache.hpp:1979, 2011"]),
    ]
    y = 34
    for r in rows:
        rh = r.get("h", RH)
        o.append(caller_cell(cx0, y, cw0, rh, r["caller"], r["cref"]))
        ax = ax0
        for i, (name, desc, ref, tg, w) in enumerate(r["api"]):
            for d in desc:
                fit(d, 9.5, w - 16, False, f"b3 {name}")
            o.append(fn_cell(ax, y, w, rh, name, desc, ref, tg))
            boxes.append((name, ref))
            if i == 1:
                gx0, gx1 = ax - CG + 3, ax - 3
                o.append(arrow(fid, "ink", [(gx0, y + rh / 2), (gx1, y + rh / 2)], C["ink"],
                               1.2))
                o.append(text((gx0 + gx1) / 2, y + rh / 2 - 5, r["link"], 8.5, "middle",
                              fill=C["ink"]))
            ax += w + CG
        o.append(ops_cell(ox0, y, ow0, rh, r["ops"], r["orefs"]))
        o.append(arrow(fid, "ink", [(cx0 + cw0 + 2, y + rh / 2), (ax0 - 2, y + rh / 2)],
                       C["ink"]))
        o.append(arrow(fid, "ink", [(ax0 + aw0 + 2, y + rh / 2), (ox0 - 2, y + rh / 2)],
                       C["ink"]))
        y += rh + GAP
    boxes += [("save_k_impl (caller)", "model.hpp:3074, 3097-3118"),
              ("apply_page_tok (caller)", "self_attention.hpp:1834, 1953-1971"),
              ("page_info::k_head_fn (caller)", "full.hpp:2747-2760; gof.hpp:61-68; gof.cpp:201-211"),
              ("book::append -> copy_from (caller)", "kv_cache.hpp:1298-1332, 2364-2375; full.hpp:1257-1259"),
              ("set_k_row / get_k_row calls of the tests (callers)", "t_k_vnni_layout.cpp:362-377; t_llama_unit.cpp:485-489; t_amx_dispatch_dtype.cpp:110"),
              ("book::fill_random (caller)", "kv_cache.hpp:1334-1349"),
              ("store_row", "tensor/k_vnni.hpp:251-267"),
              ("load_row", "tensor/k_vnni.hpp:269-284"),
              ("copy_token", "tensor/k_vnni.hpp:286-297"),
              ("k_vnni::qk_group", "kernels/k_vnni.hpp:33-38"),
              ("detail::k_vnni_access::plane", "tensor/k_vnni.hpp:188-194")]
    # helpers band
    y += 2
    o.append(rect(20, y, 960, 150, "#fff", C["ink"], 1.2, 4, "5 3"))
    o.append(text(30, y + 15, "what every row relies on (unchanged helpers, and the one "
                  "new route)", 11, weight=700))
    helpers = [
        ("page::kv_block(slot, kv_head)", ["the kv_block of this page for a slot and KV",
                                          "head (the geometry overload checks the slot)"],
         "kv_cache.hpp:2282-2292", None),
        ("book_t::declares_geometry<geometry>()", ["true when the layout declares that "
                                                    "geometry", "(the requires clause of the "
                                                    "geometry overloads)"],
         "kv_cache.hpp:1645-1656", None),
        ("uniform_geometry / primary_geometry", ["every slot shares one geometry; "
                                                           "the uniform", "overloads forward "
                                                           "to the primary one"],
         "kv_cache.hpp:793-796", None),
        ("k.as_view()", ["k_vnni_view<bf16> from an owner, <const bf16>",
                         "from a const owner; no raw pointer leaves"],
         "tensor/k_vnni.hpp:162-176", "new"),
        ("k_vnni::layout_on<head_size>", ["the compile-time gate: TRON_K_VNNI and",
                                          "head_size == 128; the same for every reader"],
         "tensor/k_vnni.hpp:86-95", "new"),
        ("kv_block_at_storage(offset, kv_head)", ["the kv_block of a physical storage "
                                                   "slot (page", "copies address storage, "
                                                   "not logical slots)"],
         "kv_cache.hpp:2294-2303", None),
    ]
    hw, hh = 310, 56
    for i, (name, desc, ref, tg) in enumerate(helpers):
        hx = 30 + (i % 3) * (hw + 10)
        hy = y + 22 + (i // 3) * (hh + 6)
        for d in desc:
            fit(d, 9.5, hw - 16, False, f"b3 helper {name}")
        o.append(fn_cell(hx, hy, hw, hh, name, desc, ref, tg))
        boxes.append((name, ref))
    cap = ("B3, the function model. Each row is one call path: the caller in another file "
           "(with the thread in brackets), the page or book function of kv_cache.hpp it "
           "calls, and the typed operation of h/tron/tensor/k_vnni.hpp that touches the "
           "bytes. Each function cell says in one line what the function does, cites its "
           "definition and tags whether the PR adds (new) or changes it. The last row is "
           "the row-major-only path: page::k still exists for every slot whose K is "
           "row-major, and does not exist for a VNNI slot. The dashed band lists what every "
           "row relies on.")
    legend = [
        ("ctx", "grey box, thin grey outline: a caller in another file (or a test), with "
                "its thread in brackets (left column)"),
        ("box", "white box, ink outline: a function of kv_cache.hpp (the page / book API "
                "cells and the helpers): name in bold monospace, a one-line description, "
                "its citation and its tag"),
        ("lane", "white box, thin grey outline: the k_vnni.hpp operation the API function "
                 "takes (right column)"),
        ("ink dashed frame: the band of helpers every row relies on", "#fff", C["ink"],
         True, False),
        ("arrow", "ink arrow: a call: caller -> API function -> k_vnni.hpp operation; the "
                  "word 'calls' between two API cells = the left one calls the right one"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = a function this PR adds; 'changed' = a function it "
                     "changes"),
    ]
    return figure(fid, W, H, "Function model: callers, page and book API, k_vnni.hpp operations",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B4: sequencing model -------------------------------------------------------------
def b4():
    fid = "kv_cache-b4"
    W, H = 1000, 560
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "q": C["q"], "hw": C["hw"],
                           "rm": C["rm"]})]
    boxes = []
    o.append(text(20, 22, "The life of one token's K row in a VNNI slot: token 37 of page 7, "
                  "storage slot 5, KV head 0 (worked example)", 12.5, weight=700))
    # ---- the writer: save_k -> set_k_row -> store_row -----------------------------------
    o.append(caller_cell(20, 50, 200, 70, ["1. save_k_impl [main thread]:", "kout = the token's "
                                           "K row (128 bf16)", "of the K buffer, per KV head"],
                         "model.hpp:3097-3099"))
    boxes.append(("save_k_impl: kout", "model.hpp:3097-3099"))
    o.append(rect(20, 130, 200, 30, C["rm_fill"], C["rm"], 1.2, 3))
    o.append(text(120, 149, "k_source_row(kout): a transfer row", 9.5, "middle", True))
    o.append(cite(216, 158, "model.hpp:3104; k_vnni.hpp:200-204"))
    boxes.append(("k_source_row(kout) (transfer row)", "model.hpp:3104-3105; tensor/k_vnni.hpp:200-210"))
    o.append(arrow(fid, "ink", [(220, 85), (258, 85)], C["ink"], 1.4))
    o.append(fn_cell(260, 50, 190, 70, "set_k_row", ["if constexpr layout_on:",
                                                    "store_row(k.as_view(), 37, row)"],
                     "kv_cache.hpp:2053-2068", "new"))
    boxes.append(("set_k_row", "kv_cache.hpp:2053-2068"))
    o.append(arrow(fid, "vnni", [(450, 85), (488, 85)], C["vnni"], 1.4))
    o.append(fn_cell(490, 50, 200, 70, "store_row", ["4 scatters of 16 dwords: the 64 pair",
                                                    "slots of column 5 in panels (s, 2)"],
                     "tensor/k_vnni.hpp:251-267", "new"))
    boxes.append(("store_row", "tensor/k_vnni.hpp:251-267"))
    o.append(arrow(fid, "vnni", [(690, 85), (728, 85)], C["vnni"], 1.4))
    # ---- the plane ------------------------------------------------------------------------
    px, py, pw, ph = 730, 44, 250, 160
    o.append(rect(px, py, pw, ph, C["vnni_fill"], C["vnni"], 1.6, 6))
    o.append(text(px + 10, py + 16, "kv_block.k: k_vnni_tensor", 10.5, mono=True, weight=700))
    o.append(text(px + 10, py + 30, "the plane of (slot 5, kv_head 0, page 7)", 9,
                  fill=C["muted"]))
    o.append(plane_strip(px + 10, py + 40, pw - 20, 22))
    o.append(text(px + 10, py + 86, "after 41 set_k_row calls: offsets 0..40 saved;", 8.5))
    o.append(text(px + 10, py + 97, "token 37 owns column 5 of block 2 in every panel", 8.5))
    o.append(text(px + 10, py + 112, "then mark_k_complete(slot, 37): kv_saves_", 8.5))
    o.append(text(px + 10, py + 123, "counts K saved; V is a separate save", 8.5))
    o.append(cite(px + pw - 6, py + ph - 5, "kv_cache.hpp:2575; model.hpp:3118; kv_cache.hpp:2208"))
    boxes += [("kv_block.k (the plane)", "kv_cache.hpp:2575"),
              ("mark_k_complete", "kv_cache.hpp:2208-2212; model.hpp:3118")]
    # ---- the readers -----------------------------------------------------------------------
    ry = 240
    o.append(text(20, ry - 10, "2. the readers of that row (each takes the plane through a "
                  "typed view; none sees a raw pointer)", 11, weight=700))
    # reader A: attention
    o.append(caller_cell(20, ry, 200, 70, ["apply_page_tok [attention workers]:", "the loop "
                                           "sets bit 37 of `live`;", "41 live tokens of page 7"],
                         "self_attention.hpp:1952-1954"))
    o.append(arrow(fid, "ink", [(220, ry + 35), (258, ry + 35)], C["ink"], 1.4))
    o.append(fn_cell(260, ry, 190, 70, "k_packed", ["k_vnni_view<const bf16, 64, 128>",
                                                   "of (slot 5, kv_head 0)"],
                     "kv_cache.hpp:2041-2051", "new"))
    o.append(arrow(fid, "q", [(450, ry + 35), (488, ry + 35)], C["q"], 1.4))
    o.append(fn_cell(490, ry, 200, 70, "k_vnni::qk_group", ["4 heads x 41 live tokens:",
                                                           "s_pages[h][t] = q_h . K_t"],
                     "kernels/k_vnni.hpp:33-38", "new", fill=C["q_fill"], stroke=C["q"]))
    o.append(arrow(fid, "q", [(690, ry + 35), (728, ry + 35)], C["q"], 1.4))
    o.append(label_box(730, ry + 4, 250, 62, "s_pages[kv_mul][64] fp32",
                       ["raw q . k, unscaled; the other", "entries stay -infinity"],
                       C["q_fill"], C["q"], 10, ref="self_attention.hpp:1901, 1967"))
    boxes += [("apply_page_tok: live", "self_attention.hpp:1927, 1952-1954"),
              ("k_packed", "kv_cache.hpp:2041-2051"),
              ("k_vnni::qk_group", "kernels/k_vnni.hpp:33-38"),
              ("s_pages", "self_attention.hpp:1901-1906, 1967-1970")]
    # reader B: FPGA staging
    ry2 = ry + 84
    o.append(caller_cell(20, ry2, 200, 70, ["gof::populate [attention workers;", "main at forward "
                                            "end]:", "k_head_fn(slot, h, k_scratch row h)"],
                         "gof.cpp:201-211; model.hpp:3231, 3244"))
    o.append(arrow(fid, "ink", [(220, ry2 + 35), (258, ry2 + 35)], C["ink"], 1.4))
    o.append(fn_cell(260, ry2, 190, 70, "page_info::k_head_fn", ["full.hpp: get_k_row into",
                                                                "k_destination_row(dest)"],
                     "full.hpp:2747-2760", "changed"))
    o.append(arrow(fid, "ink", [(450, ry2 + 35), (488, ry2 + 35)], C["ink"], 1.4))
    o.append(fn_cell(490, ry2, 200, 70, "get_k_row -> load_row", ["4 gathers of 16 dwords out of",
                                                                 "column 5 into the scratch row"],
                     "kv_cache.hpp:2070-2085", "new"))
    o.append(arrow(fid, "hw", [(690, ry2 + 35), (728, ry2 + 35)], C["hw"], 1.4))
    o.append(label_box(730, ry2 + 4, 250, 62, "k_scratch row (256 B, dimension order)",
                       ["staged for the FPGA; the HBM", "layout is unchanged"],
                       C["hw_fill"], C["hw"], 9.5, ref="gof.cpp:201; kv_cache.hpp:728-732"))
    boxes += [("gof::populate -> k_head_fn", "gof.cpp:186, 201-211; model.hpp:3231-3250"),
              ("page_info::k_head_fn", "full.hpp:2747-2760; gof.hpp:61-68"),
              ("get_k_row -> load_row", "kv_cache.hpp:2070-2085; tensor/k_vnni.hpp:269-284"),
              ("k_scratch", "gof.cpp:201")]
    # reader C: page copy
    ry3 = ry2 + 84
    o.append(caller_cell(20, ry3, 200, 70, ["book::append -> copy_from", "[tree_lock]: 41 tokens of "
                                            "page 7 to", "page 9, or all 64 tokens of a page"],
                         "kv_cache.hpp:1298-1332, 2364-2375"))
    o.append(arrow(fid, "ink", [(220, ry3 + 35), (258, ry3 + 35)], C["ink"], 1.4))
    o.append(fn_cell(260, ry3, 190, 70, "copy_storage_slot", ["whole page: dst_block.k = src_block.k",
                                                             "else: copy_token per token"],
                     "kv_cache.hpp:2324-2361", "changed"))
    o.append(arrow(fid, "vnni", [(450, ry3 + 35), (488, ry3 + 35)], C["vnni"], 1.4))
    o.append(fn_cell(490, ry3, 200, 70, "copy_token", ["load_row (page 7, 37) then",
                                                      "store_row (page 9, 37): 41 times"],
                     "tensor/k_vnni.hpp:286-297", "new"))
    o.append(arrow(fid, "vnni", [(690, ry3 + 35), (728, ry3 + 35)], C["vnni"], 1.4))
    o.append(rect(730, ry3 + 8, 250, 54, C["vnni_fill"], C["vnni"], 1.4, 5))
    o.append(text(855, ry3 + 24, "the plane of (slot 5, kv_head 0, page 9)", 9.5, "middle", True,
                  weight=700))
    o.append(plane_strip(740, ry3 + 32, 230, 14, label=False))
    o.append(cite(976, ry3 + 58, "kv_cache.hpp:2331-2344"))
    boxes += [("book::append -> copy_from", "kv_cache.hpp:1298-1332, 2364-2375; full.hpp:1257-1259"),
              ("copy_storage_slot", "kv_cache.hpp:2324-2361"),
              ("copy_token", "tensor/k_vnni.hpp:286-297")]
    # test-only
    o.append(rect(20, 506, 960, 44, C["soft"], C["line"], 1, 4))
    o.append(lines(30, 522, ["test only: book::fill_random -> fill_storage_slot writes random "
                             "bf16 over the whole plane through detail::k_vnni_access::plane("
                             "block.k.as_view());",
                             "it interprets no coordinates and marks no token complete"], 9.5, 12))
    o.append(cite(974, 546, "kv_cache.hpp:1334-1349, 1772-1776"))
    boxes.append(("book::fill_random -> fill_storage_slot", "kv_cache.hpp:1334-1349, 1766-1786"))
    cap = ("B4, the sequencing model: the life of one token's K row in a VNNI slot, for "
           "token 37 of the worked example. Row 1 is the one writer: save_k stores the row "
           "through set_k_row and store_row, 4 scatters into the token's column, and then "
           "marks K complete. Row 2 lists the three readers of the same bytes: the attention "
           "workers score the live tokens through k_packed and k_vnni::qk_group; the FPGA "
           "staging gathers one row into a scratch buffer through get_k_row and load_row; a "
           "page copy moves the token with copy_token, or the whole page as one owner "
           "assignment. Every path takes the plane through a typed view.")
    legend = [
        ("ctx", "grey box, thin grey outline: a caller in another file, with its thread in "
                "brackets, and the test-only note at the bottom"),
        ("box", "white box, ink outline: a function of kv_cache.hpp or k_vnni.hpp: name in "
                "bold monospace, one-line description, citation, tag"),
        ("vnni", "blue: the K plane of a kv_block (page 7, and page 9 after the copy) and a "
                 "saved token column of its strip"),
        ("hi", "pale yellow: token 37 in the plane strips"),
        ("empty", "grey dashed: a token column whose row is not saved (offsets 41..63)"),
        ("rm", "orange: the transfer row k_source_row(kout): one token's 128 values in "
               "dimension order"),
        ("q", "purple: the query side: k_vnni::qk_group and its scores s_pages"),
        ("hw", "yellow: the FPGA staging: the k_scratch row the staging reads"),
        ("arrow", "ink arrow: a call from a caller into the page API"),
        ("blue arrow: bytes into or out of a VNNI plane (store_row, copy_token)", "arrow",
         C["vnni"]),
        ("purple arrow: the plane read by the score reader, and its scores", "arrow", C["q"]),
        ("yellow arrow: the gathered row handed to the FPGA staging", "arrow", C["hw"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = a function this PR adds; 'changed' = a function it changes"),
    ]
    return figure(fid, W, H, "Sequencing model: the life of one token's K row in a VNNI slot",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---- B5: interaction model ---------------------------------------------------------------
def b5():
    fid = "kv_cache-b5"
    W, H = 1000, 560
    o = [marker_defs(fid, {"ink": C["ink"]})]
    boxes = []
    o.append(text(20, 26, "one forward pass of one layer (time runs to the right, durations "
                  "not to scale), then the tree work between passes", 11, weight=600))
    segs = [(150, 470, "the layer's save_k, then its attention jobs"),
            (472, 700, "later layers and the forward end"),
            (702, 994, "between passes (tree_lock held)")]
    for a, b, lab in segs:
        o.append(line(a, 62, b - 4, 62, C["muted"], 1))
        o.append(line(a, 56, a, 62, C["muted"], 1))
        o.append(line(b - 4, 56, b - 4, 62, C["muted"], 1))
        fit(lab, 9.5, b - a, False, "b5 seg")
        o.append(text((a + b - 4) / 2, 52, lab, 9.5, "middle", weight=600))
    names = [("main thread", None), ("attention workers", None), ("scheduler", None)]
    LH, BH = 96, 80
    svg, x0, ys = lane_set(10, 80, 984, names, LH, 6)
    o.append(svg)
    for lab, sub in [("main thread", "save_k_impl"),
                     ("attention workers", "apply_page_tok"),
                     ("scheduler", "defrag_books")]:
        fit(sub, 9, 130, False, "b5 lane sub")
        o.append(text(18, ys[lab] + LH / 2 + 17, sub, 9, fill=C["muted"]))
    ym, yw, ys_ = (ys[k] + 8 for k in ["main thread", "attention workers", "scheduler"])
    # idle first
    idle = [
        (yw, 150, 170, ["wait: upstream_kvs_ready", "latch of the slot"],
         "self_attention.hpp:823"),
        (yw, 600, 100, ["exits: run()", "joins the workers"], "model.hpp:3241-3242"),
        (ys_, 150, 548, ["waits: the tree work runs between forward passes; defrag_books "
                         "asserts tree_lock_held_by_this_thread"],
         "full.hpp:1257-1259"),
    ]
    for y, x, w, ls, ref in idle:
        o.append(lane_block(x, y, w, BH, ls, "#fff", C["muted"], True, 8.5, ref))
    work = [
        (ym, 150, 170, ["save_k_impl: per token,", "per KV head: set_k_row", "-> store_row; then",
                        "mark_k_complete"], C["vnni_fill"], C["vnni"], "model.hpp:3097-3118"),
        (ym, 322, 100, ["upstream_kvs_ready", "count_down (release)"], C["soft"], C["ink"],
         "model.hpp:3127"),
        (ym, 472, 100, ["later layers:", "the same per layer"], C["soft"], C["ink"], None),
        (ym, 600, 112, ["wait_for_coop_gof:", "the tail GOFs:", "k_head_fn -> get_k_row"],
         C["hw_fill"], C["hw"], "model.hpp:3244-3250"),
        (yw, 322, 150, ["attention jobs:", "apply_page_tok: live,", "k_packed -> qk_group"],
         C["q_fill"], C["q"], "self_attention.hpp:1953-1971"),
        (yw, 472, 126, ["between layers:", "help_drain_gof ->", "gof::populate ->",
                        "k_head_fn, get_k_row"], C["hw_fill"], C["hw"],
         ["model.hpp:3225-3237;", "gof.cpp:211"]),
        (ys_, 702, 140, ["defrag_books ->", "book::append ->", "copy_from ->",
                         "copy_storage_slot"], C["vnni_fill"], C["vnni"],
         ["full.hpp:1257;", "kv_cache.hpp:1298-1332"]),
        (ys_, 846, 142, ["copy_token per token, or", "dst_block.k = src_block.k", "for a whole page"],
         C["vnni_fill"], C["vnni"], "kv_cache.hpp:2331-2344"),
    ]
    for y, x, w, ls, fill, stroke, ref in work:
        o.append(lane_block(x, y, w, BH, ls, fill, stroke, False, 8.5, ref))
    boxes += [
        ("save_k_impl: set_k_row per token and KV head, mark_k_complete", "model.hpp:3097-3118"),
        ("upstream_kvs_ready: count_down after the save, wait before the attention",
         "model.hpp:3127; self_attention.hpp:823; common.hpp:1007, 1186"),
        ("attention jobs: apply_page_tok", "self_attention.hpp:1834, 1953-1971"),
        ("help_drain_gof -> fire_gof_rodeo -> gof::populate", "model.hpp:3225-3237; gof.cpp:186, 211"),
        ("wait_for_coop_gof (forward end, main)", "model.hpp:3239-3250"),
        ("run() joins the workers", "model.hpp:3241-3242"),
        ("defrag_books -> book::append -> copy_from -> copy_storage_slot",
         "full.hpp:1257-1259; kv_cache.hpp:1298-1332, 2364-2375, 2324-2361"),
        ("tree_lock", "full.hpp:1257-1259 (defrag_books asserts tree_lock_held_by_this_thread)"),
    ]
    ny = ys["scheduler"] + LH + 26
    o.append(text(20, ny, "What orders the writer and the readers", 11, weight=700))
    left = [
        "save_k stores the rows, then counts the slot's upstream_kvs_ready latch down "
        "[model.hpp:3097-3127];",
        "the attention of that slot waits on the latch before it reads a page "
        "[self_attention.hpp:823; common.hpp:1007].",
        "store_row writes only its own token's 64 pair slots, so tokens of one plane are "
        "written independently [tensor/k_vnni.hpp:26-29, 251-252].",
        "The staging gather (k_head_fn) reads a token only when kv_complete_fn says K and V "
        "are saved [gof.hpp:69-70; full.hpp:2744-2746].",
        "Page copies run in the scheduler's defrag with tree_lock held [full.hpp:1257-1259]; "
        "no forward pass runs then.",
    ]
    for s in left:
        fit(s, 9.5, 950, False, "b5 left")
    o.append(lines(20, ny + 16, left, 9.5, 12))
    o.append(text(20, ny + 86, "The kill switch (TRON_AMX_DISABLE) changes no path on this "
                  "figure: a TRON_K_VNNI binary runs the AVX-512 VNNI reader either way;", 9.5))
    o.append(text(20, ny + 98, "no AMX visit can occur for a VNNI slot [kv_cache.hpp:740-746].",
                  9.5))
    boxes.append(("kv_complete_fn", "gof.hpp:69-70; full.hpp:2744-2746"))
    boxes.append(("the kill switch keeps the layout", "kv_cache.hpp:740-746"))
    cap = ("B5, the interaction model: one forward pass of one layer and the tree work "
           "between passes, one lane per actor. The main thread writes the K rows (save_k) "
           "and then counts the slot's latch down; the attention workers wait on that latch "
           "and then read the plane through k_packed; the GOF staging (the copy of K rows "
           "for the FPGA) runs on idle attention workers between layers and on main at the "
           "forward end, and reads a row through get_k_row; page copies run in the "
           "scheduler's defrag under tree_lock. No lane shares a token's bytes with another "
           "writer at the same time.")
    legend = [
        ("grey dashed outline: waiting or idle: the latch wait, the workers after run() "
         "joins them, the scheduler during the pass", "#fff", C["muted"], True, False),
        ("ctx_ink", "grey fill, ink outline: other work: the latch count_down, later layers"),
        ("vnni", "blue: a write into or a copy of a VNNI plane (save_k -> set_k_row -> "
                 "store_row; copy_storage_slot -> copy_token or the owner assignment)"),
        ("q", "purple: the attention jobs that read the plane (k_packed -> k_vnni::qk_group)"),
        ("hw", "yellow: the FPGA staging gather (help_drain_gof / wait_for_coop_gof -> "
               "gof::populate -> k_head_fn -> get_k_row)"),
        ("font_sans", "sans-serif = prose and, in this figure, the identifiers inside the "
                      "lane blocks and the notes"),
        "font_cite",
    ]
    return figure(fid, W, H, "Interaction model: which thread touches the K plane when",
                  "".join(o), cap, boxes=boxes, legend=legend)
