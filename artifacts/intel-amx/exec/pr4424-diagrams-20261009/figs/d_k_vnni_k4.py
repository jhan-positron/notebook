"""Change diagram of unit k4 of the PR 4424 k_vnni.hpp page: the transfer
rows const_k_row_view / k_row_view and their builders (head lines 249-284).

Two figures: k_vnni-d4a (the two row paths, into and out of the plane) and
k_vnni-d4b (the worked example row of token 37 and where its bytes land).
Every fact drawn here comes from facts/k_vnni.json (verified claims:
k_vnni-data-24, k_vnni-function-11, k_vnni-function-12, k_vnni-data-49,
k_vnni-sequencing-2/31/32/33, k_vnni-unit-6) or from the cited head lines.
Line numbers are head line numbers of h/tron/tensor/k_vnni.hpp unless another
file is named.
"""
import sys

from svg_helpers import (C, arrow, cite, figure, fn_cell, label_box, line,
                         lines, marker_defs, rect, text, text_width)
from base_k_vnni import EX, BLOCK_2, block_panels

BASE = ("Updates B2: the three transfer-row boxes at the bottom of B2 become the "
        "whole path of a row, from the buffer behind it through k_source_row / "
        "k_destination_row to the page accessor and the operation that take it.")

FID_A, FID_B = "k_vnni-d4a", "k_vnni-d4b"
W = 700
LX, RX, CW = 20, 360, 320          # the two columns: source row (in), destination row (out)


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH d_k_vnni_k4 {where}: '{s}' needs {tw:.0f} px, has {w}",
              file=sys.stderr)


def _box(o, x, y, w, h, title, sub, ref, fill="#fff", stroke=C["ink"], tsize=11,
         ssize=9.5, lh=12.5, colors=None, dash=None):
    """A box: mono title, left-aligned sub-lines (colors: {i: colour}) and the
    citation in the lower-right corner. Appends to o."""
    o.append(rect(x, y, w, h, fill, stroke, 1.2, 4, dash))
    _w(title, tsize, w - 16, True, title)
    o.append(text(x + 8, y + 15, title, tsize, mono=True, weight=600))
    yy = y + 15
    for i, s in enumerate(sub):
        yy += lh
        _w(s, ssize, w - 16, False, title)
        o.append(text(x + 8, yy, s, ssize, fill=(colors or {}).get(i, C["ink"])))
    _w(ref, 8.5, w - 8, True, "cite " + title)
    o.append(cite(x + w - 4, y + h - 4, ref))


def _frame(o, x, y, w, h, title):
    """A thin dashed group frame with a title at its top-left."""
    o.append(rect(x, y, w, h, "none", C["line"], 1, 5, "4 3"))
    _w(title, 9.5, w - 12, where="frame " + title)
    o.append(text(x + 8, y + 12, title, 9.5, fill=C["muted"], weight=600))


def _vcard(o, fid, name, color, x, y0, y1, label_lines, ref):
    """A vertical how-many arrow; its label lines and the citation sit to the
    right of the line, top-aligned under the box the arrow leaves."""
    o.append(arrow(fid, name, [(x, y0), (x, y1)], color, 1.4))
    ty = y0 + 12
    for i, s in enumerate(label_lines):
        _w(s, 9, CW - 70, where="arrow label")
        o.append(text(x + 8, ty + i * 10.5, s, 9, fill=color, weight=600))
    o.append(text(x + 8, ty + len(label_lines) * 10.5, f"[{ref}]", 8.5, mono=True,
                  fill=C["cite"]))


def _fig_a():
    fid = FID_A
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"],
                           "muted": C["muted"]})]
    # ---- header -------------------------------------------------------------
    h1 = ("transfer rows (new): one token's Cols = 128 bf16 in dimension order = 256 "
          "bytes; not packed storage")
    _w(h1, 11, W - 40, where="header")
    o.append(text(LX, 18, h1, 11, weight=700))
    o.append(text(LX, 32, "the caller's Aligned and Dma flags travel with the row; "
                  "defaults VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE", 9.5, fill=C["muted"]))
    o.append(text(LX, 44, "[k_vnni.hpp:249-258; kv_cache_fwd.hpp:25-26]", 8.5, mono=True,
                  fill=C["cite"]))
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
    _box(o, bx, y1 + 18, bw, 66, "kout = row_of(ix, kv_head)", [
        "a bf16 K buffer row from slice<> of ks[ix]; keeps the",
        "buffer's alignment and DMA flags -> the view overload",
        "[main thread or a main helper: store_k_block]"],
        "model.hpp:3307-3311; model.hpp:3247-3250", C["soft"], C["line"], lh=11.5,
        colors={2: C["muted"]})
    boxes.append(("kout = row_of(ix, kv_head)", "model.hpp:3307-3311; model.hpp:3247-3250"))
    _box(o, bx, y1 + 90, bw, 76, "conv[0] / rows[t] / row", [
        "conv: any other activation type, converted to bf16 on",
        "the stack first -> the pointer overload (3317)",
        "rows[t]: the stack rows of block_to_rows (515, 522)",
        "row: the stack row of copy_token (432, 434)"],
        "model.hpp:3266-3269; k_vnni.hpp:515, 432", C["soft"], C["line"], lh=11.5)
    boxes.append(("conv[0] / rows[t] / row", "model.hpp:3266-3269; k_vnni.hpp:515, 432"))

    _frame(o, RX, y1, CW, fh, "the buffer behind the row (the caller's)")
    _box(o, bx2, y1 + 18, bw, 88, "dest: k_scratch of gof::populate", [
        "256 B per KV head of the 64-byte-aligned array on",
        "gof::populate's stack, passed to page_info::k_head_fn;",
        "filled through get_k_row for a converted block only",
        "(a row-major row is read in place, full.hpp:2762-2764)",
        "[attention worker or main, GOF staging]"],
        "gof.cpp:203, 213; full.hpp:2747-2766", C["soft"], C["line"], lh=11.5,
        colors={4: C["muted"]})
    boxes.append(("dest: k_scratch of gof::populate, 256 B per head",
                  "gof.cpp:203, 213; full.hpp:2747-2766"))
    _box(o, bx2, y1 + 112, bw, 66, "rows[t] / row", [
        "rows[16][Cols]: the stack rows of block_to_vnni",
        "(500, 505) and block_to_rows (515, 518)",
        "row[Cols]: the stack row of copy_token (432, 433)"],
        "k_vnni.hpp:500, 515, 432", C["soft"], C["line"], lh=11.5)
    boxes.append(("rows[t] / row", "k_vnni.hpp:500, 515, 432"))

    # ---- arrows to the builders ----------------------------------------------
    y2 = y1 + fh + 42
    for x in (LX + 60, RX + 60):
        _vcard(o, fid, "ink", C["ink"], x, y1 + fh, y2, [
            "1 buffer row (256 B) -> 1 builder call;",
            "the flags say what the caller knows"], "k_vnni.hpp:260-261")

    # ---- row 2: the builders (fn_cell with two description lines: 62 px, so
    # the second line's descenders clear the tag and the citation) ----------
    fh2 = 152
    cw = CW - 12
    _frame(o, LX, y2, CW, fh2, "builder: k_source_row (two overloads)")
    o.append(fn_cell(bx, y2 + 18, cw, 62, "k_source_row(view)", [
        "rank-1 bf16 view, requires(Stride == 1):",
        "keeps the view's own Aligned, Dma; no copy"], "k_vnni.hpp:268-277", "new"))
    boxes.append(("k_source_row(view)", "k_vnni.hpp:268-277"))
    o.append(fn_cell(bx, y2 + 86, cw, 62, "k_source_row(const bf16* row)", [
        "read-only row from a pointer with the caller's",
        "Aligned, Dma; neither checks alignment nor copies"], "k_vnni.hpp:262-266", "new"))
    boxes.append(("k_source_row(const bf16* row)", "k_vnni.hpp:262-266"))

    _frame(o, RX, y2, CW, fh2, "builder: k_destination_row (one overload)")
    o.append(fn_cell(bx2, y2 + 18, cw, 62, "k_destination_row(bf16* row)", [
        "writable row from a pointer with the caller's",
        "Aligned, Dma; neither checks alignment nor copies"], "k_vnni.hpp:279-283", "new"))
    boxes.append(("k_destination_row(bf16* row)", "k_vnni.hpp:279-283"))
    o.append(lines(bx2 + 8, y2 + 100, [
        "no view overload: a destination row comes from a",
        "pointer only, so the row's flags are always the",
        "caller's template arguments (defaults above)"], 9.5, 12, fill=C["muted"]))
    o.append(text(bx2 + 8, y2 + 139, "[k_vnni.hpp:279-283]", 8.5, mono=True, fill=C["cite"]))

    # ---- arrows to the row types ---------------------------------------------
    y3 = y2 + fh2 + 32
    for x in (LX + 60, RX + 60):
        _vcard(o, fid, "ink", C["ink"], x, y2 + fh2, y3, [
            "1 call -> 1 row view (the pointer, no copy)"], "k_vnni.hpp:265, 276, 282")

    # ---- row 3: the two row types --------------------------------------------
    th = 72
    o.append(label_box(LX, y3, CW, th, "const_k_row_view<Cols, Aligned, Dma>", [
        "= const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "the read-only source row of store_row (353),",
        "store_row_major (480) and page::set_k_row"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:254-255"))
    boxes.append(("const_k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:254-255"))
    o.append(label_box(RX, y3, CW, th, "k_row_view<Cols, Aligned, Dma>", [
        "= view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "the writable destination row of load_row (371),",
        "load_row_major (490) and page::get_k_row"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:257-258"))
    boxes.append(("k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:257-258"))

    # ---- arrows to the consumers ---------------------------------------------
    y4 = y3 + th + 32
    for x in (LX + 60, RX + 60):
        _vcard(o, fid, "ink", C["ink"], x, y3 + th, y4, [
            "1 row -> Cols = 128 bf16 = 256 bytes"], "k_vnni.hpp:249-251")

    # ---- row 4: the page accessors that take the row -------------------------
    ch = 68
    _box(o, LX, y4, CW, ch, "page::set_k_row(slot, kv_head, i_page, row)", [
        "k_block_is_vnni -> store_row: 4 scatters (2255)",
        "else store_row_major: memcpy of 256 B (2257)",
        "n x n_kv_heads calls per short run [model.hpp:3300-3320]"],
        "kv_cache.hpp:2247-2262", C["soft"], C["ink"], 10.5, 9.5,
        colors={0: C["vnni"], 1: C["rm"], 2: C["muted"]})
    boxes.append(("page::set_k_row", "kv_cache.hpp:2247-2262"))
    _box(o, RX, y4, CW, ch, "page::get_k_row(slot, kv_head, i_page, row)", [
        "k_block_is_vnni -> load_row: 4 gathers (2299)",
        "else load_row_major: memcpy of 256 B (2301)",
        "k_head_fn: 1 per (token, KV head) of a GOF [gof.cpp:213]"],
        "kv_cache.hpp:2291-2306", C["soft"], C["ink"], 10.5, 9.5,
        colors={0: C["vnni"], 1: C["rm"], 2: C["muted"]})
    boxes.append(("page::get_k_row", "kv_cache.hpp:2291-2306"))
    o.append(line(LX + CW + 10, 56, LX + CW + 10, y4 + ch, C["line"], 1, "2 4"))
    y5 = y4 + ch + 16
    rm_note = ["row_major_row returns the same row types with the default flags "
               "(465-466; unit k8):",
               "k_row_view<Cols> for a writable plane, const_k_row_view<Cols> for a "
               "read-only one"]
    for s in rm_note:
        _w(s, 9, W - 40, where="row_major_row note")
    o.append(lines(LX, y5, rm_note, 9, 11, fill=C["muted"]))
    H = int(y5 + 11 + 10)
    cap = ("Updates B2: the three transfer-row boxes at the bottom of B2 become the whole "
           "path of a row, in two columns. The left column is the read-only source row "
           "into the plane: a K buffer row or a stack row, one of the two overloads of "
           "k_source_row, const_k_row_view, then page::set_k_row, which calls store_row "
           "or store_row_major. The right column is the writable destination row out of "
           "the plane: the staging scratch (256 bytes per KV head of the k_scratch array "
           "that gof::populate owns on its stack and passes to page_info::k_head_fn, "
           "gof.cpp:203, 213) or a stack row, k_destination_row, k_row_view, then "
           "page::get_k_row, which calls load_row or load_row_major. Every builder wraps "
           "a pointer with no check and no copy. The row carries the caller's Aligned "
           "and Dma flags.")
    legend = [
        ("ctx", "grey box, thin grey outline: the caller's buffer behind the row, "
                "kout = row_of (model.hpp), conv[0] / rows[t] / row, dest: k_scratch of "
                "gof::populate, rows[t] / row"),
        ("grey dashed frame, grey title: a group of boxes of one column, the caller's "
         "buffers or the builders; the grey dashed line between the columns separates "
         "'into the plane' from 'out of the plane'", "none", C["line"], True, False),
        ("box", "white box, ink outline: a builder, k_source_row (two overloads) and "
                "k_destination_row, or a row type, const_k_row_view and k_row_view; name "
                "in bold monospace, description under it"),
        ("ctx_ink", "grey fill, ink outline: the page accessor that takes the row, "
                    "page::set_k_row (into the plane) and page::get_k_row (out of it)"),
        ("arrow", "ink arrow: call order top to bottom, buffer -> builder -> row type -> "
                  "page accessor; its label says how many (1 buffer row -> 1 builder call)"),
        ("blue text: the converted-block branch of the page accessor, k_block_is_vnni -> "
         "store_row (4 scatters) or load_row (4 gathers)", "text", C["vnni"]),
        ("orange text: the row-major branch, else store_row_major or load_row_major "
         "(memcpy of 256 B)", "text", C["rm"]),
        ("font_mono", "monospace = a name from the code: the buffers, the builders, "
                      "const_k_row_view, k_row_view and the page accessors"),
        ("font_sans", "sans-serif = prose: what each box holds, the how-many labels, the "
                      "frame titles, the row_major_row note"),
        ("font_cite", "small grey monospace = the head lines that define the box or the "
                      "arrow (k_vnni.hpp, kv_cache.hpp, model.hpp, gof.cpp, full.hpp)"),
        ("font_tag", "bold 'new' = the three builders are added by this PR"),
    ]
    return figure(fid, W, H, "Transfer rows: const_k_row_view, k_row_view and their builders",
                  "".join(o), cap, boxes=boxes, legend=legend)


def _fig_b():
    fid = FID_B
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"]})]
    # ---- worked example: the row of token 37 ---------------------------------
    ty = 18
    t1 = (f"worked example: the transfer row of token {EX['token']} = 128 bf16 in "
          "dimension order = 256 bytes")
    _w(t1, 10.5, W - 40, where="worked example title")
    o.append(text(LX, ty, t1, 10.5, weight=700))
    sy, sh, sw = ty + 22, 22, 640
    seg = sw / 4
    o.append(rect(LX, sy, sw, sh, "#fff", C["ink"], 1.2, 2))
    for s in range(4):
        if s:
            o.append(line(LX + s * seg, sy, LX + s * seg, sy + sh, C["ink"], 0.8))
        o.append(text(LX + s * seg + seg / 2, sy + 15, f"s = {s}", 9.5, "middle", True,
                      fill=C["muted"]))
        sub = f"dims {32 * s}..{32 * s + 31} = bytes {64 * s}..{64 * s + 63}"
        _w(sub, 8.5, seg - 6, where="segment label")
        o.append(text(LX + s * seg + seg / 2, sy + sh + 11, sub, 8.5, "middle",
                      fill=C["muted"]))
    cell = sw / 128
    dx = LX + EX["dim"] * cell
    # the marker of dimension 70: a filled cell with no border of its own
    o.append(rect(dx, sy + 1, cell, sh - 2, C["vnni"], "none", 0, 0))
    o.append(text(dx + cell / 2, sy - 5, f"dim {EX['dim']} = byte {EX['dim'] * 2} "
                  f"of the row", 9, "middle", fill=C["vnni"], weight=600))
    o.append(cite(W - 20, sy - 5, "k_vnni.hpp:249-253"))
    boxes.append((f"transfer row of token {EX['token']} (worked example)",
                  "k_vnni.hpp:249-253"))
    # ---- the two facts of this unit (lines 249-253, 260-261) -------------------
    fx, fy = 360, sy + sh + 34
    facts = [
        (["the caller's Aligned and Dma flags travel with the row:",
          "the builders neither check alignment nor copy; the",
          "flags state what the caller knows about its buffer"],
         "k_vnni.hpp:250-251, 260-261"),
        (["the row operations load and store the row with",
          "unaligned vector instructions (_mm512_loadu_si512 358,",
          "_mm512_storeu_si512 378), so a row does not need",
          "VIEW_ALIGNED_TRUE, unlike the packed V rows"],
         "k_vnni.hpp:251-253"),
    ]
    yy = fy
    for ls, ref in facts:
        for s in ls:
            _w(s, 9.5, W - 20 - fx, where="fact line")
        o.append(lines(fx, yy, ls, 9.5, 12, fill=C["ink"]))
        yy += 12 * len(ls)
        o.append(text(fx, yy, f"[{ref}]", 8.5, mono=True, fill=C["cite"]))
        yy += 18
    # ---- the row goes to page::set_k_row, which picks the operation -----------
    ax = LX + 12
    by = sy + sh + 94
    o.append(arrow(fid, "ink", [(ax, sy + sh + 16), (ax, by - 2)], C["ink"], 1.4))
    o.append(lines(ax + 8, sy + sh + 38, ["1 row (256 B) -> 1 page::set_k_row",
                                           "call per (token, KV head)"], 9, 10.5,
                   fill=C["ink"], weight=600))
    o.append(text(ax + 8, sy + sh + 61, "[kv_cache.hpp:2247-2250; model.hpp:3300-3320]",
                  8.5, mono=True, fill=C["cite"]))
    _box(o, LX, by, 320, 92, "page::set_k_row(slot, kv_head, i_page, row)", [
        "k_block_is_vnni -> store_row (unit K6): 4 scatters",
        f"into column t = {EX['t']} of block 2's 64 lines (2255)",
        "else store_row_major (unit K8): one 256-byte memcpy",
        f"into panel (1,2) #{EX['rm']['panel']}, lines 4..7 (2257)"],
        "kv_cache.hpp:2247-2262", C["soft"], C["ink"], 10.5, 9.5, 12,
        colors={0: C["vnni"], 1: C["vnni"], 2: C["rm"], 3: C["rm"]})
    boxes.append(("page::set_k_row", "kv_cache.hpp:2247-2262"))
    boxes.append(("store_row (unit K6, the converted-block branch)", "k_vnni.hpp:349-362"))
    boxes.append(("store_row_major (unit K8, the row-major branch)", "k_vnni.hpp:476-482"))
    ly = by + 92 + 18
    tail = [f"the plane holds dim {EX['dim']} of token {EX['token']} at byte {EX['byte']} "
            f"= 2 x k_vnni::index({EX['token']}, {EX['dim']}) in the VNNI form (B1), and at "
            f"element {EX['rm_dim_elem']} of the",
            "row-major form (B1, last line): the same 256 bytes, two places"]
    for s in tail:
        _w(s, 9.5, W - 40, where="tail line")
    o.append(lines(LX, ly, tail, 9.5, 12))
    H = int(ly + 12 + 8)
    cap = ("Updates B2: the worked example row of token 37 shows why a transfer row is "
           "not packed storage. Dimension 70 is byte 140 of the row but byte 10452 of the "
           "plane. The row carries the caller's Aligned and Dma flags, and the row "
           "operations read it with unaligned loads. page::set_k_row hands it to "
           "store_row (unit K6) for a converted block, or to store_row_major (unit K8) "
           "for a row-major block.")
    legend = [
        ("box", "white box, ink outline: the transfer row of token 37, 128 bf16 = 256 "
                "bytes in dimension order, split into its four segments s = 0..3"),
        ("solid blue cell: dimension 70 of the row = byte 140, the worked example's "
         "dimension", C["vnni"], "none", False, False),
        ("ctx_ink", "grey fill, ink outline: page::set_k_row, the page accessor that takes "
                    "the row and picks store_row or store_row_major"),
        ("arrow", "ink arrow: the row goes to page::set_k_row; its label says how many "
                  "(1 row -> 1 call per (token, KV head))"),
        ("blue text: the VNNI side, the dim 70 label and the converted-block branch "
         "k_block_is_vnni -> store_row (unit K6), 4 scatters into column t = 5 of block 2",
         "text", C["vnni"]),
        ("orange text: the row-major branch, else store_row_major (unit K8), one 256-byte "
         "memcpy into panel (1,2) #6", "text", C["rm"]),
        ("font_mono", "monospace = a name or a value from the code: the segment index "
                      "s = 0..3 and page::set_k_row"),
        ("font_sans", "sans-serif = prose: the segment ranges, the two facts of lines "
                      "249-253 and 260-261, the how-many label, the closing note"),
        ("font_cite", "small grey monospace = the head lines that define the row, the "
                      "facts and the accessor (k_vnni.hpp, kv_cache.hpp, model.hpp)"),
    ]
    return figure(fid, W, H, "The worked example transfer row of token 37, its two facts, "
                  "and the page accessor that takes it", "".join(o), cap, boxes=boxes,
                  legend=legend)


def figs():
    return [_fig_a(), _fig_b()]


if __name__ == "__main__":
    print("".join(figs()))
