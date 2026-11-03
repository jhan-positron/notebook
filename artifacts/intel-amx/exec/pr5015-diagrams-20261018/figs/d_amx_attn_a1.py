"""Change diagram of unit A1 (pack_q_group_128x4 becomes a template) of the
PR 5015 amx_attn.cpp page.

Facts drawn here (head 5061623a34 unless marked base 6198824246):
  * the packer is `template <size_t group_heads> requires(group_heads_ok(
    group_heads))` (amx_attn.cpp:130-131; the gate amx_attn_iface.hpp:149-154);
  * the loop over query heads runs to group_heads (amx_attn.cpp:138) instead
    of GROUP_HEADS_4 (base amx_attn.cpp:135);
  * the output layout is unchanged: packed[((step * 16 + dim_pair) * 16 +
    q_head) * 2 + j] = q_group[q_head * 128 + step * 32 + 2 * dim_pair + j]
    (amx_attn.cpp:139-142; amx_attn_iface.hpp:200-201): 4 panels x 16
    dim-pair rows x 16 columns x 2 values = Q_PACK_ELEMS_2048 bf16 = 4096 B;
  * for 4 heads, columns 4..15 of every panel stay the caller's zero padding
    (amx_attn.cpp:133-135; amx_attn_iface.hpp:192-196; self_attention.hpp:
    1552-1555); for 16 heads every column is written (amx_attn_iface.hpp:
    195-196).
Worked example (STYLE.md): query head 9. step 0, dim_pair 0, j 0:
q_group[1152] -> packed[18]; step 2, dim_pair 5, j 0: q_group[1226] ->
packed[1202] (computed with python before writing).
"""
from svg_helpers import (C, arrow, card_arrow, cite, figure, line, lines,
                         marker_defs, rect, text)
from base_amx_attn import HEAD_EXAMPLE, data_box, fit, panel_grid, tag

BASE = ("Updates B1: the pack arrow of the data model now says group_heads columns "
        "per panel (4 or 16) instead of the fixed 4 of the base, and B1's two panel "
        "grids are drawn here at full size with the loop bound that selects them.")

ink, muted = C["ink"], C["muted"]

# the worked example of this unit: query head 9, two (step, dim_pair, j) triples
STEP_A, PAIR_A, J_A = 0, 0, 0
STEP_B, PAIR_B, J_B = 2, 5, 0


def q_index(head, step, dim_pair, j):
    return head * 128 + step * 32 + 2 * dim_pair + j          # amx_attn.cpp:140-142


def packed_index(step, dim_pair, head, j):
    return ((step * 16 + dim_pair) * 16 + head) * 2 + j      # amx_attn.cpp:139


QA = q_index(HEAD_EXAMPLE, STEP_A, PAIR_A, J_A)     # 1152
PA = packed_index(STEP_A, PAIR_A, HEAD_EXAMPLE, J_A)  # 18
QB = q_index(HEAD_EXAMPLE, STEP_B, PAIR_B, J_B)     # 1226
PB = packed_index(STEP_B, PAIR_B, HEAD_EXAMPLE, J_B)  # 1202
assert (QA, PA, QB, PB) == (1152, 18, 1226, 1202)
PANEL_ELEMS = 16 * 16 * 2   # 512 bf16 per panel


def zoomed_row(x, y, cw, h, group_heads, hi_col=None):
    """One dim-pair row of a panel: 16 columns, each split into j = 0 and
    j = 1; columns group_heads..15 dashed (zero padding); hi_col highlighted
    with its two halves labelled 0 and 1."""
    o = []
    half = cw / 2
    for c in range(16):
        for j in range(2):
            cx = x + c * cw + j * half
            if hi_col is not None and c == hi_col:
                o.append(rect(cx, y, half, h, C["hi_fill"], ink, 0.8, 0))
                o.append(text(cx + half / 2, y + h / 2 + 3, str(j), 8.5, "middle", mono=True))
            elif c < group_heads:
                o.append(rect(cx, y, half, h, C["q_fill"], C["q"], 0.8, 0))
            else:
                o.append(rect(cx, y, half, h, C["empty_fill"], C["empty"], 0.8, 0, "1.5 1"))
    return "".join(o)


def fig():
    fid = "amx_attn-d1"
    W = 700
    o = [marker_defs(fid, {"ink": ink, "q": C["q"], "muted": muted})]
    boxes = []
    o.append(text(20, 18, "pack_q_group_128x4 becomes a template: group_heads query columns "
                  "per panel", 12.5, weight=700))

    # ---- (a) the template header and the loop bound -----------------------------
    o.append(text(20, 36, "(a) the template header, and the one loop bound that changed", 10,
                  weight=700))
    HX, HY, HW, HH = 20, 46, 330, 74
    o.append(rect(HX, HY, HW, HH, C["hw_fill"], C["hw"], 1.3, 4))
    o.append(text(HX + 8, HY + 15, "template <size_t group_heads>", 9.5, mono=True, weight=600))
    o.append(text(HX + 8, HY + 28, "  requires(group_heads_ok(group_heads))", 9.5, mono=True,
                  weight=600))
    o.append(lines(HX + 8, HY + 42, ["a function template on the group size; a size other",
                                     "than GROUP_HEADS_4 / GROUP_HEADS_16 does not compile"],
                   8.5, 10.5, fill=muted))
    o.append(tag(HX + 8, HY + HH - 5, "new", anchor="start"))
    o.append(cite(HX + HW - 4, HY + HH - 4, "amx_attn.cpp:130-131; amx_attn_iface.hpp:149-154"))
    boxes.append(("template <size_t group_heads> requires(group_heads_ok(group_heads))",
                  "amx_attn.cpp:130-131 (the packer's template header); amx_attn_iface.hpp:"
                  "149-154 (group_heads_ok: the group sizes the kernels are compiled for)"))
    BX, BW, BH = 370, 310, 46
    # before (base): the fixed bound
    o.append(rect(BX, HY, BW, BH, "#fff", C["gone"], 1.3, 4, "5 3"))
    o.append(text(BX + 8, HY + 14, "for (size_t q_head = 0;", 9.5, mono=True, weight=600))
    o.append(text(BX + 8, HY + 26, "     q_head < GROUP_HEADS_4; q_head++)", 9.5, mono=True,
                  weight=600))
    o.append(text(BX + 8, HY + BH - 5, "before", 9, fill=C["gone"], weight=700))
    o.append(cite(BX + BW - 4, HY + BH - 4, "base amx_attn.cpp:135"))
    boxes.append(("for (size_t q_head = 0; q_head < GROUP_HEADS_4; q_head++)",
                  "base amx_attn.cpp:135 (the removed loop bound)"))
    NY = HY + BH + 12
    o.append(arrow(fid, "ink", [(BX + 40, HY + BH + 1), (BX + 40, NY - 1)], ink, 1.2))
    o.append(text(BX + 48, NY - 3, "becomes", 8.5, fill=muted))
    o.append(rect(BX, NY, BW, BH, "#fff", ink, 1.2, 4))
    o.append(text(BX + 8, NY + 14, "for (size_t q_head = 0;", 9.5, mono=True, weight=600))
    o.append(text(BX + 8, NY + 26, "     q_head < group_heads; q_head++)", 9.5, mono=True,
                  weight=600))
    o.append(tag(BX + 8, NY + BH - 5, "new", anchor="start"))
    o.append(cite(BX + BW - 4, NY + BH - 4, "amx_attn.cpp:138"))
    boxes.append(("for (size_t q_head = 0; q_head < group_heads; q_head++)",
                  "amx_attn.cpp:138 (the new loop bound: the template parameter)"))
    LY = NY + BH + 18
    o.append(text(20, LY, "outer loops unchanged: step 0..3 (HEAD_SIZE_128 / DIM_STEP_32 panels), "
                  "dim_pair 0..15 (DIM_STEP_32 / 2 rows per panel)", 8.5, fill=muted))
    o.append(cite(W - 20, LY, "amx_attn.cpp:136-137"))
    boxes.append(("outer loops unchanged: step 0..3, dim_pair 0..15",
                  "amx_attn.cpp:136-137 (the step and dim_pair loops, the same as base "
                  "amx_attn.cpp:133-134)"))

    # ---- (b) the data model: q_group -> packed -> one panel ------------------------
    DY = LY + 20
    o.append(text(20, DY, "(b) the output layout is unchanged: one panel for 4 heads and for 16 "
                  "heads", 10, weight=700))
    RY, RH = DY + 12, 80
    o.append(data_box(20, RY, 170, RH, "q_group",
                      ["group_heads x 128 bf16", "4 heads 1024 B, 16 heads 4096 B",
                       "q.data + kv_head * kv_mul * 128"],
                      C["q_fill"], C["q"], "amx_attn_iface.hpp:187-189, 204"))
    boxes.append(("q_group", "amx_attn_iface.hpp:187-189 (one query group: group_heads query "
                  "heads x 128 dims, contiguous bf16), 204 (the parameter); "
                  "self_attention.hpp:1696-1697 (the caller's pointer)"))
    PX, PW = 270, 190
    o.append(arrow(fid, "q", [(190, RY + 40), (PX - 2, RY + 40)], C["q"], 1.4))
    o.append(lines(230, RY + 24, ["1 q_group", "-> 4 panels"], 8.5, 10.5, "middle",
                   fill=C["q"], weight=600))
    boxes.append(("1 q_group -> 4 panels", "amx_attn.cpp:133-140 (one panel per 32-dim step; "
                  "HEAD_SIZE_128 / DIM_STEP_32 = 4 steps; q_group is read at 140)"))
    o.append(data_box(PX, RY, PW, RH, "packed",
                      ["4 panels x 16 dim-pair rows", "x 16 columns x 2 values",
                       "= Q_PACK_ELEMS_2048 bf16 = 4096 B"],
                      C["q_fill"], C["q"], "amx_attn_iface.hpp:156-158, 197-201"))
    boxes.append(("packed", "amx_attn_iface.hpp:156-158 (Q_PACK_ELEMS_2048), 197-201 (the "
                  "layout formula); amx_attn.cpp:139 (dst = packed + ...)"))
    CX, CW = 500, 180
    o.append(rect(CX, RY, CW, RH, C["soft"], C["line"], 1, 4))
    o.append(text(CX + 8, RY + 14, "[caller] packed_amx_query", 9.5, weight=700))
    o.append(text(CX + 8, RY + 27, "pack_q_group_128x4", 8, mono=True))
    o.append(text(CX + 8, RY + 38, "  <geometry.kv_mul()>(q_group, slot)", 8, mono=True))
    o.append(lines(CX + 8, RY + 51, ["slot = amx_qpack_slot (4096 B),",
                                     "zero-filled once by resize()"], 8.5, 10.5, fill=muted))
    o.append(cite(CX + CW - 4, RY + RH - 4, "self_attention.hpp:1687, 1696, 259-261"))
    boxes.append(("[caller] packed_amx_query: pack_q_group_128x4<geometry.kv_mul()>(q_group, "
                  "slot)", "self_attention.hpp:1687 (the function), 1696-1697 (the call with "
                  "geometry.kv_mul()), 259-261 (amx_qpack_slot: bf16 v[Q_PACK_ELEMS_2048]), "
                  "1552-1555 (resize() zero-fills new slots)"))
    o.append(arrow(fid, "muted", [(CX, RY + 44), (PX + PW + 2, RY + 44)], muted, 1.2))
    o.append(text((CX + PX + PW) / 2, RY + 37, "slot", 8, "middle", mono=True, fill=muted))
    boxes.append(("slot (= packed)", "self_attention.hpp:1696-1697 (slot is the second "
                  "argument of the call)"))
    # packed -> one panel
    AX = PX + PW / 2
    o.append(arrow(fid, "q", [(AX, RY + RH), (AX, RY + RH + 18)], C["q"], 1.4))
    o.append(text(AX + 7, RY + RH + 14, "1 panel -> 16 dim-pair rows", 8.5, fill=C["q"],
                  weight=600))
    boxes.append(("1 panel -> 16 dim-pair rows", "amx_attn.cpp:137 (dim_pair < DIM_STEP_32 / 2 "
                  "= 16); amx_attn_iface.hpp:198 (each panel is 16 dim-pair rows x 16 query "
                  "columns)"))
    GT = RY + RH + 32
    o.append(text(AX, GT, "one panel (any step 0..3), drawn for both group sizes:", 9, "middle",
                  weight=700))
    boxes.append(("one panel (any step 0..3)", "amx_attn_iface.hpp:197-199 (4 panels, one per "
                  "32-dim step; each panel 16 dim-pair rows x 16 query columns)"))

    # the two grids
    cw, ch = 12, 9
    GX4, GX16 = 60, 380
    GHY = GT + 14          # grid heading baseline
    GAY = GHY + 30         # the violet arrows over the written columns
    GCY = GAY + 16         # column labels baseline
    GY = GCY + 6           # grid top
    GH = 16 * ch
    o.append(text(GX4, GHY, "4 heads (llama-8b): columns 0..3 written", 9, weight=700))
    boxes.append(("4 heads (llama-8b): columns 0..3 written", "amx_attn.cpp:133-135 (writes "
                  "columns 0..group_heads-1 of every panel); base amx_attn.cpp:130-131 "
                  "(writes columns 0..3)"))
    o.append(text(GX16, GHY, "16 heads (Muse Glimmer): all 16 columns written,", 9, weight=700))
    o.append(text(GX16, GHY + 10, "so the zero precondition is empty", 9, weight=700))
    boxes.append(("16 heads (Muse Glimmer): all 16 columns written, so the zero precondition "
                  "is empty", "amx_attn_iface.hpp:195-196 (for 16 heads every column is "
                  "written, so that precondition is empty)"))
    o.append(card_arrow(fid, "q", [(GX4, GAY), (GX4 + 4 * cw, GAY)], C["q"],
                        "group_heads = 4 of the 16 columns written", label_dx=-2 * cw,
                        label_dy=-5, size=8.5, anchor="start"))
    o.append(card_arrow(fid, "q", [(GX16, GAY), (GX16 + 16 * cw, GAY)], C["q"],
                        "group_heads = 16 of the 16 columns written", label_dx=-8 * cw,
                        label_dy=-5, size=8.5, anchor="start"))
    boxes.append(("group_heads of the 16 columns written", "amx_attn.cpp:138 (q_head < "
                  "group_heads), 133-135 (the comment)"))
    for gx in (GX4, GX16):
        for c in range(16):
            o.append(text(gx + c * cw + cw / 2, GCY, str(c), 8.5, "middle", mono=True,
                          fill=muted))
        o.append(text(gx + 16 * cw + 4, GCY, "q_head", 8.5, mono=True, fill=muted))
        o.append(text(gx - 4, GCY, "dim_pair", 8.5, "end", mono=True, fill=muted))
        for r in (0, 5, 10, 15):
            o.append(text(gx - 4, GY + r * ch + 7, str(r), 8.5, "end", mono=True, fill=muted))
    boxes.append(("q_head 0..15 (the columns), dim_pair 0..15 (the rows)", "amx_attn.cpp:"
                  "137-139 (the dim_pair and q_head loops and the dst index)"))
    o.append(panel_grid(GX4, GY, 4, cw=cw, ch=ch))
    o.append(panel_grid(GX16, GY, 16, cw=cw, ch=ch, hi_col=HEAD_EXAMPLE))
    # the worked example cell: dim_pair 5, column 9
    o.append(rect(GX16 + HEAD_EXAMPLE * cw, GY + PAIR_B * ch, cw, ch, "none", ink, 2.6, 0))
    o.append(text(GX16 + 16 * cw + 6, GY + PAIR_B * ch + 3, "row 5, column 9:", 8.5))
    o.append(text(GX16 + 16 * cw + 6, GY + PAIR_B * ch + 13, "the worked example", 8.5))
    boxes.append(("row 5, column 9: the worked example (dim_pair 5, query head 9)",
                  "amx_attn_iface.hpp:198-199 (16 dim-pair rows x 16 query columns, columns "
                  "0..group_heads-1 = the heads)"))
    GB = GY + GH

    # the zoomed rows: 1 row -> 16 columns x 2 values
    ZW = 17
    ZY = GB + 44
    ZH = 24
    for gx, g, hi in ((GX4, 4, None), (GX16, 16, HEAD_EXAMPLE)):
        ax = gx + (HEAD_EXAMPLE if g == 16 else 2) * cw + cw / 2
        lab = ("1 row -> 16 columns x 2 values" if g == 16
               else "1 row -> 4 of 16 columns written")
        o.append(arrow(fid, "q", [(ax, GB + 2), (ax, ZY - 2)], C["q"], 1.4))
        o.append(text(ax + 7, GB + 24, lab, 8.5, fill=C["q"], weight=600))
        o.append(zoomed_row(gx, ZY, ZW, ZH, g, hi))
        for c in range(16):
            o.append(text(gx + c * ZW + ZW / 2, ZY + ZH + 10, str(c), 8.5, "middle", mono=True,
                          fill=muted))
        o.append(text(gx - 4, ZY + ZH / 2 + 3, "row 5", 8.5, "end", mono=True, fill=muted))
    boxes.append(("1 row -> 16 columns x 2 values", "amx_attn_iface.hpp:199-201 (x 2 paired "
                  "values; the index formula); amx_attn.cpp:139-142 (dst[0], dst[1])"))
    boxes.append(("1 row -> 4 of 16 columns written", "amx_attn.cpp:133-138 (writes columns "
                  "0..group_heads-1 of every panel; q_head < group_heads, 4 here)"))
    NY2 = ZY + ZH + 24
    o.append(text(GX4, NY2, "columns 4..15: zero padding the caller keeps", 8.5, fill=muted))
    o.append(text(GX4, NY2 + 11, "(resize() zero-fills the slot once)", 8.5, fill=muted))
    o.append(cite(GX4, NY2 + 22, "amx_attn.cpp:133-135; self_attention.hpp:1552-1555",
                  anchor="start"))
    boxes.append(("columns 4..15: zero padding the caller keeps", "amx_attn.cpp:133-135 (the "
                  "remaining columns are padding the caller keeps zero); amx_attn_iface.hpp:"
                  "192-196 (a buffer zeroed once at allocation stays valid); "
                  "self_attention.hpp:1552-1555 (resize() zero-fills new slots)"))
    o.append(text(GX16, NY2, f"column 9, j 0: packed[{PB}] = q_group[{QB}]", 8.5, mono=True))
    o.append(text(GX16, NY2 + 11, f"column 9, j 1: packed[{PB + 1}] = q_group[{QB + 1}]", 8.5,
                  mono=True))
    o.append(text(GX16, NY2 + 22, "each column holds the pair j = 0, j = 1 (64 B per row)", 8.5,
                  fill=muted))
    o.append(cite(GX16 + 16 * ZW, NY2 + 33, "amx_attn.cpp:139-142; amx_attn_iface.hpp:200-201"))
    boxes.append((f"column 9, j 0: packed[{PB}] = q_group[{QB}]; j 1: packed[{PB + 1}] = "
                  f"q_group[{QB + 1}]", "amx_attn.cpp:139-142 (dst[0] and dst[1]); "
                  "amx_attn_iface.hpp:200-201 (the index formula)"))

    # ---- (c) the worked example strip ---------------------------------------------
    EY = NY2 + 48
    EH = 80
    o.append(rect(20, EY, W - 40, EH, C["hi_fill"], ink, 1, 4))
    o.append(text(28, EY + 15, "worked example (Muse Glimmer, 16 heads): query head 9; for "
                  "llama-8b (4 heads) head 9 does not exist", 9.5, weight=700))
    o.append(text(28, EY + 29, "q_group[9 * 128 + step * 32 + 2 * dim_pair + j] -> "
                  "packed[((step * 16 + dim_pair) * 16 + 9) * 2 + j]", 8.5, mono=True))
    o.append(text(28, EY + 41, f"step {STEP_A}, dim_pair {PAIR_A}, j {J_A}: q_group[{QA}] -> "
                  f"packed[{PA}]   (panel 0, row 0, column 9, j 0)", 8.5, mono=True))
    o.append(text(28, EY + 53, f"step {STEP_B}, dim_pair {PAIR_B}, j {J_B}: q_group[9 * 128 + "
                  f"{STEP_B * 32} + {2 * PAIR_B}] = q_group[{QB}] -> packed[(({STEP_B} * 16 + "
                  f"{PAIR_B}) * 16 + 9) * 2] = packed[{PB}]", 8.5, mono=True, weight=600))
    o.append(text(28, EY + 66, f"packed[{PB}] = byte {2 * PB} of the 4096-byte slot: panel "
                  f"{STEP_B} starts at element {STEP_B * PANEL_ELEMS} (byte "
                  f"{2 * STEP_B * PANEL_ELEMS}); the framed cell above is row {PAIR_B}, "
                  f"column 9 of it", 8.5, fill=muted))
    o.append(cite(W - 24, EY + EH - 4, "amx_attn.cpp:139-142; amx_attn_iface.hpp:200-201"))
    boxes.append((f"worked example: q_group[9 * 128 + step * 32 + 2 * dim_pair + j] -> "
                  f"packed[((step * 16 + dim_pair) * 16 + 9) * 2 + j]; q_group[{QA}] -> "
                  f"packed[{PA}]; q_group[{QB}] -> packed[{PB}]",
                  "amx_attn.cpp:139-142 (dst index and the two source indices); "
                  "amx_attn_iface.hpp:200-201 (the layout formula)"))

    H = EY + EH + 12
    cap = (BASE + " (a) The packer gained a template header with the requires clause; the "
           "only loop whose bound changed is the query-head loop, from GROUP_HEADS_4 (before, "
           "red dashed) to group_heads (new). (b) The output layout is the same: every panel "
           "is 16 dim-pair rows x 16 columns x 2 values; for 4 heads columns 4..15 stay the "
           "caller's zero padding (dashed), for 16 heads every column is written. The worked "
           "example (query head 9, column 9 of the 16-head panel) follows the unchanged index "
           "formula to packed[18] and packed[1202].")
    legend = [
        ("hw", "yellow: the template header with its requires clause (group_heads_ok)"),
        ("gone", "red dashed: the base loop bound q_head < GROUP_HEADS_4, marked 'before'"),
        ("box", "white box, ink outline: the new loop bound q_head < group_heads"),
        ("q", "violet: q_group, packed, the written columns of a panel and of the zoomed row"),
        ("empty", "grey dashed cells: columns 4..15 of a panel and of its row for 4 heads (zero "
                  "padding the caller keeps)"),
        ("hi", "the worked example: column 9 of the 16-head panel and of its zoomed row, and "
               "the strip at the bottom"),
        ("thick_ink", "thick ink frame: the cell dim_pair 5, column 9 (packed[1202] in panel 2)"),
        ("ctx", "grey: the caller packed_amx_query in self_attention.hpp"),
        ("violet arrows: the data flow, each labelled with how many", "arrow", C["q"]),
        ("arrow", "ink arrow: the base loop bound becomes the new one"),
        ("arrow_muted", "grey arrow: the caller's slot is the packed buffer"),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = added by this PR (the template header, the loop bound); "
                     "red 'before' = the base code"),
    ]
    return figure(fid, W, H, "Unit A1: pack_q_group_128x4 becomes a template", "".join(o), cap,
                  boxes=boxes, legend=legend)
