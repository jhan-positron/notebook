"""Base diagrams B1-B5 of the PR 4956 page for h/tron/kernels/k_vnni.hpp (the
AVX-512 score reader k_vnni::qk_group).

Every fact drawn here comes from the head file (a5697f86d3) and its callers.
Line numbers are head line numbers of h/tron/kernels/k_vnni.hpp
("kernels/k_vnni.hpp:NN") unless another file is named; "k_vnni.hpp:NN" is
h/tron/tensor/k_vnni.hpp.

Module-level constants and building blocks (imported by the change diagrams):
  KV_MUL_4, LIVE_0_40, MASKS, EX, mask_hex, live_bits, acc_regs, score_grid,
  panel_grid, pair_row_lanes, ctx_box, step_badge, legend_common
"""
import sys

from svg_helpers import (C, arrow, bit_row, card_arrow, cite, figure, fn_cell,
                         label_box, line, lines, marker_defs, rect, text,
                         text_width)

# ---------------------------------------------------------------------------
# The worked example (STYLE.md): a query group of kv_mul = 4 heads scores page
# 7 (storage slot 5, KV head 0). The loop of apply_page_tok marks offsets
# 0..40 in `live`. Token 37 = block c = 2, lane t = 5; dimension 70 = step 2,
# pair dp = 3.
KV_MUL_4 = 4
LIVE_0_40 = (1 << 41) - 1                      # bits 0..40 set
MASKS = [(LIVE_0_40 >> (16 * c)) & 0xffff for c in range(4)]   # kernels/k_vnni.hpp:58
assert MASKS == [0xffff, 0xffff, 0x01ff, 0x0000]
EX = dict(token=37, dim=70, c=2, t=5, step=2, dp=3, kv_mul=KV_MUL_4,
          live_tokens=41, blocks_read=3)
N_LOADS = EX["blocks_read"] * 4 * 16           # 3 blocks x DIM_STEPS_4 x STEP_PAIRS_16
assert N_LOADS == 192


def mask_hex(c):
    return f"0x{MASKS[c]:04x}"


def _w(s, size, w, mono=False, where=""):
    """Warn (stderr) when a string is wider than the space it must fit."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WIDTH {where}: '{s}' needs {tw:.0f} px, has {w}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Building blocks


def live_bits(x, y, live=LIVE_0_40, cell=9, gap=1, group_gap=8, labels=True):
    """The 64-bit live mask as 4 groups of 16 squares (one per token block c);
    a set bit is drawn in the live colour. Returns svg and the end x."""
    bits = "".join("1" if (live >> i) & 1 else "0" for i in range(64))
    svg, cx = bit_row(x, y, bits, cell, gap, C["rows_fill"], C["rows"],
                      group=16, group_gap=group_gap)
    o = [svg]
    if labels:
        gw = 16 * (cell + gap) - gap
        for c in range(4):
            gx = x + c * (gw + gap + group_gap)
            m = (live >> (16 * c)) & 0xffff
            o.append(text(gx + gw / 2, y + cell + 11, f"c = {c}: mask 0x{m:04x}", 8.5,
                          "middle", True, fill=C["muted"]))
    return "".join(o), cx


def acc_regs(x, y, w, n=KV_MUL_4, h=14, gap=4, mask=0xffff, label_x=None):
    """acc[0..n-1]: one 512-bit register per head, 16 lanes = the 16 tokens of
    block c. Lanes whose mask bit is clear are drawn empty (never stored)."""
    o = []
    lw = w / 16
    for hh in range(n):
        ry = y + hh * (h + gap)
        for t in range(16):
            on = (mask >> t) & 1
            o.append(rect(x + t * lw, ry, lw, h, C["q_fill"] if on else C["empty_fill"],
                          C["q"] if on else C["empty"], 0.8, 0, None if on else "2 2"))
        o.append(text((label_x if label_x is not None else x - 6), ry + h - 3,
                      f"acc[{hh}]", 9, "end", True))
    return "".join(o)


def score_grid(x, y, w, h, n=KV_MUL_4, live=LIVE_0_40, cell_gap=0.5):
    """s[h * s_stride + t]: n rows of 64 cells; a live token's cell is drawn in
    the query colour, the others grey dashed (left untouched)."""
    o = []
    cw, ch = w / 64, h / n
    for hh in range(n):
        for t in range(64):
            on = (live >> t) & 1
            o.append(rect(x + t * cw, y + hh * ch, cw - cell_gap, ch - cell_gap,
                          C["q_fill"] if on else C["empty_fill"],
                          C["q"] if on else C["empty"], 0.5, 0, None if on else "1 1"))
    for c in range(1, 4):
        o.append(line(x + c * 16 * cw, y - 3, x + c * 16 * cw, y + h + 3, C["muted"], 0.8))
    return "".join(o)


def panel_grid(x, y, cw, ch, gap=4, hi=None, read_blocks=(0, 1, 2), skip_block=3):
    """The plane as its 16 panels, rows = step (dimension step), columns = c
    (token block). Panels of a block the reader skips (mask 0) are grey dashed.
    hi = (step, c) is outlined thick."""
    o = []
    for c in range(4):
        o.append(text(x + c * (cw + gap) + cw / 2, y - 6, f"c = {c}", 9.5, "middle",
                      fill=C["muted"]))
    for s in range(4):
        o.append(text(x + 4 * cw + 3 * gap + 6, y + s * (ch + gap) + ch / 2 + 4,
                      f"step {s}", 9.5, fill=C["muted"]))
        for c in range(4):
            px, py = x + c * (cw + gap), y + s * (ch + gap)
            if c == skip_block:
                o.append(rect(px, py, cw, ch, C["empty_fill"], C["empty"], 1, 3, "3 2"))
            else:
                o.append(rect(px, py, cw, ch, C["vnni_fill"], C["vnni"], 1, 3))
            o.append(text(px + cw / 2, py + ch / 2 + 4, f"({s},{c})", 9.5, "middle", True))
    if hi is not None:
        s, c = hi
        o.append(rect(x + c * (cw + gap) - 2, y + s * (ch + gap) - 2, cw + 4, ch + 4,
                      "none", C["ink"], 1.6, 3))
    return "".join(o)


def pair_row_lanes(x, y, w, h, mask=0xffff, hi_t=None, base_token=0):
    """One 64-byte pair row as 16 dwords = 16 tokens (one per lane); each dword
    = 2 bf16 (dimension 2 dp low, 2 dp + 1 high). Lanes whose mask bit is clear
    are drawn grey dashed: _mm512_maskz_loadu_epi32 never reads them."""
    dw = w / 16
    o = []
    for t in range(16):
        on = (mask >> t) & 1
        f = C["vnni"] if (on and t == hi_t) else (C["vnni_fill"] if on else C["empty_fill"])
        o.append(rect(x + t * dw, y, dw, h, f, C["vnni"] if on else C["empty"],
                      1.0 if on else 0.8, 0, None if on else "2 2"))
        if on:
            o.append(line(x + t * dw + dw / 2, y + 2, x + t * dw + dw / 2, y + h - 2,
                          C["line"], 0.6, "2 2"))
        o.append(text(x + t * dw + dw / 2, y + h + 10, str(base_token + t), 8.5,
                      "middle", True, fill=C["muted"]))
    return "".join(o)


def ctx_box(x, y, w, h, title, sub, ref, size=11):
    """A context box (grey): a caller in another file, a test, a later PR."""
    _w(title, size, w - 8, True, f"ctx {title}")
    for s in sub:
        _w(s, size - 1.5, w - 8, where=f"ctx {title}")
    o = [rect(x, y, w, h, C["soft"], C["line"], 1, 4),
         text(x + w / 2, y + 15, title, size, "middle", True, weight=600),
         lines(x + w / 2, y + 29, sub, size - 1.5, 12, "middle", fill=C["muted"]),
         cite(x + w - 4, y + h - 4, ref)]
    return "".join(o)


def step_badge(x, y, n, r=9):
    """A numbered step badge (ink circle, white digit)."""
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{C["ink"]}"/>'
            + text(x, y + 3.5, str(n), 9.5, "middle", fill="#fff", weight=700))


# the fonts every figure of this page has
FONTS = ["font_mono", "font_sans", "font_cite"]


# ---------------------------------------------------------------------------
# B1: data model


def b1():
    fid = "kernels-b1"
    W, H = 1000, 620
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "q": C["q"],
                           "live": C["rows"]})]
    o.append(text(20, 20, "The inputs and the output of qk_group, as the reader sees them "
                  "(worked example: kv_mul = 4, live = page offsets 0..40)", 11,
                  weight=700))
    # ---- k_page: the plane as 16 panels ---------------------------------
    kx, ky, kw, kh = 20, 40, 330, 310
    o.append(rect(kx, ky, kw, kh, "#fff", C["ink"], 1.2, 5))
    o.append(text(kx + 8, ky + 16, "k_page: k_vnni_view<const bf16, 64, 128>", 11,
                  mono=True, weight=600))
    o.append(text(kx + 8, ky + 30, "the read-only VNNI plane of one page (page::k_packed)",
                  9.5, fill=C["muted"]))
    o.append(panel_grid(kx + 14, ky + 58, 60, 40, hi=(EX["step"], EX["c"])))
    o.append(text(kx + 8, ky + 250, "4 x 4 panels: rows = dimension step, columns = token block c",
                  9, fill=C["muted"]))
    o.append(text(kx + 8, ky + 262, "grey dashed column: block c = 3 has mask 0, its panels are", 9,
                  fill=C["muted"]))
    o.append(text(kx + 8, ky + 274, "never read (line 59). Thick frame: panel (2,2) of token 37.", 9,
                  fill=C["muted"]))
    o.append(cite(kx + kw - 4, ky + kh - 4, "kernels/k_vnni.hpp:34; k_vnni.hpp:123"))
    boxes.append(("k_page: k_vnni_view<const bf16, 64, 128>", "kernels/k_vnni.hpp:34; k_vnni.hpp:123"))
    boxes.append(("panel (step, c)", "kernels/k_vnni.hpp:65; k_vnni.hpp:70"))
    # the pair row under the plane
    prx, pry, prw = 40, 395, 290
    px_panel = kx + 14 + 2 * 64 + 30            # centre x of panel (2,2)
    px_lane = prx + (EX["t"] + 0.5) * (prw / 16)  # lane t = 5 of the pair row
    o.append(arrow(fid, "vnni", [(px_panel, ky + 58 + 2 * 44 + 42), (px_lane, pry - 4)], C["vnni"]))
    o.append(text(175, ky + 292, "1 panel -> STEP_PAIRS_16 pair rows", 9, fill=C["vnni"], weight=600))
    o.append(text(prx, pry - 20, "pair row dp = 3 of panel (2,2): 64 bytes, one token per lane",
                  9.5, weight=600))
    o.append(pair_row_lanes(prx, pry, prw, 22, mask=MASKS[2], hi_t=EX["t"], base_token=32))
    o.append(text(prx, pry + 48, "1 pair row -> BLOCK_TOKENS_16 lanes; 1 lane = 1 dword = PAIR_2 bf16",
                  9, fill=C["muted"]))
    o.append(text(prx, pry + 60, "(dimensions 2 dp and 2 dp + 1 of one token; line 67)", 9,
                  fill=C["muted"]))
    o.append(cite(prx + prw, pry + 72, "kernels/k_vnni.hpp:66-69; k_vnni.hpp:63, 68"))
    boxes.append(("pair row dp (one 64-byte line, 16 tokens x one dimension pair)",
                  "kernels/k_vnni.hpp:66-69; k_vnni.hpp:62-63, 68"))
    o.append(text(prx, pry + 95, "plane -> N_PANELS_16 panels [k_vnni.hpp:73]; the plane address comes",
                  9, fill=C["muted"]))
    o.append(text(prx, pry + 107, "from detail::k_vnni_access::plane(k_page) [kernels/k_vnni.hpp:56]", 9,
                  fill=C["muted"]))
    # ---- live (top right) ---------------------------------------------------
    lx, ly = 380, 40
    o.append(rect(lx, ly, 600, 76, "#fff", C["ink"], 1.2, 5))
    o.append(text(lx + 8, ly + 16, "live: uint64_t", 11, mono=True, weight=600))
    o.append(text(lx + 160, ly + 16, "one bit per token of the page; bit t set = score token t "
                  "(lines 24-27)", 9.5, fill=C["muted"]))
    svg, _ = live_bits(lx + 12, ly + 26, cell=8, gap=1, group_gap=10)
    o.append(svg)
    o.append(text(lx + 8, ly + 70, "1 live -> TOKEN_BLOCKS_4 masks of BLOCK_TOKENS_16 bits, one per "
                  "token block c", 9, fill=C["rows"], weight=600))
    o.append(cite(lx + 596, ly + 72, "kernels/k_vnni.hpp:36, 58"))
    boxes.append(("live: uint64_t (one bit per token)", "kernels/k_vnni.hpp:36, 58"))
    boxes.append(("mask = __mmask16(live >> (c * BLOCK_TOKENS_16))", "kernels/k_vnni.hpp:58"))
    # ---- q (right, middle) ---------------------------------------------------
    qx, qy, qw, qh = 700, 140, 280, 130
    o.append(rect(qx, qy, qw, qh, C["q_fill"], C["q"], 1.2, 5))
    o.append(text(qx + 8, qy + 16, "q: const q_scalar*", 11, mono=True, weight=600))
    o.append(cite(qx + qw - 4, qy + 14, "kernels/k_vnni.hpp:27-28, 35"))
    o.append(text(qx + 8, qy + 30, "kv_mul rows of 128 values, row stride HEAD_SIZE_128", 9.5,
                  fill=C["muted"]))
    for hh in range(KV_MUL_4):
        ry = qy + 40 + hh * 14
        o.append(rect(qx + 10, ry, 220, 11, "#fff", C["q"], 0.8, 1))
        o.append(text(qx + 236, ry + 9, f"q_{hh}", 9, mono=True))
    o.append(text(qx + 8, qy + 108, "1 q -> kv_mul rows; 1 row -> HEAD_SIZE_128 values", 9,
                  fill=C["q"], weight=600))
    o.append(text(qx + 8, qy + 122, "q_scalar = bf16, float or fp16 (lines 46, 54-55)", 9,
                  fill=C["muted"]))
    boxes.append(("q: const q_scalar* (kv_mul rows of HEAD_SIZE_128 values)",
                  "kernels/k_vnni.hpp:27-28, 35"))
    # ---- acc ------------------------------------------------------------------
    ax, ay, aw = 380, 300, 250
    o.append(rect(ax, ay, aw, 110, "#fff", C["ink"], 1.2, 5))
    o.append(text(ax + 8, ay + 16, "acc[kv_mul]: __m512", 11, mono=True, weight=600))
    o.append(text(ax + 8, ay + 30, "one accumulator register per head (lines 20, 60-63)", 9.5,
                  fill=C["muted"]))
    o.append(acc_regs(ax + 52, ay + 40, 180, h=11, gap=3, mask=MASKS[2]))
    o.append(text(ax + 8, ay + 104, "1 acc[h] -> 16 lanes = the 16 tokens of block c", 9,
                  fill=C["q"], weight=600))
    o.append(cite(ax + aw - 4, ay + 92, "kernels/k_vnni.hpp:60-63"))
    boxes.append(("acc[kv_mul]: __m512 (one register per head)", "kernels/k_vnni.hpp:20-21, 60-63"))
    o.append(text(ax + 8, ay + 124, "drawn for block c = 2 (mask 0x01ff): lanes 9..15 are never stored",
                  9, fill=C["muted"]))
    # arrows into acc
    o.append(arrow(fid, "vnni", [(kx + kw, ky + 190), (ax, ay + 40)], C["vnni"]))
    o.append(text(ax + 4, ay - 18, "per pair row: 1 masked", 9, fill=C["vnni"], weight=600))
    o.append(text(ax + 4, ay - 7, "64-byte load (lines 68-69)", 9, fill=C["vnni"], weight=600))
    o.append(arrow(fid, "live", [(600, ly + 76), (600, ay)], C["rows"]))
    o.append(text(592, 200, "mask = __mmask16(live >> (c * 16))", 9, "end", fill=C["rows"],
                  weight=600))
    o.append(text(592, 212, "(line 58): the mask of block c", 9, "end", fill=C["rows"], weight=600))
    o.append(arrow(fid, "q", [(qx + 40, qy + qh), (ax + aw - 30, ay)], C["q"]))
    o.append(text(594, 250, "per pair row and head:", 9, "end", fill=C["q"], weight=600))
    o.append(text(594, 262, "1 pair of q_h (lines 73-74, 85-87)", 9, "end", fill=C["q"], weight=600))
    # ---- s ---------------------------------------------------------------------
    sx, sy, sw, sh = 720, 300, 260, 140
    o.append(rect(sx, sy, sw, sh, "#fff", C["ink"], 1.2, 5))
    o.append(text(sx + 8, sy + 16, "s: float*  s[h * s_stride + t]", 11, mono=True, weight=600))
    o.append(text(sx + 8, sy + 30, "q_h . K_t (UNSCALED) for every live token t", 9.5,
                  fill=C["muted"]))
    o.append(score_grid(sx + 36, sy + 40, 216, 56))
    for hh in range(KV_MUL_4):
        o.append(text(sx + 32, sy + 40 + hh * 14 + 11, f"h={hh}", 8.5, "end", True))
    o.append(text(sx + 8, sy + 110, "live cells written; the other entries are left", 9,
                  fill=C["muted"]))
    o.append(text(sx + 8, sy + 122, "untouched (lines 25-26): the caller's -infinity fill", 9,
                  fill=C["muted"]))
    o.append(cite(sx + sw - 4, sy + sh - 4, "kernels/k_vnni.hpp:24-25, 37-38, 93"))
    boxes.append(("s: float* (s[h * s_stride + t])", "kernels/k_vnni.hpp:24-25, 37-38, 93"))
    o.append(arrow(fid, "q", [(ax + aw, ay + 60), (sx, ay + 60)], C["q"]))
    o.append(text(675, ay + 50, "per (c, h):", 8.5, "middle", fill=C["q"], weight=600))
    o.append(text(675, ay + 74, "1 masked store", 8.5, "middle", fill=C["q"], weight=600))
    o.append(text(sx + 8, sy + sh + 14, "of BLOCK_TOKENS_16 scores (line 93); in the caller s is",
                  9, fill=C["muted"]))
    o.append(text(sx + 8, sy + sh + 26, "s_pages[kv_mul][64] with s_stride = page_size", 9,
                  fill=C["muted"]))
    o.append(text(sx + 8, sy + sh + 38, "[self_attention.hpp:1900, 1967-1970]", 8.5, mono=True,
                  fill=C["cite"]))
    # ---- worked example note --------------------------------------------
    o.append(rect(380, 490, 600, 120, C["hi_fill"], C["ink"], 1, 5))
    o.append(text(390, 506, "Worked example", 11, weight=700))
    o.append(lines(390, 522, [
        "live = offsets 0..40 -> masks 0xffff (c = 0), 0xffff (c = 1), 0x01ff (c = 2), 0x0000 (c = 3).",
        "Block c = 3 is skipped (line 59). 3 blocks x 4 steps x 16 pair rows = 192 masked loads of 64 bytes.",
        "Token 37 is lane t = 5 of block 2: its dimension pair (70, 71) is dword 5 of pair row 3 in",
        "panel (2,2). Its 4 scores land in s[h * s_stride + 37], h = 0..3; s[h * s_stride + 41..63] stay as the",
        "caller left them.",
    ], 9.5, 13))
    o.append(cite(976, 606, "kernels/k_vnni.hpp:57-59, 93"))
    boxes.append(("Worked example (kv_mul = 4, live = 0..40)", "#kernels-b1"))
    legend = [
        ("vnni", "blue box: the VNNI plane k_page and its panels; a lane of a pair row that is loaded"),
        ("vnni_solid", "solid blue lane: the dword of token 37 (dimensions 70, 71)"),
        ("live", "green square: a token whose bit in live is set (page offsets 0..40)"),
        ("bit_clear", "white square: a clear bit of live (offsets 41..63)"),
        ("q", "violet: the query side: q rows, the accumulators acc[h], the scores written to s"),
        ("empty", "grey dashed: never read or never written: the panels of block 3, the lanes with a clear mask bit, the untouched entries of s"),
        ("hi", "pale yellow: the worked example"),
        ("box", "white box, ink outline: an argument or local of qk_group (k_page, live, acc, s)"),
        ("white row, violet outline: one query row q_h (128 values)", "#fff", C["q"], False, False),
        ("ink frame: panel (2,2), the panel of token 37 at dimension step 2", "none", C["ink"], False, False),
        ("blue arrow: a load from the plane", "arrow", C["vnni"]),
        ("violet arrow: a query pair into an accumulator; an accumulator into s", "arrow", C["q"]),
        ("green arrow: the mask of one token block", "arrow", C["rows"]),
        ("thin grey lines: the 4 token blocks of s", "line", C["muted"]),
        ("dotted grey line inside a lane: the boundary of its two bf16", "line", C["line"], True),
    ] + FONTS
    return figure(fid, W, H, "Data model: the inputs and the output of qk_group", "".join(o),
                  "The reader takes four things: the read-only VNNI plane k_page (16 panels, each 16 "
                  "pair rows of 16 tokens), the query rows q, the live mask (one bit per token) and "
                  "the output pointer s with its row stride. One accumulator register per head holds "
                  "the 16 running scores of one token block. Every arrow says how many. Worked example: "
                  "live = page offsets 0..40, so block 3 is never read and offsets 41..63 of s stay "
                  "untouched.", boxes, legend=legend)


# ---------------------------------------------------------------------------
# B2: function model


def b2():
    fid = "kernels-b2"
    W, H = 1000, 620
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "muted": C["muted"], "gone": C["gone"]})]
    o.append(text(20, 18, "callers", 11, weight=700, fill=C["muted"]))
    o.append(text(300, 18, "qk_group: the three if-constexpr branches (all new in this PR)", 11,
                  weight=700, fill=C["muted"]))
    o.append(text(700, 18, "what each branch calls", 11, weight=700, fill=C["muted"]))
    # callers
    o.append(ctx_box(20, 30, 250, 150, "apply_page_tok (self_attention.hpp)", [
        "the per-page scoring function; for a",
        "VNNI slot the loop marks each relevant",
        "token in `live` (line 1954) and, after the",
        "loop, calls qk_group once per (page, KV",
        "head) with page::k_packed, the group's q",
        "rows, live, &s_pages[0][0], page_size",
        "(lines 1963-1972); 0 live tokens: no call",
    ], "self_attention.hpp:1909, 1927, 1954, 1966-1970"))
    boxes.append(("apply_page_tok (caller)", "self_attention.hpp:1834; 1909, 1927, 1954, 1966-1970"))
    o.append(ctx_box(20, 200, 250, 96, "check_reader_against_dotter<KV_MUL>", [
        "the test: qk_group with bf16, float and",
        "fp16 queries against dotter<bf16, 128>",
        "and dotter<float, 128>, over 91 live masks;",
        "KV_MUL = 4, 20 and 32 (t_k_vnni_layout.cpp)",
    ], "t_k_vnni_layout.cpp:193, 253-255, 306-313"))
    boxes.append(("check_reader_against_dotter (test caller)", "t_k_vnni_layout.cpp:193, 253-255"))
    o.append(ctx_box(20, 316, 250, 70, "page::k_packed (kv_cache.hpp)", [
        "the read-only view of one page's plane",
        "for a slot and KV head, VNNI slots only",
        "(the k_page argument)",
    ], "kv_cache.hpp:2041-2051"))
    boxes.append(("page::k_packed (the k_page argument)", "kv_cache.hpp:2041-2051"))
    # qk_group cells
    cx, cw = 300, 310
    o.append(rect(cx - 8, 30, 408, 372, "none", C["ink"], 1.2, 6, "4 3"))
    o.append(text(cx, 46, "qk_group<kv_mul, q_scalar>(k_page, q, live, s, s_stride)", 11,
                  mono=True, weight=600))
    o.append(text(cx, 59, "scores of one query group against the live tokens of one page", 9,
                  fill=C["muted"]))
    o.append(cite(cx + 396, 398, "kernels/k_vnni.hpp:32-39"))
    boxes.append(("qk_group<kv_mul, q_scalar>", "kernels/k_vnni.hpp:32-39"))
    cells = [
        ("kv_mul > MAX_KV_MUL_16: the split", ["Two passes: heads 0..15, then the rest, each",
                                                "with its own q and s offset; no add order changes"],
         "kernels/k_vnni.hpp:40-45"),
        ("q_scalar == fp16: widen", ["Convert the kv_mul x 128 fp16 queries to float on",
                                     "the stack, call qk_group<kv_mul, float> (51), return"],
         "kernels/k_vnni.hpp:46-52"),
        ("bf16 or float q: the masked block loop", ["Per token block with a non-zero mask: zero acc,",
                                                    "4 x 16 masked loads and products, masked store"],
         "kernels/k_vnni.hpp:53-95"),
    ]
    y = 70
    for name, desc, ref in cells:
        _w(name, 11.5, cw - 16, True, f"b2 {name}")
        o.append(fn_cell(cx, y, cw, 64, name, desc, ref, "new"))
        boxes.append((name, ref))
        y += 74
    # the recursion of the split: heads 0..15 and the rest, both through the block loop
    o.append(arrow(fid, "ink", [(cx + cw, 100), (cx + cw + 12, 100), (cx + cw + 12, 250),
                                (cx + cw, 250)], C["ink"]))
    o.append(lines(cx + cw + 18, 128, ["the split", "calls", "qk_group<16>", "then qk_group",
                                       "<kv_mul - 16>", "(42-45)"], 8.5, 10.5, fill=C["muted"]))
    # callers -> qk_group
    o.append(arrow(fid, "ink", [(270, 100), (cx - 8, 100)], C["ink"]))
    o.append(arrow(fid, "ink", [(270, 240), (cx - 8, 240)], C["ink"]))
    o.append(arrow(fid, "muted", [(270, 350), (cx - 8, 350)], C["muted"]))
    # the main-branch internals
    o.append(text(cx, 310, "inside the block loop (lines 56-94):", 9.5, weight=600))
    o.append(lines(cx, 324, [
        "plane = detail::k_vnni_access::plane(k_page)                      (56)",
        "mask = __mmask16(live >> (c * 16)); if (mask == 0) continue;        (58-59)",
        "k_pairs = _mm512_maskz_loadu_epi32(mask, panel + dp * 32)          (68-69)",
        "bf16 q: acc[h] = _mm512_dpbf16_ps(acc[h], set1(q_pair), k_pairs)   (73-76)",
        "float q: k_even = slli(k_pairs, 16); k_odd = and(k_pairs, 0xffff0000) (79-82)",
        "         acc[h] = fmadd(set1(q[d]), k_even, acc[h]); then q[d + 1], k_odd  (84-87)",
    ], 8.5, 11, mono=True))
    # callees
    kx = 720
    callees = [
        ("detail::k_vnni_access::plane", ["The one route from a view to its plane address",
                                          "(friend of k_vnni_view)"], "k_vnni.hpp:188-193"),
        ("_mm512_maskz_loadu_epi32", ["One 64-byte masked load: pair row dp of panel",
                                      "(step, c); clear lanes read nothing, get 0"],
         "kernels/k_vnni.hpp:68-69"),
        ("_mm512_dpbf16_ps", ["VDPBF16PS: acc[h] += q_pair . k_pair, per lane", "(bf16 q)"],
         "kernels/k_vnni.hpp:75-76"),
        ("_mm512_slli_epi32 / _mm512_and_si512", ["Widen the even (shift) and odd (mask) bf16 of",
                                                   "each dword to fp32 (float q)"],
         "kernels/k_vnni.hpp:79-82"),
        ("_mm512_fmadd_ps", ["Two FMAs per pair row and head: q[d] * k_even,",
                             "q[d + 1] * k_odd (float q)"], "kernels/k_vnni.hpp:84-87"),
        ("_mm512_mask_storeu_ps", ["The 16 scores of (c, h) into s, live lanes only"],
         "kernels/k_vnni.hpp:92-94"),
    ]
    y = 30
    for name, desc, ref in callees:
        _w(name, 11, 260 - 16, True, f"b2 callee {name}")
        o.append(fn_cell(kx, y, 260, 56, name, desc, ref, size=11))
        boxes.append((name, ref))
        y += 62
    o.append(arrow(fid, "ink", [(cx + 400, 250), (kx - 4, 250)], C["ink"]))
    # alternatives band
    ay = 430
    o.append(text(20, ay, "the other readers of K, and why qk_group is the one a VNNI slot takes", 11,
                  weight=700, fill=C["muted"]))
    o.append(rect(20, ay + 10, 300, 80, C["rm_fill"], C["rm"], 1.2, 5))
    o.append(text(28, ay + 26, "the row-major dotter loop", 11, mono=True, weight=600))
    o.append(lines(28, ay + 40, ["dotter<scalar_t, 128> per token, inside the loop;",
                                 "compiled only for row-major slots (if constexpr",
                                 "!k_vnni_on); reads page::k, which a VNNI slot lacks"],
                   9, 11, fill=C["muted"]))
    o.append(cite(316, ay + 86, "self_attention.hpp:1916-1924, 1955-1961; kv_cache.hpp:724-727"))
    boxes.append(("the row-major dotter loop", "self_attention.hpp:1916-1924, 1955-1961; kv_cache.hpp:724-727"))
    o.append(rect(340, ay + 10, 310, 80, "#fff", C["gone"], 1.2, 5, "5 3"))
    o.append(text(348, ay + 26, "the dense AMX page path (qk_rowmajor_128x4)", 11, mono=True,
                  weight=600))
    o.append(lines(348, ay + 40, ["not compiled for a VNNI slot: its kernel reads",
                                  "row-major K (&& !k_vnni::layout_on<head_size>); so",
                                  "every page of a VNNI slot takes the software path"],
                   9, 11, fill=C["muted"]))
    o.append(cite(646, ay + 86, "self_attention.hpp:1882-1886; kv_cache.hpp:718-720"))
    boxes.append(("the dense AMX page path (qk_rowmajor_128x4), not compiled for a VNNI slot",
                  "self_attention.hpp:1882-1886; kv_cache.hpp:718-720"))
    o.append(ctx_box(670, ay + 10, 310, 80, "the VNNI AMX kernel", [
        "lands in PR 4958, not in this PR: \"VNNI K: not",
        "taken until the VNNI AMX kernel lands\"; until then",
        "TRON_AMX_DISABLE=1 changes no score of a VNNI slot",
    ], "amx_attn_iface.hpp:60-62; kv_cache.hpp:744-746"))
    boxes.append(("the VNNI AMX kernel (lands in PR 4958)", "amx_attn_iface.hpp:60-62; kv_cache.hpp:744-746"))
    o.append(arrow(fid, "gone", [(495, ay + 10), (495, 414), (cx + 180, 414)], C["gone"],
                   dash="4 3"))
    o.append(text(500, 410, "excluded by the gate; the VNNI slot falls through to qk_group", 8.5,
                  fill=C["gone"]))
    o.append(text(20, ay + 110, "visit_path::avx counts a qk_group visit, as it counts a dotter-loop "
                  "visit [attn_stats.hpp:110-116; self_attention.hpp:2009]", 9, fill=C["muted"]))
    o.append(text(20, ay + 124, "kill switch: with TRON_AMX_DISABLE=1 a TRON_K_VNNI binary still runs "
                  "qk_group, not the row-major dotter [kv_cache.hpp:740-743]", 9, fill=C["muted"]))
    legend = [
        ("box", "white box, ink outline: a function cell: name, what it does, its definition"),
        ("ctx", "grey box: a caller in another file, the test, the kernel of a later PR"),
        ("rm", "orange box: the row-major dotter loop (row-major slots only)"),
        ("gone", "red dashed: the dense AMX page path, not compiled for a VNNI slot"),
        ("ink dashed frame: the body of qk_group", "none", C["ink"], True, False),
        ("arrow", "ink arrow: a call"),
        ("arrow_muted", "grey arrow: an argument (k_page) handed in"),
        ("red dashed arrow: the path the gate excludes", "arrow", C["gone"]),
        "font_tag",
    ] + FONTS
    return figure(fid, W, H, "Function model: callers, the three branches of qk_group, callees",
                  "".join(o),
                  "apply_page_tok calls qk_group once per (page, KV head) after its loop marked "
                  "the live tokens; the test calls it with three query types. qk_group has three "
                  "if-constexpr branches: the split above 16 heads, the fp16 widening, and the masked "
                  "block loop that does the work. The bottom band shows the two other readers: the "
                  "row-major dotter loop, compiled only for row-major slots, and the dense AMX page "
                  "path, excluded by the layout gate; the VNNI AMX kernel is a later PR.",
                  boxes, legend=legend)


# ---------------------------------------------------------------------------
# B3: sequencing model


def b3():
    fid = "kernels-b3"
    W, H = 1000, 780
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "q": C["q"]})]
    o.append(text(20, 18, "The loop nest of the masked block loop (lines 57-95), on the worked "
                  "example: kv_mul = 4, live = offsets 0..40, bf16 q", 11, weight=700))
    # c lanes
    lx, ly, lw = 20, 34, 960
    o.append(text(lx, ly + 10, "for c in 0..TOKEN_BLOCKS_4 - 1 (line 57): mask = __mmask16(live >> "
                  "(c * 16)) (58); if (mask == 0) continue (59)", 10, weight=600))
    cws = [(lw - 3 * 8) / 4] * 4
    for c in range(4):
        x = lx + c * (cws[0] + 8)
        skip = MASKS[c] == 0
        o.append(rect(x, ly + 18, cws[0], 48, C["empty_fill"] if skip else C["vnni_fill"],
                      C["empty"] if skip else C["vnni"], 1.2, 4, "4 3" if skip else None))
        o.append(text(x + 8, ly + 34, f"c = {c}: mask {mask_hex(c)}", 10.5, mono=True, weight=600))
        o.append(text(x + 8, ly + 48, "skipped: continue (59)" if skip else
                      f"{bin(MASKS[c]).count('1')} live tokens: offsets {16 * c}..{16 * c + bin(MASKS[c]).count('1') - 1}",
                      9, fill=C["muted"]))
        o.append(text(x + 8, ly + 60, "" if skip else "steps 1-6 below", 8.5, fill=C["muted"]))
    o.append(cite(lx + lw, ly + 78, "kernels/k_vnni.hpp:57-59"))
    boxes.append(("for c (token block), mask", "kernels/k_vnni.hpp:57-59"))
    # the body for one block, as numbered steps
    bx, by = 20, 126
    o.append(rect(bx, by, 960, 545, "none", C["ink"], 1.2, 6))
    o.append(text(bx + 10, by + 16, "the body for one block with a non-zero mask, drawn for c = 2 "
                  "(mask 0x01ff: tokens 32..40 live, 41..47 not)", 10.5, weight=600))
    # step 1: zero acc
    sy = by + 30
    o.append(step_badge(bx + 18, sy + 10, 1))
    o.append(text(bx + 34, sy + 14, "zero the kv_mul accumulators: acc[h] = _mm512_setzero_ps() (60-63)",
                  10))
    o.append(acc_regs(bx + 100, sy + 24, 200, h=10, gap=3, mask=0xffff))
    o.append(text(bx + 310, sy + 50, "4 registers x 16 lanes = 64 running fp32 scores", 9,
                  fill=C["muted"]))
    boxes.append(("acc[h] = _mm512_setzero_ps()", "kernels/k_vnni.hpp:60-63"))
    # step 2: step loop
    sy = by + 110
    o.append(step_badge(bx + 18, sy + 10, 2))
    o.append(text(bx + 34, sy + 14, "for step in 0..DIM_STEPS_4 - 1 (64): panel = plane + (step * 4 + c) "
                  "* PANEL_ELEMS_512 (65)", 10))
    o.append(panel_grid(bx + 60, sy + 40, 54, 30, hi=(EX["step"], 2), skip_block=3))
    o.append(text(bx + 390, sy + 52, "the 4 panels of block c = 2, one per step: #2, #6, #10, #14", 9,
                  fill=C["muted"]))
    o.append(text(bx + 390, sy + 64, "(panel index step * TOKEN_BLOCKS_4 + c; 1 KiB each)", 9,
                  fill=C["muted"]))
    o.append(cite(bx + 390 + 250, sy + 78, "kernels/k_vnni.hpp:64-65"))
    boxes.append(("panel = plane + (step * TOKEN_BLOCKS_4 + c) * PANEL_ELEMS_512", "kernels/k_vnni.hpp:64-65"))
    # step 3: dp loop and the masked load
    sy = by + 300
    o.append(step_badge(bx + 18, sy + 10, 3))
    o.append(text(bx + 34, sy + 14, "for dp in 0..STEP_PAIRS_16 - 1 (66): k_pairs = _mm512_maskz_loadu_epi32"
                  "(mask, panel + dp * ROW_ELEMS_32) (68-69)", 10))
    o.append(text(bx + 34, sy + 30, "pair row dp of panel (step, 2): one token per lane; lanes 9..15 "
                  "(tokens 41..47) are not read and hold 0", 9, fill=C["muted"]))
    o.append(pair_row_lanes(bx + 60, sy + 38, 320, 18, mask=MASKS[2], hi_t=EX["t"], base_token=32))
    o.append(text(bx + 400, sy + 50, "d = step * 32 + 2 * dp (70): dimensions d, d + 1", 9.5,
                  mono=True))
    boxes.append(("k_pairs = _mm512_maskz_loadu_epi32(mask, panel + dp * ROW_ELEMS_32)",
                  "kernels/k_vnni.hpp:66-70"))
    # step 4: products
    sy = by + 385
    o.append(step_badge(bx + 18, sy + 10, 4))
    o.append(text(bx + 34, sy + 14, "for h in 0..kv_mul - 1: one product per head and pair row", 10))
    o.append(rect(bx + 34, sy + 22, 440, 54, C["q_fill"], C["q"], 1, 4))
    o.append(lines(bx + 42, sy + 36, [
        "bf16 q (71-77): q_pair = the 2 bf16 of q_h at d, d + 1 (memcpy, 73-74);",
        "acc[h] = _mm512_dpbf16_ps(acc[h], set1_epi32(q_pair), k_pairs) (75-76):",
        "16 lanes x (q[d] * k[d] + q[d + 1] * k[d + 1]) added into acc[h]",
    ], 9, 12))
    o.append(cite(bx + 470, sy + 74, "kernels/k_vnni.hpp:71-77"))
    boxes.append(("acc[h] = _mm512_dpbf16_ps(acc[h], (__m512bh)_mm512_set1_epi32(int(q_pair)), (__m512bh)k_pairs)",
                  "kernels/k_vnni.hpp:71-77"))
    o.append(rect(bx + 490, sy + 22, 450, 54, C["q_fill"], C["q"], 1, 4))
    o.append(lines(bx + 498, sy + 36, [
        "float q (78-88): k_even = castsi512_ps(slli_epi32(k_pairs, 16)), k_odd = castsi512_ps(",
        "and_si512(k_pairs, 0xffff0000)) (79-82); acc[h] = fmadd(set1_ps(q[d]), k_even, acc[h]);",
        "acc[h] = fmadd(set1_ps(q[d + 1]), k_odd, acc[h]) (84-87): 2 FMAs per head",
    ], 9, 12))
    o.append(cite(bx + 936, sy + 74, "kernels/k_vnni.hpp:78-88"))
    boxes.append(("k_even / k_odd, acc[h] = _mm512_fmadd_ps(...)", "kernels/k_vnni.hpp:78-88"))
    # step 5: store
    sy = by + 475
    o.append(step_badge(bx + 18, sy + 10, 5))
    o.append(text(bx + 34, sy + 14, "after the 4 steps: for h: _mm512_mask_storeu_ps(s + h * s_stride + "
                  "c * 16, mask, acc[h]) (92-94)", 10))
    o.append(score_grid(bx + 60, sy + 24, 320, 28, live=LIVE_0_40))
    o.append(text(bx + 400, sy + 36, "the 9 live lanes of block 2 land in s[h * s_stride + 32..40];", 9,
                  fill=C["muted"]))
    o.append(text(bx + 400, sy + 48, "lanes 9..15 are not stored (the mask), so s[.. + 41..47] stay untouched",
                  9, fill=C["muted"]))
    boxes.append(("_mm512_mask_storeu_ps(s + h * s_stride + c * BLOCK_TOKENS_16, mask, acc[h])",
                  "kernels/k_vnni.hpp:92-94"))
    # counts
    ky = by + 555
    o.append(rect(bx, ky, 960, 80, C["hi_fill"], C["ink"], 1, 5))
    o.append(text(bx + 10, ky + 16, "Instruction count of the worked example (3 blocks read, 4 steps, "
                  "16 pair rows, kv_mul = 4)", 10.5, weight=700))
    o.append(lines(bx + 10, ky + 32, [
        "masked loads: 3 x 4 x 16 = 192, each 64 bytes = 12 KiB of the 16 KiB plane (block 3 is never read).",
        "bf16 q: 192 x 4 = 768 VDPBF16PS, one per (pair row, head). float q: 192 x 2 widenings and 192 x 4 x 2 = 1536 FMAs.",
        "masked stores: 3 x 4 = 12, one per (block, head). The 4 scores of token 37 are lane 5 of acc[0..3] after block 2.",
    ], 9.5, 13))
    boxes.append(("Instruction count of the worked example", "#kernels-b3"))
    legend = [
        ("vnni", "blue: a token block the reader visits; a panel; a loaded lane of a pair row"),
        ("vnni_solid", "solid blue lane: the dword of token 37 (dimensions 70, 71)"),
        ("empty", "grey dashed: block c = 3 (mask 0, skipped) and the lanes 9..15 of block 2 (not read, not stored)"),
        ("q", "violet: the accumulators acc[h] and the products that feed them; the scores written to s"),
        ("hi", "pale yellow: the instruction count of the worked example"),
        ("ink frame: the body of the block loop for one block", "none", C["ink"], False, False),
        ("ink frame (thick): panel (2,2), the panel of dimension step 2", "none", C["ink"], False, False),
        ("thin grey lines: the 4 token blocks of s", "line", C["muted"]),
        ("dotted grey line inside a lane: the boundary of its two bf16", "line", C["line"], True),
    ] + FONTS
    return figure(fid, W, H, "Sequencing model: the loop nest of qk_group on the worked example",
                  "".join(o),
                  "Top: the block loop visits the 3 blocks whose mask is not zero and skips block 3. "
                  "Inside, for one block: zero the accumulators (1), for each of the 4 dimension steps "
                  "(2) and each of the 16 pair rows (3) one masked 64-byte load, then one product per "
                  "head (4): a VDPBF16PS for a bf16 query or two FMAs for a float query; after the 4 "
                  "steps one masked store per head (5). The yellow box counts the instructions of the "
                  "worked example.", boxes, legend=legend)


# ---------------------------------------------------------------------------
# B4: numerics model


def b4():
    fid = "kernels-b4"
    W, H = 1000, 560
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "q": C["q"], "rm": C["rm"], "vnni": C["vnni"]})]
    o.append(text(20, 18, "The numerics contract of lines 28-31: the same products as the row-major "
                  "dotter, a different order of the fp32 adds", 11, weight=700))
    # left: dotter<bf16,128> for one token
    lx, ly, lw, lh = 20, 34, 470, 250
    o.append(rect(lx, ly, lw, lh, C["rm_fill"], C["rm"], 1.2, 6))
    o.append(text(lx + 8, ly + 16, "dotter<bf16, 128>::dot(y) for ONE token t (row-major K)", 11,
                  mono=True, weight=600))
    o.append(text(lx + 8, ly + 30, "q held as 4 registers x01, x23, x45, x67 (32 bf16 each); K_t loaded "
                  "as y01..y67", 9, fill=C["muted"]))
    # 4 row loads
    for i, nm in enumerate(["y01", "y23", "y45", "y67"]):
        yy = ly + 44 + i * 16
        o.append(rect(lx + 60, yy, 220, 12, C["rm_fill"], C["rm"], 0.8, 1))
        o.append(text(lx + 56, yy + 10, nm, 9, "end", True))
        o.append(text(lx + 284, yy + 10, f"dims {32 * i}..{32 * i + 31} of K_t (64 B)", 8.5,
                      fill=C["muted"]))
    o.append(lines(lx + 8, ly + 124, [
        "sum1 = dpbf16(0, x01, y01); sum2 = dpbf16(0, x23, y23);",
        "sum1 = dpbf16(sum1, x45, y45); sum2 = dpbf16(sum2, x67, y67);",
        "return reduce_sum(sum1 + sum2);",
    ], 9, 12, mono=True))
    # the reduction picture
    o.append(rect(lx + 90, ly + 170, 180, 12, C["q_fill"], C["q"], 0.8, 1))
    o.append(text(lx + 86, ly + 180, "sum1 + sum2", 9, "end", True))
    o.append(text(lx + 274, ly + 180, "16 lanes = 16 partial sums of ONE token", 8.5, fill=C["muted"]))
    o.append(arrow(fid, "q", [(lx + 180, ly + 186), (lx + 180, ly + 206)], C["q"]))
    o.append(rect(lx + 170, ly + 208, 20, 12, C["q_fill"], C["q"], 0.8, 1))
    o.append(text(lx + 196, ly + 218, "reduce_sum: one horizontal add tree -> the scalar s_pages[h][t]",
                  8.5, fill=C["muted"]))
    o.append(text(lx + 8, ly + 234, "per token: 4 VDPBF16PS into 2 accumulators, then a horizontal "
                  "reduction of 16 lanes", 9, fill=C["muted"]))
    o.append(cite(lx + lw - 4, ly + lh - 4, "dotter.hpp:174, 211-221"))
    boxes.append(("dotter<bf16, 128>::dot (the row-major dotter)", "dotter.hpp:174, 211-221"))
    boxes.append(("reduce_sum(sum1 + sum2)", "dotter.hpp:220"))
    # right: qk_group per lane
    rx, ry, rw, rh = 510, 34, 470, 250
    o.append(rect(rx, ry, rw, rh, C["vnni_fill"], C["vnni"], 1.2, 6))
    o.append(text(rx + 8, ry + 16, "qk_group, bf16 q: acc[h] for the 16 tokens of block c", 11,
                  mono=True, weight=600))
    o.append(text(rx + 8, ry + 30, "one lane = one token; one pair row = one dimension pair of all "
                  "16 tokens", 9, fill=C["muted"]))
    for i in range(4):
        yy = ry + 44 + i * 16
        o.append(rect(rx + 60, yy, 220, 12, C["vnni_fill"], C["vnni"], 0.8, 1))
        o.append(text(rx + 56, yy + 10, f"dp {i}" if i < 3 else "dp 15", 9, "end", True))
        o.append(text(rx + 284, yy + 10, f"dims {2 * i}, {2 * i + 1} of tokens 16c..16c+15" if i < 3
                      else "dims 30, 31 ... (x 4 steps)", 8.5, fill=C["muted"]))
    o.append(lines(rx + 8, ry + 124, [
        "acc[h] = dpbf16(acc[h], set1(q_pair), k_pairs)   64 times:",
        "step 0 dp 0, dp 1, ... dp 15, step 1 dp 0, ... step 3 dp 15",
        "(no horizontal reduction; lane t IS the score of token t)",
    ], 9, 12, mono=True))
    o.append(rect(rx + 60, ry + 170, 200, 12, C["q_fill"], C["q"], 0.8, 1))
    o.append(text(rx + 56, ry + 180, "acc[h]", 9, "end", True))
    o.append(text(rx + 264, ry + 180, "16 lanes = the 16 scores of 16 tokens", 8.5, fill=C["muted"]))
    o.append(arrow(fid, "q", [(rx + 160, ry + 186), (rx + 160, ry + 206)], C["q"]))
    o.append(rect(rx + 60, ry + 208, 200, 12, C["q_fill"], C["q"], 0.8, 1))
    o.append(text(rx + 264, ry + 218, "mask store: lane t -> s[h * s_stride + t]", 8.5,
                  fill=C["muted"]))
    o.append(text(rx + 8, ry + 234, "per token: 64 VDPBF16PS adds in one lane, in (step, dp) order; "
                  "no reduction", 9, fill=C["muted"]))
    o.append(cite(rx + rw - 4, ry + rh - 4, "kernels/k_vnni.hpp:28-31, 60-63, 75-76, 93"))
    boxes.append(("qk_group, bf16 q: acc[h] per lane", "kernels/k_vnni.hpp:28-31, 60-63, 75-76, 93"))
    # middle statement
    o.append(text(500, 300, "same 64 products q_pair . k_pair per (token, head); the dotter sums them "
                  "4 pairs at a time into 2 accumulators and then across lanes,", 9.5, "middle"))
    o.append(text(500, 313, "qk_group sums them one pair at a time into one lane. "
                  "\"Only the order of the fp32 adds differs\" (line 30-31).", 9.5, "middle"))
    # float row
    fy = 330
    o.append(rect(20, fy, 470, 110, C["rm_fill"], C["rm"], 1.2, 6))
    o.append(text(28, fy + 16, "dotter<float, 128>::dot: fp32 q, K widened per 16", 11, mono=True,
                  weight=600))
    o.append(lines(28, fy + 32, [
        "x0..x7 = q as 8 fp32x16; the K row is widened by bf16s_to_fp32s per",
        "16 dimensions; sum1 = mul(x0, k0); sum2 = mul(x1, k1); then 6 fma",
        "alternating into sum1 / sum2; return reduce_sum(sum1 + sum2).",
        "fp16 q: the test widens q to float and uses this dotter.",
    ], 9, 12))
    o.append(cite(486, fy + 106, "dotter.hpp:42, 117-128; t_k_vnni_layout.cpp:268"))
    boxes.append(("dotter<float, 128>::dot", "dotter.hpp:42, 117-128"))
    o.append(rect(510, fy, 470, 110, C["vnni_fill"], C["vnni"], 1.2, 6))
    o.append(text(518, fy + 16, "qk_group, float q: 2 FMAs per pair row", 11, mono=True, weight=600))
    o.append(lines(518, fy + 32, [
        "k_even = the even bf16 of each dword shifted up 16 bits (the exact fp32),",
        "k_odd = the odd bf16 masked with 0xffff0000; acc[h] = fma(q[d], k_even, acc[h]);",
        "acc[h] = fma(q[d + 1], k_odd, acc[h]): 128 FMAs per lane in dimension order.",
        "fp16 q: qk_group widens q to float on the stack and takes this branch (47-51).",
    ], 9, 12))
    o.append(cite(976, fy + 106, "kernels/k_vnni.hpp:46-52, 78-88; k_vnni.hpp:75-77"))
    boxes.append(("qk_group, float q: k_even / k_odd and the two FMAs", "kernels/k_vnni.hpp:46-52, 78-88"))
    # the test envelope
    ty = 456
    o.append(rect(20, ty, 960, 90, C["soft"], C["line"], 1, 5))
    o.append(text(28, ty + 16, "how the contract is tested: check_reader_against_dotter (t_k_vnni_layout.cpp)",
                  10.5, weight=700))
    o.append(lines(28, ty + 32, [
        "For every live mask (all 65 prefixes 0..64, 24 random masks, bit 63 alone, bit 16 alone) and every live token t and head h:",
        "|s_bf16[h][t] - dot_bf16(K_t)| <= 1e-4 x (sum of |q[d] * k[d]|) + 1e-6, the same for the float and the fp16 query; a dead",
        "token's slot must still hold the preset -infinity. Dead tokens hold NaN poison, so a dead value reaching a live score fails.",
    ], 9, 12))
    o.append(cite(976, ty + 86, "t_k_vnni_layout.cpp:193-207, 223-232, 235-241, 270-295"))
    boxes.append(("check_reader_against_dotter: the error envelope", "t_k_vnni_layout.cpp:193-207, 290-295"))
    legend = [
        ("rm", "orange: the row-major dotter (dotter<bf16, 128>, dotter<float, 128>) and the row of one token it loads"),
        ("vnni", "blue: qk_group and the pair rows it loads (one dimension pair of 16 tokens)"),
        ("q", "violet: an accumulator register and the result it holds"),
        ("ctx", "grey box: the test that checks the contract"),
        ("violet arrow: from the accumulator to the result", "arrow", C["q"]),
    ] + FONTS
    return figure(fid, W, H, "Numerics model: the same products, a different order of the fp32 adds",
                  "".join(o),
                  "Left: the row-major dotter scores one token with 4 VDPBF16PS into two accumulators "
                  "and a horizontal reduce_sum across 16 lanes. Right: qk_group keeps one lane per token "
                  "and adds the 64 dimension-pair products into that lane in (step, dp) order, so no "
                  "reduction is needed. The products are the same; the order of the fp32 adds is not. "
                  "The bottom rows show the float query variants and the test envelope that bounds the "
                  "difference.", boxes, legend=legend)


# ---------------------------------------------------------------------------
# B5: interaction model


def b5():
    fid = "kernels-b5"
    W, H = 1000, 470
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "q": C["q"], "live": C["rows"]})]
    o.append(text(20, 18, "Who runs the reader, what it reads, and what it never touches", 11,
                  weight=700))
    # lane 1: attention worker
    y1, lh = 30, 150
    o.append(rect(20, y1, 960, lh, "#fff", C["line"], 1, 4))
    o.append(text(28, y1 + 16, "[attention worker]", 11, weight=600))
    o.append(text(28, y1 + 30, "apply_page_tok, one", 9.5, fill=C["muted"]))
    o.append(text(28, y1 + 42, "(query, page, KV head)", 9.5, fill=C["muted"]))
    x = 170
    steps = [
        (C["rows_fill"], C["rows"], 200, ["for i in begin..end: page.at_offset(i)", "visible to the query and inside the",
                                          "sliding window ->", "live |= uint64_t{1} << i;",
                                          "relevant_k_tokens++"], "self_attention.hpp:1935-1961"),
        (C["vnni_fill"], C["vnni"], 170, ["page.k_packed<geometry.kv>(slot,", "kv_head): the read-only view",
                                          "k_vnni_view<const bf16, 64, 128>", "of the page's plane"],
         "kv_cache.hpp:2041-2051"),
        (C["vnni_fill"], C["vnni"], 190, ["qk_group<kv_mul>(k_packed, q group,", "live, &s_pages[0][0], page_size):",
                                          "masked loads read the live tokens'", "dwords only (lines 26-27, 68-69)"],
         "self_attention.hpp:1966-1971"),
        (C["q_fill"], C["q"], 180, ["s_pages[kv_mul][64], a local of the", "worker, pre-filled with -infinity;",
                                    "the live entries now hold q_h . K_t;", "softmax and PV follow"],
         "self_attention.hpp:1900, 1906, 1979-"),
    ]
    for fill, stroke, w, ls, ref in steps:
        o.append(rect(x, y1 + 24, w, 100, fill, stroke, 1.2, 3))
        for s in ls:
            _w(s, 9, w - 8, where=f"b5 {ref}")
        o.append(lines(x + 5, y1 + 38, ls, 9, 11.5))
        o.append(cite(x + w - 3, y1 + 120, ref, size=8.5))
        boxes.append((ls[0], ref))
        x += w + 10
        if ref != steps[-1][4]:
            o.append(arrow(fid, "ink", [(x - 10, y1 + 74), (x, y1 + 74)], C["ink"]))
    o.append(text(170, y1 + 142, "0 live tokens: no qk_group call, the visit returns visit_path::empty "
                  "(1966, 1976-1977); otherwise visit_path::avx (2009)", 8.5, fill=C["muted"]))
    # lane 2: the writers of the plane
    y2 = 200
    o.append(rect(20, y2, 960, 110, "#fff", C["line"], 1, 4))
    o.append(text(28, y2 + 16, "[save_k thread]", 11, weight=600))
    o.append(text(28, y2 + 30, "stores one token's", 9.5, fill=C["muted"]))
    o.append(text(28, y2 + 42, "K row", 9.5, fill=C["muted"]))
    o.append(rect(170, y2 + 24, 300, 74, C["vnni_fill"], C["vnni"], 1.2, 3))
    o.append(lines(175, y2 + 38, ["pg.set_k_row<geometry.kv>(slot, kv_head, j, k_source_row(kout))",
                                  "-> store_row: 4 scatters write this token's 64 dwords (its",
                                  "column) and no other token's slots (store_row comment);",
                                  "then pg.mark_k_complete(slot, j)"], 9, 11.5))
    o.append(cite(467, y2 + 94, "model.hpp:3100-3118; kv_cache.hpp:713-717; k_vnni.hpp:251-252"))
    boxes.append(("pg.set_k_row -> store_row (the writer of a token's column)",
                  "model.hpp:3100-3118; kv_cache.hpp:713-717; k_vnni.hpp:251-252"))
    o.append(rect(490, y2 + 24, 480, 74, "#fff", C["empty"], 1.2, 3, "4 3"))
    o.append(lines(495, y2 + 38, ["a token whose live bit is clear: its dwords are never read by the reader",
                                  "(masked loads, lines 26-27). \"So unwritten tokens cannot change the result.\"",
                                  "The reader reads no completion state itself: which tokens are live is the",
                                  "caller's decision (the loop above)."], 9, 11.5))
    o.append(cite(967, y2 + 94, "kernels/k_vnni.hpp:23-27"))
    boxes.append(("a token whose live bit is clear is never read", "kernels/k_vnni.hpp:23-27"))
    # lane 3: the test
    y3 = 320
    o.append(rect(20, y3, 960, 90, "#fff", C["line"], 1, 4))
    o.append(text(28, y3 + 16, "[the test, t_k_vnni_layout]", 11, weight=600))
    o.append(rect(170, y3 + 24, 240, 56, C["empty_fill"], C["empty"], 1.2, 3, "4 3"))
    o.append(lines(175, y3 + 38, ["poison_plane: every token's slots hold", "NaN 0x7fc1, then store_row for the",
                                  "live tokens only"], 9, 11.5))
    o.append(cite(407, y3 + 76, "t_k_vnni_layout.cpp:235-241"))
    boxes.append(("poison_plane (NaN poison for dead tokens)", "t_k_vnni_layout.cpp:71-80, 235-241"))
    o.append(arrow(fid, "ink", [(410, y3 + 52), (430, y3 + 52)], C["ink"]))
    o.append(rect(430, y3 + 24, 250, 56, C["vnni_fill"], C["vnni"], 1.2, 3))
    o.append(lines(435, y3 + 38, ["qk_group<KV_MUL>(plane, q_bf16 / q_f32 /", "q_f16, live, &s[0][0], PAGE_TOKENS_64)",
                                  "for 91 live masks"], 9, 11.5))
    o.append(cite(677, y3 + 76, "t_k_vnni_layout.cpp:223-232, 253-255"))
    boxes.append(("qk_group<KV_MUL>(plane, q, live, s, PAGE_TOKENS_64) in the test", "t_k_vnni_layout.cpp:253-255"))
    o.append(arrow(fid, "ink", [(680, y3 + 52), (700, y3 + 52)], C["ink"]))
    o.append(rect(700, y3 + 24, 270, 56, C["q_fill"], C["q"], 1.2, 3))
    o.append(lines(705, y3 + 38, ["dead slots == PRESET_NEG_INF; live scores", "within the envelope of the dotter",
                                  "(a NaN that leaked in fails the check)"], 9, 11.5))
    o.append(cite(967, y3 + 76, "t_k_vnni_layout.cpp:270-295"))
    boxes.append(("dead slots == PRESET_NEG_INF; live scores within the envelope", "t_k_vnni_layout.cpp:270-295"))
    o.append(text(20, y3 + 108, "qk_group holds no state of its own: its inputs are the caller's view, "
                  "query rows and mask, its output the caller's array. Threads are lanes here, not colours.",
                  9, fill=C["muted"]))
    o.append(text(20, y3 + 122, "The thread that runs save_k and when a page's rows become visible to a "
                  "reader are decided outside this file (model.hpp, the page's completion marks).",
                  9, fill=C["muted"]))
    o.append(text(20, y3 + 136, "[model.hpp:3118; kv_cache.hpp: mark_k_complete]", 8.5, mono=True,
                  fill=C["cite"]))
    legend = [
        ("live", "green: the loop that builds the live mask"),
        ("vnni", "blue: a read or write of the VNNI plane (k_packed, qk_group, set_k_row -> store_row)"),
        ("q", "violet: the scores s_pages / s and the check of their values"),
        ("empty", "grey dashed: the tokens whose live bit is clear: never read; the NaN poison of the test"),
        ("lane", "a lane = one thread or actor (white band, thin grey outline)"),
        ("arrow", "ink arrow: the order of the steps in a lane"),
        "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Interaction model: who runs qk_group, what it reads, what it never touches",
                  "".join(o),
                  "Top lane: an attention worker builds the live mask in its loop, takes the read-only "
                  "view page::k_packed, calls qk_group and keeps the scores in its own s_pages. Middle "
                  "lane: save_k writes one token's column with store_row; the reader never reads a "
                  "token whose live bit is clear, so unwritten tokens cannot change the result. Bottom "
                  "lane: the test poisons dead tokens with NaN and checks that no poison reaches a live "
                  "score and that dead slots keep their preset.", boxes, legend=legend)
