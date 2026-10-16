"""Change diagrams of unit k6 of the PR 4424 page for h/tron/tensor/k_vnni.hpp:
store_row, load_row and copy_token (head lines 344-381, 422-436).

Two figures: k_vnni-d6a (the two row operations on the worked example) and
k_vnni-d6b (the block-bit check of their callers, and copy_token).

Every fact drawn here comes from facts/k_vnni.json (verified claims) or from
the head file itself. Line numbers are head line numbers of
h/tron/tensor/k_vnni.hpp unless another file is named.
"""
import sys

from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, label_box,
                         lines, marker_defs, rect, text, text_width)
from base_k_vnni import EX, BLOCK_2, panel_lines

BASE = ("Updates B4: steps 3 and 4 (store_row and load_row on block 2 of the worked "
        "example) are drawn at the instruction level. The 256-byte transfer row splits "
        "into its 4 dimension steps, each scattered into column t = 5 of panel (s, 2) "
        "at pair_base + pair_row_offsets, and the gather back. The second figure (d6b) "
        "updates B4 and the callers box of B3: the block-bit check of page::set_k_row / "
        "get_k_row that selects them, the row-major operations of the other branch, and "
        "copy_token as load_row then store_row through a local row.")

W = 700
GX, PW, PG, PH = 164, 118, 14, 72          # the 4 panels of block 2, as in B4
T = EX["t"]                                # token 37 = column t = 5 of its block
DP = EX["dp"]                              # dimension 70 = pair row 3 of step 2
S_EX = EX["s"]


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH d6 {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


def _px(s):
    """x of panel (s, 2) and of its column t = 5."""
    x = GX + s * (PW + PG)
    return x, x + T * (PW / 16) + PW / 32


def _row_segment(x, y, w, h, hi_dp=None):
    """One dimension step of a transfer row as 16 dwords (dimension pairs
    dp = 0..15, two bf16 each); hi_dp is drawn in the VNNI colour."""
    dw = w / 16
    o = []
    for dp in range(16):
        on = dp == hi_dp
        o.append(rect(x + dp * dw, y, dw, h, C["vnni_fill"] if on else "#fff",
                      C["vnni"] if on else C["line"], 1.4 if on else 0.7, 0))
    o.append(rect(x, y, w, h, "none", C["ink"], 0.9, 0))
    return "".join(o)


def _transfer_row(o, y, labels_above):
    """The 4 steps of one transfer row, one segment above (or below) each
    panel (s, 2); the worked example's dword (dims 70, 71) is marked."""
    for s in range(4):
        x, _ = _px(s)
        o.append(_row_segment(x, y, PW, 24, hi_dp=DP if s == S_EX else None))
        lab = f"s = {s}: dims {32 * s}..{32 * s + 31}"
        ly = y - 5 if labels_above else y + 24 + 11
        o.append(text(x + PW / 2, ly, lab, 9, "middle", True, fill=C["muted"]))


def _panels(o, y, labels_above, col_read):
    """The 4 panels of block 2 in the VNNI form, column t = 5 marked
    (written: solid; read: dashed), pair row 3 of panel (2,2) outlined."""
    for s in range(4):
        x, _ = _px(s)
        lab = f"panel ({s},{BLOCK_2}) #{4 * s + BLOCK_2}"
        ly = y - 5 if labels_above else y + PH + 11
        o.append(text(x + PW / 2, ly, lab, 9, "middle", True, fill=C["muted"]))
        o.append(panel_lines(x, y, PW, PH, ["vnni"] * 16,
                             hi_rows=[DP] if s == S_EX else (), col=T,
                             col_read=col_read))


def _vlabels(o, x, y, items, color):
    for i, s in enumerate(items):
        o.append(text(x, y + i * 10, s, 9, fill=color, weight=600 if i == 0 else None))


def _header(o, y, title, sub, ref):
    _w(title, 12, W - 20, where="header")
    _w(sub, 9.5, W - 20, where="header sub")
    o.append(text(14, y + 14, title, 12, weight=700))
    o.append(text(14, y + 28, sub, 9.5, fill=C["muted"]))
    o.append(text(14, y + 40, ref, 8.5, mono=True, fill=C["cite"]))


# ---------------------------------------------------------------------------
# d6a: store_row and load_row on the worked example


def fig_a():
    fid = "k_vnni-d6a"
    boxes = []
    o = [marker_defs(fid, {"vnni": C["vnni"]})]
    # ---- 1: store_row ---------------------------------------------------------
    y0 = 8
    _header(o, y0, "1  store_row(plane, 37, src): one token's row into its column of "
            "block 2 (worked example)",
            "[main thread | main helpers], each inside its claimed unit: several threads "
            "store different tokens of one plane at the same time",
            "[k_vnni.hpp:346-348; Note [Shared block save] model.hpp:3085-3152; "
            "model.hpp:3346-3350]")
    ry = y0 + 70
    _transfer_row(o, ry, labels_above=True)
    o.append(label_box(14, ry - 17, 140, 64, "src", [
        "const_k_row_view<128>", "256 B, loadu per step"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:353; 254-255"))
    boxes.append(("src (const_k_row_view<Cols, Aligned, Dma>)", "k_vnni.hpp:353; 254-255"))
    py = ry + 78
    for s in range(4):
        x, cx = _px(s)
        o.append(arrow(fid, "vnni", [(cx, ry + 24), (cx, py - 1)], C["vnni"], 1.4))
        _vlabels(o, cx + 6, ry + 44, ["scatter", "16 dwords", "4 B x 16 lines"], C["vnni"])
    _panels(o, py, labels_above=False, col_read=False)
    o.append(label_box(14, py, 140, PH + 6, "block 2", [
        "panels (s, 2), s = 0..3", "4 KiB; token 37 owns", "dword 5 of all 64 lines"],
        C["vnni_fill"], C["vnni"], 11, ref="k_vnni.hpp:30-32, 443-445"))
    boxes.append(("block 2: panels (s, 2), column t = 5", "k_vnni.hpp:30-32, 443-445"))
    boxes.append(("store_row", "k_vnni.hpp:349-362"))
    ny = py + PH + 28
    n1 = ("1 token -> DIM_STEPS_4 x STEP_PAIRS_16 = 64 dword slots; only these are "
          "written [k_vnni.hpp:344-348, 357-361]")
    n2 = ("pair_base(plane, s, 37) = plane + ((s * 4 + 2) * 256 + 5) * 4 B; "
          "pair_row_offsets() x 4 B = 0, 64, .., 960 [k_vnni.hpp:288-310]")
    n3 = (f"worked example: s = 2, dword 3 of the row = dims 70, 71 -> byte 10260 + 192 "
          f"= {EX['byte']} = 2 x k_vnni::index(37, 70) [k_vnni.hpp:132-141]")
    _w(n1, 9.5, W - 28, where="n1")
    _w(n2, 9, W - 28, where="n2")
    _w(n3, 9, W - 28, where="n3")
    o.append(text(14, ny, n1, 9.5, fill=C["ink"]))
    o.append(lines(14, ny + 11, [n2, n3], 9, 11, fill=C["muted"]))
    # ---- 2: load_row ----------------------------------------------------------
    y1 = ny + 30
    _header(o, y1, "2  load_row(plane, 37, dst): the inverse, 4 gathers of 16 dwords out "
            "of the same 64 slots",
            "[GOF staging: attention worker or main] via get_k_row; [scheduler thread, "
            "tree lock] via copy_storage_slot and block_to_rows",
            "[full.hpp:2762-2766; kv_cache.hpp:2750, 701-704; k_vnni.hpp:518]")
    py2 = y1 + 64
    _panels(o, py2, labels_above=True, col_read=True)
    o.append(label_box(14, py2, 140, PH + 6, "src", [
        "k_vnni_view<const bf16,", "64, 128>: block 2 read,", "dword 5 of all 64 lines"],
        "#fff", C["vnni"], 11, ref="k_vnni.hpp:367-369"))
    boxes.append(("src (k_vnni_view<const bf16, Rows, Cols>)", "k_vnni.hpp:367-369"))
    ry2 = py2 + PH + 58
    for s in range(4):
        x, cx = _px(s)
        o.append(arrow(fid, "vnni", [(cx, py2 + PH), (cx, ry2 - 1)], C["vnni"], 1.4,
                       dash="4 3"))
        _vlabels(o, cx + 6, py2 + PH + 22, ["gather", "16 dwords", "4 B x 16 lines"],
                 C["vnni"])
    _transfer_row(o, ry2, labels_above=False)
    o.append(label_box(14, ry2 - 17, 140, 64, "dst", [
        "k_row_view<128>", "256 B, storeu per step"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:371; 257-258"))
    boxes.append(("dst (k_row_view<Cols, Aligned, Dma>)", "k_vnni.hpp:371; 257-258"))
    boxes.append(("load_row", "k_vnni.hpp:367-380"))
    ny2 = ry2 + 24 + 32
    m1 = ("same addresses as store_row: pair_base(plane, s, 37) + pair_row_offsets() "
          "[k_vnni.hpp:374-377]; 64 lines read for one token")
    m2 = ("the row-major form of a block costs 4 lines per token instead "
          "(load_row_major, k_vnni.hpp:484-492)")
    _w(m1, 9.5, W - 28, where="m1")
    _w(m2, 9, W - 28, where="m2")
    o.append(text(14, ny2, m1, 9.5, fill=C["ink"]))
    o.append(text(14, ny2 + 11, m2, 9, fill=C["muted"]))
    H = int(ny2) + 20
    cap = ("Updates B4: steps 3 and 4 of the base sequencing diagram, drawn at the "
           "instruction level for the worked example (token 37 = column t = 5 of block "
           "2, dimension 70 = pair row 3 of step 2). store_row splits the 256-byte "
           "transfer row into 4 dimension steps and scatters each as 16 dwords into "
           "column t = 5 of panel (s, 2), so one token touches 4 bytes in each of its "
           "block's 64 lines and no other token's bytes. load_row gathers the same 64 "
           "slots back into a transfer row; look at the marked dword (dims 70, 71) and "
           "the outlined pair row 3 it lands in.")
    legend = [
        ("vnni", "blue: the 16 pair rows of each panel (s, 2) of block 2, the block 2 "
                 "box, and the marked dword (dims 70, 71) of the transfer row; blue text = "
                 "the scatter and gather labels"),
        ("lane", "white cell, thin grey outline: a dword of a transfer-row step (16 per "
                 "step s), other than the marked dword 3 of step 2"),
        ("solid blue column, ink outline: column t = 5 of panel (s, 2), the 64 dword "
         "slots store_row writes for token 37", C["vnni"], C["ink"], False, False),
        ("dashed ink column: column t = 5 of panel (s, 2), the same 64 dword slots as "
         "load_row reads them", "none", C["ink"], True, False),
        ("ink frame: the outline of a panel or of a transfer-row step; the thicker one "
         "is pair row 3 of panel (2,2), where dims 70, 71 land",
         "none", C["ink"], False, False),
        ("box", "white box, ink outline: the transfer-row views src (const_k_row_view<128>) "
                "and dst (k_row_view<128>); name in bold monospace, description in grey "
                "sans-serif"),
        ("white box, blue outline: src of load_row, a k_vnni_view<const bf16, 64, 128> "
         "that reads block 2", "#fff", C["vnni"], False, False),
        ("blue arrow: a scatter of store_row (solid) or a gather of load_row (dashed), "
         "16 dwords between a transfer-row step and column t = 5; the blue labels name "
         "them", "arrow", C["vnni"]),
        ("font_mono", "monospace = src, dst, block 2, the step labels s = 0..3 and the "
                      "panel labels (s,2) #n"),
        ("font_sans", "sans-serif = the two step titles, the thread notes under them, the "
                      "scatter and gather labels, and the notes under the panels"),
        ("font_cite", "small grey monospace = the lines that define a box, a step or a "
                      "note (file:line)"),
    ]
    return figure(fid, W, H, "store_row and load_row: one token's row into and out of "
                  "the packed plane", "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# d6b: the callers' block-bit check, and copy_token


def fig_b():
    fid = "k_vnni-d6b"
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    # ---- 3: the callers' check ---------------------------------------------------
    y2 = 8
    _header(o, y2, "3  who calls them: page::set_k_row / get_k_row pick by the block's "
            "converted bit",
            "reads block bit c = i_page / 16 of k_vnni_blocks_ with one acquire load; "
            "set once the block holds the VNNI layout",
            "[kv_cache.hpp:2514-2518; k_vnni_blocks_ kv_cache.hpp:2618-2622; "
            "Note [K VNNI storage] kv_cache.hpp:651]")
    rows = [
        ("page::set_k_row", ["Layout-agnostic K row store: the row",
                             "into the layout the slot and block use"],
         "kv_cache.hpp:2247-2262", "store_row",
         ["One token's row in: 4 scatters", "of 16 dwords, 64 pair slots"],
         "k_vnni.hpp:349-362", "true: store_row [kv_cache.hpp:2254-2255]",
         "store_row_major", "k_vnni.hpp:476-482", "2257"),
        ("page::get_k_row", ["Layout-agnostic K row load: the",
                             "inverse of set_k_row, unaligned stores"],
         "kv_cache.hpp:2291-2306", "load_row",
         ["One token's row out: 4 gathers", "of 16 dwords (the inverse)"],
         "k_vnni.hpp:367-380", "true: load_row [kv_cache.hpp:2298-2299]",
         "load_row_major", "k_vnni.hpp:486-492", "2301"),
    ]
    lw, kw, tw, ch = 220, 160, 180, 64
    lx, kx, tx = 14, 14 + lw + 52, 14 + lw + 52 + kw + 52
    cy = y2 + 54
    boxes.append(("k_block_is_vnni(k_state_ix(slot), i_page)", "kv_cache.hpp:2514-2518"))
    for name, desc, ref, tgt, tdesc, tref, true_, else_name, else_ref, else_site in rows:
        for d in desc:
            _w(d, 9.5, lw - 16, where=f"desc {name}")
        for d in tdesc:
            _w(d, 9.5, tw - 16, where=f"desc {tgt}")
        o.append(fn_cell(lx, cy, lw, ch, name, desc, ref, "new"))
        boxes.append((name, ref))
        o.append(label_box(kx, cy + 3, kw, 58, "k_block_is_vnni", [
            "(k_state_ix(slot), i_page)", "load acquire, block bit c"],
            C["blk_fill"], C["blk"], 11, ref="kv_cache.hpp:2514-2518"))
        o.append(fn_cell(tx, cy, tw, ch, tgt, tdesc, tref, "new", C["vnni_fill"],
                         C["vnni"]))
        my = cy + ch / 2
        o.append(card_arrow(fid, "ink", [(lx + lw, my), (kx - 2, my)], C["ink"],
                            "1 row", 0, -6, 1.4, size=9.5))
        o.append(card_arrow(fid, "vnni", [(kx + kw, my), (tx - 2, my)], C["vnni"],
                            "true", 0, -6, 1.6, size=9.5))
        fx = kx + kw / 2
        # the false branch: an orange box of the row-major operation (unit K8)
        # under the decision box, the arrow pointing at it
        o.append(arrow(fid, "rm", [(fx, cy + 61), (fx, cy + 78)], C["rm"], 1.6))
        o.append(text(fx + 6, cy + 74, f"false [kv_cache.hpp:{else_site}]", 9, fill=C["rm"],
                      weight=600))
        ebx = kx - 20
        o.append(rect(ebx, cy + 80, 200, 22, C["rm_fill"], C["rm"], 1.2, 3))
        o.append(text(ebx + 6, cy + 95, else_name, 10, mono=True, weight=600))
        o.append(cite(ebx + 196, cy + 95, else_ref))
        boxes.append((f"{else_name} (the false branch of {name})", else_ref))
        o.append(text(14, cy + ch + 13, true_, 9, fill=C["vnni"], weight=600))
        cy += ch + 56
    boxes.append(("store_row (target of set_k_row)", "k_vnni.hpp:349-362"))
    boxes.append(("load_row (target of get_k_row)", "k_vnni.hpp:367-380"))
    oc = ["other callers of load_row: copy_storage_slot moves a token out of a converted "
          "source block into row_major_row of the",
          "destination [kv_cache.hpp:2747-2756]; block_to_rows gathers the 16 rows of a "
          "block to the stack [k_vnni.hpp:518]"]
    for s_ in oc:
        _w(s_, 9, W - 28, where="oc")
    o.append(lines(14, cy + 2, oc, 9, 11, fill=C["muted"]))
    # ---- 4: copy_token -----------------------------------------------------------
    y3 = cy + 24
    _header(o, y3, "4  copy_token(dst, dst_token, src, src_token): load_row, then "
            "store_row, through a local row",
            "callers at the head: the layout test only (t_k_vnni_layout.cpp:197); the "
            "production page copy does not use it",
            "[k_vnni.hpp:422-435; kv_cache.hpp:2747-2756]")
    by = y3 + 50
    bw, bh = 124, 62
    bx = [14, 276, 538]
    o.append(label_box(bx[0], by, bw, bh, "src", ["k_vnni_view<const bf16,", "64, 128>"],
                       "#fff", C["vnni"], 10, ref="k_vnni.hpp:430"))
    boxes.append(("src (copy_token)", "k_vnni.hpp:430"))
    o.append(label_box(bx[1], by, bw, bh, "row[Cols]", ["alignas(64) bf16, 256 B",
                                                        "on the stack"],
                       C["soft"], C["ink"], 10, ref="k_vnni.hpp:432"))
    boxes.append(("row[Cols] (copy_token local row)", "k_vnni.hpp:432"))
    o.append(label_box(bx[2], by, bw, bh, "dst", ["k_vnni_view<bf16,", "64, 128>"],
                       C["vnni_fill"], C["vnni"], 10, ref="k_vnni.hpp:428"))
    boxes.append(("dst (copy_token)", "k_vnni.hpp:428"))
    boxes.append(("copy_token", "k_vnni.hpp:426-435"))
    ay = by + 24
    calls = [(["load_row(src,", "src_token,", "k_destination_row(row))"], "k_vnni.hpp:433"),
             (["store_row(dst,", "dst_token,", "k_source_row(row))"], "k_vnni.hpp:434")]
    for i, (cl, cref) in enumerate(calls):
        x0, x1 = bx[i] + bw, bx[i + 1]
        o.append(card_arrow(fid, "vnni", [(x0, ay), (x1 - 2, ay)], C["vnni"],
                            "64 dword slots", 0, -6, 1.4, size=9.5))
        for d in cl:
            _w(d, 8.5, x1 - x0 - 8, True, where="call")
        o.append(lines(x0 + 4, ay + 14, cl, 8.5, 10, mono=True, fill=C["ink"]))
        o.append(text(x0 + 4, ay + 44, f"[{cref}]", 8.5, mono=True, fill=C["cite"]))
    ey = by + bh + 28
    e = ["tokens own disjoint slots, so no other token of dst is touched "
         "[k_vnni.hpp:424-425]; the production page copy moves a token with",
         "load_row + store_row_major via row_major_row [kv_cache.hpp:2747-2756]; "
         "copy_token at kv_cache.hpp:2681 is the V plane's (v_vnni.hpp)"]
    for s_ in e:
        _w(s_, 9, W - 28, where="e")
    o.append(lines(14, ey, e, 9, 11, fill=C["muted"]))
    H = int(ey) + 20
    cap = ("Updates B4 (and the callers box of B3): page::set_k_row and page::get_k_row "
           "reach store_row and load_row only when k_block_is_vnni finds the block's "
           "converted bit set. A row-major block takes store_row_major / load_row_major "
           "instead (the orange box under the decision box, unit K8). copy_token chains "
           "load_row and store_row through a 64-byte-aligned local row. At the head only "
           "the layout test calls it (t_k_vnni_layout.cpp:197), so the production "
           "callers of load_row and store_row are the ones named in the two headers "
           "above, not copy_token.")
    legend = [
        ("box", "white box, ink outline: the callers page::set_k_row and page::get_k_row; "
                "name in bold monospace, description in sans-serif"),
        ("blk", "pink: the k_block_is_vnni decision box, one acquire load of block bit c "
                "of k_vnni_blocks_"),
        ("vnni", "blue: store_row and load_row, the targets of the true branch, and dst "
                 "of copy_token (k_vnni_view<bf16, 64, 128>)"),
        ("rm", "orange: store_row_major and load_row_major, the targets of the false "
               "branch (unit K8)"),
        ("white box, blue outline: src of copy_token, a k_vnni_view<const bf16, 64, 128> "
         "that is only read", "#fff", C["vnni"], False, False),
        ("ctx_ink", "grey fill, ink outline: row[Cols], the 256-byte local row on the "
                    "stack that copy_token passes through"),
        ("arrow", "ink arrow: page::set_k_row / get_k_row hand 1 row to the "
                  "k_block_is_vnni check"),
        ("blue arrow: the true branch into store_row / load_row, and the two copy_token "
         "calls (64 dword slots each); the blue labels name them", "arrow", C["vnni"]),
        ("orange arrow: the false branch into store_row_major / load_row_major; the "
         "orange labels name it", "arrow", C["rm"]),
        ("font_mono", "monospace = page::set_k_row, page::get_k_row, k_block_is_vnni, "
                      "store_row, load_row, store_row_major, load_row_major, src, "
                      "row[Cols], dst and the two copy_token calls"),
        ("font_sans", "sans-serif = the two step titles, what each cell does, the true and "
                      "false labels, the how-many labels and the notes"),
        ("font_cite", "small grey monospace = the lines that define a cell or a branch "
                      "(file:line)"),
        ("font_tag", "bold 'new' = added by this PR (the four function cells)"),
    ]
    return figure(fid, W, H, "The block-bit check of set_k_row / get_k_row, and copy_token",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
