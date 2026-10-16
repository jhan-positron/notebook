"""Change diagram of unit q2 of the PR 4956 page for h/tron/kernels/k_vnni.hpp:
the fp16 query path (head lines 46-52).

Line numbers are head line numbers of h/tron/kernels/k_vnni.hpp
("kernels/k_vnni.hpp:NN") unless another file is named.
"""
from svg_helpers import C, arrow, cite, figure, label_box, lines, marker_defs, rect, text
from base_kernels import FONTS, ctx_box

BASE = ("Updates B2: the fp16 branch is drawn as its data flow: the kv_mul x 128 fp16 queries are "
        "widened one by one into a 64-byte-aligned float array on the stack, the float branch of "
        "the block loop runs on that array, and the branch returns; the test checks this path "
        "against dotter<float, 128> on the same widened queries.")


def fig():
    fid = "kernels-d2"
    W, H = 700, 316
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "q": C["q"]})]
    o.append(text(16, 18, "q_scalar == fp16: widen the queries, then take the float path (lines 46-52)",
                  11, weight=700))
    # fp16 q
    o.append(rect(16, 40, 200, 90, C["q_fill"], C["q"], 1.2, 5))
    o.append(text(24, 56, "q: const fp16*", 11, mono=True, weight=600))
    o.append(text(24, 70, "kv_mul x HEAD_SIZE_128 values", 9.5, fill=C["muted"]))
    for h in range(4):
        o.append(rect(24, 78 + h * 10, 150, 8, "#fff", C["q"], 0.8, 1))
    o.append(text(180, 100, "fp16", 9, mono=True, fill=C["muted"]))
    o.append(cite(212, 126, "kernels/k_vnni.hpp:35, 46"))
    boxes.append(("q: const fp16* (the fp16 queries)", "kernels/k_vnni.hpp:35, 46"))
    # the loop
    o.append(arrow(fid, "q", [(216, 85), (260, 85)], C["q"]))
    o.append(text(238, 102, "for i (48)", 8.5, "middle", True, fill=C["q"]))
    o.append(label_box(260, 50, 180, 70, "qf[i] = float(q[i])",
                       ["one conversion per value", "(lines 48-50)"],
                       "#fff", C["ink"], 11, ref="kernels/k_vnni.hpp:48-50"))
    boxes.append(("qf[i] = float(q[i])", "kernels/k_vnni.hpp:48-50"))
    # qf
    o.append(arrow(fid, "q", [(440, 85), (484, 85)], C["q"]))
    o.append(rect(484, 40, 200, 90, C["q_fill"], C["q"], 1.2, 5))
    o.append(text(492, 56, "alignas(64) float qf[...]", 11, mono=True, weight=600))
    o.append(text(492, 70, "kv_mul * HEAD_SIZE_128 floats on the", 9.5, fill=C["muted"]))
    o.append(text(492, 82, "stack of this call (line 47)", 9.5, fill=C["muted"]))
    for h in range(4):
        o.append(rect(492, 88 + h * 8, 150, 6, "#fff", C["q"], 0.8, 1))
    o.append(text(648, 110, "fp32", 9, mono=True, fill=C["muted"]))
    o.append(cite(680, 126, "kernels/k_vnni.hpp:47"))
    boxes.append(("alignas(64) float qf[kv_mul * HEAD_SIZE_128]", "kernels/k_vnni.hpp:47"))
    # the float call
    o.append(arrow(fid, "ink", [(584, 130), (584, 160)], C["ink"]))
    o.append(rect(300, 160, 384, 72, "#fff", C["ink"], 1.2, 5))
    o.append(text(308, 176, "qk_group<kv_mul, float>(k_page, qf, live, s, s_stride)", 11, mono=True,
                  weight=600))
    o.append(text(308, 190, "the float branch of the block loop (lines 78-88): k_even / k_odd", 9,
                  fill=C["muted"]))
    o.append(text(308, 202, "widening, 2 FMAs per pair row and head", 9, fill=C["muted"]))
    o.append(text(308, 214, "then return (52): the fp16 call does nothing else", 9, fill=C["muted"]))
    o.append(cite(680, 228, "kernels/k_vnni.hpp:51-52"))
    boxes.append(("qk_group<kv_mul, float>(k_page, qf, live, s, s_stride)", "kernels/k_vnni.hpp:51-52"))
    # test
    o.append(ctx_box(16, 160, 270, 72, "the test's fp16 case", [
        "q_f16_widened[i] = float(q_f16[i]); s_f16 is",
        "checked against dotter<float, 128>(q_f16_widened)",
    ], "t_k_vnni_layout.cpp:213-214, 220-221, 268, 294"))
    boxes.append(("the test's fp16 case (q_f16_widened, dot_f16_widened)",
                  "t_k_vnni_layout.cpp:213-214, 220-221, 268, 294"))
    o.append(lines(16, 254, [
        "The static_assert at lines 54-55 admits bf16 and float only in the block loop; fp16 reaches it",
        "through this branch. The stack array costs kv_mul x 128 x 4 bytes: 2 KiB for kv_mul = 4, 8 KiB for",
        "kv_mul = 16 (the largest pass, see Q1). The widening is exact: fp16 -> fp32 loses no value.",
    ], 9, 12))
    legend = [
        ("q", "violet: the query arrays (fp16 in, float out)"),
        ("white row, violet outline: one query row inside an array", "#fff", C["q"], False, False),
        ("box", "white box, ink outline: the conversion loop and the float call"),
        ("ctx", "grey box: the test case that checks this path"),
        ("violet arrow: the flow of the query values", "arrow", C["q"]),
        ("arrow", "ink arrow: the call of the float branch"),
    ] + FONTS
    return figure(fid, W, H, "The fp16 query path: widen to float on the stack, then the float branch",
                  "".join(o),
                  "Updates B2: the fp16 branch converts every query value to float into a 64-byte-aligned "
                  "stack array, calls the float instantiation of qk_group on it and returns. The test "
                  "compares that result with the row-major float dotter on the same widened queries.",
                  boxes, legend=legend)
