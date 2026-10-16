"""Change diagram of unit q0 of the PR 4956 page for h/tron/kernels/k_vnni.hpp:
the header comment (head lines 1-5).

Line numbers are head line numbers of h/tron/kernels/k_vnni.hpp
("kernels/k_vnni.hpp:NN") unless another file is named.
"""
from svg_helpers import C, arrow, cite, figure, label_box, lines, marker_defs, rect, text
from base_kernels import FONTS, ctx_box

BASE = ("Updates B2: the header comment places the file between the layout header it reads "
        "(h/tron/tensor/k_vnni.hpp), the Note that says who writes and reads the layout, and the "
        "translation units that may include it because no AMX instruction runs here.")


def fig():
    fid = "kernels-d0"
    W, H = 700, 330
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "muted": C["muted"]})]
    o.append(text(16, 18, "The three statements of the header comment (lines 2-5)", 11, weight=700))
    # the file
    o.append(label_box(230, 120, 210, 60, "h/tron/kernels/k_vnni.hpp",
                       ["the AVX-512 QK score reader of", "the K VNNI layout (line 2)"],
                       C["vnni_fill"], C["vnni"], 11, ref="kernels/k_vnni.hpp:2"))
    boxes.append(("h/tron/kernels/k_vnni.hpp (the AVX-512 QK score reader)", "kernels/k_vnni.hpp:2"))
    # statement 1: the layout header
    o.append(label_box(16, 40, 200, 60, "h/tron/tensor/k_vnni.hpp",
                       ["the K VNNI layout: constants,", "k_vnni_view, detail::k_vnni_access"],
                       C["vnni_fill"], C["vnni"], 11, ref="k_vnni.hpp:1-8; 16"))
    boxes.append(("h/tron/tensor/k_vnni.hpp (the layout header)", "k_vnni.hpp:1-8"))
    o.append(arrow(fid, "ink", [(230, 140), (216, 70)], C["ink"]))
    o.append(text(236, 100, "reads (line 2; #include at 16)", 9, fill=C["muted"]))
    # statement 2: no AMX
    o.append(rect(480, 40, 204, 70, "#fff", C["gone"], 1.2, 5, "5 3"))
    o.append(text(582, 56, "AMX instruction", 11, "middle", True, weight=600))
    o.append(lines(582, 70, ["none runs here (line 3): the file", "needs no -mamx-tile build flag;",
                             "AMX is a later PR's kernel"], 9.5, 12, "middle", fill=C["muted"]))
    o.append(cite(680, 106, "kernels/k_vnni.hpp:3"))
    boxes.append(("AMX instruction: none runs here", "kernels/k_vnni.hpp:3"))
    o.append(arrow(fid, "muted", [(440, 130), (560, 112)], C["muted"], dash="4 3"))
    # consequence: includers
    o.append(ctx_box(440, 130, 244, 96, "any translation unit may include it", [
        "self_attention.hpp:26 (apply_page_tok)",
        "and t/t_k_vnni_layout.cpp:22 (the test)",
        "include it; both compile without",
        "AMX build flags (line 3)",
    ], "kernels/k_vnni.hpp:3; self_attention.hpp:26"))
    boxes.append(("any translation unit may include it (self_attention.hpp, t_k_vnni_layout.cpp)",
                  "kernels/k_vnni.hpp:3; self_attention.hpp:26; t_k_vnni_layout.cpp:22"))
    o.append(arrow(fid, "ink", [(350, 180), (350, 200), (440, 200)], C["ink"]))
    o.append(text(356, 196, "so", 9, fill=C["muted"]))
    # statement 3: the Note
    o.append(ctx_box(16, 220, 300, 90, "Note [K VNNI storage] (kv_cache.hpp)", [
        "\"the layout, who writes it and who reads it\"",
        "(lines 4-5): item 3 names qk_group as the",
        "software reader of every page of a VNNI slot;",
        "the kill switch (TRON_AMX_DISABLE) keeps this reader",
    ], "kv_cache.hpp:685-686, 721-727, 740-746"))
    boxes.append(("Note [K VNNI storage]", "kv_cache.hpp:685-686, 721-727, 740-746"))
    o.append(arrow(fid, "ink", [(290, 180), (230, 220)], C["ink"]))
    o.append(text(300, 230, "described in (lines 4-5)", 9, fill=C["muted"]))
    o.append(text(16, 322, "Comment only: no code changes in this unit.", 9.5, fill=C["muted"]))
    legend = [
        ("vnni", "blue box: this file and the layout header it reads"),
        ("gone", "red dashed: what the file does not contain (an AMX instruction)"),
        ("ctx", "grey box: the includers and the Note in other files"),
        ("arrow", "ink arrow: reads / is described in / may be included by"),
        ("arrow_muted", "grey dashed arrow: the absence that allows the inclusion"),
    ] + FONTS
    return figure(fid, W, H, "The header comment: what the file is, what it reads, who may include it",
                  "".join(o),
                  "Updates B2: the header comment names the layout header this reader reads, states that no "
                  "AMX instruction runs here (so any translation unit may include it: apply_page_tok and "
                  "the layout test do), and points to Note [K VNNI storage] for who writes and reads the "
                  "layout.", boxes, legend=legend)
