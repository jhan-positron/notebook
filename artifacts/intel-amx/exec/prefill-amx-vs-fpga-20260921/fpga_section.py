#!/usr/bin/env python3
"""Section 5 of the prefill page from the measured FPGA-attention curve (campaign q4b-fpga-20260921).

Reads fpga-campaign-rows.json (written by ingest_fpga.py) and returns HTML: a figure (client-side TTFT against prompt
length, one line per arm, cold cells as squares), the per-cell table, and a computed summary dict for the prose.

Arms shown (all CI harness, whole delphi-3bda, 4 tp2 engines x 2 users, 1536 generated tokens):
  base      nightly deb (AVX)          + CPU attention   (q4b-swattn 2026-09-20, 3 passes)
  canon     canonical AMX deb          + CPU attention   (q4b-swattn 2026-09-20 + q4b-fpga passes)
  fpgabase  nightly deb (AVX)          + FPGA attention  (q4b-fpga)
  fpgacanon canonical AMX deb          + FPGA attention  (q4b-fpga)
Warm = cells 1536..8192 inside a pass (12 to 50 % prefix-cache hits); cold = the first cell of a driver run (fresh engines).
Pure ASCII.
"""
import json
import math
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS = os.path.join(HERE, "fpga-campaign-rows.json")
PROMPTS = [1024, 1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192]
ARMS = ["base", "canon", "fpgabase", "fpgacanon"]
ARM_LABEL = {"base": "nightly deb (AVX) + CPU attention", "canon": "canonical AMX deb + CPU attention",
             "fpgabase": "nightly deb (AVX) + FPGA attention", "fpgacanon": "canonical AMX deb + FPGA attention",
             "vnnik": "VNNI-K deb + CPU attention", "fpgavnnik": "VNNI-K deb + FPGA attention"}
ARM_COL = {"base": "#86b6ef", "canon": "#1c5cab", "fpgabase": "#eb6834", "fpgacanon": "#8f2f0c", "vnnik": "#1baf7a", "fpgavnnik": "#0d6b4a"}   # blues = CPU attention (light AVX, dark AMX), oranges = FPGA attention (light AVX build, dark AMX build)
INK, INK2, INK3, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def f0(x):
    return "-" if x is None else f"{x:,.0f}"


def load():
    if not os.path.exists(ROWS):
        return []
    return json.load(open(ROWS))


def aggregate(rows):
    """{arm: {prompt: {"warm": [pass means], "cold": [means], "tags": [...]}}} using the harness TTFT mean per cell."""
    agg = {}
    for r in rows:
        a = agg.setdefault(r["arm"], {}).setdefault(r["prompt_length"], {"warm": [], "cold": [], "warm_tags": [], "cold_tags": [], "tps": [], "cache": []})
        v = r["ttft_harness_ms"] if r.get("ttft_harness_ms") is not None else r["ttft_mean_ms"]
        if r["cold"]:
            a["cold"].append(v); a["cold_tags"].append(r["tag"])
        else:
            a["warm"].append(v); a["warm_tags"].append(r["tag"])
        if r.get("tps_mean") is not None:
            a["tps"].append(r["tps_mean"])
        if r.get("cache_hit_pct") is not None:
            a["cache"].append(r["cache_hit_pct"])
    return agg


def mean(xs):
    return statistics.mean(xs) if xs else None


def sd(xs):
    return statistics.stdev(xs) if len(xs) > 1 else None


def have_fpga(agg):
    return any(a in agg for a in ("fpgabase", "fpgacanon"))


def fig(agg):
    W, H = 1060, 520
    left, right, top, bot = 90, 720, 96, 440
    def X(p):
        return left + (math.log2(p) - 10) / (13 - 10) * (right - left)
    vals = [v for a in agg.values() for p in a.values() for v in p["warm"] + p["cold"]]
    ymin = math.log10(300)
    ymax = math.log10(max(20000, max(vals) * 1.15 if vals else 20000))
    def Y(ms):
        return bot - (math.log10(ms) - ymin) / (ymax - ymin) * (bot - top)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Client-side TTFT against prompt length for four arms" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="16" y="24" font-size="15" font-weight="600" fill="{INK}">Prefill against prompt length, measured: attention on the FPGA against attention on the CPU</text>')
    out.append(f'<text x="16" y="44" font-size="12" fill="{INK2}">CI harness, whole delphi-3bda, 4 tp2 engines x 2 users, client-side TTFT in ms (mean over 8 users x 10 rounds), mean of the passes. Both axes logarithmic.</text>')
    out.append(f'<text x="16" y="60" font-size="12" fill="{INK2}">Lines: the cells of a pass (prompt 1024 cold, the others warm: 12 to 54 % prefix-cache hits). Squares: cold cells (fresh engines). End labels: the 8192 warm means.</text>')
    lx = 16
    for a in ARMS:
        if a not in agg:
            continue
        out.append(f'<line x1="{lx}" y1="78" x2="{lx + 22}" y2="78" stroke="{ARM_COL[a]}" stroke-width="3"/><circle cx="{lx + 11}" cy="78" r="4" fill="{ARM_COL[a]}"/>')
        out.append(f'<text x="{lx + 28}" y="82" font-size="11" fill="{INK2}">{esc(ARM_LABEL[a])}</text>')
        lx += 240
    for ms in (300, 500, 1000, 2000, 5000, 10000, 20000):
        if math.log10(ms) < ymin or math.log10(ms) > ymax:
            continue
        yy = Y(ms)
        out.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 8}" y="{yy + 4:.1f}" font-size="11" fill="{INK3}" text-anchor="end">{ms / 1000:g} s</text>')
    for p in PROMPTS:
        x = X(p)
        out.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bot}" stroke="{GRID}" stroke-dasharray="2 4"/>')
        out.append(f'<text x="{x:.1f}" y="{bot + 18}" font-size="10" fill="{INK3}" text-anchor="middle">{p}</text>')
    out.append(f'<text x="{(left + right) / 2:.1f}" y="{bot + 40}" font-size="11" fill="{INK3}" text-anchor="middle">prompt length, tokens (log scale)</text>')
    out.append(f'<text x="20" y="{(top + bot) / 2:.1f}" font-size="11" fill="{INK3}" text-anchor="middle" transform="rotate(-90 20 {(top + bot) / 2:.1f})">TTFT, client side, ms (log scale)</text>')
    end_labels = []
    for a in ARMS:
        if a not in agg:
            continue
        pts = [(p, mean(agg[a][p]["warm"] + (agg[a][p]["cold"] if p == 1024 else []))) for p in PROMPTS if p in agg[a] and (agg[a][p]["warm"] or (p == 1024 and agg[a][p]["cold"]))]
        pts = [(p, v) for p, v in pts if v]
        if len(pts) >= 2:
            out.append('<polyline points="' + " ".join(f"{X(p):.1f},{Y(v):.1f}" for p, v in pts) + f'" fill="none" stroke="{ARM_COL[a]}" stroke-width="2"/>')
        for p, v in pts:
            n = len(agg[a][p]["warm"]) + (len(agg[a][p]["cold"]) if p == 1024 else 0)
            out.append(f'<circle cx="{X(p):.1f}" cy="{Y(v):.1f}" r="4.5" fill="{ARM_COL[a]}" stroke="{SURF}" stroke-width="1.5"><title>{esc(ARM_LABEL[a])}, prompt {p}: {v:,.0f} ms (n = {n})</title></circle>')
        for p in PROMPTS:
            if p in agg[a] and agg[a][p]["cold"] and p != 1024:
                v = mean(agg[a][p]["cold"])
                out.append(f'<rect x="{X(p) - 5:.1f}" y="{Y(v) - 5:.1f}" width="10" height="10" fill="{SURF}" stroke="{ARM_COL[a]}" stroke-width="2"><title>{esc(ARM_LABEL[a])}, prompt {p}, cold: {v:,.0f} ms (n = {len(agg[a][p]["cold"])})</title></rect>')
        if pts:
            end_labels.append((Y(pts[-1][1]), a, pts[-1][1]))
    # end labels, de-collided
    end_labels.sort()
    last = -100
    for yy, a, v in end_labels:
        yy2 = max(yy, last + 14)
        out.append(f'<text x="{right + 10}" y="{yy2 + 4:.1f}" font-size="11" fill="{INK}">{esc(ARM_LABEL[a].split(" + ")[0])} + {esc(ARM_LABEL[a].split(" + ")[1].split(" ")[0])}, warm 8192: {v / 1000:.1f} s</text>')
        last = yy2
    out.append('</svg>')
    return "\n".join(out)


def table(agg):
    arms = [a for a in ARMS + ["vnnik", "fpgavnnik"] if a in agg]
    h = ['<div class="tw"><table class="num"><thead><tr><th>prompt length</th>']
    for a in arms:
        h.append(f'<th>{esc(ARM_LABEL[a])}<br>warm mean (passes) / cold</th>')
    h.append('<th>FPGA vs CPU, canonical deb (warm)</th><th>FPGA vs CPU, nightly deb (warm)</th></tr></thead><tbody>')
    for p in PROMPTS:
        h.append(f'<tr><td>{p}</td>')
        for a in arms:
            c = agg.get(a, {}).get(p)
            if not c:
                h.append('<td>-</td>'); continue
            w = mean(c["warm"]); cw = f"{f0(w)}" + (f" +/- {sd(c['warm']):.0f}" if sd(c["warm"]) else "") + f" ({len(c['warm'])})" if c["warm"] else "-"
            cd = (f"{f0(mean(c['cold']))} ({len(c['cold'])})" if c["cold"] else "-")
            h.append(f'<td>{cw} / {cd}</td>')
        for cpu, fp in (("canon", "fpgacanon"), ("base", "fpgabase")):
            wc = mean(agg.get(cpu, {}).get(p, {}).get("warm", [])) if p != 1024 else mean(agg.get(cpu, {}).get(p, {}).get("cold", []))
            wf = mean(agg.get(fp, {}).get(p, {}).get("warm", [])) if p != 1024 else mean(agg.get(fp, {}).get(p, {}).get("cold", []))
            h.append(f'<td>{(100 * (wf - wc) / wc):+.0f} %</td>' if (wc and wf) else '<td>-</td>')
        h.append('</tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)


def summary(agg):
    """Computed facts for the prose."""
    s = {}
    for cpu, fp in (("canon", "fpgacanon"), ("base", "fpgabase")):
        d = {}
        for p in PROMPTS:
            key = "cold" if p == 1024 else "warm"
            wc = mean(agg.get(cpu, {}).get(p, {}).get(key, []))
            wf = mean(agg.get(fp, {}).get(p, {}).get(key, []))
            if wc and wf:
                d[p] = dict(cpu=wc, fpga=wf, pct=100 * (wf - wc) / wc)
        cold = {}
        for p in PROMPTS:
            wc = mean(agg.get(cpu, {}).get(p, {}).get("cold", []))
            wf = mean(agg.get(fp, {}).get(p, {}).get("cold", []))
            if wc and wf:
                cold[p] = dict(cpu=wc, fpga=wf, pct=100 * (wf - wc) / wc)
        s[fp] = dict(warm=d, cold=cold)
    return s


if __name__ == "__main__":
    agg = aggregate(load())
    print(json.dumps(summary(agg), indent=1))
    print(table(agg)[:400])


# ---------------------------------------------------------------- AMX build against AVX build, both with FPGA attention
# Earlier prompt-1024 pairs (both arms FPGA attention, only the CPU build differs). Values from rows-extracted.json / the
# campaign summaries; TTFT ms, decode TPS per user.
PRIOR_1024 = [
    # (setup, harness, n_amx, n_avx, ttft_amx, ttft_avx, tps_amx, tps_avx, note, ref)
    ("whole 3bda, tp2, 4 engines x 2 users, CI harness (canon-ci 2026-09-18 vs the 2026-09-18 nightly)", "CI harness", 1, 1, 516, 528, 186.25, 186.33,
     "canonical deb 0594dc54 vs nightly deb 3faba6d0. Mean over 13 nightly runs (2026-09-05 to 09-17): 509.5 ms, 185.67 TPS", "exec/results/canon-ci-20260918/canon/summary.txt:36; exec/results/ci-mimic-20260918/reference/nightly-0918.arm.json"),
    ("whole 3bda, tp4, 2 engines x 4 users, CI harness (canon-ci vs the 2026-09-18 nightly)", "CI harness", 1, 1, 646, 636, 146.05, 148.82,
     "mean over 13 nightly runs (2026-09-05 to 09-17): 635.2 ms, 145.18 TPS", "exec/results/canon-ci-20260918/canon/summary.txt:37; exec/results/ci-mimic-20260918/reference/nightly-0918.arm.json"),
    ("whole 3bda, tp2, 4 engines x 2 users, CI harness (this campaign, q4b-fpga 2026-09-21/22, the cold 1024 cells of the three passes)", "CI harness", 3, 3, 512.3, 554.0, 186.25, 185.12,
     "fpgacanon passes 1-3 (520, 513, 504 ms) vs fpgabase passes 1-3 (555, 554, 553 ms), prompt-1024 cells. The AVX side is 25 to 45 ms above the cell's history; against the 13-night mean (509.5 ms) the AMX side reads +0.5 %", "exec/results/q4b-fpga-20260921/fpgacanon-pass1/perf.json; exec/results/q4b-fpga-20260921/fpgabase-pass1/perf.json"),
    ("runtron, tp2, 8 users, our half (wedperf-attr 2026-09-16)", "runtron", 6, 6, 3195.1, 3214.2, 125.41, 124.80,
     "canonical c7844ca2ce vs AVX eb2de0265a; separate blocks", "exec/results/wedperf-attr-20260916/summary.md:25-26"),
    ("runtron, tp4, 8 users, our half (wedperf-attr 2026-09-16)", "runtron", 6, 6, 2288.3, 2253.1, 129.65, 132.30,
     "same binaries as the tp2 row", "exec/results/wedperf-attr-20260916/summary.md:22-23"),
]
PRIOR_1024_VNNIK = [
    ("whole 3bda, tp2, CI harness (ci-mimic target vs the 2026-09-18 nightly)", 504, 528, 176.75, 186.33, "VNNI-K deb 29a8a547; client under CPU pressure 27-48 % in the target run", "exec/results/ci-mimic-20260918/target-pass1/summary.txt:36"),
    ("whole 3bda, tp4, CI harness (ci-mimic target vs the 2026-09-18 nightly)", 629, 636, 133.44, 148.82, "the issue-4500 decode loss", "exec/results/ci-mimic-20260918/target-pass1/summary.txt:37"),
    ("our half, tp2, 1 engine x 2 users, CI harness (issue-4500 campaign, measurement block m6 = rinzler plus the CI client on our half, n = 2)", 699.5, 762, 183.88, 192.21, "VNNI-K deb vs nightly deb. With the kill switch the VNNI-K deb gives 762.5 ms and 184.5 TPS", "exec/results/issue4500-20260918/m6/summary.md:5-8"),
    ("our half, tp4, 1 engine x 4 users, CI harness (issue-4500 campaign, block m6, n = 2)", 809, 848.5, 135.37, 156.33, "with the kill switch: 814.5 ms and 144.62 TPS", "exec/results/issue4500-20260918/m6/summary.md:10-12"),
]


def welch(a, b):
    """Welch t of mean(b) - mean(a) with unequal variances. None when either side has fewer than 2 values."""
    if len(a) < 2 or len(b) < 2:
        return None
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    return (statistics.mean(b) - statistics.mean(a)) / se if se else None


def pass_no(tag):
    """1, 2, 3 for <arm>-pass<N>; 1 for <arm>-cold-p<len>, 2 for <arm>-cold2-p<len>."""
    m = re.search(r"pass(\d+)$", tag)
    if m:
        return int(m.group(1))
    m = re.search(r"cold(\d*)-p", tag)
    return int(m.group(1)) if (m and m.group(1)) else 1


def amx_vs_avx_rows(rows):
    """This campaign's cells, fpgabase (AVX build) against fpgacanon (AMX build), paired by pass number.

    One dict per (prompt, kind): the means over the paired passes, the per-pass deltas (ttft_pcts, tps_pcts, AMX minus AVX in
    percent of AVX), their means (ttft_pct, tps_pct) and the Welch t of the two arms' pass means."""
    fb, fc = {}, {}
    for r in rows:
        if r["arm"] in ("fpgabase", "fpgacanon"):
            (fb if r["arm"] == "fpgabase" else fc)[(r["prompt_length"], r["cold"], pass_no(r["tag"]))] = r
    keys = {}
    for k in set(fb) & set(fc):
        keys.setdefault((k[0], k[1]), []).append(k[2])
    out = []
    for (p, cold), passes in sorted(keys.items(), key=lambda x: (x[0][0], not x[0][1])):
        passes = sorted(passes)
        a = [fb[(p, cold, n)] for n in passes]
        b = [fc[(p, cold, n)] for n in passes]
        ta = [x["ttft_harness_ms"] for x in a]; tb = [x["ttft_harness_ms"] for x in b]
        pa = [x["tps_mean"] for x in a]; pb = [x["tps_mean"] for x in b]
        dt = [100.0 * (y - x) / x for x, y in zip(ta, tb)]
        dp = [100.0 * (y - x) / x for x, y in zip(pa, pb)]
        # per uncached prompt token: TTFT / (prompt tokens x (1 - prefix-cache hit share)), then the same paired delta
        def per_tok(x):
            return x["ttft_harness_ms"] / (x["prompt_tokens_mean"] * (1.0 - x["cache_hit_pct"] / 100.0))
        dk = [100.0 * (per_tok(y) - per_tok(x)) / per_tok(x) for x, y in zip(a, b)]
        out.append(dict(prompt=p, kind="cold" if cold else "warm", n=len(passes), passes=passes,
                        ttft_avx=mean(ta), ttft_amx=mean(tb), tps_avx=mean(pa), tps_amx=mean(pb),
                        ttft_avx_sd=sd(ta), ttft_amx_sd=sd(tb), tps_avx_sd=sd(pa), tps_amx_sd=sd(pb),
                        cache_avx=round(mean([x["cache_hit_pct"] for x in a]), 1), cache_amx=round(mean([x["cache_hit_pct"] for x in b]), 1),
                        ttft_pcts=dt, tps_pcts=dp, ttft_pct=mean(dt), tps_pct=mean(dp), tok_pcts=dk, tok_pct=mean(dk),
                        cache_avx_pcts=[x["cache_hit_pct"] for x in a], cache_amx_pcts=[x["cache_hit_pct"] for x in b],
                        t_ttft=welch(ta, tb), t_tps=welch(pa, pb)))
    return out


def fig_amx_vs_avx(cells):
    """Two panels: TTFT change and decode-TPS change of the AMX build against the AVX build, both with FPGA attention."""
    W = 1100
    SHORT_PRIOR = ["whole 3bda tp2, CI harness, 09-18 (canon-ci vs nightly)", "whole 3bda tp4, CI harness, 09-18 (canon-ci vs nightly)",
                   "runtron tp2, 8 users, 09-16 (wedperf-attr, n = 6)", "runtron tp4, 8 users, 09-16 (wedperf-attr, n = 6)"]
    rows = cells + [dict(prompt=1024, kind="prior", ttft_pct=100.0 * (p[4] - p[5]) / p[5], tps_pct=100.0 * (p[6] - p[7]) / p[7], prior=True, label="1024 " + sp) for p, sp in zip(PRIOR_1024[:2] + PRIOR_1024[3:], SHORT_PRIOR)]
    row_h = 26
    top = 134
    H = top + len(rows) * row_h + 70
    lab_w = 370
    p1l, p1r = lab_w + 10, lab_w + 320    # TTFT panel
    p2l, p2r = p1r + 50, p1r + 360         # TPS panel
    tmin, tmax = -55.0, 15.0
    smin, smax = -20.0, 25.0
    def X1(v):
        return p1l + (v - tmin) / (tmax - tmin) * (p1r - p1l)
    def X2(v):
        return p2l + (v - smin) / (smax - smin) * (p2r - p2l)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="AMX build against AVX build under FPGA attention: TTFT and decode TPS change per prompt length" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="16" y="24" font-size="15" font-weight="600" fill="{INK}">AMX build against AVX build, both with attention on the FPGA</text>')
    out.append(f'<text x="16" y="44" font-size="12" fill="{INK2}">Left: TTFT change (negative = the AMX build prefills faster). Right: decode TPS change (positive = the AMX build decodes faster). qwen3-4b.</text>')
    out.append(f'<text x="16" y="60" font-size="12" fill="{INK2}">Rows above the horizontal line: this campaign, tp2, 2 users per engine. Dot = mean of the paired per-pass deltas (2 or 3 passes per arm), pale bar = their range.</text>')
    out.append(f'<text x="16" y="76" font-size="12" fill="{INK2}">warm = later cells of a pass, cold = fresh engines. Rows below the line: prompt-1024 pairs from earlier campaigns (tp4 = 4 users per engine, runtron = 8 users in one process).</text>')
    for (xl, xr, X, lo, hi, step, title) in ((p1l, p1r, X1, tmin, tmax, 10, "TTFT: AMX build relative to AVX build, percent"), (p2l, p2r, X2, smin, smax, 5, "decode TPS: AMX build relative to AVX build, percent")):
        out.append(f'<text x="{(xl + xr) / 2:.1f}" y="{top - 30}" font-size="12" font-weight="600" fill="{INK}" text-anchor="middle">{title}</text>')
        v = lo
        while v <= hi + 1e-9:
            x = X(v)
            out.append(f'<line x1="{x:.1f}" y1="{top - 12}" x2="{x:.1f}" y2="{H - 50}" stroke="{GRID if abs(v) > 1e-9 else INK3}" stroke-width="{1 if abs(v) > 1e-9 else 1.5}"/>')
            out.append(f'<text x="{x:.1f}" y="{H - 36}" font-size="10" fill="{INK3}" text-anchor="middle">{v:+.0f}</text>')
            v += step
    y = top
    for i, r in enumerate(rows):
        if r.get("prior") and (i == 0 or not rows[i - 1].get("prior")):
            out.append(f'<line x1="16" y1="{y - row_h / 2:.1f}" x2="{W - 16}" y2="{y - row_h / 2:.1f}" stroke="{INK3}" stroke-width="1"/>')
        label = r["label"] if r.get("prior") else f'prompt {r["prompt"]}, {r["kind"]}'
        out.append(f'<text x="{lab_w}" y="{y + 4}" font-size="11" fill="{INK}" text-anchor="end">{esc(label[:58])}</text>')
        for X, key, xl, xr in ((X1, "ttft_pct", p1l, p1r), (X2, "tps_pct", p2l, p2r)):
            v = r[key]
            vv = max(min(v, (tmax if key == "ttft_pct" else smax)), (tmin if key == "ttft_pct" else smin))
            fill = SURF if r.get("prior") else ("#8f2f0c" if r["kind"] == "warm" else "#eb6834")
            out.append(f'<line x1="{X(0):.1f}" y1="{y}" x2="{X(vv):.1f}" y2="{y}" stroke="{"#8f2f0c" if not r.get("prior") else INK3}" stroke-width="2"/>')
            pcts = r.get("ttft_pcts" if key == "ttft_pct" else "tps_pcts") or []
            if len(pcts) > 1:   # range of the per-pass deltas behind the mean dot
                lo_v, hi_v = max(min(pcts), (tmin if key == "ttft_pct" else smin)), min(max(pcts), (tmax if key == "ttft_pct" else smax))
                out.append(f'<line x1="{X(lo_v):.1f}" y1="{y}" x2="{X(hi_v):.1f}" y2="{y}" stroke="#8f2f0c" stroke-width="7" stroke-opacity="0.25" stroke-linecap="round"><title>{esc(label)}: per pass {", ".join(f"{v:+.1f}" for v in pcts)} %</title></line>')
            if r.get("prior"):
                out.append(f'<rect x="{X(vv) - 5:.1f}" y="{y - 5}" width="10" height="10" fill="{SURF}" stroke="{INK3}" stroke-width="2"><title>{esc(label)}: {v:+.1f} %</title></rect>')
            else:
                out.append(f'<circle cx="{X(vv):.1f}" cy="{y}" r="5" fill="{fill}" stroke="#8f2f0c" stroke-width="2"><title>{esc(label)}: {v:+.1f} %</title></circle>')
            # the value label sits outside the range bar: left of its low end for negative means, right of its high end otherwise;
            # near the panel's left edge it goes right of the high end, so it does not touch the row label
            lo_e = max(min(pcts or [v]), (tmin if key == "ttft_pct" else smin)); hi_e = min(max(pcts or [v]), (tmax if key == "ttft_pct" else smax))
            anchor, lx = ("end", X(lo_e) - 9) if v < 0 else ("start", X(hi_e) + 9)
            if X(lo_e) - xl < 48:
                anchor, lx = "start", X(hi_e) + 9
            out.append(f'<text x="{lx:.1f}" y="{y + 4}" font-size="10" fill="{INK}" text-anchor="{anchor}">{v:+.1f} %</text>')
        y += row_h
    out.append(f'<text x="{(p1l + p2r) / 2:.1f}" y="{H - 16}" font-size="11" fill="{INK3}" text-anchor="middle">dark dot = warm cell, light dot = cold cell, pale bar = range over the passes, hollow square = earlier prompt-1024 pair</text>')
    out.append('</svg>')
    return "\n".join(out)


def table_amx_vs_avx(cells):
    h = ['<div class="tw"><table class="num"><thead><tr><th>cell (this campaign)</th><th>passes (paired)</th><th>TTFT, AVX build (ms, mean +/- sd)</th><th>TTFT, AMX build (ms, mean +/- sd)</th><th>TTFT change, mean of the per-pass deltas</th><th>per-pass TTFT change</th><th>Welch t (TTFT)</th><th>TTFT change per uncached prompt token, mean (per pass)</th><th>decode TPS, AVX build</th><th>decode TPS, AMX build</th><th>TPS change, mean</th><th>per-pass TPS change</th><th>prefix-cache hits AVX / AMX (%, per pass)</th></tr></thead><tbody>']
    def pm(v, s):
        return f"{v:,.0f}" + (f" +/- {s:,.0f}" if s else "")
    for r in cells:
        h.append(f'<tr><td>prompt {r["prompt"]}, {r["kind"]}</td><td>{r["n"]}</td><td>{pm(r["ttft_avx"], r.get("ttft_avx_sd"))}</td><td>{pm(r["ttft_amx"], r.get("ttft_amx_sd"))}</td><td>{r["ttft_pct"]:+.1f} %</td><td>{", ".join(f"{v:+.1f}" for v in r.get("ttft_pcts", []))}</td><td>{"-" if r.get("t_ttft") is None else f"{r[chr(116)+chr(95)+chr(116)+chr(116)+chr(102)+chr(116)]:+.1f}"}</td><td>{r["tok_pct"]:+.1f} % ({", ".join(f"{v:+.1f}" for v in r.get("tok_pcts", []))})</td><td>{r["tps_avx"]:.1f}</td><td>{r["tps_amx"]:.1f}</td><td>{r["tps_pct"]:+.1f} %</td><td>{", ".join(f"{v:+.1f}" for v in r.get("tps_pcts", []))}</td><td>{", ".join(f"{v:.0f}" for v in r.get("cache_avx_pcts", []))} / {", ".join(f"{v:.0f}" for v in r.get("cache_amx_pcts", []))}</td></tr>')
    h.append('</tbody></table></div>')
    h.append('<div class="tw"><table class="num"><thead><tr><th>prompt-1024 pairs, both arms FPGA attention (this campaign\'s cold cell included)</th><th>n (AMX / AVX)</th><th>TTFT, AVX build (ms)</th><th>TTFT, AMX build (ms)</th><th>TTFT change</th><th>TPS, AVX build</th><th>TPS, AMX build</th><th>TPS change</th><th>note</th><th>source</th></tr></thead><tbody>')
    for (setup, harness, na, nb, ta, tb, pa, pb, note, ref) in PRIOR_1024:
        h.append(f'<tr><td>{esc(setup)}</td><td>{na} / {nb}</td><td>{tb:,.0f}</td><td>{ta:,.0f}</td><td>{100 * (ta - tb) / tb:+.1f} %</td><td>{pb:.1f}</td><td>{pa:.1f}</td><td>{100 * (pa - pb) / pb:+.1f} %</td><td>{esc(note)}</td><td><code>{esc(ref)}</code></td></tr>')
    h.append('</tbody></table></div>')
    h.append('<div class="tw"><table class="num"><thead><tr><th>VNNI-K build against AVX build, both FPGA attention, prompt 1024</th><th>TTFT, AVX (ms)</th><th>TTFT, VNNI-K (ms)</th><th>TTFT change</th><th>TPS, AVX</th><th>TPS, VNNI-K</th><th>TPS change</th><th>note</th><th>source</th></tr></thead><tbody>')
    for (setup, ta, tb, pa, pb, note, ref) in PRIOR_1024_VNNIK:
        h.append(f'<tr><td>{esc(setup)}</td><td>{tb:,.0f}</td><td>{ta:,.0f}</td><td>{100 * (ta - tb) / tb:+.1f} %</td><td>{pb:.1f}</td><td>{pa:.1f}</td><td>{100 * (pa - pb) / pb:+.1f} %</td><td>{esc(note)}</td><td><code>{esc(ref)}</code></td></tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)
