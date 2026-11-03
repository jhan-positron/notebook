"""Change diagram of unit A2 of the PR 5015 amx_attn.cpp page:
store_transposed_rows<lane>, the transposing store for one 128-bit lane
(4 score rows). Head 5061623a34, base 6198824246.

The figure updates B4: the (c) strips and the (d) lane table of B4 are the
body and the selector table of ONE new helper; the base store loop (lane 0
only, literal 0x88) is drawn as the before state.

Facts drawn here come from the head lines of src/tron/kernels/amx_attn.cpp
(150-162 the comment, 163-167 the constants, 169-183 the template, 254-260
the caller), the base lines 209-213 (the removed loop) and transpose_sim.py
(lane L of u[row_group][k] = column 4L+k; selectors per lane; the worked
example head 9 / token 37 -> lane 2, k 1 -> s[9][37]).
"""
from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, line,
                         lines, marker_defs, rect, text)
from base_amx_attn import (HEAD_EXAMPLE, K_INDEX, LANE, LANE_ROWS, SELECTORS,
                           TILE_R, TOKEN_EXAMPLE, fit, reg_lanes, s_grid, tag)

BASE = ("Updates B4: the (c) strips and the (d) lane table of B4 are the loop body "
        "and the selector table of one new helper, store_transposed_rows<lane>; the "
        "figure adds the base store loop it replaces (lane 0 only, literal 0x88) and "
        "the two selector decisions taken from the bits of lane.")

ink, muted = C["ink"], C["muted"]


def fig():
    fid = "amx_attn-d2"
    W = 700
    o = [marker_defs(fid, {"ink": ink})]
    boxes = []
    o.append(text(20, 18, "store_transposed_rows<lane>: stages 3 and 4 of the transpose for "
                  "one 128-bit lane", 12.5, weight=700))
    o.append(cite(W - 20, 32, "amx_attn.cpp:148-185, 254-260; base amx_attn.cpp:209-213"))

    # ---- row A: before (the base loop) -> the helper ---------------------------
    AY, AH = 40, 100
    BX, BW = 20, 290
    o.append(rect(BX, AY, BW, AH, "#fff", C["gone"], 1.3, 4, "5 3"))
    o.append(text(BX + 8, AY + 15, "before: base amx_attn.cpp:209-213", 9.5, fill=C["gone"],
                  weight=700))
    o.append(lines(BX + 8, AY + 29, [
        fit("for (int k = 0; k < 4; k++) {", 8.5, BW - 16, True, "before"),
        fit("  p  = _mm512_shuffle_f32x4(u[0][k], u[1][k], 0x88);", 8.5, BW - 16, True, "before"),
        fit("  q2 = _mm512_shuffle_f32x4(u[2][k], u[3][k], 0x88);", 8.5, BW - 16, True, "before"),
        fit("  _mm512_storeu_ps(s + k * s_stride_floats + r * 16,", 8.5, BW - 16, True, "before"),
        fit("      _mm512_shuffle_f32x4(p, q2, 0x88)); }", 8.5, BW - 16, True, "before")],
        8.5, 11, mono=True))
    o.append(text(BX + 8, AY + 86, "rows 0..3 only (lane 0); the literal 0x88 three times, "
                  "the literal 4", 8.5, fill=muted))
    o.append(cite(BX + BW - 4, AY + AH - 4, "base amx_attn.cpp:209-213"))
    boxes.append(("before: the base store loop (_mm512_shuffle_f32x4 with the literal 0x88, "
                  "rows 0..3 only)", "base amx_attn.cpp:209-213 (the for (k) loop with three "
                  "0x88 shuffles and one store per k)"))

    FX, FW = 366, 314
    o.append(fn_cell(FX, AY, FW, AH, "store_transposed_rows<lane>",
                     ["assembles output row 4 * lane + k (one query head, 16",
                      "tokens) from lane `lane` of u[0..3][k] by two shuffle stages"],
                     "amx_attn.cpp:169-183", tag="new", fill=C["pend_fill"], stroke=C["pend"]))
    o.append(lines(FX + 8, AY + 58, [
        fit("u: __m512 [4][4] (the unpacked registers of one tile)", 8.5, FW - 16, True,
            "fn params"),
        fit("s_block: float* (= s + r * 16); s_stride_floats: size_t", 8.5, FW - 16, True,
            "fn params")], 8.5, 11, mono=True, fill=muted))
    boxes.append(("store_transposed_rows<lane>", "amx_attn.cpp:169-173 (the template and its "
                  "three parameters), 150-162 (the comment: output row 4 * lane + k is "
                  "assembled from lane `lane` of u[0..3][k] by two _mm512_shuffle_f32x4 stages)"))
    o.append(arrow(fid, "ink", [(BX + BW, AY + 50), (FX - 2, AY + 50)], ink, 1.3))
    o.append(text((BX + BW + FX) / 2, AY + 42, "replaced by", 8, "middle", fill=ink, weight=600))
    o.append(text((BX + BW + FX) / 2, AY + 62, "lane 0 =", 8, "middle", fill=ink, weight=600))
    o.append(text((BX + BW + FX) / 2, AY + 72, "base loop", 8, "middle", fill=ink, weight=600))
    boxes.append(("replaced by: lane 0 = (0x88, 0x88) is the one store sequence the 4-head "
                  "kernel emits", "amx_attn.cpp:161-162; base amx_attn.cpp:209-213"))

    # ---- row B: the two selector decisions from the bits of lane ---------------
    BY, BH = 158, 64
    o.append(arrow(fid, "ink", [(FX + FW / 2, AY + AH), (FX + FW / 2, BY - 2)], ink, 1.3))
    o.append(text(FX + FW / 2 - 6, BY - 6, "lane (the template argument) -> 2 constexpr "
                  "selectors", 8, "end", fill=ink, weight=600))
    boxes.append(("lane (the template argument) -> 2 constexpr selectors", "amx_attn.cpp:160-162 "
                  "(the selectors are immediates, so lane is a template argument), 169, 174-175"))

    def decision(x, title, expr, meaning, ref):
        o.append(rect(x, BY, 320, BH, C["pend_fill"], C["pend"], 1.3, 4))
        o.append(text(x + 8, BY + 15, title, 10, mono=True, weight=600))
        o.append(text(x + 8, BY + 29, fit(expr, 8.5, 304, True, title), 8.5, mono=True))
        o.append(text(x + 8, BY + 42, fit(meaning, 8.5, 304, False, title), 8.5, fill=muted))
        o.append(cite(x + 316, BY + BH - 4, ref))

    decision(20, "bit 0 of lane -> pair_sel",
             "pair_sel = (lane & 1) ? LANES_ODD_0XDD : LANES_EVEN_0X88",
             "stage 3: pairs row groups 0/1 and 2/3; lanes {0, 2} or {1, 3}",
             "amx_attn.cpp:174; 154-158")
    boxes.append(("pair_sel = (lane & 1) ? LANES_ODD_0XDD : LANES_EVEN_0X88",
                  "amx_attn.cpp:174; 154-158 (stage 3 pairs row groups 0/1 and 2/3 and selects "
                  "lanes {0, 2} or {1, 3}: bit 0 of lane)"))
    decision(360, "bit 1 of lane -> quad_sel",
             "quad_sel = (lane & 2) ? LANES_ODD_0XDD : LANES_EVEN_0X88",
             "stage 4: joins the two pairs; first or second lane of each",
             "amx_attn.cpp:175; 158-160")
    boxes.append(("quad_sel = (lane & 2) ? LANES_ODD_0XDD : LANES_EVEN_0X88",
                  "amx_attn.cpp:175; 158-160 (stage 4 joins the two pairs and selects the first "
                  "or the second lane of each: bit 1 of lane)"))

    # ---- row C: the lane table and the named constants --------------------------
    TY = 238
    cols = [("lane", 40), ("pair_sel", 66), ("quad_sel", 66), ("s rows written", 96),
            ("emitted for", 180)]
    TW = sum(w for _, w in cols)
    o.append(rect(20, TY, TW, 18, C["soft"], C["line"], 1, 0))
    x = 20
    for name, w in cols:
        o.append(text(x + 4, TY + 13, name, 8.5, weight=700))
        x += w
    who = {0: "both sizes (= the base loop)", 1: "16 heads only (if constexpr)",
           2: "16 heads only (if constexpr)", 3: "16 heads only (if constexpr)"}
    ty = TY
    for L in range(4):
        ty += 18
        o.append(rect(20, ty, TW, 18, C["eagle_fill"] if L else "#fff",
                      C["eagle"] if L else C["line"], 1, 0))
        x = 20
        vals = [str(L), SELECTORS[L][0], SELECTORS[L][1], LANE_ROWS[L], who[L]]
        for (name, w), v in zip(cols, vals):
            o.append(text(x + 4, ty + 13, v, 8.5, mono=name != "emitted for",
                          weight=700 if L == LANE and name == "lane" else None))
            x += w
    TB = ty + 18
    o.append(cite(20 + TW, TB + 11, "amx_attn.cpp:174-176, 161-162, 255-260; transpose_sim.py"))
    boxes.append(("lane 0..3: pair_sel, quad_sel, s rows written, emitted for",
                  "amx_attn.cpp:174-176 (the selectors and the row offset), 161-162 (lane 0 = "
                  "(0x88, 0x88) is the one store sequence the 4-head kernel emits), 255-260 "
                  "(the caller: lane 0 always, lanes 1..3 under if constexpr); transpose_sim.py "
                  "(selectors per lane)"))

    KX, KW = 486, 194
    o.append(rect(KX, TY, KW, TB - TY, "#fff", ink, 1.2, 4))
    o.append(lines(KX + 8, TY + 15, ["LANES_EVEN_0X88 = 0x88", "LANES_ODD_0XDD = 0xdd",
                                      "ROWS_PER_LANE_4 = 4"], 9, 12, mono=True, weight=600))
    o.append(lines(KX + 8, TY + 52, ["named constants: replace the",
                                      "literals 0x88 and 4 of the base loop"], 8.5, 11, fill=muted))
    o.append(tag(KX + 8, TB - 5, "new", anchor="start"))
    o.append(cite(KX + KW - 4, TB - 4, "amx_attn.cpp:163-167"))
    boxes.append(("LANES_EVEN_0X88 = 0x88, LANES_ODD_0XDD = 0xdd, ROWS_PER_LANE_4 = 4",
                  "amx_attn.cpp:163-167 (the three constexpr constants and the comment of "
                  "ROWS_PER_LANE_4)"))

    # ---- row D: the loop body for the worked example (lane 2, k = 1) --------------
    DY = TB + 50
    o.append(arrow(fid, "ink", [(36, TB), (36, DY - 2)], ink, 1.3))
    o.append(text(44, TB + 22, "4 rows per lane call (k = 0..3, ROWS_PER_LANE_4); drawn: lane 2, "
                  "k = 1", 8.5, fill=ink, weight=600))
    o.append(text(44, TB + 36, "worked example: head 9, token 37 -> lane 2, k = 1 -> s row 9; "
                  "pair_sel 0x88, quad_sel 0xdd", 9.5, weight=700))
    boxes.append(("4 rows per lane call (k = 0..3, ROWS_PER_LANE_4)", "amx_attn.cpp:177 (the "
                  "for k loop bound), 165-167"))
    boxes.append(("worked example: head 9, token 37 -> lane 2, k = 1 -> s row 9",
                  "transpose_sim.py (column 9 -> lane 2, k 1; store_transposed_rows<2> row k = 1 "
                  "writes s row 9); amx_attn.cpp:152-153"))
    FH = 160
    o.append(rect(20, DY, 660, FH, "none", C["pend"], 1.2, 4))
    o.append(text(28, DY + 13, "for (size_t k = 0; k < ROWS_PER_LANE_4; k++)  (k = 1 shown)", 9,
                  mono=True, weight=600))
    o.append(cite(676, DY + 13, "amx_attn.cpp:177-182"))
    boxes.append(("for (size_t k = 0; k < ROWS_PER_LANE_4; k++)", "amx_attn.cpp:177-182 (the "
                  "loop body: p, q2, the store)"))
    SX, SW, SH = 76, 420, 22
    k = K_INDEX
    rows_d = [
        ("p =", [f"u[0][{k}] L0", f"u[0][{k}] L2", f"u[1][{k}] L0", f"u[1][{k}] L2"], 3,
         None, f"p = _mm512_shuffle_f32x4(u[0][{k}], u[1][{k}], pair_sel 0x88): lanes {{0, 2}} of each"),
        ("q2 =", [f"u[2][{k}] L0", f"u[2][{k}] L2", f"u[3][{k}] L0", f"u[3][{k}] L2"], None,
         None, f"q2 = _mm512_shuffle_f32x4(u[2][{k}], u[3][{k}], pair_sel 0x88)"),
        ("row 9 =", ["p L1 = col 9 t32..35", "p L3 = col 9 t36..39", "q2 L1 = col 9 t40..43",
                     "q2 L3 = col 9 t44..47"], 1, C["rows_fill"],
         "row 9 = _mm512_shuffle_f32x4(p, q2, quad_sel 0xdd): lanes {1, 3}; L1 holds token 37"),
    ]
    ys = []
    for i, (lab, labels, hi, lf, note) in enumerate(rows_d):
        ry = DY + 22 + i * 44
        ys.append(ry)
        o.append(text(28, ry + SH / 2 + 3, lab, 9.5, mono=True, weight=600))
        o.append(reg_lanes(SX, ry, SW, SH, labels, hi_lane=hi, lane_fill=lf))
        o.append(text(SX, ry + SH + 11, fit(note, 8.5, SW + 60, False, lab), 8.5, fill=C["pend"]))
    boxes.append(("p, q2, row 9 (the three _mm512_shuffle_f32x4 of lane 2, k = 1)",
                  "amx_attn.cpp:178-181; 154-160 (stage 3, stage 4; 0x88 even lanes, 0xdd odd "
                  "lanes); transpose_sim.py (lane L of u[row_group][k] = column 4L+k; output row "
                  "r = column r)"))
    # the how-many of the shuffles: p and q2 feed row 9
    mid = [y + SH / 2 for y in ys]
    AXX = SX + SW + 22
    o.append(line(SX + SW + 2, mid[1], AXX, mid[1], ink, 1.3))
    o.append(arrow(fid, "ink", [(SX + SW + 2, mid[0]), (AXX, mid[0]), (AXX, mid[2]),
                                (SX + SW + 4, mid[2])], ink, 1.3))
    o.append(lines(AXX + 8, mid[1] - 8, ["3 _mm512_shuffle_f32x4", "per row: p, q2,",
                                          "then the stored row"], 8.5, 11, fill=ink, weight=600))
    boxes.append(("3 _mm512_shuffle_f32x4 per row: p, q2, then the stored row",
                  "amx_attn.cpp:178-181"))

    # ---- row E: the store and the row offset arithmetic ---------------------------
    EY = DY + FH + 30
    o.append(arrow(fid, "ink", [(120, DY + FH), (120, EY - 2)], ink, 1.3))
    o.append(text(128, EY - 8, "1 _mm512_storeu_ps per row (16 floats = 16 tokens)", 8.5,
                  fill=ink, weight=600))
    boxes.append(("1 _mm512_storeu_ps per row (16 floats = 16 tokens)", "amx_attn.cpp:180-181"))
    OX, OW, OH = 20, 400, 104
    o.append(rect(OX, EY, OW, OH, C["hi_fill"], ink, 1, 4))
    o.append(text(OX + 8, EY + 15, "the row offset of the worked example (lane 2, k = 1)", 9.5,
                  weight=700))
    o.append(lines(OX + 8, EY + 29, [
        fit("s_block = s + r * 16 = s + 2 * 16", 8.5, OW - 16, True, "offset"),
        fit("s_rows = s_block + lane * ROWS_PER_LANE_4 * s_stride_floats", 8.5, OW - 16, True,
            "offset"),
        fit("       = s_block + 2 * 4 * s_stride_floats", 8.5, OW - 16, True, "offset"),
        fit("row 9 = s_rows + 1 * s_stride_floats = s + 9 * s_stride_floats + 32", 8.5, OW - 16,
            True, "offset")], 8.5, 11, mono=True))
    o.append(text(OX + 8, EY + 84, "-> s[9][32..47]; element 5 = s[9][37]", 8.5, mono=True,
                  weight=700))
    o.append(cite(OX + OW - 4, EY + OH - 4, "amx_attn.cpp:176, 180-181, 254; transpose_sim.py"))
    boxes.append(("s_rows = s_block + lane * ROWS_PER_LANE_4 * s_stride_floats",
                  "amx_attn.cpp:176"))
    boxes.append(("s_block = s + r * 16", "amx_attn.cpp:254"))
    boxes.append(("row 9 = s_rows + 1 * s_stride_floats -> s[9][32..47]; element 5 = s[9][37]",
                  "amx_attn.cpp:180-181 (s_rows + k * s_stride_floats); transpose_sim.py (the "
                  "worked example chain)"))

    GX, GY = 444, EY + 14
    cw, ch = 3.6, 4
    o.append(text(GX - 14, GY - 6, "lane", 8, "end", fill=muted))
    o.append(text(GX, GY - 6, "s[16][s_stride_floats] (16 heads); tile r = 2 framed", 8.5,
                  fill=muted))
    o.append(s_grid(GX, GY, 16, cw=cw, ch=ch, hi=(HEAD_EXAMPLE, TOKEN_EXAMPLE), tile_r=TILE_R))
    for L in range(4):
        o.append(rect(GX - 14, GY + L * 4 * ch, 10, 4 * ch, C["eagle_fill"] if L else C["pend_fill"],
                      C["eagle"] if L else C["pend"], 1, 1))
        o.append(text(GX - 9, GY + L * 4 * ch + 12, str(L), 8, "middle", mono=True))
    o.append(text(GX, GY + 16 * ch + 12, "rows 4..15 (lanes 1..3): 16 heads only", 8, fill=muted))
    o.append(cite(GX + 64 * cw, GY + 16 * ch + 24, "amx_attn.cpp:176; amx_attn_iface.hpp:107-110"))
    boxes.append(("s[16][s_stride_floats] (16 heads): lane L writes rows 4L..4L+3; tile r = 2 "
                  "= columns 32..47", "amx_attn.cpp:176 (lane * ROWS_PER_LANE_4 * "
                  "s_stride_floats), 254 (s + r * 16); amx_attn_iface.hpp:107-110 (s needs only "
                  "group_heads rows)"))

    H = EY + OH + 16
    cap = ("Updates B4: the (c) strips and the (d) lane table of B4 now belong to one new "
           "helper, store_transposed_rows<lane>, drawn here with its before state. Top: the "
           "base store loop (lane 0 only, the literal 0x88 three times) is replaced by the "
           "template, whose two selectors are constexpr from the bits of lane (bit 0 -> "
           "pair_sel, bit 1 -> quad_sel); the table lists the four lanes, of which the 4-head "
           "kernel emits lane 0 only. Bottom: the loop body for the worked example (lane 2, "
           "k = 1): three _mm512_shuffle_f32x4 assemble s row 9 and one _mm512_storeu_ps "
           "writes it at s_rows + 1 * s_stride_floats, with s_rows = s_block + 2 * 4 * "
           "s_stride_floats, so the element lands in s[9][37]. transpose_sim.py checked the "
           "mapping.")
    legend = [
        ("gone", "red dashed: the base store loop (before), replaced by the helper"),
        ("pend_solid", "vermillion: store_transposed_rows<lane> (the new helper), the two "
                       "selector decisions pair_sel / quad_sel, the lanes of p and q2, the "
                       "shuffle notes, lane 0's marker at the left of s"),
        ("vermillion frame: the for k loop body (ROWS_PER_LANE_4 iterations)", "none",
         C["pend"], False, False),
        ("box", "white box, ink outline: the named constants LANES_EVEN_0X88, LANES_ODD_0XDD, "
                "ROWS_PER_LANE_4"),
        ("eagle", "sky blue: lanes 1..3 in the table and at the left of s (16 heads only)"),
        ("lane", "thin grey outline: the table row of lane 0 (both sizes)"),
        ("ctx", "grey: the table header"),
        ("hi", "the worked example: the row offset box and s[9][37] in s"),
        ("worked-example fill with vermillion outline: the lane that holds the element in p "
         "and in row 9", C["hi_fill"], C["pend"], False, False),
        ("green fill, vermillion lanes: the assembled register 'row 9'", C["rows_fill"],
         C["pend"], False, False),
        ("rows", "green: the caller's s rows (16 heads)"),
        ("thick_ink", "thick ink frame: tile r = 2's 16 token columns in s"),
        ("arrow", "ink arrows: 'replaced by', the selectors from lane, and the how-many of "
                  "the loop (4 rows per lane call, 3 shuffles per row, 1 store per row)"),
        ("thin ink line: q2 joining the shuffle arrow", "line", ink),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR (the helper, the named constants)"),
    ]
    return figure(fid, W, H, "Change A2: store_transposed_rows<lane>, the transposing store "
                  "for one 128-bit lane", "".join(o), cap, boxes=boxes, legend=legend)
