#!/usr/bin/env python3
"""Generate token-divergence-issue4444-report.html from the td-20261016 campaign records.

Reads (all on NFS):
  exec/results/td-20261016/layers-<off>-vs-<on>.json   per-record comparisons (dd_first_divergence.py)
  exec/results/td-20261016/layers-<off>-vs-<on>.csv    per-key rows (for the WO statistics)
  exec/results/td-20261016/steps-<off>-vs-<on>.json    per-step logits comparisons (dd_logits_step.py)
  exec/results/p83-20261013/steps-fnew-vs-fbase.json   the 2026-10-13 FPGA-attention pair (logits only)
  exec/results/td2-20261016/verdict.txt, steps-*.json  prompt-8192 round (optional)
  exec/results/td3-20261016/verdict.txt, stats-*.txt   attention path counters round (optional)
  exec/td-20261016/ktest/results.txt                   kernel bit-exactness program output
  exec/td-20261016/replay/results.md                   offline replay (numbers quoted as literals below, with the section)
  exec/td-20261016/tiestats/tie_stats.json             near-tie statistics
Every measured number printed in the page comes from one of these files or from a literal marked with its source.
Usage: python3 gen_report.py [--out PATH]
"""
import argparse
import csv
import html
import json
import math
import statistics

EXEC = "/home/jhan/workspace/intel-AMX/exec"
RES = f"{EXEC}/results/td-20261016"
RES2 = f"{EXEC}/results/td2-20261016"
RES3 = f"{EXEC}/results/td3-20261016"
P83 = f"{EXEC}/results/p83-20261013"
KTEST = f"{EXEC}/td-20261016/ktest/results.txt"
TIES = f"{EXEC}/td-20261016/tiestats/tie_stats.json"
OUT_DEFAULT = "/home/jhan/workspace/intel-AMX/token-divergence-4444/token-divergence-issue4444-report.html"

# Validated palette (dataviz skill, references/palette.md, light mode): slots 1-3 validate all-pairs.
BLUE, ORANGE, AQUA, YELLOW, VIOLET, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6", "#e34948"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"

PAIRS = [  # (off, on, what the pair isolates, mechanism tag)
    ("baseoff", "pocoff", "kill switch on both: main's dotter against the PoC's unpack + dotter on VNNI K (the layout alone)", "none"),
    ("clean", "baseoff", "main built without AMX against main with the kill switch (the kill-switch contract on row-major K)", "none"),
    ("base", "poc", "AMX on both: the PoC removes the reader's add order; what is left is the page-end path choice", "page-end"),
    ("base", "new", "AMX on both: the VNNI reader's add order against the dotter's on partial pages", "order"),
    ("baseoff", "newoff", "kill switch on both: the reader's add order against the dotter's on every VNNI block", "order"),
    ("newoff", "trunc", "AMX order against AVX order, both with truncated weights (order only, on dense pages)", "order"),
    ("new", "trunc", "AMX weights rounded to nearest against truncated, same AMX order (rounding only)", "rounding"),
    ("new", "newoff", "the kill switch on the stack binary: AMX path against reader + AVX path", "rounding+order"),
    ("baseoff", "base", "the kill switch on main: AMX path against dotter + AVX path (the PR 3879 question)", "rounding+order"),
    ("clean", "new", "the issue's question: the row-major binary against the stack's AMX binary", "rounding+order"),
]
ARMS = [
    ("new", "runtron.pr4", "PR 4959 probe commit ea94e95a4e, VNNI K + AMX on", "the stack's binary"),
    ("base", "runtron.main1010", "main 72308ec90c, row-major K, AMX on", "the stack's comparator"),
    ("clean", "runtron.clean", "main 72308ec90c built with TRON_AMX_DISPATCH=OFF", "the issue's row-major binary"),
    ("poc", "runtron.poc", "ea94e95a4e + commit 017181c02d: each VNNI token row unpacked and scored by the row-major dotter", "PoC: removes the reader's add order"),
    ("trunc", "runtron.trunc", "ea94e95a4e + commit 3d1426f549: the AMX PV weights truncated to bf16 like the AVX path", "PoC: removes the rounding-mode difference"),
    ("newoff", "runtron.pr4 + TRON_AMX_DISABLE=1", "the stack's kill switch", "AMX off, VNNI reader + AVX path"),
    ("baseoff", "runtron.main1010 + TRON_AMX_DISABLE=1", "main's kill switch", "AMX off, dotter + AVX path"),
    ("pocoff", "runtron.poc + TRON_AMX_DISABLE=1", "the PoC's kill switch", "AMX off, unpack + dotter + AVX path"),
]


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def read_text(path):
    try:
        with open(path, errors="replace") as f:
            return f.read()
    except OSError:
        return None


def fmt_e(x, digits=2):
    if x is None:
        return "n/a"
    if x == 0:
        return "0"
    return f"{x:.{digits}e}".replace("e-0", "e-").replace("e+0", "e+")


def pct(x, digits=1):
    return "n/a" if x is None else f"{100 * x:.{digits}f} %"


def percentile_linear(values, q):
    """The numpy default (linear interpolation), the convention of tie_stats.py."""
    v = sorted(values)
    if not v:
        return float("nan")
    pos = (len(v) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def layer_stats(off, on):
    """Per-record comparison summary + WO statistics from the csv."""
    j = load_json(f"{RES}/layers-{off}-vs-{on}.json")
    out = {"pair": f"{off} vs {on}", "pending": j is None}
    if j is None:
        return out
    s = j["summary"]
    out.update(n=s["n_keys_compared"], n_over=s["n_over_threshold"], first=s["first_over"], min_token=s["min_token_over"],
               missing=(s["n_missing_in_off"], s["n_missing_in_on"]), dups=s.get("off_duplicate_keys"))
    rows, wo_any, logits = [], [], {}
    try:
        with open(f"{RES}/layers-{off}-vs-{on}.csv") as f:
            for r in csv.DictReader(f):
                if r["label"] == "WO" and r["layer"] == "0":
                    rows.append((int(r["token"]), float(r["rel_l2"]), float(r["frac_changed"])))
                if r["label"] == "WO" and float(r["rel_l2"]) > 0:
                    wo_any.append((int(r["token"]), int(r["layer"]), float(r["rel_l2"]), float(r["frac_changed"])))
                if r["label"] == "Logits":
                    logits[int(r["token"])] = (float(r["rel_l2"]), float(r["frac_changed"]))
    except OSError:
        pass
    rows.sort()
    wo_any.sort()
    out["wo_first_any"] = wo_any[0] if wo_any else None
    out["logits_at"] = logits
    diff = [r for r in rows if r[1] > 0]
    out["wo0"] = {
        "n_tokens": len(rows), "n_diff": len(diff), "first_tokens": [r[0] for r in diff[:6]],
        "n_diff_prompt": len([r for r in diff if r[0] < 1024]), "n_diff_decode": len([r for r in diff if r[0] >= 1024]),
        "median_rel": statistics.median([r[1] for r in diff]) if diff else 0.0,
        "max_rel": max([r[1] for r in diff]) if diff else 0.0,
        "median_frac": statistics.median([r[2] for r in diff]) if diff else 0.0,
        "at_128": next((r for r in rows if r[0] == 128), None),
        "diff_tokens": [r[0] for r in diff],
    }
    return out


def step_stats(path):
    j = load_json(path)
    if j is None:
        return None
    s = j["summary"]
    steps = j["steps"]
    flips = [st for st in steps if not st["same_top1"]]
    fracs = [st["frac_changed"] for st in steps]
    return {"summary": s, "steps": steps, "flips": flips, "frac_min": min(fracs), "frac_median": statistics.median(fracs),
            "p95_pair_linear": percentile_linear([abs(st["delta_pair"]) for st in steps], 0.95),
            "max_abs_median": statistics.median([st["max_abs_delta"] for st in steps]),
            "max_abs_p95": percentile_linear([st["max_abs_delta"] for st in steps], 0.95),
            "max_abs_max": max(st["max_abs_delta"] for st in steps)}


def ktest_lines():
    t = read_text(KTEST) or ""
    want = ("T0 ", "T1 ", "T1b", "T2 ", "T3   lane=s2:(acc+po)+pe reduce=halving", "T4   s2", "T5m qk_vnni_128x4 vs even/odd-chain model, combine=acc+fl(E+O)",
            "T6a", "T6c", "T6d weights_times_v_128x4 vs even/odd-chain model (RNE P), combine=acc+fl(E+O)", "T7a", "T8a", "T9a", "T9b", "T9c")
    out = {}
    for line in t.splitlines():
        for w in want:
            if line.startswith(w):
                out.setdefault(w.strip(), []).append(line)
    return out


def svg_header(w, h):
    return f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px;font-family:inherit" role="img">'


def legend(out, L, y, items):
    lx = L
    for lab, c in items:
        out.append(f'<circle cx="{lx + 6}" cy="{y}" r="5" fill="{c}"/><text x="{lx + 16}" y="{y + 4}" font-size="11" fill="{INK2}">{lab}</text>')
        lx += 16 + 6.5 * len(lab) + 26


LEGEND = (("add order only", BLUE), ("weight rounding (with or without an order difference)", ORANGE), ("page-end path choice", VIOLET), ("no difference", AQUA))


def first_record_text(st):
    """The first differing record in forward-pass order (WO of the first differing token when the WO differs there)."""
    if st.get("pending"):
        return "pending"
    if st["n_over"] == 0:
        return "no differing record"
    tok = st["min_token"]
    wf = st.get("wo_first_any")
    if wf and wf[0] == tok:
        return f"token {tok}, WO layer {wf[1]}: {pct(wf[3])} of its values, relative change {fmt_e(wf[2])}"
    f = st["first"]
    return f"token {tok}, {html.escape(f['key'].split(' of token')[0])}: {pct(f['frac_changed'])} of its values, relative change {fmt_e(f['rel_l2'])}"


def chart_first_token(layers):
    """Dot plot: first differing record per arm pair (log x), identical pairs at the right edge."""
    W, L, R, T, B = 960, 150, 40, 40, 60
    H = T + 34 * len(PAIRS) + 12 + B
    xs = lambda tok: L + (math.log10(max(tok, 1)) / math.log10(1400)) * (W - L - R)
    out = [svg_header(W, H), f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}"/>']
    for tok, lab, row in ((1, "token 1", 0), (10, "10", 0), (100, "100", 0), (128, "128", 1), (1000, "1000", 0), (1087, "1087", 1)):
        x = xs(tok)
        out.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{H - B}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - B + 16 + 13 * row}" font-size="11" fill="{INK2}" text-anchor="middle">{lab}</text>')
    out.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 6}" font-size="12" fill="{INK2}" text-anchor="middle">position of the first differing record (prompt tokens 0-1023, decode tokens 1024-1279; log scale)</text>')
    color = {"none": AQUA, "order": BLUE, "rounding": ORANGE, "rounding+order": BLUE, "page-end": VIOLET}
    for i, (off, on, what, mech) in enumerate(PAIRS):
        y = T + 18 + 34 * i
        st = layers[(off, on)]
        out.append(f'<text x="{L - 10}" y="{y + 4}" font-size="12" fill="{INK}" text-anchor="end">{off} vs {on}</text>')
        if st.get("pending"):
            out.append(f'<text x="{L + 6}" y="{y + 4}" font-size="11" fill="{MUTED}">pending</text>')
            continue
        if st["n_over"] == 0:
            x = xs(1280)
            out.append(f'<rect x="{x - 6:.1f}" y="{y - 6}" width="12" height="12" rx="2" fill="{AQUA}"/>')
            out.append(f'<text x="{x - 12:.1f}" y="{y + 4}" font-size="11" fill="{INK2}" text-anchor="end">identical over all {st["n"]:,} record keys</text>')
            continue
        tok = st["min_token"]
        x = xs(tok)
        out.append(f'<line x1="{xs(1)}" y1="{y}" x2="{x:.1f}" y2="{y}" stroke="{GRID}" stroke-width="2"/>')
        lab = first_record_text(st)
        if mech == "rounding+order" and tok < 128:
            x2 = xs(128)
            w0 = st["wo0"]["at_128"]
            out.append(f'<line x1="{x:.1f}" y1="{y}" x2="{x2:.1f}" y2="{y}" stroke="{GRID}" stroke-width="2"/>')
            out.append(f'<circle cx="{x2:.1f}" cy="{y}" r="6" fill="{ORANGE}" stroke="{SURF}" stroke-width="2"/>')
            lab2 = f'token 128, WO layer 0: {pct(w0[2]) if w0 else "n/a"} of its values, relative change {fmt_e(w0[1]) if w0 else "n/a"}'
            out.append(f'<text x="{x2 - 10:.1f}" y="{y + 15}" font-size="11" fill="{INK2}" text-anchor="end">{html.escape(lab2)}</text>')
            out.append(f'<circle cx="{x:.1f}" cy="{y}" r="6" fill="{BLUE}" stroke="{SURF}" stroke-width="2"/>')
            out.append(f'<text x="{x + 10:.1f}" y="{y - 7}" font-size="11" fill="{INK2}">{html.escape(lab)}</text>')
            continue
        dot_color = ORANGE if (mech == "rounding+order" and tok >= 128) else color[mech]
        out.append(f'<circle cx="{x:.1f}" cy="{y}" r="6" fill="{dot_color}" stroke="{SURF}" stroke-width="2"/>')
        if x < W - 380:
            out.append(f'<text x="{x + 10:.1f}" y="{y + 4}" font-size="11" fill="{INK2}">{html.escape(lab)}</text>')
        else:
            out.append(f'<text x="{x - 10:.1f}" y="{y + 4}" font-size="11" fill="{INK2}" text-anchor="end">{html.escape(lab)}</text>')
    legend(out, L, T - 16, LEGEND)
    out.append("</svg>")
    return "\n".join(out)


def chart_seam(layers):
    """Dot-and-stem on a log axis: the layer-0 WO difference size (median relative change over the tokens where it differs) per pair."""
    items = []
    for off, on, what, mech in PAIRS:
        st = layers[(off, on)]
        if st.get("pending") or st["n_over"] == 0 or not st.get("wo0") or st["wo0"]["n_diff"] == 0:
            continue
        w = st["wo0"]
        items.append((f"{off} vs {on}", w["median_rel"], w["n_diff"], w["n_tokens"], mech))
    W, L, R, T, B = 960, 220, 170, 40, 44
    H = T + 30 * len(items) + 16 + B
    lo, hi = 1e-5, 1e-2
    xs = lambda v: L + (math.log10(max(v, lo)) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (W - L - R)
    out = [svg_header(W, H), f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
    for v, lab in ((1e-5, "1e-5"), (1e-4, "1e-4"), (1e-3, "1e-3"), (1e-2, "1e-2")):
        x = xs(v)
        out.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{H - B}" stroke="{GRID}"/>')
        out.append(f'<text x="{x:.1f}" y="{H - B + 16}" font-size="11" fill="{INK2}" text-anchor="middle">{lab}</text>')
    out.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 6}" font-size="12" fill="{INK2}" text-anchor="middle">median relative change of the layer-0 WO record over the tokens where it differs (log scale)</text>')
    color = {"order": BLUE, "rounding": ORANGE, "rounding+order": ORANGE, "page-end": VIOLET}
    for i, (lab, v, nd, nt, mech) in enumerate(items):
        y = T + 16 + 30 * i
        out.append(f'<text x="{L - 10}" y="{y + 4}" font-size="12" fill="{INK}" text-anchor="end">{lab}</text>')
        out.append(f'<line x1="{L}" y1="{y}" x2="{xs(v):.1f}" y2="{y}" stroke="{GRID}" stroke-width="2"/>')
        out.append(f'<circle cx="{xs(v):.1f}" cy="{y}" r="6" fill="{color[mech]}" stroke="{SURF}" stroke-width="2"/>')
        out.append(f'<text x="{xs(v) + 10:.1f}" y="{y + 4}" font-size="11" fill="{INK2}">{fmt_e(v)} ({nd} of {nt} tokens differ)</text>')
    legend(out, L, T - 16, LEGEND[:3])
    out.append("</svg>")
    return "\n".join(out)


def chart_margins(sp, title):
    """Strip: per-step margin (first arm, bf16 ulps) with flip steps highlighted; the p95 pair movement as a line."""
    W, H, L, R, T, B = 960, 250, 60, 20, 36, 40
    steps = sp["steps"]
    maxu = 80
    ys = lambda u: H - B - (min(u, maxu) / maxu) * (H - T - B)
    xs = lambda k: L + (k - 1) / 255 * (W - L - R)
    out = [svg_header(W, H), f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
    for u in (0, 20, 40, 60, 80):
        out.append(f'<line x1="{L}" y1="{ys(u):.1f}" x2="{W - R}" y2="{ys(u):.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{L - 6}" y="{ys(u) + 4:.1f}" font-size="11" fill="{INK2}" text-anchor="end">{u}{"+" if u == maxu else ""}</text>')
    p95 = percentile_linear([abs(st["delta_pair"]) / st["ulp_top1_off"] for st in steps if st["ulp_top1_off"]], 0.95)
    out.append(f'<line x1="{L}" y1="{ys(p95):.1f}" x2="{W - R}" y2="{ys(p95):.1f}" stroke="{ORANGE}" stroke-width="2"/>')
    out.append(f'<text x="{W - R}" y="{ys(p95) - 6:.1f}" font-size="11" fill="{INK2}" text-anchor="end">p95 of the pair movement: {p95:.1f} ulps</text>')
    for st in steps:
        u = st["margin_off_ulps"]
        x, y = xs(st["step"]), ys(u)
        if not st["same_top1"]:
            out.append(f'<line x1="{x:.1f}" y1="{y - 6:.1f}" x2="{x:.1f}" y2="{y - 34:.1f}" stroke="{INK2}" stroke-width="1"/>')
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{RED}" stroke="{SURF}" stroke-width="2"/>')
            out.append(f'<text x="{x:.1f}" y="{y - 38:.1f}" font-size="11" fill="{INK}" text-anchor="middle">flip at step {st["step"]}: margin {u:g} ulp</text>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{BLUE}"/>')
    out.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 8}" font-size="12" fill="{INK2}" text-anchor="middle">generated step 1-256; y = gap between the two best candidates in the first arm, in bf16 ulps (capped at 80)</text>')
    out.append(f'<text x="{L}" y="{T - 14}" font-size="12" fill="{INK}">{html.escape(title)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_bias():
    """Dot plot of the mass-weighted bias and RMS relative error vs exact (replay M3, layer 0, 201 tokens; ktest T7a mass_weighted_bias)."""
    rows = [  # label, mass-weighted bias, rms, source
        ("replay, real data: truncated (AVX path)", -7.8e-4, 2.00e-3, "replay results.md M3 'clean'"),
        ("replay, real data: AMX arms (base, new)", -6.3e-4, 1.91e-3, "replay results.md M3 'base'"),
        ("replay, real data: all rounded to nearest", -1.6e-5, 1.60e-3, "replay results.md M3 'clean_rne'"),
        ("kernel test, random pages: truncated (AVX)", -8.339e-4, 2.917e-3, "ktest T7a o_trunc mass_weighted_bias / rms_rel"),
        ("kernel test, random pages: AMX kernel (RNE)", -3.961e-6, 1.624e-3, "ktest T7a o_rne mass_weighted_bias / rms_rel"),
    ]
    W, L, R, T, B = 960, 330, 120, 40, 50
    H = T + 40 * len(rows) + 10 + B
    lo, hi = -1.0e-3, 3.2e-3
    xs = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    out = [svg_header(W, H), f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
    for v in (-1e-3, -5e-4, 0, 5e-4, 1e-3, 1.5e-3, 2e-3, 2.5e-3, 3e-3):
        x = xs(v)
        out.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{H - B}" stroke="{GRID if v else INK2}"/>')
        out.append(f'<text x="{x:.1f}" y="{H - B + 16}" font-size="11" fill="{INK2}" text-anchor="middle">{v * 100:+.2f} %</text>')
    out.append(f'<text x="{(L + W - R) / 2:.0f}" y="{H - 6}" font-size="12" fill="{INK2}" text-anchor="middle">relative to the exact fp64 attention output: mass-weighted bias (dot) and RMS relative error (bar end)</text>')
    for i, (lab, bias, rms, src) in enumerate(rows):
        y = T + 22 + 40 * i
        out.append(f'<text x="{L - 10}" y="{y + 4}" font-size="12" fill="{INK}" text-anchor="end">{html.escape(lab)}</text>')
        out.append(f'<line x1="{xs(0):.1f}" y1="{y}" x2="{xs(rms):.1f}" y2="{y}" stroke="{GRID}" stroke-width="6"/>')
        out.append(f'<text x="{xs(rms) + 8:.1f}" y="{y + 4}" font-size="11" fill="{INK2}">RMS error {rms * 100:.2f} %</text>')
        out.append(f'<circle cx="{xs(bias):.1f}" cy="{y}" r="6" fill="{ORANGE if bias < -1e-4 else AQUA}" stroke="{SURF}" stroke-width="2"/>')
        out.append(f'<text x="{xs(bias):.1f}" y="{y - 11}" font-size="11" fill="{INK2}" text-anchor="middle">bias {bias * 100:+.3f} %</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_orders():
    """Schematic of the three fp32 add orders for one 128-dim score."""
    W, H = 960, 290
    out = [svg_header(W, H), f'<rect width="{W}" height="{H}" fill="{SURF}"/>']
    cols = [
        ("Row-major dotter (AVX-512)", BLUE, [
            "16 lanes; lane j holds dims 2j, 2j+1",
            "acc1[j]: dims 0-31, then 64-95",
            "acc2[j]: dims 32-63, then 96-127",
            "t[j] = acc1[j] + acc2[j]",
            "tree over the 16 lanes:",
            "  j+8, then j+4, then j+2, then 0+1",
            "lane step: (acc + odd) + even product"]),
        ("VNNI reader (AVX-512)", ORANGE, [
            "one lane per token",
            "one chain over the 64 dimension",
            "  pairs, in dimension order",
            "step: (acc + odd) + even product",
            "no tree",
            "",
            "scalar model bit-exact: 512,000 / 512,000"]),
        ("AMX tile (TDPBF16PS)", VIOLET, [
            "4 instructions of 16 pairs each",
            "per instruction:",
            "  E = chain of the 16 even products",
            "  O = chain of the 16 odd products",
            "  acc = acc + fl(E + O)",
            "found by experiment, not in the manual",
            "model bit-exact: 512,000 / 512,000"]),
    ]
    cw = (W - 40) / 3
    for i, (title, c, lines) in enumerate(cols):
        x = 20 + i * cw
        out.append(f'<rect x="{x}" y="16" width="{cw - 16}" height="{H - 32}" rx="6" fill="none" stroke="{c}" stroke-width="2"/>')
        out.append(f'<text x="{x + 12}" y="42" font-size="14" font-weight="600" fill="{INK}">{html.escape(title)}</text>')
        for k, ln in enumerate(lines):
            out.append(f'<text x="{x + 12}" y="{70 + 28 * k}" font-size="12" fill="{INK2}" xml:space="preserve">{html.escape(ln)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def td2_section():
    v = read_text(f"{RES2}/verdict.txt")
    t = read_text(f"{RES2}/tokens.txt")
    if not v:
        return "<p><em>Pending: the prompt-8192 round (probe-td2.sh) has not finished.</em></p>"
    rows = []
    for off, on in (("base", "new"), ("new", "newoff"), ("base", "poc")):
        j = load_json(f"{RES2}/steps-{off}-vs-{on}.json")
        if not j:
            continue
        s = j["summary"]
        rows.append(f"<tr><td>{off} vs {on}</td><td class='num'>{s['n_identical_steps']} of {s['n_steps']}</td><td>{s['flip_steps'] or 'none'}</td>"
                    f"<td class='num'>{pct(s['nonflip_median_frac_changed'])}</td><td class='num'>{s['nonflip_median_mean_abs_delta']:.3f}</td><td class='num'>{s['median_margin_off']:.3f}</td><td class='num'>{s['max_tvd']:.3f}</td></tr>")
    jb = load_json(f"{RES2}/steps-base-vs-new.json")
    j1 = load_json(f"{RES}/steps-base-vs-new.json")
    lead = ""
    if jb and j1:
        sb, s1 = jb["summary"], j1["summary"]
        tie2 = sum(1 for st in jb["steps"] if st["margin_off_ulps"] <= 2)
        lead = (f"<p>Answer: the logits are not identical at prompt 8,192 either. base and new differ at {256 - sb['n_identical_steps']} of 256 steps with a median {pct(sb['nonflip_median_frac_changed'])} of the logits changed, the same spread as at prompt 1,024. "
                f"No top token changed because this prompt leaves no near tie: the median margin is {sb['median_margin_off']:.2f} logit units against {s1['median_margin_off']:.2f} at prompt 1,024, and {tie2} of the 256 steps have a margin of at most 2 ulps. "
                f"The pair base vs poc is again identical for the first 64 steps and differs from step 65 on, the step whose token completes decode page 128 (8,192 prompt tokens fill pages 0 to 127 exactly). "
                f"So the identical tokens of the issue's prompt-8192 cells are a property of the prompt, not of the paths.</p>")
    return (lead + f"<p>Forced runs at prompt 8,192 tokens, 256 generated tokens, CPU attention, the same binaries. Token checks:</p><pre class='small'>{html.escape(t or '')}</pre>"
            f"<table><thead><tr><th>pair</th><th class='num'>steps with identical logits</th><th>top-token flips (step)</th>"
            f"<th class='num'>median share of logits changed</th><th class='num'>median mean |delta| (logit units)</th><th class='num'>median margin (logit units)</th><th class='num'>max TVD</th></tr></thead><tbody>{''.join(rows)}</tbody></table>")


RES4 = f"{EXEC}/results/td4-20261016"


def td3_section():
    v3 = read_text(f"{RES3}/verdict.txt")
    v4 = read_text(f"{RES4}/verdict.txt")
    if not v3:
        return "<p><em>Pending: the path-counter round (probe-td3.sh) has not finished.</em></p>"
    out = ("<p>Attention path counters (<code>TRON_ATTN_STATS=1</code>: the key tokens per layer visited by the AMX path and by the AVX path) of main, of the stack binary and of the PoC binary, forced to the same tokens, after 64 and after 65 generated tokens. A run of N generated tokens runs its decode forwards at positions 1024 to 1022 + N, so the forward at position 1087 (the page-end step of decode page 16) is the 65th token's forward. The difference between the 65-token and the 64-token run of one binary is what that forward added. Round 3 (63 against 64 tokens) measured the forward at position 1086 by mistake; it showed identical counters for main and the stack (16 pages on AMX, 63 tokens of page 16 on the AVX path, per layer and KV head), which is the expected state one step before the page completes.</p>"
           f"<pre class='small'>round 3, forward at position 1086 (64 against 63 tokens):\n{html.escape(v3)}</pre>")
    if v4:
        out += f"<pre class='small'>round 4, forward at position 1087 (65 against 64 tokens):\n{html.escape(v4)}</pre>"
        out += ("<p>Reading: per layer, the AMX path's count is in key tokens over the 8 KV heads of the rank, so one 64-token page is 512 and 16 pages are 8,192. At position 1087 main scores 17 pages on AMX (8,704) and nothing on the AVX path, while the stack binary and the PoC binary score 16 pages on AMX (8,192) and the 64 tokens of page 16 on the AVX path (512). That is the path-choice asymmetry of cause 3, measured directly.</p>"
                if ("8704, 0" in v4 and "8192, 512" in v4) else "<p>Reading: see the numbers above against the expected values (main 8,704 AMX + 0 AVX; stack 8,192 AMX + 512 AVX per layer).</p>")
    else:
        out += "<p><em>Pending: the 65-token round (probe-td4.sh) has not finished.</em></p>"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    layers = {(off, on): layer_stats(off, on) for off, on, _, _ in PAIRS}
    steps = {(off, on): step_stats(f"{RES}/steps-{off}-vs-{on}.json") for off, on, _, _ in PAIRS}
    fpga = step_stats(f"{P83}/steps-fnew-vs-fbase.json")
    kt = ktest_lines()
    ties = load_json(TIES) or {}
    td = ties.get("td20261016", {})

    # ---------- derived numbers used in the prose ----------
    base_new, base_poc, new_newoff, newoff_trunc, new_trunc = (layers[k] for k in (("base", "new"), ("base", "poc"), ("new", "newoff"), ("newoff", "trunc"), ("new", "trunc")))
    bn_wo, nn_wo, nt_wo, bp_wo = (x.get("wo0", {}) for x in (base_new, new_newoff, newoff_trunc, base_poc))
    order_counts = [layers[k]["wo0"]["n_diff"] for k in (("base", "new"), ("baseoff", "newoff"), ("newoff", "trunc")) if not layers[k].get("pending")]
    nonid = [(k, v) for k, v in steps.items() if v and v["summary"]["n_identical_steps"] < 256]
    frac_meds = [v["summary"]["nonflip_median_frac_changed"] for k, v in nonid]
    frac_mins = [min(st["frac_changed"] for st in v["steps"] if st["frac_changed"] > 0) for k, v in nonid]
    mean_abs = [v["summary"]["nonflip_median_mean_abs_delta"] for k, v in nonid]
    maxabs_max = [v["max_abs_max"] for k, v in nonid]
    bp_steps = steps[("base", "poc")]
    bp_step65 = next((st for st in bp_steps["steps"] if st["step"] == 65), None) if bp_steps else None
    bn_steps = steps[("base", "new")]
    bn_step1 = bn_steps["steps"][0] if bn_steps else None
    ratio_med = (nn_wo.get("median_rel", 0) / bn_wo["median_rel"]) if bn_wo.get("median_rel") else float("nan")
    tie_pairs = td.get("pairs", {})
    tie_pred = td.get("prediction", {})
    tie_tot = td.get("totals", {})
    exact_ties = [p["margin_counts"]["eq_0"] for p in tie_pairs.values()] if tie_pairs else []
    le2 = [p["margin_counts"]["le_2ulp"] for p in tie_pairs.values()] if tie_pairs else []
    exp_flips = [tie_pred[k]["own_ulps"]["expected_flips"] for k in tie_pred if tie_pred[k].get("own_ulps") and tie_pred[k]["own_ulps"]["expected_flips"] > 0] or [float("nan")]

    # ---------- tables ----------
    arm_rows = "".join(f"<tr><td><code>{n}</code></td><td>{b}</td><td>{d}</td><td>{r}</td></tr>" for n, b, d, r in ARMS)
    pair_rows = []
    for off, on, what, mech in PAIRS:
        st = layers[(off, on)]
        if st.get("pending"):
            res = "pending"
        elif st["n_over"] == 0:
            res = f"identical: 0 of {st['n']:,} record keys differ"
        else:
            w = st["wo0"]
            extra = ""
            if st["first"]["label"] == "Logits" and st.get("wo_first_any") and st["wo_first_any"][0] == st["min_token"]:
                lg = st["logits_at"].get(st["min_token"])
                extra = f"; the logits of that step change by {fmt_e(lg[0])} ({pct(lg[1])} of entries)" if lg else ""
            res = (f"first difference at {first_record_text(st)}{extra}. {st['n_over']:,} of {st['n']:,} record keys differ. "
                   f"The layer-0 WO record differs at {w['n_diff']} of {w['n_tokens']} tokens (first: {', '.join(map(str, w['first_tokens']))}).")
        sp = steps[(off, on)]
        if sp:
            s = sp["summary"]
            lg = (f"{s['n_identical_steps']} of 256 steps identical. Flips at {s['flip_steps'] or 'none'}. "
                  f"Median {pct(s['nonflip_median_frac_changed'])} of the logits changed per step.")
        else:
            lg = "pending"
        pair_rows.append(f"<tr><td><code>{off}</code> vs <code>{on}</code></td><td>{html.escape(what)}</td><td>{res}</td><td>{lg}</td></tr>")

    flip_rows = []
    for off, on, what, mech in PAIRS:
        sp = steps[(off, on)]
        if not sp:
            continue
        for st in sp["flips"]:
            flip_rows.append(f"<tr><td>{off} vs {on}</td><td class='num'>{st['step']}</td><td>{st['off_top1']} / {st['off_top2']}</td><td class='num'>{st['margin_off']:g} = {st['margin_off_ulps']:g} ulps</td>"
                             f"<td class='num'>{st['delta_pair']:+g} = {st['delta_pair'] / st['ulp_top1_off']:+g} ulps</td><td class='num'>{st['on_top1']}</td></tr>")

    sat_rows = []
    for off, on, what, mech in PAIRS:
        sp = steps[(off, on)]
        if not sp:
            continue
        s = sp["summary"]
        sat_rows.append(f"<tr><td>{off} vs {on}</td><td class='num'>{s['n_identical_steps']}</td><td class='num'>{pct(s['nonflip_median_frac_changed'])}</td><td class='num'>{s['nonflip_median_mean_abs_delta']:.3f}</td>"
                        f"<td class='num'>{s['nonflip_median_abs_delta_pair']:g} / {sp['p95_pair_linear']:.4g}</td><td class='num'>{sp['max_abs_median']:.2f} / {sp['max_abs_max']:.1f}</td><td class='num'>{s['median_margin_off']:g}</td><td class='num'>{s['max_tvd']:.3f}</td><td>{s['flip_steps'] or 'none'}</td></tr>")

    kt_rows = "".join(f"<tr><td><code>{html.escape(k)}</code></td><td><code class='small'>{html.escape(' | '.join(v))}</code></td></tr>" for k, v in kt.items())

    tie_rows = []
    for off, on, what, mech in PAIRS:
        k = f"{off}-vs-{on}"
        pr, pq = tie_pred.get(k), tie_pairs.get(k)
        if not pr or not pq:
            continue
        own = pr.get("own_ulps", {})
        mc = pq.get("margin_counts", {})
        tie_rows.append(f"<tr><td>{off} vs {on}</td><td class='num'>{len(pq.get('observed_flips', []))} ({', '.join(map(str, pq.get('observed_flips', []))) or '-'})</td>"
                        f"<td class='num'>{own.get('expected_flips', float('nan')):.2f}</td><td class='num'>{own.get('p_at_least_one', float('nan')):.2f}</td>"
                        f"<td class='num'>{mc.get('eq_0', 'n/a')}</td><td class='num'>{mc.get('le_2ulp', 'n/a')}</td></tr>")

    fpga_txt = ""
    if fpga:
        s = fpga["summary"]
        fpga_txt = (f"The forced run of 2026-10-13 under FPGA attention (the PR 4959 probe commit against main, prompt 1,024) shows the same logit statistics as the CPU pairs: "
                    f"{s['n_identical_steps']} of 256 steps identical, a median {pct(s['nonflip_median_frac_changed'])} of the logits changed per step, flips at {s['flip_steps'] or 'none'} [exec/results/p83-20261013/steps-fnew-vs-fbase.json].")

    css = f"""
    :root {{ color-scheme: light; --ink:{INK}; --ink2:{INK2}; --muted:{MUTED}; --grid:{GRID}; --surf:{SURF}; --blue:{BLUE}; --orange:{ORANGE}; --aqua:{AQUA}; --violet:{VIOLET}; }}
    html, body {{ background:#ffffff; color:var(--ink); font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; line-height:1.45; margin:0; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 24px 16px 64px; }}
    h1 {{ font-size: 1.6rem; margin: 0 0 4px; }} h2 {{ font-size: 1.25rem; margin: 36px 0 8px; border-bottom: 1px solid var(--grid); padding-bottom: 4px; }} h3 {{ font-size: 1.05rem; margin: 22px 0 6px; }}
    p, li {{ max-width: 80ch; }} .meta {{ color: var(--ink2); font-size: .9rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: .9rem; margin: 10px 0 16px; }} th, td {{ border-bottom: 1px solid var(--grid); padding: 6px 8px; text-align: left; vertical-align: top; }} th {{ color: var(--ink2); font-weight: 600; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .88em; }} pre {{ background: #f4f4f1; padding: 10px; overflow-x: auto; font-size: .82rem; }}
    .small {{ font-size: .8rem; }} .short {{ background: #f4f6fa; border-left: 4px solid var(--blue); padding: 10px 14px; }}
    figure {{ margin: 14px 0 22px; }} figcaption {{ color: var(--ink2); font-size: .88rem; margin-top: 6px; max-width: 90ch; }}
    .verdict {{ background: #fdf3ee; border-left: 4px solid var(--orange); padding: 10px 14px; }}
    .ok {{ color: #1b7f5a; font-weight: 600; }} .miss {{ color: #b23b3b; font-weight: 600; }}
    """

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Issue 4444 root cause</title><style>{css}</style></head><body><main>
<h1>Issue #4444: the root cause of the token divergence, measured</h1>
<p class="meta">Campaign td-20261016 on delphi-3bda, 2026-10-16. Written by Claude Code for jhan. Every measured number on this page comes from a file named in the section "Records". The generator is <code>exec/td-20261016/report/gen_report.py</code>. Code line numbers refer to the PR 4959 head 6b081187e1 unless a commit is named.</p>

<h2>Short version</h2>
<div class="short">
<p>The tokens diverge for three reasons: the three attention engines add the same products in three different fp32 orders, the AVX-512 path truncates the softmax weights while the AMX path rounds them to nearest, and at the PR 4959 head one decode step in 64 scores one page on the software path where main uses AMX. Each cause was isolated with a proof-of-concept binary and measured record for record, and no kernel defect was found. The one pre-existing accuracy problem is the AVX-512 truncation of the weights, which biases the attention output low by 0.08 % on average and raises its error against an exact reference by 1.13 to 1.8 times, depending on where it is measured.</p>
</div>

<h2>Words used here</h2>
<table><thead><tr><th>term</th><th>meaning</th></tr></thead><tbody>
<tr><td>tron, runtron</td><td>tron is the inference program under test. runtron is its command-line tool. All runs here are runtron runs.</td></tr>
<tr><td>AMX, AVX-512</td><td>Two Intel CPU instruction sets. AMX multiplies 16-row tiles (instruction TDPBF16PS). AVX-512 works on 16-lane vectors (instruction VDPBF16PS). Both multiply bf16 pairs and add in fp32.</td></tr>
<tr><td>bf16, fp32, fp64, ulp</td><td>bf16 is the 16-bit float the activations and the KV cache use (8 significant bits, one notch = 0.39 % to 0.78 % of the value). fp32 is the 32-bit float the sums are formed in (one notch = 0.6e-7 to 1.2e-7 of the value). fp64 is the 64-bit float of the exact reference. A ulp is one notch at the size of the value.</td></tr>
<tr><td>dotter, reader, AMX kernels</td><td>The three ways tron scores a query against stored keys: the row-major dotter (<code>dotter&lt;bf16,128&gt;</code>, one token at a time), the VNNI reader (<code>k_vnni::qk_group</code>, one token per vector lane, reads the VNNI K layout of PR 4956), and the AMX kernels (<code>qk_rowmajor_128x4</code> / <code>qk_vnni_128x4</code> for a whole 64-token page, <code>weights_times_v_128x4</code> for the PV product). The AMX kernels serve head size 128 with 4 query heads per KV head only.</td></tr>
<tr><td>VNNI K</td><td>The K cache layout of PR 4956: dimension pairs of 16 consecutive tokens interleaved in one 64-byte line, the layout the AMX tile multiply reads directly.</td></tr>
<tr><td>PV path, softmax weights P</td><td>After the scores, attention forms P = exp(score - max) and multiplies P with the stored values V. The AVX-512 PV path (<code>scaled_v_expr</code>) truncates P to bf16 (drops the low 16 bits). The AMX PV kernel rounds P to the nearest bf16.</td></tr>
<tr><td>page, block, dense page, page-end step</td><td>A page is 64 tokens of the KV cache. A block is a 16-token quarter of a page. A dense page is one the AMX kernels take whole: complete, fully visible to the query and, at the PR 4959 head, all four blocks in the VNNI layout. The page-end step is the decode step whose new token completes a page.</td></tr>
<tr><td>prefill, pass, decode</td><td>Prefill scores the 1,024 prompt tokens in 8 passes of 128 tokens. Decode then generates one token per step (256 steps). Tokens are numbered 0 to 1,279 over the whole run.</td></tr>
<tr><td>kill switch</td><td>The environment variable <code>TRON_AMX_DISABLE=1</code>: the same binary runs with the AMX kernels off.</td></tr>
<tr><td>the stack, main, clean binary</td><td>The stack is PR 4956 to 4959 (VNNI K layout + AMX), measured at the PR 4959 probe commit ea94e95a4e. main is 72308ec90c, the commit the stack is based on. The clean binary is main built with <code>TRON_AMX_DISPATCH=OFF</code>, the issue's "row-major binary". ea94e95a4e is an ancestor of the PR 4959 head 6b081187e1, which merges newer main; the cited functions exist at both commits and the line numbers are the head's.</td></tr>
<tr><td>tp2, greedy, --pay-for-determinism</td><td>tp2 is tensor parallelism over 2 cards. Greedy decoding picks the top token at every step (temperature 0). <code>--pay-for-determinism</code> is the runtron flag that fixes the reduction order across threads, so a run repeats bit for bit.</td></tr>
<tr><td>forced run, record, record key</td><td>A forced run feeds every binary the same 256 generated tokens (teacher forcing), so all binaries score the same context at every step. A record is one logged intermediate vector ("WO layer 3 of token 517"). The comparison keys a run's 2,167,394 logged lines by their first 50 characters and compares the first line of each of the 416,443 distinct keys: the 32 per-head WQ lines and the 8 per-KV-head WK lines of a token share one key, so only their first head is compared. The roped WQ/WK, WV, WO, WFF and Logits records are single complete lines.</td></tr>
<tr><td>relative change</td><td>The relative L2 error of one record: the length of (new record minus old record) divided by the length of the old record. 2e-3 means the record moved by 0.2 % of its size.</td></tr>
<tr><td>WO, o_proj, Logits</td><td>WO is the output of the attention output projection (o_proj), the first logged value downstream of attention (the attention output itself is not logged for this model). Logits are the per-word scores of one step. The top token is the greedy choice.</td></tr>
<tr><td>near tie, margin, flip, pair movement</td><td>The margin is the gap between the two best candidates' logits at a step. A near tie is a margin within a few ulps. A flip is a step where two binaries choose different top tokens. The pair movement is how far the second arm moves the margin.</td></tr>
<tr><td>p95, TVD, RMS error</td><td>p95 is the 95th percentile: the value that 95 % of the steps stay below. TVD is the total variation distance between the two arms' next-token probability distributions at one step (0 = identical, 1 = disjoint). RMS error is the root mean square of the relative error.</td></tr>
<tr><td>Note [AMX attention dispatch]</td><td>A named comment block in <code>h/tron/kernels/amx_attn_iface.hpp</code> that states the dispatch rules and the numerics contract of the AMX kernels.</td></tr>
<tr><td>PR 3879</td><td>The PR that added the AMX attention kernels and the kill switch to main (merged 2026-09-15). The kill-switch pair on main, baseoff vs base, is the difference that PR introduced.</td></tr>
<tr><td>software loop, software path</td><td>The AVX-512 attention loop: the dotter or the reader for the scores and <code>scaled_v_expr</code> for PV. Every page the AMX kernels do not take goes through it.</td></tr>
<tr><td>query group, running state, RNE, mass-weighted bias</td><td>A query group is the 4 query heads that share one KV head; the AMX kernels score one group per call. The running state is the partial attention output with its max and sum, carried from page to page (v*, s*, m* in the code). RNE is round to nearest even, the rounding the AMX PV kernel applies to P. The mass-weighted bias of an output o against the exact output e is sum((o - e) x sign(e)) / sum(|e|); for a pure scale error it equals that scale.</td></tr>
<tr><td>Xeon 6962P, sliding window, softcap</td><td>The Xeon 6962P is the CPU of delphi-3bda. Sliding-window attention limits the scores to a window of recent tokens. Softcap applies a tanh cap to the scores. qwen3-4b uses neither.</td></tr>
<tr><td>PoC</td><td>Proof-of-concept binary: a measurement-only code change that removes exactly one suspected cause, so the record-level comparison tests that cause alone.</td></tr>
</tbody></table>

<h2>1. What was asked and what was run</h2>
<p>Issue #4444 asks for the cause of the token differences between the AMX/VNNI binaries and the row-major binary, with a measurement, and for a decision on the kill-switch contract. The earlier forced runs (2026-10-11, 2026-10-13) had shown that every flip occurs at a near tie. They had not shown which operation makes the scores differ, nor by how much, nor whether any of it is a defect.</p>
<p>Method: one cell (qwen3-4b, tp2, 1 user, prompt 1,024 tokens, 256 generated tokens, CPU attention, greedy, <code>--pay-for-determinism</code>). Eight binaries or settings ("arms") ran as forced runs with the full per-layer record kept (20.6 GB per run). The records were compared key for key and the logits step for step. Two proof-of-concept binaries remove one cause each. Predictions were written before the runs (<code>token-divergence-4444/predictions.md</code>) and are scored in section 8. Kernel-level facts come from a standalone program that drives the real kernels on the machine. An offline replay on the real logged Q, K, V values gives the accuracy against an exact reference. Run-to-run noise is excluded by the bit-identity of three different binaries (clean, baseoff, pocoff: 0 of 416,443 record keys differ) and by the A/A control of 2026-10-13 (the same binary run twice, 256 of 256 steps identical) [exec/td-20261016/tiestats/tie_stats.md, section 1].</p>
<table><thead><tr><th>arm</th><th>binary</th><th>what it is</th><th>role</th></tr></thead><tbody>{arm_rows}</tbody></table>

<h2>2. The results, pair by pair: which pairs differ, where and how much</h2>
<figure>{chart_first_token(layers)}
<figcaption>Each row is one pair of arms run on the same forced tokens. The dot marks the first record that differs, in forward-pass order. The label names it and how much it changed. The three pairs that swap the reader for the dotter (base vs new, baseoff vs newoff, clean vs new) first differ at prompt token 1: one fp32 ulp in a score, rarely visible in bf16. Every pair whose difference needs a dense page on AMX (the AMX add order in newoff vs trunc, the weight rounding in the other three) first differs at token 128, the first query that sees a dense page. clean vs new carries both causes and shows its rounding component as a second dot at token 128. The pair base vs poc isolates the page-end path choice: identical for 1,087 tokens. Two pairs are identical over the whole run.</figcaption></figure>
<table><thead><tr><th>pair</th><th>what the pair isolates</th><th>records (416,443 keys per run)</th><th>logits (256 steps)</th></tr></thead><tbody>{''.join(pair_rows)}</tbody></table>
<figure>{chart_seam(layers)}
<figcaption>Size of the difference where it starts: the layer-0 WO record of each token. The add-order pairs (blue) change the record by about 1e-4 relative, at {min(order_counts) if order_counts else 'n/a'} to {max(order_counts) if order_counts else 'n/a'} of the 1,279 tokens. The rounding pairs (orange) change it by about 2e-3 at every token from 128 on. The page-end pair (violet) changes it at three tokens only.</figcaption></figure>

<h2>3. Cause 1: three fp32 add orders</h2>
<figure>{chart_orders()}
<figcaption>How each engine sums the 128 products of one score. The products are identical (bf16 times bf16 is exact in fp32). Only the grouping of the fp32 adds differs. The two AVX-512 orders were confirmed bit for bit against scalar models (512,000 scores each). The AMX order was found by experiment and confirmed bit for bit on both AMX kernels. Source: <code>exec/td-20261016/ktest/results.txt</code>, lines T0, T3, T4, T5m, T6d.</figcaption></figure>
<p>Kernel level (random data, 2,000 query groups x 64 tokens). The AMX kernel and the VNNI reader disagree on 49.5 % of the scores, by a median of one fp32 ulp and at most 2 bf16 ulps where the sum cancels. The dotter and the AMX kernel disagree on 50.1 %. The two AMX QK kernels (row-major K and VNNI K) agree bit for bit. The AMX PV kernel and the AVX-512 PV loop differ in 72.8 % of outputs even when both see the same bf16 weights. So the PV path has an order difference of its own. [ktest T1, T1b, T2, T6a, T6c]</p>
<p>Model level. The stack binary (reader on partial pages) and main (dotter on partial pages) first differ at prompt token 1 ({first_record_text(base_new)}). In the offline replay a median one-ulp score difference changes the attention output at 88 of 201 sampled tokens, in 49 of them exactly one of the 4,096 bf16 elements [replay results.md, M2]. In the logged records the layer-0 WO differs at {bn_wo.get('n_diff', 'n/a')} of {bn_wo.get('n_tokens', 'n/a')} tokens (first at token {bn_wo.get('first_tokens', ['n/a'])[0]}), with a median relative change of {fmt_e(bn_wo.get('median_rel'))} and a median {pct(bn_wo.get('median_frac'))} of its values changed, because the o_proj mixes every element. The same first record appears in the kill-switch pair baseoff vs newoff, where the reader serves every VNNI block (the rows of the decode tail block still go through the dotter, section 5).</p>
<p><b>Proof by removal.</b> The PoC binary <code>poc</code> unpacks every VNNI token row and scores it with the row-major dotter. The reader never runs in it. Under the kill switch, <code>pocoff</code> equals <code>baseoff</code> in all {layers[('baseoff', 'pocoff')].get('n', 0):,} record keys and all 256 logit vectors. So the VNNI layout itself changes no number, and the add order of the reader is the whole difference between the two kill-switch arms. With AMX on, <code>poc</code> equals <code>base</code> for every record of the 1,024 prompt tokens and of decode tokens 1,024 to 1,086, and first differs at token {base_poc.get('min_token', 'n/a')} (cause 3 below). Prediction P1 held for the add order. The residual is a separate, smaller cause.</p>
<p>The clean binary and main under the kill switch are bit-identical ({layers[('clean', 'baseoff')].get('n_over', 'pending')} differing record keys, 256 of 256 logit vectors identical). So the kill-switch contract of Note [AMX attention dispatch] holds exactly on row-major K. With VNNI K it does not: <code>newoff</code> differs from <code>baseoff</code> from prompt token 1 on. The issue predicted this (the kill switch runs the VNNI reader, not the dotter). This run measures where it starts.</p>

<h2>4. Cause 2: the rounding of the softmax weights</h2>
<p>The AVX-512 PV path truncates P to bf16 (<code>interleave_bf16_ps</code> keeps the high 16 bits of each fp32 weight, kv_cache.hpp:2996-3001). The AMX PV kernel rounds to nearest even (<code>_mm512_cvtne2ps_pbh</code>, amx_attn.cpp, <code>weights_times_v_128x4</code>). Truncation always rounds toward zero. So the truncated weights sum to less than the exact ones while the divisor (the fp32 sum of the unrounded weights) does not shrink, and the output is scaled down. The difference itself is documented: Note [AMX attention dispatch] names the rounding of P as one of the two admissible reasons for AVX-against-AMX differences, and the unit test <code>t/t_amx_numerics.cpp</code> checks that the kernels stay within the error those two reasons allow. What was not known is its size and sign, measured here. The truncation dates from 2024 (commit 5d94957ac8), and no comment states a reason for it.</p>
<p>Model level. With AMX on, the first dense page is seen by prompt token 128, the first query of the second prefill pass. A pass's own pages are never dense, because the query mask holds one range per key of the pass (ranged_mask.cpp:43-49, 131-138). There <code>new</code> and <code>newoff</code> first differ ({first_record_text(new_newoff)}). From there the layer-0 WO differs at {nn_wo.get('n_diff', 'n/a')} of {nn_wo.get('n_tokens', 'n/a')} tokens (every token from 128 on), median relative change {fmt_e(nn_wo.get('median_rel'))}: about {ratio_med:.0f} times the add-order median of {fmt_e(bn_wo.get('median_rel'))}. main under its own kill switch shows the same first record and the same size (baseoff vs base). So this is the PR 3879 difference, not a stack difference.</p>
<p><b>Separating rounding from order.</b> The PoC binary <code>trunc</code> truncates P inside the AMX kernel. <code>new</code> vs <code>trunc</code> (rounding only, same AMX order) reproduces the token-128 record exactly ({first_record_text(new_trunc)}). <code>newoff</code> vs <code>trunc</code> (order only: AMX order against AVX order, both truncated) first differs at {first_record_text(newoff_trunc)}. Layers 0 and 1 of token 128 are bit-identical in that pair. The layer-0 WO of the order-only pair differs at {nt_wo.get('n_diff', 'n/a')} tokens with a median relative change of {fmt_e(nt_wo.get('median_rel'))}. Nothing else differs between the two paths: the scale, page max, exp, sum and the running-state update are the same code for the AMX page and the software page [self_attention.hpp:1783-1823 and 2040-2071], the Q packing is a copy [amx_attn.cpp:224-228], and both kernels read the same stored bf16 K and V. So at the first differing record the rounding mode is the dominant mechanism and the AMX-against-AVX add order is a minor one.</p>
<figure>{chart_bias()}
<figcaption>Which path is closer to the exact result. Offline replay of layer-0 attention on the real logged Q, K, V of 201 tokens (replay results.md, M3) and the kernel test on random 64-token pages (ktest T7a, mass-weighted bias). The truncating AVX path is biased low by 0.08 % of the output on average over the 201 sampled tokens, rising from 0.07 % at 16 attended tokens to 0.15 % at 1,088, and up to 0.18 % at single tokens. The rounding-to-nearest path's mean bias is -0.002 %, 50 times smaller, and changes sign from token to token. The error against the exact output is larger with truncation at every point it was measured: 1.25 times on the fp32 attention output (2.00e-3 against 1.60e-3 relative L2), 1.13 times on the bf16 output the next layer sees (2.57e-3 against 2.28e-3, where the final bf16 store of the output adds the same error to both paths), and 1.8 times in the kernel test, which measures the rounding step alone on one page. The AMX arms lie between the two, because their partial pages still go through the truncating path.</figcaption></figure>
<p>The truncation removes 0.16 % of the softmax weight mass on average on real data (0.14 % on random pages). For a weight whose mantissa is uniformly placed the expected loss is 0.27 % (2^-8 x ln 2). The measured loss is smaller for two reasons, both hypotheses not measured separately. The weights that carry most of the mass are the large ones. The weight of the running-maximum token is exactly 1, and truncation leaves it unchanged. In the binary the page max is taken against the running max [self_attention.hpp:1793-1794 and 2052-2053], so only the page holding the running max has a weight of exactly 1. [replay M3, ktest T7a]</p>

<h2>5. Cause 3: one page per 64 decode steps takes a different path (PR 4959 only)</h2>
<p>With the reader's order removed, <code>poc</code> and <code>base</code> still differ from decode token {base_poc.get('min_token', 'n/a')} on. At layer 0 their WO records differ only at tokens {', '.join(map(str, bp_wo.get('diff_tokens', [])[:6])) or 'n/a'}: the decode steps whose new token is the 64th of its page. The size of that difference ({fmt_e(bp_wo.get('median_rel'))} median) is that of the rounding mechanism, not of an add order. Code reading attributes it to the path choice (citations in the records section): in that step main sees a complete, fully visible page and scores it on AMX (AMX order, rounded weights). The PR 4959 head stores the new row row-major into the page's last block and converts the block to VNNI only at the end of the forward pass, after attention ran. So the page fails the layout gate and goes through the software loop (reader + dotter, truncated weights) for that one step. From the next step on both score the page on AMX. The mechanism is documented in the code (self_attention.hpp:1905-1907, kv_cache.hpp:815-818). Its consequence, one page scored differently from main at every 64th decode step, is stated nowhere. By code reading (not measured at record level), PR 4957 and PR 4958 write every new row into the VNNI column at once (<code>set_k_row</code> scatters the row, kv_cache.hpp of the PR 4958 head b39765ec29:718). So at those heads the page is VNNI-complete at the page-end step, and they should behave like main there. With the kill switch no arm uses AMX, so the asymmetry is absent there. The direct measurement of the path counters at that forward is in section 7.1: main adds 17 pages on AMX and nothing on the AVX path, the stack binary 16 pages on AMX and the 64 tokens of page 16 on the AVX path.</p>

<h2>6. From a one-ulp difference to a different token</h2>
<p>Every difference spreads over the vocabulary quickly. At the logits of a later step a median {pct(min(frac_meds)) if frac_meds else 'n/a'} to {pct(max(frac_meds)) if frac_meds else 'n/a'} of the 151,936 vocabulary scores differ by at least one bf16 ulp between any two non-identical arms. No step at which the two arms differ at all changes fewer than {pct(min(frac_mins)) if frac_mins else 'n/a'} of them, and the first logged step of base vs new changes {pct(bn_step1['frac_changed']) if bn_step1 else 'n/a'}. The pair base vs poc shows that the spread needs no more than one forward pass: its first differing record is the layer-0 WO of token 1087, and {pct(bp_step65['frac_changed']) if bp_step65 else 'n/a'} of that same token's logits differ. The median mean |delta| over the vocabulary is {min(mean_abs):.3f} to {max(mean_abs):.3f} logit units for the add-order pairs and the rounding pairs alike, while single logits move by up to {min(maxabs_max):.0f} to {max(maxabs_max):.0f} logit units at a few steps. The pairs whose difference includes the weight rounding mostly move the logits somewhat more at the 95th percentile (p95 of the pair movement 0.5 to 0.625 logit units for new vs trunc, new vs newoff and baseoff vs base, against 0.28 to 0.375 for the order-only pairs). clean vs new, which carries both causes, is at 0.375, and the flip counts do not separate the causes either. So the logits carry no information about which cause produced them. Only the record-level first difference does.</p>
<table><thead><tr><th>pair</th><th class="num">identical steps</th><th class="num">median share of logits changed</th><th class="num">median mean |delta| (logit units)</th><th class="num">pair movement median / p95 (logit units)</th><th class="num">largest single-logit change, median / max</th><th class="num">median margin (logit units)</th><th class="num">max TVD</th><th>flips at step</th></tr></thead><tbody>{''.join(sat_rows)}</tbody></table>
<p>A flip needs a near tie. The top token changed at three steps in the whole campaign: 20, 84 and 248. At each one the first arm's margin was 0 (an exact tie, resolved to the lower token id), 1 or 2 ulps, and the pair movement was 1 to 2 ulps. The median margin over the 256 steps is 3.9 logit units, about 39 ulps. This prompt has an exact tie at {min(exact_ties) if exact_ties else 'n/a'} to {max(exact_ties) if exact_ties else 'n/a'} of its 256 steps and a margin of at most 2 ulps at {min(le2) if le2 else 'n/a'} to {max(le2) if le2 else 'n/a'} of them, about one step in 25 [tie_stats.md, S2.1].</p>
<table><thead><tr><th>pair</th><th class="num">step</th><th>top two ids (first arm)</th><th class="num">margin</th><th class="num">movement of the pair</th><th class="num">top id in the second arm</th></tr></thead><tbody>{''.join(flip_rows) or '<tr><td colspan=6>pending</td></tr>'}</tbody></table>
<figure>{chart_margins(steps[('base', 'new')], 'base vs new: margin per step, flip highlighted') if steps[('base', 'new')] else ''}
<figcaption>Every generated step of the base-vs-new pair: the gap between the two best candidates in base (bf16 ulps). The orange line is the 95th percentile of how far the arm change moves that gap (linear-interpolation percentile, the convention of tie_stats.py). A step below the line is the one at risk. A step above it would need a movement larger than 19 of 20 measured ones, and none did here. Step 84, an exact tie in base, flipped. The near-tie model of section 7.3 expects {min(exp_flips):.1f} to {max(exp_flips):.1f} flips per 256 steps for the eight non-identical pairs of this cell ({tie_pred.get('base-vs-new', {}).get('own_ulps', {}).get('expected_flips', float('nan')):.1f} for base vs new). 0 to 2 were observed per pair, {tie_tot.get('observed_flips_total', 'n/a')} over the eight pairs against {tie_tot.get('expected_flips_total_own_ulps', float('nan')):.1f} expected.</figcaption></figure>

<h2>7. Confirmations: counters, the prompt-8192 cell, near-tie prediction</h2>
<h3>7.1 Attention path counters at the page-end forward (rounds 3 and 4)</h3>
{td3_section()}
<h3>7.2 The prompt-8192 cell, where every stack PR reported identical tokens (round 2)</h3>
{td2_section()}
<h3>7.3 Near-tie flip prediction</h3>
<p>The flip rule "the top token changes when the margin plus the pair movement crosses zero" (ties to the lower token id) matches every observed flip by construction. It uses the measured margin and movement of each step. It also confirms that the winning token is always one of the first arm's top two. The test of the model is its predictive form, which draws the movement independently of the margin from the pair's own measured movements (in ulps) and sums the flip probability over the 256 steps. On the earlier records (2026-10-13, 2026-08-30) it expected 0.76 to 1.54 flips per 256 steps per pair against 0 to 3 observed. On this campaign's eight non-identical pairs it reproduces every flip and expects {min(exp_flips):.1f} to {max(exp_flips):.1f} flips per pair, {tie_tot.get('expected_flips_total_own_ulps', float('nan')):.1f} in all. {tie_tot.get('observed_flips_total', 'n/a')} were observed, and the probability of that many or fewer is {tie_tot.get('p_total_le_observed_pooled_td_ulps', float('nan')):.2f} under the pooled-movement form of the model (which expects {tie_tot.get('expected_flips_total_pooled_td_ulps', float('nan')):.1f}). The eight pairs share arms and the same three near-tie steps, so the sum counts correlated events. The independent evidence is three distinct near-tie steps (20, 84, 248) over one prompt, plus the 2026-08-30 prompt-2048 pair (3 flips at margins 0, 0 and 3 ulps). Source: <code>exec/td-20261016/tiestats/tie_stats.md</code>, section 2.</p>
<table><thead><tr><th>pair</th><th class="num">observed flips (steps)</th><th class="num">expected flips</th><th class="num">P(at least one flip)</th><th class="num">exact ties among 256 steps</th><th class="num">steps with margin at most 2 ulps</th></tr></thead><tbody>{''.join(tie_rows) or '<tr><td colspan=6>pending</td></tr>'}</tbody></table>

<h2>8. Predictions written before the runs, and what happened</h2>
<table><thead><tr><th>prediction</th><th>outcome</th></tr></thead><tbody>
<tr><td>P1 poc == base in every record</td><td><span class="miss">Held for 1,087 tokens, then failed</span>: identical for all prompt tokens and decode tokens to 1,086. The residual is the page-end path choice (cause 3), found through this failure.</td></tr>
<tr><td>P2 pocoff == baseoff and baseoff == clean</td><td><span class="ok">Held</span>: 0 differing record keys in both pairs.</td></tr>
<tr><td>P3 base vs new first differs at prompt token 1, layer 0, about 1e-5 relative</td><td><span class="ok">Held on the token</span> (token 1), <span class="miss">missed on the layer and size</span>: the first bf16-visible record is WO at layer 16, 2.6e-4 relative, and layer 0 first differs at token 26. One-ulp score differences rarely survive the bf16 output rounding.</td></tr>
<tr><td>P4 newoff vs new first differs at prompt token 128, layer 0</td><td><span class="ok">Held</span>.</td></tr>
<tr><td>P5 trunc == newoff if the AMX and AVX orders agree</td><td><span class="miss">The orders do not agree</span>: the kernel test found the AMX tile adds its 16 pairs as two chains (even and odd products) joined once per instruction. The pair differs from token 128 (layer 2) on, by about a tenth of the rounding record at its first record and a thirtieth at the layer-0 WO median.</td></tr>
<tr><td>P6 new vs trunc: rounding only, first record at token 128 layer 0, about 1e-3, systematic sign</td><td><span class="ok">Held</span>: 1.9e-3, 36 % of values. The truncating side is biased low by 0.08 % on real data.</td></tr>
<tr><td>P7 spread logits for every non-identical pair; flips only at near ties (step 84 at 0-2 ulps, step 248 at 1 ulp)</td><td><span class="ok">Held for the two predicted steps</span>. A third flip step (20, an exact tie in baseoff and clean) appeared in the pairs that include those arms, also a near tie.</td></tr>
</tbody></table>

<h2>9. Verdict</h2>
<div class="verdict">
<p><b>Root cause</b> (measured on one cell: qwen3-4b, tp2, prompt 1,024, CPU attention). The divergence has three mechanical causes, each isolated and measured:</p>
<ul>
<li>three fp32 add orders (dotter, reader, AMX tile), which move a score by a median of one fp32 ulp (up to 2 bf16 ulps) and the logged layer-0 WO record at a quarter to a half of the tokens;</li>
<li>the truncation of the softmax weights in the AVX-512 PV path against round-to-nearest in the AMX PV kernel, which moves 20 to 30 % of the attention output elements (replay) and a third of the values of the logged WO record by one bf16 notch at every token that sees a dense page, and carries a systematic bias;</li>
<li>at the PR 4959 head only, a difference confined to the page-completing decode steps (layer-0 WO differs at tokens 1087, 1151, 1215 and nowhere else), which the code reading attributes to that step scoring its page in the software loop where main uses AMX, and the path counters confirm (section 7.1).</li>
</ul>
<p>The one cause whose first difference falls at a logged step (cause 3, token 1087) changes 55.6 % of that step's logits. Every cause changes about 80 % of the logits at the median later step. The greedy choice changes only at a near tie. This prompt has an exact tie at 0 to 4 of its 256 steps and a margin of at most 2 ulps at 10 to 11 of them, about one step in 25, and every observed flip occurs at one of those steps.</p>
<p>Which causes a cell can have: the AMX kernels serve head size 128 with 4 query heads per KV head only. So on qwen-3-30b-a3b (8 query heads per KV head) only cause 1 exists, on gpt-oss-120b (64-dimension heads) none exists (the issue reports it identical), and on llama-3.1-8b (128 x 4) all three can.</p>
<p><b>Is it a real problem?</b></p>
<ul>
<li>The add orders: no. All three are correct fp32 summations. The VNNI layout changes no number (pocoff equals baseoff bit for bit), and the same flips occur between any two orders.</li>
<li>The page-end path choice: not a defect. It is an asymmetry whose mechanism the code documents but whose consequence no comment states, and it prevents the stack from matching main bit for bit even after the reader order is matched.</li>
<li>The weight truncation: a pre-existing, systematic error of the AVX-512 path, measured here in the clean binary and under the kill switch, and by the code also the path taken on AMD hosts (the AMD fallback test of 2026-09-11, not run in this campaign). It costs a -0.08 % bias and a 1.13 to 1.8 times larger error than rounding to nearest. At the logits its effect is the same ulp-level spread as an add order, and no quality regression has been attributed to it. The cost of rounding to nearest in the AVX loop was not measured.</li>
<li>The kill-switch contract of Note [AMX attention dispatch]: broken exactly as the issue says. On VNNI K the switch gives an AMX-off run of the same binary, not the clean binary's numerics.</li>
</ul>
<p>No kernel defect was found: the dotter, the VNNI reader, the two AMX QK kernels and the AMX PV kernel each match an fp32 model of their own add order bit for bit (scalar models for the AVX-512 kernels, the even/odd-chain model for the AMX kernels) on 512,000 scores and 102,400 outputs of random data on one Xeon 6962P, and an AVX-512 re-implementation of the AMX order matches both AMX kernels on 512,000 scores and 1,024,000 outputs [ktest T3, T4, T5m, T6d, T9a, T9b]. The AVX-512 PV loop was compared with the AMX PV kernel only (T6a, T6c), not with a scalar model. Sliding-window and softcap operation were not exercised. The design note <code>token-divergence-issue4444-fix-design.html</code> proposes what to change.</p>
<p>What would refute this:</p><ul><li>a record that differs between baseoff and pocoff, or between clean and baseoff;</li><li>a base-vs-poc difference at a token that is not the 64th of its page;</li><li>a trunc-vs-newoff or new-vs-trunc difference before the first dense page;</li><li>a flip whose margin exceeds the pair's largest movement.</li></ul><p>None occurred in this cell. The same checks apply to any other model or to the FPGA path.</p>
</div>

<h2>10. Records</h2>
<ul>
<li>Runs: <code>exec/td-20261016/probe-td.sh</code> (round 1, 8 arms), <code>probe-td2.sh</code> (prompt 8192), <code>probe-td3.sh</code> (counters). Results in <code>exec/results/td-20261016/</code>, <code>td2-20261016/</code>, <code>td3-20261016/</code>. Full records on delphi-3bda in <code>/var/tmp/jhan/td/&lt;arm&gt;.full</code>.</li>
<li>Comparisons: <code>exec/dd/dd_first_divergence.py</code> (records. It lists the Logits record of a token before its layer records, so the first record in forward-pass order is taken from the csv) and <code>exec/dd/dd_logits_step.py</code> (logits), driven by <code>exec/td-20261016/analyze-td.sh</code>.</li>
<li>PoC commits (measurement-only branches of the shared tron repo): <code>jhan-td-poc</code> 017181c02d (unpack + dotter), <code>jhan-td-trunc</code> 3d1426f549 (truncated AMX weights). Builds: <code>exec/td-20261016/build-variant.sh</code>, <code>build-clean.sh</code>.</li>
<li>Kernel bit-exactness program: <code>exec/td-20261016/ktest/</code> (ktest.cpp, results.txt, README.md). Offline replay: <code>exec/td-20261016/replay/</code> (replay.py, results.md). Near-tie statistics: <code>exec/td-20261016/tiestats/</code>. Facts file with every number and its source: <code>exec/td-20261016/report/facts.md</code>.</li>
<li>Code citations for cause 3 (PR 4959 head 6b081187e1; the binaries were built at ea94e95a4e, where the same functions exist at these lines of that commit: convert_pending_k_blocks model.hpp:1847, k_layout_dense self_attention.hpp:1924-1935, note_k_row_saved kv_cache.hpp:2169, k_block_to_vnni_at kv_cache.hpp:2216):
  <ul>
  <li>page.count() includes the pass's own token [h/tron/scheduler/full.hpp:2349-2353; kv_cache.hpp:2038-2041];</li>
  <li>one range for a single decode query [src/tron/models/ranged_mask.cpp:43-90]; is_dense_amx_page [self_attention.hpp:1717-1728]; main's two gates [main 72308ec90c self_attention.hpp:1879-1890];</li>
  <li>the row-major tail block and its conversion at the forward end [model.hpp:3295-3312, 3412-3429, 1834-1842; kv_cache.hpp:2215-2231, 2261-2283]; the layout gate [self_attention.hpp:1909-1925];</li>
  <li>the prefill mask with one range per key of the pass [ranged_mask.cpp:43-49, 131-138; doc/hw-kv-ranged-mask.md:143-147].</li>
  </ul></li>
<li>Code citations for the paths: dotter [h/tron/kernels/dotter.hpp:211-221; reduce h/tron/simd/fp32.hpp:679], reader [h/tron/kernels/k_vnni.hpp:60-99], AMX kernels [src/tron/kernels/amx_attn.cpp], AVX PV truncation [h/tron/models/kv_cache.hpp:2996-3001], AMX PV rounding [amx_attn.cpp, weights_times_v_128x4], the numerics contract [h/tron/kernels/amx_attn_iface.hpp:74-85 at main 72308ec90c; 77-88 at the PR 4959 head].</li>
</ul>
<h3>Kernel-test lines quoted above</h3>
<table class="small"><tbody>{kt_rows}</tbody></table>
<h3>Limits</h3>
<ul>
<li>One model (qwen3-4b), one prompt, one tensor-parallel setting, CPU attention. The FPGA attention path was not measured at record level. {fpga_txt} The token identity in the issue's table for PR 4959 under FPGA attention is a token-level fact only. Under FPGA attention the PR 4959 head never converts a block that decode completes (Note [Row-major blocks under hardware attention], kv_cache.hpp:763-790). Such a page therefore takes the software loop on the stack for as long as the CPU scores it, while main can score the same complete page on AMX until the FPGA covers it. So a cause-3-like asymmetry is possible under FPGA attention, and it is not limited to the page-end step.</li>
<li>The AMX add order was found by experiment on one Xeon 6962P. Intel's manual does not promise it across implementations.</li>
<li>The replay models the AMX kernels' internal order. Its numbers for the AMX arms are model numbers, validated against the logged WO records to within the o_proj's own rounding (1.4e-3 to 2.4e-3 relative L2, the size that rounding alone produces at token 0).</li>
<li>The other observations in the issue (llama-3.1-8b token 46, qwen-3-30b-a3b token 5, the September cells) have no record-level data. The three-cause model names which causes each of those cells can have (section 9), but was not run on them.</li>
</ul>
</main></body></html>"""
    with open(a.out, "w") as f:
        f.write(page)
    print(f"wrote {a.out} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
