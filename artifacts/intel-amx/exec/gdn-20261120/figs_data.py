#!/usr/bin/env python3
"""Data-driven figures of gdn-amx-design.html. Every number comes from collected.json or predictions.json."""
from pagelib import C, dumbbell, fmt, hbars, lines_chart, rel_dots, stacked

# model geometry (tron PR #3696, checkpoint config.json)
LLAMA = {"layers": 32, "heads": 32, "head_dim": 128}
Q35 = {"attn_layers": 8, "heads": 16, "head_dim": 256, "gdn_layers": 24, "value_heads": 32, "dk": 128, "dv": 128}


def macs_per_context_token(layers, heads, head_dim):
    """bf16 multiply-adds per (generated token, context token): QK scores plus the weighted V sum."""
    return layers * heads * head_dim * 2


def gdn_fmas_per_token():
    """FP32 fused multiply-adds per generated token in the GDN layers: three per state element."""
    return Q35["gdn_layers"] * Q35["value_heads"] * Q35["dk"] * Q35["dv"] * 3


def cell_label(rec):
    return f"{rec['users']} user{'s' if rec['users'] > 1 else ''}, prompt {rec['prompt']:,}"


def order(pred):
    return sorted(pred["cells"], key=lambda c: (pred["cells"][c]["users"], pred["cells"][c]["prompt"]))


def fig_work_vs_context():
    xs = [0, 1024, 2048, 4096, 8192, 12288, 16384]
    la = macs_per_context_token(LLAMA["layers"], LLAMA["heads"], LLAMA["head_dim"]) / 1e6
    qa = macs_per_context_token(Q35["attn_layers"], Q35["heads"], Q35["head_dim"]) / 1e6
    g = gdn_fmas_per_token() / 1e6
    series = [
        {"name": "llama-3.1-8b", "color": C["other"], "pts": [(x, la * x) for x in xs], "endlabel": "32 attention layers"},
        {"name": "Qwen3.5 4B total", "color": C["ink"], "pts": [(x, qa * x + g) for x in xs], "endlabel": "attention + GDN", "dash": "5 4"},
        {"name": "Qwen3.5 4B attention", "color": C["attn"], "pts": [(x, qa * x) for x in xs], "endlabel": "8 layers, grows"},
        {"name": "Qwen3.5 4B GDN", "color": C["gdn"], "pts": [(x, g) for x in xs], "endlabel": f"24 layers, flat at {g:.1f} M"},
    ]
    return lines_chart(series, "context length (tokens already in the sequence)", "multiply-adds on the CPU per generated token (millions)",
                       "CPU arithmetic per generated token against context length for llama-3.1-8b and Qwen3.5 4B",
                       xticks=[0, 4096, 8192, 12288, 16384], marks=[(576, "576 tokens: GDN = attention")])


def fig_baseline_ttft(pred):
    rows = []
    for c in order(pred):
        r = pred["cells"][c]
        rows.append({"label": f"prompt {r['prompt']:,}", "value": r["prefill"]["ttft_s"], "color": C["ink2"],
                     "group": f"{r['users']} user{'s' if r['users'] > 1 else ''} at once",
                     "note": f"({r['prompt'] * r['users'] / r['prefill']['ttft_s']:,.0f} prompt tokens/s)"})
    return hbars(rows, "s", "Measured time to first token per cell", left=150, right=260, xlabel="time to first token (s), slowest user")


def fig_baseline_tps(pred):
    rows = []
    for c in order(pred):
        r = pred["cells"][c]
        rows.append({"label": f"prompt {r['prompt']:,}", "value": r["decode"]["tps"], "color": C["ink2"],
                     "group": f"{r['users']} user{'s' if r['users'] > 1 else ''} at once",
                     "note": f"per user ({r['decode']['tps'] * r['users']:,.0f} in total)"})
    return hbars(rows, "tok/s", "Measured decode tokens per second per user per cell", left=150, right=260,
                 xlabel="decode speed (tokens per second per user)")


PARTS = [("gdn", "GDN wall", C["gdn"]), ("attn", "attention busy time", C["attn"]), ("rest", "the rest: FPGA matrix multiplies, small host kernels, waits", C["other"])]


def fig_split(pred, kind):
    rows = []
    for c in order(pred):
        r = pred["cells"][c]
        k = r[kind]
        rows.append({"label": cell_label(r), "values": {"gdn": k["gdn_ms"], "attn": k["attn_ms"], "rest": k["rest_ms"]}})
    what = "prefill pass" if kind == "prefill" else "decode step"
    return stacked(rows, PARTS, "ms", f"Where the wall time of one {what} goes, per cell", left=190, right=110,
                   xlabel=f"wall of one {what}", gap=22, normalize=True)


def fig_pred_ttft(pred):
    """Time to first token relative to today: Part 0 alone (no AMX) and both AMX kernels (est.)."""
    rows = []
    for c in order(pred):
        r = pred["cells"][c]
        p = r["pred"]
        t0 = r["prefill"]["ttft_s"]
        rel = lambda v: 100.0 * v / t0
        rows.append({"label": cell_label(r), "a_text": f"{fmt(t0)} s", "m": rel(p["mid"]["reorder"]["ttft_s"]), "m_text": f"{fmt(p['mid']['reorder']['ttft_s'])} s",
                     "b": rel(p["mid"]["amx_both"]["ttft_s"]), "b_text": f"{fmt(p['mid']['amx_both']['ttft_s'])} s",
                     "b_lo": rel(p["hi"]["amx_both"]["ttft_s"]), "b_hi": rel(p["lo"]["amx_both"]["ttft_s"]),
                     "delta_text": f"{rel(p['mid']['amx_both']['ttft_s']) - 100:+.0f} % (est.)"})
    return rel_dots(rows, "Time to first token today and predicted, relative to today", "time to first token, percent of today's value",
                    xmin=40, xmax=100, step=10, m_name="Part 0 only: no AMX (est.)", b_name="Parts A and B: both AMX kernels (est.)")


def fig_pred_tps(pred):
    rows = []
    for c in order(pred):
        r = pred["cells"][c]
        p = r["pred"]
        d0 = r["decode"]["tps"]
        rel = lambda v: 100.0 * v / d0
        rows.append({"label": cell_label(r), "a_text": f"{d0:.1f} tok/s", "b": rel(p["mid"]["amx_attn"]["tps"]), "b_text": "",
                     "b_lo": rel(p["lo"]["amx_attn"]["tps"]), "b_hi": rel(p["hi"]["amx_attn"]["tps"]),
                     "delta_text": f"{rel(p['lo']['amx_attn']['tps']) - 100:+.1f} to {rel(p['hi']['amx_attn']['tps']) - 100:+.1f} % (est.)"})
    return rel_dots(rows, "Decode speed today and predicted, relative to today", "decode tokens per second per user, percent of today's value",
                    xmin=92, xmax=110, step=2, right=190, a_name="measured today = 100 %", b_name="Part B, working value: no change (est.)", better="higher", row_h=48,
                    a_dot=False)


def fig_kernel_cycles(rows):
    """rows: [{label, value (cycles per value head per token), color, hatch, note}]"""
    return hbars(rows, "us", "Time per value head per prompt token for the GDN recurrence", left=310, right=290,
                 xlabel="time per value head per prompt token (us)")
