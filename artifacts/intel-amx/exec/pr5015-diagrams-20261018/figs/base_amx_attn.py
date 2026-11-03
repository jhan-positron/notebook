"""Base diagrams B1-B4 of the PR 5015 amx_attn.cpp page (key "amx_attn").

Worked example (STYLE.md): Muse Glimmer (16 heads = kv_mul 16), one dense
64-token page, KV head 0, the element query head 9 / token 37:
s_transposed[37][9] -> tile r = 2, row 5 -> row_group 1, position 1 ->
u[1][1] lane 2 -> store_transposed_rows<2>, k = 1 -> s[9][37] -> P[9][37] ->
o[9][0..127]. transpose_sim.py computed and checked the chain.

Every fact drawn here comes from the cited head lines of
src/tron/kernels/amx_attn.cpp (5061623a34), h/tron/kernels/amx_attn_iface.hpp,
h/tron/models/self_attention.hpp and h/tron/tensor/v_vnni.hpp.

Exports for the change diagrams (from base_amx_attn import ...):
  constants: HEAD_EXAMPLE, TOKEN_EXAMPLE, TILE_R, ROW_IN_TILE, ROW_GROUP,
             POSITION, LANE, K_INDEX, SELECTORS (lane -> (pair_sel, quad_sel)),
             LANE_ROWS (lane -> "rows a..b")
  building blocks: data_box, tile_box, grid, panel_grid, p_grid, s_grid,
             reg_lanes, step_box, two_col, fit
"""
from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, line,
                         lines, marker_defs, rect, text, text_width)

# ---- the worked example ----------------------------------------------------
HEAD_EXAMPLE = 9          # query head 9 of the 16-head group
TOKEN_EXAMPLE = 37        # token 37 of the 64-token page
TILE_R = TOKEN_EXAMPLE // 16            # 2: tokens 32..47 (amx_attn.cpp:231-232)
ROW_IN_TILE = TOKEN_EXAMPLE % 16        # 5
ROW_GROUP = ROW_IN_TILE // 4            # 1: rows 4..7 (amx_attn.cpp:234-236)
POSITION = ROW_IN_TILE % 4              # 1
LANE = HEAD_EXAMPLE // 4                # 2: lane L holds column 4L+k (150-153)
K_INDEX = HEAD_EXAMPLE % 4              # 1
# selectors per lane (amx_attn.cpp:174-175; transpose_sim.py output)
SELECTORS = {0: ("0x88", "0x88"), 1: ("0xdd", "0x88"), 2: ("0x88", "0xdd"),
             3: ("0xdd", "0xdd")}
LANE_ROWS = {L: f"rows {4 * L}..{4 * L + 3}" for L in range(4)}

ink, muted = C["ink"], C["muted"]


def fit(s, size, w, mono=False, where=""):
    """Warn when a string is wider than the space it must fit (layout check)."""
    tw = text_width(s, size, mono)
    if tw > w:
        print(f"WARNING {where}: text {tw:.0f} px > {w} px: {s!r}")
    return s


def tag(x, y, s, col=None, anchor="end", size=9):
    col = col or C["new"]
    return text(x, y, s, size, anchor, fill=col, weight=700)


def data_box(x, y, w, h, name, sub, fill, stroke, ref, tag_word=None, dash=None,
             size=11):
    """A data-model box: the name (mono, bold), shape lines (sans, grey),
    the citation lower-right, an optional tag ('new' / 'changed') lower-left."""
    o = [rect(x, y, w, h, fill, stroke, 1.3, 4, dash)]
    o.append(text(x + 8, y + 15, fit(name, size, w - 16, True, name), size, mono=True,
                  weight=600))
    subs = sub if isinstance(sub, (list, tuple)) else [sub]
    o.append(lines(x + 8, y + 29, [fit(s, 9, w - 16, False, name) for s in subs], 9, 11.5,
                   fill=muted))
    if tag_word:
        o.append(tag(x + 8, y + h - 5, tag_word, anchor="start"))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def tile_box(x, y, w, h, name, holds, ref):
    """A tile register (grey-blue): its constant name and what it holds."""
    o = [rect(x, y, w, h, C["unit_fill"], C["unit"], 1.3, 4)]
    names = name if isinstance(name, (list, tuple)) else [name]
    for i, nm in enumerate(names):
        o.append(text(x + 6, y + 14 + 12 * i, fit(nm, 10, w - 12, True, nm), 10, mono=True,
                      weight=600))
    hs = holds if isinstance(holds, (list, tuple)) else [holds]
    o.append(lines(x + 6, y + 27 + 12 * (len(names) - 1),
                   [fit(t, 8.5, w - 12, False, names[0]) for t in hs], 8.5, 10.5, fill=muted))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def grid(x, y, cols, rows, cw, ch, cell):
    """A grid of small cells; cell(c, r) -> (fill, stroke, dash) or None."""
    o = []
    for r in range(rows):
        for c in range(cols):
            st = cell(c, r)
            if st is None:
                continue
            f, s, d = st
            o.append(rect(x + c * cw, y + r * ch, cw, ch, f, s, 0.7, 0, d))
    return "".join(o)


def panel_grid(x, y, group_heads, cw=6, ch=4, hi_col=None):
    """One packed-Q panel: 16 dim-pair rows x 16 columns; columns
    0..group_heads-1 are the heads (violet), the rest zero padding (dashed)."""
    def cell(c, r):
        if hi_col is not None and c == hi_col:
            return (C["hi_fill"], ink, None)
        if c < group_heads:
            return (C["q_fill"], C["q"], None)
        return (C["empty_fill"], C["empty"], "1.5 1")
    return grid(x, y, 16, 16, cw, ch, cell)


def p_grid(x, y, group_heads, cw=3, ch=5, hi=None):
    """The P scratch: 16 rows x 64 tokens; rows 0..group_heads-1 written
    (green), the rest zero padding (dashed). hi = (row, token) cell."""
    def cell(c, r):
        if hi and (c, r) == (hi[1], hi[0]):
            return (C["hi_fill"], ink, None)
        if r < group_heads:
            return (C["rows_fill"], C["rows"], None)
        return (C["empty_fill"], C["empty"], "1.5 1")
    return grid(x, y, 64, 16, cw, ch, cell)


def s_grid(x, y, group_heads, cw=3, ch=5, hi=None, tile_r=None):
    """The caller's s: group_heads rows x 64 token columns (green); rows
    group_heads..15 not written (dashed) when group_heads is 4; the 16 token
    columns of tile_r framed."""
    def cell(c, r):
        if hi and (c, r) == (hi[1], hi[0]):
            return (C["hi_fill"], ink, None)
        if r < group_heads:
            return (C["rows_fill"], C["rows"], None)
        return (C["empty_fill"], C["empty"], "1.5 1")
    o = [grid(x, y, 64, 16, cw, ch, cell)]
    if tile_r is not None:
        o.append(rect(x + tile_r * 16 * cw, y, 16 * cw, 16 * ch, "none", ink, 2.6, 0))
    return "".join(o)


def reg_lanes(x, y, w, h, labels, hi_lane=None, lane_fill=None, dashed_lanes=(),
              size=8.5):
    """A 512-bit register as 4 lanes (vermillion); labels[L] = the lane's
    text; hi_lane gets the worked example fill; dashed_lanes are drawn with a
    dashed outline (a lane the 4-head kernel does not store)."""
    lw = w / 4
    o = []
    for L in range(4):
        f = C["hi_fill"] if L == hi_lane else (lane_fill or C["pend_fill"])
        d = "4 2" if L in dashed_lanes else None
        o.append(rect(x + L * lw, y, lw, h, f, C["pend"], 1.1, 2, d))
        o.append(text(x + L * lw + lw / 2, y + h / 2 + 3, fit(labels[L], size, lw - 4, False,
                                                             "lane"), size, "middle"))
    return "".join(o)


def step_box(x, y, w, h, n, title, body, ref, fill="#fff", stroke=None, who=None):
    """A numbered step of a sequence: badge n, a bold title (mono), body
    lines (sans), citation lower-right, optional '[who]' at the right."""
    stroke = stroke or ink
    o = [rect(x, y, w, h, fill, stroke, 1.2, 4)]
    o.append(rect(x + 6, y + 6, 18, 14, ink, ink, 1, 7))
    o.append(text(x + 15, y + 17, str(n), 9.5, "middle", fill="#fff", weight=700))
    o.append(text(x + 30, y + 17, fit(title, 10, w - 120, True, title), 10, mono=True,
                  weight=600))
    if who:
        o.append(text(x + w - 8, y + 17, who, 9, "end", fill=muted, weight=600))
    bl = body if isinstance(body, (list, tuple)) else [body]
    o.append(lines(x + 30, y + 31, [fit(s, 9, w - 40, False, title) for s in bl], 9, 11.5))
    o.append(cite(x + w - 4, y + h - 4, ref))
    return "".join(o)


def two_col(x, y, w, h, left, right, ref=None):
    """A '4 heads | 16 heads' cell pair: left for GROUP_HEADS_4, right (sky
    blue) for GROUP_HEADS_16."""
    hw = w / 2
    o = [rect(x, y, hw, h, "#fff", ink, 1, 2),
         rect(x + hw, y, hw, h, C["eagle_fill"], C["eagle"], 1, 2)]
    ls = left if isinstance(left, (list, tuple)) else [left]
    rs = right if isinstance(right, (list, tuple)) else [right]
    o.append(lines(x + 5, y + 12, [fit(s, 8.5, hw - 10, False, "two_col") for s in ls], 8.5,
                   10.5))
    o.append(lines(x + hw + 5, y + 12, [fit(s, 8.5, hw - 10, False, "two_col") for s in rs],
                   8.5, 10.5))
    if ref:
        o.append(cite(x + w - 3, y + h - 3, ref))
    return "".join(o)


# =============================================================================
# B1: data model
# =============================================================================
def b1():
    fid = "amx_attn-b1"
    W = 1000
    o = [marker_defs(fid, {"ink": ink, "q": C["q"], "rm": C["rm"], "vnni": C["vnni"],
                           "rows": C["rows"], "blk": C["blk"], "muted": muted})]
    boxes = []
    o.append(text(20, 18, "The buffers of one dense (query, page) pair, QK row then PV row; "
                  "every arrow says how many", 12.5, weight=700))
    o.append(cite(W - 20, 18, "amx_attn_iface.hpp:57-69 (the contract diagram)"))
    C1, W1 = 20, 190     # inputs
    C2, W2 = 240, 230    # the packed forms
    C3, W3 = 500, 190    # tile registers
    C4, W4 = 740, 240    # outputs

    def gap_label(x, y, words, col):
        """A how-many label stacked in a narrow gap (one short word per line)."""
        return lines(x, y, words, 8, 10, "middle", fill=col, weight=600)

    # ---- QK row --------------------------------------------------------------
    o.append(text(20, 40, "QK: S^T[64][16] = K_page . Q^T, then the transposing store", 10.5,
                  weight=700))
    boxes.append(("S^T[64][16] = K_page . Q^T", "amx_attn.cpp:187-190 (the kernel comment); "
                  "amx_attn_iface.hpp:206-233 (Note [QK orientation])"))
    o.append(data_box(C1, 50, W1, 70, "q_group",
                      ["group_heads x 128 bf16, contiguous", "4 heads 1024 B, 16 heads 4096 B",
                       "q.data + kv_head * kv_mul * 128"],
                      C["q_fill"], C["q"], "amx_attn_iface.hpp:187-189"))
    boxes.append(("q_group", "amx_attn_iface.hpp:187-189 (the packer's comment: one query "
                  "group, group_heads query heads x 128 dims); self_attention.hpp:1696-1697 "
                  "(the caller's pointer)"))
    o.append(arrow(fid, "q", [(C1 + W1, 85), (C2 - 2, 85)], C["q"], 1.4))
    o.append(text(C1, 138, "pack_q_group_128x4<group_heads>:", 8.5, mono=True, fill=C["q"],
                  weight=600))
    o.append(lines(C1, 150, ["1 q_group -> 4 panels", "(HEAD_SIZE_128 / DIM_STEP_32 steps)",
                             "x 16 dim pairs x group_heads heads"], 8.5, 11, fill=C["q"],
                   weight=600))
    boxes.append(("1 q_group -> 4 panels", "amx_attn.cpp:136-138 (HEAD_SIZE_128 / DIM_STEP_32 "
                  "= 4 steps, one panel each; 16 dim pairs; group_heads heads)"))
    o.append(data_box(C2, 50, W2, 162, "packed / q_packed",
                      ["4 panels x 16 dim-pair rows x 16 cols x 2",
                       "= Q_PACK_ELEMS_2048 bf16 = 4096 B",
                       "columns 4..15 zero padding for 4 heads"],
                      C["q_fill"], C["q"], "amx_attn_iface.hpp:156-158, 197-201"))
    boxes.append(("packed / q_packed", "amx_attn_iface.hpp:156-158 (Q_PACK_ELEMS_2048), "
                  "192-201 (the layout formula); amx_attn.cpp:139 (dst index)"))
    o.append(panel_grid(C2 + 10, 104, 4, cw=6, ch=4))
    o.append(text(C2 + 10 + 48, 180, "4 heads", 8.5, "middle", fill=muted))
    o.append(panel_grid(C2 + 122, 104, 16, cw=6, ch=4, hi_col=HEAD_EXAMPLE))
    o.append(text(C2 + 122 + 48, 180, "16 heads", 8.5, "middle", fill=muted))
    o.append(text(C2 + 8, 196, "panel 0: 16 dim-pair rows x 16 columns (heads)", 8.5, fill=muted))
    boxes.append(("panel 0: 16 dim-pair rows x 16 columns (heads)", "amx_attn_iface.hpp:"
                  "197-199 (4 panels, one per 32-dim step; each panel 16 dim-pair rows x 16 "
                  "query columns); amx_attn.cpp:136-137 (the step and dim_pair loops)"))
    o.append(tile_box(C3, 50, W3, 52, "Q_TILE_6",
                      ["one panel per step (B operand)", "16 rows x 64 B"], "amx_attn.cpp:52, 207-208"))
    boxes.append(("Q_TILE_6", "amx_attn.cpp:52 (the constant), 207-208 (the load: q_packed + "
                  "step * TILE_ROWS_16 * DIM_STEP_32, stride TILE_ROW_BYTES_64)"))
    o.append(arrow(fid, "q", [(C2 + W2, 76), (C3 - 2, 76)], C["q"], 1.3))
    o.append(gap_label(C2 + W2 + 15, 56, ["4", "loads"], C["q"]))
    boxes.append(("4 loads (Q_TILE_6)", "amx_attn.cpp:206-208 (one _tile_loadd of Q per step)"))
    o.append(tile_box(C3, 112, W3, 70, "ACCUMULATOR_TILE_0..3",
                      ["16 tokens x 16 columns fp32 each", "tile j = K slice j",
                       "4 _tile_dpbf16ps each (1 per step)"], "amx_attn.cpp:44-47, 211-220"))
    boxes.append(("ACCUMULATOR_TILE_0..3", "amx_attn.cpp:40-47 (accumulator tiles hold the "
                  "running sums), 211-220 (_tile_dpbf16ps per slice and step)"))
    o.append(arrow(fid, "q", [(C3 + 95, 102), (C3 + 95, 110)], C["q"], 1.2))
    o.append(tile_box(C3, 222, W3, 62, ["K_EVEN_BLOCK_TILE_4 /", "K_ODD_BLOCK_TILE_5"],
                      ["16 tokens x 32 dims per load (A)",
                       "slices 0, 2 -> 4; slices 1, 3 -> 5"], "amx_attn.cpp:48-51, 209-219"))
    boxes.append(("K_EVEN_BLOCK_TILE_4 / K_ODD_BLOCK_TILE_5", "amx_attn.cpp:48-51 (the "
                  "constants and their comment), 209-219 (the four loads per step)"))
    o.append(arrow(fid, "rm", [(C3 + 30, 220), (C3 + 30, 184)], C["rm"], 1.2))
    o.append(text(C3 + 36, 206, "16 _tile_dpbf16ps", 8, mono=True, fill=C["rm"]))
    boxes.append(("16 _tile_dpbf16ps (QK)", "amx_attn.cpp:206-221 (4 steps x 4 slices)"))
    o.append(data_box(C1, 222, W1, 76, "k_rows = k_page.data",
                      ["64 tokens x 128 dims bf16 row-major", "one 256-byte row per token",
                       "4 slices of 16 tokens (4 tiles)"],
                      C["rm_fill"], C["rm"], "amx_attn.cpp:197-199, 70"))
    boxes.append(("k_rows = k_page.data", "amx_attn.cpp:197-199 (token 0's row; 64 "
                  "consecutive 128-dim rows); amx_attn.cpp:70 (BF16_ROW_BYTES); "
                  "amx_attn_iface.hpp:238-240 (k_page = the page's whole native K plane)"))
    o.append(card_arrow(fid, "rm", [(C1 + W1, 258), (C3 - 2, 258)], C["rm"],
                        "4 slices x 4 steps = 16 tile loads", label_dy=-6, size=8.5))
    boxes.append(("4 slices x 4 steps = 16 tile loads", "amx_attn.cpp:206-221 (the step loop: "
                  "four _tile_loadd of K per step)"))
    o.append(data_box(C4, 112, W4, 70, "s_transposed",
                      ["64 x 16 fp32: [token][query]", "(PAGE_TOKENS_64 * TILE_ROWS_16 floats)",
                       "inside the kernel, 64-byte aligned"],
                      C["rows_fill"], C["rows"], "amx_attn.cpp:200-201"))
    boxes.append(("s_transposed", "amx_attn.cpp:200-201 (the tiles produce the scores "
                  "transposed: s_transposed[token][query])"))
    o.append(arrow(fid, "rows", [(C3 + W3, 147), (C4 - 2, 147)], C["rows"], 1.3))
    o.append(gap_label(C3 + W3 + 25, 127, ["4 tile", "stores"], C["rows"]))
    boxes.append(("4 tile stores", "amx_attn.cpp:222-225 (_tile_stored x 4, TILE_FP32S apart); "
                  "60 (TILE_FP32S = 256 floats per stored tile)"))
    o.append(data_box(C4, 222, W4, 76, "s (the caller's s_pages)",
                      ["[group_heads][s_stride_floats] fp32", "64 token columns, UNSCALED",
                       "needs only group_heads rows"],
                      C["rows_fill"], C["rows"], "amx_attn_iface.hpp:235-237, 107-110"))
    boxes.append(("s (the caller's s_pages)", "amx_attn_iface.hpp:235-237 (writes "
                  "s[group_heads][s_stride_floats], all 64 token columns, UNSCALED); 107-110 "
                  "(s needs only group_heads rows); self_attention.hpp:1756 "
                  "(tensor<operation_kv_mul, page::page_size> s_pages)"))
    o.append(arrow(fid, "rows", [(C4 + W4 - 40, 182), (C4 + W4 - 40, 220)], C["rows"], 1.3))
    o.append(lines(C4 + W4 - 48, 196, ["4 tiles x (1 or 4 lanes) x 4 rows",
                                        "= group_heads rows x 64 tokens"], 8, 11, "end",
                   fill=C["rows"], weight=600))
    boxes.append(("4 tiles x (1 or 4 lanes) x 4 rows = group_heads rows x 64 tokens",
                  "amx_attn.cpp:227-230 (the transpose comment: lane 0 always, lanes 1..3 "
                  "only when group_heads is 16), 254-260"))

    # ---- PV row ----------------------------------------------------------------
    PY = 330
    o.append(text(20, PY, "PV: O[group_heads][128] = bf16(P) . V_page, P = the caller's exp rows",
                  10.5, weight=700))
    boxes.append(("O[group_heads][128] = bf16(P) . V_page", "amx_attn_iface.hpp:66-67, "
                  "249-255 (the PV kernel's comment)"))
    o.append(data_box(C1, PY + 10, W1, 70, "exp_rows",
                      ["= the caller's s_pages after exp:", "group_heads rows, row_stride_floats",
                       "P = exp(s - m_page), in place"],
                      C["rows_fill"], C["rows"], "self_attention.hpp:1766-1786"))
    boxes.append(("exp_rows", "amx_attn_iface.hpp:258-262 (the exp_rows parameter), 63-66 (the caller computes P = exp(s - m_page)), 249-251 (the caller's fp32 exp rows); self_attention.hpp:1766-1786 (the exp step), 1791-1793 (&s_pages[0][0] passed as exp_rows)"))
    o.append(arrow(fid, "rows", [(C1 + W1, PY + 45), (C2 - 2, PY + 45)], C["rows"], 1.4))
    o.append(text(C1, PY + 98, "weights_times_v_128x4<group_heads>:", 8.5, mono=True,
                  fill=C["rows"], weight=600))
    o.append(lines(C1, PY + 110, ["group_heads rows x 64 tokens -> P",
                                   "rows 0..group_heads-1 (bf16, round to",
                                   "nearest even: _mm512_cvtne2ps_pbh)"], 8.5, 11,
                   fill=C["rows"], weight=600))
    boxes.append(("group_heads rows x 64 tokens -> P rows 0..group_heads-1", "amx_attn.cpp:"
                  "285-293 (the conversion loop: q < group_heads, c += 32, "
                  "_mm512_cvtne2ps_pbh)"))
    o.append(data_box(C2, PY + 10, W2, 168, "P[TILE_ROWS_16][PAGE_TOKENS_64]",
                      ["uint16_t bf16 bit patterns, thread_local",
                       "one scratch per specialization (4 / 16)",
                       "rows group_heads..15 zero (4 heads)"],
                      C["rows_fill"], C["rows"], "amx_attn.cpp:276-284"))
    boxes.append(("P[TILE_ROWS_16][PAGE_TOKENS_64]", "amx_attn.cpp:276-284 (the comment and "
                  "the thread_local declaration)"))
    o.append(p_grid(C2 + 10, PY + 64, 4, cw=1.6, ch=4))
    o.append(text(C2 + 10 + 51, PY + 140, "4 heads", 8.5, "middle", fill=muted))
    o.append(p_grid(C2 + 122, PY + 64, 16, cw=1.6, ch=4, hi=(HEAD_EXAMPLE, TOKEN_EXAMPLE)))
    o.append(text(C2 + 122 + 51, PY + 140, "16 heads", 8.5, "middle", fill=muted))
    o.append(text(C2 + 8, PY + 160, "16 rows (one per head) x 64 tokens", 8.5, fill=muted))
    o.append(tile_box(C3, PY + 10, W3, 52, "P_TILE_4",
                      ["16 rows x 32 tokens per load", "(A operand); s = 0, 1"], "amx_attn.cpp:55, 301"))
    boxes.append(("P_TILE_4", "amx_attn.cpp:53-55 (P loads into tile 4), 301 (the load: "
                  "&P[0][s * DIM_STEP_32], P_ROW_BYTES)"))
    o.append(arrow(fid, "rows", [(C2 + W2, PY + 36), (C3 - 2, PY + 36)], C["rows"], 1.3))
    o.append(gap_label(C2 + W2 + 15, PY + 16, ["4", "loads"], C["rows"]))
    boxes.append(("4 loads (P_TILE_4)", "amx_attn.cpp:295-301 (2 halves x 2 s: one _tile_loadd "
                  "of P each)"))
    o.append(tile_box(C3, PY + 72, W3, 70, "ACCUMULATOR_TILE_0..3",
                      ["16 heads x 16 dims fp32 each", "tile j = dim slice half * 4 + j",
                       "2 _tile_dpbf16ps each per half"], "amx_attn.cpp:44-47, 306-321"))
    boxes.append(("ACCUMULATOR_TILE_0..3 (PV)", "amx_attn.cpp:296-299 (_tile_zero per half), "
                  "306-321 (_tile_dpbf16ps per dim slice)"))
    o.append(arrow(fid, "rows", [(C3 + 95, PY + 62), (C3 + 95, PY + 70)], C["rows"], 1.2))
    o.append(tile_box(C3, PY + 180, W3, 62, ["V_EVEN_SLICE_TILE_5 /", "V_ODD_SLICE_TILE_6"],
                      ["16 pair rows x 16 dims x 2 tokens (B)",
                       "slices 0, 2 -> tile 5; 1, 3 -> tile 6"], "amx_attn.cpp:56-57, 302-320"))
    boxes.append(("V_EVEN_SLICE_TILE_5 / V_ODD_SLICE_TILE_6", "amx_attn.cpp:53-57 (the "
                  "constants), 302-320 (the four V loads per s)"))
    o.append(arrow(fid, "vnni", [(C3 + 30, PY + 178), (C3 + 30, PY + 144)], C["vnni"], 1.2))
    o.append(text(C3 + 36, PY + 166, "16 _tile_dpbf16ps", 8, mono=True, fill=C["vnni"]))
    boxes.append(("16 _tile_dpbf16ps (PV)", "amx_attn.cpp:295-322 (2 halves x 2 s x 4 tiles)"))
    o.append(data_box(C1, PY + 160, W1, 86, "v_pairs",
                      ["= v_vnni_access::plane(v_page):", "32 pair rows x 128 dims x 2 tokens",
                       "bf16; pair row = tokens 2p, 2p + 1", "(V_PAIR_ROW_BYTES = 512)"],
                      C["vnni_fill"], C["vnni"], "amx_attn.cpp:271-274; v_vnni.hpp:31-46"))
    boxes.append(("v_pairs", "amx_attn.cpp:271-274 (the plane's first element; pair row s*16 "
                  "starts s*16*2*128 elements later); amx_attn.cpp:66-72 (V_PAIR_TOKENS_2, "
                  "V_PAIR_ROW_BYTES); v_vnni.hpp:31-46 (Note [VNNI Packed V layout])"))
    o.append(card_arrow(fid, "vnni", [(C1 + W1, PY + 210), (C3 - 2, PY + 210)], C["vnni"],
                        "2 halves x 2 s x 4 = 16 tile loads", label_dy=-6, size=8.5))
    boxes.append(("2 halves x 2 s x 4 = 16 tile loads", "amx_attn.cpp:295-322 (half loop, s "
                  "loop, four V loads and four _tile_dpbf16ps per s)"))
    o.append(data_box(C4, PY + 72, W4, 86, "o (the caller's amx_o)",
                      ["[16][128] fp32 = 8192 B, 64-byte aligned", "row stride 128 floats",
                       "rows group_heads..15 = products of", "the zero padding rows (4 heads)"],
                      C["blk_fill"], C["blk"], "amx_attn_iface.hpp:253-255, 97-106"))
    boxes.append(("o (the caller's amx_o)", "amx_attn_iface.hpp:253-255 (o MUST hold 16 * 128 "
                  "fp32), 93-106 (Note [Tile stores write 16 rows]); self_attention.hpp:1790 "
                  "(alignas(64) float amx_o[TILE_ROWS_16 * operation_head_size])"))
    o.append(arrow(fid, "blk", [(C3 + W3, PY + 107), (C4 - 2, PY + 107)], C["blk"], 1.3))
    o.append(gap_label(C3 + W3 + 25, PY + 87, ["2 halves", "x 4 stores"], C["blk"]))
    boxes.append(("2 halves x 4 stores (_tile_stored into o)", "amx_attn.cpp:323-326 (_tile_stored x 4 per half, o + half * 64 + 16 * j, stride O_ROW_BYTES); 73-74"))
    o.append(rect(C4, PY + 180, W4, 62, C["soft"], C["line"], 1, 4))
    o.append(text(C4 + 8, PY + 195, "[caller] v*/s*/m* update", 9.5, weight=700))
    o.append(lines(C4 + 8, PY + 208, ["reads rows 0..kv_mul-1 of amx_o",
                                       "(memcpy per head); ignores the rest"], 8.5, 10.5,
                   fill=muted))
    o.append(cite(C4 + W4 - 4, PY + 238, "self_attention.hpp:1795-1811"))
    boxes.append(("[caller] v*/s*/m* update", "self_attention.hpp:1795-1811 (the running-"
                  "softmax update from amx_o rows 0..operation_kv_mul-1); "
                  "amx_attn_iface.hpp:105 (callers read rows 0..group_heads-1)"))
    o.append(arrow(fid, "blk", [(C4 + W4 - 40, PY + 158), (C4 + W4 - 40, PY + 178)], C["blk"],
                   1.3))
    o.append(text(C4 + W4 - 48, PY + 171, "group_heads rows", 8, "end", fill=C["blk"],
                  weight=600))
    boxes.append(("group_heads rows (read by the caller)", "self_attention.hpp:1787-1789 (only rows 0..kv_mul-1 of amx_o carry the result), 1795-1811"))

    # ---- the worked example strip -------------------------------------------------
    EY = PY + 258
    o.append(rect(20, EY, W - 40, 52, C["hi_fill"], ink, 1, 4))
    o.append(text(28, EY + 15, "worked example (Muse Glimmer, 16 heads): query head 9, token 37",
                  9.5, weight=700))
    o.append(text(28, EY + 30, "QK: s_transposed[37][9] -> (tile r = 2, row_group 1, lane 2 "
                  "of u[1][1]) -> s[9][37]   PV: P[9][37] = bf16(exp_rows[9][37]);   "
                  "o[9][d] = sum over t of P[9][t] * V[t][d]", 8.5, mono=True))
    o.append(text(28, EY + 44, "the highlighted cells above: column 9 of the 16-head panel, "
                  "P[9][37] in the 16-head scratch; B4 follows the QK element through the "
                  "transpose", 8.5, fill=muted))
    o.append(cite(W - 24, EY + 48, "transpose_sim.py; amx_attn.cpp:291; amx_attn_iface.hpp:66"))
    boxes.append(("worked example: s_transposed[37][9] -> s[9][37]; P[9][37] = "
                  "bf16(exp_rows[9][37]); o[9][d] = sum_t P[9][t] * V[t][d]",
                  "transpose_sim.py (the QK chain); amx_attn.cpp:285-291 (the conversion); "
                  "amx_attn_iface.hpp:66 (O[group_heads][128] = bf16(P) . V)"))

    H = EY + 64
    cap = ("The data model of one dense page. Top row (QK): the query group is packed into "
           "four panels, the K page is the A operand, the four accumulator tiles are stored "
           "into s_transposed, and the transpose writes group_heads rows of 64 tokens into the "
           "caller's s. Bottom row (PV): the caller's exp rows become the bf16 scratch P "
           "(the A operand), the packed V plane is the B operand, and eight tile stores write "
           "o, of which the caller reads rows 0..kv_mul-1. The small grids show what 4 heads "
           "leave as zero padding (dashed) and what 16 heads fill; the worked example "
           "(head 9, token 37) is the highlighted cell and the strip at the bottom.")
    legend = [
        ("q", "violet: q_group, the packed Q (packed / q_packed) and its panel grids, the pack "
              "arrow and its label, the Q tile loads"),
        ("rm", "orange: the K page k_rows and its 16 tile loads"),
        ("vnni", "blue: the packed V plane v_pairs and its 16 tile loads"),
        ("rows", "green: s_transposed, s, exp_rows, the P scratch and its grids, the "
                 "conversion label, the P tile loads, the tile stores and the transpose arrow"),
        ("blk", "purple: the output o, its 8 tile stores, the rows the caller reads"),
        ("unit", "grey-blue: the tile registers Q_TILE_6, K tiles 4 / 5, ACCUMULATOR_TILE_0..3, "
                 "P_TILE_4, V tiles 5 / 6"),
        ("empty", "grey dashed cells: zero padding for 4 heads (panel columns 4..15, P rows "
                  "4..15)"),
        ("hi", "the worked example: the highlighted cell (column 9 of the 16-head panel, "
               "P[9][37]) and the strip at the bottom"),
        ("ctx", "grey: the caller's v*/s*/m* update in self_attention.hpp"),
        ("violet, orange, green, blue and purple arrows: the data flow, each labelled with "
         "how many", "multi", [("arrow", C["q"]), ("arrow", C["rm"]), ("arrow", C["rows"]),
                               ("arrow", C["vnni"]), ("arrow", C["blk"])]),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Data model: the buffers of one dense page", "".join(o), cap,
                  boxes=boxes, legend=legend)


# =============================================================================
# B2: function model
# =============================================================================
def b2():
    fid = "amx_attn-b2"
    W = 1000
    o = [marker_defs(fid, {"ink": ink, "muted": muted, "hw": C["hw"], "q": C["q"],
                           "rows": C["rows"]})]
    boxes = []
    o.append(text(20, 18, "The kernels of amx_attn.cpp, the new helper, the gate in the "
                  "interface header, and the callers in self_attention.hpp", 12.5, weight=700))

    # ---- left: callers (context) ----------------------------------------------
    LX, LW = 20, 300
    o.append(rect(LX, 30, LW, 570, C["soft"], C["line"], 1, 6))
    o.append(text(LX + 8, 46, "self_attention.hpp (callers, context)", 10.5, weight=700))
    o.append(fn_cell(LX + 10, 56, LW - 20, 70, "apply_page_range<geometry>",
                     ["amx_on = eligible<scalar>(head_size, kv_mul)",
                      "&& available(); begin_region() ... end_region()",
                      "around this worker's page loop"],
                     "self_attention.hpp:1536-1562", fill="#fff"))
    boxes.append(("apply_page_range<geometry>", "self_attention.hpp:1536-1562 (amx_eligible, "
                  "amx_on, amx_qpack.resize, begin_region, the finally end_region)"))
    o.append(fn_cell(LX + 10, 136, LW - 20, 72, "packed_amx_query<geometry>",
                     ["returns this token's packed Q group for kv_head,",
                      "packing it on the first request of the call",
                      "(amx_packed records which tokens are done)"],
                     "self_attention.hpp:1681-1700", fill="#fff", tag="changed"))
    boxes.append(("packed_amx_query<geometry>", "self_attention.hpp:1681-1700 (comment and "
                  "definition); 1696 (the call with geometry.kv_mul())"))
    o.append(fn_cell(LX + 10, 218, LW - 20, 84, "apply_dense_amx_page<geometry>",
                     ["the whole AMX path for one (query, page) pair:",
                      "the QK kernel, the same scale / max / exp step",
                      "as the dotter, the PV kernel, the running-",
                      "softmax update (v*, s*, m*)"],
                     "self_attention.hpp:1725-1812", fill="#fff", tag="changed"))
    boxes.append(("apply_dense_amx_page<geometry>", "self_attention.hpp:1725-1812 (comment "
                  "and definition); 1763 and 1791 (the two kernel calls with "
                  "operation_kv_mul)"))
    o.append(rect(LX + 10, 312, LW - 20, 60, "#fff", C["line"], 1, 4))
    o.append(text(LX + 18, 326, "the template argument = the model's kv_mul", 9.5, weight=700))
    o.append(lines(LX + 18, 339, ["geometry.kv_mul() (packer), operation_kv_mul",
                                   "(QK, PV): 4 for llama-8b, 16 for Muse Glimmer"], 8.5, 11,
                   fill=muted))
    o.append(cite(LX + LW - 14, 368, "self_attention.hpp:1696, 1745, 1763, 1791"))
    boxes.append(("the template argument = the model's kv_mul", "self_attention.hpp:1696 "
                  "(pack_q_group_128x4<geometry.kv_mul()>), 1745 (constexpr operation_kv_mul "
                  "= geometry.kv_mul()), 1763, 1791"))
    o.append(rect(LX + 10, 382, LW - 20, 90, "#fff", C["line"], 1, 4))
    o.append(text(LX + 18, 396, "caller buffers, geometry-sized already", 9.5, weight=700))
    o.append(lines(LX + 18, 409, ["amx_qpack_slot: bf16 v[Q_PACK_ELEMS_2048] (4096 B)",
                                   "s_pages: tensor<operation_kv_mul, page_size>",
                                   "amx_o: float[TILE_ROWS_16 * operation_head_size]",
                                   "(no size change in this PR)"], 8.5, 11, fill=muted))
    o.append(cite(LX + LW - 14, 468, "self_attention.hpp:259-261, 1756, 1790"))
    boxes.append(("caller buffers, geometry-sized already (amx_qpack_slot, s_pages, amx_o)",
                  "self_attention.hpp:259-261 (amx_qpack_slot), 1756 (s_pages), 1790 (amx_o)"))

    # ---- middle: the kernels --------------------------------------------------
    MX, MW = 360, 300
    o.append(text(MX, 46, "amx_attn.cpp (namespace tron::amx_attn_h128g4)", 10.5, weight=700))
    o.append(fn_cell(MX, 56, MW, 56, "available()",
                     ["true when CPU, OS and the per-process permission",
                      "allow AMX and TRON_AMX_DISABLE is not 1; probed once"],
                     "amx_attn.cpp:104-114", fill="#fff"))
    boxes.append(("available()", "amx_attn.cpp:104-114; amx_attn_iface.hpp:182-185"))
    o.append(fn_cell(MX, 120, MW, 56, "begin_region() / end_region()",
                     ["begin: configures all 8 tiles as 16 rows x 64 bytes",
                      "(LDTILECFG, palette 1); end: TILERELEASE"],
                     "amx_attn.cpp:116-128", fill="#fff"))
    boxes.append(("begin_region() / end_region()", "amx_attn.cpp:116-128; "
                  "amx_attn_iface.hpp:264-267"))
    o.append(fn_cell(MX, 190, MW, 62, "pack_q_group_128x4<group_heads>",
                     ["packs one query group into the VNNI B-operand",
                      "layout: group_heads columns of every panel,",
                      "the rest zero padding the caller keeps"],
                     "amx_attn.cpp:130-146", fill=C["q_fill"], stroke=C["q"], tag="changed"))
    boxes.append(("pack_q_group_128x4<group_heads>", "amx_attn.cpp:130-146; "
                  "amx_attn_iface.hpp:187-204 (the contract)"))
    o.append(fn_cell(MX, 260, MW, 62, "qk_rowmajor_128x4<group_heads>",
                     ["S^T[64][16] = K_page . Q^T in tiles, then a",
                      "transposing store of the group_heads useful",
                      "query rows into the caller's s (UNSCALED)"],
                     "amx_attn.cpp:187-262", fill=C["rows_fill"], stroke=C["rows"], tag="changed"))
    boxes.append(("qk_rowmajor_128x4<group_heads>", "amx_attn.cpp:187-262 (comment and "
                  "definition); amx_attn_iface.hpp:235-247"))
    o.append(fn_cell(MX + 30, 344, MW - 30, 62, "store_transposed_rows<lane>",
                     ["stages 3 and 4 of the transpose for one 128-bit",
                      "lane: assembles and stores output rows",
                      "4 * lane + k, k = 0..3 (anonymous namespace)"],
                     "amx_attn.cpp:150-183", fill=C["pend_fill"], stroke=C["pend"], tag="new"))
    boxes.append(("store_transposed_rows<lane>", "amx_attn.cpp:150-183 (the comment and the "
                  "template); 169-170 (the declaration)"))
    o.append(fn_cell(MX, 416, MW, 62, "weights_times_v_128x4<group_heads>",
                     ["O = P[group_heads][64] . V_page: converts the",
                      "group_heads exp rows into bf16 P, 16 tile",
                      "products, 8 tile stores into o (16 rows)"],
                     "amx_attn.cpp:264-328", fill=C["blk_fill"], stroke=C["blk"], tag="changed"))
    boxes.append(("weights_times_v_128x4<group_heads>", "amx_attn.cpp:264-328; "
                  "amx_attn_iface.hpp:249-262"))
    o.append(rect(MX, 488, MW, 108, C["hw_fill"], C["hw"], 1.3, 4))
    o.append(text(MX + 8, 503, "explicit instantiations", 10.5, mono=True, weight=600))
    o.append(tag(MX + MW - 8, 503, "new"))
    o.append(lines(MX + 8, 517, ["template void pack_q_group_128x4<GROUP_HEADS_4>(...);",
                                 "template void pack_q_group_128x4<GROUP_HEADS_16>(...);",
                                 "qk_rowmajor_128x4<4>, <16>; weights_times_v_128x4<4>, <16>",
                                 "= 3 kernels x 2 sizes = 6 bodies; 'this list is the set",
                                 "of group sizes callers can use: it equals group_heads_ok'"],
                   8.5, 11))
    o.append(cite(MX + MW - 4, 592, "amx_attn.cpp:330-354"))
    boxes.append(("explicit instantiations: template void kernel<GROUP_HEADS_4 | GROUP_HEADS_16>(...)", "amx_attn.cpp:330-354 (the comment and the six template declarations)"))

    # ---- right: the gate ------------------------------------------------------
    RX, RW = 700, 280
    o.append(rect(RX, 30, RW, 570, C["soft"], C["line"], 1, 6))
    o.append(text(RX + 8, 46, "amx_attn_iface.hpp (the gate)", 10.5, weight=700))
    o.append(rect(RX + 10, 56, RW - 20, 64, C["hw_fill"], C["hw"], 1.3, 4))
    o.append(text(RX + 18, 71, "GROUP_HEADS_4 = 4, GROUP_HEADS_16 = 16", 9.5, mono=True,
                  weight=600))
    o.append(lines(RX + 18, 85, ["16 heads fill the 16 packed-Q columns of the QK",
                                 "B tile and the 16 P rows of the PV A tile,",
                                 "so that group size needs no padding"], 8.5, 10.5, fill=muted))
    o.append(cite(RX + RW - 14, 116, "amx_attn_iface.hpp:142-147"))
    boxes.append(("GROUP_HEADS_4 = 4, GROUP_HEADS_16 = 16", "amx_attn_iface.hpp:142-147 (the "
                  "constants and the static_assert GROUP_HEADS_16 == TILE_ROWS_16)"))
    o.append(fn_cell(RX + 10, 130, RW - 20, 58, "group_heads_ok(g)",
                     ["g == GROUP_HEADS_4 || g == GROUP_HEADS_16:",
                      "the group sizes the kernels are compiled for"],
                     "amx_attn_iface.hpp:149-154", fill=C["hw_fill"], stroke=C["hw"], tag="new"))
    boxes.append(("group_heads_ok(g)", "amx_attn_iface.hpp:149-154"))
    o.append(rect(RX + 10, 198, RW - 20, 70, C["hw_fill"], C["hw"], 1.3, 4, "5 3"))
    o.append(text(RX + 18, 213, "template <size_t group_heads>", 9.5, mono=True, weight=600))
    o.append(text(RX + 18, 226, "  requires(group_heads_ok(group_heads))", 9.5, mono=True,
                  weight=600))
    o.append(lines(RX + 18, 240, ["on each of the three declarations and definitions;",
                                  "any other size is rejected at compile time"], 8.5, 10.5,
                   fill=muted))
    o.append(cite(RX + RW - 14, 264, "amx_attn_iface.hpp:202-204, 242-247, 256-262"))
    boxes.append(("template <size_t group_heads> requires(group_heads_ok(group_heads))",
                  "amx_attn_iface.hpp:202-204, 242-247, 256-262 (declarations); "
                  "amx_attn.cpp:130-131, 191-192, 264-265 (definitions)"))
    o.append(fn_cell(RX + 10, 278, RW - 20, 58, "shape_ok(head_size, kv_mul)",
                     ["head_size == HEAD_SIZE_128 &&",
                      "group_heads_ok(kv_mul): the shape half of the gate"],
                     "amx_attn_iface.hpp:161-165", fill="#fff", tag="changed"))
    boxes.append(("shape_ok(head_size, kv_mul)", "amx_attn_iface.hpp:161-165"))
    o.append(fn_cell(RX + 10, 346, RW - 20, 58, "eligible<query_scalar_t>(...)",
                     ["shape_ok && query_scalar_ok: the gate the",
                      "dispatch evaluates (bf16 Q only)"],
                     "amx_attn_iface.hpp:176-180", fill="#fff"))
    boxes.append(("eligible<query_scalar_t>(...)", "amx_attn_iface.hpp:176-180; 167-174 "
                  "(query_scalar_ok)"))
    o.append(rect(RX + 10, 414, RW - 20, 76, "#fff", C["line"], 1, 4))
    o.append(text(RX + 18, 429, "kept names", 9.5, weight=700))
    o.append(lines(RX + 18, 442, ["namespace amx_attn_h128g4 and the _128x4 suffix",
                                  "of every kernel record the first shape, kv_mul 4,",
                                  "and are kept (the header's words)"], 8.5, 10.5, fill=muted))
    o.append(cite(RX + RW - 14, 486, "amx_attn_iface.hpp:13-16"))
    boxes.append(("kept names (amx_attn_h128g4, _128x4)", "amx_attn_iface.hpp:13-16"))

    # ---- arrows ---------------------------------------------------------------
    # callers -> kernels
    o.append(card_arrow(fid, "ink", [(LX + LW - 10, 84), (MX - 2, 84)], ink,
                        "1 call per apply_page_range", label_dy=-5, size=8))
    o.append(arrow(fid, "ink", [(LX + LW - 10, 100), (MX - 2, 148)], ink, 1.2))
    o.append(text(MX - 20, 132, "begin / end", 8, "end", fill=ink, weight=600))
    o.append(arrow(fid, "q", [(LX + LW - 10, 172), (MX - 2, 221)], C["q"], 1.4))
    o.append(text(MX + 2, 186, "1 call per token, at its first dense page", 8, fill=C["q"],
                  weight=600))
    boxes.append(("1 call per token, at its first dense page", "self_attention.hpp:1529-1533 (each token's Q group is packed once per call, at its first page that passes the outer checks), 1681-1684"))
    o.append(card_arrow(fid, "rows", [(LX + LW - 10, 250), (MX - 2, 291)], C["rows"],
                        "1 call per (query, page)", label_dx=0, label_dy=-6, size=8))
    o.append(arrow(fid, "rows", [(LX + LW - 10, 302), (MX - 20, 302), (MX - 20, 447),
                                 (MX - 2, 447)], C["rows"], 1.4))
    o.append(text(MX - 24, 420, "1 call per (query, page)", 8, "end", fill=C["rows"],
                  weight=600, extra=f' transform="rotate(-90 {MX - 24} 420)"'))
    boxes.append(("1 call per (query, page)", "self_attention.hpp:1725-1729 (the whole AMX "
                  "path for one (query, page) pair), 1763, 1791"))
    # qk -> store helper
    o.append(arrow(fid, "ink", [(MX + 20, 322), (MX + 20, 360), (MX + 28, 360)], ink, 1.3))
    o.append(text(MX + 34, 337, "4 tiles x (1 or 4) calls", 8, fill=ink, weight=600))
    boxes.append(("4 tiles x (1 or 4) calls", "amx_attn.cpp:231 (r = 0..3), 255-260 (lane 0 "
                  "always; lanes 1..3 when group_heads is 16)"))
    # kernels -> gate (requires)
    for y in (221, 291, 447):
        o.append(arrow(fid, "hw", [(MX + MW, y), (RX + 8, 233)], C["hw"], 1.1, "4 3"))
    o.append(text(RX - 20, 300, "requires", 8.5, "end", fill=C["hw"], weight=600))
    # instantiations -> group_heads_ok
    o.append(arrow(fid, "hw", [(MX + MW, 542), (RX + 8, 160)], C["hw"], 1.2))
    o.append(text(MX + MW + 6, 558, "equals", 8.5, fill=C["hw"], weight=600))
    o.append(text(MX + MW + 6, 568, "group_heads_ok", 8, mono=True, fill=C["hw"]))

    H = 610
    cap = ("The function model. Left: the two callers in self_attention.hpp, which pass the "
           "model's kv_mul as the template argument; the caller buffers were already sized "
           "by the geometry. Middle: the three kernels (changed: a group_heads template "
           "parameter each), the new store helper the QK kernel calls once or four times per "
           "tile, and the new explicit instantiation list. Right: the gate in the interface "
           "header; the requires clause on every kernel and the instantiation list both "
           "name group_heads_ok, so a size the list does not compile cannot be called.")
    legend = [
        ("ctx", "grey panels: the two context files, self_attention.hpp (callers) and "
                "amx_attn_iface.hpp (the gate)"),
        ("box", "white cell: a function with its one-line description (apply_page_range, "
                "packed_amx_query, apply_dense_amx_page, available, begin_region / "
                "end_region, shape_ok, eligible)"),
        ("lane", "white box, thin grey outline: a note (the template argument, the caller "
                 "buffers, the kept names)"),
        ("q", "violet: pack_q_group_128x4<group_heads> and its call arrow"),
        ("rows", "green: qk_rowmajor_128x4<group_heads> and weights_times_v_128x4's call "
                 "arrows (1 call per (query, page))"),
        ("blk", "purple: weights_times_v_128x4<group_heads>"),
        ("pend_solid", "vermillion: store_transposed_rows<lane>, the new helper"),
        ("hw", "yellow: the group-size gate (GROUP_HEADS_4 / 16, group_heads_ok, the "
               "explicit instantiations)"),
        ("yellow dashed box: the requires clause quoted from the declarations", C["hw_fill"],
         C["hw"], True, False),
        ("yellow arrows: 'requires' (dashed) from each kernel to the clause; 'equals "
         "group_heads_ok' from the instantiation list", "arrow", C["hw"]),
        ("arrow", "ink arrows: calls (apply_page_range -> available, begin / end; the QK "
                  "kernel -> store_transposed_rows)"),
        ("violet and green arrows: the kernel calls from the callers", "multi",
         [("arrow", C["q"]), ("arrow", C["rows"])]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR (store_transposed_rows, "
                     "group_heads_ok, the instantiations); 'changed' = the three kernels, the "
                     "two callers, shape_ok"),
    ]
    return figure(fid, W, H, "Function model: kernels, helper, gate, callers", "".join(o),
                  cap, boxes=boxes, legend=legend)


# =============================================================================
# B3: sequencing model
# =============================================================================
def b3():
    fid = "amx_attn-b3"
    W = 1000
    o = [marker_defs(fid, {"ink": ink})]
    boxes = []
    o.append(text(20, 18, "One dense (query, page) pair, instruction by instruction; right: "
                  "what differs between 4 and 16 heads", 12.5, weight=700))
    SX, SW = 20, 640
    DX, DW = 680, 300
    o.append(text(DX + 5, 40, "GROUP_HEADS_4", 9, mono=True, weight=600))
    o.append(text(DX + DW / 2 + 5, 40, "GROUP_HEADS_16", 9, mono=True, weight=600))
    y = 48
    steps = [
        ("pack_q_group_128x4<kv_mul>(q_group, slot)", "[caller]",
         ["once per token, at its first dense page (packed_amx_query); 4 steps x",
          "16 dim pairs x group_heads heads: two bf16 copies per (step, dim_pair, head)"],
         "amx_attn.cpp:136-143; self_attention.hpp:1693-1699", C["q_fill"], C["q"],
         ("4 columns per panel;", "columns 4..15 stay zero"), ("16 columns per panel;", "no padding"),
         "amx_attn.cpp:138"),
        ("_tile_zero(ACCUMULATOR_TILE_0..3)", "[QK]",
         ["clears the four accumulators"], "amx_attn.cpp:202-205", C["unit_fill"], C["unit"],
         ("same",), ("same",), None),
        ("for step 0..3: Q load, 4 x (K load, _tile_dpbf16ps)", "[QK]",
         ["per step: Q_TILE_6 <- panel step; for each 16-token slice j: K tile <- slice j",
          "dims step*32..+32, ACCUMULATOR_TILE_j += K . Q; 4 Q loads, 16 K loads, 16 products"],
         "amx_attn.cpp:206-221", C["unit_fill"], C["unit"], ("same: all 16 columns", "are computed"),
         ("same",), None),
        ("_tile_stored(ACCUMULATOR_TILE_j, s_transposed + j * TILE_FP32S)", "[QK]",
         ["4 tile stores: s_transposed[token][query], 64 x 16 fp32"], "amx_attn.cpp:222-225",
         C["rows_fill"], C["rows"], ("same",), ("same",), None),
        ("for r 0..3: unpack loop, then store_transposed_rows<lane>", "[QK]",
         ["per tile r: 4 row groups x (4 loads, 4 unpack_ps, 4 unpack_pd) -> u[4][4];",
          "store_transposed_rows<0>(u, s + r * 16, stride); lanes 1..3 under if constexpr"],
         "amx_attn.cpp:231-261", C["pend_fill"], C["pend"],
         ("1 lane store per tile:", "rows 0..3 (16 row stores)"),
         ("4 lane stores per tile:", "rows 0..15 (64 row stores)"), "amx_attn.cpp:255-260"),
        ("scale or softcap, m_page, exp(s - m_page), sum, per head", "[caller]",
         ["operation_kv_mul rows of s_pages, in place: the same math as the dotter epilogue"],
         "self_attention.hpp:1766-1786; amx_attn_iface.hpp:63-64", C["soft"], C["line"],
         ("4 rows",), ("16 rows",), "self_attention.hpp:1769"),
        ("for q < group_heads: P[q] <- cvtne2ps_pbh(exp_rows[q])", "[PV]",
         ["2 x (2 loads of 16 fp32, 1 convert, 1 store of 32 bf16) per row"],
         "amx_attn.cpp:285-293", C["rows_fill"], C["rows"],
         ("4 rows written;", "rows 4..15 zero padding"), ("16 rows written;", "no padding"),
         "amx_attn.cpp:285"),
        ("for half 0..1: zero; for s 0..1: P load, 4 x (V load, _tile_dpbf16ps)", "[PV]",
         ["P_TILE_4 <- P[0..15][s*32..+32]; V tile <- pair rows s*16..+16, dims (half*4+j)*32;",
          "ACCUMULATOR_TILE_j += P . V; 4 P loads, 16 V loads, 16 products"],
         "amx_attn.cpp:295-322", C["unit_fill"], C["unit"], ("same",), ("same",), None),
        ("_tile_stored(ACCUMULATOR_TILE_j, o + half * 64 + 16 * j)", "[PV]",
         ["4 stores per half = 8: o[16][128] fp32, all 16 rows written"],
         "amx_attn.cpp:323-326", C["blk_fill"], C["blk"],
         ("16 rows stored; rows 4..15", "= products of zero rows"), ("16 rows stored,", "all real"),
         "amx_attn_iface.hpp:103-106"),
        ("v*/s*/m* update from amx_o rows 0..kv_mul-1", "[caller]",
         ["per head: memcpy one 128-float row, fma into v_star, s_star, m_star"],
         "self_attention.hpp:1795-1811", C["soft"], C["line"], ("4 rows read",), ("16 rows read",),
         "self_attention.hpp:1796"),
    ]
    for i, (title, who, body, ref, fill, stroke, l4, l16, dref) in enumerate(steps, 1):
        h = 30 + 11.5 * len(body) + 6
        o.append(step_box(SX, y, SW, h, i, title, body, ref, fill, stroke, who))
        boxes.append((f"step {i}: {title}", ref))
        o.append(two_col(DX, y, DW, h, l4, l16, dref))
        if i < len(steps):
            o.append(arrow(fid, "ink", [(SX + 15, y + h), (SX + 15, y + h + 10)], ink, 1.1))
        y += h + 12
    boxes.append(("GROUP_HEADS_4 | GROUP_HEADS_16 (the right column)", "amx_attn_iface.hpp:"
                  "142-147; the per-row citations name the line whose bound differs"))
    o.append(line(SX, y, W - 20, y, C["line"]))
    o.append(text(SX, y + 14, "Per page: 16 + 16 _tile_dpbf16ps, 4 + 8 tile stores, 4 + 4 + "
                  "16 + 16 tile loads, for both group sizes.", 9.5))
    o.append(text(SX, y + 27, "Only the bounds in steps 1, 5, 7 (and the caller's row counts) "
                  "depend on group_heads.", 9.5))
    o.append(cite(W - 20, y + 27, "amx_attn.cpp:206-221, 295-322"))
    H = int(y + 38)
    cap = ("The sequence for one dense page, in file order: the pack (step 1, once per token), "
           "the QK kernel (steps 2-5), the caller's softmax step (6), the PV kernel (7-9) and "
           "the caller's update (10). Each step cites the lines that do it and says how many "
           "instructions. The right column shows that 4 and 16 heads run the same tile "
           "instructions; only the pack loop, the number of lane stores in the transpose and "
           "the P conversion loop depend on group_heads.")
    legend = [
        ("q", "violet step: the packer, pack_q_group_128x4<kv_mul>"),
        ("unit", "grey-blue steps: tile instructions (_tile_zero, _tile_loadd, _tile_dpbf16ps)"),
        ("rows", "green steps: the tile stores into s_transposed and the P conversion"),
        ("pend_solid", "vermillion step: the transpose with store_transposed_rows<lane>"),
        ("blk", "purple step: the tile stores into o"),
        ("ctx", "grey steps: the caller's softmax step and the v*/s*/m* update (self_attention.hpp)"),
        ("box", "white cell, left half of the right column: the GROUP_HEADS_4 behaviour of the "
                "step"),
        ("eagle", "sky blue cell, right half of the right column: the GROUP_HEADS_16 behaviour"),
        ("arrow", "ink arrow: the next step"),
        ("ink badge with a white number: the step number", ink, ink, False, False),
        ("thin grey line: the end of the sequence", "line", C["line"]),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Sequencing model: one dense page, instruction by instruction",
                  "".join(o), cap, boxes=boxes, legend=legend)


# =============================================================================
# B4: the transpose (interaction model)
# =============================================================================
def b4():
    fid = "amx_attn-b4"
    W = 1000
    o = [marker_defs(fid, {"ink": ink, "rows": C["rows"], "pend": C["pend"]})]
    boxes = []
    o.append(text(20, 18, "The 16 x 16 transpose of one stored tile: tile rows -> 128-bit "
                  "lanes -> s rows", 12.5, weight=700))
    o.append(cite(W - 20, 18, "amx_attn.cpp:150-162, 227-261; transpose_sim.py"))

    # ---- (a) s_transposed and tile r = 2 -----------------------------------------
    AX = 20
    o.append(text(AX, 42, "(a) s_transposed: 4 stored tiles", 10, weight=700))
    cw, ch = 3, 3
    for r in range(4):
        ty = 50 + r * (16 * ch + 6)
        o.append(rect(AX, ty, 16 * cw, 16 * ch, C["rows_fill"], C["rows"], 1, 0))
        o.append(text(AX + 16 * cw + 8, ty + 8 * ch + 3, f"r = {r}: tokens {16 * r}..{16 * r + 15}",
                      8.5, fill=muted))
        if r == TILE_R:
            o.append(rect(AX - 2, ty - 2, 16 * cw + 4, 16 * ch + 4, "none", ink, 2.6, 0))
    o.append(text(AX + 16 * cw + 8, 50 + 8 * ch + 15, "16 tokens x 16 columns", 8.5, fill=muted))
    o.append(cite(AX + 16 * cw + 8, 50 + 3 * (16 * ch + 6) + 8 * ch + 15,
                  "amx_attn.cpp:200-201, 231-232", anchor="start"))
    boxes.append(("s_transposed: 4 stored tiles (r = 0..3) of 16 tokens x 16 columns",
                  "amx_attn.cpp:200-201 (s_transposed[token][query]), 222-225 (4 tile "
                  "stores), 231-232 (src = s_transposed + r * TILE_FP32S)"))
    # zoom of tile r = 2
    ZX, ZY = 240, 50
    zc, zr = 11, 11
    o.append(text(ZX, 42, "tile r = 2 (tokens 32..47): 16 rows = tokens, 16 columns = query "
                  "heads 0..15", 10, weight=700))
    for rr in range(16):
        for cc in range(16):
            hi = (rr == ROW_IN_TILE and cc == HEAD_EXAMPLE)
            f = C["hi_fill"] if hi else (C["eagle_fill"] if cc >= 4 else C["rows_fill"])
            st = ink if hi else (C["eagle"] if cc >= 4 else C["rows"])
            o.append(rect(ZX + cc * zc, ZY + rr * zr, zc, zr, f, st, 0.6, 0))
    # row group bands
    for rg in range(4):
        o.append(rect(ZX - 1, ZY + rg * 4 * zr - 1, 16 * zc + 2, 4 * zr + 2, "none",
                      C["pend"] if rg == ROW_GROUP else C["line"], 1.4 if rg == ROW_GROUP else 0.8,
                      0))
        o.append(text(ZX + 16 * zc + 6, ZY + rg * 4 * zr + 2 * zr + 3,
                      f"row_group {rg}: rows {4 * rg}..{4 * rg + 3}", 8.5,
                      fill=C["pend"] if rg == ROW_GROUP else muted))
    o.append(text(ZX, ZY + 16 * zr + 12, "columns 0..3: stored by lane 0 (both sizes); "
                  "columns 4..15: lanes 1..3 (16 heads only)", 8.5, fill=muted))
    o.append(text(ZX, ZY + 16 * zr + 24, "row 5 = token 37; column 9 = head 9 -> the element", 8.5,
                  fill=muted))
    o.append(cite(ZX + 16 * zc + 300, ZY + 16 * zr + 24, "amx_attn.cpp:234-236; STYLE.md"))
    boxes.append(("tile r = 2 (tokens 32..47): row_group 0..3", "amx_attn.cpp:234-236 "
                  "(row_group: which 4-row group of the 16x16 tile this pass interleaves)"))
    boxes.append(("row 5 = token 37; column 9 = head 9 (the element)", "amx_attn.cpp:152-153 (tile column 4 * lane + k for the four tokens of the row group); STYLE.md worked example; transpose_sim.py"))

    # ---- (b) stages 1 and 2: the unpack of row_group 1 ---------------------------
    BY = ZY + 16 * zr + 50
    o.append(text(AX, BY, "(b) stages 1 and 2 (the unpack loop): row_group 1 -> u[1][0..3]; "
                  "lane L of u[1][k] = column 4L+k of tokens 36..39", 10, weight=700))
    boxes.append(("stages 1 and 2 (the unpack loop)", "amx_attn.cpp:150-153 (stage 1 "
                  "interleaves 32-bit values, stage 2 interleaves 64-bit pairs; lane holds "
                  "column 4 * lane + k), 237-252"))
    rx, rw, rh = AX, 460, 22
    for k in range(4):
        ry = BY + 10 + k * (rh + 6)
        o.append(text(rx, ry + rh / 2 + 3, f"u[1][{k}]", 9.5, mono=True, weight=600))
        labels = [f"col {4 * L + k}: t36..39" for L in range(4)]
        o.append(reg_lanes(rx + 60, ry, rw, rh, labels,
                           hi_lane=LANE if k == K_INDEX else None))
    for L in range(4):
        o.append(text(rx + 60 + (L + 0.5) * rw / 4, BY + 10 + 4 * (rh + 6) + 6, f"lane {L}", 8.5,
                      "middle", mono=True, fill=C["pend"]))
    o.append(text(rx + 60 + rw + 8, BY + 10 + 4 * (rh + 6) + 6, "(128 bits = 4 fp32 each)", 8.5,
                  fill=C["pend"]))
    o.append(cite(rx + 60 + rw + 300, BY + 10 + 4 * (rh + 6) + 6, "amx_attn.cpp:237-252"))
    boxes.append(("u[1][0..3] (4 registers, lane L = column 4L+k of tokens 36..39)", "amx_attn.cpp:152-153 (lane holds tile column 4 * lane + k), 233 (__m512 u[4][4]), 245-252 (the four unpack_pd results); transpose_sim.py ('verified for all row_group, k, lane: True')"))
    # the element's lane
    EX = rx + 60 + rw + 20
    o.append(rect(EX, BY + 10, 300, 70, C["hi_fill"], ink, 1, 4))
    o.append(text(EX + 8, BY + 24, "the element after stage 2", 9.5, weight=700))
    o.append(lines(EX + 8, BY + 38, ["u[1][1] lane 2 = column 9 of tokens 36..39",
                                      "= [s(36,9), s(37,9), s(38,9), s(39,9)]",
                                      "position 1 of the lane = token 37"], 8.5, 11, mono=True))
    o.append(cite(EX + 296, BY + 76, "transpose_sim.py"))
    boxes.append(("u[1][1] lane 2 = column 9 of tokens 36..39; position 1 = token 37",
                  "transpose_sim.py (the worked example chain); amx_attn.cpp:152-153"))

    # ---- (c) stages 3 and 4: store_transposed_rows<2>, k = 1 ---------------------
    CY = BY + 10 + 4 * (rh + 6) + 26
    o.append(text(AX, CY, "(c) stages 3 and 4: store_transposed_rows<2>, k = 1 -> s row 9; "
                  "pair_sel 0x88 (bit 0 of lane = 0), quad_sel 0xdd (bit 1 = 1)", 10,
                  weight=700))
    boxes.append(("store_transposed_rows<2>, k = 1", "amx_attn.cpp:169-183; 174-175 (pair_sel, "
                  "quad_sel from the bits of lane); 256-259 (the call for lane 2)"))
    cy = CY + 10
    rw2 = 460
    o.append(text(rx, cy + rh / 2 + 3, "p =", 9.5, mono=True, weight=600))
    o.append(reg_lanes(rx + 60, cy, rw2, rh, ["u[0][1] L0", "u[0][1] L2", "u[1][1] L0",
                                               "u[1][1] L2"], hi_lane=3))
    o.append(text(rx + 60 + rw2 + 8, cy + rh / 2 + 3, "shuffle_f32x4(u[0][1], u[1][1], 0x88): "
                  "lanes {0, 2} of each", 8.5, fill=C["pend"]))
    cy += rh + 6
    o.append(text(rx, cy + rh / 2 + 3, "q2 =", 9.5, mono=True, weight=600))
    o.append(reg_lanes(rx + 60, cy, rw2, rh, ["u[2][1] L0", "u[2][1] L2", "u[3][1] L0",
                                               "u[3][1] L2"]))
    o.append(text(rx + 60 + rw2 + 8, cy + rh / 2 + 3, "shuffle_f32x4(u[2][1], u[3][1], 0x88)",
                  8.5, fill=C["pend"]))
    cy += rh + 6
    o.append(text(rx, cy + rh / 2 + 3, "row 9 =", 9.5, mono=True, weight=600))
    o.append(reg_lanes(rx + 60, cy, rw2, rh, ["p L1 = col 9 t32..35", "p L3 = col 9 t36..39",
                                               "q2 L1 = col 9 t40..43", "q2 L3 = col 9 t44..47"],
                       hi_lane=1, lane_fill=C["rows_fill"]))
    o.append(text(rx + 60 + rw2 + 8, cy + rh / 2 + 3, "shuffle_f32x4(p, q2, 0xdd): lanes {1, 3}",
                  8.5, fill=C["pend"]))
    cy += rh + 6
    o.append(text(rx + 60, cy + 10, "_mm512_storeu_ps(s_rows + 1 * s_stride_floats, row 9) with "
                  "s_rows = s_block + 2 * 4 * s_stride_floats, s_block = s + 2 * 16", 8.5,
                  mono=True))
    o.append(text(rx + 60, cy + 22, "= s + 9 * s_stride_floats + 32: s[9][32..47]; element 5 = "
                  "s[9][37]", 8.5, mono=True, weight=600))
    o.append(cite(rx + 60 + rw2 + 300, cy + 22, "amx_attn.cpp:176-181, 254; transpose_sim.py"))
    boxes.append(("p, q2, row 9 (the three _mm512_shuffle_f32x4 of lane 2, k = 1)",
                  "amx_attn.cpp:178-181; 154-160 (stage 3 pairs row groups 0/1 and 2/3, stage "
                  "4 joins the two pairs; 0x88 even lanes, 0xdd odd lanes); transpose_sim.py"))
    boxes.append(("s_rows = s_block + 2 * 4 * s_stride_floats; s_block = s + 2 * 16",
                  "amx_attn.cpp:176 (s_rows), 254 (s_block = s + r * 16)"))

    # ---- (d) the lane table and the s layout --------------------------------------
    DY = cy + 40
    o.append(text(AX, DY, "(d) the four lanes: selectors and s rows; right: the caller's s "
                  "(16 heads) with tile r = 2's 16 token columns framed", 10, weight=700))
    ty = DY + 10
    cols = [("lane", 50), ("pair_sel", 70), ("quad_sel", 70), ("s rows written", 110),
            ("emitted for", 150)]
    x = AX
    o.append(rect(AX, ty, sum(w for _, w in cols), 18, C["soft"], C["line"], 1, 0))
    for name, w in cols:
        o.append(text(x + 4, ty + 13, name, 8.5, weight=700))
        x += w
    rows_t = [(0, "both sizes (the base kernel's store)"), (1, "16 heads only"),
              (2, "16 heads only"), (3, "16 heads only")]
    for L, who in rows_t:
        ty += 18
        f = C["eagle_fill"] if L > 0 else "#fff"
        o.append(rect(AX, ty, sum(w for _, w in cols), 18, f, C["eagle"] if L > 0 else C["line"],
                      1, 0))
        x = AX
        vals = [str(L), SELECTORS[L][0], SELECTORS[L][1], LANE_ROWS[L], who]
        for (name, w), v in zip(cols, vals):
            o.append(text(x + 4, ty + 13, v, 8.5, mono=name != "emitted for",
                          weight=700 if L == LANE and name == "lane" else None))
            x += w
    o.append(cite(AX + sum(w for _, w in cols), ty + 30, "amx_attn.cpp:161-162, 174-176, 255-260"))
    boxes.append(("lane 0..3: pair_sel, quad_sel, s rows written, emitted for",
                  "amx_attn.cpp:174-176 (the selectors and the row offset), 161-162 (lane 0 "
                  "= (0x88, 0x88) is the one store sequence the 4-head kernel emits), "
                  "255-260; transpose_sim.py (selectors per lane)"))
    # s layout at the right
    SXX = AX + sum(w for _, w in cols) + 40
    o.append(text(SXX, DY + 22, "s[16][s_stride_floats], 64 token columns (16 heads):", 8.5,
                  fill=muted))
    o.append(s_grid(SXX, DY + 28, 16, cw=6, ch=5, hi=(HEAD_EXAMPLE, TOKEN_EXAMPLE), tile_r=TILE_R))
    for L in range(4):
        o.append(rect(SXX - 14, DY + 28 + L * 4 * 5, 10, 20, C["eagle_fill"] if L else C["pend_fill"],
                      C["eagle"] if L else C["pend"], 1, 1))
        o.append(text(SXX - 9, DY + 28 + L * 20 + 14, str(L), 8, "middle", mono=True))
    o.append(text(SXX - 14, DY + 22, "lane", 8, "end", fill=muted))
    o.append(text(SXX + 64 * 6 + 6, DY + 28 + 44, "rows 4..15: not", 8, fill=muted))
    o.append(text(SXX + 64 * 6 + 6, DY + 28 + 55, "written for 4 heads", 8, fill=muted))
    o.append(cite(SXX + 64 * 6, DY + 28 + 94, "amx_attn_iface.hpp:107-110"))
    boxes.append(("s[16][s_stride_floats] (16 heads): lane L writes rows 4L..4L+3; tile r = 2 "
                  "= columns 32..47", "amx_attn.cpp:176 (lane * ROWS_PER_LANE_4 * "
                  "s_stride_floats), 254 (s + r * 16); amx_attn_iface.hpp:107-110 (s needs only "
                  "group_heads rows)"))

    H = DY + 28 + 100
    cap = ("The interaction model of the transpose, followed through the worked example. (a) "
           "The four stored tiles; tile r = 2 holds tokens 32..47, and the element head 9 / "
           "token 37 is row 5, column 9 of it. (b) After the two unpack stages, each 128-bit "
           "lane L of u[row_group][k] holds column 4L+k of the row group's four tokens; the "
           "element is position 1 of lane 2 of u[1][1]. (c) store_transposed_rows<2> gathers "
           "lane 2 of u[0..3][1] with two shuffle stages (0x88, then 0xdd) into s row 9 and "
           "stores it at s + 9 * stride + 32. (d) The four lanes and their selectors; lane 0 "
           "is the base kernel's one store, lanes 1..3 exist only in the 16-head "
           "instantiation. transpose_sim.py computed and checked every mapping shown.")
    legend = [
        ("rows", "green: s_transposed and its tiles, columns 0..3 of the zoomed tile (stored for "
                 "both sizes), the caller's s rows, and the assembled row 9 register"),
        ("eagle", "sky blue: columns 4..15 of the zoomed tile and lanes 1..3 in the table and "
                  "at the left of s (16 heads only)"),
        ("pend_solid", "vermillion: the 128-bit lanes of the registers u[1][k], p and q2; the "
                       "row_group 1 frame; the shuffle notes; lane 0's marker at the left of s"),
        ("hi", "the worked example: the element cell (row 5, column 9 of tile r = 2), "
               "s[9][37], and the note after stage 2"),
        ("worked-example fill with vermillion outline: the lane that holds the element in "
         "u[1][1], p and row 9", C["hi_fill"], C["pend"], False, False),
        ("vermillion frame: row_group 1 of the zoomed tile (rows 4..7)", "none", C["pend"],
         False, False),
        ("thick_ink", "thick ink frame: tile r = 2 in s_transposed and its 16 token columns "
                      "in s"),
        ("green fill, vermillion lanes: the assembled register 'row 9' (scores, split in "
         "the four lanes the final shuffle gathered)", C["rows_fill"], C["pend"], False, False),
        ("lane", "thin grey outline: the other row-group frames of the zoomed tile and the "
                 "table row of lane 0"),
        ("ctx", "grey: the table header"),
        "font_mono", "font_sans", "font_cite",
    ]
    return figure(fid, W, H, "Interaction model: the 16 x 16 transpose", "".join(o), cap,
                  boxes=boxes, legend=legend)
