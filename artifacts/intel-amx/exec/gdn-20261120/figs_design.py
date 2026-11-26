#!/usr/bin/env python3
"""Design figures of gdn-amx-design.html: the wall-clock lanes of one GDN layer, the block kernel's matrix
products, and the call path. Durations in the lanes figure are measured values passed in by the caller."""
from figs_static import TINT, box
from pagelib import C, arrow_defs, esc, fmt, line, rect, svg_open, text


def lanes(gdn_ms, rest_ms, steps, step_us, s_mid, clock_ms=0.0, n_threads=16, n_idle=40, title_cell="1 user, prompt 1,024"):
    """Wall-clock lanes of ONE GDN layer inside a prefill pass.
    gdn_ms: wall of one GDN operation; rest_ms: FPGA matmuls and small host kernels of the layer (position schematic);
    steps: tokens in the chain; step_us: wall of one GDN step on the slowest thread; s_mid: predicted factor of the block kernel (est.);
    clock_ms: time that the lower core clock adds to the other work of the layer (est.)."""
    W = 960
    left, right = 190, 30
    pw = W - left - right
    total = rest_ms + gdn_ms
    X = lambda ms: left + pw * ms / total
    lane_h, gap = 22, 8
    H = 0
    out = []

    def panel(y0, heading, gdn_wall, blocks, crit_label, predicted, extra=None):
        o = [text(14, y0 + 14, heading, size=13.5, weight=600)]
        y = y0 + 30
        names = ["FPGA cards", "main thread", "main helper 1", "main helper 2", f"... helpers 3 to {n_threads - 1}", f"{n_idle} attention workers"]
        for i, name in enumerate(names):
            yy = y + i * (lane_h + gap)
            o.append(text(left - 10, yy + lane_h * 0.68, name, size=12, anchor="end", fill=C["ink"] if i != 4 else C["muted"]))
            o.append(line(left, yy + lane_h + gap / 2, left + pw, yy + lane_h + gap / 2, stroke=C["grid"]))
            if i == 0:
                o.append(rect(X(0), yy, X(rest_ms) - X(0), lane_h, C["other"], rx=2, title=f"FPGA matrix multiplies and small host kernels, mean per layer: {rest_ms:.2f} ms"))
                o.append(text(X(0) + 6, yy + lane_h * 0.68, f"FPGA + small host kernels: {rest_ms:.2f} ms", size=11, fill="#ffffff", weight=600))
                o.append(rect(X(rest_ms), yy, X(rest_ms + gdn_wall) - X(rest_ms), lane_h, C["surface"], stroke=C["other"], dash="4 3", rx=2))
                if X(rest_ms + gdn_wall) - X(rest_ms) > 170:
                    o.append(text(X(rest_ms) + 6, yy + lane_h * 0.68, "waits for the GDN output", size=11, fill=C["muted"]))
            elif i in (1, 2, 3):
                o.append(rect(X(0), yy, X(rest_ms) - X(0), lane_h, C["surface"], stroke=C["other"], dash="4 3", rx=2))
                if i == 1:
                    o.append(text(X(0) + 6, yy + lane_h * 0.68, "waits for the 4 input projections", size=11, fill=C["muted"]))
                col = C["crit"] if i == 1 else C["gdn"]
                x0 = X(rest_ms)
                bw = (X(rest_ms + gdn_wall) - x0) / blocks
                for b in range(blocks):
                    o.append(rect(x0 + b * bw + 0.4, yy, max(bw - 0.8, 0.6), lane_h, col, rx=1 if blocks > 16 else 2))
            elif i == 4:
                o.append(text(X(rest_ms) + 6, yy + lane_h * 0.68, "the same work, one key head each", size=11, fill=C["muted"]))
            else:
                o.append(rect(X(0), yy, X(rest_ms + gdn_wall) - X(0), lane_h, C["surface"], stroke=C["attn"], dash="4 3", rx=2))
                o.append(text(X(0) + 6, yy + lane_h * 0.68, "idle: this layer has no attention", size=11, fill=C["muted"]))
        yb = y + len(names) * (lane_h + gap) + 4
        # critical path bracket
        x0, x1 = X(rest_ms), X(rest_ms + gdn_wall)
        o.append(line(x0, yb, x1, yb, stroke=C["crit"], sw=2))
        o.append(line(x0, yb - 5, x0, yb + 5, stroke=C["crit"], sw=2))
        o.append(line(x1, yb - 5, x1, yb + 5, stroke=C["crit"], sw=2))
        o.append(text(x0, yb + 17, crit_label, size=12, weight=600, fill=C["crit"]))
        if predicted:
            o.append(rect(x1, y + lane_h + gap, X(rest_ms + gdn_ms) - x1, 3 * (lane_h + gap) - gap, "#eaf7f1", stroke=C["amx"], dash="3 3", rx=2))
            o.append(text((x1 + X(rest_ms + gdn_ms)) / 2, y + 2.6 * (lane_h + gap), f"time saved: {gdn_ms - gdn_wall:.2f} ms (est.)", size=12, weight=600,
                          fill="#0e7d55", anchor="middle"))
        if extra:
            o.append(text(extra[0] if extra[0] is not None else x0, yb + 34, extra[1], size=12, fill=C["ink2"]))
            return "".join(o), yb + 48
        return "".join(o), yb + 30

    p1, y1 = panel(6, f"Today (measured, {title_cell}): one GDN layer of a prefill pass", gdn_ms, steps,
                   f"serial path: {steps} GDN steps, one after another = {gdn_ms:.2f} ms", False,
                   extra=(None, f"{step_us:.1f} us per GDN step on the slowest thread"))
    new_wall = gdn_ms / s_mid
    saved = gdn_ms - new_wall
    p2, y2 = panel(y1 + 8, "With Part A (predicted, est.): the same layer", new_wall, max(1, steps // 32),
                   f"{max(1, steps // 32)} blocks of 32 tokens = {new_wall:.2f} ms (est., factor {s_mid:g})", True,
                   extra=(left, f"The lower core clock adds {clock_ms:.2f} ms to the other work of the layer (est.). Net time saved: {saved - clock_ms:.2f} ms (est.)."))
    # axis
    H = y2 + 30
    axis_y = y2 + 2
    out.append(svg_open(W, H, "Wall-clock lanes of one GDN layer in a prefill pass, today and with the block kernel"))
    out.append(p1)
    out.append(p2)
    out.append(line(left, axis_y, left + pw, axis_y, stroke=C["ink2"]))
    step = 0.25 if total < 2.5 else (1.0 if total < 10 else 5.0)
    t = 0.0
    while t <= total + 1e-9:
        out.append(line(X(t), axis_y, X(t), axis_y + 5, stroke=C["ink2"]))
        out.append(text(X(t), axis_y + 18, f"{t:g}", size=11, fill=C["muted"], anchor="middle"))
        t += step
    out.append(text(left + pw, axis_y + 18, "ms", size=11, fill=C["muted"], anchor="end") if False else "")
    out.append(text(left - 10, axis_y + 18, "wall clock (ms)", size=11, fill=C["muted"], anchor="end"))
    out.append("</svg>")
    return "".join(out)


def matrix(x, y, w, h, fill, stroke, label, sub=None, planes=1, dash=None):
    o = []
    for p in range(planes - 1, -1, -1):
        o.append(rect(x + 5 * p, y - 5 * p, w, h, fill, stroke=stroke, rx=2, sw=1.3, dash=dash))
    o.append(text(x + w / 2, y + h / 2 + 2, label, size=12.5, weight=600, anchor="middle"))
    if sub:
        o.append(text(x + w / 2, y + h / 2 + 17, sub, size=10.5, anchor="middle", fill=C["ink2"]))
    return "".join(o)


def block_kernel(B=32, counts=None):
    """The matrix products of the GDN block kernel for one value head and one block of B tokens."""
    counts = counts or {}
    W, H = 960, 594
    IN, ST, RES = "#e9edf2", "#c9def8", "#fdf3d7"
    out = [svg_open(W, H, "The matrix products of the GDN block kernel for one value head and one block of tokens"), arrow_defs("ab1")]
    out.append(text(14, 20, f"One value head, one block of {B} prompt tokens. K, Q, V rows are the tokens. S is the 128 x 128 state.", size=13, weight=600))
    # legend
    lx, ly = 14, 34
    for fill, stroke, name in ((IN, C["other"], "bf16 inputs (K, Q, V)"), (ST, C["gdn"], "FP32 state, split into 3 bf16 planes for the tile product"),
                               (RES, "#c9a227", "FP32 results"), (C["surface"], C["amx"], "AMX tile product (TDPBF16PS)")):
        out.append(rect(lx, ly, 13, 13, fill, stroke=stroke, rx=2, sw=1.6 if stroke == C["amx"] else 1, dash="3 2" if stroke == C["amx"] else None))
        out.append(text(lx + 19, ly + 11, name, size=11.5, fill=C["ink2"]))
        lx += 19 + 6.4 * len(name) + 24
    # ---- row 1: products that READ the state ----
    y = 104
    out.append(text(14, y - 24, "Stage 1. Read the state", size=12.5, weight=600, fill=C["gdn"]))
    out.append(matrix(40, y, 64, 128, IN, C["other"], "K and Q", f"{2 * B} x 128"))
    out.append(text(124, y + 68, "x", size=18, weight=600))
    out.append(matrix(150, y, 128, 128, ST, C["gdn"], "S0", "128 x 128", planes=3))
    out.append(text(302, y + 68, "=", size=18, weight=600))
    out.append(matrix(330, y, 128, 128 * 0.5, RES, "#c9a227", "K S0 and Q S0", f"{2 * B} x 128"))
    out.append(rect(30, y - 16, 440, 160, "none", stroke=C["amx"], rx=6, sw=1.8, dash="6 4"))
    out.append(text(250, y + 160, counts.get("p1", "tile product 1"), size=11.5, fill="#0e7d55", weight=600, anchor="middle"))
    # ---- row 1 right: Gram ----
    gx = 520
    out.append(text(gx, y - 24, "Stage 2. Token against token (no state)", size=12.5, weight=600, fill=C["ink"]))
    out.append(matrix(gx + 10, y, 64, 128, IN, C["other"], "K and Q", f"{2 * B} x 128"))
    out.append(text(gx + 94, y + 68, "x", size=18, weight=600))
    out.append(matrix(gx + 120, y + 32, 128, 64, IN, C["other"], "K^T", f"128 x {B}"))
    out.append(text(gx + 268, y + 68, "=", size=18, weight=600))
    out.append(matrix(gx + 296, y + 20, 80, 88, RES, "#c9a227", "G and H", f"{2 * B} x {B}"))
    out.append(rect(gx, y - 16, 396, 160, "none", stroke=C["amx"], rx=6, sw=1.8, dash="6 4"))
    out.append(text(gx + 198, y + 160, counts.get("p2", "tile product 2"), size=11.5, fill="#0e7d55", weight=600, anchor="middle"))
    # ---- row 2: forward substitution ----
    y2 = 316
    out.append(text(14, y2 - 14, "Stage 3. Corrections, token by token (AVX-512)", size=12.5, weight=600))
    out.append(rect(30, y2, 420, 122, "#f3f5f8", stroke=C["line"], rx=6))
    out.append(text(44, y2 + 20, "for t = 1 .. B:", size=12, mono=True))
    # The sum of r_t and of o_t goes on a second line, so that every formula line ends inside the box.
    # x = 103.2 puts the second line under the first term: 6 characters of 7.2 px (0.6 em at 12 px) after x = 60.
    out.append(text(60, y2 + 38, "r_t = g_t (K S0)_t", size=12, mono=True))
    out.append(text(103.2, y2 + 56, "+ sum over u<t of w_tu G_tu delta_u", size=12, mono=True))
    out.append(text(60, y2 + 74, "delta_t = beta_t (v_t - r_t)", size=12, mono=True))
    out.append(text(60, y2 + 92, "o_t = scale (g_t (Q S0)_t", size=12, mono=True))
    out.append(text(103.2, y2 + 110, "+ sum over u<=t of w_tu H_tu delta_u)", size=12, mono=True))
    out.append(text(44, y2 + 140, "g_t = product of the decays up to token t.", size=11.5, fill=C["ink2"]))
    out.append(text(44, y2 + 156, "w_tu = product of the decays after token u, up to token t.", size=11.5, fill=C["ink2"]))
    out.append(text(44, y2 + 172, "G = K K^T. H = Q K^T. S0 = the state at the start of the block.", size=11.5, fill=C["ink2"]))
    out.append(text(44, y2 + 188, "K and Q = the 32 key rows above the 32 query rows.", size=11.5, fill=C["ink2"]))
    out.append(text(44, y2 + 204, "Delta = the rows delta_t. S_B = the state after the block.", size=11.5, fill=C["ink2"]))
    out.append(text(44, y2 + 220, "scale = 1 / sqrt(128), in the FP32 coefficients.", size=11.5, fill=C["ink2"]))
    out.append(text(44, y2 + 242, counts.get("sub", ""), size=11.5, fill=C["ink2"], weight=600))
    # ---- row 2 right: state update ----
    ux = 520
    out.append(text(ux, y2 - 14, "Stage 4. Write the state once", size=12.5, weight=600, fill=C["gdn"]))
    out.append(matrix(ux + 10, y2 + 4, 56, 100, IN, C["other"], "K^T", f"128 x {B}"))
    out.append(text(ux + 84, y2 + 58, "x", size=18, weight=600))
    out.append(matrix(ux + 106, y2 + 32, 96, 48, RES, "#c9a227", "w . Delta", f"{B} x 128", planes=3))
    out.append(text(ux + 226, y2 + 58, "+ g_B S0 =", size=12.5, weight=600))
    out.append(matrix(ux + 306, y2 + 4, 80, 100, ST, C["gdn"], "S_B", "128 x 128"))
    out.append(rect(ux, y2 - 4, 396, 122, "none", stroke=C["amx"], rx=6, sw=1.8, dash="6 4"))
    out.append(text(ux + 198, y2 + 136, counts.get("p3", "tile product 3"), size=11.5, fill="#0e7d55", weight=600, anchor="middle"))
    out.append(text(14, H - 12, f"Today each token reads S twice and writes it once. The block form reads S twice and writes it once per block of {B} tokens.", size=12.5, weight=600))
    out.append("</svg>")
    return "".join(out)


def call_path():
    """Where the new code sits in tron's call path."""
    W, H = 960, 400
    out = [svg_open(W, H, "Call path of a GDN layer and of a full-attention layer, with the new AMX code"), arrow_defs("ac1")]
    A = lambda x1, y1, x2, y2, lab=None, dx=6, dy=-5: (line(x1, y1, x2, y2, stroke=C["ink2"], sw=1.4, marker="ac1")
                                                       + (text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, lab, size=11, fill=C["ink2"]) if lab else ""))
    out.append(text(14, 20, "GDN layer (24 of 32 layers)", size=13.5, weight=600, fill=C["gdn"]))
    out.append(box(14, 32, 190, 66, "Generated plugin", ["qwen_3p5_4b.hpp", "one call per GDN layer"], "fpga"))
    out.append(box(246, 32, 210, 66, "run_gdn_operation", ["gdn_execution.hpp", "one work item = (chain, key head)"], "gdn"))
    out.append(A(206, 65, 243, 65))
    out.append(text(480, 40, "chain of 1 token (decode)", size=11.5, fill=C["ink2"]))
    out.append(text(470, 134, "chain of 2 or more tokens (prefill)", size=11.5, fill=C["ink2"]))
    out.append(box(690, 20, 256, 58, "step()   unchanged", ["today's kernel, on the stored state"], "gdn"))
    out.append(A(458, 58, 687, 50))
    out.append(box(690, 92, 256, 74, "advance()   new, Part 0", ["phase 1, per token: convolve, normalize", "phase 2: recurrence over the chain", "phase 3, per token: norm, output gate"], "gdn"))
    out.append(A(458, 74, 687, 124))
    out.append(box(690, 182, 256, 58, "amx_gdn.cpp   new, Part A", ["phase 2 as an AMX block kernel:", "tile products 1, 2, 3 per 32 tokens"], "amx"))
    out.append(A(818, 168, 818, 180))
    out.append(text(246, 196, "No AMX, or the kill switch or the GDN switch is set:", size=11.5, fill=C["ink2"]))
    out.append(text(246, 212, "phase 2 runs the column-half kernel of Part 0", size=11.5, fill=C["ink2"]))
    out.append(text(246, 228, "(AVX-512, same bits as today).", size=11.5, fill=C["ink2"]))
    out.append(line(14, 262, W - 14, 262, stroke=C["line"]))
    out.append(text(14, 286, "Full-attention layer (8 of 32 layers)", size=13.5, weight=600, fill=C["attn"]))
    out.append(box(14, 298, 190, 66, "Generated plugin", ["attention_geometry", "{16, {4, 256}}"], "fpga"))
    out.append(box(246, 298, 210, 66, "apply_page_range", ["self_attention.hpp", "check: AMX shape? full page?"], "attn"))
    out.append(A(206, 331, 243, 331))
    out.append(box(690, 284, 256, 46, "AVX-512 path   unchanged", ["dotter<bf16,256>, scaled_v"], "attn"))
    out.append(box(690, 338, 256, 56, "amx_attn kernels for 256 x 4   new", ["QK 32 + PV 32 tile products per", "query token, page and KV head"], "amx"))
    out.append(A(458, 320, 687, 306, "page of this pass, or no AMX", dx=-88, dy=-10))
    out.append(A(458, 342, 687, 364, "full page of an earlier pass", dx=-84, dy=19))
    out.append("</svg>")
    return "".join(out)


if __name__ == "__main__":
    import sys
    import cairosvg
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    figs = {"lanes": lanes(0.847, 0.675, 128, 6.6, 3.2, 0.02), "block_kernel": block_kernel(), "call_path": call_path()}
    for name, svg in figs.items():
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{d}/{name}.png", output_width=1440)
        print("wrote", f"{d}/{name}.png")
