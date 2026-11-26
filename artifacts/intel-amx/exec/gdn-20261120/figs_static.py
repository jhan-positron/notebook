#!/usr/bin/env python3
"""Static diagrams of gdn-amx-design.html: they depend on the model geometry only, not on measurements."""
from pagelib import C, arrow_defs, esc, line, rect, svg_open, text

TINT = {"gdn": "#e3eefb", "attn": "#fde9df", "fpga": "#eef0f3", "amx": "#def5ec"}


def box(x, y, w, h, title, lines, kind, where=None):
    """A labeled box. kind picks the tint: gdn, attn, fpga, amx. where = small tag in the top-right corner."""
    stroke = {"gdn": C["gdn"], "attn": C["attn"], "fpga": C["other"], "amx": C["amx"]}[kind]
    out = [rect(x, y, w, h, TINT[kind], stroke=stroke, rx=5, sw=1.4)]
    out.append(text(x + 9, y + 18, title, size=12.5, weight=600))
    if where:
        out.append(text(x + w - 8, y + 18, where, size=10.5, anchor="end", fill=C["muted"], weight=600))
    yy = y + 35
    for ln in lines:
        out.append(text(x + 9, yy, ln, size=11.5, fill=C["ink2"]))
        yy += 15
    return "".join(out)


def layer_stack():
    """Figure: the 32 layers of llama-3.1-8b and of Qwen3.5 4B, one square per layer."""
    W, H = 960, 236
    left, sq, gap = 190, 20, 3.2
    out = [svg_open(W, H, "Layer types of llama-3.1-8b and Qwen3.5 4B, one square per layer")]
    out.append(text(left, 20, "layer 1", size=11, fill=C["muted"]))
    out.append(text(left + 32 * (sq + gap) - gap, 20, "layer 32", size=11, fill=C["muted"], anchor="end"))
    rows = [("llama-3.1-8b", 34, lambda i: "attn", "32 layers. Every layer is a full-attention layer."),
            ("Qwen3.5 4B", 116, lambda i: "attn" if i % 4 == 3 else "gdn",
             "24 GDN layers and 8 full-attention layers. The pattern is GDN, GDN, GDN, attention, 8 times.")]
    for name, y, kind, cap in rows:
        out.append(text(left - 14, y + 15, name, size=13.5, weight=600, anchor="end"))
        for i in range(32):
            k = kind(i)
            out.append(rect(left + i * (sq + gap), y, sq, sq, C[k], rx=3,
                            title=f"{name} layer {i + 1}: {'full attention' if k == 'attn' else 'GDN (GatedDeltaNet)'}"))
        out.append(text(left, y + sq + 18, cap, size=12, fill=C["ink2"]))
    y = 200
    out.append(rect(left, y, 13, 13, C["attn"], rx=2))
    out.append(text(left + 19, y + 11, "full attention: reads every earlier token, so the work grows with the context", size=12, fill=C["ink2"]))
    out.append(rect(left, y + 19, 13, 13, C["gdn"], rx=2))
    out.append(text(left + 19, y + 30, "GDN: reads and rewrites a memory of fixed size, so the work per token is constant", size=12, fill=C["ink2"]))
    out.append("</svg>")
    return "".join(out)


def token_flow():
    """Figure: what one new token does in one attention layer and in one GDN layer."""
    W, H = 960, 560
    out = [svg_open(W, H, "Per-token data flow of an attention layer and of a GDN layer"), arrow_defs("af1"), arrow_defs("af2", C["gdn"])]
    # ---- panel A: attention layer ----
    out.append(text(14, 22, "A. One token in a full-attention layer (every llama-3.1-8b layer, and 8 of the 32 Qwen3.5 4B layers)", size=13.5, weight=600))
    y, h = 36, 84
    xs = [14, 204, 394, 584, 774]
    w = 172
    out.append(box(xs[0], y, w, h, "Project", ["Q, K, V from the", "token's hidden vector"], "fpga", "FPGA"))
    out.append(box(xs[1], y, w, h, "Append K, V", ["one more row in the", "KV cache (bf16)"], "attn", "CPU"))
    out.append(box(xs[2], y, w, h, "Score", ["dot product of Q with", "EVERY stored K"], "attn", "CPU"))
    out.append(box(xs[3], y, w, h, "Mix", ["softmax, then weighted", "sum of EVERY stored V"], "attn", "CPU"))
    out.append(box(xs[4], y, w, h, "Project out", ["back to the hidden", "vector width"], "fpga", "FPGA"))
    for i in range(4):
        out.append(line(xs[i] + w + 2, y + h / 2, xs[i + 1] - 3, y + h / 2, stroke=C["ink2"], sw=1.4, marker="af1"))
    # KV cache strip under the CPU boxes
    ky = y + h + 34
    out.append(text(xs[1], ky - 8, "KV cache of this layer: one 64-token page after another", size=12, fill=C["ink2"]))
    px = xs[1]
    for i in range(9):
        out.append(rect(px + i * 44, ky, 40, 26, "#f9c8b1", stroke=C["attn"], rx=2))
    out.append(rect(px + 9 * 44, ky, 40, 26, C["surface"], stroke=C["attn"], rx=2, dash="4 3"))
    out.append(rect(px + 10 * 44, ky, 40, 26, C["surface"], stroke=C["attn"], rx=2, dash="4 3"))
    out.append(text(px + 11 * 44 + 6, ky + 17, "... grows with the context", size=12, fill=C["attn"], weight=600))
    out.append(line(xs[2] + w / 2, y + h + 2, xs[2] + w / 2, ky - 22, stroke=C["attn"], sw=1.2, dash="3 3"))
    out.append(line(xs[3] + w / 2, y + h + 2, xs[3] + w / 2, ky - 22, stroke=C["attn"], sw=1.2, dash="3 3"))
    out.append(text(14, ky + 50, "Work per token: proportional to the context length. Memory: grows with the context.", size=12.5, weight=600))
    out.append(line(14, ky + 66, W - 14, ky + 66, stroke=C["line"]))
    # ---- panel B: GDN layer ----
    by = ky + 92
    out.append(text(14, by - 10, "B. One token in a GDN layer (24 of the 32 Qwen3.5 4B layers)", size=13.5, weight=600))
    w2 = 146
    xb = [14, 174, 334, 494, 654, 814]
    hb = 100
    out.append(box(xb[0], by, w2, hb, "Project", ["q, k, v: 8,192 values", "gate z: 4,096 values", "a, b: 32 values each"], "fpga", "FPGA"))
    out.append(box(xb[1], by, w2, hb, "Convolve", ["4 taps: this token and", "the last 3, then SiLU"], "gdn", "CPU"))
    out.append(box(xb[2], by, w2, hb, "Normalize", ["q and k of each of", "the 16 key heads,", "to unit length"], "gdn", "CPU"))
    out.append(box(xb[3], by, w2, hb, "Recurrence", ["recall, correct, write,", "read on the state S", "(lines 1 to 4 below)"], "gdn", "CPU"))
    out.append(box(xb[4], by, w2, hb, "Norm, gate", ["RMS norm per head,", "times SiLU(z)"], "gdn", "CPU"))
    out.append(box(xb[5], by, 132, hb, "Project out", ["4,096 values to", "the hidden width"], "fpga", "FPGA"))
    for i in range(5):
        out.append(line(xb[i] + w2 + 2, by + hb / 2, xb[i + 1] - 3, by + hb / 2, stroke=C["ink2"], sw=1.4, marker="af1"))
    # the state
    sy = by + hb + 30
    sx = xb[3] - 150
    out.append(rect(sx, sy, 120, 120, "#c9def8", stroke=C["gdn"], rx=3, sw=1.6))
    for i in range(1, 4):
        out.append(line(sx + 30 * i, sy, sx + 30 * i, sy + 120, stroke="#a9c8f0"))
        out.append(line(sx, sy + 30 * i, sx + 120, sy + 30 * i, stroke="#a9c8f0"))
    out.append(text(sx + 60, sy + 56, "state S", size=13, weight=600, anchor="middle"))
    out.append(text(sx + 60, sy + 73, "FP32", size=11.5, anchor="middle", fill=C["ink2"]))
    out.append(line(xb[3] + w2 / 2, by + hb + 2, sx + 122, sy + 40, stroke=C["gdn"], sw=1.4, marker="af2"))
    out.append(text(sx - 10, sy + 14, "one matrix per value head:", size=12, anchor="end", fill=C["ink2"]))
    out.append(text(sx - 10, sy + 30, "128 key rows x 128 value columns", size=12, anchor="end", fill=C["ink2"]))
    out.append(text(sx - 10, sy + 52, "32 value heads per layer", size=12, anchor="end", fill=C["ink2"]))
    out.append(text(sx - 10, sy + 68, "= 2 MiB per layer", size=12, anchor="end", weight=600))
    out.append(text(sx - 10, sy + 84, "= 48 MiB of state S per sequence (24 layers)", size=12, anchor="end", weight=600))
    out.append(text(sx - 10, sy + 106, "same size at every context length", size=12, anchor="end", fill=C["gdn"], weight=600))
    tx = sx + 190  # right of the arrow from the Recurrence box, so that the arrow crosses no text
    # three columns per line (number, step name, formula): SVG collapses runs of spaces, so each column has its own x
    steps = [("1", "recall", "r = decay x (k times S)"), ("2", "correct", "delta = beta x (v - r)"),
             ("3", "write", "S = decay x S + (k outer delta)"), ("4", "read", "o = (scale x q) times S")]
    for i, cols in enumerate(steps):
        for dx, s in zip((0, 22.5, 97.5), cols):
            out.append(text(tx + dx, sy + 22 + i * 22, s, size=12.5, mono=True))
    out.append(text(tx, sy + 22 + 4 * 22 + 4, "k, q, v are bf16 values. S, decay and delta are FP32.", size=12, fill=C["ink2"]))
    out.append(text(tx, sy + 22 + 4 * 22 + 20, "scale = 1 / sqrt(128) = 0.0884. It multiplies q in FP32.", size=12, fill=C["ink2"]))
    out.append(text(14, sy + 150, "Work per token: constant. Memory: constant. Order matters: token t needs the state left by token t-1.", size=12.5, weight=600))
    out.append("</svg>")
    return "".join(out)


if __name__ == "__main__":
    import sys
    import cairosvg
    d = sys.argv[1] if len(sys.argv) > 1 else "."
    for name, fn in (("layer_stack", layer_stack), ("token_flow", token_flow)):
        cairosvg.svg2png(bytestring=fn().encode(), write_to=f"{d}/{name}.png", output_width=1440)
        print("wrote", f"{d}/{name}.png")
