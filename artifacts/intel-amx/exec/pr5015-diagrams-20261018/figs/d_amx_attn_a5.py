"""Change diagram for unit A5 of the PR 5015 amx_attn.cpp page: the six
explicit instantiations (3 kernels x {GROUP_HEADS_4, GROUP_HEADS_16}).

The chain drawn: the three template declarations in amx_attn_iface.hpp (each
under requires(group_heads_ok(group_heads))) -> the three bodies in
amx_attn.cpp (the ONLY translation unit compiled with -mamx-tile/-mamx-bf16)
-> the explicit instantiation list (a 3 x 2 grid, one compiled body per cell)
-> the two callers in self_attention.hpp, whose template argument is the
model's kv_mul (4 for llama-8b, 16 for Muse Glimmer). A dashed cell shows the
instantiation that does not exist (kv_mul 8): group_heads_ok(8) is false, so
shape_ok rejects the shape and a direct call fails the requires clause.

Every fact comes from the cited head lines (5061623a34) of
src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp,
h/tron/models/self_attention.hpp, t/t_amx_numerics.cpp and
t/t_amx_dispatch_dtype.cpp.
"""
from svg_helpers import (C, arrow, card_arrow, cite, figure, fn_cell, lines,
                         marker_defs, rect, text)
from base_amx_attn import fit, tag

BASE = ("Updates B2: the yellow 'explicit instantiations' box becomes a 3 x 2 grid of "
        "compiled bodies, placed between the three declarations (with their requires "
        "clause), the three kernel bodies in the only AMX translation unit, and the two "
        "callers whose template argument (kv_mul 4 or 16) picks one column; a dashed cell "
        "shows that kv_mul 8 has no instantiation.")

ink, muted = C["ink"], C["muted"]


def fig():
    fid = "amx_attn-d5"
    W = 700
    o = [marker_defs(fid, {"ink": ink, "hw": C["hw"]})]
    boxes = []
    o.append(text(14, 16, "Unit A5: the six explicit instantiations, from the declarations "
                  "to the callers' template arguments", 12.5, weight=700))

    # ---- row A: the declarations in amx_attn_iface.hpp (context) ----------------
    AX, AY, AW, AH = 14, 28, 672, 96
    o.append(rect(AX, AY, AW, AH, C["soft"], C["line"], 1, 6))
    o.append(text(AX + 8, AY + 14, "amx_attn_iface.hpp (the declarations, context)", 10.5,
                  weight=700))
    o.append(rect(AX + 10, AY + 22, AW - 20, 66, C["hw_fill"], C["hw"], 1.3, 4, "5 3"))
    o.append(text(AX + 18, AY + 37, "template <size_t group_heads> requires(group_heads_ok("
                  "group_heads))", 9.5, mono=True, weight=600))
    o.append(lines(AX + 18, AY + 51, [
        "declares pack_q_group_128x4, qk_rowmajor_128x4 and weights_times_v_128x4 with no "
        "body in the header;",
        "a group size outside group_heads_ok is rejected at compile time (the clause is on "
        "the definitions too)"], 8.5, 11, fill=muted))
    o.append(cite(AX + AW - 14, AY + 84, "amx_attn_iface.hpp:202-204, 242-247, 256-262"))
    boxes.append(("template <size_t group_heads> requires(group_heads_ok(group_heads))",
                  "amx_attn_iface.hpp:202-204, 242-247, 256-262 (the three declarations); "
                  "amx_attn.cpp:130-131, 191-192, 264-265 (the definitions repeat the clause)"))

    # ---- arrow A -> B: declarations -> bodies ---------------------------------------
    o.append(arrow(fid, "ink", [(140, AY + AH), (140, 150)], ink, 1.4))
    o.append(text(148, 141, "3 declarations -> 3 bodies, defined only in amx_attn.cpp "
                  "(1 body per kernel)", 8.5, fill=ink, weight=600))
    boxes.append(("3 declarations -> 3 bodies, defined only in amx_attn.cpp",
                  "amx_attn.cpp:330-332 (the kernel bodies live only in this translation "
                  "unit); amx_attn_iface.hpp:2-5 (the implementations live in amx_attn.cpp)"))

    # ---- row B: amx_attn.cpp, the only AMX translation unit ---------------------------
    BX, BY, BW, BH = 14, 152, 672, 336
    o.append(rect(BX, BY, BW, BH, "#fff", C["line"], 1, 6))
    o.append(text(BX + 10, BY + 14, "amx_attn.cpp: the ONLY translation unit compiled with "
                  "-mamx-tile/-mamx-bf16", 10.5, weight=700))
    o.append(cite(BX + 480, BY + 14, "amx_attn.cpp:1-3", anchor="start"))
    boxes.append(("amx_attn.cpp: the ONLY translation unit compiled with -mamx-tile/-mamx-bf16",
                  "amx_attn.cpp:1-3 (the file comment); amx_attn_iface.hpp:3-5"))
    # the three bodies (left column)
    KX, KW, KH = 24, 232, 64
    ROWS = (214, 286, 358)
    o.append(text(KX, 206, "the kernel bodies (one template definition each)", 9.5,
                  weight=700))
    boxes.append(("the kernel bodies (one template definition each)", "amx_attn.cpp:330-331 "
                  "(the kernel bodies live only in this translation unit)"))
    kernels = [
        ("pack_q_group_128x4<group_heads>",
         ["packs one query group into the VNNI B-operand",
          "layout: group_heads columns, the rest zero padding"],
         "amx_attn.cpp:130-146", C["q_fill"], C["q"]),
        ("qk_rowmajor_128x4<group_heads>",
         ["S^T[64][16] = K_page . Q^T in tiles, then the",
          "transposing store of group_heads rows into s"],
         "amx_attn.cpp:187-262", C["rows_fill"], C["rows"]),
        ("weights_times_v_128x4<group_heads>",
         ["O = P[group_heads][64] . V_page: exp rows -> bf16",
          "P, 16 tile products, 8 tile stores into o"],
         "amx_attn.cpp:264-328", C["blk_fill"], C["blk"]),
    ]
    for (name, desc, ref, f, s), y in zip(kernels, ROWS):
        fit(name, 10, KW - 16, True, name)
        for d in desc:
            fit(d, 8, KW - 16, False, name)
        o.append(fn_cell(KX, y, KW, KH, name, desc, ref, tag="changed", fill=f, stroke=s,
                         size=10))
    boxes.append(("pack_q_group_128x4<group_heads>", "amx_attn.cpp:130-146 (the definition); "
                  "amx_attn_iface.hpp:187-204 (the contract)"))
    boxes.append(("qk_rowmajor_128x4<group_heads>", "amx_attn.cpp:187-262 (the definition); "
                  "amx_attn_iface.hpp:235-247"))
    boxes.append(("weights_times_v_128x4<group_heads>", "amx_attn.cpp:264-328 (the "
                  "definition); amx_attn_iface.hpp:249-262"))

    # the explicit instantiation list (yellow frame, 3 x 2 grid)
    GX, GY, GW, GH = 310, 178, 260, 300
    o.append(rect(GX, GY, GW, GH, C["hw_fill"], C["hw"], 1.3, 4))
    o.append(text(GX + 8, GY + 14, "explicit instantiations", 10, mono=True, weight=600))
    o.append(tag(GX + GW - 8, GY + 14, "new"))
    CW = 118
    COLS = (GX + 8, GX + 8 + CW + 8)
    for cx, hdr in zip(COLS, ("GROUP_HEADS_4", "GROUP_HEADS_16")):
        o.append(text(cx + CW / 2, GY + 28, hdr, 9, "middle", mono=True, weight=600))
    boxes.append(("GROUP_HEADS_4, GROUP_HEADS_16 (the two columns)", "amx_attn_iface.hpp:"
                  "142-147 (the constants)"))
    cells = [
        # (row, col, body line, citation)
        (0, 0, "", "amx_attn.cpp:333"), (0, 1, "", "amx_attn.cpp:334"),
        (1, 0, "16 _tile_dpbf16ps", "amx_attn.cpp:335-339"),
        (1, 1, "16 _tile_dpbf16ps", "amx_attn.cpp:340-344"),
        (2, 0, "16 _tile_dpbf16ps", "amx_attn.cpp:345-349"),
        (2, 1, "16 _tile_dpbf16ps", "amx_attn.cpp:350-354"),
    ]
    short = ("pack_q_group_128x4", "qk_rowmajor_128x4", "weights_times_v_128x4")
    for r, c, body, ref in cells:
        cx, cy = COLS[c], ROWS[r]
        o.append(rect(cx, cy, CW, KH, "#fff", C["hw"], 1.2, 3))
        sz = "<GROUP_HEADS_4>" if c == 0 else "<GROUP_HEADS_16>"
        o.append(text(cx + 6, cy + 14, fit(short[r], 8.5, CW - 10, True, "grid"), 8.5,
                      mono=True))
        o.append(text(cx + 6, cy + 26, sz, 9, mono=True, weight=600))
        o.append(text(cx + 6, cy + 38, "1 body", 8, fill=muted))
        if body:
            o.append(text(cx + 6, cy + 49, fit(body, 8, CW - 10, True, "grid"), 8, mono=True,
                          fill=muted))
        o.append(cite(cx + CW - 3, cy + KH - 4, ref))
        boxes.append((f"template void {short[r]}{sz}(...)", f"{ref} (the explicit "
                      "instantiation declaration)"))
    o.append(lines(GX + 8, GY + 256, ["3 kernels x 2 sizes = 6 bodies",
                                      "QK, PV x 2 sizes: 4 x 16 = 64 _tile_dpbf16ps",
                                      "in the binary (the PR description reports)"], 8.5, 10))
    boxes.append(("3 kernels x 2 sizes = 6 bodies", "amx_attn.cpp:333-354 (the six template "
                  "declarations); 330-332 (the comment: the kernel bodies)"))
    boxes.append(("4 x 16 = 64 _tile_dpbf16ps in the binary (the PR description reports)",
                  "amx_attn.cpp:206-221 (QK: 4 steps x 4 slices = 16 _tile_dpbf16ps), "
                  "295-322 (PV: 2 halves x 2 s x 4 tiles = 16)"))
    o.append(tag(GX + 8, GY + GH - 5, "new", anchor="start"))
    o.append(cite(GX + GW - 4, GY + GH - 4, "amx_attn.cpp:330-354"))
    boxes.append(("explicit instantiations: template void kernel<GROUP_HEADS_4>(...) and "
                  "<GROUP_HEADS_16>(...)", "amx_attn.cpp:330-354 (the comment and the six "
                  "template declarations)"))
    # bodies -> grid rows
    for y in ROWS:
        o.append(card_arrow(fid, "ink", [(KX + KW, y + 28), (GX - 2, y + 28)], ink,
                            "2 bodies", label_dy=-5, size=8.5))
    boxes.append(("2 bodies (per kernel: one per group size)", "amx_attn.cpp:333-354 (two "
                  "explicit instantiations per kernel)"))

    # the instantiation that does not exist: kv_mul 8
    DX, DY, DW, DH = 578, 214, 106, 208
    o.append(rect(DX, DY, DW, DH, "#fff", muted, 1.2, 3, "5 3"))
    o.append(text(DX + DW / 2, DY + 16, "kv_mul 8", 9.5, "middle", mono=True, weight=600))
    o.append(lines(DX + DW / 2, DY + 32, ["(llama-70b family)", "does not exist:", "rejected",
                                          "group_heads_ok(8)", "is false, so", "shape_ok is false;",
                                          "a direct call fails", "the requires clause"],
                   8.5, 11, "middle", fill=muted))
    o.append(cite(DX + DW - 4, DY + DH - 14, "amx_attn_iface.hpp:"))
    o.append(cite(DX + DW - 4, DY + DH - 4, "149-154, 161-165"))
    boxes.append(("kv_mul 8: does not exist, rejected (group_heads_ok(8) is false)",
                  "amx_attn_iface.hpp:149-154 (group_heads_ok), 161-165 (shape_ok); "
                  "t_amx_numerics.cpp:118-121 (the llama-70b / qwen-3-32b family stays "
                  "refused: KV_MUL_8)"))
    # requires -> the missing cell
    o.append(arrow(fid, "hw", [(628, AY + AH), (628, DY - 2)], C["hw"], 1.2, "4 3"))
    o.append(text(634, 186, "requires", 8.5, fill=C["hw"], weight=600))
    o.append(text(634, 197, "rejects", 8.5, fill=C["hw"], weight=600))
    boxes.append(("requires rejects (a direct call with group_heads 8 fails at compile time)",
                  "amx_attn_iface.hpp:202-204, 242-247, 256-262 (requires(group_heads_ok("
                  "group_heads)) on each declaration)"))

    # ---- row C left: the equality -----------------------------------------------
    EX, EY, EW, EH = 14, 518, 296, 72
    o.append(rect(EX, EY, EW, EH, C["hw_fill"], C["hw"], 1.3, 4))
    o.append(text(EX + 8, EY + 16, "this list == group_heads_ok", 9.5, mono=True, weight=600))
    o.append(text(EX + 8, EY + 28, "== {GROUP_HEADS_4, GROUP_HEADS_16}", 9.5, mono=True,
                  weight=600))
    o.append(lines(EX + 8, EY + 42, ["'this list is the set of group sizes callers can use:",
                                     "it equals group_heads_ok in amx_attn_iface.hpp'"], 8.5, 11,
                   fill=muted))
    o.append(cite(EX + EW - 4, EY + EH - 4, "amx_attn.cpp:330-332; amx_attn_iface.hpp:149-154"))
    boxes.append(("this list == group_heads_ok == {GROUP_HEADS_4, GROUP_HEADS_16}",
                  "amx_attn.cpp:330-332 (the comment above the instantiations); "
                  "amx_attn_iface.hpp:149-154 (group_heads_ok: g == GROUP_HEADS_4 || g == "
                  "GROUP_HEADS_16)"))
    o.append(arrow(fid, "hw", [(334, GY + GH + 2), (EX + EW - 10, EY - 2)], C["hw"], 1.3))
    o.append(text(338, 506, "equals", 8.5, fill=C["hw"], weight=600))

    # the tests that pin the gate
    TX, TY, TW, TH = 14, 600, 296, 128
    o.append(rect(TX, TY, TW, TH, "#fff", C["line"], 1, 4))
    o.append(text(TX + 8, TY + 14, "tests that pin the two sizes", 9.5, weight=700))
    o.append(lines(TX + 8, TY + 27, [
        "t_amx_numerics.cpp:113-114 STATIC_REQUIRE:",
        "eligible<bf16>(HEAD_SIZE_128, GROUP_HEADS_4) and",
        "the same for GROUP_HEADS_16; 120-121 STATIC_REQUIRE_",
        "FALSE(... KV_MUL_8), comment 118-119: 'the llama-70b /",
        "qwen-3-32b family ... stays refused'.",
        "t_amx_dispatch_dtype.cpp:301 exercise_page<host_bf16,",
        "GROUP_HEADS_16>; 255-276: fakes repeat the requires"],
        8.5, 11, fill=muted))
    o.append(cite(TX + TW - 4, TY + TH - 14, "t_amx_numerics.cpp:113-121;"))
    o.append(cite(TX + TW - 4, TY + TH - 4, "t_amx_dispatch_dtype.cpp:255-276, 301"))
    boxes.append(("STATIC_REQUIRE(eligible<bf16>(HEAD_SIZE_128, GROUP_HEADS_16)); "
                  "STATIC_REQUIRE_FALSE(eligible<bf16>(HEAD_SIZE_128, KV_MUL_8))",
                  "t_amx_numerics.cpp:113-121"))
    boxes.append(("exercise_page<host_bf16, GROUP_HEADS_16>", "t_amx_dispatch_dtype.cpp:301 "
                  "(the 16-head dispatch section); 255-276 (the fake kernels repeat "
                  "requires(group_heads_ok(group_heads)))"))

    # ---- row C right: the callers (context) ---------------------------------------
    PX, PY, PW, PH = 326, 518, 358, 242
    o.append(rect(PX, PY, PW, PH, C["soft"], C["line"], 1, 6))
    o.append(text(PX + 8, PY + 14, "self_attention.hpp (callers, context)", 10.5, weight=700))
    o.append(fn_cell(PX + 8, PY + 22, PW - 16, 64, "packed_amx_query<geometry>",
                     ["pack_q_group_128x4<geometry.kv_mul()>(q_group, slot):",
                      "1 call site; packs this token's Q group on its first request"],
                     "self_attention.hpp:1681-1700, 1696", tag="changed", size=10))
    boxes.append(("packed_amx_query<geometry>", "self_attention.hpp:1681-1700 (the "
                  "definition); 1696 (pack_q_group_128x4<geometry.kv_mul()>)"))
    o.append(fn_cell(PX + 8, PY + 94, PW - 16, 64, "apply_dense_amx_page<geometry>",
                     ["qk_rowmajor_128x4<operation_kv_mul>, weights_times_v_128x4",
                      "<operation_kv_mul>: 2 call sites, 1 per kernel, per (query, page)"],
                     "self_attention.hpp:1745, 1763-1765, 1791-1793", tag="changed", size=10))
    boxes.append(("apply_dense_amx_page<geometry>", "self_attention.hpp:1725-1812 (the "
                  "definition); 1745 (constexpr operation_kv_mul = geometry.kv_mul()), "
                  "1763-1765 (the QK call), 1791-1793 (the PV call)"))
    o.append(rect(PX + 8, PY + 166, PW - 16, 68, "#fff", C["line"], 1, 4))
    o.append(text(PX + 16, PY + 180, "amx_on = eligible<scalar>(head_size, kv_mul) && "
                  "available()", 9, weight=700))
    o.append(lines(PX + 16, PY + 193, [
        "geometry.kv_mul() (packer) and operation_kv_mul (QK, PV) are the",
        "template argument: 4 for llama-8b, 16 for Muse Glimmer. kv_mul 8 fails",
        "shape_ok, so amx_on is false and the page runs the AVX dotter loop."],
        8.5, 11, fill=muted))
    o.append(cite(PX + PW - 12, PY + PH - 6, "self_attention.hpp:1536-1539, 1745, 1707"))
    boxes.append(("amx_on = eligible<scalar>(head_size, kv_mul) && available()",
                  "self_attention.hpp:1536-1539 (amx_eligible, amx_on); 1745 (operation_kv_mul); "
                  "1707 (everything else runs the dotter loop)"))
    # callers -> the instantiation each call site resolves to
    for cx, lab in zip(COLS, ("kv_mul 4 (llama-8b)", "kv_mul 16 (Muse Glimmer)")):
        xm = cx + CW / 2
        o.append(arrow(fid, "ink", [(xm, PY - 2), (xm, GY + GH + 2)], ink, 1.4))
        o.append(text(xm + 6, 502, lab, 8.5, fill=ink, weight=600))
    boxes.append(("kv_mul 4 (llama-8b), kv_mul 16 (Muse Glimmer): each call site resolves to "
                  "1 of the 2 instantiations", "self_attention.hpp:1696 "
                  "(pack_q_group_128x4<geometry.kv_mul()>), 1745 (operation_kv_mul = "
                  "geometry.kv_mul()), 1763, 1791"))

    H = 770
    cap = ("Updates B2: the explicit instantiation box of the function model is opened into "
           "the full chain. Top: the three declarations in the interface header, each under "
           "requires(group_heads_ok(group_heads)). Middle: the three bodies in amx_attn.cpp, "
           "the only translation unit compiled for AMX, and the 3 x 2 grid of explicit "
           "instantiations (new), one compiled body per cell; the dashed cell at the right "
           "is the instantiation kv_mul 8 does not get. Bottom: the list equals "
           "group_heads_ok (yellow), the tests that pin both sizes, and the two callers, "
           "whose template argument (the model's kv_mul: 4 for llama-8b, 16 for Muse "
           "Glimmer) resolves each call site to one column.")
    legend = [
        ("ctx", "grey panels: the two context files, amx_attn_iface.hpp (the declarations) "
                "and self_attention.hpp (the callers)"),
        ("lane", "white box, thin grey outline: amx_attn.cpp (the only AMX translation unit), "
                 "the tests note and the amx_on note"),
        ("q", "violet: the pack_q_group_128x4<group_heads> body"),
        ("rows", "green: the qk_rowmajor_128x4<group_heads> body"),
        ("blk", "purple: the weights_times_v_128x4<group_heads> body"),
        ("hw", "yellow: the explicit instantiation list (the frame) and the equality with "
               "group_heads_ok"),
        ("white cell, yellow outline: one explicit instantiation = one compiled body "
         "(template void kernel<GROUP_HEADS_x>(...))", "#fff", C["hw"], False, False),
        ("yellow dashed box: the requires clause quoted from the declarations", C["hw_fill"],
         C["hw"], True, False),
        ("deleted", "white, grey dashed: the instantiation that does not exist (kv_mul 8): "
                    "group_heads_ok(8) is false, shape_ok and the requires clause reject it"),
        ("box", "white cell: a caller with its one-line description (packed_amx_query, "
                "apply_dense_amx_page)"),
        ("arrow", "ink arrows: declarations -> bodies (3 -> 3), body -> instantiations (2 "
                  "bodies each), call site -> the instantiation it resolves to"),
        ("yellow arrows: 'equals' (solid) from the list to group_heads_ok; 'requires rejects' "
         "(dashed) from the clause to the missing cell", "arrow", C["hw"]),
        "font_mono", "font_sans", "font_cite",
        ("font_tag", "bold 'new' = the explicit instantiation list (added by this PR); "
                     "'changed' = the three kernel bodies and the two callers"),
    ]
    return figure(fid, W, H, "Unit A5: the six explicit instantiations", "".join(o), cap,
                  boxes=boxes, legend=legend)
