"""Change diagram A3 of the PR 5015 amx_attn.cpp page: qk_rowmajor_128x4
becomes a template; lanes 1..3 of the transposing store exist only for 16 heads.

Facts drawn here (head 5061623a34 unless marked base 6198824246):
  * the kernel is `template <size_t group_heads> requires(group_heads_ok(
    group_heads))` (amx_attn.cpp:191-192); the base kernel was a plain
    function (base amx_attn.cpp:149);
  * the tile part (4 _tile_zero, 4 steps x (1 Q load + 4 x (K load +
    _tile_dpbf16ps)), 4 _tile_stored into s_transposed) is unchanged
    (amx_attn.cpp:202-225) and computes all 16 accumulator columns for both
    sizes;
  * the unpack loop (stages 1 and 2) is unchanged (amx_attn.cpp:231-253);
  * the removed loop (base amx_attn.cpp:209-213) stored rows 0..3 with literal
    0x88 selectors; now s_block = s + r * 16 (254), store_transposed_rows<0>
    always (255), lanes 1..3 under if constexpr (256-260); the comment at
    227-230 says it;
  * transpose_sim.py: "group_heads 4: rows written = [0, 1, 2, 3] selectors
    {0: (0x88, 0x88)}"; 16 heads: all 16 rows; the worked example
    s_transposed[37][9] -> store_transposed_rows<2>, k = 1 -> s[9][37].
"""
from svg_helpers import C, arrow, cite, figure, line, lines, marker_defs, rect, text
from base_amx_attn import (HEAD_EXAMPLE, TOKEN_EXAMPLE, TILE_R, fit, ink, muted, s_grid,
                           step_box, tag)

BASE = ("Updates B3 step 5 and B4 (d): the store of the transpose becomes "
        "store_transposed_rows<0> always plus lanes 1..3 under if constexpr for 16 heads, so "
        "per tile r the caller's s gets rows 0..3 (4 heads) or rows 0..15 (16 heads).")


def fig():
    fid = "amx_attn-d3"
    W = 700
    o = [marker_defs(fid, {"ink": ink, "rows": C["rows"]})]
    boxes = []
    o.append(text(20, 18, "qk_rowmajor_128x4<group_heads>: the parts that did not change and "
                  "the store that did", 12.5, weight=700))

    # ---- the template header (changed) and the base header (removed) ---------------
    y = 30
    HX, HW, HH = 20, 430, 50
    o.append(rect(HX, y, HW, HH, C["hw_fill"], C["hw"], 1.3, 4))
    o.append(text(HX + 8, y + 15, fit("template <size_t group_heads>", 10, HW - 16, True, "hdr"),
                  10, mono=True, weight=600))
    o.append(text(HX + 8, y + 27, fit("  requires(group_heads_ok(group_heads))", 10, HW - 16,
                                      True, "hdr"), 10, mono=True, weight=600))
    o.append(text(HX + 8, y + 40, fit("one body, compiled for GROUP_HEADS_4 and GROUP_HEADS_16", 8.5, HW - 100, False,
                                      "hdr"), 8.5, fill=muted))
    o.append(tag(HX + HW - 8, y + 15, "changed", muted))
    o.append(cite(HX + HW - 4, y + HH - 4, "amx_attn.cpp:191-192, 330-354"))
    boxes.append(("template <size_t group_heads> requires(group_heads_ok(group_heads))",
                  "amx_attn.cpp:191-192 (the definition's header), 330-354 (the explicit "
                  "instantiations); amx_attn_iface.hpp:242-247 (the declaration)"))
    BX, BW = 470, 210
    o.append(rect(BX, y, BW, HH, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(text(BX + 8, y + 15, "before:", 9, fill=C["gone"], weight=700))
    o.append(text(BX + 52, y + 15, fit("void qk_rowmajor_128x4(", 9, BW - 60, True, "before"),
                  9, mono=True, weight=600))
    o.append(lines(BX + 8, y + 28, ["a plain function: one body, written for",
                                    "the 4 useful query rows"], 8.5, 10.5, fill=muted))
    o.append(cite(BX + BW - 4, y + HH - 4, "base amx_attn.cpp:146-149"))
    boxes.append(("before: void qk_rowmajor_128x4(...) (a plain function)",
                  "base amx_attn.cpp:146-149 (the base comment: 'the 4 useful query rows', and "
                  "the non-template definition)"))

    # ---- the unchanged parts: B3 steps 2-4 and the unpack loop of step 5 -----------
    y = 92
    SW = 660
    body = ["4 Q loads, 16 K loads, 16 _tile_dpbf16ps, 4 tile stores: s_transposed[64][16];",
            "all 16 accumulator columns are computed for both group sizes"]
    h = 30 + 11.5 * len(body) + 6
    o.append(step_box(20, y, SW, h, "2-4", "_tile_zero x 4; for step 0..3: Q load, 4 x (K load, "
                      "_tile_dpbf16ps); _tile_stored x 4", body, "amx_attn.cpp:202-225",
                      C["unit_fill"], C["unit"], "[unchanged]"))
    boxes.append(("steps 2-4: _tile_zero x 4; for step 0..3: Q load, 4 x (K load, "
                  "_tile_dpbf16ps); _tile_stored x 4", "amx_attn.cpp:202-225 (identical in base "
                  "amx_attn.cpp:157-180)"))
    o.append(arrow(fid, "ink", [(35, y + h), (35, y + h + 10)], ink, 1.1))
    y += h + 12
    body = ["per tile r: 4 row groups x (4 loads, 4 unpack_ps, 4 unpack_pd) -> u[4][4]; the "
            "same for both group sizes"]
    h = 30 + 11.5 * len(body) + 6
    o.append(step_box(20, y, SW, h, "5", "for r 0..3: the unpack loop (stages 1 and 2) -> "
                      "u[row_group][k]", body, "amx_attn.cpp:231-253", C["pend_fill"], C["pend"],
                      "[unchanged]"))
    boxes.append(("step 5: for r 0..3: the unpack loop (stages 1 and 2) -> u[row_group][k]",
                  "amx_attn.cpp:231-253 (identical in base amx_attn.cpp:186-208); 227-230 (the "
                  "comment: stages 1 and 2 are the same for both group sizes)"))
    o.append(arrow(fid, "ink", [(35, y + h), (35, y + h + 10)], ink, 1.1))
    y += h + 12

    # ---- step 5, the store: before | after ---------------------------------------
    o.append(text(20, y + 10, "step 5, the store (stages 3 and 4), per tile r: before | after",
                  10, weight=700))
    y += 18
    PX, PW, PH = 20, 300, 112
    o.append(rect(PX, y, PW, PH, "#fff", C["gone"], 1.2, 4, "5 3"))
    o.append(tag(PX + 8, y + 15, "removed", C["gone"], anchor="start"))
    o.append(text(PX + 66, y + 15, "for (int k = 0; k < 4; k++)", 9, mono=True, weight=600))
    code = ["p  = _mm512_shuffle_f32x4(u[0][k], u[1][k], 0x88);",
            "q2 = _mm512_shuffle_f32x4(u[2][k], u[3][k], 0x88);",
            "_mm512_storeu_ps(s + k * s_stride_floats + r * 16,",
            "    _mm512_shuffle_f32x4(p, q2, 0x88));"]
    o.append(lines(PX + 8, y + 30, [fit(s, 8.5, PW - 16, True, "before code") for s in code],
                   8.5, 11, mono=True))
    o.append(lines(PX + 8, y + 78, ["rows 0..3 only, literal selectors 0x88:",
                                    "'width-4 specialization' (the base comment)"], 8.5, 10.5,
                   fill=muted))
    o.append(cite(PX + PW - 4, y + PH - 4, "base amx_attn.cpp:209-213, 183-185"))
    boxes.append(("removed: for (int k = 0; k < 4; k++) { p, q2 = _mm512_shuffle_f32x4(..., "
                  "0x88); _mm512_storeu_ps(s + k * s_stride_floats + r * 16, ...) }",
                  "base amx_attn.cpp:209-213 (the loop), 183-185 (the comment 'width-4 "
                  "specialization: only the k-loop stage-2 paths for output rows 0-3 are "
                  "emitted')"))
    AX, AW = 340, 340
    o.append(rect(AX, y, AW, PH, "#fff", ink, 1.2, 4))
    o.append(tag(AX + 8, y + 15, "changed", muted, anchor="start"))
    o.append(text(AX + 62, y + 15, fit("float* const s_block = s + r * 16;", 9, AW - 70, True,
                                        "after"), 9, mono=True, weight=600))
    o.append(text(AX + 8, y + 31, fit("store_transposed_rows<0>(u, s_block, s_stride_floats);",
                                      9, AW - 16, True, "after"), 9, mono=True, weight=600))
    o.append(text(AX + 8, y + 43, "always: lane 0 = (0x88, 0x88), the removed loop's selectors, "
                  "rows 0..3", 8.5, fill=muted))
    EX, EY, EW, EH = AX + 8, y + 50, AW - 16, 40
    o.append(rect(EX, EY, EW, EH, C["eagle_fill"], C["eagle"], 1.2, 3))
    o.append(text(EX + 6, EY + 13, fit("if constexpr (group_heads == GROUP_HEADS_16)", 9, EW - 12,
                                       True, "eagle"), 9, mono=True, weight=600))
    o.append(text(EX + 6, EY + 25, fit("store_transposed_rows<1> <2> <3>(u, s_block, s_stride_floats)", 8.5, EW - 12, True, "eagle"), 8.5,
                  mono=True))
    o.append(text(EX + 6, EY + 35, "16 heads only: lanes 1..3 = rows 4..15", 8.5, fill=muted))
    o.append(cite(AX + AW - 4, y + PH - 4, "amx_attn.cpp:254-260, 161-162"))
    boxes.append(("s_block = s + r * 16", "amx_attn.cpp:254"))
    boxes.append(("store_transposed_rows<0>(u, s_block, s_stride_floats)",
                  "amx_attn.cpp:255 (the call, both sizes); 169-183 (the helper); 161-162 "
                  "(lane 0 = (0x88, 0x88) is the one store sequence the 4-head kernel emits); "
                  "transpose_sim.py (group_heads 4: rows written = [0, 1, 2, 3], selectors "
                  "{0: (0x88, 0x88)})"))
    boxes.append(("if constexpr (group_heads == GROUP_HEADS_16): store_transposed_rows<1>, <2>, "
                  "<3>", "amx_attn.cpp:256-260; 227-230 (the comment: lanes 1..3, rows 4..15, "
                  "only when group_heads is 16); transpose_sim.py (16 heads: all 16 rows "
                  "written)"))
    y += PH

    # ---- the arrows into s, with how many ------------------------------------------
    GY = y + 84                      # the grids' top
    cw, ch = 4, 5
    G4X, G16X = 34, 404
    o.append(arrow(fid, "rows", [(AX + 40, y), (AX + 40, y + 18), (G4X + 128, y + 18),
                                 (G4X + 128, GY - 14)], C["rows"], 1.4))
    o.append(lines(G4X + 136, y + 32, ["per tile r: 1 lane call", "= 4 row stores of 16 floats",
                                       "per page 4 tiles -> rows 0..3"], 8.5, 11, fill=C["rows"],
                   weight=600))
    boxes.append(("per tile r: 1 lane call = 4 row stores of 16 floats; per page 4 tiles -> "
                  "rows 0..3", "amx_attn.cpp:255 (one call per tile r for 4 heads), 176-181 "
                  "(ROWS_PER_LANE_4 stores of one __m512 each), 231 (r = 0..3)"))
    o.append(arrow(fid, "rows", [(AX + AW - 60, y), (AX + AW - 60, y + 18), (G16X + 128, y + 18),
                                 (G16X + 128, GY - 14)], C["rows"], 1.4))
    o.append(lines(G16X + 136, y + 32, ["per tile r: 4 lane calls", "= 16 row stores of 16 floats",
                                        "per page 4 tiles -> rows 0..15"], 8.5, 11,
                   fill=C["rows"], weight=600))
    boxes.append(("per tile r: 4 lane calls = 16 row stores of 16 floats; per page 4 tiles -> "
                  "rows 0..15", "amx_attn.cpp:255-259 (four calls per tile r for 16 heads), "
                  "176-181, 231"))

    # ---- the resulting s per group size (B4 (d)'s grid) -----------------------------
    o.append(text(G4X, GY - 4, "4 heads (llama-8b, kv_mul 4): s[4][s_stride_floats]", 8.5,
                  weight=700))
    o.append(text(G16X, GY - 4, "16 heads (Muse Glimmer): s[16][s_stride_floats]", 8.5,
                  weight=700))
    o.append(s_grid(G4X, GY, 4, cw=cw, ch=ch, tile_r=TILE_R))
    o.append(s_grid(G16X, GY, 16, cw=cw, ch=ch, hi=(HEAD_EXAMPLE, TOKEN_EXAMPLE), tile_r=TILE_R))
    for gx, g in ((G4X, 4), (G16X, 16)):
        for L in range(4):
            stored = L == 0 or g == 16
            f = C["pend_fill"] if L == 0 else (C["eagle_fill"] if stored else C["pend_fill"])
            s = C["pend"] if L == 0 else (C["eagle"] if stored else C["pend"])
            o.append(rect(gx - 14, GY + L * 4 * ch, 10, 4 * ch, f, s, 1, 1,
                          None if stored else "3 2"))
            o.append(text(gx - 9, GY + L * 4 * ch + 14, str(L), 8, "middle", mono=True))
        o.append(text(gx - 14, GY - 4 - 11, "lane", 8, "start", fill=muted))
    by = GY + 16 * ch + 14
    o.append(lines(G4X - 14, by, ["rows 0..3 written (lane 0); rows 4..15 not written",
                                  "(s needs only group_heads rows); lanes 1..3 not stored"],
                   8.5, 11, fill=muted))
    o.append(cite(G4X + 64 * cw, by + 22, "amx_attn_iface.hpp:107-110; amx_attn.cpp:255"))
    boxes.append(("s[4][s_stride_floats] (4 heads): rows 0..3 written, rows 4..15 not written, "
                  "lanes 1..3 not stored", "amx_attn_iface.hpp:107-110 (s needs only "
                  "group_heads rows); amx_attn.cpp:255 (lane 0 only); self_attention.hpp:1756 "
                  "(tensor<operation_kv_mul, page::page_size> s_pages)"))
    o.append(lines(G16X - 14, by, ["rows 0..15 written (lanes 0..3); the worked example",
                                   "s[9][37] = s + 9 * s_stride_floats + 32 + 5, lane 2, k = 1"],
                   8.5, 11, fill=muted))
    o.append(cite(G16X + 64 * cw, by + 22, "amx_attn.cpp:176-181; transpose_sim.py"))
    boxes.append(("s[16][s_stride_floats] (16 heads): rows 0..15 written; s[9][37] = s + 9 * "
                  "s_stride_floats + 32 + 5 (lane 2, k = 1)", "amx_attn.cpp:176-181 (s_rows = "
                  "s_block + lane * ROWS_PER_LANE_4 * s_stride_floats; row k), 254 (s_block = "
                  "s + r * 16); transpose_sim.py (the worked example chain); "
                  "self_attention.hpp:1756"))
    fy = by + 36
    o.append(line(20, fy, W - 20, fy, C["line"]))
    o.append(text(20, fy + 13, "thick frame = tile r = 2 (s_block = s + 2 * 16): token columns "
                  "32..47 of every written row; the same frame in both grids", 8.5, fill=muted))
    o.append(cite(W - 20, fy + 13, "amx_attn.cpp:254, 231-232"))
    boxes.append(("s_block = s + 2 * 16: tile r = 2 = token columns 32..47",
                  "amx_attn.cpp:254 (s_block = s + r * 16), 231-232 (tile r of s_transposed)"))

    H = int(fy + 24)
    cap = ("Updates B3 step 5 and B4 (d) (worked example). The kernel's tile instructions "
           "(steps 2-4) and the unpack loop of step 5 are unchanged and run the same for both "
           "group sizes; what changed is the header (a template on group_heads) and the store "
           "of step 5: the removed loop wrote rows 0..3 of s with literal 0x88 selectors, the "
           "new code calls store_transposed_rows<0> for every tile r and, only in the 16-head "
           "instantiation, lanes 1, 2 and 3 under if constexpr. The two grids show the caller's "
           "s per group size: 4 heads get rows 0..3 per tile (rows 4..15 stay unwritten), 16 "
           "heads get rows 0..15, with s[9][37] (query head 9, token 37, tile r = 2) marked. "
           "The PR description reports that the -O3 object of the 4-head instantiation is "
           "instruction-identical to main's kernel.")
    legend = [
        ("hw", "yellow: the template header, template <size_t group_heads> "
               "requires(group_heads_ok(group_heads))"),
        ("gone", "red dashed: the base code this unit replaces (the plain function header; "
                 "the for (k) store loop with literal 0x88 selectors)"),
        ("unit", "grey-blue step: the tile instructions of B3 steps 2-4, unchanged"),
        ("pend_solid", "vermillion: the unpack loop of B3 step 5 (stages 1 and 2), unchanged; "
                       "lane 0's marker at the left of each s grid"),
        ("box", "white box, ink outline: the store after the change (s_block, "
                "store_transposed_rows<0>)"),
        ("eagle", "sky blue: the if constexpr block (store_transposed_rows<1>, <2>, <3>) and "
                  "the markers of lanes 1..3 at the 16-head grid"),
        ("pend", "vermillion dashed: lanes 1..3 at the 4-head grid, which that instantiation "
                 "does not store"),
        ("rows", "green cells: the rows of s the kernel writes"),
        ("empty", "grey dashed cells: rows 4..15 of s, not written for 4 heads"),
        ("hi", "the worked example: s[9][37] in the 16-head grid"),
        ("thick_ink", "thick ink frame: tile r = 2's 16 token columns (32..47) in each grid"),
        ("green arrows: the stores into s, labelled with how many per tile r and per page",
         "arrow", C["rows"]),
        ("arrow", "ink arrow: the next part of the kernel"),
        ("ink badge with a white number: the B3 step number of the part", ink, ink, False,
         False),
        ("thin grey line: the end of the figure's parts", "line", C["line"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag_changed", "grey 'changed' = changed by this PR; '[unchanged]' = identical "
                             "to base; red 'removed' = removed"),
    ]
    return figure(fid, W, H, "A3: qk_rowmajor_128x4 as a template; lanes 1..3 stored only for "
                  "16 heads", "".join(o), cap, boxes=boxes, legend=legend)
