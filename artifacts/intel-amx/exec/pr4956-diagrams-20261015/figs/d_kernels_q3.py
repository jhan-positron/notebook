"""Change diagrams of unit q3 of the PR 4956 page for h/tron/kernels/k_vnni.hpp:
the masked block loop (head lines 53-91).

Two figures: kernels-d3a (the masked load of one pair row on the worked
example) and kernels-d3b (the two product branches, bf16 and float).

Line numbers are head line numbers of h/tron/kernels/k_vnni.hpp
("kernels/k_vnni.hpp:NN") unless another file is named.
"""
from svg_helpers import C, arrow, cite, figure, line, lines, marker_defs, rect, text
from base_kernels import EX, FONTS, MASKS, acc_regs, mask_hex, pair_row_lanes, step_badge

BASE = ("Updates B3: steps 2-4 of the loop nest are drawn at the lane level for the worked example "
        "(block c = 2, mask 0x01ff, pair row dp = 3 of step 2, token 37 in lane 5): the masked "
        "64-byte load, what a clear lane holds, and the two product branches that add into "
        "acc[h]: one VDPBF16PS for a bf16 query, two FMAs on the widened halves for a float query.")

W = 700


def fig_a():
    fid = "kernels-d3a"
    H = 400
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "vnni": C["vnni"], "live": C["rows"]})]
    o.append(text(16, 18, "One masked load (lines 57-70) on the worked example: block c = 2, step 2, "
                  "pair row dp = 3", 11, weight=700))
    # mask
    o.append(step_badge(24, 44, 1))
    o.append(text(40, 48, f"mask = __mmask16(live >> (c * BLOCK_TOKENS_16)) = {mask_hex(2)} for c = 2 "
                  "(58); mask == 0 would skip the block (59)", 9.5))
    bits = "".join("1" if (MASKS[2] >> t) & 1 else "0" for t in range(16))
    bx = 60
    for t, b in enumerate(bits):
        on = b == "1"
        o.append(rect(bx + t * 20, 56, 18, 12, C["rows_fill"] if on else "#fff",
                      C["rows"] if on else C["empty"], 0.8, 1))
        o.append(text(bx + t * 20 + 9, 65, b, 8.5, "middle", True))
        o.append(text(bx + t * 20 + 9, 80, str(32 + t), 8, "middle", True, fill=C["muted"]))
    o.append(text(bx + 330, 65, "bit t = token 32 + t of the page", 9, fill=C["muted"]))
    boxes.append(("mask = __mmask16(live >> (c * BLOCK_TOKENS_16))", "kernels/k_vnni.hpp:58-59"))
    # panel address
    o.append(step_badge(24, 108, 2))
    o.append(text(40, 112, "panel = plane + (step * TOKEN_BLOCKS_4 + c) * PANEL_ELEMS_512 = plane + "
                  "(2 * 4 + 2) * 512 (65): panel #10", 9.5))
    o.append(text(40, 126, "plane = detail::k_vnni_access::plane(k_page) (56): the one route from the view "
                  "to the plane address", 9, fill=C["muted"]))
    boxes.append(("panel = plane + (step * TOKEN_BLOCKS_4 + c) * PANEL_ELEMS_512", "kernels/k_vnni.hpp:56, 65"))
    # the pair row in memory and the load
    o.append(step_badge(24, 156, 3))
    o.append(text(40, 160, "k_pairs = _mm512_maskz_loadu_epi32(mask, panel + dp * ROW_ELEMS_32) (68-69): "
                  "pair row dp = 3", 9.5))
    o.append(text(60, 184, "in memory: panel #10, pair row 3 (bytes 192..255 of the panel), 16 dwords", 9,
                  fill=C["muted"]))
    o.append(pair_row_lanes(60, 190, 480, 22, mask=0xffff, hi_t=EX["t"], base_token=32))
    o.append(text(548, 205, "memory: all 16", 8.5, fill=C["muted"]))
    o.append(text(548, 215, "dwords exist", 8.5, fill=C["muted"]))
    for t in range(16):
        x = 60 + t * 30 + 15
        if (MASKS[2] >> t) & 1:
            o.append(arrow(fid, "vnni", [(x, 226), (x, 250)], C["vnni"]))
        else:
            o.append(line(x, 226, x, 250, C["empty"], 1, "3 2"))
    o.append(text(60, 262, "k_pairs (a __m512i register): lane t = dword t when mask bit t is set, else 0; "
                  "a clear lane's memory is never read", 9, fill=C["muted"]))
    o.append(pair_row_lanes(60, 268, 480, 22, mask=MASKS[2], hi_t=EX["t"], base_token=32))
    o.append(text(548, 283, "register: lanes", 8.5, fill=C["muted"]))
    o.append(text(548, 293, "9..15 hold 0", 8.5, fill=C["muted"]))
    o.append(cite(684, 304, "kernels/k_vnni.hpp:66-70"))
    boxes.append(("k_pairs = _mm512_maskz_loadu_epi32(mask, panel + dp * ROW_ELEMS_32)", "kernels/k_vnni.hpp:66-70"))
    boxes.append(("pair row dp = 3 of panel #10 (the worked example)", "kernels/k_vnni.hpp:67; k_vnni.hpp:23-28"))
    # token 37
    o.append(rect(60, 318, 624, 44, C["hi_fill"], C["ink"], 1, 4))
    o.append(lines(68, 333, [
        "Token 37 = lane t = 5 (solid blue): its dword holds K[37][70] (low bf16) and K[37][71] (high bf16);",
        "d = step * STEP_DIMS_32 + PAIR_2 * dp = 2 * 32 + 2 * 3 = 70 (line 70) names the same two dimensions in q.",
    ], 9, 12))
    boxes.append(("d = step * STEP_DIMS_32 + PAIR_2 * dp (= 70 for the worked example)", "kernels/k_vnni.hpp:70"))
    o.append(text(16, 386, "The loop runs this load for every (step, dp): 4 x 16 = 64 loads per visited "
                  "block, each 64 bytes (lines 64-69).", 9, fill=C["muted"]))
    legend = [
        ("vnni", "blue: a dword (one token's dimension pair) in memory or in a loaded lane"),
        ("vnni_solid", "solid blue: the dword of token 37 (dimensions 70, 71)"),
        ("live", "green square: a set mask bit"),
        ("bit_clear", "white square: a clear mask bit"),
        ("empty", "grey dashed: a lane whose mask bit is clear: not read, holds 0"),
        ("hi", "pale yellow: the worked example's token"),
        ("blue arrow: the dword a set lane loads", "arrow", C["vnni"]),
        ("grey dashed line: no load for a clear lane", "line", C["empty"], True),
        ("dotted grey line inside a lane: the boundary of its two bf16", "line", C["line"], True),
    ] + FONTS
    return figure(fid, W, H, "One masked load of a pair row on the worked example", "".join(o),
                  "Updates B3 (steps 2-3): for block c = 2 the mask is 0x01ff. The load of pair row 3 "
                  "of panel #10 fills lanes 0..8 with the dwords of tokens 32..40 and sets lanes 9..15 "
                  "to 0 without reading their memory. Token 37 is lane 5; its dword holds dimensions 70 "
                  "and 71, the pair that d = 70 names in q.", boxes, legend=legend)


def fig_b():
    fid = "kernels-d3b"
    H = 430
    boxes = []
    o = [marker_defs(fid, {"ink": C["ink"], "q": C["q"], "vnni": C["vnni"]})]
    o.append(text(16, 18, "The two product branches (lines 71-88), per pair row and head h", 11, weight=700))
    # inputs
    o.append(rect(16, 32, 300, 44, C["vnni_fill"], C["vnni"], 1.2, 4))
    o.append(text(24, 48, "k_pairs: 16 lanes x (K[t][d], K[t][d + 1]) as bf16", 10, mono=True, weight=600))
    o.append(text(24, 62, "the loaded pair row (d3a); clear lanes hold 0", 9, fill=C["muted"]))
    boxes.append(("k_pairs (the loaded pair row)", "kernels/k_vnni.hpp:68-69"))
    o.append(rect(384, 32, 300, 44, C["q_fill"], C["q"], 1.2, 4))
    o.append(text(392, 48, "q[h * HEAD_SIZE_128 + d], q[... + d + 1]", 10, mono=True, weight=600))
    o.append(text(392, 62, "the two query values of head h at dimensions d, d + 1", 9, fill=C["muted"]))
    boxes.append(("q[h * HEAD_SIZE_128 + d], q[h * HEAD_SIZE_128 + d + 1]", "kernels/k_vnni.hpp:74, 85, 87"))
    # bf16 branch (left)
    bx, by = 16, 96
    o.append(rect(bx, by, 326, 220, "#fff", C["ink"], 1.2, 5))
    o.append(text(bx + 8, by + 16, "if constexpr (q_scalar == bf16) (71-77)", 10.5, mono=True, weight=600))
    o.append(rect(bx + 8, by + 26, 310, 40, C["q_fill"], C["q"], 1, 3))
    o.append(lines(bx + 14, by + 40, ["uint32_t q_pair; memcpy(&q_pair, q + h * 128 + d, 4) (73-74):",
                                      "the two bf16 of head h at d, d + 1 as one dword"], 8.5, 11))
    o.append(arrow(fid, "q", [(bx + 296, by + 66), (bx + 296, by + 84)], C["q"]))
    o.append(text(bx + 14, by + 80, "set1_epi32(int(q_pair)) broadcasts the dword to all 16 lanes (76)", 8.5,
                  fill=C["muted"]))
    o.append(rect(bx + 8, by + 86, 310, 60, C["q_fill"], C["q"], 1, 3))
    o.append(lines(bx + 14, by + 100, ["acc[h] = _mm512_dpbf16_ps(acc[h], (__m512bh) q_pair x16,",
                                       "                          (__m512bh) k_pairs)   (75-76)",
                                       "per lane t: acc[h][t] += q[d] * K[t][d] + q[d + 1] * K[t][d + 1]",
                                       "(VDPBF16PS: both products and the add in one instruction)"],
                   8.5, 11))
    o.append(acc_regs(bx + 60, by + 156, 240, n=1, h=10, gap=2, mask=MASKS[2]))
    o.append(text(bx + 8, by + 182, "acc[h] after this pair row: lanes 0..8 advanced, 9..15 unchanged (0 + 0)",
                  8.5, fill=C["muted"]))
    o.append(text(bx + 8, by + 196, "1 instruction per (pair row, head): 64 per head per block", 8.5,
                  fill=C["muted"]))
    o.append(cite(bx + 322, by + 216, "kernels/k_vnni.hpp:71-77"))
    boxes.append(("acc[h] = _mm512_dpbf16_ps(acc[h], (__m512bh)_mm512_set1_epi32(int(q_pair)), (__m512bh)k_pairs)",
                  "kernels/k_vnni.hpp:71-77"))
    boxes.append(("q_pair (memcpy of the two bf16 of head h at d, d + 1)", "kernels/k_vnni.hpp:73-74"))
    # float branch (right)
    fx, fy = 358, 96
    o.append(rect(fx, fy, 326, 220, "#fff", C["ink"], 1.2, 5))
    o.append(text(fx + 8, fy + 16, "else: q_scalar == float (78-88)", 10.5, mono=True, weight=600))
    o.append(rect(fx + 8, fy + 26, 310, 50, C["vnni_fill"], C["vnni"], 1, 3))
    o.append(lines(fx + 14, fy + 40, ["k_even = slli_epi32(k_pairs, BF16_BITS_16) as fp32 (79-80):",
                                      "the low bf16 of each lane shifted up 16 bits = its exact fp32;",
                                      "k_odd = and(k_pairs, HIGH_HALF_0XFFFF0000) (81-82): the high bf16"],
                   8.5, 11))
    o.append(arrow(fid, "vnni", [(fx + 160, fy + 76), (fx + 160, fy + 94)], C["vnni"]))
    o.append(rect(fx + 8, fy + 96, 310, 60, C["q_fill"], C["q"], 1, 3))
    o.append(lines(fx + 14, fy + 110, ["acc[h] = fmadd_ps(set1_ps(q[h*128 + d]),     k_even, acc[h])",
                                       "acc[h] = fmadd_ps(set1_ps(q[h*128 + d + 1]), k_odd,  acc[h])",
                                       "(84-87): two fused multiply-adds per lane, even dimension first",
                                       "then the odd one; the products are the same as the dotter's FMAs"],
                   8.5, 11))
    o.append(acc_regs(fx + 60, fy + 166, 240, n=1, h=10, gap=2, mask=MASKS[2]))
    o.append(text(fx + 8, fy + 192, "2 instructions per (pair row, head): 128 FMAs per head per block", 8.5,
                  fill=C["muted"]))
    o.append(text(fx + 8, fy + 206, "a clear lane: k_even = k_odd = 0, so acc stays 0 there", 8.5,
                  fill=C["muted"]))
    o.append(cite(fx + 322, fy + 216, "kernels/k_vnni.hpp:78-88"))
    boxes.append(("k_even = _mm512_castsi512_ps(_mm512_slli_epi32(k_pairs, BF16_BITS_16))", "kernels/k_vnni.hpp:79-80; k_vnni.hpp:74-75"))
    boxes.append(("k_odd = _mm512_castsi512_ps(_mm512_and_si512(k_pairs, _mm512_set1_epi32(int(HIGH_HALF_0XFFFF0000))))", "kernels/k_vnni.hpp:81-82; k_vnni.hpp:76-77"))
    boxes.append(("acc[h] = _mm512_fmadd_ps(...)", "kernels/k_vnni.hpp:83-88"))
    o.append(arrow(fid, "vnni", [(166, 76), (166, 96)], C["vnni"]))
    o.append(arrow(fid, "vnni", [(300, 76), (300, 88), (fx + 160, 88), (fx + 160, 96)], C["vnni"]))
    o.append(arrow(fid, "q", [(534, 76), (534, 96)], C["q"]))
    o.append(arrow(fid, "q", [(384, 54), (342, 54), (342, 110), (326, 110)], C["q"]))
    o.append(lines(16, 336, [
        "Both branches keep one token per lane and add into acc[h] without any cross-lane operation. The",
        "static_assert at lines 54-55 admits bf16 and float here; fp16 arrives widened to float (Q2).",
        "The loop order is step (4) x dp (16) x h (kv_mul), so the adds of one lane happen in dimension",
        "order for every head: the add order the numerics model (B4) compares with the row-major dotter.",
        "The two widening constants are defined in the layout header [k_vnni.hpp:74-77].",
    ], 9, 12))
    legend = [
        ("vnni", "blue: the loaded K pair row and its widened halves k_even / k_odd"),
        ("q", "violet: the query values, the product instructions and the accumulator they feed"),
        ("empty", "grey dashed lane: a clear mask bit (acc unchanged there)"),
        ("box", "white box, ink outline: one if-constexpr branch"),
        ("blue arrow: the K lanes into a product", "arrow", C["vnni"]),
        ("violet arrow: the query values into a product", "arrow", C["q"]),
    ] + FONTS
    return figure(fid, W, H, "The bf16 and float product branches of the block loop", "".join(o),
                  "Updates B3 (step 4): for a bf16 query the two query values of head h at d and d + 1 "
                  "are one dword, broadcast to 16 lanes, and one VDPBF16PS adds both products of every "
                  "lane into acc[h]. For a float query the loaded dwords are widened into k_even and "
                  "k_odd and two FMAs add the products. Clear lanes hold 0 and stay 0.",
                  boxes, legend=legend)


def figs():
    return [fig_a(), fig_b()]
