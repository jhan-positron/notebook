"""Change diagram of unit q1 of the PR 4956 page for h/tron/kernels/k_vnni.hpp:
MAX_KV_MUL_16, the contract comment and signature of qk_group, and the split
above 16 heads (head lines 18-46).

Line numbers are head line numbers of h/tron/kernels/k_vnni.hpp
("kernels/k_vnni.hpp:NN") unless another file is named.
"""
from svg_helpers import C, arrow, cite, figure, lines, marker_defs, rect, text
from base_kernels import FONTS, acc_regs

BASE = ("Updates B2 and B1: the split branch of B2 is drawn for kv_mul = 20 (a test case): two "
        "passes of qk_group, heads 0..15 and 16..19, each with its own q offset, s offset and its "
        "own 16 accumulators of B1; no head's accumulator is shared between passes, so the add "
        "order of every head is the same as in a single pass.")


def _pass(o, boxes, fid, x, y, w, title, heads, q_off, s_off, n_acc, ref):
    o.append(rect(x, y, w, 150, "#fff", C["ink"], 1.2, 5))
    o.append(text(x + 8, y + 16, title, 11, mono=True, weight=600))
    o.append(text(x + 8, y + 30, f"heads {heads}", 9.5, fill=C["muted"]))
    o.append(text(x + 8, y + 42, f"q + {q_off}", 9, mono=True, fill=C["q"]))
    o.append(text(x + 8, y + 54, f"s + {s_off}", 9, mono=True, fill=C["q"]))
    o.append(acc_regs(x + 60, y + 62, w - 72, n=min(n_acc, 4), h=7, gap=2, mask=0xffff, label_x=x + 56))
    if n_acc > 4:
        o.append(text(x + 60 + (w - 72) / 2, y + 62 + 4 * 9 + 8, f"... {n_acc} accumulators acc[0..{n_acc - 1}]",
                      8.5, "middle", True, fill=C["muted"]))
    else:
        o.append(text(x + 60 + (w - 72) / 2, y + 62 + 4 * 9 + 8, f"{n_acc} accumulators acc[0..{n_acc - 1}]",
                      8.5, "middle", True, fill=C["muted"]))
    o.append(text(x + 8, y + 132, "one __m512 per head: 16 lanes = 16 tokens", 8.5, fill=C["muted"]))
    o.append(cite(x + w - 4, y + 146, ref))
    boxes.append((title, ref))


def fig():
    fid = "kernels-d1"
    W, H = 700, 470
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "q": C["q"]})]
    o.append(text(16, 18, "kv_mul > MAX_KV_MUL_16: the split, drawn for kv_mul = 20 (test section "
                  "\"20 query heads\")", 11, weight=700))
    # the call
    o.append(rect(16, 30, 668, 56, C["q_fill"], C["q"], 1.2, 5))
    o.append(text(24, 46, "qk_group<20, q_scalar>(k_page, q, live, s, s_stride)", 11, mono=True,
                  weight=600))
    o.append(text(24, 60, "20 > MAX_KV_MUL_16 (line 40): \"Each head has its own accumulator, so the "
                  "split changes no head's add order.\" (41)", 9, fill=C["muted"]))
    o.append(text(24, 74, "MAX_KV_MUL_16 = 16: query heads scored per pass, one accumulator register "
                  "per head (lines 20-21)", 9, fill=C["muted"]))
    o.append(cite(680, 82, "kernels/k_vnni.hpp:20-21, 40-45"))
    boxes.append(("qk_group<20, q_scalar> (the split)", "kernels/k_vnni.hpp:40-45"))
    boxes.append(("MAX_KV_MUL_16", "kernels/k_vnni.hpp:20-21"))
    # two passes
    _pass(o, boxes, fid, 16, 120, 320, "qk_group<16, q_scalar>", "0..15", "0", "0", 16,
          "kernels/k_vnni.hpp:42")
    _pass(o, boxes, fid, 364, 120, 320, "qk_group<20 - 16, q_scalar>", "16..19",
          "MAX_KV_MUL_16 * HEAD_SIZE_128", "MAX_KV_MUL_16 * s_stride", 4, "kernels/k_vnni.hpp:43-45")
    o.append(arrow(fid, "ink", [(120, 86), (120, 120)], C["ink"]))
    o.append(text(128, 106, "pass 1 (line 42)", 9, fill=C["muted"]))
    o.append(arrow(fid, "ink", [(560, 86), (560, 120)], C["ink"]))
    o.append(text(568, 106, "pass 2 (lines 43-45)", 9, fill=C["muted"]))
    # q and s offsets picture
    y = 290
    o.append(text(16, y, "the same k_page and live in both passes; q and s are offset by whole heads:", 10,
                  weight=600))
    # q rows
    o.append(text(16, y + 24, "q", 10, mono=True, weight=600))
    for h in range(20):
        x = 40 + h * 32
        o.append(rect(x, y + 12, 30, 16, C["q_fill"], C["q"], 0.8, 2))
        o.append(text(x + 15, y + 24, str(h), 8.5, "middle", True))
    o.append(rect(38, y + 10, 16 * 32 - 2 + 4, 20, "none", C["ink"], 1.2, 3))
    o.append(rect(38 + 16 * 32, y + 10, 4 * 32 - 2 + 4, 20, "none", C["ink"], 1.2, 3))
    o.append(text(40, y + 42, "rows 0..15: q + 0", 9, fill=C["muted"]))
    o.append(text(684, y + 42, "rows 16..19: q + 16 * HEAD_SIZE_128 (44)", 9, "end", fill=C["muted"]))
    # s rows
    o.append(text(16, y + 72, "s", 10, mono=True, weight=600))
    for h in range(20):
        x = 40 + h * 32
        o.append(rect(x, y + 60, 30, 16, C["q_fill"], C["q"], 0.8, 2))
        o.append(text(x + 15, y + 72, str(h), 8.5, "middle", True))
    o.append(rect(38, y + 58, 16 * 32 + 2, 20, "none", C["ink"], 1.2, 3))
    o.append(rect(38 + 16 * 32, y + 58, 4 * 32 + 2, 20, "none", C["ink"], 1.2, 3))
    o.append(text(40, y + 90, "rows 0..15: s + 0", 9, fill=C["muted"]))
    o.append(text(684, y + 90, "rows 16..19: s + 16 * s_stride (44-45)", 9, "end", fill=C["muted"]))
    boxes.append(("q + MAX_KV_MUL_16 * HEAD_SIZE_128 (the q offset of pass 2: rows 16..19)", "kernels/k_vnni.hpp:43-44"))
    boxes.append(("s + MAX_KV_MUL_16 * s_stride (the s offset of pass 2: rows 16..19)", "kernels/k_vnni.hpp:44-45"))
    o.append(lines(16, y + 112, [
        "The contract (lines 23-31): s[h * s_stride + t] = q_h . K_t (UNSCALED) for every token t whose bit is set in live;",
        "the other entries of s are left untouched; the K storage of a token whose bit is clear is never read.",
        "static_assert(kv_mul > 0) (39). Tested with KV_MUL = 4 (one pass), 20 (16 + 4) and 32 (16 + 16)",
        "[t_k_vnni_layout.cpp:301-313]; 32 recurses once: qk_group<16> then qk_group<16>.",
    ], 9, 12))
    legend = [
        ("q", "violet: the query side: the call, the q rows, the s rows, the accumulators"),
        ("box", "white box, ink outline: one pass of qk_group"),
        ("ink frame: the rows one pass covers", "none", C["ink"], False, False),
        ("arrow", "ink arrow: the two recursive calls"),
    ] + FONTS
    return figure(fid, W, H, "The split above 16 heads: two passes with their own q and s offsets",
                  "".join(o),
                  "Updates B2 and B1: for kv_mul = 20 the split runs qk_group<16> on heads 0..15 and "
                  "qk_group<4> on heads 16..19, the second with q and s moved by 16 heads. Each pass "
                  "owns its accumulators, so a head's scores are added in the same order as in one "
                  "pass. The text below restates the contract of the comment at lines 23-31.",
                  boxes, legend=legend)
