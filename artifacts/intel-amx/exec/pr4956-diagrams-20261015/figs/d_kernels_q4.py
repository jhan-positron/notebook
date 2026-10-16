"""Change diagram of unit q4 of the PR 4956 page for h/tron/kernels/k_vnni.hpp:
the masked store of the scores (head lines 92-99).

Line numbers are head line numbers of h/tron/kernels/k_vnni.hpp
("kernels/k_vnni.hpp:NN") unless another file is named.
"""
from svg_helpers import C, arrow, cite, figure, line, lines, marker_defs, rect, text
from base_kernels import EX, FONTS, KV_MUL_4, LIVE_0_40, MASKS, acc_regs, mask_hex, score_grid

BASE = ("Updates B1: the s box of B1 is drawn at the lane level for the worked example: after block "
        "c = 2 each accumulator's 16 lanes go to s[h * s_stride + 32..47] under mask 0x01ff, so "
        "tokens 32..40 receive their score and 41..47 keep the caller's -infinity fill; the stores "
        "of blocks 0 and 1 filled 0..31 before, block 3 is never stored.")


def fig():
    fid = "kernels-d4"
    W, H = 700, 400
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "q": C["q"]})]
    o.append(text(16, 18, "The masked store (lines 92-94) after block c = 2 of the worked example "
                  "(mask 0x01ff, kv_mul = 4)", 11, weight=700))
    # acc
    o.append(text(16, 44, "acc[0..3] after the 4 steps of block 2:", 10, weight=600))
    o.append(acc_regs(70, 52, 320, n=KV_MUL_4, h=12, gap=3, mask=MASKS[2]))
    o.append(text(440, 62, "16 lanes = tokens 32..47;", 9, fill=C["muted"]))
    o.append(text(440, 74, "lanes 9..15 (tokens 41..47) hold 0", 9, fill=C["muted"]))
    o.append(text(440, 86, "and are not stored", 9, fill=C["muted"]))
    boxes.append(("acc[h] after the 4 steps of block c", "kernels/k_vnni.hpp:60-63, 91"))
    # arrows
    for h in range(KV_MUL_4):
        y = 52 + h * 15 + 6
        o.append(arrow(fid, "q", [(390, y), (420, y)], C["q"]))
    o.append(arrow(fid, "q", [(420, 58), (420, 146)], C["q"]))
    o.append(text(426, 110, "4 stores, one per head", 8.5, fill=C["q"], weight=600))
    o.append(text(16, 128, "_mm512_mask_storeu_ps(s + h * s_stride + c * BLOCK_TOKENS_16, mask, acc[h]) "
                  "for h in 0..kv_mul - 1 (92-94)", 9.5, mono=True))
    # s grid
    sx, sy = 70, 150
    o.append(text(16, sy + 8, "s", 10, mono=True, weight=600))
    o.append(score_grid(sx, sy, 576, 56, live=LIVE_0_40))
    for h in range(KV_MUL_4):
        o.append(text(sx - 6, sy + h * 14 + 11, f"h = {h}", 8.5, "end", True))
    for c in range(4):
        o.append(text(sx + c * 144 + 72, sy + 68, f"c = {c}: s + h * s_stride + {16 * c}", 8.5, "middle",
                      True, fill=C["muted"]))
    o.append(rect(sx + 2 * 144 - 2, sy - 2, 144 + 4, 60, "none", C["ink"], 1.4, 2))
    o.append(text(sx + 2 * 144 + 72, sy + 82, "this store: block 2, 9 lanes written", 8.5, "middle",
                  fill=C["ink"], weight=600))
    o.append(cite(sx + 576, sy + 96, "kernels/k_vnni.hpp:92-94"))
    boxes.append(("_mm512_mask_storeu_ps(s + h * s_stride + c * BLOCK_TOKENS_16, mask, acc[h])",
                  "kernels/k_vnni.hpp:92-94"))
    boxes.append(("s[h * s_stride + t] (the caller's s_pages)", "kernels/k_vnni.hpp:24-25; self_attention.hpp:1900, 1970"))
    # token 37: a thin frame round its column
    tx = sx + 37 * 9
    o.append(rect(tx - 0.5, sy - 1, 9.5, 58, "none", C["ink"], 1.2, 1))
    # what the caller sees
    o.append(rect(16, 262, 668, 92, C["hi_fill"], C["ink"], 1, 5))
    o.append(lines(24, 278, [
        "Before the call the caller filled s_pages with -infinity (self_attention.hpp:1906) and passed",
        "s_stride = page::page_size = 64 (1970). After the three stores (blocks 0, 1, 2) the 41 live entries hold",
        "q_h . K_t (UNSCALED); entries 41..63 still hold -infinity: \"the other entries of s are left untouched\"",
        "(lines 25-26). The caller then scales, takes the page max and exponentiates (amx_attn_iface.hpp:63-64).",
        "Token 37 (thin frame): s[h * s_stride + 37] = q_h . K_37 for h = 0..3, written by this store (lane 5).",
    ], 9, 12))
    boxes.append(("s_pages[offset] = constant<page::page_size>(-1.0f / 0.0f) (the caller's -infinity fill); page::page_size as s_stride", "self_attention.hpp:1906, 1970"))
    o.append(lines(16, 372, [
        "The test asserts both halves: a dead token's slot still equals PRESET_NEG_INF, a live one is within the",
        "envelope of the dotter [t_k_vnni_layout.cpp:270-295]. Lines 95-99 close the loop, the branch, the function",
        "and the namespace.",
    ], 9, 12))
    legend = [
        ("q", "violet: an accumulator lane and the s entry it is stored to"),
        ("empty", "grey dashed: a lane with a clear mask bit (not stored) and an s entry left untouched"),
        ("hi", "pale yellow: what the caller sees after the call"),
        ("ink frame: the 16 entries of block 2 that this store addresses; the thin frame: the column of token 37", "none", C["ink"], False, False),
        ("violet arrow: one masked store, acc[h] -> s", "arrow", C["q"]),
        ("thin grey lines: the 4 token blocks of s", "line", C["muted"]),
    ] + FONTS
    return figure(fid, W, H, "The masked store: each accumulator's live lanes into s", "".join(o),
                  "Updates B1: after block 2, each of the 4 accumulators is stored to s + h * s_stride + 32 "
                  "under mask 0x01ff: tokens 32..40 receive q_h . K_t, tokens 41..47 are not written. "
                  "Blocks 0 and 1 were stored before, block 3 never; so entries 41..63 keep the -infinity "
                  "the caller put there.", boxes, legend=legend)
