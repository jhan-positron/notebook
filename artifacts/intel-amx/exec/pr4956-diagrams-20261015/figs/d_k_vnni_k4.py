"""Change diagram of unit k4 of the PR 4956 k_vnni.hpp page: the transfer
rows const_k_row_view / k_row_view and their builders (head lines 197-225).

One figure, k_vnni-d4: the two row paths, into and out of the plane, from the
buffer behind the row through k_source_row / k_destination_row to the page
accessor and the operation that take it. Line numbers are head lines of
PR 4956 (a5697f86d3), h/tron/tensor/k_vnni.hpp unless another file is named.
"""
import sys

from svg_helpers import (C, arrow, figure, fn_cell, label_box, line, lines,
                         marker_defs, rect, text, text_width)

BASE = ("Updates B2: the three transfer-row boxes at the bottom of B2 become the "
        "whole path of a row, from the buffer behind it through k_source_row / "
        "k_destination_row to the page accessor and the operation that take it.")

W = 700
LX, RX, CW = 20, 360, 320          # the two columns: source row (in), destination row (out)


def _w(s, size, w, mono=False, where=""):
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH d_k_vnni_k4 {where}: '{s}' needs {tw:.0f} px, has {w}",
              file=sys.stderr)


def _box(o, x, y, w, h, title, sub, ref, fill="#fff", stroke=C["ink"], tsize=11,
         ssize=9.5, lh=12.5, colors=None, dash=None):
    o.append(rect(x, y, w, h, fill, stroke, 1.2, 4, dash))
    _w(title, tsize, w - 16, True, title)
    o.append(text(x + 8, y + 15, title, tsize, mono=True, weight=600))
    yy = y + 15
    for i, s in enumerate(sub):
        yy += lh
        _w(s, ssize, w - 16, False, title)
        o.append(text(x + 8, yy, s, ssize, fill=(colors or {}).get(i, C["ink"])))
    _w(ref, 8.5, w - 8, True, "cite " + title)
    o.append(text(x + w - 4, y + h - 4, ref, 8.5, "end", True, fill=C["cite"]))


def _frame(o, x, y, w, h, title):
    o.append(rect(x, y, w, h, "none", C["line"], 1, 5, "4 3"))
    _w(title, 9.5, w - 12, where="frame " + title)
    o.append(text(x + 8, y + 12, title, 9.5, fill=C["muted"], weight=600))


def _vcard(o, fid, name, color, x, y0, y1, label_lines, ref):
    o.append(arrow(fid, name, [(x, y0), (x, y1)], color, 1.4))
    ty = y0 + 12
    for i, s in enumerate(label_lines):
        _w(s, 9, CW - 70, where="arrow label")
        o.append(text(x + 8, ty + i * 10.5, s, 9, fill=color, weight=600))
    o.append(text(x + 8, ty + len(label_lines) * 10.5, f"[{ref}]", 8.5, mono=True,
                  fill=C["cite"]))


def fig():
    fid = "k_vnni-d4"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "hw": C["hw"]})]
    h1 = ("transfer rows (new): one token's Cols = 128 bf16 in dimension order = 256 "
          "bytes; not packed storage")
    _w(h1, 11, W - 40, where="header")
    o.append(text(LX, 18, h1, 11, weight=700))
    o.append(text(LX, 32, "the caller's Aligned and Dma flags travel with the row; the "
                  "defaults are the bare literals true, false", 9.5, fill=C["muted"]))
    o.append(text(LX, 44, "[k_vnni.hpp:197-204]", 8.5, mono=True, fill=C["cite"]))
    o.append(text(LX + 250, 44, "arrows: call order, top to bottom (not the data direction)",
                  9, fill=C["muted"]))
    o.append(text(LX, 66, "into the plane: the read-only source row", 11, weight=700))
    o.append(text(RX, 66, "out of the plane: the writable destination row", 11,
                  weight=700))
    # ---- row 1: the buffer behind the row ------------------------------------
    y1, fh = 74, 184
    bx, bw = LX + 6, CW - 12
    bx2 = RX + 6
    _frame(o, LX, y1, CW, fh, "the buffer behind the row (the caller's)")
    _box(o, bx, y1 + 18, bw, 66, "kout = slice<head_size>()(ks[ix], kv_head)", [
        "a K buffer row of save_k_impl; a bf16 row keeps the",
        "buffer's alignment and DMA flags -> the view overload",
        "[the thread of save_k]"],
        "model.hpp:3098-3105", C["soft"], C["line"], tsize=10, lh=11.5,
        colors={2: C["muted"]})
    boxes.append(("kout = slice<head_size>()(ks[ix], kv_head)", "model.hpp:3098-3099, 3104-3105"))
    _box(o, bx, y1 + 90, bw, 76, "row[head_size] / row[Cols] / poison_row", [
        "row: a non-bf16 kout converted to bf16 on the stack",
        "first -> the pointer overload (model.hpp:3108-3111)",
        "row[Cols]: the stack row of copy_token (294, 296)",
        "poison_row, buf.rows: the test's rows (67, 78)"],
        "model.hpp:3108; k_vnni.hpp:294; t_k_vnni_layout.cpp:66-78", C["soft"], C["line"],
        tsize=10, lh=11.5)
    boxes.append(("row[head_size] / row[Cols] / poison_row",
                  "model.hpp:3108; k_vnni.hpp:294; t_k_vnni_layout.cpp:66-78"))
    _frame(o, RX, y1, CW, fh, "the buffer behind the row (the caller's)")
    _box(o, bx2, y1 + 18, bw, 88, "dest: k_scratch of gof::populate", [
        "HW_BAKED_HEAD_SIZE bf16 per KV head of the 64-byte-",
        "aligned array on gof::populate's stack, passed to",
        "page_info::k_head_fn; filled through get_k_row for a",
        "VNNI slot (a row-major slot returns the row in place)",
        "[the FPGA staging: an attention worker or main]"],
        "gof.cpp:201, 211; full.hpp:2747-2756", C["hw_fill"], C["hw"], lh=11.5,
        colors={4: C["muted"]})
    boxes.append(("dest: k_scratch of gof::populate", "gof.cpp:201, 211; full.hpp:2747-2756"))
    _box(o, bx2, y1 + 112, bw, 66, "row[Cols] / got", [
        "row[Cols]: the stack row of copy_token (294-295)",
        "got: the test's destination row (t_k_vnni_layout.cpp:",
        "148-149, 361, 374); scratch of t_phase1 (876-877)"],
        "k_vnni.hpp:294; t_k_vnni_layout.cpp:361", C["soft"], C["line"], lh=11.5)
    boxes.append(("row[Cols] / got", "k_vnni.hpp:294; t_k_vnni_layout.cpp:148-149, 361"))
    # ---- arrows to the builders ----------------------------------------------
    y2 = y1 + fh + 42
    for x in (LX + 60, RX + 60):
        _vcard(o, fid, "ink", C["ink"], x, y1 + fh, y2, [
            "1 buffer row (256 B) -> 1 builder call;",
            "the flags say what the caller knows"], "k_vnni.hpp:197-199")
    # ---- row 2: the builders -------------------------------------------------
    fh2 = 152
    cw = CW - 12
    _frame(o, LX, y2, CW, fh2, "builder: k_source_row (two overloads)")
    o.append(fn_cell(bx, y2 + 18, cw, 62, "k_source_row(view)", [
        "rank-1 bf16 view, requires(Stride == 1):",
        "keeps the view's own Aligned, Dma; no copy"], "k_vnni.hpp:212-218", "new"))
    boxes.append(("k_source_row(view)", "k_vnni.hpp:212-218"))
    o.append(fn_cell(bx, y2 + 86, cw, 62, "k_source_row(const bf16* row)", [
        "read-only row from a pointer with the caller's",
        "Aligned, Dma; neither checks alignment nor copies"], "k_vnni.hpp:206-210", "new"))
    boxes.append(("k_source_row(const bf16* row)", "k_vnni.hpp:206-210"))
    _frame(o, RX, y2, CW, fh2, "builder: k_destination_row (one overload)")
    o.append(fn_cell(bx2, y2 + 18, cw, 62, "k_destination_row(bf16* row)", [
        "writable row from a pointer with the caller's",
        "Aligned, Dma; neither checks alignment nor copies"], "k_vnni.hpp:220-224", "new"))
    boxes.append(("k_destination_row(bf16* row)", "k_vnni.hpp:220-224"))
    o.append(lines(bx2 + 8, y2 + 100, [
        "no view overload: a destination row comes from a",
        "pointer only, so the row's flags are always the",
        "caller's template arguments (defaults above)"], 9.5, 12, fill=C["muted"]))
    o.append(text(bx2 + 8, y2 + 139, "[k_vnni.hpp:220-224]", 8.5, mono=True, fill=C["cite"]))
    # ---- arrows to the row types ---------------------------------------------
    y3 = y2 + fh2 + 32
    for x in (LX + 60, RX + 60):
        _vcard(o, fid, "ink", C["ink"], x, y2 + fh2, y3, [
            "1 call -> 1 row view (the pointer, no copy)"], "k_vnni.hpp:209, 217, 223")
    # ---- row 3: the two row types --------------------------------------------
    th = 72
    o.append(label_box(LX, y3, CW, th, "const_k_row_view<Cols, Aligned, Dma>", [
        "= const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "the read-only source row of store_row (257)",
        "and page::set_k_row (kv_cache.hpp:2060)"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:200-201"))
    boxes.append(("const_k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:200-201"))
    o.append(label_box(RX, y3, CW, th, "k_row_view<Cols, Aligned, Dma>", [
        "= view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "the writable destination row of load_row (274)",
        "and page::get_k_row (kv_cache.hpp:2077)"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:203-204"))
    boxes.append(("k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:203-204"))
    # ---- arrows to the consumers ---------------------------------------------
    y4 = y3 + th + 32
    for x in (LX + 60, RX + 60):
        _vcard(o, fid, "ink", C["ink"], x, y3 + th, y4, [
            "1 row -> Cols = 128 bf16 = 256 bytes"], "k_vnni.hpp:197-201")
    # ---- row 4: the page accessors that take the row -------------------------
    ch = 68
    _box(o, LX, y4, CW, ch, "page::set_k_row(slot, kv_head, i_page, row)", [
        "VNNI slot: store_row, 4 scatters (2063)",
        "row-major slot: std::memcpy of 256 B (2065-2066)",
        "1 call per (token, KV head) of save_k [model.hpp:3104]"],
        "kv_cache.hpp:2053-2068", C["soft"], C["ink"], 10.5, 9.5,
        colors={0: C["vnni"], 1: C["rm"], 2: C["muted"]})
    boxes.append(("page::set_k_row", "kv_cache.hpp:2053-2068"))
    _box(o, RX, y4, CW, ch, "page::get_k_row(slot, kv_head, i_page, row)", [
        "VNNI slot: load_row, 4 gathers (2080)",
        "row-major slot: std::memcpy of 256 B (2082-2083)",
        "k_head_fn: 1 per (token, KV head) of a GOF [gof.cpp:211]"],
        "kv_cache.hpp:2070-2085", C["soft"], C["ink"], 10.5, 9.5,
        colors={0: C["vnni"], 1: C["rm"], 2: C["muted"]})
    boxes.append(("page::get_k_row", "kv_cache.hpp:2070-2085"))
    o.append(line(LX + CW + 10, 56, LX + CW + 10, y4 + ch, C["line"], 1, "2 4"))
    y5 = y4 + ch + 16
    note = ["the uniform-geometry overloads of set_k_row / get_k_row (kv_cache.hpp:2087-2107) "
            "forward to these with",
            "layout_t::primary_geometry; the tests and t_amx_dispatch_dtype.cpp:110 call them"]
    for s in note:
        _w(s, 9, W - 40, where="note")
    o.append(lines(LX, y5, note, 9, 11, fill=C["muted"]))
    H = int(y5 + 11 + 10)
    cap = ("Updates B2: the three transfer-row boxes at the bottom of B2 become the whole "
           "path of a row, in two columns. The left column is the read-only source row "
           "into the plane: a K buffer row of save_k or a stack row, one of the two "
           "overloads of k_source_row, const_k_row_view, then page::set_k_row, which calls "
           "store_row for a VNNI slot and memcpy for a row-major slot. The right column is "
           "the writable destination row out of the plane: the staging scratch (one row "
           "per KV head of the k_scratch array that gof::populate owns on its stack and "
           "passes to page_info::k_head_fn) or a stack row, k_destination_row, k_row_view, "
           "then page::get_k_row, which calls load_row or memcpy. Every builder wraps a "
           "pointer with no check and no copy. The row carries the caller's Aligned and "
           "Dma flags.")
    legend = [
        ("box", "white box, ink outline: the builders k_source_row (two overloads) and "
                "k_destination_row, and the two row types const_k_row_view / k_row_view; "
                "name in bold monospace, description in sans-serif"),
        ("ctx", "grey box, thin grey outline: a buffer behind a row (a K buffer row of "
                "save_k, a stack row, a test row)"),
        ("ctx_ink", "grey fill, ink outline: the page accessors page::set_k_row and "
                    "page::get_k_row that take the row; blue line = the VNNI-slot branch, "
                    "orange line = the row-major branch"),
        ("hw", "yellow: dest, the k_scratch row of the FPGA staging (gof::populate -> "
               "page_info::k_head_fn)"),
        ("grey dashed frame: a stage of the path (the buffer, the builder)", "none",
         C["line"], True, False),
        ("arrow", "ink arrow: one stage hands its row to the next, with its how-many"),
        ("blue text: what the VNNI-slot branch of the accessor calls", "text", C["vnni"]),
        ("orange text: what the row-major branch of the accessor calls", "text", C["rm"]),
        ("font_mono", "monospace = the box titles (the buffers, the builders, the row "
                      "types, the accessors)"),
        ("font_sans", "sans-serif = the headers, the descriptions, the how-many labels and "
                      "the notes"),
        ("font_cite", "small grey monospace = the lines that define a box or an arrow "
                      "(file:line)"),
        ("font_tag", "bold 'new' = the three builders are added by this PR"),
    ]
    return figure(fid, W, H, "The transfer rows: from the buffer behind a row to the "
                  "accessor that takes it", "".join(o), cap, boxes=boxes, legend=legend)
