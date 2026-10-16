"""Base diagrams B1-B5 of the PR 4958 page for h/tron/tensor/k_vnni.hpp.

Adapted from exec/pr4956-diagrams-20261015/figs/base_k_vnni.py (the plane
geometry and the building blocks) and exec/pr4424-diagrams-20261009/figs/
d_k_vnni_k7.py (the register grids). Every fact drawn here comes from the
head file (PR 4958 head b39765ec29) or from the cited caller files of the
same head. Line numbers are head line numbers of h/tron/tensor/k_vnni.hpp
unless another file is named.

Module-level constants and building blocks (imported by the change diagrams):
  EX, UNITS, PRESENT_FULL, PRESENT_UNIT2, ABSENT_UNIT2, index_of,
  transpose_sim, STAGES, TRACK, _w, panel_grid, panel_lines, pair_row_dwords,
  block_panels, dword_grid, present_bits, lane_block, callers_box, nx_box
"""
import sys

from svg_helpers import (C, arrow, bit_row, card_arrow, cite, figure, fn_cell, label_box,
                         lane, line, lines, marker_defs, rect, text, text_width)

# ---------------------------------------------------------------------------
# The worked example of the page (STYLE.md): one prefill pass of 41 items at
# page 7 offsets 0..40, storage slot 5, KV head 0, shared by 3 workers.
# unit_start = [0, 16, 32, 41]; unit 0 = block 0 (present 0xffff), unit 1 =
# block 1 (0xffff), unit 2 = block 2 (offsets 32..40, present 0x01ff).
# Token 37 = block 2, lane t = 5; dimension 70 = step s = 2, pair dp = 3, j = 0.
PRESENT_FULL = 0xffff
PRESENT_UNIT2 = 0x01ff
ABSENT_UNIT2 = [t for t in range(16) if not (PRESENT_UNIT2 >> t) & 1]   # lanes 9..15
UNITS = [(0, 16, 0, PRESENT_FULL), (16, 32, 1, PRESENT_FULL), (32, 41, 2, PRESENT_UNIT2)]


def index_of(token, dim):
    """k_vnni::index (k_vnni.hpp:107-114) and its five coordinates."""
    s, c = dim // 32, token // 16
    dp, t, j = (dim % 32) // 2, token % 16, dim % 2
    return dict(s=s, c=c, dp=dp, t=t, j=j,
                index=(((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j,
                panel=s * 4 + c)


EX = dict(token=37, dim=70)
EX.update(index_of(EX["token"], EX["dim"]))          # s=2 c=2 dp=3 t=5 j=0, index 5226
EX["byte"] = EX["index"] * 2                           # 10452
assert EX["index"] == 5226 and EX["panel"] == 10 and EX["t"] == 5 and EX["dp"] == 3
assert ABSENT_UNIT2 == list(range(9, 16))


# ---------------------------------------------------------------------------
# A simulation of transpose_16x16_epi32 (k_vnni.hpp:261-287) on 16 registers
# of 16 dword lanes. A register is a list of 16 cells; a cell is the pair
# (input register, input lane) it came from. The four stages follow the code
# line by line; STAGES holds the state after each stage and TRACK the place of
# the worked example's dword (input register t = 5, lane dp = 3) after each.
def _unpacklo32(a, b):
    return [x for q in range(4) for x in (a[4 * q], b[4 * q], a[4 * q + 1], b[4 * q + 1])]


def _unpackhi32(a, b):
    return [x for q in range(4) for x in (a[4 * q + 2], b[4 * q + 2], a[4 * q + 3], b[4 * q + 3])]


def _unpacklo64(a, b):
    return [x for q in range(4) for x in (a[4 * q], a[4 * q + 1], b[4 * q], b[4 * q + 1])]


def _unpackhi64(a, b):
    return [x for q in range(4) for x in (a[4 * q + 2], a[4 * q + 3], b[4 * q + 2], b[4 * q + 3])]


def _shuffle_i32x4(a, b, imm):
    out = []
    for k in range(4):
        src = a if k < 2 else b
        q = (imm >> (2 * k)) & 3
        out.extend(src[4 * q:4 * q + 4])
    return out


def transpose_sim():
    """Returns [after stage 1, after stage 2, after stage 3, after stage 4]."""
    EVEN, ODD = 0x88, 0xdd
    r = [[(t, l) for l in range(16)] for t in range(16)]
    t_ = [None] * 16
    for i in range(8):                       # lines 267-270
        t_[2 * i] = _unpacklo32(r[2 * i], r[2 * i + 1])
        t_[2 * i + 1] = _unpackhi32(r[2 * i], r[2 * i + 1])
    s1 = [list(x) for x in t_]
    for i in range(4):                       # lines 271-276
        r[4 * i] = _unpacklo64(t_[4 * i], t_[4 * i + 2])
        r[4 * i + 1] = _unpackhi64(t_[4 * i], t_[4 * i + 2])
        r[4 * i + 2] = _unpacklo64(t_[4 * i + 1], t_[4 * i + 3])
        r[4 * i + 3] = _unpackhi64(t_[4 * i + 1], t_[4 * i + 3])
    s2 = [list(x) for x in r]
    for i in range(4):                       # lines 277-282
        t_[i] = _shuffle_i32x4(r[i], r[i + 4], EVEN)
        t_[i + 4] = _shuffle_i32x4(r[i], r[i + 4], ODD)
        t_[i + 8] = _shuffle_i32x4(r[i + 8], r[i + 12], EVEN)
        t_[i + 12] = _shuffle_i32x4(r[i + 8], r[i + 12], ODD)
    s3 = [list(x) for x in t_]
    for i in range(8):                       # lines 283-286
        r[i] = _shuffle_i32x4(t_[i], t_[i + 8], EVEN)
        r[i + 8] = _shuffle_i32x4(t_[i], t_[i + 8], ODD)
    s4 = [list(x) for x in r]
    return [s1, s2, s3, s4]


STAGES = transpose_sim()
# the transpose is exact: r[i] lane t holds input register t, lane i
assert all(STAGES[3][i][t] == (t, i) for i in range(16) for t in range(16))


def _find(state, cell):
    for reg, lanes_ in enumerate(state):
        for lane_, c in enumerate(lanes_):
            if c == cell:
                return reg, lane_
    raise KeyError(cell)


TRACK = [_find(s, (EX["t"], EX["dp"])) for s in STAGES]   # (register, lane) after each stage
assert TRACK[3] == (EX["dp"], EX["t"])


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
    frame (the worked example's block)."""
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
            o.append(text(px + cw / 2, py + ch / 2 - 1, f"({s},{c})", 9.5, "middle", True))
            o.append(text(px + cw / 2, py + ch / 2 + 11, f"#{4 * s + c}", 9, "middle", True,
                          fill=C["muted"]))
    if block is not None:
        bx = x + block * (cw + gap) - 3
        o.append(rect(bx, y - 3, cw + 6, 4 * ch + 3 * gap + 6, "none", C["ink"], 1.4, 4))
    return "".join(o)


def panel_lines(x, y, w, h, forms, hi_rows=(), col=None, col_read=False,
                cols_empty=(), cols_present=None, written_rows=None):
    """One panel as its 16 pair rows of 64 bytes, top line = pair row 0.
    forms: 16 states, one per line: 'vnni' | 'empty'.
    hi_rows: line indexes drawn with a thick outline.
    col: a dword index 0..15 whose 4-byte slot is marked in every line (a
    token's column); col_read: mark it as a read (dashed) instead of a write.
    cols_empty: dword indexes whose column holds no saved row (grey dashed).
    cols_present: a 16-bit mask; the columns of its set bits are drawn in the
    present colour (written by this store), the clear bits grey dashed
    (not written)."""
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
    if cols_present is not None:
        for t in range(16):
            if (cols_present >> t) & 1:
                o.append(rect(x + t * cwid, y, cwid, h, C["rows_fill"], C["rows"], 0.8, 0))
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
    o.append(rect(x, y, w, h, "none", C["ink"], 0.8, 0))
    return "".join(o)


def pair_row_dwords(x, y, w, h, hi_t=None, base_token=32, present=None):
    """One pair row (64 bytes) as 16 dwords, one per token lane of the block;
    each dword = 2 bf16 (j = 0 low half, j = 1 high half). present: a 16-bit
    mask; a clear lane is drawn grey dashed (not written)."""
    dw = w / 16
    o = []
    for t in range(16):
        on = t == hi_t
        absent = present is not None and not (present >> t) & 1
        if absent:
            o.append(rect(x + t * dw, y, dw, h, C["empty_fill"], C["empty"], 0.8, 0, "2 2"))
        else:
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


def dword_grid(x, y, fill, stroke, hi_row=None, hi_col=None, hi_cell=None,
               row_labels=(), col_labels=(), row_prefix="", col_prefix="",
               cell=10, zero_rows=(), zero_cols=(), zero_label=True):
    """16 x 16 dwords: 16 registers (rows) x 16 lanes (columns) of 32 bits.
    hi_row / hi_col get a thick outline; hi_cell = (row, col) is filled in the
    VNNI colour with an ink outline. zero_rows / zero_cols: registers or lanes
    that hold zeros (absent tokens): grey dashed."""
    n = 16
    o = []
    for r in range(n):
        for c in range(n):
            if r in zero_rows or c in zero_cols:
                o.append(rect(x + c * cell, y + r * cell, cell, cell, C["empty_fill"],
                              C["empty"], 0.4, 0, "2 1"))
            else:
                o.append(rect(x + c * cell, y + r * cell, cell, cell, fill, stroke, 0.4, 0))
    if hi_cell is not None:
        r, c = hi_cell
        o.append(rect(x + c * cell, y + r * cell, cell, cell, C["vnni"], C["ink"], 1.0, 0))
    if hi_row is not None:
        o.append(rect(x, y + hi_row * cell, n * cell, cell, "none", C["ink"], 1.6, 0))
    if hi_col is not None:
        o.append(rect(x + hi_col * cell, y, cell, n * cell, "none", C["ink"], 1.6, 0))
    o.append(rect(x, y, n * cell, n * cell, "none", C["ink"], 0.8, 0))
    for i in row_labels:
        hi = i == hi_row
        o.append(text(x - 4, y + i * cell + cell / 2 + 3, f"{row_prefix}{i}", 8.5, "end",
                      True, fill=C["ink"] if hi else C["muted"], weight=600 if hi else None))
    for i in col_labels:
        hi = i == hi_col
        o.append(text(x + i * cell + cell / 2, y - 3, f"{col_prefix}{i}", 8.5, "middle",
                      True, fill=C["ink"] if hi else C["muted"], weight=600 if hi else None))
    return "".join(o)


def present_bits(x, y, mask, cell=11, gap=1):
    """The 16 lanes of a present mask: lane t set = green (the row is stored),
    clear = grey dashed. Returns (svg, x_end). Bit 0 at the left."""
    o = []
    cx = x
    for t in range(16):
        on = (mask >> t) & 1
        if on:
            o.append(rect(cx, y, cell, cell, C["rows_fill"], C["rows"], 0.8, 1))
        else:
            o.append(rect(cx, y, cell, cell, C["empty_fill"], C["empty"], 0.8, 1, "2 2"))
        cx += cell + gap
    return "".join(o), cx


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


def nx_box(x, y, w, h, title, sub, ref):
    """'does not exist': a function or route the code does not provide
    (white box, grey dashed outline)."""
    o = [rect(x, y, w, h, "#fff", C["muted"], 1.2, 4, "5 3"),
         text(x + 8, y + 16, title, 10.5, mono=True, weight=700, fill=C["muted"])]
    ty = y + 30
    for s in sub:
        _w(s, 9, w - 16, False, "nx_box")
        o.append(text(x + 8, ty, s, 9, fill=C["muted"]))
        ty += 11.5
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def _vcard(o, fid, name, color, x, y0, y1, label, ref):
    mid = (y0 + y1) / 2
    o.append(arrow(fid, name, [(x, y0), (x, y1)], color, 1.4))
    o.append(text(x + 8, mid - 3, label, 9.5, fill=color, weight=600))
    o.append(text(x + 8, mid + 10, f"[{ref}]", 8.5, mono=True, fill=C["cite"]))


# ---------------------------------------------------------------------------
# B1: data model of one plane, with the present mask of block 2


def b1():
    fid = "k_vnni-b1"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "present": C["rows"]})]
    # ---- top: the owner (context) --------------------------------------------
    o.append(label_box(20, 14, 316, 46, "detail::kv_block::k = k_vnni_tensor<64, 128>",
                       ["the owner of the plane (kv_cache.hpp, PR 4956; unchanged here)"],
                       C["soft"], C["line"], 10.5, ref="k_vnni.hpp:163-188"))
    boxes.append(("detail::kv_block::k = k_vnni_tensor<64, 128>", "k_vnni.hpp:163-188"))
    # ---- left column: containment with how-many ---------------------------
    lx, lw, bh, step = 20, 316, 58, 84
    col = [
        ("plane", ["K for one KV head of one page",
                   "64 tokens x 128 dimensions of bf16 = 16 KiB"],
         C["vnni_fill"], C["vnni"], "k_vnni.hpp:19-26",
         ("ink", "1 plane -> TOKEN_BLOCKS_4 = 4 token blocks", "k_vnni.hpp:66")),
        ("token block c", ["16 tokens: page offsets 16 c .. 16 c + 15",
                           "owns panel (s, c), s = 0..3: 4 KiB of its own"],
         "#fff", C["ink"], "k_vnni.hpp:22-28, 65",
         ("ink", "1 block -> BLOCK_TOKENS_16 = 16 token lanes t", "k_vnni.hpp:65")),
        ("token lane t, bit t of present", ["token c * 16 + t owns column t of the 4 panels;",
                                            "bit t of `present` set = its row is stored"],
         C["rows_fill"], C["rows"], "k_vnni.hpp:28-29, 326-327, 76-77",
         ("ink", "1 token -> DIM_STEPS_4 = 4 steps s x STEP_PAIRS_16 pairs", "k_vnni.hpp:67-69")),
        ("dimension step s, pair dp", ["1 step = STEP_PAIRS_16 = 16 pairs (a tile depth)",
                                       "1 pair = PAIR_2 bf16 (dims 2 dp, 2 dp + 1): 1 dword"],
         "#fff", C["ink"], "k_vnni.hpp:61-62, 67-69", None),
    ]
    y = 76
    for title, sub, fill, stroke, ref, arr in col:
        _w(title, 12, lw - 8, True, f"b1 {title}")
        for s in sub:
            _w(s, 11, lw - 8, where=f"b1 {title}")
        o.append(label_box(lx, y, lw, bh, title, sub, fill, stroke, ref=ref))
        boxes.append((title, ref))
        if arr:
            _vcard(o, fid, arr[0], C[arr[0]], lx + 60, y + bh, y + step, arr[1], arr[2])
        y += step
    plane_mid = 76 + bh / 2
    block_mid = 76 + step + bh / 2
    # ---- middle column: the panel grid --------------------------------------
    gx, gy, cw, ch = 440, 100, 56, 44
    o.append(text(gx + 118, 76, "the plane: 16 panels (s, c), panel index 4 s + c", 11,
                  "middle", weight=700))
    o.append(panel_grid(gx, gy, cw, ch, hi=(EX["s"], EX["c"]), block=EX["c"]))
    o.append(arrow(fid, "vnni", [(lx + lw, plane_mid), (gx - 4, plane_mid)], C["vnni"], 1.4))
    gap_mid = (lx + lw + gx - 4) / 2
    o.append(lines(gap_mid, plane_mid + 16, ["1 plane ->", "N_PANELS_16 =", "DIM_STEPS_4 x",
                                             "TOKEN_BLOCKS_4", "= 16 panels"], 8.5, 10,
                   "middle", fill=C["vnni"], weight=600))
    o.append(text(gap_mid, plane_mid + 70, "[k_vnni.hpp:75]", 8.5, "middle", True,
                  fill=C["cite"]))
    bx = gx + EX["c"] * (cw + 4) + cw / 2
    grid_bot = gy + 4 * ch + 3 * 4
    o.append(arrow(fid, "ink", [(lx + lw, block_mid), (gx - 14, block_mid),
                                (gx - 14, grid_bot + 14), (bx, grid_bot + 14),
                                (bx, grid_bot + 6)], C["ink"], 1.6))
    o.append(lines(bx + 8, 310, ["block 2 ->", "DIM_STEPS_4 = 4", "panels (s, 2): 4 KiB"],
                   9, 12, fill=C["ink"], weight=600))
    o.append(text(bx + 8, 348, "[k_vnni.hpp:22-28]", 8.5, mono=True, fill=C["cite"]))
    mem = ["memory order: panel index 4 s + c,",
           "byte offset 1024 x (4 s + c). block 2 (framed)",
           "owns panels #2, #6, #10, #14: four 1 KiB pieces",
           "4 KiB apart. panel (2,2) #10 (blue) holds token",
           "37, dim 70. store_block fills panel (s, c) with",
           "16 line stores per step s."]
    for s in mem:
        _w(s, 9.5, 290, where="b1 memory order")
    o.append(lines(gx - 20, 400, mem, 9.5, 12, fill=C["ink"]))
    o.append(text(gx - 20, 472, "[k_vnni.hpp:356-365]", 8.5, mono=True, fill=C["cite"]))
    # the present mask of block 2 (unit 2 of the worked example)
    o.append(text(gx - 20, 486, "present of unit 2 = 0x01ff: lanes 0..8 stored,", 9.5,
                  weight=600))
    o.append(text(gx - 20, 498, "lanes 9..15 (tokens 41..47) absent: never written", 9.5,
                  weight=600))
    svg, xe = present_bits(gx - 20, 504, PRESENT_UNIT2, 12, 1)
    o.append(svg)
    o.append(text(gx - 20 + 6, 528, "t = 0", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(gx - 20 + 8 * 13 + 6, 528, "t = 8", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(gx - 20 + 15 * 13 + 6, 528, "t = 15", 8.5, "middle", True, fill=C["muted"]))
    o.append(text(gx - 20, 544, "[k_vnni.hpp:326-327, 331-332; model.hpp:3245-3257]", 8.5,
                  mono=True, fill=C["cite"]))
    boxes.append(("present of unit 2 = 0x01ff (__mmask16)", "k_vnni.hpp:326-327, 344; model.hpp:3245"))
    o.append(text(gx - 20, 570, "pair row 3 of panel #10: 16 dwords, lane t = token % 16",
                  9.5, weight=600))
    o.append(pair_row_dwords(gx - 20, 578, 256, 26, hi_t=EX["t"], base_token=32,
                             present=PRESENT_UNIT2))
    o.append(lines(gx - 20, 630, ["token 37 = dword 5: low half j = 0 is dim 70,",
                                  "high half j = 1 is dim 71; dwords 9..15 not written"],
                   9, 12, fill=C["ink"]))
    o.append(text(gx - 20, 655, "[k_vnni.hpp:60-62, 82-83, 331-332]", 8.5, mono=True,
                  fill=C["cite"]))
    # ---- right column: one panel zoomed, panel and pair row boxes ------------
    rx, ry = 740, 150
    o.append(text(rx + 100, 126, "panel (2,2) #10: 16 pair rows x 64 B", 11, "middle",
                  weight=700))
    o.append(panel_lines(rx, ry, 200, 160, ["vnni"] * 16, hi_rows=[EX["dp"]],
                         cols_present=PRESENT_UNIT2))
    for dp in range(16):
        o.append(text(rx - 4, ry + dp * 10 + 8, f"dp {dp}", 8.5, "end", True,
                      fill=C["vnni"] if dp == EX["dp"] else C["muted"]))
    o.append(text(rx, 326, "thick row dp 3 = dims 70, 71 of tokens 32..47;", 9, fill=C["ink"]))
    o.append(text(rx, 338, "green columns = the 9 present lanes of unit 2", 9, fill=C["ink"]))
    o.append(text(rx, 350, "64 B apart: pair_row_offsets [k_vnni.hpp:248-256]", 9,
                  fill=C["muted"]))
    o.append(label_box(rx - 10, 362, 250, 52, "panel (s, c)",
                       ["16 pair rows x 64 B = 1 KiB: one AMX B tile"], "#fff", C["vnni"],
                       11, ref="k_vnni.hpp:27-28, 72-75"))
    boxes.append(("panel (s, c)", "k_vnni.hpp:27-28, 72-75"))
    o.append(arrow(fid, "vnni", [(rx + 30, 414), (rx + 30, 448)], C["vnni"], 1.4))
    o.append(lines(rx + 38, 424, ["1 panel -> STEP_PAIRS_16", "= 16 pair rows"], 9, 10,
                   fill=C["vnni"], weight=600))
    o.append(text(rx + 38, 445, "[k_vnni.hpp:68, 72]", 8.5, mono=True, fill=C["cite"]))
    o.append(label_box(rx - 10, 450, 250, 52, "pair row dp",
                       ["64 B line: one dimension pair of 16 tokens"], "#fff", C["vnni"],
                       11, ref="k_vnni.hpp:63-65, 70-71"))
    boxes.append(("pair row dp", "k_vnni.hpp:63-65, 70-71"))
    o.append(arrow(fid, "vnni", [(rx, 502), (rx, 591), (gx - 20 + 256 + 6, 591)],
                   C["vnni"], 1.4))
    o.append(lines(rx + 8, 520, ["1 pair row -> BLOCK_TOKENS_16", "= LANES_16 = 16 dwords,",
                                 "1 per token lane"],
                   9.5, 12, fill=C["vnni"], weight=600))
    o.append(text(rx + 8, 557, "[k_vnni.hpp:65, 71, 79, 91-92]", 8.5, mono=True, fill=C["cite"]))
    # ---- bottom: the index map and the worked example -----------------------
    by = 668
    H = 792
    o.append(line(20, by - 8, 980, by - 8, C["line"]))
    o.append(rect(20, by, 960, 118, "#fff", C["ink"], 1.2, 5))
    o.append(text(30, by + 17, "k_vnni::index(token, dim)", 12, mono=True, weight=700))
    o.append(text(230, by + 17, "element index of K[token][dim] inside the plane (PR 4956, "
                  "unchanged)", 10.5, fill=C["muted"]))
    o.append(cite(976, by + 114, "k_vnni.hpp:105-114"))
    boxes.append(("k_vnni::index(token, dim)", "k_vnni.hpp:105-114"))
    o.append(lines(30, by + 34, [
        "index = (((s * TOKEN_BLOCKS_4 + c) * STEP_PAIRS_16 + dp) * BLOCK_TOKENS_16 + t) * PAIR_2 + j",
        "s = dim / 32, c = token / 16, dp = (dim % 32) / 2, t = token % 16, j = dim % 2",
    ], 10, 13, mono=True))
    o.append(text(30, by + 69, "worked example, token 37 and dimension 70 (s 2, c 2, dp 3, t 5, "
                  "j 0):", 10.5, weight=600, fill=C["vnni"]))
    o.append(lines(30, by + 85, [
        f"index = (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2 + 0 = {EX['index']}   ->   byte "
        f"{EX['byte']} = panel #{EX['panel']} x 1024 + pair row {EX['dp']} x 64 + lane "
        f"{EX['t']} x 4 + j x 2",
        "store_block writes it with the pair-row-3 store of step 2 (r[3] lane 5)",
    ], 10, 13, mono=True))
    cap = ("B1, data model. A plane is K (the key matrix) for one KV head (key/value head) "
           "of one page (64 tokens of KV storage): 64 tokens x 128 dimensions of bf16 "
           "(16-bit floats) = 16 KiB, owned by k_vnni_tensor. It is 16 panels of 1 KiB, "
           "one per (dimension step s, token block c). A panel is 16 pair rows of 64 "
           "bytes, and a pair row holds one dimension pair for 16 token lanes. New in this "
           "PR is the present mask: bit t of `present` says that lane t of the block is "
           "stored. The worked example (unit 2 of the shared window: block 2, present = "
           "0x01ff) traces token 37, dimension 70 to element 5226 (panel #10, pair row 3, "
           "lane 5); lanes 9..15 of the block are never written.")
    legend = [
        ("ctx", "grey box, thin grey outline: the owner detail::kv_block::k = "
                "k_vnni_tensor, context from PR 4956"),
        ("vnni", "blue: the VNNI entities that own bytes: the plane, panel (2,2) #10 in "
                 "the grid, the 16 pair rows of the zoomed panel, and dword 5 (token 37) "
                 "of pair row 3; blue text = the VNNI how-many labels and the worked "
                 "example"),
        ("white box, blue outline: the VNNI entities panel (s, c) and pair row dp",
         "#fff", C["vnni"], False, False),
        ("present", "green: a token lane whose bit of present is set (lanes 0..8 of "
                    "unit 2): the box 'token lane t, bit t of present', the 9 set bits "
                    "of the mask and the 9 written columns of the zoomed panel"),
        ("empty", "grey dashed: a lane whose bit of present is clear (lanes 9..15): "
                  "its bit, its column of the zoomed panel and its dword of pair row 3 "
                  "are never written"),
        ("box", "white box, ink outline: the data-model entities token block c and "
                "dimension step s / pair dp, and the index map k_vnni::index; name in "
                "bold monospace, description in grey sans-serif"),
        ("lane", "white cell, thin grey outline: a panel of the grid other than (2,2) #10, "
                 "and a dword of pair row 3 other than token 37's"),
        ("ink frame: block 2's column in the panel grid, pair row dp 3 of the zoomed "
         "panel (drawn heavier), and that panel's outline", "none", C["ink"], False, False),
        ("arrow", "ink arrow: a containment with its how-many (plane -> blocks, block -> "
                  "lanes, lane -> steps and pairs, block 2 -> its 4 panels)"),
        ("blue arrow: a how-many inside the VNNI layout (plane -> 16 panels, panel -> "
         "16 pair rows, pair row -> 16 dwords)", "arrow", C["vnni"]),
        ("font_mono", "monospace = a name or a value from the code: box titles, panel "
                      "indexes, dp rows, token numbers, the index formula and the worked "
                      "example"),
        ("font_sans", "sans-serif = the drawing titles (bold), the descriptions "
                      "under a box title, the how-many labels, the memory-order note, "
                      "the present-mask note and the notes under the zoomed panel"),
        ("font_cite", "small grey monospace = the lines that define a box or an arrow "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Data model: one K plane, its panels, pair rows, lanes and the "
                  "present mask", "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B2: the register model of store_block

CELL = 10
GRID = 16 * CELL


def b2():
    fid = "k_vnni-b2"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "muted": C["muted"]})]
    o.append(text(20, 18, "the registers of store_block for one dimension step s: 16 zmm "
                  "registers r[t] of 16 dword lanes (LANES_16); worked example: block 2, "
                  "present 0x01ff, s = 2", 11, weight=700))
    o.append(text(20, 32, "a dword is 32 bits = one dimension pair (2 bf16) of one token; "
                  "register t holds the row of token 32 + t, lane dp its pair dp of the step",
                  9.5, fill=C["muted"]))
    # ---- the inputs rows[] ------------------------------------------------------
    A = 52
    o.append(text(20, A + 4, "rows[BLOCK_TOKENS_16]: 16 native rows in dimension order "
                  "(orange); a null pointer for an absent lane", 10, weight=700))
    rx, ry, segw, rowh = 60, A + 28, 48, 9
    for s in range(4):
        hi = s == EX["s"]
        o.append(text(rx + s * segw + segw / 2, ry - 4, f"s = {s}", 8.5, "middle", True,
                      fill=C["vnni"] if hi else C["muted"], weight=600 if hi else None))
    for t in range(16):
        for s in range(4):
            if t in ABSENT_UNIT2:
                o.append(rect(rx + s * segw, ry + t * rowh, segw, rowh, C["empty_fill"],
                              C["empty"], 0.5, 0, "2 2"))
            else:
                o.append(rect(rx + s * segw, ry + t * rowh, segw, rowh, C["rm_fill"], C["rm"],
                              0.5, 0))
    o.append(rect(rx + EX["s"] * segw, ry - 2, segw, 16 * rowh + 4, "none", C["vnni"], 1.6, 0))
    o.append(rect(rx, ry + EX["t"] * rowh, 4 * segw, rowh, "none", C["ink"], 1.6, 0))
    o.append(rect(rx, ry, 4 * segw, 16 * rowh, "none", C["ink"], 0.8, 0))
    for t, lab in ((0, "t=0"), (EX["t"], "t=5"), (8, "t=8"), (9, "t=9"), (15, "t=15")):
        hi = t == EX["t"]
        o.append(text(rx - 4, ry + t * rowh + rowh - 1, lab, 8.5, "end", True,
                      fill=C["ink"] if hi else C["muted"], weight=600 if hi else None))
    o.append(text(rx, ry + 16 * rowh + 12, "[k_vnni.hpp:332-334, 345]", 8.5, mono=True,
                  fill=C["cite"]))
    boxes.append(("rows[BLOCK_TOKENS_16] (rows[t] = the 128 bf16 of token c * 16 + t)",
                  "k_vnni.hpp:332-334, 345"))
    notes = ["1 row = 128 bf16 = 256 B = 4 steps of 64 B (STEP_DIMS_32 bf16 each)",
             "token 37 = rows[5] (thick outline); rows[9..15] null: absent (0x01ff)",
             "one 64-byte load per present row: _mm512_loadu_si512(rows[t] + s * 32)",
             "an absent lane loads nothing: r[t] = _mm512_setzero_si512()"]
    for s in notes:
        _w(s, 9, 420, where="b2 rows notes")
    o.append(lines(rx + 4 * segw + 14, ry + 10, notes, 9, 12, fill=C["ink"]))
    o.append(text(rx + 4 * segw + 14, ry + 62, "[k_vnni.hpp:350-354]", 8.5, mono=True,
                  fill=C["cite"]))
    # ---- the two register grids --------------------------------------------------
    gy = ry + 16 * rowh + 92
    gx1, gx2 = 60, 420
    o.append(lines(gx1 - 40, gy - 30, ["r[t] after the 16 loads (lines 351-353):",
                                       "row = register t (token 32 + t), column = lane dp"],
                   10, 11, weight=700))
    o.append(lines(gx2 - 2, gy - 30, ["r[dp] after transpose_16x16_epi32(r) (line 355):",
                                      "row = register dp (pair row dp), column = lane t"],
                   10, 11, weight=700))
    o.append(dword_grid(gx1, gy, C["rm_fill"], C["rm"], hi_row=EX["t"],
                        hi_cell=(EX["t"], EX["dp"]), row_labels=(0, EX["t"], 8, 9, 15),
                        col_labels=(0, EX["dp"], 15), row_prefix="t=", col_prefix="",
                        zero_rows=ABSENT_UNIT2))
    o.append(dword_grid(gx2, gy, C["vnni_fill"], C["vnni"], hi_row=EX["dp"], hi_col=EX["t"],
                        hi_cell=(EX["dp"], EX["t"]), row_labels=(0, EX["dp"], 15),
                        col_labels=(0, EX["t"], 8, 9, 15), row_prefix="dp=", col_prefix="",
                        zero_cols=ABSENT_UNIT2))
    boxes.append(("r[BLOCK_TOKENS_16] (__m512i, 16 registers of LANES_16 dwords)",
                  "k_vnni.hpp:349-355, 78-79"))
    o.append(cite(gx1 + GRID, gy + GRID + 10, "k_vnni.hpp:349-354"))
    o.append(cite(gx2 + GRID, gy + GRID + 10, "k_vnni.hpp:355, 257-259"))
    my = gy + GRID / 2
    o.append(arrow(fid, "vnni", [(gx1 + GRID + 6, my), (gx2 - 40, my)], C["vnni"], 1.6))
    mx = (gx1 + GRID + 6 + gx2 - 40) / 2
    o.append(text(mx, my - 32, "transpose_16x16_epi32(r)", 9, "middle", True, fill=C["vnni"],
                  weight=600))
    o.append(text(mx, my - 20, "in place: 4 stages, 64 shuffles", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my - 8, "r[i] lane t <- input register t, lane i", 8.5, "middle",
                  fill=C["ink"]))
    o.append(text(mx, my + 14, "zeros of the absent rows become", 8.5, "middle", fill=C["ink"]))
    o.append(text(mx, my + 25, "zeros of lanes 9..15 (never stored)", 8.5, "middle",
                  fill=C["ink"]))
    o.append(text(mx, my + 38, "[k_vnni.hpp:257-287, 361-364]", 8.5, "middle", True,
                  fill=C["cite"]))
    boxes.append(("transpose_16x16_epi32(r)", "k_vnni.hpp:257-287"))
    u = gy + GRID + 24
    o.append(text(gx1 - 40, u, "lane dp = dims 64 + 2 dp, 65 + 2 dp of step 2", 9,
                  fill=C["muted"]))
    o.append(text(gx1 - 40, u + 12, "r[5] lane 3 = dims 70, 71 of token 37 (solid blue cell)",
                  9, fill=C["ink"]))
    o.append(text(gx2 - 2, u, "lane t = token 32 + t; register dp = one 64 B pair row", 9,
                  fill=C["muted"]))
    o.append(text(gx2 - 2, u + 12, "r[3] lane 5 = the same dword: pair row 3, lane 5 of "
                  "panel (2,2)", 9, fill=C["ink"]))
    # ---- the mapping, as a table at the right -----------------------------------
    tx, ty = 630, A - 6
    o.append(rect(tx, ty, 350, 214, "#fff", C["ink"], 1.2, 5))
    o.append(text(tx + 10, ty + 18, "the lanes of r[t] and r[dp], before and after", 10.5,
                  weight=700))
    rows_ = [("", "r[t] (loaded)", "r[dp] (transposed)"),
             ("register", "token lane t", "pair row dp"),
             ("lane", "pair dp of step s", "token lane t"),
             ("dword", "pair dp of token 16c+t", "the same dword"),
             ("absent lane", "register t = 0", "lane t = 0 everywhere"),
             ("store", "-", "one 64 B line, panel+dp*32"),
             ("mask", "-", "present, when partial")]
    yy = ty + 38
    for i, (a, b, c) in enumerate(rows_):
        bold = i == 0
        o.append(text(tx + 10, yy, a, 9, weight=700 if bold else 600))
        o.append(text(tx + 86, yy, b, 9, weight=700 if bold else None, mono=not bold))
        o.append(text(tx + 212, yy, c, 9, weight=700 if bold else None, mono=not bold))
        yy += 15
        if i == 0:
            o.append(line(tx + 6, yy - 10, tx + 344, yy - 10, C["line"]))
    for b in ["token lane t", "pair row dp", "pair dp of step s", "pair dp of token 16c+t",
              "register t = 0", "lane t = 0 everywhere", "one 64 B line, panel+dp*32",
              "present, when partial"]:
        _w(b, 9, 134, True, "b2 table")
    o.append(lines(tx + 10, yy + 6, ["the static_assert of line 91-92 pins the square:",
                                     "BLOCK_TOKENS_16 == LANES_16 == STEP_PAIRS_16, so the",
                                     "16 token rows of a step become the 16 pair rows of",
                                     "a panel in one 16 x 16 transpose"], 9, 11, fill=C["ink"]))
    o.append(cite(tx + 346, ty + 210, "k_vnni.hpp:257-259, 326-331, 356-364, 91-92"))
    boxes.append(("the lanes of r[t] and r[dp], before and after",
                  "k_vnni.hpp:257-259, 326-331, 356-364"))
    H = int(u + 30)
    cap = ("B2, the register model of store_block (new). For one dimension step s, the "
           "16 loads put the 16 dimension pairs of token 32 + t into register r[t] (lane "
           "dp = pair dp). transpose_16x16_epi32 turns the 16 x 16 grid of dwords: "
           "afterwards register r[dp] holds pair row dp of the panel, with the token in "
           "lane t. The worked example's dword (dims 70, 71 of token 37) moves from r[5] "
           "lane 3 to r[3] lane 5. An absent lane of the present mask (lanes 9..15 of "
           "unit 2) loads a zero register, and its zeros land in lane t of every register "
           "after the transpose, where the masked store skips them.")
    legend = [
        ("rm", "orange: the row-major side: the 16 native rows rows[t] in dimension "
               "order (4 steps of 64 B each) and the r[t] register grid after the loads"),
        ("vnni", "blue: the VNNI side: the r[dp] register grid after the transpose; "
                 "blue text = the step s = 2 and the transpose"),
        ("solid blue cell, ink outline: the worked example's dword, dims 70, 71 of token "
         "37: r[5] lane 3 after the loads, r[3] lane 5 after the transpose",
         C["vnni"], C["ink"], False, False),
        ("empty", "grey dashed: an absent lane of present (lanes 9..15 of unit 2): a "
                  "null row pointer, a zero register r[t] before the transpose, a zero "
                  "lane t after it"),
        ("blue frame: the column s = 2 of rows[], the dimension step this figure follows",
         "none", C["vnni"], False, False),
        ("ink outline: the frame of rows[] and of each register grid, and the "
         "highlighted row or column of the worked example: row t = 5 of rows[] and of "
         "r[t] (token 37), register dp = 3 and lane t = 5 of r[dp]",
         "none", C["ink"], False, False),
        ("box", "white box, ink outline: the table of what a dword lane means before "
                "and after the transpose"),
        ("blue arrow: transpose_16x16_epi32, r[t] -> r[dp]", "arrow", C["vnni"]),
        ("font_mono", "monospace = the intrinsic calls, the t, dp and s labels, the "
                      "table's code names"),
        ("font_sans", "sans-serif = the titles, the notes beside rows[] and under the "
                      "grids, the table's headers"),
        ("font_cite", "small grey monospace = the lines that define a drawing or a step "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Register model: the 16 x 16 dwords of one dimension step "
                  "before and after the transpose", "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B3: function model


def _band(o, boxes, fid, y, header, callers, callers_ref, callers_reg, cells, callees,
          cx0=245, cw_total=740, cell_h=62, callers_h=84, tags=None):
    """One group of operations: header, the callers box at the left, the
    function cells and their callees under them. Returns the next y."""
    _w(header, 11, 740, where="band_header")
    o.append(text(cx0, y, header, 11, weight=700))
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
        tag = tags[i] if tags else "unchanged"
        o.append(fn_cell(x, y, cw, cell_h, name, desc, ref, tag))
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
    o.append(text(245, 18, "the operations of k_vnni.hpp that this PR adds or touches, and "
                  "their neighbours; a cell = name, what it does, its definition, its tag",
                  10, fill=C["muted"]))
    o.append(text(245, 30, "under a cell: what it calls, expands to, or who reads it", 10,
                  fill=C["muted"]))
    y = 50
    y = _band(o, boxes, fid, y, "the block save: a run of 2..16 tokens of one block (lines "
              "326-367, new)", [
        "model.hpp: store_k_block 3201: a run",
        "with n >= 2 tokens -> page::set_k_block",
        "3288 (slot, kv_head, c, present, rows)",
        "kv_cache.hpp: set_k_block 2089 ->",
        "store_block(k.as_view(), c, present,",
        "rows) 2095; any thread of the window",
        "tests: t_k_vnni_layout.cpp 241 (38 masks)"],
        "model.hpp:3201; kv_cache.hpp:2089", [
        ("store_k_block (caller)", "model.hpp:3193-3205"),
        ("page::set_k_block (caller)", "kv_cache.hpp:2078-2096"),
        ("the block-save test (caller)", "t_k_vnni_layout.cpp:192-250")], [
        ("store_block", ["Up to 16 rows of one block, transposed", "in registers, written as whole lines"],
         "k_vnni.hpp:326-367"),
        ("transpose_16x16_epi32", ["In-place 16 x 16 transpose of dword", "lanes: 4 stages, 64 shuffles"],
         "k_vnni.hpp:257-287"),
    ], [["-> k_vnni_access::plane, 16 loads per step,", "transpose_16x16_epi32, 16 (masked) stores"],
        ["-> _mm512_unpacklo/hi_epi32, _epi64,", "_mm512_shuffle_i32x4 (0x88, 0xdd)"]],
        tags=["new", "new"])
    y = _band(o, boxes, fid, y, "one token's row into and out of the plane (lines 290-324, "
              "369-380; store_row's comment changed)", [
        "model.hpp: store_k_block 3260-3272: a run",
        "of 1 token -> page::set_k_row (scatter)",
        "kv_cache.hpp: set_k_row 2065 (store_row",
        "2071), get_k_row 2102 (load_row 2108),",
        "copy_storage_slot 2353 (copy_token 2369)",
        "full.hpp: k_head_fn 2747 (get_k_row 2754)"],
        "model.hpp:3260; kv_cache.hpp:2065, 2102", [
        ("page::set_k_row (caller)", "kv_cache.hpp:2061-2075"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2098-2112"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2353"),
        ("page_info::k_head_fn (caller)", "full.hpp:2747-2756")], [
        ("store_row", ["One token's row in: 4 scatters of 16", "dwords into the token's 64 pair slots"],
         "k_vnni.hpp:290-307"),
        ("load_row", ["One token's row out: 4 gathers", "of 16 dwords (the inverse)"],
         "k_vnni.hpp:309-324"),
        ("copy_token", ["One token between planes via a", "local row: load_row, store_row"],
         "k_vnni.hpp:369-380"),
    ], [["-> k_vnni_access::plane, pair_base,", "pair_row_offsets; threads: disjoint tokens"],
        ["-> k_vnni_access::plane, pair_base,", "pair_row_offsets"],
        ["-> load_row, store_row,", "k_destination_row, k_source_row"]],
        tags=["changed", "unchanged", "unchanged"])
    y = _band(o, boxes, fid, y, "the one access route and the address helpers (lines 195-203, "
              "234-256, unchanged)", [
        "in this file: store_block 347, store_row",
        "299, load_row 316 (k_vnni_access::plane)",
        "kernels/k_vnni.hpp: qk_group 57",
        "amx_attn.cpp: qk_vnni_128x4 239",
        "kv_cache.hpp: fill_storage_slot 1780",
        "(the documented exception)"],
        "k_vnni.hpp:32-39", [
        ("k_vnni::qk_group (caller)", "kernels/k_vnni.hpp:33-39"),
        ("qk_vnni_128x4 (caller)", "amx_attn.cpp:233-239")], [
        ("k_vnni_access::plane", ["The view's plane address:", "the one route to the bytes"],
         "k_vnni.hpp:195-203"),
        ("pair_base", ["Byte address of dimension pair 0 of", "step s for a token (store_row, load_row)"],
         "k_vnni.hpp:235-247"),
        ("pair_row_offsets", ["Dword offsets of the 16 pair rows of", "one panel (64 bytes = 16 dwords apart)"],
         "k_vnni.hpp:248-256"),
    ], [["-> k.data_ (friend of k_vnni_view)"],
        ["store_block does not use it: it addresses", "panel (s, c) directly (line 356)"],
        ["store_block does not use it: whole lines,", "no scatter index"]],
        tags=["unchanged", "unchanged", "unchanged"])
    H = int(y) + 4
    cap = ("B3, function model. The two new operations of the file (store_block and "
           "transpose_16x16_epi32) sit in the top group with their callers: "
           "store_k_block in model.hpp sends a run of 2 to 16 tokens through "
           "page::set_k_block, on any thread of the shared window. The middle group is "
           "the per-token path that PR 4956 added: a run of one token still goes through "
           "page::set_k_row -> store_row, whose comment now states that several threads "
           "may store different tokens of one plane at the same time. The bottom group "
           "is the one access route and the two address helpers, which store_block does "
           "not need: it addresses panel (s, c) directly and stores whole lines.")
    legend = [
        ("box", "white box, ink outline: one operation of k_vnni.hpp (a cell): its name "
                "in bold monospace, what it does in sans-serif, its tag and the lines "
                "that define it"),
        ("ctx", "grey box, thin grey outline: the callers in other files of one group, "
                "each with its call-site line"),
        ("arrow", "ink arrow: the callers (grey box at the left) -> the group of "
                  "operations they call"),
        ("font_mono", "bold monospace = an operation's name"),
        ("font_sans", "sans-serif = what an operation does, the group headers, the "
                      "callers with their call-site lines, and what a cell calls or "
                      "expands to (grey, under the cell)"),
        ("font_cite", "small grey monospace = the lines that define an operation, or "
                      "the callers of a group (file:line)"),
        ("font_tag", "bold 'new' = added by this PR (store_block, transpose_16x16_epi32); "
                     "'changed' = store_row's comment; 'unchanged' = context from PR 4956"),
    ]
    return figure(fid, W, H, "Function model: the new operations, their neighbours, callers "
                  "and callees", "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B4: the bytes of one block through store_block (full and masked) and store_row


def b4():
    fid = "k_vnni-b4"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 20, "worked example: the plane of slot 5, KV head 0, page 7; a block's "
                  "bytes are its 4 panels (s, c) = 4 KiB; a panel: 16 pair rows of 64 B", 11,
                  weight=700))
    o.append(text(20, 36, "the three store paths of one prefill pass (units 0 and 2 of the "
                  "shared window) and of one decode step; schematic, not to scale", 9.5,
                  fill=C["muted"]))
    # key
    kx, ky = 20, 48
    o.append(rect(kx, ky, 22, 12, C["vnni_fill"], C["vnni"], 1, 1))
    o.append(text(kx + 28, ky + 10, "VNNI pair row (64 B), written whole", 10))
    kx += 28 + text_width("VNNI pair row (64 B), written whole", 10) + 18
    o.append(rect(kx, ky, 8, 12, C["rows_fill"], C["rows"], 1, 0))
    o.append(text(kx + 14, ky + 10, "column of a present lane (masked store)", 10))
    kx += 14 + text_width("column of a present lane (masked store)", 10) + 18
    o.append(rect(kx, ky, 8, 12, C["empty_fill"], C["empty"], 1, 0, "3 2"))
    o.append(text(kx + 14, ky + 10, "column of an absent lane: never written", 10))
    kx += 14 + text_width("column of an absent lane: never written", 10) + 18
    o.append(rect(kx, ky, 6, 12, C["vnni"], C["ink"], 1, 0))
    o.append(text(kx + 12, ky + 10, "one token's column, scattered", 10))
    px0, pw, ph, pg = 300, 118, 72, 14
    step_h = 150
    y = 84
    steps = [
        dict(n="1", title="store_block(plane, 0, 0xffff, rows)", c=0,
             sub=["unit 0: tokens 0..15, a full block:",
                  "per step s, 16 loads, 1 transpose, 16 whole-",
                  "line stores into panel (s, 0); 64 stores"],
             fill=C["vnni_fill"], stroke=C["vnni"], ref="k_vnni.hpp:342-345, 357-360",
             kw=dict(),
             note=["page::set_k_block(slot 5, kv_head, c = 0, 0xffff, rows) from store_k_block, "
                   "on the thread that claimed unit 0 [model.hpp:3276-3289]",
                   "every one of the block's 64 lines is written once, whole: 64 stores of 64 B "
                   "= 4 KiB [k_vnni.hpp:334-337; kv_cache.hpp:2089-2095]",
                   "unit 1 (block 1, tokens 16..31) is the same call with c = 1 on another "
                   "thread: disjoint panels (s, 1)"]),
        dict(n="2", title="store_block(plane, 2, 0x01ff, rows)", c=2,
             sub=["unit 2: tokens 32..40, 9 of 16 lanes present:",
                  "per step s, 9 loads + 7 zero registers,",
                  "1 transpose, 16 masked stores (lanes 0..8)"],
             fill=C["vnni_fill"], stroke=C["vnni"], ref="k_vnni.hpp:350-354, 361-365",
             kw=dict(cols_present=PRESENT_UNIT2),
             note=["_mm512_mask_storeu_epi32(panel + dp * ROW_ELEMS_32, present, r[dp]): "
                   "lanes 9..15 (tokens 41..47) are not written [k_vnni.hpp:361-365]",
                   "bit-identical to set_k_row per present token: the test compares 4 blocks x "
                   "38 masks [kv_cache.hpp:2082-2084; t_k_vnni_layout.cpp:192-250]",
                   "a later run of the same block (its other lanes) is another masked store on "
                   "disjoint lanes [common.hpp:1207-1214]"]),
        dict(n="3", title="store_row(plane, 41, src)", c=2,
             sub=["a decode step: one token per user, 8 items,",
                  "not shared; a run of 1 token -> set_k_row:",
                  "4 scatters into the token's 64 pair slots"],
             fill=C["vnni_fill"], stroke=C["vnni"], ref="k_vnni.hpp:290-307",
             kw=dict(col=9, cols_empty=list(range(10, 16))),
             note=["store_k_block, n == k_scatter_run_len (= 1): page::set_k_row(slot, kv_head, "
                   "41, k_source_row(kout)) [model.hpp:3260-3273, 3141]",
                   "4 AVX-512 scatters that together write 4 bytes into each of the token's 64 "
                   "lines (the PR 4956 store) [kv_cache.hpp:716-721]",
                   "drawn: block 2 after offset 41 was saved this way: lanes 0..8 from unit 2, "
                   "lane 9 scattered, lanes 10..15 still absent"]),
    ]
    for st in steps:
        o.append(text(20, y + 10, st["n"], 13, weight=700))
        _w(st["title"], 10.5, 242, True, f"b4 title {st['title']}")
        for s in st["sub"]:
            _w(s, 9.5, 242, where=f"b4 sub {st['title']}")
        o.append(label_box(36, y - 2, 250, 80, st["title"], st["sub"], st["fill"],
                           st["stroke"], 10.5, ref=st["ref"]))
        boxes.append((st["title"], st["ref"]))
        for s in range(4):
            x = px0 + s * (pw + pg)
            c = st["c"]
            o.append(text(x + pw / 2, y + 2, f"panel ({s},{c}) #{4 * s + c}", 9, "middle",
                          True, fill=C["muted"]))
            o.append(panel_lines(x, y + 7, pw, ph, ["vnni"] * 16, **st["kw"]))
        for i, s in enumerate(st["note"]):
            _w(s, 9.5 if i == 0 else 9, 680, where=f"b4 note {st['title']}")
        o.append(text(px0, y + ph + 20, st["note"][0], 9.5, fill=C["ink"]))
        o.append(lines(px0, y + ph + 32, st["note"][1:], 9, 11, fill=C["muted"]))
        y += step_h
    # the write-pattern comparison, from the comment of store_block
    cy = y - 10
    o.append(line(20, cy - 6, 980, cy - 6, C["line"]))
    o.append(text(20, cy + 10, "the write pattern of one block, from the comment of store_block "
                  "(lines 334-337): the same 4 KiB, a different pattern", 10.5, weight=700))
    o.append(label_box(20, cy + 18, 460, 66, "store_row x 16 (16 x step 3)",
                       ["64 scatters per block, each writing 4 B into 16 lines:",
                        "every one of the block's 64 lines receives 16 partial writes"],
                       "#fff", C["ink"], 10.5, ref="k_vnni.hpp:334-337, 302-306"))
    boxes.append(("store_row x 16 (the per-token write pattern)", "k_vnni.hpp:334-337, 302-306"))
    o.append(label_box(500, cy + 18, 480, 66, "store_block, a full block (step 1)",
                       ["64 stores of whole lines per block (16 per step x 4 steps):",
                        "each of the 64 lines is written once, whole"],
                       C["vnni_fill"], C["vnni"], 10.5, ref="k_vnni.hpp:334-337, 357-360"))
    boxes.append(("store_block, a full block (the whole-line write pattern)",
                  "k_vnni.hpp:334-337, 357-360"))
    H = int(cy + 96)
    cap = ("B4, sequencing model: the bytes of one block through the three store paths "
           "of this PR, on the worked example. Step 1 is a full block (unit 0 of the "
           "shared window): 16 loads, one transpose and 16 whole-line stores per "
           "dimension step fill the block's 4 panels, 64 lines written once each. Step 2 "
           "is the partial block of unit 2 (present = 0x01ff): the same loop with 7 zero "
           "registers and masked stores that touch the 9 present columns only. Step 3 is "
           "the per-token scatter of PR 4956, which a run of one token (a decode step) "
           "still takes: 4 bytes into each of the token's 64 lines. The bottom row quotes "
           "the comment's comparison: the same 4 KiB, written as 64 whole lines instead "
           "of 64 scatters of 16 partial writes.")
    legend = [
        ("vnni", "blue: a VNNI pair row, 64 B, of the block (every step), the step boxes "
                 "and the whole-line write pattern box"),
        ("present", "green column: a present lane of unit 2 (tokens 32..40), written "
                    "by the masked stores of step 2"),
        ("empty", "grey dashed column: an absent lane (tokens 41..47 in step 2, 42..47 "
                  "in step 3): never written"),
        ("solid blue column, ink outline: the column of token 41 (lane 9) written by "
         "store_row in step 3, 4 B in each of the 64 lines", C["vnni"], C["ink"], False, False),
        ("ink outline: a panel's frame", "none", C["ink"], False, False),
        ("box", "white box, ink outline: the per-token write pattern box at the bottom"),
        ("font_mono", "monospace = an operation call in a step box, and the panel "
                      "labels (s,c) #n"),
        ("font_sans", "sans-serif = the worked example's header, the key, the step "
                      "numbers 1 to 3 (bold), what a step does, and the notes under the "
                      "panels"),
        ("font_cite", "small grey monospace = the lines that define a step's operation "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Sequencing model: the bytes of one block through store_block "
                  "(full and masked) and store_row", "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B5: interaction model (which thread calls which operation)

B5_COLUMNS = [(165, 395, "main opens the window", "model.hpp:3329-3333"),
              (405, 745, "every thread claims units: store_k_block", "model.hpp:3340-3346"),
              (755, 980, "join, then marks", "model.hpp:3347-3376")]


def b5():
    fid = "k_vnni-b5"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    for x0, x1, name, ref in B5_COLUMNS:
        o.append(rect(x0, 12, x1 - x0, 26, C["soft"], C["line"], 1, 3))
        o.append(text((x0 + x1) / 2, 24, name, 9.5, "middle", weight=600))
        o.append(text((x0 + x1) / 2, 35, ref, 8.5, "middle", True, fill=C["cite"]))
    lanes_ = [("[main]", "worker_ix 0: save_k", 104),
              ("[helper 1]", "worker_ix 1: run_main_help", 62),
              ("[helper 2]", "worker_ix 2: run_main_help", 62),
              ("attention workers", "self_attention.hpp", 56),
              ("a decode step", "8 items: not shared", 56)]
    ly = 46
    lane_y = {}
    for name, sub, h in lanes_:
        svg, _ = lane(20, ly, 960, h, name, sub)
        o.append(svg)
        lane_y[name] = (ly, h)
        ly += h + 4
    # main
    y, h = lane_y["[main]"]
    o.append(lane_block(165, y + 6, 230, 92, [
        "k_store_shared: 3 workers, 41 items > 16",
        "-> shared; k_store_cut_units: unit_start =",
        "[0, 16, 32, 41], n_units = 3; next_unit = 0,",
        "finished = 0; opened.fetch_add(1) (release)",
        "[a page block, a page or a KV change ends",
        "a unit]"],
        C["unit_fill"], C["unit"], "model.hpp:3153-3191, 3329-3333", size=9))
    boxes.append(("k_store_shared, k_store_cut_units, the window open",
                  "model.hpp:3153-3161, 3165-3191, 3329-3333"))
    o.append(lane_block(405, y + 6, 330, 60, [
        "u = next_unit.fetch_add(1) = 0: store_k_block(items 0..15):",
        "run of 16 in block 0 of page 7 -> page::set_k_block(slot 5,",
        "kv_head, c = 0, 0xffff, rows) -> store_block, per KV head;",
        "then u = 3 >= n_units: leave the loop"],
        C["vnni_fill"], C["vnni"], "model.hpp:3340-3346, 3276-3289; k_vnni.hpp:342", size=9))
    boxes.append(("the claim loop and store_k_block -> set_k_block -> store_block",
                  "model.hpp:3340-3346, 3193-3205, 3276-3289"))
    o.append(lane_block(405, y + 70, 330, 26, [
        "[idle: no 4th unit] the loop ends at the first u >= n_units"],
        "#fff", C["ink"], "model.hpp:3343", idle=True, size=9))
    boxes.append(("the loop ends at u >= n_units", "model.hpp:3341-3343"))
    o.append(lane_block(755, y + 6, 215, 48, [
        "spin on finished < 2 (_mm_pause);",
        "the watchdog aborts after 120 s"],
        "#fff", C["ink"], "model.hpp:3351-3365", idle=True, size=9))
    boxes.append(("main's join: finished == n_workers - 1", "model.hpp:3351-3365"))
    o.append(lane_block(755, y + 58, 215, 40, [
        "marks: mark_k_complete(slot, j) and",
        "the GOF credits, items in order"],
        C["hw_fill"], C["hw"], "model.hpp:3369-3384", size=9))
    boxes.append(("the marks loop (mark_k_complete, GOF credits)", "model.hpp:3369-3384"))
    # helper 1
    y, h = lane_y["[helper 1]"]
    o.append(lane_block(165, y + 6, 230, 44, [
        "my_window = ++helper_windows[1] = 1;",
        "spin while opened < 1 (_mm_pause)",
        "[the helper is idle: its next kernel waits]"],
        "#fff", C["ink"], "model.hpp:3334-3339", idle=True, size=9))
    boxes.append(("a helper waits for its window: opened >= my_window", "model.hpp:3334-3339"))
    o.append(lane_block(405, y + 6, 330, 48, [
        "u = 1: store_k_block(items 16..31): run of 16 in block 1",
        "-> set_k_block(slot 5, kv_head, c = 1, 0xffff, rows) ->",
        "store_block: panels (s, 1), disjoint from main's (s, 0)"],
        C["vnni_fill"], C["vnni"], "model.hpp:3340-3346; k_vnni.hpp:27-29, 356", size=9))
    boxes.append(("helper 1: unit 1 -> store_k_block of block 1", "model.hpp:3340-3346"))
    o.append(lane_block(755, y + 6, 215, 36, [
        "finished.fetch_add(1) (release);",
        "return (no marks on a helper)"],
        C["unit_fill"], C["unit"], "model.hpp:3347-3350", size=9))
    boxes.append(("a helper's finished.fetch_add and return", "model.hpp:3347-3350"))
    # helper 2
    y, h = lane_y["[helper 2]"]
    o.append(lane_block(165, y + 6, 230, 44, [
        "my_window = ++helper_windows[2] = 1;",
        "spin while opened < 1",
        "[the test's late helper starts 20 ms late]"],
        "#fff", C["ink"], "model.hpp:3334-3339; t_llama_unit.cpp:4054", idle=True, size=9))
    o.append(lane_block(405, y + 6, 330, 48, [
        "u = 2: store_k_block(items 32..40): run of 9 in block 2",
        "-> set_k_block(slot 5, kv_head, c = 2, 0x01ff, rows) ->",
        "store_block: masked stores, lanes 0..8 of panels (s, 2)"],
        C["vnni_fill"], C["vnni"], "model.hpp:3340-3346; k_vnni.hpp:361-365", size=9))
    boxes.append(("helper 2: unit 2 -> store_k_block of block 2 with present 0x01ff",
                  "model.hpp:3340-3346; k_vnni.hpp:361-365"))
    o.append(lane_block(755, y + 6, 215, 36, [
        "finished.fetch_add(1) (release);",
        "return"],
        C["unit_fill"], C["unit"], "model.hpp:3347-3350", size=9))
    # attention workers
    y, h = lane_y["attention workers"]
    o.append(lane_block(165, y + 6, 570, 40, [
        "the pending sections wait behind save_k: a page is read only after its K and V",
        "rows are complete (is_kv_complete); every row store happens-before the latch count_down"],
        "#fff", C["q"], "model.hpp:3085, 3124-3126; full.hpp:2744-2746", idle=True, size=9))
    boxes.append(("attention workers: the pending sections wait behind save_k",
                  "model.hpp:3085, 3121-3126"))
    o.append(lane_block(755, y + 6, 215, 40, [
        "qk_group(k_packed, q, live, s, 64) or",
        "qk_vnni_128x4 read the plane"],
        C["q_fill"], C["q"], "self_attention.hpp:1977-1978, 1773", size=9))
    boxes.append(("apply_page_tok -> qk_group(k_packed) / qk_vnni_128x4",
                  "self_attention.hpp:1773, 1977-1978"))
    # a decode step
    y, h = lane_y["a decode step"]
    o.append(lane_block(165, y + 6, 570, 40, [
        "k_store_shared is false (8 items <= k_store_block): main alone runs store_k_block(0, 8);",
        "every run has n = 1 = k_scatter_run_len -> page::set_k_row -> store_row (4 scatters)"],
        C["vnni_fill"], C["vnni"], "model.hpp:3153-3161, 3366-3368, 3260-3273", size=9))
    boxes.append(("a decode step: not shared, set_k_row -> store_row per token",
                  "model.hpp:3153-3161, 3260-3273, 3366-3368"))
    o.append(lane_block(755, y + 6, 215, 40, [
        "helpers return at once:",
        "!is_main && !shared"],
        "#fff", C["ink"], "model.hpp:3314-3315", idle=True, size=9))
    boxes.append(("a helper returns when the store is not shared", "model.hpp:3314-3315"))
    ry = ly + 4
    o.append(text(20, ry + 12, "rules, each cited from the comment that states it",
                  11, weight=700))
    rules = [
        ("R1", ["tokens are written independently: token i owns column (i % 16) of its "
                "block in every panel, so several threads may store different tokens of one "
                "plane at the same time"],
         "k_vnni.hpp:27-29, 290-292"),
        ("R2", ["a unit never crosses a page, a 16-token page block, or a change of "
                "token_jobs_do_kv; items of one block that are not consecutive fall into",
                "several units, whose writers touch disjoint token lanes (masked stores), so "
                "two threads may write one block without conflict"],
         "common.hpp:1207-1214; model.hpp:3109-3113"),
        ("R3", ["both sides decide with k_store_shared, so a helper never waits for a window "
                "main does not open; n_workers == 1 never shares"],
         "model.hpp:3103-3106, 3099-3101"),
        ("R4", ["a unit index is assigned once (fetch_add on next_unit): a thread that leaves "
                "the claim loop has stored every unit it took"],
         "model.hpp:3118-3120"),
        ("R5", ["main returns only when finished == n_workers - 1: every unit is stored, and "
                "every row store happens-before the downstream latch count_down"],
         "model.hpp:3121-3126"),
        ("R6", ["the block index is checked in store_block, as store_row checks its token "
                "index: an index at or above Rows / 16 would write into other panels"],
         "k_vnni.hpp:337-339, 346"),
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
    cap = ("B5, interaction model. One lane per thread of the worked example's shared "
           "window (schematic, not to scale), left to right in the order of one save_k: "
           "main cuts the 41 items into 3 units and opens the window, every thread claims "
           "units with fetch_add and runs store_k_block -> page::set_k_block -> "
           "store_block on its own block (disjoint panels, or disjoint lanes of one "
           "block), the helpers count themselves finished and return, main joins and "
           "then marks the tokens. The attention workers only read, after the marks. A "
           "decode step is not shared: main alone scatters one row per token with "
           "store_row. R1 to R6 cite the comment that states each rule.")
    legend = [
        ("vnni", "blue: a writer of the plane: store_k_block -> set_k_block -> "
                 "store_block (one unit per block), and the decode step's set_k_row -> "
                 "store_row"),
        ("unit", "grey-blue: the window bookkeeping: the cut into units and the open "
                 "on main, finished.fetch_add on a helper"),
        ("q", "purple: the attention workers' reads of the plane (qk_group, "
              "qk_vnni_128x4)"),
        ("hw", "yellow: the marks loop on main (mark_k_complete and the GOF credits for "
               "the hardware attention), after the join"),
        ("idle", "white, ink dashed outline: a thread that waits or has nothing to do: "
                 "a helper that spins on opened, main that spins on finished, the "
                 "helpers of an unshared store, the loop's end"),
        ("white, purple dashed outline: the attention workers' pending sections that "
         "wait behind save_k", "#fff", C["q"], True, False),
        ("ctx", "grey box, thin grey outline: a phase header of the top row, with the "
                "lines that bound the phase"),
        ("lane", "white frame, thin grey outline: one lane; its name at the left "
                 "in bold, its role under it in grey"),
        ("font_mono", "bold monospace = the rule tags R1 to R6"),
        ("font_sans", "sans-serif = the lane and phase names, what each block does, "
                      "and the rules"),
        ("font_cite", "small grey monospace = the lines that define a block, a phase "
                      "or a rule (file:line)"),
    ]
    return figure(fid, W, H, "Interaction model: which thread calls which operation on which "
                  "block", "".join(o), cap, boxes=boxes, legend=legend)
