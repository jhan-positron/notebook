"""Base diagrams B1-B5 of the PR 4959 page for h/tron/tensor/k_vnni.hpp.

Adapted from exec/pr4956-diagrams-20261015/figs/base_k_vnni.py (the plane
building blocks) and exec/pr4424-diagrams-20261009/figs (the row-major form
helpers). Every fact drawn here comes from the head file (PR 4959 head
6b081187e1) or from the cited caller files of the same head. Line numbers are
head line numbers of h/tron/tensor/k_vnni.hpp unless another file is named.

Module-level constants and building blocks (imported by the change diagrams):
  EX, PAGE_7, SLOT_5, KV_HEAD_0, BLOCK_2, ROWS_SAVED_0_45, BLOCK2_ROWS_SAVED,
  ROWS_MASK, BLOCKS_MASK, index_of, row_major_elem_of, rm_forms, token_rows,
  plane_grid, panel_lines, pair_row_dwords, block_panels, bits64, bits4,
  lane_block, callers_box, band_header, _band, _w
"""
import sys

from svg_helpers import (C, arrow, bit_row, card_arrow, cite, figure, fn_cell,
                         label_box, lane, line, lines, marker_defs, rect, text,
                         text_width)

# ---------------------------------------------------------------------------
# The worked example of the page (STYLE.md): page 7, storage slot 5, KV head 0.
# Offsets 0..45 saved: blocks 0 and 1 were whole-block saves (converted), block
# 2 holds offsets 32..45 row-major (14 of 16 rows), block 3 holds nothing.
# Token 37 = block 2, t = 5; dimension 70 = step 2, pair 3, j = 0.
PAGE_7, SLOT_5, KV_HEAD_0, BLOCK_2 = 7, 5, 0, 2
ROWS_SAVED_0_45 = list(range(0, 46))
BLOCK2_ROWS_SAVED = [o for o in ROWS_SAVED_0_45 if o // 16 == BLOCK_2]   # 32..45
ROWS_MASK = sum(1 << i for i in ROWS_SAVED_0_45)                           # k_rows_saved_[5]
BLOCKS_MASK = 0b0011                                                       # k_vnni_blocks_[5]


def index_of(token, dim):
    """k_vnni::index (k_vnni.hpp:126-135) and its five coordinates."""
    s, c = dim // 32, token // 16
    dp, t, j = (dim % 32) // 2, token % 16, dim % 2
    return dict(s=s, c=c, dp=dp, t=t, j=j,
                index=(((s * 4 + c) * 16 + dp) * 16 + t) * 2 + j,
                panel=s * 4 + c)


def row_major_elem_of(token, cols=128):
    """row_major_row (k_vnni.hpp:429-439): panel (t / 4, c), row t % 4."""
    c, t = token // 16, token % 16
    panel = (t // 4) * 4 + c
    row = t % 4
    return dict(panel=panel, row=row, step=t // 4, elem=panel * 512 + row * cols)


EX = dict(token=37, dim=70)
EX.update(index_of(EX["token"], EX["dim"]))          # s=2 c=2 dp=3 t=5 j=0, index 5226
EX["byte"] = EX["index"] * 2                           # 10452
EX["rm"] = row_major_elem_of(EX["token"])             # panel 6, row 1, elem 3200
EX["rm_dim_elem"] = EX["rm"]["elem"] + EX["dim"]       # 3270
EX["rm_dim_byte"] = EX["rm_dim_elem"] * 2              # 6540
assert EX["index"] == 5226 and EX["panel"] == 10 and EX["rm"]["elem"] == 3200
assert EX["rm_dim_elem"] == 3270 and ROWS_MASK == 0x3fffffffffff


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Building blocks


def rm_forms(saved_tokens, c=BLOCK_2):
    """Row-major forms of the 4 panels of block c: token t of the block owns
    lines 4 (t % 4) .. 4 (t % 4) + 3 of panel (t / 4, c) (k_vnni.hpp:405-411)."""
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


def plane_grid(x, y, cw, ch, states=None, hi=None, block=None, gap=4):
    """The plane as its 16 panels (s rows x c columns), panel index 4 s + c.
    states: one state per block c ('vnni' | 'rm' | 'empty' | None) that colours
    the column; hi = (s, c) gets a heavier outline; column `block` gets an ink
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
            st = states[c] if states else None
            if st == "vnni":
                fill, stroke, dash = C["vnni_fill"], C["vnni"], None
            elif st == "rm":
                fill, stroke, dash = C["rm_fill"], C["rm"], None
            elif st == "empty":
                fill, stroke, dash = C["empty_fill"], C["empty"], "3 2"
            else:
                fill, stroke, dash = "#fff", C["line"], None
            on = hi == (s, c)
            o.append(rect(px, py, cw, ch, fill, C["ink"] if on else stroke,
                          1.6 if on else 1, 3, dash))
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
    """One panel as its 16 lines of 64 bytes, top line first.
    forms: 16 states, one per line: 'vnni' (a pair row) | 'rm' (one line of a
    row-major token row) | 'empty'. hi_rows: line indexes drawn with a thick
    outline. col: a dword index 0..15 marked in every line (a token's VNNI
    column); col_read: as a read (dashed). read_all: dashed outline round the
    panel = the 1 KiB is read. cols_empty / cols_live: VNNI columns with no
    saved row, or the live mask of the reader."""
    lh = h / 16
    o = []
    for i, f in enumerate(forms):
        ly = y + i * lh
        if f == "vnni":
            o.append(rect(x, ly, w, lh, C["vnni_fill"], C["vnni"], 0.5, 0))
        elif f == "rm":
            o.append(rect(x, ly, w, lh, C["rm_fill"], C["rm"], 0.5, 0))
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
    """One pair row (64 bytes) as 16 dwords, one per token of the block."""
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


def block_panels(x, y, c, forms4, pw=118, ph=72, gap=14, labels=True, **kw):
    """The 4 panels (s, c), s = 0..3, of token block c = the block's 4 KiB."""
    o = []
    for s in range(4):
        px = x + s * (pw + gap)
        if labels:
            o.append(text(px + pw / 2, y - 5, f"panel ({s},{c}) #{4 * s + c}", 9, "middle",
                          True, fill=C["muted"]))
        k = dict(kw)
        if "hi_rows" in k and isinstance(k["hi_rows"], dict):
            k["hi_rows"] = k["hi_rows"].get(s, ())
        o.append(panel_lines(px, y, pw, ph, forms4[s], **k))
    return "".join(o)


def bits64(x, y, mask, cell=9, gap=1, on="rows"):
    """k_rows_saved_: 64 squares, bit 0 first, grouped 16 per block."""
    bits = "".join("1" if (mask >> i) & 1 else "0" for i in range(64))
    return bit_row(x, y, bits, cell, gap, C[on + "_fill"], C[on], group=16, group_gap=8)


def bits4(x, y, mask, cell=14, gap=2, on="blk"):
    """k_vnni_blocks_: 4 squares, bit 0 first."""
    bits = "".join("1" if (mask >> i) & 1 else "0" for i in range(4))
    return bit_row(x, y, bits, cell, gap, C[on + "_fill"], C[on], group=0)


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


def _band(o, boxes, fid, y, header, callers, callers_ref, callers_reg, cells, callees,
          cx0=245, cw_total=740, cell_h=62, callers_h=96, tag="new", fill="#fff",
          stroke=None):
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
        o.append(fn_cell(x, y, cw, cell_h, name, desc, ref, tag, fill, stroke or C["ink"]))
        boxes.append((name, ref))
        cl = callees[i]
        for d in cl:
            _w(d, 9, cw - 4, False, f"callee {name}")
        o.append(lines(x + 2, y + cell_h + 11, cl, 9, 10.5, fill=C["muted"]))
    return y + max(cell_h + 10.5 * max(len(c) for c in callees) + 20, callers_h + 14)


# ---------------------------------------------------------------------------
# B1: data model: the plane, block 2 in its two forms


def b1():
    fid = "k_vnni-b1"
    W, H = 1000, 600
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "rm": C["rm"]})]
    # ---- the plane grid -------------------------------------------------------
    gx, gy, cw, ch = 40, 44, 56, 44
    o.append(text(gx, 20, "the plane: 16 panels (s, c), index 4 s + c", 11, weight=700))
    o.append(plane_grid(gx, gy, cw, ch, states=["vnni", "vnni", "rm", "empty"],
                        hi=(EX["s"], EX["c"]), block=BLOCK_2))
    boxes.append(("plane", "k_vnni.hpp:20-29 (a plane is K for one KV head of one page)"))
    boxes.append(("panel (s,c) #4s+c", "k_vnni.hpp:29-30 (one (s, c) is one 1 KiB panel)"))
    gb = gy + 4 * ch + 3 * 4
    o.append(lines(gx, gb + 18, [
        "slot 5, KV head 0, page 7. Column c = token block c:",
        "blocks 0 and 1 converted (VNNI), block 2 row-major",
        "(14 rows), block 3 no row saved. A block's bytes are",
        "its 4 panels (s, c): 4 KiB of its own, in either form."],
        9, 11))
    o.append(text(gx, gb + 64, "[k_vnni.hpp:405-411; kv_cache.hpp:711-720]", 8.5, mono=True,
                  fill=C["cite"]))
    boxes.append(("token block c", "k_vnni.hpp:25-27, 68-69 (BLOCK_TOKENS_16, TOKEN_BLOCKS_4); 405-411"))
    # ---- block 2 in its two forms --------------------------------------------
    bx, pw, ph, pg = 340, 112, 72, 14
    # row-major form (the current state)
    ry = 60
    o.append(text(bx, 20, "block 2 (page offsets 32..47) now: the row-major form, "
                  "rows 32..45 saved", 11, weight=700, fill=C["rm"]))
    o.append(text(bx, 34, "panel (t / 4, 2) holds the rows of tokens 4 (t / 4) .. 4 (t / 4) + 3, "
                  "256 B each; token 37 = panel (1,2) #6, row 1", 9, fill=C["muted"]))
    forms_now = rm_forms(BLOCK2_ROWS_SAVED)
    p_step, t_lines = token_rows(EX["token"])
    o.append(block_panels(bx, ry, BLOCK_2, forms_now, pw, ph, pg,
                          hi_rows={p_step: t_lines}))
    boxes.append(("block 2, row-major form (rows 32..45)", "k_vnni.hpp:403-411"))
    for s in range(4):
        px = bx + s * (pw + pg)
        for r in range(4):
            tokn = 32 + 4 * s + r
            o.append(text(px + pw + 2, ry + (4 * r + 2.6) * ph / 16, str(tokn), 7.5,
                          mono=True, fill=C["rm"] if tokn == EX["token"] else C["muted"]))
    o.append(label_box(bx + 4 * (pw + pg) + 14, ry - 2, 128, 76, "token row", [
        "256 B = Cols bf16 in", "dimension order = 4", "whole 64-byte lines"],
        C["rm_fill"], C["rm"], 10.5, ref="k_vnni.hpp:407-408, 441-442"))
    boxes.append(("token row", "k_vnni.hpp:407-408 (token t of block c owns 256 contiguous bytes); 441-442"))
    o.append(card_arrow(fid, "rm", [(bx + 1.5 * (pw + pg) - pg / 2, ry + ph + 8),
                                    (bx + 1.5 * (pw + pg) - pg / 2, ry + ph + 30)],
                        C["rm"], "1 panel -> PANEL_ROWS_4 = 4 token rows of 256 B  [k_vnni.hpp:87-89, 409-410]",
                        label_dx=-150, label_dy=28, size=9, anchor="start"))
    # the two addresses of the worked example
    fy = ry + ph + 66
    f1 = (f"row_major_row(plane, 37): panel ({p_step},2) #{EX['rm']['panel']}, row {EX['rm']['row']} = "
          f"element ({p_step} * 4 + 2) * 512 + {EX['rm']['row']} * 128 = {EX['rm']['elem']}; "
          f"dim 70 at {EX['rm_dim_elem']}, byte {EX['rm_dim_byte']}")
    _w(f1, 9, W - bx - 10, True, "b1 f1")
    o.append(text(bx, fy, f1, 9, mono=True))
    o.append(text(bx, fy + 12, "[k_vnni.hpp:425-439]", 8.5, mono=True, fill=C["cite"]))
    # VNNI form (after the conversion)
    vy = fy + 48
    o.append(text(bx, vy - 22, "block 2 after block_to_vnni (the forward end of the pass "
                  "that saves offset 47): the VNNI form", 11, weight=700, fill=C["vnni"]))
    o.append(text(bx, vy - 9, "panel (s, 2) = 16 pair rows of 64 B: dimension pairs of "
                  "step s for tokens 32..47; token 37 = dword t = 5 of every row", 9,
                  fill=C["muted"]))
    o.append(block_panels(bx, vy, BLOCK_2, [["vnni"] * 16 for _ in range(4)], pw, ph, pg,
                          labels=False, hi_rows={EX["s"]: [EX["dp"]]}, col=EX["t"]))
    boxes.append(("block 2, VNNI form (after block_to_vnni)", "k_vnni.hpp:24-32, 416-418"))
    o.append(label_box(bx + 4 * (pw + pg) + 14, vy - 2, 128, 76, "pair row", [
        "64 B line: one dimension", "pair of 16 tokens; 16", "pair rows per panel"],
        C["vnni_fill"], C["vnni"], 10.5, ref="k_vnni.hpp:17-18, 29"))
    boxes.append(("pair row", "k_vnni.hpp:17-18 (one 64-byte row holds that dimension pair for 16 consecutive tokens); 29"))
    o.append(card_arrow(fid, "vnni", [(bx + 1.5 * (pw + pg) - pg / 2, vy + ph + 8),
                                      (bx + 1.5 * (pw + pg) - pg / 2, vy + ph + 30)],
                        C["vnni"], "1 panel -> STEP_PAIRS_16 = 16 pair rows; 1 pair row -> BLOCK_TOKENS_16 = 16 dwords  [k_vnni.hpp:68, 71, 29-30]",
                        label_dx=-150, label_dy=28, size=9, anchor="start"))
    f2 = (f"k_vnni::index(37, 70) = (((2 * 4 + 2) * 16 + 3) * 16 + 5) * 2 + 0 = {EX['index']} "
          f"(byte {EX['byte']}: panel #{EX['panel']}, pair row {EX['dp']}, dword {EX['t']})")
    _w(f2, 9, W - bx - 10, True, "b1 f2")
    o.append(text(bx, vy + ph + 66, f2, 9, mono=True))
    o.append(text(bx, vy + ph + 78, "[k_vnni.hpp:126-135, 24-28]", 8.5, mono=True, fill=C["cite"]))
    # the same 4 KiB: a bracket between the two forms
    sy = vy + ph + 94
    o.append(rect(bx, sy, 640, 54, C["soft"], C["ink"], 1.2, 4))
    sl = ["the same 4 KiB: the row-major form and the VNNI form of block 2 occupy the 4 panels",
          "(s, 2) and no other block is touched by either layout. The same value (K[37][70]) sits at",
          f"element {EX['rm_dim_elem']} in one form and at element {EX['index']} in the other."]
    for s_ in sl:
        _w(s_, 9.5, 628, where="b1 same")
    o.append(lines(bx + 8, sy + 15, sl, 9.5, 12))
    o.append(cite(bx + 636, sy + 50, "k_vnni.hpp:408-411"))
    boxes.append(("the same 4 KiB (two forms of one block)", "k_vnni.hpp:408-411"))
    # ---- the entities column at the left, under the grid ------------------------
    ey = gb + 82
    ents = [
        ("plane", ["K for one KV head of one page:", "64 tokens x 128 dims = 16 KiB"],
         C["vnni_fill"], C["vnni"], "k_vnni.hpp:20-25",
         ("ink", "1 plane -> TOKEN_BLOCKS_4 = 4 blocks", "k_vnni.hpp:69")),
        ("token block c", ["16 tokens, offsets 16 c .. 16 c + 15;", "its 4 panels (s, c) = 4 KiB"],
         "#fff", C["ink"], "k_vnni.hpp:25-27, 405-411",
         ("ink", "1 block -> DIM_STEPS_4 = 4 panels", "k_vnni.hpp:72, 408-409")),
        ("panel (s, c)", ["1 KiB: 16 pair rows (VNNI form) or", "4 token rows of 256 B (row-major form)"],
         "#fff", C["ink"], "k_vnni.hpp:29-30, 87-89, 408-410", None),
    ]
    lw, bh, step = 250, 62, 84
    y = ey
    for title, sub, fill, stroke, ref, arr in ents:
        for s_ in sub:
            _w(s_, 10, lw - 8, where=f"b1 ent {title}")
        o.append(label_box(gx, y, lw, bh, title, sub, fill, stroke, 10.5, ref=ref))
        boxes.append((title + " (entity)", ref))
        if arr:
            o.append(arrow(fid, arr[0], [(gx + 40, y + bh), (gx + 40, y + step)], C["ink"], 1.4))
            o.append(text(gx + 48, y + bh + 11, arr[1], 9, fill=C["ink"], weight=600))
            o.append(text(gx + 48, y + bh + 21, f"[{arr[2]}]", 8.5, mono=True, fill=C["cite"]))
        y += step
    cap = ("B1, data model. The grid is the plane of the worked example (page 7, storage "
           "slot 5, KV head 0): 16 panels of 1 KiB, one per (dimension step s, token "
           "block c). A block owns the 4 panels of its column. Blocks 0 and 1 are "
           "converted (VNNI), block 2 holds 14 rows in the row-major form, block 3 is "
           "empty. On the right, block 2 is drawn in both forms. In the row-major form "
           "a panel holds 4 token rows of 256 bytes, and token 37 is row 1 of panel "
           "(1,2) #6. In the VNNI form a panel holds 16 pair rows of 64 bytes, and token "
           "37 is dword 5 of every pair row. Both forms are the same 4 KiB.")
    legend = [
        ("vnni", "blue: a converted block in the grid (blocks 0 and 1), the VNNI form of "
                 "block 2 (16 pair rows per panel), the plane entity and the pair row box; "
                 "blue text = the VNNI titles and how-many labels"),
        ("rm", "orange: the row-major block 2 in the grid and its row-major form (4 token "
               "rows of 4 lines per panel), and the token row box; orange text = the "
               "row-major titles, token 37's label and how-many label"),
        ("empty", "grey dashed: block 3 in the grid (no row saved), and the 2 unsaved rows "
                  "(offsets 46, 47) of block 2 in the row-major form"),
        ("orange cell, ink outline: panel (2,2) #10 in the grid, the worked example's panel "
         "of the row-major block 2", C["rm_fill"], C["ink"], False, False),
        ("solid blue column, ink outline: dword t = 5 (token 37) in every pair row of the "
         "VNNI form", C["vnni"], C["ink"], False, False),
        ("ink frame: block 2's column in the grid, panel (2,2) #10 (drawn heavier), token "
         "37's 4 lines in panel (1,2) and pair row 3 of panel (2,2), and each panel's "
         "outline", "none", C["ink"], False, False),
        ("box", "white box, ink outline: the entities token block c and panel (s, c); "
                "name in bold monospace, description in grey sans-serif"),
        ("ctx_ink", "grey box, ink outline: the note on the same 4 KiB"),
        ("arrow", "ink arrow: a containment with its how-many (plane -> blocks, block -> "
                  "panels)"),
        ("orange arrow: 1 panel -> 4 token rows (the row-major form)", "arrow", C["rm"]),
        ("blue arrow: 1 panel -> 16 pair rows, 1 pair row -> 16 dwords (the VNNI form)",
         "arrow", C["vnni"]),
        ("font_mono", "monospace = a name or a value from the code: panel indexes, token "
                      "numbers, the two address formulas, the entity titles"),
        ("font_sans", "sans-serif = the titles, the descriptions, the how-many labels and "
                      "the notes"),
        ("font_cite", "small grey monospace = the lines that define a box or an arrow "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Data model: one K plane and the two forms of one 16-token block",
                  "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B2: the bit model


def b2():
    fid = "k_vnni-b2"
    W, H = 1000, 630
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "rows": C["rows"], "blk": C["blk"],
                           "q": C["q"], "pend": C["pend"]})]
    o.append(text(20, 20, "the K layout state of one page for one storage slot (worked "
                  "example: slot 5 after offset 45 was saved)", 11.5, weight=700))
    o.append(text(20, 34, "kept by the page (kv_cache.hpp); the bit helpers of this file "
                  "name the bits", 9.5, fill=C["muted"]))
    # k_rows_saved_
    ry = 58
    o.append(text(20, ry + 10, "k_rows_saved_[5]", 11, mono=True, weight=700))
    o.append(text(170, ry + 10, "uint64_t: one bit per page offset, bit 0 first; bits "
                  "0..45 set = 0x3fff_ffff_ffff", 9.5, fill=C["ink"]))
    svg, xe = bits64(20, ry + 18, ROWS_MASK)
    o.append(svg)
    for c in range(4):
        x0 = 20 + c * (16 * 10 + 8)
        o.append(text(x0 + 80, ry + 40, f"block {c}: bits {16 * c}..{16 * c + 15}", 8.5,
                      "middle", fill=C["muted"]))
    o.append(text(20, ry + 56, "offset_bit(offset) = uint64_t{1} << offset: the bit of one "
                  "row  [k_vnni.hpp:97-101]", 9.5, mono=True))
    o.append(text(20, ry + 68, "k_block_bits(c) = FULL_BLOCK_0XFFFF << (c * 16): the 16 "
                  "bits of block c  [kv_cache.hpp:2540-2544]", 9.5, mono=True))
    o.append(cite(xe + 160, ry + 10, "kv_cache.hpp:2639-2648"))
    boxes.append(("k_rows_saved_[5]", "kv_cache.hpp:2639-2648"))
    boxes.append(("offset_bit(offset)", "k_vnni.hpp:97-101"))
    boxes.append(("k_block_bits(c)", "kv_cache.hpp:2540-2544"))
    # k_vnni_blocks_
    by = ry + 92
    o.append(text(20, by + 10, "k_vnni_blocks_[5]", 11, mono=True, weight=700))
    o.append(text(170, by + 10, "uint8_t: one bit per 16-token block, bit 0 first; bits 0 "
                  "and 1 set = 0b0011", 9.5, fill=C["ink"]))
    svg, xb = bits4(20, by + 18, BLOCKS_MASK)
    o.append(svg)
    for c in range(4):
        o.append(text(20 + c * 16 + 7, by + 44, str(c), 8.5, "middle", True, fill=C["muted"]))
    o.append(text(20, by + 60, "block_bit(c) = uint8_t(1u << c): the bit of block c  "
                  "[k_vnni.hpp:93-96]", 9.5, mono=True))
    o.append(text(20, by + 72, "BLOCKS_PER_PAGE_MASK_0XF = 0xf = block_bit(4) - 1: every "
                  "block of the page  [k_vnni.hpp:90-92, 108-109]", 9.5, mono=True))
    o.append(cite(xe + 160, by + 10, "kv_cache.hpp:2649-2653"))
    boxes.append(("k_vnni_blocks_[5]", "kv_cache.hpp:2649-2653"))
    boxes.append(("block_bit(c)", "k_vnni.hpp:93-96"))
    boxes.append(("BLOCKS_PER_PAGE_MASK_0XF", "k_vnni.hpp:90-92"))
    # the derived block states
    sy = by + 96
    o.append(text(20, sy + 10, "what the two words say about each block (the state names "
                  "used on all three pages)", 11, weight=700))
    states = [
        ("block 0", "converted: VNNI layout", "16 row bits set, block bit set",
         C["vnni_fill"], C["vnni"], None),
        ("block 1", "converted: VNNI layout", "16 row bits set, block bit set",
         C["vnni_fill"], C["vnni"], None),
        ("block 2", "row-major rows", "14 of 16 row bits set, block bit clear",
         C["rm_fill"], C["rm"], None),
        ("block 3", "no row saved", "no row bit, block bit clear",
         C["empty_fill"], C["empty"], "3 2"),
    ]
    for i, (name, st, why, fill, stroke, dash) in enumerate(states):
        x = 20 + i * 240
        o.append(rect(x, sy + 20, 228, 50, fill, stroke, 1.4, 4, dash))
        o.append(text(x + 8, sy + 36, f"{name}: {st}", 10.5, mono=True, weight=700))
        o.append(text(x + 8, sy + 50, why, 9, fill=C["muted"]))
        o.append(cite(x + 224, sy + 66, "kv_cache.hpp:711-720"))
    boxes.append(("converted: VNNI layout (block state)", "kv_cache.hpp:716-720"))
    boxes.append(("row-major rows (block state)", "kv_cache.hpp:711-716"))
    boxes.append(("no row saved (block state)", "kv_cache.hpp:716-717"))
    # the fifth state: complete, may wait
    py = sy + 84
    o.append(rect(20, py, 468, 50, C["pend_fill"], C["pend"], 1.6, 4, "5 3"))
    o.append(text(28, py + 16, "complete, may wait", 10.5, mono=True, weight=700))
    o.append(lines(28, py + 30, ["16 row bits set, block bit clear: after the save of offset 47,",
                                 "until block_to_vnni runs at the forward end (B4 step 4)"], 9, 11,
                   fill=C["muted"]))
    o.append(cite(484, py + 46, "kv_cache.hpp:717-718"))
    boxes.append(("complete, may wait (block state)", "kv_cache.hpp:717-718"))
    o.append(rect(508, py, 472, 50, C["hw_fill"], C["hw"], 1.4, 4))
    o.append(text(516, py + 16, "row-major, no bits (hardware attention)", 10.5, mono=True, weight=700))
    o.append(lines(516, py + 30, ["a short run of a hardware-scored operation records no row bit;",
                                  "the block never leaves the row-major form"], 9, 11, fill=C["muted"]))
    o.append(cite(976, py + 46, "kv_cache.hpp:763-768"))
    boxes.append(("row-major, no bits (hardware attention) (block state)", "kv_cache.hpp:763-768"))
    # the readers of the bits
    qy = py + 66
    o.append(text(20, qy + 10, "who reads the bits through these helpers", 11, weight=700))
    readers = [
        ("note_k_row_saved", ["(after | offset_bit) & k_block_bits(c) == k_block_bits(c)",
                              "and block_bit(c) clear -> true: queue the block"],
         "kv_cache.hpp:2212-2231", C["rows_fill"], C["rows"]),
        ("k_block_is_vnni", ["k_vnni_blocks_[ix] & block_bit(offset / 16): the layout",
                             "set_k_row, get_k_row and k_row_if_row_major follow"],
         "kv_cache.hpp:2545-2551", C["blk_fill"], C["blk"]),
        ("k_layout_dense", ["page::k_vnni_blocks(slot) == BLOCKS_PER_PAGE_MASK_0XF:",
                            "the AMX kernel reads the page only then (0b0011: no)"],
         "self_attention.hpp:1915-1922", C["q_fill"], C["q"]),
        ("apply_page_tok loop", ["vnni_blocks & block_bit(i / 16): live |= offset_bit(i);",
                                 "else row_major_row(*plane, i) -> the dotter"],
         "self_attention.hpp:2008-2017", C["q_fill"], C["q"]),
    ]
    for i, (name, desc, ref, fill, stroke) in enumerate(readers):
        x = 20 + (i % 2) * 488
        yq = qy + 18 + (i // 2) * 66
        for d in desc:
            _w(d, 9, 456, where=f"b2 reader {name}")
        o.append(rect(x, yq, 472, 58, fill, stroke, 1.2, 4))
        o.append(text(x + 8, yq + 15, name, 10.5, mono=True, weight=700))
        o.append(lines(x + 8, yq + 29, desc, 9, 11, mono=True))
        o.append(cite(x + 468, yq + 55, ref))
        boxes.append((name + (" (vnni_blocks, live)" if name.startswith("apply") else ""), ref))
    cap = ("B2, the bit model. The page keeps two words per storage slot: k_rows_saved_ "
           "(one bit per page offset, the saved rows) and k_vnni_blocks_ (one bit per "
           "16-token block, the converted blocks). This file names the bits: offset_bit "
           "and block_bit, and BLOCKS_PER_PAGE_MASK_0XF for every block of a page. The "
           "worked example has bits 0..45 set and blocks 0b0011, which the four cells "
           "read as: blocks 0 and 1 converted, block 2 row-major with 14 rows, block 3 "
           "empty. The fifth and sixth states are the complete block that waits for the "
           "forward end and the block of a hardware-scored operation that keeps no bits. "
           "The bottom row names the readers of the bits.")
    legend = [
        ("rows", "green square: a k_rows_saved_ bit that is set (one square per page "
                 "offset); green box: note_k_row_saved, which sets them"),
        ("blk", "pink square: a k_vnni_blocks_ bit that is set (one square per block); "
                "pink box: k_block_is_vnni, which reads them"),
        ("bit_clear", "white square: a bit that is clear"),
        ("vnni", "blue: a converted block (blocks 0 and 1)"),
        ("rm", "orange: a row-major block (block 2)"),
        ("empty", "grey dashed: a block with no row saved (block 3)"),
        ("pend", "orange-red dashed: complete, may wait (16 row bits set, block bit clear)"),
        ("hw", "yellow: the block of a hardware-scored operation, row-major with no bits"),
        ("q", "purple: the readers on the query side, k_layout_dense and the "
              "apply_page_tok loop"),
        ("font_mono", "monospace = the two state words, the bit helpers with their "
                      "formulas, the state names and the reader names"),
        ("font_sans", "sans-serif = the titles, the meaning of each bit set and of each "
                      "state, and what each reader does"),
        ("font_cite", "small grey monospace = the lines that define a word, a helper, a "
                      "state or a reader (file:line)"),
    ]
    return figure(fid, W, H, "The bit model: the saved-row bits, the converted-block bits "
                  "and the helpers that name them", "".join(o), cap, boxes=boxes,
                  legend=legend)


# ---------------------------------------------------------------------------
# B3: function model


def b3():
    fid = "k_vnni-b3"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 18, "callers in other files", 11, weight=700, fill=C["muted"]))
    o.append(text(245, 18, "the operations of k_vnni.hpp by purpose; a cell = name, what it "
                  "does, its definition, its tag", 10, fill=C["muted"]))
    o.append(text(245, 30, "under a cell: what it calls, or who reads it", 10,
                  fill=C["muted"]))
    y = 42
    y = _band(o, boxes, fid, y, "the bit helpers (lines 87-101): who names a bit", [
        "kv_cache.hpp: note_k_row_saved 2222,",
        "2229; note_k_block_saved 2246;",
        "k_block_to_vnni_at 2265; k_block_bits",
        "2543; k_block_is_vnni 2549; k_forget_row",
        "2585-2586, 2602; copy_storage_slot",
        "2744, 2770, 2777, 2788",
        "self_attention.hpp: 1918, 2008-2009"], "kv_cache.hpp:2212, 2545, 2583, 2722", [
        ("note_k_row_saved (caller)", "kv_cache.hpp:2212-2215"),
        ("k_block_is_vnni (caller)", "kv_cache.hpp:2545-2546"),
        ("k_forget_row (caller)", "kv_cache.hpp:2583"),
        ("copy_storage_slot (caller)", "kv_cache.hpp:2722"),
        ("k_layout_dense (caller)", "self_attention.hpp:1915-1918")], [
        ("block_bit(c)", ["Bit c of a block mask", "(page::k_vnni_blocks)"],
         "k_vnni.hpp:93-96"),
        ("offset_bit(offset)", ["Bit `offset` of a page-offset", "mask (the saved rows of a page)"],
         "k_vnni.hpp:97-101"),
        ("BLOCKS_PER_PAGE_MASK_0XF", ["The 4 token blocks of a page,", "one bit each: all set"],
         "k_vnni.hpp:90-92"),
    ], [["constexpr, uint8_t(1u << c)"], ["constexpr, uint64_t{1} << offset"],
        ["= block_bit(TOKEN_BLOCKS_4) - 1", "(static_assert 108-109)"]])
    y = _band(o, boxes, fid, y, "the row-major form of a block (lines 403-459)", [
        "kv_cache.hpp: set_k_row 2301,",
        "get_k_row 2344, k_row_if_row_major",
        "2385, copy_storage_slot 2779, 2781-2782",
        "self_attention.hpp: apply_page_tok",
        "2013 (row_major_row -> the dotter)",
        "tests: t_k_vnni_layout.cpp 278, 300,",
        "310, 676, 690"], "kv_cache.hpp:2291, 2334, 2378, 2722", [
        ("page::set_k_row (caller)", "kv_cache.hpp:2291"),
        ("page::get_k_row (caller)", "kv_cache.hpp:2334"),
        ("page::k_row_if_row_major (caller)", "kv_cache.hpp:2378"),
        ("apply_page_tok (caller)", "self_attention.hpp:1847")], [
        ("PANEL_ROWS_4", ["A row-major block keeps 4 token", "rows of 256 B in each panel"],
         "k_vnni.hpp:87-89"),
        ("row_major_row", ["The token's row inside a", "row-major block, a typed view"],
         "k_vnni.hpp:425-439"),
        ("store_row_major", ["One token's row into its", "row-major block: 4 whole lines"],
         "k_vnni.hpp:441-449"),
        ("load_row_major", ["One token's row out of its", "row-major block (the inverse)"],
         "k_vnni.hpp:451-459"),
    ], [["= PANEL_ELEMS_512 / HEAD_SIZE_128", "read by row_major_row 436, 438"],
        ["-> k_vnni_access::plane +", "((t / 4) * 4 + c) * 512", "+ (t % 4) * Cols"],
        ["-> row_major_row(dst, token).data,", "memcpy(Cols * sizeof(bf16) = 256 B)"],
        ["-> row_major_row(src, token).data,", "memcpy(256 B)"]])
    y = _band(o, boxes, fid, y, "the in-place conversion of one block (lines 461-491)", [
        "kv_cache.hpp: k_block_to_vnni_at 2275",
        "(from convert_pending_k_blocks,",
        "model.hpp 3174); k_forget_row 2607;",
        "copy_storage_slot 2771 (to rows),",
        "2787 (to VNNI)",
        "tests: t_k_vnni_layout.cpp 302, 305"], "kv_cache.hpp:2261, 2583, 2722", [
        ("page::k_block_to_vnni_at (caller)", "kv_cache.hpp:2261"),
        ("convert_pending_k_blocks (caller)", "model.hpp:3170"),
        ("page::k_forget_row (caller)", "kv_cache.hpp:2583"),
        ("page::copy_storage_slot (caller)", "kv_cache.hpp:2722")], [
        ("block_to_vnni", ["Convert block c from row-major to", "the VNNI layout, in place"],
         "k_vnni.hpp:461-476"),
        ("block_to_rows", ["The inverse: block c from the VNNI", "layout back to row-major, in place"],
         "k_vnni.hpp:478-491"),
    ], [["-> 16 x load_row_major onto rows[16][Cols]", "(4 KiB stack), then store_block(plane, c,",
         "FULL_BLOCK_0XFFFF, row_ptrs)"],
        ["-> 16 x load_row onto rows[16][Cols],", "then 16 x store_row_major"]])
    y = _band(o, boxes, fid, y, "unchanged operations this PR builds on (lines 216-401)", [
        "kv_cache.hpp: set_k_row 2299 (store_row,",
        "a converted block), get_k_row 2342,",
        "set_k_block 2326 (store_block, whole",
        "blocks only now), copy_storage_slot",
        "2778 (load_row), fill_storage_slot 1887",
        "kernels/k_vnni.hpp: qk_group 60",
        "(k_vnni_access::plane)"], "kv_cache.hpp:2321; kernels/k_vnni.hpp:38", [
        ("page::set_k_block (caller)", "kv_cache.hpp:2321"),
        ("k_vnni::qk_group (caller)", "kernels/k_vnni.hpp:38")], [
        ("store_row", ["One token's row into a packed", "plane: 4 scatters, 64 slots"],
         "k_vnni.hpp:311-328"),
        ("load_row", ["The inverse of store_row:", "4 gathers of 16 dwords"],
         "k_vnni.hpp:330-345"),
        ("store_block", ["Up to 16 rows of block c in", "registers, whole-line stores"],
         "k_vnni.hpp:347-388"),
        ("k_vnni_access::plane", ["The one route from a view to", "its plane address"],
         "k_vnni.hpp:216-224"),
    ], [["in-file callers: copy_token 400"], ["in-file callers: copy_token 399,", "block_to_rows 485"],
        ["in-file caller: block_to_vnni 475", "(always FULL_BLOCK_0XFFFF now)"],
        ["in-file callers: row_major_row 435,", "store_row 320, load_row 337,", "store_block 368"]],
        tag="unchanged")
    H = int(y) + 4
    cap = ("B3, function model. Every operation this PR adds to k_vnni.hpp as a cell: "
           "its name, one line on what it does, and the lines that define it. The grey "
           "box at the left of each group names the callers in other files with their "
           "call-site lines; its citation and the register give the lines that define "
           "those callers. The last group is the unchanged operations of PR 4956 and PR "
           "4958 that the new ones call: block_to_vnni ends in store_block, block_to_rows "
           "starts with load_row, and every address goes through k_vnni_access::plane.")
    legend = [
        ("box", "white box, ink outline: one operation of k_vnni.hpp (a cell): its name "
                "in bold monospace, what it does in sans-serif, its tag and the lines "
                "that define it"),
        ("ctx", "grey box, thin grey outline: the callers in other files of one group, "
                "each with its call-site line"),
        ("arrow", "ink arrow: the callers in other files (grey box at the left) -> the "
                  "group of operations they call"),
        ("font_mono", "bold monospace = an operation's name"),
        ("font_sans", "sans-serif = what an operation does, the group headers, the "
                      "callers with their call-site lines, and what a cell calls "
                      "(grey, under the cell); grey 'unchanged' = the operation predates "
                      "this PR"),
        ("font_cite", "small grey monospace = the lines that define an operation, or "
                      "the callers of a group (file:line)"),
        ("font_tag", "bold 'new' = the operation is added by PR 4959 (the first three "
                     "groups)"),
    ]
    return figure(fid, W, H, "Function model: every operation the PR adds, its callers "
                  "and what it calls", "".join(o), cap, boxes=boxes, legend=legend)


# ---------------------------------------------------------------------------
# B4: the bytes of one block through its life


def b4_legend(x, y):
    o = []
    cx = x
    for st, lab in [("rm", "row-major token row (4 lines of 64 B)"),
                    ("vnni", "VNNI pair row (one 64 B line)"),
                    ("empty", "no row saved")]:
        if st == "empty":
            o.append(rect(cx, y, 22, 12, C["empty_fill"], C["empty"], 1, 1, "3 2"))
        else:
            o.append(rect(cx, y, 22, 12, C[st + "_fill"], C[st], 1, 1))
        o.append(text(cx + 28, y + 10, lab, 10))
        cx += 28 + text_width(lab, 10) + 18
    o.append(rect(cx, y, 22, 12, "#fff", C["ink"], 1.6, 1))
    o.append(text(cx + 28, y + 10, "thick: token 37's lines", 10))
    cx += 28 + text_width("thick: token 37's lines", 10) + 18
    o.append(rect(cx, y, 22, 12, "#fff", C["ink"], 1.2, 1, "4 3"))
    o.append(text(cx + 28, y + 10, "dashed: the 4 KiB is read", 10))
    return "".join(o)


def b4():
    fid = "k_vnni-b4"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    o.append(text(20, 20, "worked example: block 2 (page offsets 32..47) of the plane of slot "
                  "5, KV head 0, page 7; its bytes are the 4 panels (s, 2) = 4 KiB", 11,
                  weight=700))
    o.append(text(20, 36, "each panel: 16 lines of 64 bytes, drawn top to bottom; the steps "
                  "are in time order (several forward passes), not to scale", 9.5,
                  fill=C["muted"]))
    o.append(b4_legend(20, 48))
    px0, pw, ph, pg = 300, 118, 72, 14
    step_h = 150
    y = 84
    p_step, t_lines = token_rows(EX["token"])
    steps = [
        dict(n="1", title="store_row_major(plane, j, src)",
             sub=["prefill unit 2: offsets 32..40 (9 tokens): a",
                  "run shorter than a block; set_k_row stores",
                  "each row row-major [kv_cache.hpp:2301]"],
             fill=C["rm_fill"], stroke=C["rm"], ref="k_vnni.hpp:441-449",
             forms=rm_forms(range(32, 41)), hi={p_step: t_lines},
             note=["one memcpy of 256 B per token = 4 whole lines of panel (t / 4, 2); token 37 "
                   "is row 1 of panel (1,2) #6",
                   "the window thread that claimed unit 2 (main or a helper) stores; after the join, "
                   "main records bits 32..40 (note_k_row_saved: false)",
                   "[model.hpp:3297-3312, 3419-3430; kv_cache.hpp:2212-2231]"]),
        dict(n="2", title="row_major_row(plane, i) (reads)",
             sub=["decode steps 41..45 add rows the same way; the",
                  "readers of the block take its rows in place:",
                  "the dotter, and the FPGA staging"],
             fill="#fff", stroke=C["rm"], ref="k_vnni.hpp:425-439",
             forms=rm_forms(BLOCK2_ROWS_SAVED), hi={p_step: t_lines}, read_all=True,
             note=["the state drawn in B1 and B2: 14 rows (32..45), block bit clear",
                   "apply_page_tok: bit 2 of vnni_blocks clear -> s_pages[h][i] = "
                   "dot_q[h](row_major_row(*plane, i)) [self_attention.hpp:2008-2017]",
                   "the staging: k_head_fn -> k_row_if_row_major returns the row pointer, no copy "
                   "[full.hpp:2757-2759; kv_cache.hpp:2378-2387]"]),
        dict(n="3", title="store_row_major(plane, 47, src)",
             sub=["the decode step that saves offset 47, the 16th",
                  "row: still row-major; note_k_row_saved returns",
                  "true, so save_k queues the block"],
             fill=C["rm_fill"], stroke=C["rm"], ref="k_vnni.hpp:441-449",
             forms=rm_forms(range(32, 48)), hi={p_step: t_lines},
             note=["complete, may wait: 16 row bits set, block bit clear, until the forward end",
                   "pending_k_blocks_.push_back({&page 7, k_storage_of(slot 5), block 2}) on "
                   "main, after the join [model.hpp:3426-3428]",
                   "under hardware attention this step records no bit and nothing follows "
                   "[kv_cache.hpp:763-768; model.hpp:3419]"]),
        dict(n="4", title="block_to_vnni(plane, 2)",
             sub=["forward end of that pass, main thread, after",
                  "wait_for_coop_gof: convert_pending_k_blocks ->",
                  "k_block_to_vnni_at -> block_to_vnni per head"],
             fill=C["pend_fill"], stroke=C["pend"], ref="k_vnni.hpp:461-476",
             forms=[["vnni"] * 16 for _ in range(4)], hi={EX["s"]: [EX["dp"]]}, col=EX["t"],
             note=["16 x load_row_major onto rows[16][Cols] (4 KiB on the stack), then "
                   "store_block(plane, 2, FULL_BLOCK_0XFFFF, row_ptrs)",
                   "why the stack copy: store_block writes panel (s,2) while the rows of tokens "
                   "4 s .. 4 s + 3 still live there [k_vnni.hpp:461-463]",
                   "then k_vnni_blocks_[5] |= block_bit(2) (release) = 0b0111 "
                   "[kv_cache.hpp:2273-2283; model.hpp:1838-1842, 3170-3177]"]),
        dict(n="5", title="block_to_rows(plane, 2)",
             sub=["the way back: a new token takes offset 37",
                  "(k_forget_row) or a page copy lands in the",
                  "converted block (copy_storage_slot)"],
             fill=C["pend_fill"], stroke=C["pend"], ref="k_vnni.hpp:478-491",
             forms=rm_forms(range(32, 48)), hi={p_step: t_lines}, read_all=False,
             note=["16 x load_row onto rows[16][Cols] (4 KiB on the stack), then 16 x "
                   "store_row_major: the block holds its 16 rows row-major again",
                   "k_forget_row: block 2 keeps rows 32..36 below the offset, so its bytes go back "
                   "first; then bits 37..63 and block bits 2, 3 drop",
                   "[kv_cache.hpp:2577-2618 (block_to_rows at 2607); 2766-2774 (copy)]"]),
    ]
    for st in steps:
        o.append(text(20, y + 10, st["n"], 13, weight=700))
        for s_ in st["sub"]:
            _w(s_, 9.5, 242, where=f"b4 sub {st['title']}")
        o.append(label_box(36, y - 2, 250, 80, st["title"], st["sub"], st["fill"],
                           st["stroke"], 10.5, ref=st["ref"]))
        boxes.append((st["title"], st["ref"]))
        kw = {}
        if st.get("col") is not None:
            kw["col"] = st["col"]
        o.append(block_panels(px0, y + 12, BLOCK_2, st["forms"], pw, ph, pg,
                              hi_rows=st["hi"], read_all=st.get("read_all", False), **kw))
        for i, s_ in enumerate(st["note"]):
            _w(s_, 9.5 if i == 0 else 9, 690, where=f"b4 note {st['title']}")
        o.append(text(px0, y + ph + 26, st["note"][0], 9.5, fill=C["ink"]))
        o.append(lines(px0, y + ph + 38, st["note"][1:], 9, 11, fill=C["muted"]))
        y += step_h
    H = int(y) - 10
    cap = ("B4, sequencing model: the bytes of block 2 of the worked example through its "
           "life. Each row shows the block's 4 panels (4 KiB) after one operation. A run "
           "shorter than a block stores row-major rows (4 whole lines per token). The "
           "readers of the incomplete block take the rows in place through "
           "row_major_row. The 16th row is stored the same way, and the forward end "
           "then transposes the block in place through a 4 KiB stack copy "
           "(block_to_vnni). block_to_rows is the way back when a row is forgotten or "
           "a page copy lands in the block. Look at the orange lines: no VNNI pair row "
           "exists in the block before step 4.")
    legend = [
        ("rm", "orange: a row-major token row (4 lines of a panel) in steps 1, 2, 3 and 5, "
               "and the step boxes store_row_major"),
        ("white box, orange outline: step 2, the reads of the row-major form through "
         "row_major_row", "#fff", C["rm"], False, False),
        ("vnni", "blue: the VNNI pair rows of block 2 after block_to_vnni (step 4)"),
        ("pend_solid", "orange box, orange-red outline: the conversions block_to_vnni "
                       "(step 4) and block_to_rows (step 5)"),
        ("empty", "grey dashed line: a token row not saved yet (offsets 41..47 in step 1, "
                  "46..47 in step 2)"),
        ("solid blue column, ink outline: dword t = 5 (token 37) in every pair row of "
         "the VNNI form (step 4)", C["vnni"], C["ink"], False, False),
        ("ink outline: a panel's frame; drawn heavier, token 37's 4 lines (steps 1, 2, 3, "
         "5) and pair row 3 of panel (2,2) (step 4)", "none", C["ink"], False, False),
        ("dashed ink outline round the four panels: the 4 KiB is read (step 2)",
         "none", C["ink"], True, False),
        ("box", "white chip, ink outline, in the key at the top: stands for the heavier "
                "outline of token 37's lines"),
        ("white chip, dashed ink outline, in the key at the top: stands for the dashed "
         "frame of a read block", "#fff", C["ink"], True, False),
        ("font_mono", "monospace = an operation call in a step box, and the panel "
                      "labels (s,2) #n"),
        ("font_sans", "sans-serif = the worked example's header, the key, the step "
                      "numbers 1 to 5 (bold), what a step does, and the notes under the "
                      "panels"),
        ("font_cite", "small grey monospace = the lines that define a step's operation "
                      "(file:line)"),
    ]
    return figure(fid, W, H, "Sequencing model: the bytes of one block from its first "
                  "row-major row to the VNNI form and back", "".join(o), cap, boxes=boxes,
                  legend=legend)


# ---------------------------------------------------------------------------
# B5: interaction model (who calls which operation from which thread)

B5_COLUMNS = [(165, 425, "save_k of one layer", "model.hpp:3345-3440"),
              (435, 695, "scoring and staging of the pass", "self_attention.hpp:1847; gof.cpp:186"),
              (705, 835, "forward end", "model.hpp:1838-1842"),
              (845, 980, "between passes", "kv_cache.hpp:733-736")]


def b5():
    fid = "k_vnni-b5"
    W = 1000
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"]})]
    for x0, x1, name, ref in B5_COLUMNS:
        o.append(rect(x0, 12, x1 - x0, 26, C["soft"], C["line"], 1, 3))
        o.append(text((x0 + x1) / 2, 24, name, 9.5, "middle", weight=600))
        o.append(text((x0 + x1) / 2, 35, ref, 8.5, "middle", True, fill=C["cite"]))
    lanes_ = [("save_k window", "main + main helpers", 118),
              ("attention workers", "self_attention.hpp", 110),
              ("GOF staging", "workers | main", 90),
              ("scheduler thread", "tree work", 122),
              ("tests", "t_k_vnni_layout.cpp", 70)]
    ly = 46
    lane_y = {}
    for name, sub, h in lanes_:
        svg, _ = lane(20, ly, 960, h, name, sub)
        o.append(svg)
        lane_y[name] = (ly, h)
        ly += h + 4
    y, h = lane_y["save_k window"]
    o.append(lane_block(165, y + 6, 260, 106, [
        "store_k_block, per run of consecutive items:",
        "a run of 16 -> set_k_block -> store_block (VNNI",
        "at once), then note_k_block_saved [any window",
        "thread]; a shorter run -> set_k_row, which takes",
        "store_row_major (block not converted) or",
        "store_row (converted: a row saved again).",
        "After the join, main: note_k_row_saved per item;",
        "true -> pending_k_blocks_ (not under hardware",
        "attention: cached_operation_uses_hw)"],
        C["rm_fill"], C["rm"], "model.hpp:3238, 3413; kv_cache.hpp:2291", size=9))
    boxes.append(("store_k_block -> set_k_row -> store_row_major | store_row", "model.hpp:3238, 3297-3312; kv_cache.hpp:2291-2307"))
    boxes.append(("note_k_row_saved -> pending_k_blocks_", "model.hpp:3413-3432"))
    o.append(lane_block(705, y + 6, 130, 106, [
        "convert_pending_k_",
        "blocks, after run()",
        "joined its workers",
        "and wait_for_coop_",
        "gof drained: per",
        "entry k_block_to_",
        "vnni_at -> block_",
        "to_vnni x n_kv_heads;",
        "then the block bit"],
        C["pend_fill"], C["pend"], "model.hpp:1842, 3170", size=9))
    boxes.append(("convert_pending_k_blocks -> k_block_to_vnni_at -> block_to_vnni", "model.hpp:3170-3177; kv_cache.hpp:2261-2284"))
    y, h = lane_y["attention workers"]
    o.append(lane_block(165, y + 6, 260, 40, [
        "a page is read only after its K and V rows are",
        "complete (is_kv_complete); unchanged"],
        "#fff", C["ink"], "full.hpp:2744-2746", idle=True, size=9))
    boxes.append(("attention worker: waits for a complete page (is_kv_complete)", "full.hpp:2744-2746"))
    o.append(lane_block(435, y + 6, 260, 98, [
        "apply_page_tok, per page of a VNNI slot:",
        "the AMX kernel only when k_layout_dense",
        "(k_vnni_blocks == 0xf); else the loop reads",
        "vnni_blocks once: a token of a converted block",
        "-> live |= offset_bit(i); a token of a row-major",
        "block -> row_major_row(*plane, i) -> the dotter",
        "(4 lines); then qk_group(*plane, q, live, ...)",
        "scores the live tokens"],
        C["q_fill"], C["q"], "self_attention.hpp:1915-1927, 2003-2034", size=9))
    boxes.append(("apply_page_tok -> k_layout_dense | live | row_major_row -> dotter | qk_group",
                  "self_attention.hpp:1847, 1915-1927, 2003-2034"))
    y, h = lane_y["GOF staging"]
    o.append(lane_block(435, y + 6, 260, 78, [
        "gof::populate -> page_info::k_head_fn(slot, h,",
        "k_scratch): k_row_if_row_major returns the row",
        "pointer of a row-major block (no copy); a",
        "converted block is gathered with get_k_row ->",
        "load_row into the scratch row",
        "[idle attention workers: help_drain_gof; main:",
        "wait_for_coop_gof]"],
        C["hw_fill"], C["hw"], "gof.cpp:201-211; full.hpp:2747-2765", size=9))
    boxes.append(("gof::populate -> k_head_fn -> k_row_if_row_major | get_k_row -> load_row",
                  "gof.cpp:186, 201-211; full.hpp:2747-2765; kv_cache.hpp:2378-2387"))
    o.append(lane_block(705, y + 6, 130, 60, [
        "wait_for_coop_gof:",
        "main drains the",
        "staging first, then",
        "converts (above)"],
        C["hw_fill"], C["hw"], "model.hpp:1838; 3577", size=9))
    boxes.append(("wait_for_coop_gof", "model.hpp:1838, 3577"))
    y, h = lane_y["scheduler thread"]
    o.append(lane_block(845, y + 6, 135, 110, [
        "clear_kv_complete_at ->",
        "k_forget_row: a conver-",
        "ted block that keeps",
        "rows -> block_to_rows,",
        "then the bits drop.",
        "copy_from -> copy_",
        "storage_slot: block_to_",
        "rows, row copies, then",
        "block_to_vnni; bits last"],
        C["pend_fill"], C["pend"], "kv_cache.hpp:2583, 2722", size=9))
    boxes.append(("clear_kv_complete_at -> k_forget_row -> block_to_rows", "kv_cache.hpp:2509-2514, 2583-2618"))
    boxes.append(("copy_from -> copy_storage_slot -> block_to_rows, block_to_vnni", "kv_cache.hpp:2722-2812, 2815"))
    o.append(lane_block(165, y + 6, 530, 40, [
        "tree work runs between forward passes with the tree lock held: no forward pass reads",
        "the book meanwhile, so the in-place transposes of the scheduler see no reader"],
        "#fff", C["ink"], "kv_cache.hpp:733-736", idle=True, size=9))
    boxes.append(("tree work between passes: no reader (tree lock)", "kv_cache.hpp:733-736"))
    y, h = lane_y["tests"]
    o.append(lane_block(165, y + 6, 530, 58, [
        "t_k_vnni_layout.cpp: the tail block converts to VNNI and back, bit for bit (253); page K blocks",
        "turn VNNI at the 16th saved row and back when a row is forgotten (616); the EAGLE storage view",
        "keeps its own K layout state (792); forgetting a row (868); page append carries the state (906)"],
        C["soft"], C["line"], "t_k_vnni_layout.cpp:253, 616, 792, 868, 906", size=9))
    boxes.append(("TEST_CASE blocks of t_k_vnni_layout.cpp", "t_k_vnni_layout.cpp:253, 616, 792, 868, 906"))
    ry = ly + 4
    o.append(text(20, ry + 12, "rules, each cited from the comment that states it",
                  11, weight=700))
    rules = [
        ("R1", ["a block holds the VNNI layout only once all 16 of its K rows are saved; until then",
                "it holds its rows row-major inside the same 4 KiB, and no other block is touched by either layout"],
         "k_vnni.hpp:405-411"),
        ("R2", ["the operations of this file take the layout from the caller; which layout a block holds is",
                "recorded per (page, slot) by the page's converted-block bit, and every reader and writer of a row takes it from there"],
         "k_vnni.hpp:420-423; kv_cache.hpp:719-720"),
        ("R3", ["block_to_vnni runs at the forward end of the pass that saved the 16th row, after wait_for_coop_gof:",
                "the cooperative staging gather of an earlier minibatch is the reader that can still hold the block's rows row-major"],
         "k_vnni.hpp:416-418; model.hpp:3152-3160"),
        ("R4", ["every token block with a live bit must hold the VNNI layout: the caller scores the tokens of",
                "a row-major block with the row-major dotter and keeps their bits clear in the reader's mask"],
         "kernels/k_vnni.hpp:28-31"),
        ("R5", ["a whole-block save writes the VNNI form at once (store_block); the AMX kernel "
                "reads the page as its B operand once every block of the page is VNNI"],
         "k_vnni.hpp:418-420; self_attention.hpp:1915-1922"),
        ("R6", ["under hardware attention a short run records no row bit and queues no block: "
                "the block stays row-major, and a page copy does not convert it either"],
         "kv_cache.hpp:763-768"),
    ]
    yy = ry + 28
    for tag, rl, ref in rules:
        o.append(text(20, yy, tag, 10, weight=700, mono=True))
        for s_ in rl:
            _w(s_, 9.5, 932, where=f"b5 rule {tag}")
        o.append(lines(48, yy, rl, 9.5, 10))
        o.append(text(48, yy + 10 * len(rl), f"[{ref}]", 8.5, mono=True, fill=C["cite"]))
        yy += 20 + 10 * (len(rl) - 1)
    H = int(yy) - 6
    cap = ("B5, interaction model. One lane per kind of thread or caller, left to right in "
           "time order (schematic, not to scale). The save_k window (main and the main "
           "helpers) stores whole blocks in the VNNI form and shorter runs row-major; main "
           "records the row bits after the join and queues a completed block. The attention "
           "workers only read: converted blocks through the reader's live mask, row-major "
           "rows through row_major_row and the dotter. The GOF staging (the copy of K/V "
           "rows for the FPGA) reads a row-major row in place and gathers a converted one. "
           "Main converts the queued blocks at the forward end, after the staging drained. "
           "The scheduler's tree work converts back (and forth) between passes under the "
           "tree lock. R1 to R6 cite the comment that states each rule.")
    legend = [
        ("rm", "orange: the writer of the row-major form, store_k_block -> set_k_row -> "
               "store_row_major, with main's row recording after the join"),
        ("pend_solid", "orange box, orange-red outline: a conversion: convert_pending_k_blocks "
                       "-> block_to_vnni (main, forward end) and the scheduler's "
                       "block_to_rows / block_to_vnni (tree work)"),
        ("q", "purple: the attention workers' scoring, apply_page_tok -> live / "
              "row_major_row -> dotter / qk_group"),
        ("hw", "yellow: the FPGA staging path, gof::populate -> k_head_fn -> "
               "k_row_if_row_major | get_k_row, and main's wait_for_coop_gof"),
        ("ctx", "grey box, thin grey outline: a phase header of the top row, with the "
                "lines that bound the phase; and the tests block"),
        ("lane", "white frame, thin grey outline: one lane; its name at the left "
                 "in bold, its file or role under it in grey"),
        ("idle", "dashed outline: a thread waits or does not touch the block: the "
                 "attention workers before a page is complete, and the tree work's rule"),
        ("font_mono", "bold monospace = the rule tags R1 to R6"),
        ("font_sans", "sans-serif = the lane and phase names, what each block does, "
                      "and the rules"),
        ("font_cite", "small grey monospace = the lines that define a block, a phase "
                      "or a rule (file:line)"),
    ]
    return figure(fid, W, H, "Interaction model: who calls which operation from which thread",
                  "".join(o), cap, boxes=boxes, legend=legend)
