"""Base diagrams B1-B5 of the PR 4956 page for h/tron/tensor/k_vnni.hpp.

Adapted from exec/pr4424-diagrams-20261009/figs/base_k_vnni.py. Every fact
drawn here comes from the head file (PR 4956 head a5697f86d3) or from the
cited caller files of the same head. Line numbers are head line numbers of
h/tron/tensor/k_vnni.hpp unless another file is named.

Module-level constants and building blocks (imported by the change diagrams):
  EX, PAGE_7, SLOT_5, KV_HEAD_0, BLOCK_2, ROWS_SAVED_0_40, LIVE_MASK,
  BLOCK_MASKS, index_of, panel_grid, panel_lines, pair_row_dwords,
  block_panels, lane_block, callers_box, band_header, _vcard, _band_box
"""
import sys

from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, label_box,
                         lane, line, lines, marker_defs, rect, text, text_width)

# ---------------------------------------------------------------------------
# The worked example of the page (STYLE.md): page 7, storage slot 5, KV head 0,
# the K rows of offsets 0..40 saved; token 37 = block 2, t = 5; dimension 70 =
# step 2, pair 3, j = 0. One scoring visit marks offsets 0..40 live.
PAGE_7, SLOT_5, KV_HEAD_0, BLOCK_2 = 7, 5, 0, 2
ROWS_SAVED_0_40 = list(range(0, 41))            # page offsets whose K row is saved
LIVE_MASK = sum(1 << i for i in ROWS_SAVED_0_40)  # the live mask of the visit
BLOCK_MASKS = [(LIVE_MASK >> (16 * c)) & 0xffff for c in range(4)]  # 0xffff, 0xffff, 0x01ff, 0


def index_of(token, dim):
    """k_vnni::index (k_vnni.hpp:99-106) and its five coordinates."""
    s, c = dim // 32, token // 16
    dp, t, j = (dim % 32) // 2, token % 16, dim % 2
    return dict(s=s, c=c, dp=dp, t=t, j=j,
                index=(((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j,
                panel=s * 4 + c)


EX = dict(token=37, dim=70)
EX.update(index_of(EX["token"], EX["dim"]))          # s=2 c=2 dp=3 t=5 j=0, index 5226
EX["byte"] = EX["index"] * 2                           # 10452
assert EX["index"] == 5226 and EX["panel"] == 10
assert BLOCK_MASKS == [0xffff, 0xffff, 0x01ff, 0]


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
    frame (the frame marks the worked example's block, not a layout state)."""
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
                read_all=False, cols_empty=(), cols_live=None):
    """One panel as its 16 pair rows of 64 bytes, top line = pair row 0.
    forms: 16 states, one per line: 'vnni' | 'empty'.
    hi_rows: line indexes drawn with a thick outline.
    col: a dword index 0..15 whose 4-byte slot is marked in every line (a
    token's column); col_read: mark it as a read (dashed) instead of a write.
    read_all: dashed outline round the whole panel = the 1 KiB is read.
    cols_empty: dword indexes whose column holds no saved row (grey dashed).
    cols_live: a 16-bit mask; the columns of its set bits are drawn as read
    (dashed ink), the clear bits as not read (grey dashed)."""
    lh = h / 16
    o = []
    for i, f in enumerate(forms):
        ly = y + i * lh
        if f == "vnni":
            o.append(rect(x, ly, w, lh, C["vnni_fill"], C["vnni"], 0.5, 0))
        else:
            o.append(rect(x, ly, w, lh, C["empty_fill"], C["empty"], 0.5, 0, "2 2"))
    cwid = w / 16
    for t in cols_empty:
        o.append(rect(x + t * cwid, y, cwid, h, C["empty_fill"], C["empty"], 0.8, 0, "2 2"))
    if cols_live is not None:
        for t in range(16):
            if (cols_live >> t) & 1:
                o.append(rect(x + t * cwid, y, cwid, h, "none", C["ink"], 0.8, 0, "2 2"))
            else:
                o.append(rect(x + t * cwid, y, cwid, h, C["empty_fill"], C["empty"], 0.8, 0,
                              "2 2"))
    for i in hi_rows:
        o.append(rect(x, y + i * lh, w, lh, "none", C["ink"], 1.6, 0))
    if col is not None:
        cx = x + col * cwid
        if col_read:
            o.append(rect(cx, y, cwid, h, "none", C["ink"], 1.2, 0, "2 2"))
        else:
            o.append(rect(cx, y, cwid, h, C["vnni"], C["ink"], 1.0, 0))
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


def block_panels(x, y, c, pw=118, ph=72, gap=14, **kw):
    """The 4 panels (s, c), s = 0..3, of token block c = the block's 4 KiB,
    with a 'panel (s,c) #n' label above each. kw go to panel_lines."""
    o = []
    for s in range(4):
        px = x + s * (pw + gap)
        o.append(text(px + pw / 2, y - 5, f"panel ({s},{c}) #{4 * s + c}", 9, "middle",
                      True, fill=C["muted"]))
        o.append(panel_lines(px, y, pw, ph, ["vnni"] * 16, **kw))
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
    """The callers of a group of operations, in other files (file: name line)."""
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


def _band_box(o, boxes, x, y, w, h, title, sub, fill, stroke, ref, reg=None, size=11):
    """A box of B1's containment band: label_box + register entry + width check."""
    _w(title, size, w - 8, True, f"b1 band {title}")
    for s in sub:
        _w(s, size - 1, w - 8, where=f"b1 band {title}")
    o.append(label_box(x, y, w, h, title, sub, fill, stroke, size, ref=ref))
    boxes.append((title, reg or ref))


# ---------------------------------------------------------------------------
# B1: data model of one plane


def b1():
    fid = "k_vnni-b1"
    W, H = 1000, 760
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    # ---- top band: the containment, book -> page -> kv_block -> k, v ------
    by0, bh0 = 24, 48
    my = by0 + bh0 / 2
    _band_box(o, boxes, 20, by0, 140, bh0, "book", ["the KV cache (unchanged)"],
              C["soft"], C["ink"], "kv_cache.hpp:969, 1448")
    _band_box(o, boxes, 262, by0, 170, bh0, "page", ["64-token page (changed)"],
              C["soft"], C["ink"], "kv_cache.hpp:1880")
    _band_box(o, boxes, 560, by0, 200, bh0, "detail::kv_block",
              ["one KV head of one KV slot"], C["soft"], C["ink"], "kv_cache.hpp:2559-2561")
    o.append(arrow(fid, "ink", [(160, my), (258, my)], C["ink"], 1.4))
    o.append(lines(209, my - 18, ["1 book ->", "n_pages pages"], 9, 10, "middle",
                   fill=C["ink"], weight=600))
    o.append(text(209, my + 13, "[kv_cache.hpp:1448]", 8.5, "middle", True,
                  fill=C["cite"]))
    o.append(arrow(fid, "ink", [(432, my), (556, my)], C["ink"], 1.4))
    o.append(lines(494, my - 26, ["1 page ->", "n_kv_heads kv_blocks", "per storage slot"],
                   8.5, 10, "middle", fill=C["ink"], weight=600))
    o.append(text(494, my + 13, "[kv_cache.hpp:1668, 1708]", 8.5, "middle", True,
                  fill=C["cite"]))
    o.append(arrow(fid, "ink", [(660, by0 + bh0), (660, 92), (180, 92), (180, 104)],
                   C["ink"], 1.4))
    o.append(text(190, 86, "1 kv_block -> 1 K plane (k) + 1 V plane (v)", 9, fill=C["ink"],
                  weight=600))
    o.append(text(440, 86, "[kv_cache.hpp:2575, 2585, 2588]", 8.5, mono=True, fill=C["cite"]))
    _band_box(o, boxes, 780, by0, 200, bh0, "detail::kv_block::v",
              ["V plane: v_vnni_tensor (unchanged)"], C["soft"], C["line"],
              "kv_cache.hpp:2580-2585", size=10.5)
    o.append(arrow(fid, "muted", [(760, my), (776, my)], C["muted"], 1.2))
    # ---- left column: containment with how-many ---------------------------
    lx, lw, bh, step = 20, 316, 60, 86
    col = [
        ("detail::kv_block::k", ["k_storage = k_vnni_tensor<64, 128> (VNNI slot)",
                                 "or native_k_storage = bf16[64 * 128]; changed"],
         C["soft"], C["ink"], "kv_cache.hpp:2565-2575",
         ("ink", "1 k -> 1 owner k_vnni_tensor (a VNNI slot)", "kv_cache.hpp:2566-2568")),
        ("k_vnni_tensor<64, 128>", ["alignas(64) bf16 data_[Rows * Cols]: owner (new)",
                                    "trivial, no allocation, no initialization"],
         C["vnni_fill"], C["vnni"], "k_vnni.hpp:155-185",
         ("vnni", "1 owner -> Rows * Cols = 8192 bf16 = 16 KiB", "k_vnni.hpp:179, 181-185")),
        ("plane", ["K for one KV head of one page (new)",
                   "64 tokens x 128 dimensions of bf16 = 16 KiB"],
         C["vnni_fill"], C["vnni"], "k_vnni.hpp:18-25",
         ("ink", "1 plane -> TOKEN_BLOCKS_4 = PAGE_TOKENS_64 / BLOCK_TOKENS_16 = 4 token blocks",
          "k_vnni.hpp:64")),
        ("token block c", ["16 tokens: page offsets 16 c .. 16 c + 15 (new)",
                           "owns panel (s, c), s = 0..3: 4 KiB of its own"],
         "#fff", C["ink"], "k_vnni.hpp:22-27, 63-64",
         ("ink", "1 block -> BLOCK_TOKENS_16 = 16 tokens", "k_vnni.hpp:63")),
        ("token i", ["column (i % 16) of block (i / 16) in all 4 panels",
                     "-> DIM_STEPS_4 x STEP_PAIRS_16 = 64 dword slots"],
         "#fff", C["ink"], "k_vnni.hpp:27-29, 251-252",
         ("ink", "1 token -> DIM_STEPS_4 = 4 steps", "k_vnni.hpp:65-67")),
        ("dimension step s, pair dp", ["1 step = STEP_PAIRS_16 pairs (AMX tile depth)",
                                       "1 pair = PAIR_2 bf16 (dims 2dp, 2dp + 1), 1 dword"],
         "#fff", C["ink"], "k_vnni.hpp:58-60, 65-67", None),
    ]
    y = 106
    for title, sub, fill, stroke, ref, arr in col:
        for s in sub:
            _w(s, 11, lw - 8, where=f"b1 {title}")
        o.append(label_box(lx, y, lw, bh, title, sub, fill, stroke, ref=ref))
        boxes.append((title, ref))
        if arr:
            _vcard(o, fid, arr[0], C[arr[0]], lx + 60, y + bh, y + step, arr[1], arr[2])
        y += step
    plane_mid = 106 + 2 * step + bh / 2
    block_mid = 106 + 3 * step + bh / 2
    # ---- middle column: the panel grid --------------------------------------
    gx, gy, cw, ch = 440, 130, 56, 44
    o.append(text(gx + 118, 106, "the plane: 16 panels (s, c), panel index 4 s + c", 11,
                  "middle", weight=700))
    o.append(panel_grid(gx, gy, cw, ch, hi=(EX["s"], EX["c"]), block=BLOCK_2))
    o.append(arrow(fid, "vnni", [(lx + lw, plane_mid), (gx - 4, plane_mid)], C["vnni"], 1.4))
    gap_mid = (lx + lw + gx - 4) / 2
    o.append(lines(gap_mid, plane_mid - 64, ["1 plane ->", "N_PANELS_16 =", "DIM_STEPS_4 x",
                                             "TOKEN_BLOCKS_4", "= 16 panels"], 8.5, 10,
                   "middle", fill=C["vnni"], weight=600))
    o.append(text(gap_mid, plane_mid - 8, "[k_vnni.hpp:73]", 8.5, "middle", True,
                  fill=C["cite"]))
    bx = gx + BLOCK_2 * (cw + 4) + cw / 2
    o.append(arrow(fid, "ink", [(lx + lw, block_mid), (bx, block_mid),
                                (bx, gy + 4 * ch + 3 * 4 + 6)], C["ink"], 1.6))
    o.append(lines(bx + 8, 342, ["block 2 ->", "DIM_STEPS_4 = 4", "panels (s, 2): 4 KiB"],
                   9, 12, fill=C["ink"], weight=600))
    o.append(text(bx + 8, 380, "[k_vnni.hpp:26-27]", 8.5, mono=True, fill=C["cite"]))
    mem = ["memory order: panel index 4 s + c,",
           "byte offset 1024 x (4 s + c).",
           "block 2 (framed) owns panels #2, #6, #10, #14:",
           "four 1 KiB pieces 4 KiB apart.",
           "panel (2,2) #10 (blue) holds token 37, dim 70."]
    for s in mem:
        _w(s, 9.5, 290, where="b1 memory order")
    o.append(lines(gx - 20, 450, mem, 9.5, 12, fill=C["ink"]))
    o.append(text(gx - 20, 538, "pair row 3 of panel #10: 16 dwords, t = token % 16",
                  9.5, weight=600))
    o.append(pair_row_dwords(gx - 20, 546, 256, 26, hi_t=EX["t"], base_token=32))
    o.append(lines(gx - 20, 598, ["token 37 = dword 5: low half j = 0 is dim 70,",
                                  "high half j = 1 is dim 71"], 9, 12, fill=C["ink"]))
    o.append(text(gx - 20, 623, "[k_vnni.hpp:58-60, 75-77]", 8.5, mono=True, fill=C["cite"]))
    # ---- right column: one panel zoomed, panel and pair row boxes ------------
    rx, ry = 740, 202
    o.append(text(rx + 100, 178, "panel (2,2) #10: 16 pair rows x 64 B", 11, "middle",
                  weight=700))
    o.append(panel_lines(rx, ry, 200, 160, ["vnni"] * 16, hi_rows=[EX["dp"]]))
    for dp in range(16):
        o.append(text(rx - 4, ry + dp * 10 + 8, f"dp {dp}", 8.5, "end", True,
                      fill=C["vnni"] if dp == EX["dp"] else C["muted"]))
    o.append(text(rx, 378, "thick row dp 3 = dims 70, 71 of tokens 32..47", 9, fill=C["ink"]))
    o.append(text(rx, 390, "64 B apart: pair_row_offsets [k_vnni.hpp:240-248]", 9,
                  fill=C["muted"]))
    _band_box(o, boxes, rx - 10, 402, 250, 52, "panel (s, c) (new)",
              ["16 pair rows x 64 B = 1 KiB: one AMX B tile"], "#fff", C["vnni"],
              "k_vnni.hpp:26-27, 70-73", size=11)
    o.append(arrow(fid, "vnni", [(rx + 30, 454), (rx + 30, 488)], C["vnni"], 1.4))
    o.append(lines(rx + 38, 464, ["1 panel -> STEP_PAIRS_16", "= 16 pair rows"], 9, 10,
                   fill=C["vnni"], weight=600))
    o.append(text(rx + 38, 485, "[k_vnni.hpp:66, 70]", 8.5, mono=True, fill=C["cite"]))
    _band_box(o, boxes, rx - 10, 490, 250, 52, "pair row dp (new)",
              ["64 B line: one dimension pair of 16 tokens"], "#fff", C["vnni"],
              "k_vnni.hpp:61-63, 68-69", size=11)
    o.append(arrow(fid, "vnni", [(rx, 542), (rx, 559), (gx - 20 + 256 + 6, 559)],
                   C["vnni"], 1.4))
    o.append(lines(rx + 8, 574, ["1 pair row -> BLOCK_TOKENS_16", "= 16 dwords, 1 per token"],
                   9.5, 12, fill=C["vnni"], weight=600))
    o.append(text(rx + 8, 599, "[k_vnni.hpp:61-63, 69]", 8.5, mono=True, fill=C["cite"]))
    # ---- bottom: the index map and the worked example -----------------------
    by = 640
    o.append(line(20, by - 8, 980, by - 8, C["line"]))
    o.append(rect(20, by, 960, 108, "#fff", C["ink"], 1.2, 5))
    o.append(text(30, by + 17, "k_vnni::index(token, dim)", 12, mono=True, weight=700))
    o.append(text(230, by + 17, "element index of K[token][dim] inside the plane (new)",
                  10.5, fill=C["muted"]))
    o.append(cite(976, by + 104, "k_vnni.hpp:97-106"))
    boxes.append(("k_vnni::index(token, dim)", "k_vnni.hpp:97-106"))
    o.append(lines(30, by + 34, [
        "s = dim / STEP_DIMS_32 ; c = token / BLOCK_TOKENS_16 ; dp = (dim % STEP_DIMS_32) / PAIR_2 ; t = token % BLOCK_TOKENS_16 ; j = dim % PAIR_2",
        "index = (((s * TOKEN_BLOCKS_4 + c) * STEP_PAIRS_16 + dp) * BLOCK_TOKENS_16 + t) * PAIR_2 + j",
    ], 10, 13, mono=True))
    o.append(text(30, by + 66, "worked example, token 37 and dimension 70:", 10.5,
                  weight=600, fill=C["vnni"]))
    o.append(lines(30, by + 80, [
        f"s = 70 / 32 = {EX['s']} ; c = 37 / 16 = {EX['c']} ; dp = (70 % 32) / 2 = {EX['dp']} ; "
        f"t = 37 % 16 = {EX['t']} ; j = 70 % 2 = {EX['j']}",
        f"index = (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2 + 0 = {EX['index']}   ->   byte "
        f"{EX['byte']} = panel #{EX['panel']} x 1024 + pair row {EX['dp']} x 64 + dword "
        f"{EX['t']} x 4 + j x 2",
    ], 10, 13, mono=True))
    cap = ("B1, data model. The top band is the containment. A book holds n_pages pages. "
           "A page reaches n_kv_heads kv_blocks per storage slot. A kv_block holds one K "
           "plane (k) and one V plane (v). "
           "A plane is K (the key matrix) for one KV head (key/value head) "
           "of one page (64 tokens of KV storage): 64 "
           "tokens x 128 dimensions of bf16 (16-bit floats) = 16 KiB, owned by "
           "k_vnni_tensor. It is 16 panels of 1 KiB, one per (dimension step s, token "
           "block c). A panel is 16 pair rows of 64 bytes, and a pair row holds one "
           "dimension pair for 16 tokens. The worked example traces token 37, dimension "
           "70 through k_vnni::index to element 5226 (panel #10, pair row 3, dword 5).")
    legend = [
        ("ctx_ink", "grey box, ink outline: the kv_cache.hpp containers book, page, "
                    "detail::kv_block and its member k"),
        ("ctx", "grey box, thin grey outline: detail::kv_block::v, the V plane, which "
                "this PR does not change"),
        ("vnni", "blue: the VNNI entities that own bytes: k_vnni_tensor<64, 128>, the "
                 "plane, panel (2,2) #10 in the grid, the 16 pair rows of the zoomed panel, "
                 "and dword 5 (token 37) of pair row 3; blue text = the VNNI how-many "
                 "labels and the worked example"),
        ("white box, blue outline: the VNNI entities panel (s, c) and pair row dp",
         "#fff", C["vnni"], False, False),
        ("box", "white box, ink outline: the data-model entities token block c, token i, "
                "dimension step s / pair dp, and the index map k_vnni::index; name in "
                "bold monospace, description in grey sans-serif"),
        ("lane", "white cell, thin grey outline: a panel of the grid other than (2,2) #10 "
                 "(the frame of block 2 is drawn over such cells), and a dword of pair "
                 "row 3 other than token 37's"),
        ("ink frame: block 2's column in the panel grid, pair row dp 3 of the zoomed "
         "panel (drawn heavier), and that panel's outline", "none", C["ink"], False, False),
        ("arrow", "ink arrow: a containment with its how-many (book -> pages, page -> "
                  "kv_blocks, kv_block -> planes, k -> owner, plane -> blocks, block -> "
                  "tokens, token -> steps, block 2 -> its 4 panels)"),
        ("blue arrow: a how-many inside the VNNI layout (owner -> 8192 bf16, plane -> "
         "16 panels, panel -> 16 pair rows, pair row -> 16 dwords)", "arrow", C["vnni"]),
        ("arrow_muted", "grey arrow: kv_block -> its V plane, context only"),
        ("font_mono", "monospace = a name or a value from the code: box titles, panel "
                      "indexes, dp rows, token numbers, the index formula and the worked "
                      "example"),
        ("font_sans", "sans-serif = the drawing titles (bold), the descriptions "
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
    W, H = 1000, 690
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    o.append(label_box(20, 24, 250, 80, "detail::kv_block::k", [
        "the owner for a VNNI slot (changed):",
        "k_storage = k_vnni_tensor<64, 128>",
        "copied whole by dst_block.k = src_block.k"],
        C["soft"], C["ink"], ref="kv_cache.hpp:2565-2575; 2338"))
    boxes.append(("detail::kv_block::k", "kv_cache.hpp:2565-2575; copy at 2338"))
    o.append(arrow(fid, "ink", [(270, 60), (326, 60)], C["ink"], 1.4))
    o.append(lines(298, 42, ["1 kv_block", "-> 1 K plane"], 8.5, 10, "middle", fill=C["ink"],
                   weight=600))
    ox, oy, ow, oh = 330, 24, 320, 96
    o.append(label_box(ox, oy, ow, oh, "k_vnni_tensor<Rows, Cols>", [
        "alignas(64) bf16 data_[Rows * Cols] = 16 KiB (new)",
        "trivial to construct, copy and destroy; no init",
        "as_view() & -> writable view, TRON(this_lifetimebound)",
        "as_view() const& -> read-only view;  && = delete"],
        C["vnni_fill"], C["vnni"], ref="k_vnni.hpp:155-185"))
    boxes.append(("k_vnni_tensor<Rows, Cols>", "k_vnni.hpp:155-185"))
    o.append(label_box(700, 24, 280, 80, "page::k_packed(slot, kv_head)", [
        "kv_block.k.as_view() on a const owner (new)",
        "-> k_vnni_view<const bf16, 64, 128>",
        "handed to k_vnni::qk_group"],
        C["soft"], C["ink"], ref="kv_cache.hpp:2041-2051"))
    boxes.append(("page::k_packed(slot, kv_head)", "kv_cache.hpp:2041-2051"))
    vy, vh = 190, 104
    o.append(arrow(fid, "vnni", [(ox + 80, oy + oh), (ox + 80, vy)], C["vnni"], 1.4))
    o.append(lines(ox + 88, 148, ["as_view() &: 1 call -> 1 view;",
                                  "TRON(this_lifetimebound)"], 9, 11,
                   fill=C["vnni"], weight=600))
    o.append(text(ox + 88, 170, "[k_vnni.hpp:163-167]", 8.5, mono=True, fill=C["cite"]))
    o.append(arrow(fid, "vnni", [(ox + ow - 20, oy + oh), (ox + ow - 20, 174), (760, 174),
                                 (760, vy)], C["vnni"], 1.4))
    o.append(lines(ox + ow - 12, 140, ["as_view() const&: 1 call ->", "1 read-only view"],
                   9, 11, fill=C["vnni"], weight=600))
    o.append(text(ox + ow - 12, 164, "[k_vnni.hpp:169-173]", 8.5, mono=True, fill=C["cite"]))
    o.append(arrow(fid, "ink", [(840, 104), (840, vy)], C["ink"], 1.4))
    o.append(lines(848, 130, ["1 (slot, kv_head) ->", "1 read-only view"], 9, 11,
                   fill=C["ink"], weight=600))
    o.append(label_box(ox, vy, 296, vh, "k_vnni_view<bf16, 64, 128>", [
        "the writable view (new): T* data_ (private)",
        "at(token, dim) reads; there is no element write",
        "no public pointer access: rows enter only",
        "through store_row and copy_token"],
        C["vnni_fill"], C["vnni"], 11.5, ref="k_vnni.hpp:119-153"))
    boxes.append(("k_vnni_view<bf16, 64, 128>", "k_vnni.hpp:119-153"))
    o.append(label_box(700, vy, 280, vh, "k_vnni_view<const bf16, 64, 128>", [
        "the read-only view (new): the same reads",
        "built from a writable view by the converting",
        "constructor; requires(is_const_v<T>): the",
        "reverse direction does not exist"],
        C["vnni_fill"], C["vnni"], 11.5, ref="k_vnni.hpp:119-153; 129-133"))
    boxes.append(("k_vnni_view<const bf16, 64, 128>",
                  "k_vnni.hpp:119-153 (T = const bf16); converting constructor 129-133"))
    o.append(arrow(fid, "vnni", [(ox + 300, 236), (696, 236)], C["vnni"], 1.4))
    o.append(lines(663, 208, ["1 writable ->", "1 read-only", "copies data_"], 8.5, 10,
                   "middle", fill=C["vnni"], weight=600))
    o.append(lines(663, 252, ["never the", "reverse"], 8.5, 10, "middle", fill=C["muted"],
                   weight=600))
    o.append(label_box(20, vy, 290, vh, "friend struct (of k_vnni_view)", [
        "k_vnni_tensor<Rows, Cols>: calls the private",
        "pointer constructor (as_view, 166 and 172)",
        "detail::k_vnni_access: reads data_ (192)",
        "k_vnni_view<U, R, C>: the converting ctor (133)",
        "so no bare pointer becomes a view outside"],
        "#fff", C["ink"], ref="k_vnni.hpp:143-146"))
    boxes.append(("friend struct (of k_vnni_view)", "k_vnni.hpp:143-146"))
    o.append(arrow(fid, "muted", [(310, vy + 30), (ox - 4, vy + 30)], C["muted"], 1.2,
                   "4 3"))
    o.append(label_box(20, 316, 290, 60, "concept k_vnni_element<T>", [
        "T is bf16 or const bf16, nothing else;",
        "checked by the static_assert at 124"],
        "#fff", C["ink"], ref="k_vnni.hpp:116-117"))
    boxes.append(("concept k_vnni_element<T>", "k_vnni.hpp:116-117"))
    o.append(arrow(fid, "muted", [(310, 340), (320, 340), (320, vy + vh - 20),
                                  (ox - 4, vy + vh - 20)], C["muted"], 1.2, "4 3"))
    ay, ah = 340, 58
    o.append(arrow(fid, "ink", [(ox + 160, vy + vh), (ox + 160, ay)], C["ink"], 1.4))
    o.append(text(ox + 168, 320, "1 view -> 1 T* (the plane's first element)", 9,
                  fill=C["ink"], weight=600))
    o.append(card_arrow(fid, "ink", [(840, vy + vh), (840, ay + ah / 2), (ox + 404, ay + ah / 2)],
                        C["ink"], "1 view -> 1 T*", label_dx=8, label_dy=-2, size=9,
                        anchor="start"))
    o.append(text(848, ay - 2, "[k_vnni.hpp:189-193]", 8.5, mono=True, fill=C["cite"]))
    o.append(label_box(ox + 40, ay, 360, ah, "detail::k_vnni_access::plane(view) -> T*", [
        "the one route from a packed K view to its address (new)",
        "its users are listed in Note [K VNNI storage]"],
        "#fff", C["ink"], ref="k_vnni.hpp:187-195"))
    boxes.append(("detail::k_vnni_access::plane(view)", "k_vnni.hpp:187-195"))
    cy = 436
    bus_y = cy - 10
    o.append(line(ox + 220, ay + ah, ox + 220, bus_y, C["ink"], 1.4))
    o.append(text(20, ay + ah + 14, "who may take the address: the three callers below "
                  "[k_vnni.hpp:31-37; kv_cache.hpp:701-703]", 9, fill=C["muted"]))
    cons = [
        ("the typed operations in this header", ["store_row 259, load_row 276",
                                                 "(copy_token goes through them)"],
         "k_vnni.hpp:31-33, 251-297"),
        ("k_vnni::qk_group", ["the AVX-512 score reader", "(kernels/k_vnni.hpp:56)"],
         "kernels/k_vnni.hpp:34, 56"),
        ("book::fill_storage_slot", ["test-only fill_random body:",
                                     "the documented exception (1773)"],
         "kv_cache.hpp:1767, 1772-1773"),
    ]
    cx = 20
    centres = [cx + i * 326 + 150 for i in range(len(cons))]
    o.append(line(centres[0], bus_y, centres[-1], bus_y, C["ink"], 1.4))
    for c in centres:
        o.append(arrow(fid, "ink", [(c, bus_y), (c, cy - 1)], C["ink"], 1.4))
    for name, sub, ref in cons:
        o.append(label_box(cx, cy, 300, 62, name, sub, C["soft"], C["ink"], 10.5, ref=ref))
        boxes.append((name, ref))
        cx += 326
    ty = 536
    o.append(line(20, ty - 12, 980, ty - 12, C["line"]))
    o.append(text(20, ty, "transfer rows: one token's Cols bf16 in dimension order, "
                  "not packed storage (new)", 11, weight=700))
    o.append(label_box(20, ty + 10, 310, 90, "const_k_row_view<Cols, Aligned, Dma>", [
        "const_view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "built by k_source_row(const bf16*) or",
        "k_source_row(stride-1 bf16 view): keeps its flags",
        "the source of store_row and page::set_k_row"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:200-201, 206-218"))
    boxes.append(("const_k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:200-201, 206-218"))
    o.append(label_box(345, ty + 10, 310, 90, "k_row_view<Cols, Aligned, Dma>", [
        "view<bf16, Aligned, Dma, seq<Cols>, sseq<1>>",
        "built by k_destination_row(bf16*)",
        "the destination of load_row and",
        "page::get_k_row"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:203-204, 220-224"))
    boxes.append(("k_row_view<Cols, Aligned, Dma>", "k_vnni.hpp:203-204, 220-224"))
    o.append(label_box(670, ty + 10, 310, 90, "Aligned, Dma flags", [
        "defaults true, false (the bare literals);",
        "Aligned is not a precondition: store_row and",
        "load_row use unaligned loads and stores",
        "(unlike the packed V rows)"],
        "#fff", C["ink"], 11, ref="k_vnni.hpp:197-204"))
    boxes.append(("Aligned, Dma flags", "k_vnni.hpp:197-204"))
    o.append(text(20, ty + 124, "1 row = Cols = 128 bf16 = 256 bytes; it travels with "
                  "the caller's flags [k_vnni.hpp:197-201]", 9.5, fill=C["muted"]))
    cap = ("B2, type model. k_vnni_tensor owns the 16 KiB plane. Its as_view() is the only "
           "source of a k_vnni_view. A writable view converts to a read-only one, never "
           "back (grey text: a route the code does not provide). "
           "detail::k_vnni_access::plane is the one route from a view to the "
           "raw address, open to the typed operations of this file, the score reader "
           "k_vnni::qk_group and the test-only fill. The transfer rows const_k_row_view / "
           "k_row_view carry one token's 128 values in dimension order with the caller's "
           "alignment and DMA (direct memory access) flags.")
    legend = [
        ("vnni", "blue: the owner k_vnni_tensor<Rows, Cols> and its views "
                 "k_vnni_view<bf16, 64, 128> (writable) and k_vnni_view<const bf16, 64, 128> "
                 "(read-only); blue text = the how-many of as_view() and the conversion"),
        ("ctx_ink", "grey box, ink outline: the code outside this type model that holds "
                    "or takes the plane: detail::kv_block::k and page::k_packed in "
                    "kv_cache.hpp, and the three takers of the raw address under "
                    "k_vnni_access::plane"),
        ("box", "white box, ink outline: friend struct, concept k_vnni_element<T>, "
                "detail::k_vnni_access::plane, and the transfer rows const_k_row_view / "
                "k_row_view with their Aligned, Dma flags; name in bold monospace, "
                "description in grey sans-serif"),
        ("arrow", "ink arrow: a containment or a route with its how-many (kv_block -> "
                  "plane, k_packed -> read-only view, view -> T*, plane() -> its three "
                  "callers)"),
        ("blue arrow: as_view(), 1 call -> 1 view (owner -> writable or read-only "
         "view), and the writable -> read-only conversion", "arrow", C["vnni"]),
        ("arrow_muted", "grey dashed arrow: the friend declarations and the concept that "
                        "constrain k_vnni_view (a constraint, not a call); grey text "
                        "'never the reverse' = a conversion the code does not provide"),
        ("font_mono", "monospace = the box titles (the holder, the owner, the accessor, "
                      "the two views, friend struct, concept k_vnni_element<T>, "
                      "plane(view), the three callers, the two transfer rows and the "
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
          cx0=245, cw_total=740, cell_h=62, callers_h=84):
    """One group of operations: header, the callers box at the left, the
    function cells and their callees under them. Returns the next y."""
    o.append(band_header(cx0, y, header))
    y += 6
    n = len(cells)
    gap = 6
    cw = (cw_total - gap * (n - 1)) / n
    o.append(callers_box(20, y, 212, callers_h, callers, callers_ref))
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
    return y + max(cell_h + 38, callers_h + 14)


def b3():
    fid = "k_vnni-b3"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 18, "callers in other files", 11, weight=700, fill=C["muted"]))
    o.append(text(245, 18, "the operations of k_vnni.hpp by purpose; a cell = name, what it "
                  "does, its definition (all new in this PR)", 10, fill=C["muted"]))
    o.append(text(245, 30, "under a cell: what it calls, expands to, or who reads it", 10,
                  fill=C["muted"]))
    y = 42
    y = _band(o, boxes, fid, y, "index map and the layout gate (lines 56-108)", [
        "kv_cache.hpp: kv_block::k_storage 2566,",
        "page::k requires 1978-2033, k_view 2593,",
        "k_packed 2045, set_k_row 2062, get_k_row",
        "2079, copy_storage_slot 2331, fill 1772",
        "self_attention.hpp: apply_page_tok",
        "1886, 1909; model.hpp: save_k_impl 3100",
        "full.hpp: k_head_fn 2751"], "kv_cache.hpp:2561, 1880", [
        ("kv_block::k_storage (caller)", "kv_cache.hpp:2566-2568"),
        ("page::k (caller)", "kv_cache.hpp:1977-1978"),
        ("page::k_packed (caller)", "kv_cache.hpp:2047"),
        ("page::set_k_row (caller)", "kv_cache.hpp:2057"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2074"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2325"),
        ("book::fill_storage_slot (caller)", "kv_cache.hpp:1767"),
        ("apply_page_tok (caller)", "self_attention.hpp:1834"),
        ("save_k_impl (caller)", "model.hpp:3074"),
        ("page_info::k_head_fn (caller)", "full.hpp:2747")], [
        ("layout_on<head_size>", ["The layout gate: TRON_K_VNNI", "and 128-dimension heads"],
         "k_vnni.hpp:86-95"),
        ("index(token, dim)", ["Element index of K[token][dim]", "inside the plane"],
         "k_vnni.hpp:97-106"),
    ], [["constexpr bool, no call"], ["read by k_vnni_view::at (139)"]])
    y = _band(o, boxes, fid, y, "owner, views and the one access route (lines 110-195)", [
        "kv_cache.hpp: k_packed 2050 (const&),",
        "set_k_row 2063, get_k_row 2080,",
        "copy_storage_slot 2338, 2341,",
        "fill_storage_slot 1773",
        "kernels/k_vnni.hpp: qk_group 56",
        "(k_vnni_access::plane)"], "kv_cache.hpp:2047, 2057, 2074, 2325, 1767", [
        ("page::k_packed (caller)", "kv_cache.hpp:2047"),
        ("page::set_k_row (caller)", "kv_cache.hpp:2057"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2074"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2325"),
        ("book::fill_storage_slot (caller)", "kv_cache.hpp:1767"),
        ("k_vnni::qk_group (caller)", "kernels/k_vnni.hpp:34")], [
        ("k_vnni_tensor::as_view", ["& writable, const& read-only;", "on a temporary: deleted"],
         "k_vnni.hpp:163-176"),
        ("k_vnni_view::at", ["Bounds-checked read of element", "(token, dim); no element write"],
         "k_vnni.hpp:135-140"),
        ("k_vnni_view(other)", ["Writable -> read-only view", "conversion, never the reverse"],
         "k_vnni.hpp:129-133"),
        ("k_vnni_access::plane", ["The view's plane address:", "the one route to the bytes"],
         "k_vnni.hpp:189-193"),
    ], [["-> k_vnni_view(T*) (private)"], ["-> k_vnni::index, TRON_ASSERT_LT"],
        ["copies data_ (friend view)"], ["-> k.data_ (friend)"]])
    y = _band(o, boxes, fid, y, "transfer rows and their builders (lines 197-224)", [
        "model.hpp: save_k_impl 3105 (the view",
        "overload, k_source_row(kout)) and",
        "3109-3111 (k_destination_row(row), then",
        "the pointer overload of k_source_row)",
        "full.hpp: k_head_fn 2755",
        "(k_destination_row(dest) -> get_k_row)",
        "tests: t_k_vnni_layout.cpp 67, 149"], "model.hpp:3074; full.hpp:2747", [
        ("save_k_impl (caller)", "model.hpp:3074"),
        ("page_info::k_head_fn (caller)", "full.hpp:2747"),
        ("row_of (test caller)", "t_k_vnni_layout.cpp:66-68")], [
        ("k_source_row", ["Read-only transfer row from a const bf16* or a stride-1",
                          "bf16 view that keeps its flags; no check, no copy"],
         "k_vnni.hpp:206-218"),
        ("k_destination_row", ["Writable transfer row from a bf16*; the flags state",
                               "what the caller knows about its buffer; no copy"],
         "k_vnni.hpp:220-224"),
    ], [["-> const_k_row_view<Cols, Aligned, Dma>{row}",
         "in-file caller: copy_token 296"],
        ["-> k_row_view<Cols, Aligned, Dma>{row}",
         "in-file caller: copy_token 295"]])
    y = _band(o, boxes, fid, y, "internal helpers, namespace k_vnni::detail (lines 226-249)", [
        "no caller outside this file:",
        "store_row 261, 264 and",
        "load_row 278, 281",
        "(pair_row_offsets once per row,",
        "pair_base once per step s)"], "k_vnni.hpp:255, 272", [
        ("store_row (in-file caller)", "k_vnni.hpp:255-257"),
        ("load_row (in-file caller)", "k_vnni.hpp:272-274")], [
        ("pair_base", ["Byte address of dimension pair 0 of", "step s for a token: panel (s, c), dword t"],
         "k_vnni.hpp:227-239"),
        ("pair_row_offsets", ["Dword offsets of the 16 pair rows of", "one panel (64 bytes = 16 dwords apart)"],
         "k_vnni.hpp:240-248"),
    ], [["two overloads: bf16*, const bf16*"], ["-> _mm512_set_epi32"]])
    y = _band(o, boxes, fid, y, "one token's row into and out of the plane (lines 251-297)", [
        "kv_cache.hpp: set_k_row 2063 (store_row)",
        "get_k_row 2080 (load_row),",
        "copy_storage_slot 2341 (copy_token)",
        "tests: t_k_vnni_layout.cpp 77, 124, 148,",
        "174; t_phase1_integration.cpp 869"], "kv_cache.hpp:2057, 2074, 2325", [
        ("page::set_k_row (caller)", "kv_cache.hpp:2057"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2074"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2325"),
        ("copy_token call of the layout test", "t_k_vnni_layout.cpp:174")], [
        ("store_row", ["One token's row in: 4 scatters", "of 16 dwords, 64 pair slots"],
         "k_vnni.hpp:251-267"),
        ("load_row", ["One token's row out: 4 gathers", "of 16 dwords (the inverse)"],
         "k_vnni.hpp:269-284"),
        ("copy_token", ["One token between planes via a", "local row: load_row, store_row"],
         "k_vnni.hpp:286-297"),
    ], [["-> k_vnni_access::plane,", "pair_row_offsets, pair_base"],
        ["-> k_vnni_access::plane,", "pair_row_offsets, pair_base"],
        ["-> load_row, store_row,", "k_destination_row, k_source_row"]])
    H = int(y) + 4
    cap = ("B3, function model. Every operation of k_vnni.hpp as a cell: its name, one "
           "line on what it does, and the lines that define it. All are new in this PR. "
           "The grey box at the left of each group names the callers in other files with "
           "their call-site lines; its citation and the register give the lines that "
           "define those callers. The small text under a cell names what the cell calls, "
           "expands to, or who reads it. "
           "The page accessors of kv_cache.hpp (set_k_row, get_k_row, k_packed, "
           "copy_storage_slot) are the main callers.")
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
        ("font_tag", "bold 'new' = the operation is added by PR 4956 (every cell)"),
    ]
    return figure(fid, W, H, "Function model: every operation of the file, its callers and callees",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B4: the bytes of one token's row through the operations


def b4_legend(x, y):
    o = []
    row1 = [("vnni", "VNNI pair rows (64 B lines)"),
            ("empty", "column of a token with no row saved")]
    cx = x
    for st, lab in row1:
        if st == "empty":
            o.append(rect(cx, y, 22, 12, C["empty_fill"], C["empty"], 1, 1, "3 2"))
        else:
            o.append(rect(cx, y, 22, 12, C[st + "_fill"], C[st], 1, 1))
        o.append(text(cx + 28, y + 10, lab, 10))
        cx += 28 + text_width(lab, 10) + 18
    o.append(rect(cx, y, 6, 12, C["vnni"], C["ink"], 1, 0))
    o.append(text(cx + 12, y + 10, "column t = 5 (token 37), written (4 B per line)", 10))
    cx += 12 + text_width("column t = 5 (token 37), written (4 B per line)", 10) + 18
    o.append(rect(cx, y, 6, 12, "none", C["ink"], 1.2, 0, "2 2"))
    o.append(text(cx + 12, y + 10, "dashed: read", 10))
    cx += 12 + text_width("dashed: read", 10) + 18
    o.append(rect(cx, y, 22, 12, "#fff", C["ink"], 1.6, 1))
    o.append(text(cx + 28, y + 10, "thick: pair row 3", 10))
    return "".join(o)


def b4():
    fid = "k_vnni-b4"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 20, "worked example: block 2 (tokens 32..47) of the plane of slot 5, "
                  "KV head 0, page 7; its bytes are the 4 panels (s, 2) = 4 KiB", 11,
                  weight=700))
    o.append(text(20, 36, "each panel: 16 pair rows of 64 bytes, drawn top to bottom; the "
                  "steps are in the order of one forward pass, not to scale", 9.5,
                  fill=C["muted"]))
    o.append(b4_legend(20, 48))
    px0, pw, ph, pg = 300, 118, 72, 14
    step_h = 142
    y = 84
    not_saved = list(range(9, 16))          # tokens 41..47 of block 2: no row saved yet
    steps = [
        dict(n="1", title="store_row(plane, 37, src)",
             sub=["save_k -> page::set_k_row: 4 scatters of 16",
                  "dwords, one per step s, into dword 5 of all",
                  "64 lines [model.hpp:3104; kv_cache.hpp:2063]"],
             fill=C["vnni_fill"], stroke=C["vnni"], ref="k_vnni.hpp:251-267",
             kw=dict(col=EX["t"], cols_empty=not_saved),
             note=["state after rows 32..40 were saved this way: 9 columns written (tokens "
                   "32..40), 7 columns (41..47) hold no row yet",
                   "only this token's 64 pair slots (4 bytes in each of the 64 lines) are "
                   "written; pair_base(plane, s, 37) + pair_row_offsets address them",
                   "tokens are written independently: no read-modify-write between tokens "
                   "[k_vnni.hpp:27-29, 251-252]"]),
        dict(n="2", title="qk_group(k_packed, q, live, s, 64)",
             sub=["the score reader reads block 2's 64 pair rows",
                  "with mask 0x01ff (tokens 32..40 live), one",
                  "token per lane [kernels/k_vnni.hpp:57-69]"],
             fill=C["q_fill"], stroke=C["q"], ref="kernels/k_vnni.hpp:34-38, 56-69",
             kw=dict(hi_rows=[EX["dp"]], cols_live=BLOCK_MASKS[2]),
             note=["an attention worker, apply_page_tok: the loop marks offsets 0..40 in `live`, "
                   "then one qk_group call scores them [self_attention.hpp:1953-1971]"[:0] + "an attention worker (apply_page_tok) marks offsets 0..40 live, then one "
                   "qk_group call scores them [self_attention.hpp:1953-1971]",
                   "a masked load never reads the column of a token whose bit is clear "
                   "(tokens 41..47): unwritten tokens cannot change the result",
                   "[kernels/k_vnni.hpp:26-27]; one 64-byte load = one dimension pair of 16 "
                   "tokens; 64 loads per block, no per-token gather"]),
        dict(n="3", title="load_row(plane, 37, dst)",
             sub=["the inverse: 4 gathers of 16 dwords out of",
                  "the same 64 slots into a 256 B transfer row",
                  "[page::get_k_row kv_cache.hpp:2080]"],
             fill="#fff", stroke=C["vnni"], ref="k_vnni.hpp:269-284",
             kw=dict(col=EX["t"], col_read=True, cols_empty=not_saved),
             note=["the FPGA staging of GOF 36..39: k_head_fn gathers token 37's row into "
                   "k_scratch and returns it [full.hpp:2751-2756; gof.cpp:211]",
                   "reads 64 lines for one token; the staging bytes and the HBM layout are "
                   "unchanged [kv_cache.hpp:728-732]",
                   "a row-major slot returns the row in place instead (page::k, "
                   "full.hpp:2758)"]),
        dict(n="4", title="copy_token(dst, 37, src, 37)",
             sub=["a page copy of 41 tokens, page 7 -> page 9:",
                  "load_row from the source column, store_row",
                  "into the destination column, via a local row"],
             fill=C["vnni_fill"], stroke=C["vnni"], ref="k_vnni.hpp:286-297",
             kw=dict(col=EX["t"], cols_empty=not_saved),
             note=["copy_storage_slot: a token's column depends on its offset in the page, "
                   "so only a whole page copies as one owner assignment",
                   "(dst_block.k = src_block.k, count == 64); any other range goes token by "
                   "token [kv_cache.hpp:2331-2344]",
                   "drawn: the destination block 2 of page 9 after the copy, the same 9 "
                   "columns written, 7 untouched"]),
    ]
    for st in steps:
        o.append(text(20, y + 10, st["n"], 13, weight=700))
        for s in st["sub"]:
            _w(s, 9.5, 242, where=f"b4 sub {st['title']}")
        o.append(label_box(36, y - 2, 250, 80, st["title"], st["sub"], st["fill"],
                           st["stroke"], 10.5, ref=st["ref"]))
        boxes.append((st["title"], st["ref"]))
        for s in range(4):
            x = px0 + s * (pw + pg)
            o.append(text(x + pw / 2, y + 2, f"panel ({s},2) #{4 * s + 2}", 9, "middle",
                          True, fill=C["muted"]))
            kw = dict(st["kw"])
            if "hi_rows" in kw and s != EX["s"]:
                kw.pop("hi_rows")
            o.append(panel_lines(x, y + 7, pw, ph, ["vnni"] * 16, **kw))
        for i, s in enumerate(st["note"]):
            _w(s, 9.5 if i == 0 else 9, 680, where=f"b4 note {st['title']}")
        o.append(text(px0, y + ph + 20, st["note"][0], 9.5, fill=C["ink"]))
        o.append(lines(px0, y + ph + 32, st["note"][1:], 9, 11, fill=C["muted"]))
        y += step_h
    H = int(y) - 4
    cap = ("B4, sequencing model: the bytes of block 2 of the worked example through the "
           "operations of one forward pass. Each row shows the block's 4 panels (4 KiB) "
           "after one operation. store_row writes 4 bytes into every one of the 64 pair "
           "rows for one token (its column). k_vnni::qk_group reads the pair rows with a "
           "16-bit mask (one token per lane) and never touches the columns of tokens "
           "that are not live. load_row gathers one column back into a row. copy_token "
           "moves one column between planes. Look at the 7 grey columns: no operation of "
           "this PR reads or writes a token's bytes before its row is saved.")
    legend = [
        ("vnni", "blue: a VNNI pair row, 64 B, of block 2 (every step); also the step boxes "
                 "store_row and copy_token"),
        ("empty", "grey dashed column: a token whose K row is not saved yet (tokens 41..47), "
                  "bytes undefined, never read"),
        ("q", "purple box: step 2, qk_group, the score reader of the query side"),
        ("white box, blue outline: step 3, load_row(plane, 37, dst), a read of the plane",
         "#fff", C["vnni"], False, False),
        ("solid blue column, ink outline: dword t = 5 (token 37) written by store_row or "
         "copy_token, 4 B in each of the 64 lines", C["vnni"], C["ink"], False, False),
        ("ink outline: a panel's frame; drawn heavier, pair row 3 of panel (2,2) in step 2",
         "none", C["ink"], False, False),
        ("dashed ink outline: a read: token 37's column in load_row, and the 9 live "
         "columns of each panel in qk_group", "none", C["ink"], True, False),
        ("box", "white chip, ink outline, in the key at the top: stands for the heavier "
                "outline of pair row 3"),
        ("font_mono", "monospace = an operation call in a step box, and the panel "
                      "labels (s,2) #n"),
        ("font_sans", "sans-serif = the worked example's header, the key, the step "
                      "numbers 1 to 4 (bold), what a step does, and the notes under the "
                      "panels"),
        ("font_cite", "small grey monospace = the lines that define a step's operation "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Sequencing model: the bytes of one token's row through the operations",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B5: interaction model (who calls which operation from which thread)

B5_COLUMNS = [(165, 425, "save_k of one layer", "model.hpp:3074-3118"),
              (435, 695, "scoring and staging of the pass", "self_attention.hpp:1834; gof.cpp:186"),
              (705, 835, "forward end", "model.hpp:1836, 3244"),
              (845, 980, "page copies", "kv_cache.hpp:733-736")]


def b5():
    fid = "k_vnni-b5"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    for x0, x1, name, ref in B5_COLUMNS:
        o.append(rect(x0, 12, x1 - x0, 26, C["soft"], C["line"], 1, 3))
        o.append(text((x0 + x1) / 2, 24, name, 9.5, "middle", weight=600))
        o.append(text((x0 + x1) / 2, 35, ref, 8.5, "middle", True, fill=C["cite"]))
    lanes_ = [("the thread of save_k", "model.hpp", 96),
              ("attention workers", "self_attention.hpp", 110),
              ("GOF staging", "workers | main", 100),
              ("page copies", "book append, defrag", 90),
              ("tests", "t_k_vnni_layout.cpp", 70)]
    ly = 46
    lane_y = {}
    for name, sub, h in lanes_:
        svg, _ = lane(20, ly, 960, h, name, sub)
        o.append(svg)
        lane_y[name] = (ly, h)
        ly += h + 4
    y, h = lane_y["the thread of save_k"]
    o.append(lane_block(165, y + 6, 260, 84, [
        "save_k_impl: for every token job and KV head,",
        "set_k_row(slot, kv_head, j, k_source_row(kout))",
        "-> store_row: 4 scatters into the token's column;",
        "a non-bf16 activation is converted to a bf16 row",
        "first; then mark_k_complete(slot, j)",
        "(TRON_AMX_DISABLE leaves the store untouched)"],
        C["vnni_fill"], C["vnni"], "model.hpp:3088-3118; kv_cache.hpp:713-717", size=9))
    boxes.append(("save_k_impl -> set_k_row -> store_row", "model.hpp:3074, 3100-3111"))
    y, h = lane_y["attention workers"]
    o.append(lane_block(165, y + 6, 260, 40, [
        "a page is read only after its K and V rows are",
        "complete (is_kv_complete); not changed by this PR"],
        "#fff", C["ink"], "full.hpp:2744-2746", idle=True, size=9))
    boxes.append(("attention worker: waits for a complete page (is_kv_complete)", "full.hpp:2744-2746"))
    o.append(lane_block(435, y + 6, 260, 98, [
        "apply_page_tok, per page of a VNNI slot:",
        "the dense AMX path is not compiled (1884-1886);",
        "the loop marks every relevant offset in `live`",
        "(1953-1954); then one call",
        "qk_group<kv_mul>(page.k_packed(slot, kv_head),",
        "q, live, s_pages, 64) scores them (1963-1971);",
        "reads only through the read-only view k_packed",
        "(as_view() const&)"],
        C["q_fill"], C["q"], "self_attention.hpp:1834, 1884-1971", size=9))
    boxes.append(("apply_page_tok -> live -> qk_group(k_packed)",
                  "self_attention.hpp:1834, 1909, 1953-1954, 1963-1971"))
    y, h = lane_y["GOF staging"]
    o.append(lane_block(435, y + 6, 260, 88, [
        "gof::populate -> page_info::k_head_fn(slot, h,",
        "k_scratch + h * HW_BAKED_HEAD_SIZE): the",
        "scheduler's callback runs get_k_row -> load_row",
        "into the scratch row and returns it (a row-major",
        "slot returns the row in place: page::k)",
        "[run by idle attention workers: help_drain_gof;",
        "or by main: wait_for_coop_gof]"],
        C["hw_fill"], C["hw"], "gof.cpp:201-211; full.hpp:2747-2760", size=9))
    boxes.append(("gof::populate -> k_head_fn -> get_k_row -> load_row",
                  "gof.cpp:186, 201-211; full.hpp:2747-2760; model.hpp:1164-1166, 3231, 3244"))
    o.append(lane_block(705, y + 6, 130, 58, [
        "wait_for_coop_gof:",
        "main drains the",
        "remaining staging",
        "work at forward end"],
        C["hw_fill"], C["hw"], "model.hpp:1836, 3244", size=9))
    boxes.append(("wait_for_coop_gof", "model.hpp:1836, 3244"))
    y, h = lane_y["page copies"]
    o.append(lane_block(845, y + 6, 135, 78, [
        "copy_from (2364) ->",
        "copy_storage_slot:",
        "whole page: dst_block.k",
        "= src_block.k; else",
        "copy_token per token",
        "(load_row, store_row)"],
        C["vnni_fill"], C["vnni"], "kv_cache.hpp:2331-2344", size=9))
    boxes.append(("copy_from -> copy_storage_slot -> copy_token | owner assignment",
                  "kv_cache.hpp:2364, 2325, 2331-2344"))
    o.append(lane_block(165, y + 6, 530, 40, [
        "clear_kv_complete_at (a new token takes an offset) changes no K bytes: the next",
        "save_k overwrites the token's column; no conversion and no K layout state exist in this PR"],
        "#fff", C["ink"], "kv_cache.hpp:2230; k_vnni.hpp:27-29", idle=True, size=9))
    boxes.append(("clear_kv_complete_at: no K bytes change", "kv_cache.hpp:2230"))
    y, h = lane_y["tests"]
    o.append(lane_block(165, y + 6, 530, 58, [
        "t_k_vnni_layout.cpp: index anchors (90-104); store_row, at, load_row, copy_token (106-195);",
        "qk_group against the row-major dotter, 4 / 20 / 32 query heads (301-316);",
        "page set_k_row / get_k_row and append (353-437); t_phase1_integration.cpp 869: store_row"],
        C["soft"], C["line"], "t_k_vnni_layout.cpp:90, 106, 301, 353", size=9))
    boxes.append(("TEST_CASE blocks of t_k_vnni_layout.cpp", "t_k_vnni_layout.cpp:90, 106, 301, 353"))
    ry = ly + 4
    o.append(text(20, ry + 12, "rules, each cited from the comment that states it",
                  11, weight=700))
    rules = [
        ("R1", ["tokens are written independently: token i owns column (i % 16) of its "
                "block in every panel, so there is no read-modify-write between tokens"],
         "k_vnni.hpp:27-29; 251-252"),
        ("R2", ["the reader never reads the K storage of a token whose live bit is clear "
                "(masked loads), so unwritten tokens cannot change the result"],
         "kernels/k_vnni.hpp:25-27"),
        ("R3", ["every reader and writer of a slot sees the same layout: the gate depends "
                "on the head size only, not on the query type or on AMX availability"],
         "k_vnni.hpp:86-88; kv_cache.hpp:690-694"),
        ("R4", ["the dense AMX page path is not compiled for a VNNI slot; every page of a "
                "VNNI slot takes the software path, until the VNNI AMX kernel lands (PR 4957)"],
         "kv_cache.hpp:718-720; self_attention.hpp:1882-1886"),
        ("R5", ["the FPGA staging needs one row per token, so k_head_fn materializes it "
                "with get_k_row into caller-owned scratch; the staging bytes are unchanged"],
         "kv_cache.hpp:728-732; gof.hpp:61-67"),
        ("R6", ["the kill switch keeps the layout: with TRON_AMX_DISABLE=1 a TRON_K_VNNI "
                "binary runs the AVX-512 VNNI reader, not the row-major dotter"],
         "kv_cache.hpp:740-746"),
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
    cap = ("B5, interaction model. One lane per kind of thread or caller, left to right "
           "in the order of one forward pass (schematic, not to scale). The thread that "
           "runs save_k stores every token's row with set_k_row -> store_row. The "
           "attention workers only read: apply_page_tok collects the live tokens of a "
           "page and calls k_vnni::qk_group once on the read-only view k_packed. The GOF "
           "staging (the copy of K/V rows for the FPGA, a group of four tokens) also only "
           "reads: it has no thread of its own, idle attention workers run it through "
           "help_drain_gof and main runs the rest through wait_for_coop_gof; its callback "
           "gathers one row with get_k_row -> load_row. Page copies (append and defrag) "
           "move a whole page as one owner assignment and any other range token by token. "
           "The yellow blocks are the staging path, drawn in the hardware attention "
           "colour. R1 to R6 cite the comment that states each rule.")
    legend = [
        ("vnni", "blue: a writer of the plane: save_k_impl -> set_k_row -> store_row, and "
                 "copy_from -> copy_storage_slot (copy_token or the owner assignment)"),
        ("q", "purple: the attention workers' scoring, apply_page_tok -> live -> "
              "qk_group(k_packed)"),
        ("hw", "yellow: the FPGA staging path, gof::populate -> k_head_fn -> get_k_row (an "
               "attention worker or main) and main's wait_for_coop_gof"),
        ("ctx", "grey box, thin grey outline: a phase header of the top row, with the "
                "lines that bound the phase; and the tests block"),
        ("lane", "white frame, thin grey outline: one lane; its name at the left "
                 "in bold, its file or role under it in grey"),
        ("idle", "dashed outline: a thread waits or a step changes no K bytes: the "
                 "attention workers before a page is complete, and clear_kv_complete_at"),
        ("font_mono", "bold monospace = the rule tags R1 to R6"),
        ("font_sans", "sans-serif = the lane and phase names, what each block does, "
                      "and the rules"),
        ("font_cite", "small grey monospace = the lines that define a block, a phase "
                      "or a rule (file:line)"),
    ]
    return figure(fid, W, H, "Interaction model: who calls which operation from which thread",
                  "".join(o), cap, boxes=boxes, legend=legend)
