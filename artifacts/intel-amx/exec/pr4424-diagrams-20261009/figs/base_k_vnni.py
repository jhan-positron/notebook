"""Base diagrams B1-B5 of the PR 4424 page for h/tron/tensor/k_vnni.hpp.

Every fact drawn here comes from facts/k_vnni.json (verified claims) or from
the head file itself. Line numbers are head line numbers of
h/tron/tensor/k_vnni.hpp unless another file is named.

Module-level constants and building blocks (imported by the change diagrams):
  EX, PAGE_7, SLOT_5, KV_HEAD_0, BLOCK_2, ROWS_SAVED_0_40, BLOCK2_ROWS_SAVED,
  index_of, row_major_elem_of, rm_forms, token_rows, panel_grid, panel_lines,
  pair_row_dwords, block_panels, lane_block, callers_box, band_header,
  b4_legend, B5_COLUMNS
"""
import sys

from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, label_box,
                         lane, line, lines, marker_defs, rect, text, text_width)

# ---------------------------------------------------------------------------
# The worked example of the page (STYLE.md): page 7, storage slot 5, KV head 0,
# rows of offsets 0..40 saved; token 37 = block 2, t = 5; dimension 70 = step
# 2, pair 3, j = 0.
PAGE_7, SLOT_5, KV_HEAD_0, BLOCK_2 = 7, 5, 0, 2
ROWS_SAVED_0_40 = list(range(0, 41))            # page offsets whose K row is saved
BLOCK2_ROWS_SAVED = [o for o in ROWS_SAVED_0_40 if o // 16 == BLOCK_2]  # 32..40


def index_of(token, dim):
    """k_vnni::index (k_vnni.hpp:134-141) and its five coordinates."""
    s, c = dim // 32, token // 16
    dp, t, j = (dim % 32) // 2, token % 16, dim % 2
    return dict(s=s, c=c, dp=dp, t=t, j=j,
                index=(((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j,
                panel=s * 4 + c)


def row_major_elem_of(token, cols=128):
    """row_major_row (k_vnni.hpp:467-471): element offset of the token's
    row-major row, and the panel / row it lies in."""
    c, t = token // 16, token % 16
    return dict(panel=(t // 4) * 4 + c, row=t % 4,
                elem=((t // 4) * 4 + c) * 512 + (t % 4) * cols)


EX = dict(token=37, dim=70)
EX.update(index_of(EX["token"], EX["dim"]))          # s=2 c=2 dp=3 t=5 j=0, index 5226
EX["byte"] = EX["index"] * 2                           # 10452
EX["rm"] = row_major_elem_of(EX["token"])             # panel 6, row 1, elem 3200
EX["rm_dim_elem"] = EX["rm"]["elem"] + EX["dim"]       # 3270
assert EX["index"] == 5226 and EX["panel"] == 10 and EX["rm"]["elem"] == 3200


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Building blocks


def panel_grid(x, y, cw, ch, hi=None, block=None, gap=4):
    """The plane as its 16 panels (s rows x c columns), panel index 4 s + c.
    hi = (s, c) is drawn in the VNNI colour; column `block` gets a solid ink
    frame (the frame marks the worked example's block, not a layout state).
    Row labels sit at the right, column labels on top."""
    o = []
    for c in range(4):
        o.append(text(x + c * (cw + gap) + cw / 2, y - 6, f"c = {c}", 9.5, "middle",
                      fill=C["muted"]))
    for s in range(4):
        o.append(text(x + 4 * cw + 3 * gap + 6, y + s * (ch + gap) + ch / 2 + 4,
                      f"s = {s}", 9.5, fill=C["muted"]))
        for c in range(4):
            px, py = x + c * (cw + gap), y + s * (ch + gap)
            on = hi == (s, c)
            o.append(rect(px, py, cw, ch, C["vnni_fill"] if on else "#fff",
                          C["vnni"] if on else C["line"], 1.4 if on else 1, 3))
            o.append(text(px + cw / 2, py + ch / 2 - 1, f"({s},{c})", 9.5, "middle",
                          True))
            o.append(text(px + cw / 2, py + ch / 2 + 11, f"#{4 * s + c}", 9,
                          "middle", True, fill=C["muted"]))
    if block is not None:
        bx = x + block * (cw + gap) - 3
        o.append(rect(bx, y - 3, cw + 6, 4 * ch + 3 * gap + 6, "none", C["ink"], 1.4, 4))
    return "".join(o)


def panel_lines(x, y, w, h, forms, hi_rows=(), col=None, col_read=False,
                read_all=False):
    """One panel as its 16 lines of 64 bytes, top line = pair row 0 (VNNI form)
    or token row 0 (row-major form: 4 lines per token row).
    forms: 16 states, one per line: 'vnni' | 'rm' | 'empty' | 'pend'.
    hi_rows: line indexes drawn with a thick outline.
    col: a dword index 0..15 whose 4-byte slot is marked in every line (a
    token's column); col_read: mark it as a read (dashed) instead of a write.
    read_all: dashed outline round the whole panel = the 1 KiB is read."""
    lh = h / 16
    o = []
    for i, f in enumerate(forms):
        ly = y + i * lh
        if f == "vnni":
            o.append(rect(x, ly, w, lh, C["vnni_fill"], C["vnni"], 0.5, 0))
        elif f == "rm":
            o.append(rect(x, ly, w, lh, C["rm_fill"], C["rm"], 0.5, 0))
        elif f == "pend":
            o.append(rect(x, ly, w, lh, C["pend_fill"], C["pend"], 0.5, 0))
        else:
            o.append(rect(x, ly, w, lh, C["empty_fill"], C["empty"], 0.5, 0, "2 2"))
    for i in hi_rows:
        o.append(rect(x, y + i * lh, w, lh, "none", C["ink"], 1.6, 0))
    if col is not None:
        cx = x + col * (w / 16)
        if col_read:
            o.append(rect(cx, y, w / 16, h, "none", C["ink"], 1.2, 0, "2 2"))
        else:
            o.append(rect(cx, y, w / 16, h, C["vnni"], C["ink"], 1.0, 0))
    if read_all:
        o.append(rect(x - 2, y - 2, w + 4, h + 4, "none", C["ink"], 1.2, 2, "4 3"))
    o.append(rect(x, y, w, h, "none", C["ink"], 0.8, 0))
    return "".join(o)


def pair_row_dwords(x, y, w, h, hi_t=None, base_token=32):
    """One pair row (64 bytes) as 16 dwords, one per token of the block; each
    dword = 2 bf16 (j = 0 low half, j = 1 high half)."""
    dw = w / 16
    o = []
    for t in range(16):
        on = t == hi_t
        o.append(rect(x + t * dw, y, dw, h, C["vnni_fill"] if on else "#fff",
                      C["vnni"] if on else C["line"], 1.4 if on else 0.8, 0))
        o.append(line(x + t * dw + dw / 2, y + 2, x + t * dw + dw / 2, y + h - 2,
                      C["line"], 0.6, "2 2"))
        o.append(text(x + t * dw + dw / 2, y + h + 10, str(base_token + t), 8.5,
                      "middle", True, fill=C["muted"]))
    return "".join(o)


def rm_forms(saved_tokens, c=BLOCK_2):
    """Row-major forms of the 4 panels of block c: token t of the block owns
    lines 4 (t % 4) .. 4 (t % 4) + 3 of panel (t / 4, c) (k_vnni.hpp:441-445)."""
    forms = [["empty"] * 16 for _ in range(4)]
    for tok in saved_tokens:
        t = tok % 16
        for k in range(4):
            forms[t // 4][4 * (t % 4) + k] = "rm"
    return forms


def token_rows(tok):
    """(panel step s, the 4 line indexes) of a token's row-major row."""
    t = tok % 16
    return t // 4, [4 * (t % 4) + k for k in range(4)]


def block_panels(x, y, c, forms4, pw=118, ph=80, gap=14, **kw):
    """The 4 panels (s, c), s = 0..3, of token block c = the block's 4 KiB,
    with a 'panel (s,c) #n' label above each. forms4: four 16-entry form
    lists (see panel_lines). kw go to panel_lines (hi_rows, col, col_read,
    read_all apply to every panel)."""
    o = []
    for s in range(4):
        px = x + s * (pw + gap)
        o.append(text(px + pw / 2, y - 5, f"panel ({s},{c}) #{4 * s + c}", 9, "middle",
                      True, fill=C["muted"]))
        o.append(panel_lines(px, y, pw, ph, forms4[s], **kw))
    return "".join(o)


def lane_block(x, y, w, h, lines_, fill, stroke, ref, idle=False, size=9.5,
               lh=10, cite_size=8.5):
    """A work block of a lane: text lines and a citation. Solid = real work,
    dashed white = waiting."""
    if idle:
        o = [rect(x, y, w, h, "#fff", stroke, 1, 2, "4 3")]
    else:
        o = [rect(x, y, w, h, fill, stroke, 1.2, 2)]
    for s in lines_:
        _w(s, size, w - 8, where=f"lane_block {ref}")
    _w(ref, cite_size, w - 4, True, f"lane_block cite {ref}")
    o.append(lines(x + 4, y + 11, lines_, size, lh))
    o.append(cite(x + w - 3, y + h - 3, ref, size=cite_size))
    return "".join(o)


def callers_box(x, y, w, h, lines_, ref):
    """The callers of a group of operations, in other files (file: name line).
    Up to 7 lines of 9 px at 10 px pitch clear the citation of an 84 px box."""
    o = [rect(x, y, w, h, C["soft"], C["line"], 1, 4)]
    for s in lines_:
        _w(s, 9, w - 12, where=f"callers_box {ref}")
    o.append(lines(x + 6, y + 11, lines_, 9, 10))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def band_header(x, y, s, w=740):
    _w(s, 11, w, where="band_header")
    return text(x, y, s, 11, weight=700)


def _vcard(o, fid, name, color, x, y0, y1, label, ref):
    """A vertical how-many arrow with its label above the middle and the
    citation below it, both to the right of the line."""
    mid = (y0 + y1) / 2
    o.append(arrow(fid, name, [(x, y0), (x, y1)], color, 1.4))
    o.append(text(x + 8, mid - 3, label, 9.5, fill=color, weight=600))
    o.append(text(x + 8, mid + 10, f"[{ref}]", 8.5, mono=True, fill=C["cite"]))


# ---------------------------------------------------------------------------
# B1: data model of one plane


def _band_box(o, boxes, x, y, w, h, title, sub, fill, stroke, ref, reg=None, size=11):
    """A box of B1's containment band: label_box + register entry + width check."""
    _w(title, size, w - 8, True, f"b1 band {title}")
    for s in sub:
        _w(s, size - 1, w - 8, where=f"b1 band {title}")
    o.append(label_box(x, y, w, h, title, sub, fill, stroke, size, ref=ref))
    boxes.append((title, reg or ref))


def b1():
    fid = "k_vnni-b1"
    W, H = 1000, 800
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"],
                           "muted": C["muted"]})]
    # ---- top band: the containment, book -> page -> kv_block -> k, v, and the
    # page's state entries (facts k_vnni-data-1, -2, -3, -28, -30, -33, -34, -35)
    by0, bh0 = 36, 48
    my = by0 + bh0 / 2
    _band_box(o, boxes, 20, by0, 110, bh0, "book", ["the KV cache"],
              C["soft"], C["ink"], "kv_cache.hpp:934-943", "kv_cache.hpp:934-943, 1511")
    _band_box(o, boxes, 232, by0, 150, bh0, "page", ["64-token page (changed)"],
              C["soft"], C["ink"], "kv_cache.hpp:2484-2488")
    _band_box(o, boxes, 500, by0, 180, bh0, "detail::kv_block",
              ["one KV head of one KV slot"], C["soft"], C["ink"], "kv_cache.hpp:2982-3015")
    _band_box(o, boxes, 720, by0, 260, bh0, "k_rows_saved_ / k_vnni_blocks_ entry",
              ["one entry per storage slot (new)"], C["soft"], C["ink"],
              "kv_cache.hpp:2616-2622")
    # book -> page
    o.append(arrow(fid, "ink", [(130, my), (228, my)], C["ink"], 1.4))
    o.append(lines(181, my - 18, ["1 book ->", "n_pages pages"], 9, 10, "middle",
                   fill=C["ink"], weight=600))
    o.append(text(181, my + 13, "[kv_cache.hpp:1686]", 8.5, "middle", True, fill=C["cite"]))
    # page -> kv_block
    o.append(arrow(fid, "ink", [(382, my), (496, my)], C["ink"], 1.4))
    o.append(lines(439, my - 26, ["1 page ->", "n_kv_heads kv_blocks", "per storage slot"],
                   8.5, 10, "middle", fill=C["ink"], weight=600))
    o.append(text(439, my + 13, "[kv_cache.hpp:2634]", 8.5, "middle", True, fill=C["cite"]))
    # page -> the state entries: the arc runs over the band, clear of kv_block
    o.append(arrow(fid, "ink", [(300, by0), (300, 22), (850, 22), (850, by0)], C["ink"], 1.4))
    o.append(text(575, 15, "1 page -> layout_t::n_slots + EAGLE_STORAGE_SLOTS_1 entries of "
                  "each state word", 9, "middle", fill=C["ink"], weight=600))
    o.append(text(856, 32, "[kv_cache.hpp:2616-2622]", 8.5, mono=True, fill=C["cite"]))
    # kv_block -> k (the left column below) + v
    o.append(arrow(fid, "ink", [(660, by0 + bh0), (660, 101), (180, 101), (180, 114)],
                   C["ink"], 1.4))
    o.append(text(190, 95, "1 kv_block -> 1 K plane (k) + 1 V plane (v)", 9, fill=C["ink"],
                  weight=600))
    o.append(text(440, 95, "[kv_cache.hpp:3002-3015]", 8.5, mono=True, fill=C["cite"]))
    # the state entries -> their bits
    o.append(arrow(fid, "ink", [(760, by0 + bh0), (760, 116)], C["ink"], 1.4))
    o.append(lines(768, 93, ["1 entry -> PAGE_TOKENS_64 row bits",
                             "or TOKEN_BLOCKS_4 block bits"], 9, 10, fill=C["ink"],
                   weight=600))
    o.append(text(768, 113, "[kv_cache.hpp:2509; k_vnni.hpp:112-113]", 8.5, mono=True,
                  fill=C["cite"]))
    _band_box(o, boxes, 720, 118, 260, 48, "page offset / token block c",
              ["one bit each: offset_bit, block_bit"], "#fff", C["ink"],
              "k_vnni.hpp:97-105; kv_cache.hpp:2509")
    # ---- left column: containment with how-many ---------------------------
    lx, lw, bh, step = 20, 316, 60, 86
    col = [
        ("detail::kv_block::k", ["k_storage = k_vnni_tensor<64, 128> (VNNI slot)",
                                 "or bf16[64 * 128] (row-major slot); changed"],
         C["soft"], C["ink"], "kv_cache.hpp:2986-3001",
         ("ink", "1 k -> 1 owner k_vnni_tensor (a VNNI slot)", "kv_cache.hpp:2993-2995")),
        ("k_vnni_tensor<64, 128>", ["alignas(64) bf16 data_[Rows * Cols]: the owner (new)",
                                    "trivial, no allocation, no initialization"],
         C["vnni_fill"], C["vnni"], "k_vnni.hpp:201-236",
         ("vnni", "1 owner -> Rows * Cols = 8192 bf16 = 16 KiB", "k_vnni.hpp:230-236")),
        ("plane", ["K for one KV head of one page (new)",
                   "64 tokens x 128 dimensions of bf16 = 16 KiB"],
         C["vnni_fill"], C["vnni"], "k_vnni.hpp:20-28",
         ("ink", "1 plane -> TOKEN_BLOCKS_4 = PAGE_TOKENS_64 / BLOCK_TOKENS_16 = 4 token blocks",
          "k_vnni.hpp:69")),
        ("token block c", ["16 tokens: page offsets 16 c .. 16 c + 15 (new)",
                           "owns panel (s, c), s = 0..3: 4 KiB of its own"],
         "#fff", C["ink"], "k_vnni.hpp:30-32, 443-445",
         ("ink", "1 block -> BLOCK_TOKENS_16 = 16 tokens", "k_vnni.hpp:68-69")),
        ("token i", ["column (i % 16) in each of block (i / 16)'s 4 panels",
                     "-> DIM_STEPS_4 x STEP_PAIRS_16 = 64 dword slots"],
         "#fff", C["ink"], "k_vnni.hpp:30-32, 344-348",
         ("ink", "1 token -> DIM_STEPS_4 = 4 steps", "k_vnni.hpp:70-74")),
        ("dimension step s, pair dp", ["1 step = STEP_PAIRS_16 pairs (AMX tile depth)",
                                       "1 pair = PAIR_2 bf16 (dims 2 dp, 2 dp + 1), 1 dword"],
         "#fff", C["ink"], "k_vnni.hpp:63-74", None),
    ]
    y = 116
    for title, sub, fill, stroke, ref, arr in col:
        for s in sub:
            _w(s, 11, lw - 8, where=f"b1 {title}")
        o.append(label_box(lx, y, lw, bh, title, sub, fill, stroke, ref=ref))
        boxes.append((title, ref))
        if arr:
            _vcard(o, fid, arr[0], C[arr[0]], lx + 60, y + bh, y + step, arr[1], arr[2])
        y += step
    plane_mid = 116 + 2 * step + bh / 2            # 318
    block_mid = 116 + 3 * step + bh / 2            # 404
    # ---- middle column: the panel grid --------------------------------------
    gx, gy, cw, ch = 440, 140, 56, 44
    o.append(text(gx + 118, 116, "the plane: 16 panels (s, c), panel index 4 s + c", 11,
                  "middle", weight=700))
    o.append(panel_grid(gx, gy, cw, ch, hi=(EX["s"], EX["c"]), block=BLOCK_2))
    # the row-major position of token 37 (panel (1,2) #6): a thin orange frame
    rm_p = EX["rm"]["panel"]
    o.append(rect(gx + EX["c"] * (cw + 4), gy + (rm_p // 4) * (ch + 4), cw, ch, "none",
                  C["rm"], 1.6, 3))
    # plane -> the 16 panels: the how-many label sits in the gap, above the arrow
    o.append(arrow(fid, "vnni", [(lx + lw, plane_mid), (gx - 4, plane_mid)], C["vnni"], 1.4))
    gap_mid = (lx + lw + gx - 4) / 2
    o.append(lines(gap_mid, plane_mid - 64, ["1 plane ->", "N_PANELS_16 =", "DIM_STEPS_4 x",
                                             "TOKEN_BLOCKS_4", "= 16 panels"], 8.5, 10,
                   "middle", fill=C["vnni"], weight=600))
    o.append(text(gap_mid, plane_mid - 8, "[k_vnni.hpp:82]", 8.5, "middle", True,
                  fill=C["cite"]))
    bx = gx + BLOCK_2 * (cw + 4) + cw / 2
    o.append(arrow(fid, "ink", [(lx + lw, block_mid), (bx, block_mid),
                                (bx, gy + 4 * ch + 3 * 4 + 6)], C["ink"], 1.6))
    o.append(lines(bx + 8, 352, ["block 2 ->", "DIM_STEPS_4 = 4", "panels (s, 2): 4 KiB"],
                   9, 12, fill=C["ink"], weight=600))
    o.append(text(bx + 8, 390, "[k_vnni.hpp:443-445]", 8.5, mono=True, fill=C["cite"]))
    mem = ["memory order: panel index 4 s + c,",
           "byte offset 1024 x (4 s + c).",
           "block 2 (framed) owns panels #2, #6, #10, #14:",
           "four 1 KiB pieces 4 KiB apart.",
           "panel (2,2) #10 (blue) holds token 37, dim 70.",
           f"orange frame: panel (1,2) #{rm_p}, token 37's row-major row"]
    for s in mem:
        _w(s, 9.5, 290, where="b1 memory order")
    o.append(lines(gx - 20, 460, mem, 9.5, 12, fill=C["ink"]))
    # the pair row zoomed (middle column, bottom)
    o.append(text(gx - 20, 548, "pair row 3 of panel #10: 16 dwords, t = token % 16",
                  9.5, weight=600))
    o.append(pair_row_dwords(gx - 20, 556, 256, 26, hi_t=EX["t"], base_token=32))
    o.append(lines(gx - 20, 608, ["token 37 = dword 5: low half j = 0 is dim 70,",
                                  "high half j = 1 is dim 71"], 9, 12, fill=C["ink"]))
    o.append(text(gx - 20, 633, "[k_vnni.hpp:63-65, 87-90]", 8.5, mono=True, fill=C["cite"]))
    # ---- right column: one panel zoomed, panel and pair row boxes ------------
    rx, ry = 740, 212
    o.append(text(rx + 100, 188, "panel (2,2) #10: 16 pair rows x 64 B", 11, "middle",
                  weight=700))
    o.append(panel_lines(rx, ry, 200, 160, ["vnni"] * 16, hi_rows=[EX["dp"]]))
    for dp in range(16):
        o.append(text(rx - 4, ry + dp * 10 + 8, f"dp {dp}", 8.5, "end", True,
                      fill=C["vnni"] if dp == EX["dp"] else C["muted"]))
    o.append(text(rx, 388, "thick row dp 3 = dims 70, 71 of tokens 32..47", 9, fill=C["ink"]))
    o.append(text(rx, 400, "64 B apart: pair_row_offsets [k_vnni.hpp:302-310]", 9,
                  fill=C["muted"]))
    _band_box(o, boxes, rx - 10, 412, 250, 52, "panel (s, c) (new)",
              ["16 pair rows x 64 B = 1 KiB: one AMX B tile"], "#fff", C["vnni"],
              "k_vnni.hpp:29-30, 78-82", size=11)
    o.append(arrow(fid, "vnni", [(rx + 30, 464), (rx + 30, 498)], C["vnni"], 1.4))
    o.append(lines(rx + 38, 474, ["1 panel -> STEP_PAIRS_16", "= 16 pair rows"], 9, 10,
                   fill=C["vnni"], weight=600))
    o.append(text(rx + 38, 495, "[k_vnni.hpp:78-80]", 8.5, mono=True, fill=C["cite"]))
    _band_box(o, boxes, rx - 10, 500, 250, 52, "pair row dp (new)",
              ["64 B line: one dimension pair of 16 tokens"], "#fff", C["vnni"],
              "k_vnni.hpp:66-67, 75-77", size=11)
    # the labels sit right of the stem and below the horizontal segment, which
    # runs left from x = rx to the pair row of the middle column
    o.append(arrow(fid, "vnni", [(rx, 552), (rx, 569), (gx - 20 + 256 + 6, 569)],
                   C["vnni"], 1.4))
    o.append(lines(rx + 8, 584, ["1 pair row -> BLOCK_TOKENS_16", "= 16 dwords, 1 per token"],
                   9.5, 12, fill=C["vnni"], weight=600))
    o.append(text(rx + 8, 609, "[k_vnni.hpp:66-68]", 8.5, mono=True, fill=C["cite"]))
    # ---- bottom: the index map and the worked example -----------------------
    by = 648
    o.append(line(20, by - 8, 980, by - 8, C["line"]))
    o.append(rect(20, by, 960, 144, "#fff", C["ink"], 1.2, 5))
    o.append(text(30, by + 17, "k_vnni::index(token, dim)", 12, mono=True, weight=700))
    o.append(text(230, by + 17, "element index of K[token][dim] inside the plane (new)",
                  10.5, fill=C["muted"]))
    o.append(cite(976, by + 140, "k_vnni.hpp:132-141"))
    boxes.append(("k_vnni::index(token, dim)", "k_vnni.hpp:132-141"))
    o.append(lines(30, by + 34, [
        "s = dim / STEP_DIMS_32 ; c = token / BLOCK_TOKENS_16 ; dp = (dim % STEP_DIMS_32) / PAIR_2 ; t = token % BLOCK_TOKENS_16 ; j = dim % PAIR_2",
        "index = (((s * TOKEN_BLOCKS_4 + c) * STEP_PAIRS_16 + dp) * BLOCK_TOKENS_16 + t) * PAIR_2 + j",
    ], 10, 13, mono=True))
    o.append(text(30, by + 66, "worked example, token 37 and dimension 70 (VNNI form):", 10.5,
                  weight=600, fill=C["vnni"]))
    o.append(lines(30, by + 80, [
        f"s = 70 / 32 = {EX['s']} ; c = 37 / 16 = {EX['c']} ; dp = (70 % 32) / 2 = {EX['dp']} ; "
        f"t = 37 % 16 = {EX['t']} ; j = 70 % 2 = {EX['j']}",
        f"index = (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2 + 0 = {EX['index']}   ->   byte "
        f"{EX['byte']} = panel #{EX['panel']} x 1024 + pair row {EX['dp']} x 64 + dword "
        f"{EX['t']} x 4 + j x 2",
    ], 10, 13, mono=True))
    o.append(text(30, by + 112, "the same token in the row-major form of block 2 "
                  "(Note [Row-major tail block], k_vnni.hpp:437-456; row_major_row 462-472):",
                  10.5, weight=600, fill=C["rm"]))
    o.append(lines(30, by + 126, [
        f"row_major_row(plane, 37): panel (t / 4, c) = (1, 2) = #{EX['rm']['panel']}, row "
        f"t % 4 = {EX['rm']['row']}   ->   element {EX['rm']['elem']} = 6 x 512 + 1 x 128; "
        f"dim 70 at element {EX['rm_dim_elem']}, 256 B per token row",
    ], 10, 13, mono=True))
    cap = ("B1, data model. The top band is the containment. A book holds n_pages pages. "
           "A page reaches n_kv_heads kv_blocks per storage slot, and keeps "
           "layout_t::n_slots + EAGLE_STORAGE_SLOTS_1 entries of its two state words "
           "k_rows_saved_ (one bit per page offset) and k_vnni_blocks_ (one bit per "
           "token block). A kv_block holds one K plane (k) and one V plane (v). "
           "A plane is K (the key matrix) for one KV head (key/value head) "
           "of one page (64 tokens of KV storage): 64 "
           "tokens x 128 dimensions of bf16 (16-bit floats) = 16 KiB, owned by "
           "k_vnni_tensor. It is 16 panels of 1 KiB, one per (dimension step s, token "
           "block c). A panel is 16 pair rows of 64 bytes, and a pair row holds one "
           "dimension pair for 16 tokens. The worked example traces token 37, dimension "
           "70 through k_vnni::index to element 5226 (panel #10, pair row 3, dword 5). "
           "The orange frame on panel (1,2) #6 and the last line show where the same "
           "token lies while block 2 is still row-major.")
    # the colour and font scheme of this figure (only the styles it uses)
    legend = [
        ("ctx_ink", "grey box, ink outline: the kv_cache.hpp containers book, page, "
                    "detail::kv_block, its member k, and the k_rows_saved_ / k_vnni_blocks_ "
                    "entry"),
        ("vnni", "blue: the VNNI entities that own bytes: k_vnni_tensor<64, 128>, the "
                 "plane, panel (2,2) #10 in the grid, the 16 pair rows of the zoomed panel, "
                 "and dword 5 (token 37) of pair row 3; blue text = the VNNI how-many "
                 "labels and the worked example in VNNI form"),
        ("white box, blue outline: the VNNI entities panel (s, c) and pair row dp",
         "#fff", C["vnni"], False, False),
        ("box", "white box, ink outline: the data-model entities page offset / token "
                "block c (the bits), token block c, token i, dimension step s / pair dp, "
                "and the index map k_vnni::index; name in bold monospace, description in "
                "grey sans-serif"),
        ("lane", "white cell, thin grey outline: a panel of the grid other than (2,2) #10 "
                 "(the frames of block 2 and of panel (1,2) #6 are drawn over such cells), "
                 "and a dword of pair row 3 other than token 37's"),
        ("ink frame: block 2's column in the panel grid, pair row dp 3 of the zoomed "
         "panel (drawn heavier), and that panel's outline", "none", C["ink"], False, False),
        ("orange frame: panel (1,2) #6, where token 37's row lies while block 2 is "
         "row-major; orange text = the same token in row-major form", "none", C["rm"],
         False, False),
        ("arrow", "ink arrow: a containment with its how-many (book -> pages, page -> "
                  "kv_blocks and state entries, kv_block -> planes, entry -> bits, "
                  "k -> owner, plane -> blocks, block -> tokens, token -> steps, "
                  "block 2 -> its 4 panels)"),
        ("blue arrow: a how-many inside the VNNI layout (owner -> 8192 bf16, plane -> "
         "16 panels, panel -> 16 pair rows, pair row -> 16 dwords)", "arrow", C["vnni"]),
        ("font_mono", "monospace = a name or a value from the code: box titles, panel "
                      "indexes, dp rows, token numbers, the index formula and the worked "
                      "example"),
        ("font_sans", "sans-serif = the three drawing titles (bold), the descriptions "
                      "under a box title, the how-many labels, the memory-order note, and "
                      "the notes under the zoomed panel and under the pair row"),
        ("font_cite", "small grey monospace = the lines that define a box or an arrow "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Data model: one K plane, its panels, pair rows and the index map",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B2: type model


def b2():
    fid = "k_vnni-b2"
    W, H = 1000, 700
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"],
                           "new": C["new"]})]
    # kv_block::k and page::k_packed (callers in kv_cache.hpp)
    # title + 3 sub-lines + citation need 80 px (label_box: sub-lines 14 px
    # apart from y + 30, citation at y + h - 4)
    o.append(label_box(20, 24, 250, 80, "detail::kv_block::k", [
        "the owner for a VNNI slot (changed):",
        "k_storage = k_vnni_tensor<64, 128>",
        "copied whole by dst_block.k = src_block.k"],
        C["soft"], C["ink"], ref="kv_cache.hpp:2986-3001"))
    boxes.append(("detail::kv_block::k", "kv_cache.hpp:2986-3001"))
    o.append(arrow(fid, "ink", [(270, 60), (326, 60)], C["ink"], 1.4))
    o.append(lines(298, 42, ["1 kv_block", "-> 1 K plane"], 8.5, 10, "middle", fill=C["ink"],
                   weight=600))
    # the owner
    ox, oy, ow, oh = 330, 24, 320, 96
    o.append(label_box(ox, oy, ow, oh, "k_vnni_tensor<Rows, Cols>", [
        "alignas(64) bf16 data_[Rows * Cols] = 16 KiB (new)",
        "trivial to construct, copy and destroy; no init",
        "as_view() & -> writable view, TRON(this_lifetimebound)",
        "as_view() const& -> read-only view;  && = delete"],
        C["vnni_fill"], C["vnni"], ref="k_vnni.hpp:201-236"))
    boxes.append(("k_vnni_tensor<Rows, Cols>", "k_vnni.hpp:201-236"))
    o.append(label_box(700, 24, 280, 80, "page::k_packed(slot, kv_head)", [
        "kv_block.k.as_view() on a const owner (new)",
        "-> k_vnni_view<const bf16, 64, 128>",
        "handed to qk_vnni_128x4 and qk_group"],
        C["soft"], C["ink"], ref="kv_cache.hpp:2116-2124"))
    boxes.append(("page::k_packed(slot, kv_head)", "kv_cache.hpp:2116-2124"))
    # views; the how-many of as_view is what the code says: one view per call,
    # and the owner outlives every view (k_vnni.hpp:171-172)
    vy, vh = 190, 104
    o.append(arrow(fid, "vnni", [(ox + 80, oy + oh), (ox + 80, vy)], C["vnni"], 1.4))
    o.append(lines(ox + 88, 148, ["as_view() &: 1 call -> 1 view;",
                                  "the owner outlives every view"], 9, 11,
                   fill=C["vnni"], weight=600))
    o.append(text(ox + 88, 170, "[k_vnni.hpp:171-172, 214-218]", 8.5, mono=True,
                  fill=C["cite"]))
    o.append(arrow(fid, "vnni", [(ox + ow - 20, oy + oh), (ox + ow - 20, 174), (760, 174),
                                 (760, vy)], C["vnni"], 1.4))
    o.append(lines(ox + ow - 12, 140, ["as_view() const&: 1 call ->", "1 read-only view"],
                   9, 11, fill=C["vnni"], weight=600))
    o.append(text(ox + ow - 12, 164, "[k_vnni.hpp:171-172, 220-224]", 8.5, mono=True,
                  fill=C["cite"]))
    o.append(arrow(fid, "ink", [(840, 104), (840, vy)], C["ink"], 1.4))
    o.append(lines(848, 130, ["1 (slot, kv_head) ->", "1 read-only view"], 9, 11,
                   fill=C["ink"], weight=600))
    # rows enter through the operations the comment names (157-158, 179-180)
    # and through store_row_major (481), which writes the writable row view
    # that row_major_row returns
    o.append(label_box(ox, vy, 296, vh, "k_vnni_view<bf16, 64, 128>", [
        "the writable view (new): T* data_ (private)",
        "at(token, dim) reads; there is no element write",
        "no public pointer ctor, data(), operator[] or",
        "pointer conversion; rows enter through store_row,",
        "store_block, copy_token, store_row_major (K8)"],
        C["vnni_fill"], C["vnni"], 11.5, ref="k_vnni.hpp:156-199; 481"))
    boxes.append(("k_vnni_view<bf16, 64, 128>", "k_vnni.hpp:156-199; store_row_major 481"))
    o.append(label_box(700, vy, 280, vh, "k_vnni_view<const bf16, 64, 128>", [
        "the read-only view (new): the same reads",
        "built from a writable view by the converting",
        "constructor; requires(is_const_v<T>): the",
        "reverse direction does not exist",
        "(used at 502 and 516 for the read side)"],
        C["vnni_fill"], C["vnni"], 11.5, ref="k_vnni.hpp:163-199; 171-177"))
    boxes.append(("k_vnni_view<const bf16, 64, 128>",
                  "k_vnni.hpp:163-199 (T = const bf16); converting constructor 171-177"))
    o.append(arrow(fid, "vnni", [(ox + 300, 236), (696, 236)], C["vnni"], 1.4))
    o.append(lines(663, 208, ["1 writable ->", "1 read-only", "copies data_"], 8.5, 10,
                   "middle", fill=C["vnni"], weight=600))
    # a route the code does not provide: grey (C['gone'] is for removed code)
    o.append(lines(663, 252, ["never the", "reverse"], 8.5, 10, "middle", fill=C["muted"],
                   weight=600))
    # the three friend declarations and the concept, at the left ("friend
    # struct" is the code's phrase, k_vnni.hpp:189-192)
    o.append(label_box(20, vy, 290, vh, "friend struct (of k_vnni_view)", [
        "k_vnni_tensor<Rows, Cols>: calls the private",
        "pointer constructor (as_view, 217 and 223)",
        "detail::k_vnni_access: reads data_ (244)",
        "k_vnni_view<U, R, C>: the converting ctor (177)",
        "so no bare pointer becomes a view outside"],
        "#fff", C["ink"], ref="k_vnni.hpp:189-192"))
    boxes.append(("friend struct (of k_vnni_view)", "k_vnni.hpp:189-192"))
    o.append(arrow(fid, "muted", [(310, vy + 30), (ox - 4, vy + 30)], C["muted"], 1.2,
                   "4 3"))
    o.append(label_box(20, 316, 290, 60, "concept k_vnni_element<T>", [
        "T is bf16 or const bf16, nothing else;",
        "checked by the static_assert at 165"],
        "#fff", C["ink"], ref="k_vnni.hpp:153-154"))
    boxes.append(("concept k_vnni_element<T>", "k_vnni.hpp:153-154"))
    # the last segment enters the view box's left edge horizontally
    o.append(arrow(fid, "muted", [(310, 340), (320, 340), (320, vy + vh - 20),
                                  (ox - 4, vy + vh - 20)], C["muted"], 1.2, "4 3"))
    # the one access route
    ay, ah = 340, 58
    o.append(arrow(fid, "ink", [(ox + 160, vy + vh), (ox + 160, ay)], C["ink"], 1.4))
    o.append(text(ox + 168, 320, "1 view -> 1 T* (the plane's first element)", 9,
                  fill=C["ink"], weight=600))
    # the read-only view's route: the same how-many as the writable view's
    o.append(card_arrow(fid, "ink", [(840, vy + vh), (840, ay + ah / 2), (ox + 404, ay + ah / 2)],
                        C["ink"], "1 view -> 1 T*", label_dx=8, label_dy=-2, size=9,
                        anchor="start"))
    o.append(text(848, ay - 2, "[k_vnni.hpp:239-246]", 8.5, mono=True, fill=C["cite"]))
    o.append(label_box(ox + 40, ay, 360, ah, "detail::k_vnni_access::plane(view) -> T*", [
        "the one route from a packed K view to its address (new)",
        "panel (step 0, block 0), pair row 0, token 0"],
        "#fff", C["ink"], ref="k_vnni.hpp:238-247"))
    boxes.append(("detail::k_vnni_access::plane(view)", "k_vnni.hpp:238-247"))
    # consumers of the raw pointer: one stem from the access route to a bus
    # over the four caller boxes, a short arrow into each
    cy = 436
    bus_y = cy - 10
    o.append(line(ox + 220, ay + ah, ox + 220, bus_y, C["ink"], 1.4))
    o.append(text(ox + 228, ay + ah + 14, "who may take the address: the four callers below "
                  "[k_vnni.hpp:34-41, 146-149]", 9, fill=C["muted"]))
    cons = [
        ("the typed operations in this header", ["store_row 354, load_row 372,",
                                                 "store_block 400, row_major_row 468"],
         "k_vnni.hpp:34, 344-472"),
        ("k_vnni::qk_group", ["the AVX-512 score reader", "(kernels/k_vnni.hpp:85)"],
         "kernels/k_vnni.hpp:61, 85"),
        ("amx_attn_h128g4::qk_vnni_128x4", ["the AMX dense-page kernel",
                                            "(amx_attn.cpp:244)"], "amx_attn.cpp:237, 244"),
        ("book::fill_storage_slot", ["test-only fill_random body:",
                                     "the documented exception"],
         "kv_cache.hpp:1830, 1835-1836"),
    ]
    cx = 20
    centres = [cx + i * 242 + 116 for i in range(len(cons))]
    o.append(line(centres[0], bus_y, centres[-1], bus_y, C["ink"], 1.4))
    for c in centres:
        o.append(arrow(fid, "ink", [(c, bus_y), (c, cy - 1)], C["ink"], 1.4))
    for name, sub, ref in cons:
        o.append(label_box(cx, cy, 232, 62, name, sub, C["soft"], C["ink"], 10.5, ref=ref))
        boxes.append((name, ref))
        cx += 242
    # transfer rows
    ty = 536
    o.append(line(20, ty - 12, 980, ty - 12, C["line"]))
    o.append(text(20, ty, "transfer rows: one token's Cols bf16 in dimension order, "
                  "not packed storage (new)", 11, weight=700))
    o.append(label_box(20, ty + 10, 310, 90, "const_k_row_view<Cols, Aligned, Dma>", [
        "const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "built by k_source_row(const bf16*) or",
        "k_source_row(stride-1 bf16 view): keeps its flags",
        "the source of store_row, store_row_major, set_k_row"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:254-255, 262-277"))
    boxes.append(("const_k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:254-255, 262-277"))
    o.append(label_box(345, ty + 10, 310, 90, "k_row_view<Cols, Aligned, Dma>", [
        "view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "built by k_destination_row(bf16*)",
        "the destination of load_row, load_row_major,",
        "get_k_row; returned by row_major_row (writable)"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:257-258, 279-283"))
    boxes.append(("k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:257-258, 279-283"))
    o.append(label_box(670, ty + 10, 310, 90, "Aligned, Dma flags", [
        "defaults VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE",
        "(kv_cache_fwd.hpp:25-26); the helpers neither",
        "check alignment nor copy; the row ops use unaligned",
        "loads and stores, so no VIEW_ALIGNED_TRUE needed"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:249-253, 260-261"))
    boxes.append(("Aligned, Dma flags", "k_vnni.hpp:249-253, 260-261"))
    o.append(text(20, ty + 124, "1 row = Cols = 128 bf16 = 256 bytes; it travels with "
                  "the caller's flags [k_vnni.hpp:249-253]", 9.5, fill=C["muted"]))
    cap = ("B2, type model. k_vnni_tensor owns the 16 KiB plane. Its as_view() is the only "
           "source of a k_vnni_view. A writable view converts to a read-only one, never "
           "back (grey text: a route the code does not provide). "
           "detail::k_vnni_access::plane is the one route from a view to the "
           "raw address, open to the typed operations of this file, the two score "
           "kernels and the test-only fill. The transfer rows const_k_row_view / "
           "k_row_view carry one token's 128 values in dimension order with the caller's "
           "alignment and DMA (direct memory access) flags.")
    # the colour and font scheme of this figure (only the styles it uses)
    legend = [
        ("vnni", "blue: the owner k_vnni_tensor<Rows, Cols> and its views "
                 "k_vnni_view<bf16, 64, 128> (writable) and k_vnni_view<const bf16, 64, 128> "
                 "(read-only); blue text = the how-many of as_view() and the conversion"),
        ("ctx_ink", "grey box, ink outline: the code outside this type model that holds "
                    "or takes the plane: detail::kv_block::k and page::k_packed in "
                    "kv_cache.hpp, and the four takers of the raw address under "
                    "k_vnni_access::plane (three in other files, one being this header's "
                    "own operations)"),
        ("box", "white box, ink outline: friend struct, concept k_vnni_element<T>, "
                "detail::k_vnni_access::plane, and the transfer rows const_k_row_view / "
                "k_row_view with their Aligned, Dma flags; name in bold monospace, "
                "description in grey sans-serif"),
        ("arrow", "ink arrow: a containment or a route with its how-many (kv_block -> "
                  "plane, k_packed -> read-only view, view -> T*, plane() -> its four "
                  "callers)"),
        ("blue arrow: as_view(), 1 call -> 1 view (owner -> writable or read-only "
         "view), and the writable -> read-only conversion", "arrow", C["vnni"]),
        ("arrow_muted", "grey dashed arrow: the friend declarations and the concept that "
                        "constrain k_vnni_view (a constraint, not a call); grey text "
                        "'never the reverse' = a conversion the code does not provide"),
        ("font_mono", "monospace = the box titles (the holder, the owner, the accessor, "
                      "the two views, friend struct, concept k_vnni_element<T>, "
                      "plane(view), the four callers, the two transfer rows and the "
                      "Aligned, Dma flags)"),
        ("font_sans", "sans-serif = the descriptions under a title, the how-many labels "
                      "on the arrows, the grey words 'never the reverse', the line 'who "
                      "may take the address', the transfer-rows header and the closing "
                      "note"),
        ("font_cite", "small grey monospace = the lines that define a box or an arrow "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Type model: owner, views, the one access route, and the transfer rows",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B3: function model


def _band(o, boxes, fid, y, header, callers, callers_ref, callers_reg, cells, callees,
          cx0=245, cw_total=740, cell_h=62):
    """One group of operations: header, the callers box at the left (its drawn
    citation = the definition lines of its kv_cache.hpp callers; callers_reg =
    one register row per caller, (name, the line that defines it)), the
    function cells (62 px: name, two description lines, tag and citation) and
    their callees under them. Returns the next y."""
    o.append(band_header(cx0, y, header))
    y += 6
    n = len(cells)
    gap = 6
    cw = (cw_total - gap * (n - 1)) / n
    o.append(callers_box(20, y, 212, 84, callers, callers_ref))
    boxes.extend(callers_reg)
    o.append(arrow(fid, "ink", [(232, y + 30), (cx0 - 4, y + 30)], C["ink"]))
    for i, (name, desc, ref) in enumerate(cells):
        x = cx0 + i * (cw + gap)
        _w(name, 11.5, cw - 16, True, f"fn name {name}")
        for d in desc:
            _w(d, 9.5, cw - 16, False, f"fn desc {name}")
        o.append(fn_cell(x, y, cw, cell_h, name, desc, ref, "new"))
        boxes.append((name, ref))
        cl = callees[i]
        for d in cl:
            _w(d, 9, cw - 4, False, f"callee {name}")
        o.append(lines(x + 2, y + cell_h + 11, cl, 9, 10.5, fill=C["muted"]))
    return y + cell_h + 38


def b3():
    fid = "k_vnni-b3"
    W, H = 1000, 790
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 18, "callers in other files", 11, weight=700, fill=C["muted"]))
    o.append(text(245, 18, "the operations of k_vnni.hpp by purpose; a cell = name, what it "
                  "does, its definition (all new in this PR)", 10, fill=C["muted"]))
    o.append(text(245, 30, "under a cell: what it calls, expands to, or who reads it", 10,
                  fill=C["muted"]))
    y = 42
    y = _band(o, boxes, fid, y, "index map, bit helpers and the layout gate (lines 57-143)", [
        "kv_cache.hpp: note_k_row_saved 2175-",
        "2182, k_forget_row 2554-2555,",
        "kv_block::k_storage 2993",
        "self_attention.hpp: apply_page_tok 2024-",
        "2025, k_layout_dense 1925-1927",
        "model.hpp: k_store_shared 3193",
        "full.hpp: k_head_fn 2751"], "kv_cache.hpp:2167, 2552, 2993", [
        ("note_k_row_saved (caller)", "kv_cache.hpp:2167"),
        ("k_forget_row (caller)", "kv_cache.hpp:2552"),
        ("kv_block::k_storage (caller)", "kv_cache.hpp:2993"),
        ("apply_page_tok (caller)", "self_attention.hpp:1856"),
        ("k_layout_dense (caller)", "self_attention.hpp:1924"),
        ("k_store_shared (caller)", "model.hpp:3192"),
        ("page_info::k_head_fn (caller)", "full.hpp:2747")], [
        ("block_bit(c)", ["Bit c of a block mask", "(page::k_vnni_blocks)"],
         "k_vnni.hpp:97-100"),
        ("offset_bit(offset)", ["Bit `offset` of a page-offset", "mask (the saved rows)"],
         "k_vnni.hpp:101-105"),
        ("layout_on<head_size>", ["The layout gate: TRON_K_VNNI", "and 128-dimension heads"],
         "k_vnni.hpp:119-130"),
        ("index(token, dim)", ["Element index of K[token][dim]", "inside the plane"],
         "k_vnni.hpp:132-141"),
    ], [["= 1u << c"], ["= uint64_t{1} << offset"], ["constexpr bool, no call"],
        ["read by k_vnni_view::at (185)"]])
    y = _band(o, boxes, fid, y, "owner, views and the one access route (lines 145-247)", [
        "kv_cache.hpp: k_packed 2123 (const&),",
        "set_k_row 2253, set_k_block 2282,",
        "get_k_row 2297, k_row_if_row_major",
        "2348, fill_storage_slot 1835-1836",
        "kernels/k_vnni.hpp: qk_group 85",
        "amx_attn.cpp: qk_vnni_128x4 244"], "kv_cache.hpp:2120, 2247, 2277, 2291, 2341", [
        ("page::k_packed (caller)", "kv_cache.hpp:2120"),
        ("page::set_k_row (caller)", "kv_cache.hpp:2247"),
        ("page::set_k_block (caller)", "kv_cache.hpp:2277"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2291"),
        ("page::k_row_if_row_major (caller)", "kv_cache.hpp:2341"),
        ("book::fill_storage_slot (caller)", "kv_cache.hpp:1830"),
        ("k_vnni::qk_group (caller)", "kernels/k_vnni.hpp:61"),
        ("amx_attn_h128g4::qk_vnni_128x4 (caller)", "amx_attn.cpp:237")], [
        ("k_vnni_tensor::as_view", ["& writable, const& read-only;", "on a temporary: deleted"],
         "k_vnni.hpp:214-227"),
        ("k_vnni_view::at", ["Bounds-checked read of element", "(token, dim); no element write"],
         "k_vnni.hpp:179-186"),
        ("k_vnni_view(other)", ["Writable -> read-only view", "conversion, never the reverse"],
         "k_vnni.hpp:171-177"),
        ("k_vnni_access::plane", ["The plane's first element:", "the one route to the address"],
         "k_vnni.hpp:239-246"),
    ], [["-> k_vnni_view(T*) (private)"], ["-> k_vnni::index, TRON_ASSERT_LT"],
        ["copies data_ (friend view)"], ["-> k.data_ (friend)"]])
    y = _band(o, boxes, fid, y, "transfer rows and their builders (lines 249-284)", [
        "model.hpp: store_k_block 3311 (view",
        "overload, k_source_row(kout)) and",
        "3317 (pointer overload, conv[0])",
        "full.hpp: k_head_fn 2765-2766",
        "(k_destination_row(dest) -> get_k_row)"], "model.hpp:3241; full.hpp:2747", [
        ("store_k_block (caller)", "model.hpp:3241"),
        ("page_info::k_head_fn (caller)", "full.hpp:2747")], [
        ("k_source_row", ["Read-only transfer row from a const bf16* or a stride-1",
                          "bf16 view that keeps its flags; no check, no copy"],
         "k_vnni.hpp:262-277"),
        ("k_destination_row", ["Writable transfer row from a bf16*; the flags state",
                               "what the caller knows about its buffer; no copy"],
         "k_vnni.hpp:279-283"),
    ], [["-> const_k_row_view<Cols, Aligned, Dma>{row}",
         "in-file callers: copy_token 434, block_to_rows 522"],
        ["-> k_row_view<Cols, Aligned, Dma>{row}",
         "in-file callers: copy_token 433, block_to_vnni 505, block_to_rows 518"]])
    y = _band(o, boxes, fid, y, "internal helpers, namespace k_vnni::detail (lines 285-343)", [
        "no caller outside this file:",
        "store_row 356-359, load_row 374-377",
        "(pair_base, pair_row_offsets),",
        "store_block 408 (the transpose)"], "k_vnni.hpp:349, 367, 394", [
        ("store_row (in-file caller)", "k_vnni.hpp:349-351"),
        ("load_row (in-file caller)", "k_vnni.hpp:367-369"),
        ("store_block (in-file caller)", "k_vnni.hpp:394-396")], [
        ("pair_base", ["Byte address of dimension pair 0 of", "step s for a token: panel (s, c), dword t"],
         "k_vnni.hpp:290-301"),
        ("pair_row_offsets", ["Dword offsets of the 16 pair rows of", "one panel (64 bytes = 16 dwords apart)"],
         "k_vnni.hpp:303-310"),
        ("transpose_16x16_epi32", ["In-place transpose of 16 x 16 dwords:", "four stages, 64 shuffles in all"],
         "k_vnni.hpp:314-341"),
    ], [["two overloads: bf16*, const bf16*"], ["-> _mm512_set_epi32"],
        ["-> unpacklo/hi_epi32, _epi64, shuffle_i32x4"]])
    y = _band(o, boxes, fid, y, "one token's row, and a whole block (lines 344-436)", [
        "kv_cache.hpp: set_k_row 2255,",
        "get_k_row 2299, set_k_block 2282",
        "(<- model.hpp store_k_block 3338),",
        "copy_storage_slot 2750 (load_row)",
        "copy_token: test only",
        "(t_k_vnni_layout.cpp:197)"], "kv_cache.hpp:2247, 2291, 2277, 2691", [
        ("page::set_k_row (caller)", "kv_cache.hpp:2247"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2291"),
        ("page::set_k_block (caller)", "kv_cache.hpp:2277"),
        ("store_k_block (caller of set_k_block)", "model.hpp:3241"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2691"),
        ("copy_token call of the layout test", "t_k_vnni_layout.cpp:197")], [
        ("store_row", ["One token's row in: 4 scatters", "of 16 dwords, 64 pair slots"],
         "k_vnni.hpp:349-362"),
        ("load_row", ["One token's row out: 4 gathers", "of 16 dwords (the inverse)"],
         "k_vnni.hpp:367-380"),
        ("copy_token", ["One token between planes via a", "local row: load_row, store_row"],
         "k_vnni.hpp:426-435"),
        ("store_block", ["16 rows of block c transposed", "in registers: 64 line stores"],
         "k_vnni.hpp:394-420"),
    ], [["-> k_vnni_access::plane,", "pair_row_offsets, pair_base"],
        ["-> k_vnni_access::plane,", "pair_row_offsets, pair_base"],
        ["-> load_row, store_row,", "k_destination_row, k_source_row"],
        ["-> k_vnni_access::plane,", "transpose_16x16_epi32"]])
    y = _band(o, boxes, fid, y, "the row-major form of a block, Note [Row-major tail block] (lines 437-493)", [
        "kv_cache.hpp: set_k_row 2257,",
        "get_k_row 2301, k_row_if_row_major",
        "2348 (<- full.hpp k_head_fn 2762),",
        "copy_storage_slot 2750-2755",
        "self_attention.hpp: apply_page_tok",
        "2029 (the row-major dotter)"], "kv_cache.hpp:2341, 2247, 2291, 2691", [
        ("page::k_row_if_row_major (caller)", "kv_cache.hpp:2341"),
        ("page::set_k_row (caller)", "kv_cache.hpp:2247"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2291"),
        ("page_info::k_head_fn (caller of k_row_if_row_major)", "full.hpp:2747"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2691"),
        ("apply_page_tok (caller)", "self_attention.hpp:1856")], [
        ("row_major_row", ["The token's row inside a row-major", "block: panel (t / 4, c), row t % 4"],
         "k_vnni.hpp:462-472"),
        ("store_row_major", ["One token's row into its row-major", "block: 4 whole 64-byte lines"],
         "k_vnni.hpp:476-482"),
        ("load_row_major", ["One token's row out of its row-major", "block (the inverse of store_row_major)"],
         "k_vnni.hpp:486-492"),
    ], [["-> k_vnni_access::plane"], ["-> row_major_row, std::memcpy (256 B)"],
        ["-> row_major_row, std::memcpy (256 B)"]])
    y = _band(o, boxes, fid, y, "the in-place conversion of one block (lines 494-526)", [
        "kv_cache.hpp: k_block_to_vnni_at 2228",
        "(<- model.hpp convert_pending_k_blocks",
        "3177), copy_storage_slot 2743, 2759,",
        "k_forget_row 2576",
        "(<- clear_kv_complete_at 2476)"], "kv_cache.hpp:2214, 2691, 2552", [
        ("page::k_block_to_vnni_at (caller)", "kv_cache.hpp:2214"),
        ("convert_pending_k_blocks (caller of k_block_to_vnni_at)", "model.hpp:3173"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2691"),
        ("page::k_forget_row (caller)", "kv_cache.hpp:2552"),
        ("clear_kv_complete_at (caller of k_forget_row)", "kv_cache.hpp:2472")], [
        ("block_to_vnni", ["Block c row-major -> VNNI in place: 16 load_row_major to",
                           "the stack, then one store_block with FULL_BLOCK_0XFFFF"],
         "k_vnni.hpp:497-509"),
        ("block_to_rows", ["Block c VNNI -> row-major in place: 16 load_row to the",
                           "stack, then 16 store_row_major"],
         "k_vnni.hpp:512-524"),
    ], [["-> load_row_major, k_destination_row, store_block",
         "reads through the read-only view conversion (502)"],
        ["-> load_row, k_destination_row, store_row_major, k_source_row",
         "reads through the read-only view conversion (516)"]])
    H = int(y) + 4
    cap = ("B3, function model. Every operation of k_vnni.hpp as a cell: its name, one "
           "line on what it does, and the lines that define it. All are new in this PR. "
           "The grey box at the left of each group names the callers in other files with "
           "their call-site lines; its citation and the register give the lines that "
           "define those callers. The small text under a cell names what the cell calls, "
           "expands to, or who reads it. "
           "The page accessors of kv_cache.hpp (set_k_row, get_k_row, set_k_block, "
           "k_block_to_vnni_at, k_forget_row, copy_storage_slot) are the main callers.")
    # the colour and font scheme of this figure (only the styles it uses); the
    # grey callers box at the left of each group is a structural frame
    legend = [
        ("box", "white box, ink outline: one operation of k_vnni.hpp (a cell): its name "
                "in bold monospace, what it does in sans-serif, its tag and the lines "
                "that define it"),
        ("ctx", "grey box, thin grey outline: the callers in other files of one group, "
                "each with its call-site line; 'no caller outside this file' for the "
                "detail helpers"),
        ("arrow", "ink arrow: the callers in other files (grey box at the left) -> the "
                  "group of operations they call"),
        ("font_mono", "bold monospace = an operation's name"),
        ("font_sans", "sans-serif = what an operation does, the group headers, the "
                      "callers with their call-site lines, and what a cell calls or "
                      "expands to (grey, under the cell)"),
        ("font_cite", "small grey monospace = the lines that define an operation, or "
                      "the callers of a group (file:line)"),
        ("font_tag", "bold 'new' = the operation is added by PR 4424 (every cell)"),
    ]
    return figure(fid, W, H, "Function model: every operation of the file, its callers and callees",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B4: the bytes of one block through the operations


def b4_legend(x, y):
    o = []
    row1 = [("rm", "row-major token rows (4 lines each)"), ("vnni", "VNNI pair rows"),
            ("empty", "no row saved (bytes undefined)")]
    cx = x
    for st, lab in row1:
        if st == "empty":
            o.append(rect(cx, y, 22, 12, C["empty_fill"], C["empty"], 1, 1, "3 2"))
        else:
            o.append(rect(cx, y, 22, 12, C[st + "_fill"], C[st], 1, 1))
        o.append(text(cx + 28, y + 10, lab, 10))
        cx += 28 + text_width(lab, 10) + 18
    cx = x
    y2 = y + 18
    o.append(rect(cx, y2, 22, 12, "#fff", C["ink"], 1.6, 1))
    o.append(text(cx + 28, y2 + 10, "thick outline: the 4 lines of token 37", 10))
    cx += 28 + text_width("thick outline: the 4 lines of token 37", 10) + 18
    o.append(rect(cx, y2, 6, 12, C["vnni"], C["ink"], 1, 0))
    o.append(text(cx + 12, y2 + 10, "column t = 5 (token 37), written (4 B per line)", 10))
    cx += 12 + text_width("column t = 5 (token 37), written (4 B per line)", 10) + 18
    o.append(rect(cx, y2, 6, 12, "none", C["ink"], 1.2, 0, "2 2"))
    o.append(text(cx + 12, y2 + 10, "dashed: read", 10))
    return "".join(o)


def b4():
    fid = "k_vnni-b4"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 20, "worked example: block 2 (tokens 32..47) of the plane of slot 5, "
                  "KV head 0, page 7; its bytes are the 4 panels (s, 2) = 4 KiB", 11,
                  weight=700))
    o.append(text(20, 36, "each panel: 16 lines of 64 bytes, drawn top to bottom; the "
                  "steps are the life of the block in order, not to scale", 9.5,
                  fill=C["muted"]))
    o.append(b4_legend(20, 48))
    px0, pw, ph, pg = 300, 118, 72, 14
    step_h = 142          # the step box (80 px) plus the note lines under the panels
    y = 96
    steps = []
    # --- step 1: store_row_major --------------------------------------------
    p1, r1 = token_rows(EX["token"])
    steps.append(dict(
        n="1", title="store_row_major(plane, 37, src)",
        sub=["memcpy 256 B into row_major_row(plane, 37)",
             "= panel (1,2) #6, lines 4..7 (token row 1)",
             "[page::set_k_row, kv_cache.hpp:2257]"],
        fill=C["rm_fill"], stroke=C["rm"], ref="k_vnni.hpp:474-482",
        forms=rm_forms(BLOCK2_ROWS_SAVED), kw=dict(hi_rows=r1), kw_panel=p1,
        note=["state after rows 32..40 were saved this way (9 row-major rows: tokens "
              "32..35 in #2, 36..39 in #6, 40 in #10)",
              "writes 4 whole lines per token; any thread of the K store inside its "
              "claimed unit [model.hpp:3300-3320]",
              "token rows are disjoint bytes, so no read-modify-write between tokens "
              "[k_vnni.hpp:441-445]"]))
    # --- step 2: block_to_vnni ----------------------------------------------
    steps.append(dict(
        n="2", title="block_to_vnni(plane, 2)",
        sub=["16 x load_row_major -> stack rows[16][128]",
             "(4 KiB read), then one store_block with",
             "FULL_BLOCK_0XFFFF: 64 whole-line stores"],
        fill=C["pend_fill"], stroke=C["pend"], ref="k_vnni.hpp:497-509; 494-496",
        forms=[["vnni"] * 16 for _ in range(4)], kw=dict(read_all=True), kw_panel=None,
        note=["after rows 41..47 were saved the same way (16 row bits set, the block "
              "waits): per step s the 16 stack rows are transposed",
              "in registers and panel (s,2) is rewritten as 16 pair rows; the stack copy "
              "is needed because panel (s,2) still holds",
              "the rows of tokens 4 s .. 4 s + 3 [k_vnni.hpp:495-496]; main thread only, "
              "at the forward end [kv_cache.hpp:2206-2207; model.hpp:3171-3180]"]))
    # --- step 3: store_row ----------------------------------------------------
    steps.append(dict(
        n="3", title="store_row(plane, 37, src)",
        sub=["a row saved again into the converted block:",
             "4 scatters of 16 dwords, one per step s, into",
             "dword 5 of all 64 lines [page::set_k_row 2255]"],
        fill=C["vnni_fill"], stroke=C["vnni"], ref="k_vnni.hpp:349-362; 344-348",
        forms=[["vnni"] * 16 for _ in range(4)], kw=dict(col=EX["t"]), kw_panel=None,
        note=["only this token's 64 pair slots (4 bytes in each of the 64 lines) are "
              "written; pair_base(plane, s, 37) + pair_row_offsets",
              "address them, so several threads may store different tokens of one plane "
              "at the same time",
              "[k_vnni.hpp:346-348; Note [Shared block save], model.hpp:3085-3152]"]))
    # --- step 4: load_row -----------------------------------------------------
    steps.append(dict(
        n="4", title="load_row(plane, 37, dst)",
        sub=["the inverse: 4 gathers of 16 dwords out of",
             "the same 64 slots into a 256 B transfer row",
             "[page::get_k_row 2299; copy_storage_slot 2750]"],
        fill="#fff", stroke=C["vnni"], ref="k_vnni.hpp:367-380; 364-366",
        forms=[["vnni"] * 16 for _ in range(4)], kw=dict(col=EX["t"], col_read=True),
        kw_panel=None,
        note=["reads 64 lines for one token; the FPGA staging (k_head_fn -> get_k_row) "
              "pays this gather for a converted block only",
              "[full.hpp:2762-2767]; the row-major read of step 1's form is 4 lines "
              "(load_row_major, k_vnni.hpp:484-492;",
              "row_major_row in place, k_vnni.hpp:462-472)"]))
    # --- step 5: block_to_rows -------------------------------------------------
    steps.append(dict(
        n="5", title="block_to_rows(plane, 2)",
        sub=["16 x load_row -> stack rows[16][128]",
             "(4 KiB read by 64 gathers), then 16 x",
             "store_row_major: 4 whole lines each"],
        fill=C["rm_fill"], stroke=C["rm"], ref="k_vnni.hpp:512-524; 511",
        forms=rm_forms(range(32, 48)), kw=dict(read_all=True), kw_panel=None,
        note=["the block is row-major again, all 16 token rows in place; the page "
              "clears its block bit (k_forget_row) or",
              "recomputes it (copy_storage_slot); scheduler thread with the token tree "
              "locked, between forward passes",
              "[k_forget_row kv_cache.hpp:2550-2551, 2576; copy_storage_slot 2743]"]))
    for st in steps:
        o.append(text(20, y + 10, st["n"], 13, weight=700))
        for s in st["sub"]:
            _w(s, 9.5, 242, where=f"b4 sub {st['title']}")
        # title + 3 sub-lines + citation: 80 px (the citation sits at y + h - 4)
        o.append(label_box(36, y - 2, 250, 80, st["title"], st["sub"], st["fill"],
                           st["stroke"], 10.5, ref=st["ref"]))
        boxes.append((st["title"], st["ref"]))
        for s in range(4):
            x = px0 + s * (pw + pg)
            o.append(text(x + pw / 2, y + 2, f"panel ({s},2) #{4 * s + 2}", 9, "middle",
                          True, fill=C["muted"]))
            kw = dict(st["kw"])
            if st["kw_panel"] is not None and s != st["kw_panel"]:
                kw.pop("hi_rows", None)
            o.append(panel_lines(x, y + 7, pw, ph, st["forms"][s], **kw))
        for i, s in enumerate(st["note"]):
            _w(s, 9.5 if i == 0 else 9, 680, where=f"b4 note {st['title']}")
        o.append(text(px0, y + ph + 20, st["note"][0], 9.5, fill=C["ink"]))
        o.append(lines(px0, y + ph + 32, st["note"][1:], 9, 11, fill=C["muted"]))
        y += step_h
    H = int(y) - 4
    cap = ("B4, sequencing model: the bytes of block 2 of the worked example through the "
           "operations. Each row shows the block's 4 panels (4 KiB) after one operation. "
           "store_row_major writes 4 whole lines per token into the row-major form. "
           "block_to_vnni rewrites all 64 lines as pair rows of the VNNI form (Vector "
           "Neural Network Instructions layout) at the forward end (the end of the "
           "forward pass). "
           "store_row and load_row then touch 4 bytes in every one of the 64 lines for "
           "one token. block_to_rows puts the row-major form back in place. Look at "
           "how many lines each operation touches: 4 per token in the row-major form, "
           "64 per token in the VNNI form.")
    # the colour and font scheme of this figure (only the styles it uses)
    legend = [
        ("rm", "orange: a row-major token row, 4 lines of 64 B per token (steps 1 and 5); "
               "also the step boxes store_row_major and block_to_rows"),
        ("vnni", "blue: a VNNI pair row, 64 B, of the converted block (steps 2 to 4); "
                 "also the step box store_row"),
        ("empty", "grey dashed line: no row saved yet, bytes undefined (tokens 41..47 "
                  "in step 1)"),
        ("pend_solid", "orange-red outline: step 2, block_to_vnni(plane, 2), the "
                       "conversion of the complete block"),
        ("white box, blue outline: step 4, load_row(plane, 37, dst), a read of the VNNI "
         "form", "#fff", C["vnni"], False, False),
        ("solid blue column, ink outline: dword t = 5 (token 37) written by store_row, "
         "4 B in each of the 64 lines", C["vnni"], C["ink"], False, False),
        ("ink outline: a panel's frame; drawn heavier, the 4 lines of token 37 in "
         "step 1", "none", C["ink"], False, False),
        ("dashed ink outline: a read: the whole panel in block_to_vnni and "
         "block_to_rows, token 37's column in load_row", "none", C["ink"], True, False),
        ("box", "white chip, ink outline, in the key at the top: stands for the heavier "
                "outline of token 37's 4 lines"),
        ("font_mono", "monospace = an operation call in a step box, and the panel "
                      "labels (s,2) #n"),
        ("font_sans", "sans-serif = the worked example's header, the key, the step "
                      "numbers 1 to 5 (bold), what a step does, and the notes under the "
                      "panels"),
        ("font_cite", "small grey monospace = the lines that define a step's operation "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Sequencing model: the bytes of one block through the operations",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B5: interaction model (who calls which operation from which thread)

# phase columns of B5: (x0, x1, name, cite); time starts at x = 160
B5_COLUMNS = [(165, 485, "save_k of one layer: the shared K store window",
               "model.hpp:3346-3437"),
              (495, 675, "scoring and staging of the pass", "self_attention.hpp; full.hpp"),
              (685, 815, "forward end", "model.hpp:1836-1847"),
              (825, 980, "between passes (tree lock)", "kv_cache.hpp:701-704")]


def b5():
    fid = "k_vnni-b5"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    # the reading order (left to right = one forward pass, schematic) and the
    # solid / dashed meaning are in the caption and the page legend
    for x0, x1, name, ref in B5_COLUMNS:
        o.append(rect(x0, 12, x1 - x0, 26, C["soft"], C["line"], 1, 3))
        o.append(text((x0 + x1) / 2, 24, name, 9.5, "middle", weight=600))
        o.append(text((x0 + x1) / 2, 35, ref, 8.5, "middle", True, fill=C["cite"]))
    # lane heights: every lane_block needs 10 n + 17 px for n lines at
    # lh 10 (first baseline y + 11, citation at y + h - 3)
    lanes_ = [("main thread", "worker_ix 0", 150),
              ("main helpers", "worker_ix 1..n-1", 70),
              ("attention workers", "self_attention.hpp", 120),
              ("GOF staging", "workers | main", 88),
              ("scheduler thread", "tree work", 122)]
    ly = 46
    lane_y = {}
    for name, sub, h in lanes_:
        svg, _ = lane(20, ly, 960, h, name, sub)
        o.append(svg)
        lane_y[name] = (ly, h)
        ly += h + 4
    # --- main thread ------------------------------------------------------------
    y, h = lane_y["main thread"]
    o.append(lane_block(165, y + 6, 182, 77, [
        "k_store_cut_units, then",
        "increments opened (release);",
        "claims units: store_k_block ->",
        "set_k_row -> store_row_major",
        "| store_row; set_k_block ->",
        "store_block (+ note_k_block_saved)"],
        C["unit_fill"], C["unit"], "model.hpp:3380-3397", size=9))
    boxes.append(("save_k_impl, main: claims units -> store_k_block", "model.hpp:3352, 3380-3397"))
    o.append(lane_block(353, y + 6, 132, 77, [
        "join: waits for",
        "finished ==",
        "n_workers - 1 (acquire)",
        "with a 120 s watchdog"], "#fff", C["ink"], "model.hpp:3402-3416", idle=True,
        size=9))
    boxes.append(("save_k_impl, main: join", "model.hpp:3352, 3402-3416"))
    o.append(lane_block(165, y + 88, 320, 58, [
        "after the join, main alone: note_k_row_saved per row",
        "(offset_bit, block_bit; fetch_or) -> pending_k_blocks_;",
        "not for a hardware-scored operation; then the marks and",
        "upstream_kvs_ready.count_down"],
        C["rows_fill"], C["rows"], "model.hpp:3420-3456", size=9))
    boxes.append(("save_k_impl, main: note_k_row_saved -> pending_k_blocks_",
                  "model.hpp:3352, 3420-3456"))
    o.append(lane_block(685, y + 6, 130, 58, [
        "wait_for_coop_gof:",
        "fires the remaining",
        "gof_rodeo tasks itself,",
        "waits outstanding == 0"],
        C["hw_fill"], C["hw"], "model.hpp:3583-3592", size=9))
    boxes.append(("wait_for_coop_gof", "model.hpp:3583-3592"))
    o.append(lane_block(685, y + 72, 130, 68, [
        "convert_pending_k_blocks",
        "-> k_block_to_vnni_at ->",
        "block_to_vnni (every KV",
        "head), then the block bit;",
        "main only, no reader runs"],
        C["pend_fill"], C["pend"], "model.hpp:3171-3180", size=9))
    boxes.append(("convert_pending_k_blocks -> k_block_to_vnni_at -> block_to_vnni",
                  "model.hpp:3171-3180"))
    # --- helpers -------------------------------------------------------------
    y, h = lane_y["main helpers"]
    # three blocks in the 320 px window column: 76 + 3 + 162 + 3 + 76, so the
    # two 8.5 px citations and the 31-character line fit
    o.append(lane_block(165, y + 6, 76, 58, [
        "waits for", "opened >= W", "(acquire)"], "#fff", C["ink"],
        "model.hpp:3385", idle=True, size=9))
    boxes.append(("save_k_impl, helper: waits for opened >= W", "model.hpp:3352, 3385-3390"))
    o.append(lane_block(244, y + 6, 162, 58, [
        "claims units: store_k_block ->",
        "set_k_row -> store_row_major",
        "| store_row; set_k_block ->",
        "store_block, note_k_block_saved"],
        C["unit_fill"], C["unit"], "model.hpp:3391-3397", size=9))
    boxes.append(("save_k_impl, helper: claims units -> store_k_block", "model.hpp:3352, 3391-3397"))
    o.append(lane_block(409, y + 6, 76, 58, [
        "increments", "finished", "(release);", "returns"], "#fff", C["ink"],
        "model.hpp:3399", idle=True, size=9))
    boxes.append(("save_k_impl, helper: finished += 1, returns", "model.hpp:3352, 3398-3401"))
    # --- attention workers ---------------------------------------------------
    y, h = lane_y["attention workers"]
    o.append(lane_block(165, y + 6, 320, 84, [
        "pending sections wait behind save_k: a worker reads",
        "a pending page only after every minibatch that",
        "writes it counted upstream_kvs_ready down",
        "[kv_cache.hpp:695-699; self_attention.hpp:823]"],
        "#fff", C["ink"], "kv_cache.hpp:695-699", idle=True))
    boxes.append(("attention worker: waits for upstream_kvs_ready", "kv_cache.hpp:695-699"))
    o.append(lane_block(495, y + 6, 180, 107, [
        "apply_page_tok, per page:",
        "all 4 block bits set: the AMX",
        "kernel qk_vnni_128x4(k_packed)",
        "scores the whole page",
        "else, block bit set: its live",
        "tokens go into a mask, then",
        "qk_group(plane, mask) scores them",
        "block bit clear: row_major_row ->",
        "dotter, one token at a time"],
        C["q_fill"], C["q"], "self_attention.hpp:1906-2049", size=9))
    boxes.append(("apply_page_tok -> qk_vnni_128x4 | qk_group | row_major_row -> dotter",
                  "self_attention.hpp:1856, 1906-2049"))
    # --- GOF staging: no thread of its own (model.hpp:1167-1168) ----------------
    y, h = lane_y["GOF staging"]
    o.append(lane_block(495, y + 6, 180, 77, [
        "gof::populate -> k_head_fn:",
        "k_row_if_row_major -> the row",
        "in place | get_k_row -> load_row",
        "or load_row_major into k_scratch",
        "[attention worker: help_drain_gof",
        "| main: wait_for_coop_gof]"],
        C["hw_fill"], C["hw"], "gof.cpp:188; full.hpp:2747-2772", size=9))
    boxes.append(("gof::populate -> k_head_fn -> k_row_if_row_major | get_k_row "
                  "[attention worker (help_drain_gof) or main (wait_for_coop_gof)]",
                  "gof.cpp:188, full.hpp:2747-2772; model.hpp:1167-1168, 3570-3576, 3583-3592"))
    o.append(lane_block(685, y + 6, 130, 58, [
        "drained by main's",
        "wait_for_coop_gof",
        "before any block",
        "converts"], "#fff", C["ink"], "model.hpp:1838-1847", idle=True, size=9))
    boxes.append(("staging gather drained at the forward end", "model.hpp:1838-1847"))
    # --- scheduler ---------------------------------------------------------------
    y, h = lane_y["scheduler thread"]
    o.append(lane_block(825, y + 6, 155, 48, [
        "clear_kv_complete_at ->",
        "k_forget_row -> block_to_rows",
        "(every KV head)"],
        C["rm_fill"], C["rm"], "kv_cache.hpp:2472-2477", size=9))
    boxes.append(("clear_kv_complete_at -> k_forget_row -> block_to_rows",
                  "kv_cache.hpp:2472-2477"))
    o.append(lane_block(825, y + 60, 155, 58, [
        "copy_from -> copy_storage_slot:",
        "block_to_rows, load_row,",
        "store_row_major,",
        "row_major_row, block_to_vnni"],
        C["rm_fill"], C["rm"], "kv_cache.hpp:2787, 2691-2763", size=9))
    boxes.append(("copy_from -> copy_storage_slot", "kv_cache.hpp:2787, 2691-2763"))
    o.append(lane_block(165, y + 6, 510, 40, [
        "no forward pass reads the book while the tree lock is held: the in-place "
        "transposes of",
        "clear_kv_complete_at and copy_from rely on it, between forward passes"],
        "#fff", C["ink"], "kv_cache.hpp:701-704", idle=True))
    boxes.append(("clear_kv_complete_at and copy_from: between forward passes, tree lock held",
                  "kv_cache.hpp:701-704"))
    # --- thread rules ---------------------------------------------------------------
    ry = ly + 4
    o.append(text(20, ry + 12, "thread rules, each cited from the comment that states it",
                  11, weight=700))
    rules = [
        ("R1", ["several threads may store different tokens of one plane at the same time: "
                "store_row writes only the token's 64 pair slots, store_row_major only its 4 lines"],
         "k_vnni.hpp:346-348, 474-482; model.hpp:3122-3128"),
        ("R2", ["block_to_vnni through k_block_to_vnni_at: main thread only, at a point where "
                "no reader of the block runs (the forward end)"], "kv_cache.hpp:2206-2207"),
        ("R3", ["a completed block waits for the forward end because the cooperative GOF "
                "staging gather of an earlier minibatch may still read its rows row-major"],
         "kv_cache.hpp:692-701; model.hpp:3155-3162"),
        ("R4", ["the in-place row of k_row_if_row_major is valid as long as no writer touches "
                "the block, the same rule as get_k_row's read"], "kv_cache.hpp:2332-2336"),
        ("R5", ["the saved-row bits of short runs: main only, after the join; the full-block "
                "bits (note_k_block_saved): any thread of the window, after the last KV head"],
         "kv_cache.hpp:2608-2615, 705-711"),
        ("R6", ["k_forget_row and copy_from run their transposes with the token tree locked, "
                "between forward passes: no reader runs meanwhile"], "kv_cache.hpp:2550-2551, 701-704"),
        # Note [Row-major blocks under hardware attention] (k_vnni-sequencing-40)
        ("R7", ["a hardware-scored operation (cached_operation_uses_hw): save_k records no row "
                "bits for its short runs and queues no block, so the block stays row-major and "
                "a page copy does not",
                "convert it either; the CPU scores only the tail above the engagement point, "
                "row by row when a tail token lies in a row-major block"],
         "kv_cache.hpp:729-744; model.hpp:3420-3426"),
    ]
    yy = ry + 28
    for tag, rl, ref in rules:
        o.append(text(20, yy, tag, 10, weight=700, mono=True))
        for s in rl:
            _w(s, 9.5, 932, where=f"b5 rule {tag}")
        o.append(lines(48, yy, rl, 9.5, 10))
        o.append(text(48, yy + 10 * len(rl), f"[{ref}]", 8.5, mono=True, fill=C["cite"]))
        yy += 20 + 10 * (len(rl) - 1)
    H = int(yy) - 6
    cap = ("B5, interaction model. One lane per kind of thread, left to right in the "
           "order of one forward pass (schematic, not to scale). Main and its helpers "
           "store rows inside the shared K store window (one shared save_k call). The "
           "thread that stores a whole 16-token block publishes its 16 row bits and its "
           "block bit at once (note_k_block_saved, any thread of the window). Only main "
           "records the row bits of the shorter runs, after the join. Only main converts "
           "the completed blocks at the forward end, after the staging gather (the copy "
           "of K/V rows for the FPGA) drained. The attention workers only read. The GOF "
           "staging gather (gof::populate) also only reads, and it has no thread of its "
           "own: idle attention workers run it through help_drain_gof, and main runs the "
           "rest through wait_for_coop_gof. The scheduler thread (the thread that runs "
           "the scheduler of full.hpp between forward passes) converts blocks back to "
           "row-major under the tree lock (the lock on the token tree). The two yellow "
           "blocks are that staging path, drawn in the hardware attention colour. R1 to "
           "R7 cite the comment that states each rule. R7 is the hardware-attention "
           "exception: the rows of a hardware-scored operation get no bits and no "
           "conversion.")
    # the colour and font scheme of this figure (only the styles it uses); the
    # lanes and the phase headers are structural frames
    legend = [
        ("unit", "grey-blue: a thread claims units of the shared K store window, "
                 "store_k_block -> set_k_row / set_k_block (main and its helpers)"),
        ("rows", "green: main alone, after the join, records the saved-row bits: "
                 "note_k_row_saved -> pending_k_blocks_"),
        ("pend_solid", "orange-red outline: convert_pending_k_blocks -> "
                       "k_block_to_vnni_at -> block_to_vnni, main only at the forward end"),
        ("hw", "yellow: the FPGA staging path, gof::populate -> k_head_fn (an attention "
               "worker or main) and main's wait_for_coop_gof"),
        ("q", "purple: the attention workers' scoring, apply_page_tok -> qk_vnni_128x4 | "
              "qk_group | row_major_row -> dotter"),
        ("rm", "orange: the scheduler thread's conversions back to row-major, "
               "clear_kv_complete_at -> k_forget_row -> block_to_rows and copy_from -> "
               "copy_storage_slot"),
        ("ctx", "grey box, thin grey outline: a phase header of the top row, with the "
                "lines that bound the phase"),
        ("lane", "white frame, thin grey outline: one thread lane; its name at the left "
                 "in bold, its worker index or role under it in grey"),
        ("idle", "dashed outline: a thread waits, has no work, or leaves the window: "
                 "main's join, the helpers' wait for opened and their 'increments "
                 "finished; returns', the attention workers behind save_k, the drained "
                 "staging gather, and the scheduler's rule that no forward pass reads "
                 "under the tree lock"),
        ("font_mono", "bold monospace = the rule tags R1 to R7"),
        ("font_sans", "sans-serif = the lane and phase names, what each block does, "
                      "and the rules"),
        ("font_cite", "small grey monospace = the lines that define a block, a phase "
                      "or a rule (file:line)"),
    ]
    return figure(fid, W, H, "Interaction model: who calls which operation from which thread",
                  "".join(o), cap, boxes=boxes, legend=legend)
