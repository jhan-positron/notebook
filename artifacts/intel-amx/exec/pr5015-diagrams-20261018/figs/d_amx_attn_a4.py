"""Change diagram of unit A4 (amx_attn.cpp): weights_times_v_128x4 becomes a
template on group_heads; the conversion loop writes rows 0..group_heads-1 of
the P scratch; P is a thread_local static of the template, so each thread
has one scratch per instantiation (4 heads, 16 heads).

Two figures:
  amx_attn-d4   the loop bound before / after and the two P scratches of one
                worker thread (updates the P box of B1's PV row)
  amx_attn-d4a  the PV data flow exp_rows -> P -> P_TILE_4 ->
                ACCUMULATOR_TILE_0..3 -> o -> the caller, with how many on
                every arrow and the unchanged span marked

Every fact comes from the cited head lines (5061623a34) of
src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp and
h/tron/models/self_attention.hpp, or from base (6198824246) amx_attn.cpp.
"""
from svg_helpers import (C, arrow, cite, figure, lane, lines, marker_defs, rect,
                         text)
from base_amx_attn import (HEAD_EXAMPLE, TOKEN_EXAMPLE, data_box, fit, grid, p_grid,
                           tag, tile_box)

ink, muted = C["ink"], C["muted"]

BASE = ("Updates B1: the PV row's conversion step writes rows 0..group_heads-1 of P "
        "(4 or 16 rows) instead of rows 0..3, and the P scratch exists once per "
        "instantiation per thread; the P tile loads, the 16 tile products and the 8 "
        "tile stores into o are unchanged.")


# =============================================================================
# d4: the loop bound before / after; the two scratches of one thread
# =============================================================================
def _fig_scratch():
    fid = "amx_attn-d4"
    W = 700
    o = [marker_defs(fid, {"ink": ink})]
    boxes = []
    o.append(text(20, 18, fit("weights_times_v_128x4<group_heads>: the loop bound and the P "
                              "scratch, before and after", 12.5, 660), 12.5, weight=700))

    # ---- before (base) ---------------------------------------------------------
    BX, BY, BW, BH = 20, 30, 300, 112
    o.append(rect(BX, BY, BW, BH, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(BX + 8, BY + 14, "before (main 6198824246)", 9.5, fill=C["gone"],
                  weight=700))
    o.append(text(BX + 8, BY + 30, "void weights_times_v_128x4(", 9.5, mono=True))
    o.append(text(BX + 8 + 160, BY + 30, "no template parameter", 8.5, fill=muted))
    o.append(text(BX + 8, BY + 46, fit("for (size_t q = 0; q < GROUP_HEADS_4; q++)", 9.5,
                                       BW - 16, True), 9.5, mono=True, weight=600))
    o.append(text(BX + 8, BY + 60, "// rows 4..15 are zero padding", 8.5, mono=True,
                  fill=muted))
    o.append(text(BX + 8, BY + 71, "// (never written after thread init)", 8.5, mono=True,
                  fill=muted))
    o.append(text(BX + 8, BY + 88, "one body, one P scratch per thread", 8.5, fill=muted))
    o.append(cite(BX + BW - 4, BY + BH - 4, "base amx_attn.cpp:218, 229-233"))
    boxes.append(("before: for (size_t q = 0; q < GROUP_HEADS_4; q++); rows 4..15 are zero "
                  "padding", "base amx_attn.cpp:233 (the loop bound), 229-231 (the comment), "
                  "218 (the definition, no template parameter)"))

    # ---- becomes ---------------------------------------------------------------
    AX, AY, AW, AH = 380, 30, 300, 112
    o.append(arrow(fid, "ink", [(BX + BW, BY + 50), (AX - 2, BY + 50)], ink, 1.3))
    o.append(text((BX + BW + AX) / 2, BY + 42, "becomes", 8.5, "middle", fill=muted))

    # ---- after (head) ----------------------------------------------------------
    o.append(rect(AX, AY, AW, AH, "#fff", ink, 1.2, 4))
    o.append(text(AX + 8, AY + 14, "after (head 5061623a34)", 9.5, weight=700))
    o.append(tag(AX + AW - 8, AY + 14, "changed", col=muted))
    # the template header (the group-size gate, yellow)
    o.append(rect(AX + 8, AY + 20, AW - 16, 38, C["hw_fill"], C["hw"], 1.2, 3))
    o.append(text(AX + 14, AY + 32, "template <size_t group_heads>", 9, mono=True, weight=600))
    o.append(text(AX + 14, AY + 43, "  requires(group_heads_ok(group_heads))", 9, mono=True,
                  weight=600))
    o.append(cite(AX + AW - 12, AY + 55, "amx_attn.cpp:264-265"))
    boxes.append(("template <size_t group_heads> requires(group_heads_ok(group_heads))",
                  "amx_attn.cpp:264-265 (the kernel's template header); amx_attn_iface.hpp:"
                  "256-257 (the declaration)"))
    o.append(text(AX + 8, AY + 72, fit("for (size_t q = 0; q < group_heads; q++)", 9.5,
                                       AW - 60, True), 9.5, mono=True, weight=600))
    o.append(tag(AX + 8 + 236, AY + 72, "new", anchor="start"))
    boxes.append(("for (size_t q = 0; q < group_heads; q++)", "amx_attn.cpp:285 (the "
                  "conversion loop bound)"))
    o.append(text(AX + 8, AY + 86, "// rows group_heads..15 are zero padding", 8.5, mono=True,
                  fill=muted))
    o.append(text(AX + 8, AY + 97, "// (never written after thread init)", 8.5, mono=True,
                  fill=muted))
    o.append(cite(AX + AW - 4, AY + AH - 4, "amx_attn.cpp:277-279, 285"))
    boxes.append(("rows group_heads..15 are zero padding (never written after thread init)",
                  "amx_attn.cpp:277-279 (the comment on the P scratch)"))

    # ---- the two scratches of one thread --------------------------------------------
    TY = 164
    o.append(text(20, TY, "one P scratch per thread per instantiation: a thread_local static "
                  "of a function template", 10.5, weight=700))
    o.append(cite(W - 20, TY, "amx_attn.cpp:279-284"))
    boxes.append(("one P scratch per thread per instantiation", "amx_attn.cpp:284 (alignas(64) "
                  "thread_local uint16_t P[TILE_ROWS_16][PAGE_TOKENS_64]), 279-283 (a function "
                  "template's static locals exist once per specialization)"))
    CW, CH = 3.4, 4                     # cell size of the P grids (64 x 16 cells)
    GW = 64 * CW                        # 217.6 px

    def scratches(ly, who, sub, hi):
        band, tx = lane(20, ly, 660, 150, who, sub)
        o.append(band)
        gy = ly + 26
        # the GROUP_HEADS_4 scratch
        g1 = tx + 10
        o.append(text(g1, ly + 18, fit("P in weights_times_v_128x4<GROUP_HEADS_4>", 9, 240,
                                        True), 9, mono=True, weight=600))
        o.append(p_grid(g1, gy, 4, cw=CW, ch=CH))
        o.append(lines(g1, gy + 16 * CH + 12,
                       ["rows 0..3 written (q < GROUP_HEADS_4)",
                        "rows 4..15 zero padding, never written",
                        "after thread init: contribute nothing"], 8.5, 10, fill=muted))
        o.append(cite(g1 + GW, ly + 146, "amx_attn.cpp:284, 277-279"))
        # the GROUP_HEADS_16 scratch
        g2 = tx + 10 + GW + 32
        o.append(text(g2, ly + 18, fit("P in weights_times_v_128x4<GROUP_HEADS_16>", 9, 240,
                                        True), 9, mono=True, weight=600))
        o.append(p_grid(g2, gy, 16, cw=CW, ch=CH,
                        hi=(HEAD_EXAMPLE, TOKEN_EXAMPLE) if hi else None))
        if hi:
            # a thick ink frame around P[9][37] (the cell itself is 3.4 x 4 px)
            o.append(rect(g2 + TOKEN_EXAMPLE * CW - 3, gy + HEAD_EXAMPLE * CH - 3, CW + 6,
                          CH + 6, "none", ink, 2.6, 1))
        under = ["all 16 rows written (q < 16): no padding",
                 "the same shape, separate storage"]
        if hi:
            under = ["all 16 rows written (q < 16): no padding",
                     "worked example: the highlighted cell is",
                     "P[9][37] = bf16(exp_rows[9][37])"]
        o.append(lines(g2, gy + 16 * CH + 12, under, 8.5, 10, fill=muted))
        o.append(cite(g2 + GW, ly + 146, "amx_attn.cpp:284, 282-283, 291"))

    scratches(TY + 10, "[worker thread A]", "thread_local: its own P", True)
    scratches(TY + 170, "[worker thread B]", "its own two scratches", False)
    boxes.append(("P in weights_times_v_128x4<GROUP_HEADS_4>", "amx_attn.cpp:345 (the "
                  "GROUP_HEADS_4 instantiation), 284 (the thread_local P), 277-279 (rows "
                  "group_heads..15 are zero padding, never written after thread init), 285 "
                  "(rows 0..3 written when group_heads is 4)"))
    boxes.append(("P in weights_times_v_128x4<GROUP_HEADS_16>", "amx_attn.cpp:350 (the "
                  "GROUP_HEADS_16 instantiation), 284 (the thread_local P), 282-283 (for 16 "
                  "heads every row is written, so there is no padding), 291 (the store of "
                  "P[q] + c)"))
    boxes.append(("worked example: P[9][37] = bf16(exp_rows[9][37])", "amx_attn.cpp:285-291 "
                  "(the conversion of row q = 9, c = 32: token 37 is element 5 of the hi "
                  "load); amx_attn_iface.hpp:66"))
    boxes.append(("[worker thread A] / [worker thread B]", "amx_attn.cpp:284 (thread_local: "
                  "one P per thread); self_attention.hpp:1536-1562 (apply_page_range: this "
                  "worker's page loop)"))

    # ---- the comment's conclusion --------------------------------------------------
    NY = TY + 340
    o.append(rect(20, NY, 660, 46, "#fff", C["line"], 1, 4))
    o.append(text(28, NY + 15, "A function template's static locals exist once per "
                  "specialization. This scratch therefore belongs to the 4-head", 9.5))
    o.append(text(28, NY + 29, "or the 16-head instantiation only, and a 4-head call never "
                  "sees a 16-head call's rows.", 9.5))
    o.append(cite(676, NY + 42, "amx_attn.cpp:279-282"))
    boxes.append(("a 4-head call never sees a 16-head call's rows", "amx_attn.cpp:279-282 "
                  "(the comment on the P scratch)"))

    H = NY + 58
    cap = ("Updates B1 (the P box of the PV row), with the worked example. Top: the "
           "conversion loop's bound was GROUP_HEADS_4 (rows 0..3 of P) and is now the "
           "template parameter group_heads; the removed comment said rows 4..15 are padding, "
           "the new one says rows group_heads..15. Bottom: each worker thread now holds two "
           "P scratches, one per instantiation: the 4-head one keeps rows 4..15 as zero "
           "padding, the 16-head one is fully written (P[9][37] highlighted).")
    legend = [
        ("gone", "red dashed box and red text: the base kernel (no template parameter, the "
                 "loop bound q < GROUP_HEADS_4, the comment 'rows 4..15 are zero padding')"),
        ("box", "white box, ink outline: the head kernel's template header, loop bound and "
                "comment"),
        ("hw", "yellow: the template header with its requires clause (the group-size gate)"),
        ("rows", "green cells: the rows of P the conversion loop writes (0..3 for "
                 "GROUP_HEADS_4, 0..15 for GROUP_HEADS_16)"),
        ("empty", "grey dashed cells: rows 4..15 of the GROUP_HEADS_4 scratch, zero padding "
                  "never written after thread init"),
        ("hi", "the worked example's cell P[9][37] in thread A's GROUP_HEADS_16 scratch"),
        ("thick_ink", "thick ink frame: around that cell, so that it can be found"),
        ("lane", "white band, thin grey outline: one worker thread with its two thread_local "
                 "scratches; the quoted comment at the bottom"),
        ("arrow", "ink arrow: 'becomes' (the base code -> the head code)"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = the loop bound q < group_heads; 'changed' = the kernel"),
    ]
    return figure(fid, W, H, "A4: the loop bound before and after; two P scratches per thread",
                  "".join(o), cap, boxes=boxes, legend=legend)


# =============================================================================
# d4a: the PV data flow with how many on every arrow
# =============================================================================
def _fig_flow():
    fid = "amx_attn-d4a"
    W = 700
    o = [marker_defs(fid, {"rows": C["rows"], "blk": C["blk"]})]
    boxes = []
    o.append(text(20, 18, fit("The PV row of B1 after the change: only the conversion step "
                              "depends on group_heads", 12.5, 660), 12.5, weight=700))
    BX, BW = 190, 300            # the column of boxes
    AXC = BX + 150               # the arrows' x
    LX = AXC + 10                # the how-many labels start here (in the gap)
    GX = BX + BW + 6             # the small grids of o start here

    def how_many(y, items, ref, col):
        o.append(lines(LX, y, [fit(s, 8.5, W - 20 - LX, False, s) for s in items], 8.5, 10,
                       fill=col, weight=600))
        o.append(cite(W - 20, y + 10 * len(items) + 2, ref))

    # ---- exp_rows ----------------------------------------------------------------
    y = 30
    o.append(data_box(BX, y, BW, 56, "exp_rows",
                      ["= the caller's s_pages after exp: group_heads rows,",
                       "row_stride_floats fp32 per row"],
                      C["rows_fill"], C["rows"], "amx_attn_iface.hpp:249-251; amx_attn.cpp:268"))
    boxes.append(("exp_rows", "amx_attn_iface.hpp:249-251 (the caller's fp32 exp rows, "
                  "converted to bf16 inside); amx_attn.cpp:268 (the parameter); "
                  "self_attention.hpp:1792 (&s_pages[0][0] passed)"))
    # arrow 1: the conversion (changed)
    y1 = y + 56
    o.append(arrow(fid, "rows", [(AXC, y1), (AXC, y1 + 56)], C["rows"], 1.4))
    how_many(y1 + 14, ["group_heads rows x 64 tokens -> P rows 0..group_heads-1",
                       "per row: 2 x (2 loads of 16 fp32, _mm512_cvtne2ps_pbh,",
                       "1 store of 32 bf16)"], "amx_attn.cpp:285-292", C["rows"])
    boxes.append(("group_heads rows x 64 tokens -> P rows 0..group_heads-1", "amx_attn.cpp:285 "
                  "(q < group_heads), 286-292 (per row: c += 32, two _mm512_loadu_ps, one "
                  "_mm512_cvtne2ps_pbh, one _mm512_storeu_si512)"))
    o.append(tag(AXC - 8, y1 + 22, "new"))
    o.append(text(AXC - 8, y1 + 34, "q < group_heads", 9, "end", mono=True, weight=600))
    # the base bound (removed)
    o.append(rect(20, y1 + 6, 160, 44, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(28, y1 + 20, "before: q < GROUP_HEADS_4", 9, mono=True, fill=C["gone"],
                  weight=600))
    o.append(text(28, y1 + 32, "rows 0..3 of P only", 8.5, fill=muted))
    o.append(cite(176, y1 + 46, "base amx_attn.cpp:233"))
    boxes.append(("before: q < GROUP_HEADS_4", "base amx_attn.cpp:233 (the loop bound of the "
                  "base kernel)"))

    # ---- P -----------------------------------------------------------------------
    y = y1 + 56
    o.append(data_box(BX, y, BW, 70, "P[TILE_ROWS_16][PAGE_TOKENS_64]",
                      ["alignas(64) thread_local uint16_t, = {} at thread init",
                       "4 heads: rows 4..15 zero padding; 16 heads: all written",
                       "one scratch per specialization, per thread"],
                      C["rows_fill"], C["rows"], "amx_attn.cpp:284, 277-283",
                      tag_word="changed"))
    boxes.append(("P[TILE_ROWS_16][PAGE_TOKENS_64]", "amx_attn.cpp:284 (the thread_local "
                  "declaration), 276-283 (the comment)"))
    # arrow 2: the P tile loads (unchanged)
    y2 = y + 70
    o.append(arrow(fid, "rows", [(AXC, y2), (AXC, y2 + 44)], C["rows"], 1.4))
    how_many(y2 + 14, ["4 loads: 2 halves x 2 s, &P[0][s * DIM_STEP_32], P_ROW_BYTES",
                       "16 rows x 32 tokens per load"], "amx_attn.cpp:295-301", C["rows"])
    boxes.append(("4 loads: 2 halves x 2 s (P_TILE_4)", "amx_attn.cpp:295-301 (the half and "
                  "s loops; _tile_loadd(P_TILE_4, &P[0][s * DIM_STEP_32], P_ROW_BYTES))"))
    o.append(text(AXC - 8, y2 + 26, "unchanged", 9, "end", fill=muted, weight=700))

    # ---- P_TILE_4 ------------------------------------------------------------------
    y = y2 + 44
    o.append(tile_box(BX, y, BW, 46, "P_TILE_4",
                      ["16 rows x 32 tokens per load (the A operand); s = 0, 1"],
                      "amx_attn.cpp:55, 301"))
    boxes.append(("P_TILE_4", "amx_attn.cpp:53-55 (P loads into tile 4), 301 (the load)"))
    # arrow 3: the tile products (unchanged)
    y3 = y + 46
    o.append(arrow(fid, "rows", [(AXC, y3), (AXC, y3 + 44)], C["rows"], 1.4))
    how_many(y3 + 14, ["16 _tile_dpbf16ps: 2 halves x 2 s x 4 tiles",
                       "B operand: V_EVEN_SLICE_TILE_5 / V_ODD_SLICE_TILE_6 (v_pairs)"],
             "amx_attn.cpp:302-321", C["rows"])
    boxes.append(("16 _tile_dpbf16ps: 2 halves x 2 s x 4 tiles", "amx_attn.cpp:295-322 (the "
                  "half and s loops; the four V loads into V_EVEN_SLICE_TILE_5 / "
                  "V_ODD_SLICE_TILE_6 and the four _tile_dpbf16ps per s)"))
    o.append(text(AXC - 8, y3 + 26, "unchanged", 9, "end", fill=muted, weight=700))

    # ---- ACCUMULATOR_TILE_0..3 ---------------------------------------------------------
    y = y3 + 44
    o.append(tile_box(BX, y, BW, 58, "ACCUMULATOR_TILE_0..3",
                      ["16 rows x 16 dims fp32 each; tile j = dim slice half * 4 + j",
                       "row i of the product = row i of the A operand (P row i)"],
                      "amx_attn.cpp:44-47, 306-321; amx_attn_iface.hpp:104-105"))
    boxes.append(("ACCUMULATOR_TILE_0..3 (PV)", "amx_attn.cpp:44-47 (the constants), 306-321 "
                  "(_tile_dpbf16ps per dim slice); amx_attn_iface.hpp:104-105 (output row i "
                  "of a tile multiply comes from row i of the A operand)"))
    # arrow 4: the tile stores (unchanged)
    y4 = y + 58
    o.append(arrow(fid, "blk", [(AXC, y4), (AXC, y4 + 44)], C["blk"], 1.4))
    how_many(y4 + 14, ["8 stores: 2 halves x 4 _tile_stored, 16 rows each",
                       "o + half * 64 + 16 * j, row stride O_ROW_BYTES"],
             "amx_attn.cpp:323-326, 73-74", C["blk"])
    boxes.append(("8 stores: 2 halves x 4 _tile_stored", "amx_attn.cpp:323-326 (the four "
                  "_tile_stored per half); 73-74 (O_ROW_BYTES)"))
    o.append(text(AXC - 8, y4 + 26, "unchanged", 9, "end", fill=muted, weight=700))

    # ---- o ----------------------------------------------------------------------------
    y = y4 + 44
    OH = 84
    o.append(data_box(BX, y, BW, OH, "o (the caller's amx_o)",
                      ["[16][128] fp32: 16 rows written either way",
                       "rows group_heads..15 = the products of the zero",
                       "padding rows of P (4 heads); 16 heads: all real rows"],
                      C["blk_fill"], C["blk"], "amx_attn_iface.hpp:253-255, 103-106"))
    boxes.append(("o (the caller's amx_o)", "amx_attn_iface.hpp:253-255 (o MUST hold 16 * 128 "
                  "fp32), 103-106 (Note [Tile stores write 16 rows]); self_attention.hpp:1790 "
                  "(alignas(64) float amx_o[...])"))
    # the rows of o for the two group sizes (small grids, 16 rows each)
    ocw, och = 4, 3.5

    def o_cell(group_heads, hi_row):
        def cell(c, r):
            if hi_row is not None and r == hi_row:
                return (C["hi_fill"], ink, None)
            if r < group_heads:
                return (C["blk_fill"], C["blk"], None)
            return (C["empty_fill"], C["empty"], "1.5 1")
        return cell
    gx1, gx2, gy = GX, GX + 16 * ocw + 24, y + 16
    o.append(text(gx1, y + 10, "rows of o: 4 heads", 8.5, fill=muted))
    o.append(grid(gx1, gy, 16, 16, ocw, och, o_cell(4, None)))
    o.append(text(gx2, y + 10, "16 heads", 8.5, fill=muted))
    o.append(grid(gx2, gy, 16, 16, ocw, och, o_cell(16, HEAD_EXAMPLE)))
    o.append(text(gx2 + 16 * ocw + 6, gy + HEAD_EXAMPLE * och + 6, "o[9]", 8, mono=True))
    o.append(cite(W - 20, y + OH - 2, "amx_attn_iface.hpp:103-106"))
    boxes.append(("rows of o: 4 heads | 16 heads (the small grids)", "amx_attn_iface.hpp:"
                  "103-106 (rows group_heads..15 of o are the products of the zero padding "
                  "rows of P; for 16 heads every row of o is a real row)"))
    boxes.append(("o[9] (the worked example's output row)", "amx_attn_iface.hpp:66 "
                  "(O[group_heads][128] = bf16(P) . V_page: row 9 of o is head 9's output); "
                  "self_attention.hpp:1794-1799 (the update from the AMX PV output: amx_o + offset * "
                  "operation_head_size)"))
    # arrow 5: the caller's reads
    y5 = y + OH
    o.append(arrow(fid, "blk", [(AXC, y5), (AXC, y5 + 44)], C["blk"], 1.4))
    how_many(y5 + 14, ["rows 0..operation_kv_mul-1 of amx_o: one memcpy of",
                       "operation_head_size floats per head; rows kv_mul..15 ignored"],
             "self_attention.hpp:1795-1800", C["blk"])
    boxes.append(("rows 0..operation_kv_mul-1 of amx_o", "self_attention.hpp:1795-1800 (the "
                  "memcpy per head), 1788-1789 (only rows 0..kv_mul-1 of amx_o carry the "
                  "result)"))

    # ---- the caller ---------------------------------------------------------------------
    y = y5 + 44
    o.append(rect(BX, y, BW, 56, C["soft"], C["line"], 1, 4))
    o.append(text(BX + 8, y + 15, "[caller] v*/s*/m* update", 9.5, weight=700))
    o.append(lines(BX + 8, y + 28, ["reads rows 0..operation_kv_mul-1 of amx_o:",
                                     "fma into v_star, s_star, m_star per head"], 8.5, 10.5,
                   fill=muted))
    o.append(cite(BX + BW - 4, y + 52, "self_attention.hpp:1794-1811"))
    boxes.append(("[caller] v*/s*/m* update", "self_attention.hpp:1794-1811 (the v*/s*/m* "
                  "update from the AMX PV output)"))

    # ---- the unchanged span (left bracket) -------------------------------------------
    top, bot = y2, y5
    bx = BX - 14
    o.append(f'<polyline points="{bx + 6},{top} {bx},{top} {bx},{bot} {bx + 6},{bot}" '
             f'fill="none" stroke="{C["line"]}" stroke-width="1.2"/>')
    mid = (top + bot) / 2
    o.append(text(bx - 6, mid, "unchanged: the P tile loads, the 16 products, the 8 stores "
                  "(head 294-327)", 8.5, "middle", fill=muted, weight=600,
                  extra=f' transform="rotate(-90 {bx - 6} {mid})"'))
    boxes.append(("unchanged: the P tile loads, the 16 products, the 8 stores",
                  "amx_attn.cpp:294-327 (P_ROW_BYTES, the half and s loops, the stores: the "
                  "same lines as base 241-274)"))

    H = y + 56 + 14
    cap = ("Updates B1 (the PV row), drawn top to bottom. Only the first arrow changed: the "
           "conversion writes group_heads rows of P (the base bound GROUP_HEADS_4 is the red "
           "dashed box). The P tile loads, the 16 tile products and the 8 tile stores are the "
           "same lines as before, so o still receives 16 rows, and rows group_heads..15 are "
           "the products of P's zero rows; the small grids show which rows of o are real "
           "for 4 and for 16 heads (row 9 = the worked example). The caller reads rows "
           "0..operation_kv_mul-1.")
    legend = [
        ("rows", "green: exp_rows, the P scratch (changed: rows 0..group_heads-1 written), "
                 "the conversion arrow and the P tile loads"),
        ("unit", "grey-blue: the tile registers P_TILE_4 and ACCUMULATOR_TILE_0..3 "
                 "(unchanged)"),
        ("blk", "purple: the output o, its 8 tile stores, the rows the caller reads; the "
                "real rows of o in the small grids"),
        ("empty", "grey dashed cells: rows 4..15 of o for 4 heads (the products of the zero "
                  "padding rows of P)"),
        ("hi", "the worked example: row 9 of o for 16 heads (o[9][d] = sum over t of "
               "P[9][t] * V[t][d])"),
        ("gone", "red dashed: the base loop bound q < GROUP_HEADS_4 (removed)"),
        ("ctx", "grey: the caller's v*/s*/m* update in self_attention.hpp"),
        ("green and purple arrows: the data flow, each labelled with how many", "multi",
         [("arrow", C["rows"]), ("arrow", C["blk"])]),
        ("thin grey bracket: the span of unchanged steps (head 294-327)", "line", C["line"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = the loop bound q < group_heads; 'changed' = the P scratch"),
    ]
    return figure(fid, W, H, "A4: the PV data flow, exp_rows to the caller's reads",
                  "".join(o), cap, boxes=boxes, legend=legend)


def figs():
    return [_fig_scratch(), _fig_flow()]
