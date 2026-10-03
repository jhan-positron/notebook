#!/usr/bin/env python3
"""Generates PR3879/new-PRs/PR1/counter.html (AMX / AVX / FPGA attention path counters design).

Every number on the page is either computed here (closed form, est.) or copied from a
named measurement file. Pure-ASCII output (artifact mojibake trap, 2026-09-13).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.expanduser("~/workspace/intel-AMX/PR3879/new-PRs/PR1/counter.html")
SA = os.path.expanduser("~/workspace/intel-AMX/exec/results/single-attn-20260901/summary.json")

# ---------------------------------------------------------------- closed form (est.)
PAGE, CHUNK, ENGAGE, STEPS = 64, 128, 127, 256

def prefill_cpu(N):
    amx = avx = va = vv = 0
    for q in range(N):
        c = q // CHUNK
        for p in range(q // PAGE + 1):
            if p * PAGE + PAGE - 1 < c * CHUNK:      # written in an earlier forward: one range, dense
                amx += PAGE; va += 1
            else:                                    # own-chunk page: one range per token, dotter
                avx += min(PAGE, q - p * PAGE + 1); vv += 1
    return amx, avx, va, vv

def prefill_aof(N):
    fpga = avx = 0
    for q in range(N):
        c = q // CHUNK
        res = c * CHUNK
        if q < ENGAGE or res < 128:
            res = 0
        fpga += res
        avx += q - res + 1
    return fpga, avx

def decode_cpu(N0, steps):
    amx = avx = va = vv = 0
    for t in range(1, steps + 1):
        N = N0 + t
        amx += PAGE * (N // PAGE); va += N // PAGE
        if N % PAGE:
            avx += N % PAGE; vv += 1
    return amx, avx, va, vv

def decode_aof(N0, steps, lag=4):
    fpga = avx = 0
    for t in range(1, steps + 1):
        N = N0 + t
        fpga += N - lag
        avx += lag
    return fpga, avx

ROWS = {}
for N in (1024, 2048, 4096, 8192):
    a, v, va, vv = prefill_cpu(N)
    f, fv = prefill_aof(N)
    da, dv, dva, dvv = decode_cpu(N, STEPS)
    df, dfv = decode_aof(N, STEPS)
    ROWS[N] = dict(pre_tot=a + v, pre_amx=a, pre_avx=v, pre_va=va, pre_vv=vv,
                   pre_fpga=f, pre_fpga_avx=fv,
                   dec_tot=da + dv, dec_amx=da, dec_avx=dv, dec_va=dva, dec_vv=dvv,
                   dec_fpga=df, dec_fpga_avx=dfv, forwards=(N + CHUNK - 1) // CHUNK)
    assert a + v == N * (N + 1) // 2
    assert f + fv == N * (N + 1) // 2
    assert df + dfv == da + dv

def fmt(n):
    return f"{n:,}"

def pct(a, b):
    return f"{100.0 * a / b:.1f}"

# ---------------------------------------------------------------- measured phases (2026-09-01)
sa = json.load(open(SA))
def ph(arm, key):
    return sa[arm][key]

# ---------------------------------------------------------------- palette (dataviz reference slots 1-3)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"     # AVX, AMX, FPGA
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"

# ---------------------------------------------------------------- figure 1: prefill map
def fig_prefill():
    N = 512; W = 900
    x0, x1 = 250, 870
    sx = (x1 - x0) / N
    def X(t): return x0 + t * sx
    rowh, gap, top = 56, 14, 34
    def panel(oy, title, subtitle, ready_color, ready_label, short_label, aof):
        s = []
        s.append(f'<text x="{x0 - 230}" y="{oy - 26}" font-size="13" font-weight="600" fill="{INK}">{title}</text>')
        s.append(f'<text x="{x0 - 230}" y="{oy - 10}" font-size="12" fill="{INK2}">{subtitle}</text>')
        for c in range(N // CHUNK):
            yt = oy + top + c * (rowh + gap); yb = yt + rowh
            q0 = c * CHUNK
            s.append(f'<text x="{x0 - 10}" y="{yt + rowh/2 + 4}" font-size="12" text-anchor="end" fill="{INK2}">forward {c + 1}: queries {q0}-{q0 + CHUNK - 1}</text>')
            if c > 0:
                s.append(f'<rect x="{X(0):.1f}" y="{yt}" width="{X(q0) - X(0) - 2:.1f}" height="{rowh}" fill="{ready_color}" />')
                if aof:
                    s.append(f'<rect x="{X(q0) - 8:.1f}" y="{yt}" width="6" height="{rowh}" fill="{ORANGE}" />')
            s.append(f'<polygon points="{X(q0):.1f},{yt} {X(q0):.1f},{yb} {X(q0 + CHUNK):.1f},{yb}" fill="{BLUE}" />')
            if c > 0:
                bw_ = X(q0) - X(0)
                lbl = ready_label if bw_ > 330 else short_label
                s.append(f'<text x="{(X(0) + X(q0)) / 2:.1f}" y="{yt + rowh/2 + 4}" font-size="12" text-anchor="middle" fill="#ffffff">{lbl}</text>')
            s.append(f'<text x="{X(q0) + 6:.1f}" y="{yb - 6}" font-size="11" fill="#ffffff">own chunk: AVX</text>')
        # page grid
        for p in range(0, N + 1, PAGE):
            yA = oy + top - 4; yB = oy + top + 4 * (rowh + gap) - gap + 4
            s.append(f'<line x1="{X(p):.1f}" y1="{yA}" x2="{X(p):.1f}" y2="{yB}" stroke="{GRID}" stroke-width="1" />')
            if p % 128 == 0:
                s.append(f'<text x="{X(p):.1f}" y="{yB + 14}" font-size="11" text-anchor="middle" fill="{INK2}">{p}</text>')
        s.append(f'<text x="{x1}" y="{oy + top + 4 * (rowh + gap) - gap + 30}" font-size="11" text-anchor="end" fill="{MUTED}">K position (one grid line per 64-token KV page)</text>')
        return "\n".join(s)
    ph_h = top + 4 * (rowh + gap) - gap + 40
    H = 2 * ph_h + 90
    svg = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Which path scores which (query, K) pairs during the prefill of a 512-token prompt, under CPU attention and under attention on the FPGA" xmlns="http://www.w3.org/2000/svg">']
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}" />')
    svg.append(panel(44, "A. CPU attention (USE_HW_ATTN=0)", "pages written by earlier forwards are dense and take AMX; the chunk's own pages take AVX", ORANGE, "earlier chunks: AMX (dense pages)", "AMX", False))
    svg.append(panel(44 + ph_h + 44, "B. Attention on the FPGA", "the HBM-resident prefix goes to the FPGA; DMA-lagging pages (thin orange strip, width est.) take AMX; the own chunk takes AVX", AQUA, "earlier chunks: FPGA (HBM-resident)", "FPGA", True))
    svg.append('</svg>')
    return "\n".join(svg)

# ---------------------------------------------------------------- figure 1b: why K/V needs attention + FFN
def fig_kv_chain():
    W, H = 900, 400
    cols = [("prompt token 0", 60), ("prompt token 1", 250), ("prompt token 2", 440), ("last prompt token", 630)]
    cw = 170
    rows = [("embedding (token id)", 40, 26), ("layer 0: attention + FFN", 96, 44), ("layer 1: attention + FFN", 170, 44), ("layer 2: attention + FFN", 244, 44), ("logits + sampling", 318, 26)]
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="The K and V of a prompt token at layer L are computed from its layer L-1 output, which needs attention and the FFN; only the logits are skipped for given tokens" xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}" />')
    s.append(f'<defs><marker id="arr2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK2}" /></marker></defs>')
    for name, x in cols:
        s.append(f'<text x="{x + cw/2}" y="24" font-size="12" font-weight="600" text-anchor="middle" fill="{INK}">{name}</text>')
    for ri, (rname, y, h) in enumerate(rows):
        for ci, (cname, x) in enumerate(cols):
            last = ci == len(cols) - 1
            if ri == 0:
                fill, stroke, txt = "#f1f0ec", GRID, "given"
            elif ri == len(rows) - 1:
                if last:
                    fill, stroke, txt = "#fde8de", ORANGE, "computed: first generated token"
                else:
                    fill, stroke, txt = "none", MUTED, "skipped (token is given)"
            else:
                fill, stroke, txt = "#dfeaf9", BLUE, "runs: attention over tokens 0..i, FFN, then K/V for the next layer"
            dash = ' stroke-dasharray="4 3"' if fill == "none" else ''
            s.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{h}" rx="5" fill="{fill}" stroke="{stroke}"{dash} />')
            if ri in (0, len(rows) - 1):
                s.append(f'<text x="{x + cw/2}" y="{y + 17}" font-size="11" text-anchor="middle" fill="{INK2 if fill != "none" else MUTED}">{txt}</text>')
            else:
                s.append(f'<text x="{x + cw/2}" y="{y + 18}" font-size="11" text-anchor="middle" fill="{INK}">attention over tokens 0..{ci if not last else "n-1"}</text>')
                s.append(f'<text x="{x + cw/2}" y="{y + 33}" font-size="11" text-anchor="middle" fill="{INK}">FFN, then K/V of the next layer</text>')
            # vertical arrow to the next row
            if ri < len(rows) - 1:
                ny = rows[ri + 1][1]
                s.append(f'<line x1="{x + cw/2}" y1="{y + h}" x2="{x + cw/2}" y2="{ny - 1}" stroke="{INK2}" stroke-width="1.2" marker-end="url(#arr2)" />')
        # horizontal K/V arrows within a layer row (token j feeds token i > j)
        if 0 < ri < len(rows) - 1:
            for ci in range(len(cols) - 1):
                x_from = cols[ci][1] + cw; x_to = cols[ci + 1][1]
                s.append(f'<line x1="{x_from}" y1="{y + h/2}" x2="{x_to - 1}" y2="{y + h/2}" stroke="{AQUA}" stroke-width="1.6" marker-end="url(#arr2)" />')
    s.append(f'<text x="{cols[0][1]}" y="{rows[4][1] + 46}" font-size="11" fill="{INK2}">grey arrows (down): the layer-L output of a token is the input of its layer L+1; the K/V saved at layer L+1 are a linear map of that input.</text>')
    s.append(f'<text x="{cols[0][1]}" y="{rows[4][1] + 62}" font-size="11" fill="{INK2}">green arrows (right): attention at layer L reads the K/V of the earlier tokens at the same layer, so those K/V must exist first.</text>')
    s.append(f'<text x="{cols[0][1]}" y="{rows[4][1] + 78}" font-size="11" fill="{MUTED}">Only the embedding row is free for a given token. The logits row is the one computation the known prompt saves.</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- figure 2: one decode query
def fig_decode():
    N = 1100; W = 900; x0, x1 = 60, 880
    sx = (x1 - x0) / N
    def X(t): return x0 + t * sx
    H = 280
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="One decode query at context 1100: under CPU attention 17 full pages go to AMX and the 12-token tail page to AVX; under attention on the FPGA the resident prefix goes to the FPGA and only the last few tokens to AVX" xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}" />')
    # row A
    yA = 40; h = 34
    s.append(f'<text x="{x0}" y="{yA - 10}" font-size="13" font-weight="600" fill="{INK}">A. CPU attention: 17 full pages (1088 K tokens) on AMX, 12-token tail page on AVX</text>')
    for p in range(17):
        s.append(f'<rect x="{X(p*64):.1f}" y="{yA}" width="{64*sx - 1.5:.1f}" height="{h}" fill="{ORANGE}" />')
    s.append(f'<rect x="{X(1088):.1f}" y="{yA}" width="{12*sx:.1f}" height="{h}" fill="{BLUE}" />')
    s.append(f'<text x="{X(544):.1f}" y="{yA + h/2 + 4}" font-size="12" text-anchor="middle" fill="#ffffff">AMX: 17 dense pages x 64 = 1088 K tokens (98.9 %)</text>')
    s.append(f'<line x1="{X(1094):.1f}" y1="{yA + h}" x2="{X(1094):.1f}" y2="{yA + h + 22}" stroke="{INK2}" stroke-width="1" />')
    s.append(f'<text x="{X(1094):.1f}" y="{yA + h + 34}" font-size="11" text-anchor="end" fill="{INK2}">AVX: tail page, 12 K tokens (1.1 %)</text>')
    # row B
    yB = 140
    s.append(f'<text x="{x0}" y="{yB - 10}" font-size="13" font-weight="600" fill="{INK}">B. Attention on the FPGA (est.): the card scores 0..1095, the CPU scores the last 4 tokens on AVX, AMX gets none</text>')
    s.append(f'<rect x="{X(0):.1f}" y="{yB}" width="{1096*sx - 1.5:.1f}" height="{h}" fill="{AQUA}" />')
    s.append(f'<rect x="{X(1096):.1f}" y="{yB}" width="{max(4*sx, 2):.1f}" height="{h}" fill="{BLUE}" />')
    s.append(f'<text x="{X(548):.1f}" y="{yB + h/2 + 4}" font-size="12" text-anchor="middle" fill="#ffffff">FPGA: HBM-resident prefix, 1096 K tokens (99.6 %), boundary set by DMA progress at plan time</text>')
    s.append(f'<line x1="{X(1098):.1f}" y1="{yB + h}" x2="{X(1098):.1f}" y2="{yB + h + 22}" stroke="{INK2}" stroke-width="1" />')
    s.append(f'<text x="{X(1098):.1f}" y="{yB + h + 34}" font-size="11" text-anchor="end" fill="{INK2}">AVX: 4 K tokens behind the DMA boundary (0.4 %, est.)</text>')
    # axis
    ya = 225
    s.append(f'<line x1="{x0}" y1="{ya}" x2="{x1}" y2="{ya}" stroke="{GRID}" stroke-width="1" />')
    for t, lbl, anchor, dy in ((0, "0", "start", 16), (127, "127 engagement point", "start", 16), (1024, "1024 (end of shard 1)", "end", 16), (1088, "1088 (end of page 17)", "end", 30), (1100, "N = 1100", "end", 44)):
        s.append(f'<line x1="{X(t):.1f}" y1="{ya - 4}" x2="{X(t):.1f}" y2="{ya + dy - 12}" stroke="{INK2}" stroke-width="1" />')
        s.append(f'<text x="{X(t) - (3 if anchor == "end" else -3):.1f}" y="{ya + dy}" font-size="11" text-anchor="{anchor}" fill="{INK2}">{lbl}</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- chart A: closed-form shares
def chart_shares():
    rows = []
    for N in (1024, 8192):
        r = ROWS[N]
        rows.append((f"prompt {N}, prefill, CPU attention", r["pre_avx"], r["pre_amx"], 0, r["pre_tot"]))
        rows.append((f"prompt {N}, prefill, FPGA attention (est.)", r["pre_fpga_avx"], 0, r["pre_fpga"], r["pre_tot"]))
        rows.append((f"prompt {N}, 256 decode steps, CPU attention", r["dec_avx"], r["dec_amx"], 0, r["dec_tot"]))
        rows.append((f"prompt {N}, 256 decode steps, FPGA attention (est.)", r["dec_fpga_avx"], 0, r["dec_fpga"], r["dec_tot"]))
    W = 900; x0, x1 = 330, 745; bw = x1 - x0
    rh, gap, top = 26, 12, 40
    H = top + len(rows) * (rh + gap) + 30
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Closed-form share of attention work per path for prefill and decode at prompt 1024 and 8192, under CPU attention and under attention on the FPGA" xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}" />')
    # legend
    lx = x0
    for col, name in ((BLUE, "AVX"), (ORANGE, "AMX"), (AQUA, "FPGA")):
        s.append(f'<rect x="{lx}" y="14" width="12" height="12" rx="2" fill="{col}" />')
        s.append(f'<text x="{lx + 17}" y="24" font-size="12" fill="{INK2}">{name}</text>')
        lx += 70
    for i, (lbl, avx, amx, fpga, tot) in enumerate(rows):
        y = top + i * (rh + gap)
        s.append(f'<text x="{x0 - 10}" y="{y + rh/2 + 4}" font-size="12" text-anchor="end" fill="{INK2}">{lbl}</text>')
        x = x0
        outside = []
        for val, col, name in ((fpga, AQUA, "FPGA"), (amx, ORANGE, "AMX"), (avx, BLUE, "AVX")):
            if val == 0:
                continue
            w = bw * val / tot
            s.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w - 2, 1):.1f}" height="{rh}" fill="{col}" />')
            p = 100.0 * val / tot
            txt = f"{name} {p:.1f} %" if p >= 1 else f"{name} {p:.2f} %"
            if w > 90:
                s.append(f'<text x="{x + w/2:.1f}" y="{y + rh/2 + 4}" font-size="12" text-anchor="middle" fill="#ffffff">{txt}</text>')
            else:
                outside.append(txt)
            x += w
        if outside:
            s.append(f'<text x="{x1 + 6}" y="{y + rh/2 + 4}" font-size="11" fill="{INK2}">{", ".join(outside)}</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- chart B: measured phases
def chart_phases():
    arms = (("disable-8192", "AVX (kill switch)", BLUE), ("canon-8192", "AMX canonical", ORANGE))
    phases = (("qk", "QK (S = Q K^T)"), ("softmax", "softmax step (scale, max, exp, sum)"), ("pv", "PV (P V)"), ("state", "v*/s*/m* update"), ("total", "whole unit"))
    W = 900; x0, x1 = 300, 800; vmax = 4.0
    def X(v): return x0 + (x1 - x0) * v / vmax
    grp, bh, gap, top = 58, 18, 4, 40
    H = top + len(phases) * grp + 40
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Measured time per attention unit by phase, AVX versus canonical AMX, prompt 8192, 2026-09-01" xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}" />')
    lx = x0
    for _, name, col in arms:
        s.append(f'<rect x="{lx}" y="14" width="12" height="12" rx="2" fill="{col}" />')
        s.append(f'<text x="{lx + 17}" y="24" font-size="12" fill="{INK2}">{name}</text>')
        lx += 150
    for g in range(0, 5):
        s.append(f'<line x1="{X(g):.1f}" y1="{top - 6}" x2="{X(g):.1f}" y2="{top + len(phases)*grp - 10}" stroke="{GRID}" stroke-width="1" />')
        s.append(f'<text x="{X(g):.1f}" y="{top + len(phases)*grp + 6}" font-size="11" text-anchor="middle" fill="{INK2}">{g} us</text>')
    for i, (key, lbl) in enumerate(phases):
        y = top + i * grp
        s.append(f'<text x="{x0 - 10}" y="{y + bh + 2}" font-size="12" text-anchor="end" fill="{INK2}">{lbl}</text>')
        for j, (arm, name, col) in enumerate(arms):
            v = sa[arm][key]
            if key == "state" and arm.startswith("disable"):
                v = None   # the AVX probe folds the state update into "common"
            yy = y + j * (bh + gap)
            if v is None:
                s.append(f'<text x="{x0 + 4}" y="{yy + bh - 4}" font-size="11" fill="{MUTED}">folded into the softmax step for AVX (probe layout)</text>')
                continue
            s.append(f'<rect x="{x0}" y="{yy}" width="{X(v) - x0:.1f}" height="{bh}" rx="2" fill="{col}" />')
            s.append(f'<text x="{X(v) + 6:.1f}" y="{yy + bh - 4}" font-size="11" fill="{INK}">{v:.2f} us</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- figure 3: hook sites
def fig_hooks():
    W, H = 1000, 400
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Where the proposed counters and timers hook into tron: the three return sites of apply_page_tok, the FPGA plan site, and the forward and attention-job timers" xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURF}" />')
    s.append(f'<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK2}" /></marker></defs>')
    def box(x, y, w, h, lines, fill="#f1f0ec", stroke=GRID, bold=False):
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" />']
        for k, ln in enumerate(lines):
            fw = ' font-weight="600"' if (bold and k == 0) else ''
            out.append(f'<text x="{x + w/2}" y="{y + 18 + k*15}" font-size="12" text-anchor="middle" fill="{INK}"{fw}>{ln}</text>')
        return "\n".join(out)
    def arrow(x1, y1, x2, y2, lbl=None, dash=False):
        d = ' stroke-dasharray="5 4"' if dash else ''
        out = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK2}" stroke-width="1.4"{d} marker-end="url(#arr)" />']
        if lbl:
            out.append(f'<text x="{(x1+x2)/2}" y="{min(y1,y2) - 6}" font-size="11" text-anchor="middle" fill="{INK2}">{lbl}</text>')
        return "\n".join(out)
    # main chain (y = 60..122)
    s.append(box(20, 60, 140, 62, ["forward()", "full.hpp:1993", "one step, all users"], bold=True))
    s.append(box(210, 60, 190, 62, ["run_attention_job", "self_attention.hpp:755-807", "per worker, layer, minibatch"], bold=True))
    s.append(box(450, 60, 180, 62, ["apply_page_range", ":1374, per (kv_head, pass)", "flush tallies at :1566"], bold=True))
    s.append(box(680, 60, 150, 62, ["apply_page_tok", ":1709, per (query, page)", "one visit"], bold=True))
    s.append(arrow(160, 91, 210, 91, "plugin run"))
    s.append(arrow(400, 91, 450, 91, "run_sections"))
    s.append(arrow(630, 91, 680, 91, "per page"))
    # three return sites
    s.append(box(870, 14, 120, 44, ["AMX :1768", "+1 visit, +64 K"], fill="#fde8de", stroke=ORANGE))
    s.append(box(870, 70, 120, 44, ["empty :1820", "no work"], fill="#f1f0ec"))
    s.append(box(870, 126, 120, 44, ["AVX :1852", "+1 visit, +k tokens"], fill="#dfeaf9", stroke=BLUE))
    s.append(arrow(830, 80, 870, 38))
    s.append(arrow(830, 91, 870, 92))
    s.append(arrow(830, 102, 870, 146))
    # timers (dashed brackets around the timed calls, text below)
    s.append(f'<rect x="14" y="52" width="152" height="78" rx="8" fill="none" stroke="{INK2}" stroke-dasharray="5 4" />')
    s.append(f'<text x="20" y="148" font-size="11" fill="{INK2}">T1 forward wall</text>')
    s.append(f'<text x="20" y="162" font-size="11" fill="{INK2}">(work-queue thread)</text>')
    s.append(f'<rect x="204" y="52" width="202" height="78" rx="8" fill="none" stroke="{INK2}" stroke-dasharray="5 4" />')
    s.append(f'<text x="210" y="148" font-size="11" fill="{INK2}">T2 busy per worker (:774-806, exists today)</text>')
    s.append(f'<text x="210" y="162" font-size="11" fill="{INK2}">T3 wall on worker 0 (:755 to :806)</text>')
    s.append(f'<text x="210" y="176" font-size="11" fill="{INK2}">T4 layer period on worker 0 (entry to entry)</text>')
    # FPGA lane (y = 210..272)
    s.append(arrow(60, 122, 60, 241, dash=True))
    s.append(arrow(60, 241, 210, 241, dash=True))
    s.append(f'<text x="66" y="234" font-size="11" fill="{INK2}">main thread, FPGA</text>')
    s.append(f'<text x="66" y="258" font-size="11" fill="{INK2}">layers only</text>')
    s.append(box(210, 210, 250, 62, ["prepare_uniform_hw_attention", ":540-542 gate, :600 per (pass, query)", "fpga_k_tokens += tok_ix + 1"], fill="#dff5ec", stroke=AQUA, bold=True))
    s.append(box(500, 210, 190, 62, ["construct_hw_plan", "model.hpp:2519", "fpga_queries (distinct jobs)"], fill="#dff5ec", stroke=AQUA, bold=True))
    s.append(arrow(460, 241, 500, 241))
    s.append(box(730, 210, 260, 62, ["stream_hw_joins :1075-1078", "T5 hw_join_wait (CPU waits for the card)", "join folds FPGA + CPU partials"], fill="#dff5ec", stroke=AQUA))
    s.append(arrow(690, 241, 730, 241, dash=True))
    # per-token path set
    s.append(box(20, 300, 970, 62, ["Per-token path set: after each apply_page_tok call (:1539-1546) set the AMX / AVX bit of the token job; the FPGA bit comes from construct_hw_plan;",
                                   "fold on the main thread after plugin_state.run(q_batches) (model.hpp:1706) into token_jobs[class][{FPGA, AMX, AVX} bitmask];",
                                   "class = decode-like or prompt / mixed (proxy: listeners == token jobs at full.hpp:1993-2006)"], fill="#f1f0ec"))
    s.append(f'<text x="20" y="386" font-size="11" fill="{MUTED}">Line numbers are for main 0a51385e95 (2026-09-22). Dashed = timers or main-thread paths; solid = the call chain of one attention worker.</text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------------------------------------------------------------- page
CSS = """
:root{color-scheme:light;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--surf:#fcfcfb;--page:#f9f9f7;--blue:#2a78d6;--orange:#eb6834;--aqua:#1baf7a}
html,body{background:var(--page);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:24px;margin:0 0 4px;text-wrap:balance} h2{font-size:18px;margin:36px 0 8px;border-bottom:1px solid var(--grid);padding-bottom:4px} h3{font-size:15px;margin:20px 0 6px}
p,li{line-height:1.45;font-size:14px;max-width:78ch} .sub{color:var(--ink2);font-size:13px}
.short{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:12px 16px;margin:16px 0} .short p{margin:6px 0}
table{border-collapse:collapse;font-size:12.5px;margin:8px 0 16px;background:var(--surf)} th,td{border:1px solid var(--grid);padding:4px 8px;text-align:left;vertical-align:top} th{color:var(--ink2);font-weight:600}
td.n{font-variant-numeric:tabular-nums;text-align:right}
.tw{overflow-x:auto;margin:8px 0 16px} .tw table{margin:0}
.fig{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:8px;margin:12px 0} .fig svg{width:100%;height:auto;display:block;margin:0 auto}
.cap{font-size:13px;color:var(--ink2);margin:6px 0 12px 8px;max-width:95ch}
.take{font-size:13px;color:var(--ink2);margin:4px 0 0 8px}
code{font-size:12px;background:#f1f0ec;padding:1px 4px;border-radius:3px}
pre{font-size:12px;background:#f1f0ec;padding:10px 12px;border-radius:6px;overflow-x:auto;line-height:1.4}
.gloss dt{font-weight:600;font-size:13px;margin-top:6px} .gloss dd{margin:0 0 0 16px;font-size:13px;color:var(--ink2);max-width:90ch}
.tag{display:inline-block;font-size:11px;padding:1px 6px;border-radius:10px;border:1px solid var(--grid);color:var(--ink2);margin-left:4px}
.wrong{background:#fde8de;border-left:4px solid var(--orange);padding:8px 12px;margin:8px 0;max-width:85ch} .wrong p{margin:4px 0}
.ok{background:#dfeaf9;border-left:4px solid var(--blue);padding:8px 12px;margin:8px 0;max-width:85ch} .ok p{margin:4px 0}
ul.tight li{margin:2px 0}
nav.toc{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:10px 16px;margin:12px 0 20px}
nav.toc h2{font-size:14px;margin:0 0 6px;border:0;padding:0;color:var(--ink2)}
nav.toc ol{columns:2;column-gap:32px;margin:0;padding-left:22px;font-size:13px;line-height:1.5}
nav.toc ol ol{columns:1;padding-left:18px;font-size:12.5px}
nav.toc li{break-inside:avoid} nav.toc a{color:var(--blue);text-decoration:none} nav.toc a:hover{text-decoration:underline}
@media (max-width:600px){nav.toc ol{columns:1}}
"""

r1, r8 = ROWS[1024], ROWS[8192]

def share_table():
    out = ['<div class="tw"><table><tr><th>Cell (single user, per layer and KV head)</th><th>K tokens scored</th><th>AMX</th><th>AVX</th><th>FPGA (est.)</th><th>AMX visits</th><th>AVX visits</th><th>forwards</th></tr>']
    for N in (1024, 2048, 4096, 8192):
        r = ROWS[N]
        out.append(f'<tr><td>prompt {N}, prefill, CPU attention</td><td class="n">{fmt(r["pre_tot"])}</td><td class="n">{fmt(r["pre_amx"])} ({pct(r["pre_amx"], r["pre_tot"])} %)</td><td class="n">{fmt(r["pre_avx"])} ({pct(r["pre_avx"], r["pre_tot"])} %)</td><td class="n">0</td><td class="n">{fmt(r["pre_va"])}</td><td class="n">{fmt(r["pre_vv"])}</td><td class="n">{r["forwards"]}</td></tr>')
        out.append(f'<tr><td>prompt {N}, prefill, FPGA attention, DMA keeps up (est.)</td><td class="n">{fmt(r["pre_tot"])}</td><td class="n">0</td><td class="n">{fmt(r["pre_fpga_avx"])} ({pct(r["pre_fpga_avx"], r["pre_tot"])} %)</td><td class="n">{fmt(r["pre_fpga"])} ({pct(r["pre_fpga"], r["pre_tot"])} %)</td><td class="n">0</td><td class="n">{fmt(r["pre_vv"])}</td><td class="n">{r["forwards"]}</td></tr>')
        out.append(f'<tr><td>prompt {N}, 256 decode steps, CPU attention</td><td class="n">{fmt(r["dec_tot"])}</td><td class="n">{fmt(r["dec_amx"])} ({pct(r["dec_amx"], r["dec_tot"])} %)</td><td class="n">{fmt(r["dec_avx"])} ({pct(r["dec_avx"], r["dec_tot"])} %)</td><td class="n">0</td><td class="n">{fmt(r["dec_va"])}</td><td class="n">{fmt(r["dec_vv"])}</td><td class="n">256</td></tr>')
        out.append(f'<tr><td>prompt {N}, 256 decode steps, FPGA attention, lag 4 tokens (est.)</td><td class="n">{fmt(r["dec_tot"])}</td><td class="n">0</td><td class="n">{fmt(r["dec_fpga_avx"])} ({100.0*r["dec_fpga_avx"]/r["dec_tot"]:.2f} %)</td><td class="n">{fmt(r["dec_fpga"])} ({pct(r["dec_fpga"], r["dec_tot"])} %)</td><td class="n">0</td><td class="n">256</td><td class="n">256</td></tr>')
    out.append('</table></div>')
    return "\n".join(out)

def phase_table():
    out = ['<div class="tw"><table><tr><th>Arm (prompt length)</th><th>QK us</th><th>softmax us</th><th>PV us</th><th>state us</th><th>whole unit us</th><th>units per pass</th></tr>']
    for arm, name in (("disable-8192", "AVX, kill switch, 8192"), ("canon-8192", "AMX canonical, 8192"), ("disable-2048", "AVX, kill switch, 2048"), ("canon-2048", "AMX canonical, 2048"), ("disable-256", "AVX, kill switch, 256"), ("canon-256", "AMX canonical, 256")):
        d = sa[arm]
        st = "in softmax" if arm.startswith("disable") else f'{d["state"]:.3f}'
        out.append(f'<tr><td>{name}</td><td class="n">{d["qk"]:.3f}</td><td class="n">{d["softmax"]:.3f}</td><td class="n">{d["pv"]:.3f}</td><td class="n">{st}</td><td class="n">{d["total"]:.3f}</td><td class="n">{int(d["units"])}</td></tr>')
    out.append('</table></div>')
    return "\n".join(out)

qk_ratio = ph("disable-8192", "qk") / ph("canon-8192", "qk")
pv_ratio = ph("disable-8192", "pv") / ph("canon-8192", "pv")
tot_ratio = ph("disable-8192", "total") / ph("canon-8192", "total")


DECISION_JSON = os.path.expanduser(
    "~/workspace/intel-AMX/exec/attnstats-20260924/decision.json")


def section13():
    """Section 13: the 2026-09-24 decision (one environment variable) and its
    implementation and measurement record. Numbers come from decision.json,
    written by exec/attnstats-20260924/decide.py after the delphi-3bda runs;
    until then the measurement rows say pending."""
    d = {}
    if os.path.exists(DECISION_JSON):
        d = json.load(open(DECISION_JSON))
    pr = d.get("pr", "draft PR (number pending)")
    head = d.get("head", "9b3832eb4b")
    base = d.get("base", "66c7bb8db1")
    verdict = d.get("verdict", "pending: the A/A on delphi-3bda has not finished")
    rows = d.get("rows", [])
    prelim = "" if d.get("final") else " <b>(preliminary: the campaign is still running, rows will change)</b>"
    if rows:
        cells = "".join(
            f"<tr><td>{r['cell']}</td><td>{r['arm']}</td><td>{r['n']}</td><td>{r['tps']}</td>"
            f"<td>{r['sd']}</td><td>{r['delta']}</td><td>{r['note']}</td></tr>" for r in rows)
        table = (f"<p>Rows so far{prelim}:</p><div class=\"tw\"><table><tr><th>Cell</th><th>Arm</th><th>Runs</th>"
                 "<th>TPS (mean)</th><th>sd</th><th>Delta vs base</th><th>Reading</th></tr>"
                 f"{cells}</table></div>")
    else:
        table = ("<p><b>Measurement rows: pending.</b> The chain exec/attnstats-20260924/chain.sh "
                 "builds the head, runs the unit tests, then the cells; decide.py writes the rows.</p>")
    checks = d.get("checks", [])
    checks_html = "".join(f"<li>{c}</li>" for c in checks) if checks else "<li>pending</li>"
    return f"""
<h2 id="decision">13. Decision record (2026-09-24): one environment variable, and what was built</h2>
<p><b>Decision.</b> Every counter and timer of sections 5.1 and 5.2 sits behind one run-time switch, the environment variable TRON_ATTN_STATS (exactly "1" turns collection on, read once per process, the rule of TRON_AMX_DISABLE). No CMake option. jhan's rule for the choice: prefer the environment variable because it is easier to turn on, and fall back to a build option only if the always-compiled hooks have an obvious cost when the variable is unset. Section 9 had put the per-visit tallies behind a build option by the hook-frequency rule. The cost analysis below says the per-visit hook costs one predictable branch on a bool copied once per apply_page_range call, against visits of thousands of cycles, so the measurement decides, not the rule. The per-phase timers of section 6 stay out of this change (lab-build option, unchanged recommendation).</p>
<p><b>Why the environment variable can carry the per-visit hooks.</b> A visit (one apply_page_tok call) costs 2.1 to 2.4 us on the AMX path and 2.8 to 2.9 us on the AVX path at prompt 1024 (2026-09-01 measurement, rows prompt 256 and 2048 of section 6), that is est. 5,800 to 11,200 cycles at 2.7 to 3.9 GHz. With the switch off the hook adds one test of a stack bool per visit and, per apply_page_range call, one byte load and the zeroing of a 64-byte stack tally: est. 1 to 2 cycles per visit, a margin of 60x to 400x below a 1 % change of TPS. In the llama-3.1-8b shape of section 10 the dense AMX visit is 94.6 % of all visits (est.: 32 layers x 8 KV heads x 17 full pages per user per step), so the overhead is diluted by the largest visit type. The one place where the relative overhead is largest, the empty visit (est. 60 to 120 cycles, only under FPGA attention), does not occur in a CPU-attention run. Reviewer precedent points both ways: the page-share counters of PR0 in the same loop are a build option, and the approving reviewers of PR0 asked for exactly the run-time switch with FUSE leaves (issue #4303).</p>
<p><b>What "obvious" means here.</b> The A/A cannot see 0.1 %: at the p1024 cell the same-binary spread of the 2026-09-22 Step E pairs was 0.6 to 0.7 TPS (0.8 to 0.9 %) with 3 repetitions. The acceptance rule, fixed before the runs finished (exec/attnstats-20260924/decide.py): per cell, band = the largest of |base2 - base|, twice the largest per-arm sd, and 0.5 % of the base mean; the head binary with the variable unset must sit inside that band. A loss larger than the band at every cell (both prompt lengths) flips the decision to a build option for the per-visit tallies (the code keeps the environment variable for everything else, as section 9 planned); a loss at one cell only means repeat that cell. The A/A sees no effect below about 1 %, so the record says "inside the band", never "less than 0.1 % measured". Two deterministic checks accompany it: the lock-prefixed instruction count and the size of the apply_page_range instantiations in the two binaries (exec/attnstats-20260924/objdump-check.sh), and the exit-report counts against the closed-form visit model.</p>
<p><b>What was built</b> ({pr}, branch jhan-attn-path-stats, head {head} on main {base}; worktree ~/workspace/ai-runs/tron-attn-stats):</p>
<ul class="tight">
<li>New header h/tron/models/attn_stats.hpp: Note [Attention path stats]; visit_tally (stack, per apply_page_range call); one row per (forward class, attention worker, layer) with visits and K tokens per path and per pass, AVX full-page visits, T2 to T5 in cycles; FPGA K tokens and query passes per layer; forwards, T1 and token jobs by path set per class; JSON renderers; casual FUSE leaves under /model/&lt;id&gt;/attention/ (summary, &lt;class&gt;_totals, &lt;class&gt;_forwards, &lt;class&gt;_layer_&lt;L&gt;, &lt;class&gt;_worker_&lt;W&gt;) whose callbacks hold a weak_ptr; one stderr summary when the model state is destroyed.</li>
<li>apply_page_tok returns a 16-byte struct {{hint, relevant K tokens, path}} instead of the pair; the three exits name their path (amx, empty, avx). apply_page_range copies the switch once per call, tallies per visit behind it, records each token job's path bit, and adds the tally to the worker's own row once per call (single writer, relaxed load-add-store, no lock prefix).</li>
<li>run_attention_job records T2 (busy cycles, exists today) and T3 (wall on worker 0) per job, and T4 as the layer period on worker 0 measured from one attention operation's first job to the next operation's first job (the second minibatch of the same operation starts no period, which the entry-to-entry rule of section 5.2 got wrong). stream_hw_joins times only its wait loop into an accumulator run_joins passes (nullptr when off) for T5 (join_wait_cycles: the loop ends when an FPGA pass or the peer workers' software partials become ready).</li>
<li>prepare_uniform_hw_attention counts FPGA K tokens (inclusive last index + 1 per query) and queries per pass per layer; construct_hw_plan counts token jobs with at least one FPGA pass from the plan's by_job index; model::state::run_forward sets the forward class (decode_like = every token job has a listener) before the workers start and folds the path bits after they finish; full_scheduler::forward times the forward (T1: model forward, logits and listener delivery; scheduler work before and after excluded).</li>
<li>Free perfetto arguments: "layer" on the Attention Ready/Pending span, "n_listeners" on the forward event.</li>
<li>Tests: new t/t_attn_stats.cpp (13 cases: tallies, rows, path sets, timers, the switch rule, class routing, JSON leaves below the FUSE string limit, the exit report, FUSE registration with the weak_ptr rule, last-wins takeover, EAGLE directory), compiled into the t_llama_unit binary so no cost-data row is needed; t_llama_unit's fake-lane apply_page_range case asserts the stats-on tallies (CI-lane coverage of the per-visit hook without AMX); t_amx_dispatch_dtype asserts the amx/avx split against the kernel fakes and gets the two apply_page_range arguments main's copy lacks; the direct callers follow the new return type and the run_joins / stream_hw_joins parameters.</li>
<li>Review rounds after the first commit (workflows wf_58133db0-409 and wf_93caf57d-93e): FPGA counters got the forward-class dimension; every hook returns when the switch is off; FUSE registration is last-wins with one log line; the per-worker path bits are hoisted per call; the kill-switch identity was corrected (below); the T5 name lost its "hw" prefix; the duplicate frequency accessor was dropped for the existing get_cpu_freq(); the C++ guide's named values and braces were applied to the added lines (exceptions listed in the PR body).</li>
<li>Not built (unchanged from section 9): the phase timers (section 6), the AVX-visit reasons, hollow tile regions, Q packs per call, DMA lag, HBM fallback, prefill accounting, inter-token latency (section 7). The page-share counters of PR0 keep their build option.</li>
</ul>
<p><b>Measurement record</b> (delphi-3bda, our half, runtron, CPU attention, qwen-3-4b tp2, 8 users, 256 generated tokens; arms: base and base2 = main binary, variable unset; head = branch binary, variable unset; headon = branch binary, TRON_ATTN_STATS=1; headkill = headon with TRON_AMX_DISABLE=1):</p>
{table}
<p><b>Cross-checks:</b></p>
<ul class="tight">{checks_html}</ul>
<p class="take">Verdict: {verdict}</p>
"""

HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AMX path counters</title>
<style>{CSS}</style></head><body><main>
<h1>Counters for the AVX / AMX / FPGA attention paths: what to count, where, and what the answers already are</h1>
<p class="sub">For jhan. Date 2026-09-22, updated 2026-09-24 with the decision record (section 13). Source revision: tron main 0a51385e95 (read-only worktree ~/workspace/ai-runs/tron-counters-ro), the tree that contains PR 3879 (merged 2026-09-15). Verification: a 30-agent read / refute / design / judge workflow (wf_a8e982c8-1b8) produced 411 code claims with file:line citations, of which 327 hold, 82 hold with a qualifier and 2 were refuted and dropped. Every number below is either computed by exec/counter-20260922/closed_form.py (marked est.) or copied from a named measurement file. Generated by exec/counter-20260922/gen_counter.py.</p>

<div class="short"><h2 style="margin-top:0;border:0">Short version</h2>
<p>Prefill runs attention for every prompt token, so the prefill counter is the largest one, not a useless one (section 1). One decode token uses several paths at once, one choice per 64-token page of cached keys, so the counter must count key tokens scored per path, not tokens per path (section 2). The 2026-09-24 decision puts every counter and timer of the design behind one environment variable, TRON_ATTN_STATS, built and measured as recorded in section 13, and keeps the 2026-09-01 probe that timed the QK, softmax and PV phases of attention as a lab-build option (section 6).</p></div>

<nav class="toc" aria-label="Table of contents"><h2>Contents</h2>
<ol>
<li><a href="#words">Words used here</a></li>
<li><a href="#q1">1. Prefill: not one token, and not AMX-only</a>
  <ol><li><a href="#q1b">1.1 Why a given prompt token still runs attention and the FFN</a></li></ol></li>
<li><a href="#q2">2. Decode: the path is chosen per page visit, not per token</a>
  <ol><li><a href="#q2a">2.1 What is closed-form and what is not</a></li></ol></li>
<li><a href="#q3">3. Layers: the same path in every layer only for uniform models</a></li>
<li><a href="#today">4. What tron measures today, and the gaps</a></li>
<li><a href="#design">5. Proposed counters and timers (v1)</a>
  <ol><li><a href="#counters">5.1 Counters</a></li><li><a href="#timers">5.2 Timers</a></li></ol></li>
<li><a href="#phases">6. Timing QK, the softmax step and PV per path</a>
  <ol><li><a href="#phases-rec">6.1 Recommendation for per-phase timers</a></li></ol></li>
<li><a href="#more">7. Other counters worth adding</a></li>
<li><a href="#gating">8. Gating and reporting: the decision to make</a></li>
<li><a href="#control">9. Which switch for which counter: build option, environment variable or perfetto</a></li>
<li><a href="#measure">10. Measurements to run first, and acceptance tests</a></li>
<li><a href="#open">11. Open points (Insufficient data)</a></li>
<li><a href="#sources">12. Sources</a></li>
<li><a href="#decision">13. Decision record (2026-09-24): one environment variable, and what was built</a></li>
</ol></nav>

<h2 id="words">Words used here</h2>
<dl class="gloss">
<dt>tron, runtron, rinzler</dt><dd>tron is the inference program; runtron is its command-line tool; rinzler is the production server, started by platformd as rinzler@N units.</dd>
<dt>AMX, AVX</dt><dd>AMX = Intel Advanced Matrix Extensions (tile-matrix instructions). AVX = the AVX-512 vector instructions used by the software attention loop (the "dotter" loop in apply_page_tok). The kill switch TRON_AMX_DISABLE=1 turns AMX off at run time; the CMake option TRON_AMX_DISPATCH compiles the AMX kernels in (default OFF; no preset sets it at this revision, PR #4505 adds it to the deb preset).</dd>
<dt>AoF, FPGA attention, HW attention</dt><dd>Three names for the same thing: attention on the FPGA card. Controlled by USE_HW_ATTN (unset = on for ingested models such as qwen-3-4b, off for the handwritten llama plugin; 0 = off; N &gt; 0 = on and raises the engagement point).</dd>
<dt>KV page, HW page, shard, GOF</dt><dd>KV page = 64-token block of the key/value cache (page::page_size). HW page = 128 tokens (POS_PER_PAGE), the FPGA's unit. Shard = 1024 tokens of FPGA memory (HBM) on one card. GOF = group of four tokens, the unit copied to HBM by DMA.</dd>
<dt>engagement point</dt><dd>Sequence position 127 (MIN_TOK_IDX_FOR_HWATTN). A query below it is always scored on the CPU; the first shard engages once 128 tokens (32 GOFs) are resident.</dd>
<dt>visit, K tokens scored, dot products</dt><dd>A visit is one apply_page_tok call = one query token x one KV page x one KV head. "K tokens scored" is the number of K rows the visit multiplied against the query (AMX: always 64; AVX: 1 to 64). Dot products = K tokens scored x kv_mul (query heads per KV head, 4 on the AMX-eligible models); tron's planner calls this k_dot_products.</dd>
<dt>dense page</dt><dd>A page that passes is_dense_amx_page: 64 active entries, the query sees all of them through one mask range, and the whole page is inside the sliding window. Only dense pages take AMX.</dd>
<dt>ready / pending pass</dt><dd>Ready = pages whose K/V were written in earlier forwards; pending = pages written in this forward (the current prompt chunk, or the new decode token). Each attention job runs the ready pass, waits for upstream K/V, then runs the pending pass.</dd>
<dt>forward, decode step, prefill, prompt chunk</dt><dd>forward() = one model run for all users' pending token jobs. A decode step is a forward whose jobs are one new token per user. Prefill = the forwards over the prompt, fed 128 tokens per user per forward (TRON_PER_USER_PROMPT_CHUNK_LIMIT).</dd>
<dt>attention worker, minibatch, join</dt><dd>Attention runs on n_attn_workers threads, each owning a slice of (KV head, page range) sections; their partial results (v*, s*, m*) and the FPGA partial are folded by the join. Ingested plugins run one minibatch; the llama plugin can split a forward in two.</dd>
<dt>rdtsc, perfetto, FUSE stats</dt><dd>rdtsc = the CPU cycle counter (hardware::system::rdtsc(), converted by cycles_to_ns). perfetto = the trace library tron uses for spans ("Attention Ready", "forward", "launch_hw_attn"). FUSE stats = tron's live statistics tree, mounted as files under /var/run/rinzler/N/ in production.</dd>
<dt>PR0, PR 3879, PR 4424, issue #4303</dt><dd>PR0 = #4267, the page-share counters (compile-time option TRON_PAGE_SHARE_COUNTERS, exit report). PR 3879 = the canonical AMX attention kernel, merged. PR 4424 = VNNI K layout (open; shifts the same lines). Issue #4303 = the approving reviewer's request to publish counters as FUSE stats with an env-var opt-in.</dd>
<dt>est.</dt><dd>An estimate or a closed-form computation, not a measurement.</dd>
</dl>

<h2 id="q1">1. Prefill: not one token, and not AMX-only</h2>
<div class="wrong"><p><b>Premise in the question:</b> "prefill tokens: only the first token, and it has to be on AMX no matter what AoF is enabled or not, so this counter may be useless."</p>
<p><b>What the code does:</b> every prompt token is a query that runs attention and the FFN at every layer, because its K/V at layer L are computed from its layer L-1 output (section 1.1). Only the last chunk requests logits, which is why one token comes out [src/tron/generation/context.cpp:48-50].</p></div>
<ul class="tight">
<li>The prompt is fed 128 tokens per user per forward [h/libtron.hpp:196-204]. Prompt 1024 takes 8 forwards, prompt 8192 takes 64 [src/tron/generation/context.cpp:41-42, 71-75].</li>
<li>Under CPU attention, the pages written by earlier forwards are ready and dense, so they take AMX. The current chunk's own pages carry one mask range per query token (each prompt token is a query event), so the dense test <code>pg.at_offset(63) &lt; range.tok_hi</code> fails and they run on the AVX dotter [h/tron/models/self_attention.hpp:1488-1491, 1609-1610; src/tron/models/ranged_mask.cpp:42-49, 64-66]. The first chunk of a fresh prompt is 100 % AVX.</li>
<li>Under FPGA attention, queries at position 127 and above attend the HBM-resident prefix on the card, in 4-token GOF steps, once 128 tokens are resident [h/libpos.hpp:90; h/tron/gof.hpp:33-37; h/tron/models/model.hpp:2511-2519]. The own-chunk causal triangle and any page whose DMA has not finished stay on the CPU. On that CPU remainder the AMX dispatch does not look at the FPGA flag; it looks at query_visible, which under FPGA attention means sw_required, so a dense DMA-lagging page still takes AMX [self_attention.hpp:1406-1407, 1746-1747].</li>
<li>Work scale (est., single user, no prefix cache): prompt 1024 prefill scores {fmt(r1["pre_tot"])} K tokens per layer and KV head, versus {fmt(r1["dec_tot"])} for all 256 decode steps together ({r1["pre_tot"]/r1["dec_tot"]:.2f}x). At prompt 8192 the ratio is {r8["pre_tot"]/r8["dec_tot"]:.2f}x. Prefill is the largest attention workload of a run, and its AMX share ({pct(r1["pre_amx"], r1["pre_tot"])} % at prompt 1024 under CPU attention) is where the AMX gain in time-to-first-token comes from.</li>
</ul>
<div class="fig">{fig_prefill()}</div>
<p class="cap">Figure 1. Prefill of a 512-token prompt (4 forwards of 128 tokens), one user, per layer and KV head. Each row is one forward; its query tokens run top to bottom. The rectangle on the left is the K/V of earlier forwards (ready pages); the triangle is the causal part of the chunk's own tokens (pending pages). Panel A: ready pages are dense and take AMX; the own chunk takes AVX. Panel B: the resident prefix goes to the FPGA; the thin orange strip marks pages whose DMA had not completed at plan time, which the CPU scores with AMX because they are dense (width est., not measured). Forward 1 is all AVX in both modes. Drawn to scale in K position; the DMA lag is schematic.</p>
<p class="take">Takeaway: a prefill counter answers a question no other counter can: how much of the prefill went to the FPGA versus AMX versus AVX, and how much DMA lag pushes onto the CPU.</p>
<h3 id="q1b">1.1 Why a given prompt token still runs attention and the FFN</h3>
<p>The clarification (jhan, 2026-09-22): "prefill processes every prompt token because we need their K/V cache, but those tokens are given, so there is no attention or FFN involved; only the one generated token involves attention." The K/V cache makes this impossible, layer by layer.</p>
<ul class="tight">
<li>The K and V saved for token i at layer L are a linear map of token i's hidden state at the input of layer L. save_k_impl computes them for every token job of the minibatch from that layer's buffers [h/tron/models/model.hpp:2745-2760].</li>
<li>That hidden state is the output of layer L-1 for token i: the residual stream after attention over tokens 0..i and after the FFN of layer L-1. Only at layer 0 does the K/V follow from the token id alone (the embedding).</li>
<li>So knowing the prompt saves exactly one computation per token: the logits projection and the sampling. It does not save attention or the FFN at any layer, because the K/V of the deeper layers do not exist until those ran.</li>
<li>tron does exactly this. A prompt token without K/V becomes a token job with do_kv = 1 [h/tron/scheduler/full.hpp:2014-2030]. The layer loop runs, for every token job of the forward, the attention (maybe_launch_wo waits for it), the FFN (ffn_state.run) and the next layer's K/V jobs [h/tron/plugins/llama.hpp:656-700]. Only tokens with a logits listener, the last chunk, reach the logits [src/tron/generation/context.cpp:48-50]. The plan document defines it the same way: "Query - is a token that has logits requested (generation) or is missing KV cache (parse and gen)" [doc/hw-kv-rules.md:4].</li>
</ul>
<div class="fig">{fig_kv_chain()}</div>
<p class="cap">Figure 1b. Dependency chain for a 4-token prompt and 3 layers. Every blue cell runs for every prompt token: attention over the tokens up to and including itself (reading the green K/V arrows of the same layer) and the FFN, which produces the input, and therefore the K/V, of the next layer. The dashed cells are the only work a given token skips.</p>
<p>Two measurements agree with the code reading:</p>
<ul class="tight">
<li>The 2026-08-19 page-share counters (the PR0 counters, then called p1_share_counters) counted an average of 110.9 query tokens per page visit during prefill, against 1.02 in decode. Those 110.9 queries per visit are prompt tokens attending to the same page in one forward [memory note amx-tron-softattn-project, section "P1 SHARING MEASURED"].</li>
<li>Time to first token at prompt 8192 on qwen-3-4b: 15,764 ms with the AVX dotter, 6,929 ms with the canonical AMX kernel on the CPU-attention build (warm cells), and 6,743 ms cold with attention on the FPGA [CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html, campaigns q4b-swattn-20260919 and q4b-fpga-20260921]. An attention kernel or an attention card cannot change the time to first token unless prefill runs attention for the prompt tokens.</li>
</ul>
<p class="take">Takeaway: prefill is N queries of attention plus N passes through every FFN, not one. What the known prompt saves is N-1 logits projections.</p>

<h2 id="q2">2. Decode: the path is chosen per page visit, not per token</h2>
<div class="wrong"><p><b>Premise in the question:</b> "out of 256 generated tokens, how many are generated by the AVX path, AMX path or AoF path? This can be calculated."</p>
<p><b>What the code does:</b> apply_page_tok decides per (query token, KV page, KV head) whether the pair takes AMX (dense page), the AVX dotter (everything else) or nothing (the FPGA owns the range), and the join folds the FPGA partial and the CPU partial into one output [self_attention.hpp:1746-1768, 1800-1852; model.hpp:2503-2519]. One decode token therefore uses a set of paths.</p></div>
<div class="fig">{fig_decode()}</div>
<p class="cap">Figure 2. One decode query at context 1100 (prompt 1024 plus 76 generated tokens), one layer, one KV head, drawn to scale in K position. Row A, CPU attention: 17 full 64-token pages are dense and take AMX; the 12-token tail page (the pending page, written in this forward) takes AVX. Row B, FPGA attention: the card scores the HBM-resident prefix up to the last complete GOF at plan time (here 1096, est. with a 4-token lag); the CPU scores the remaining 4 tokens on AVX; no full CPU page exists, so AMX gets no work in steady-state decode. Positions below 127 are scored on the CPU only when the query itself is below 127.</p>
<h3 id="q2a">2.1 What is closed-form and what is not</h3>
<ul class="tight">
<li>Under CPU attention, at context N (query at position N-1): floor(N/64) full pages on AMX, N mod 64 tokens on AVX, one visit each per KV head [self_attention.hpp:1601-1611]. In 63 of 64 steps the token's path set is {{AMX, AVX}}; when N mod 64 == 0 the pending page is full and, for a single-user sequence with one mask range, should be dense and take AMX (likely, not yet verified by a run: 4 of the 256 steps at prompt 1024).</li>
<li>Under FPGA attention the CPU/FPGA boundary B is captured at plan time from asynchronous DMA completion [model.hpp:2503-2507; h/tron/scheduler/full.hpp:2756-2803]. It lags the newest token by at least one GOF, needs 32 complete GOFs before the first shard engages, and a shard whose HBM allocation failed falls back to the CPU for all 1024 tokens (counted today only per shard in the sw_fallback_total leaf) [src/tron/gof.cpp:73-79; src/rinzler.cpp:4271]. Nothing in the code fixes B for a given N, so the FPGA share must be measured.</li>
<li>Two more things that only a measurement shows: prefix-cache branch points inside a page split the page's mask range and force AVX for that page, and USE_HW_ATTN=N raises the engagement point (N=128 gives 255, rounded to HW pages of 128) [src/tron/models/hw_attn_config.cpp:24-30].</li>
<li>The steady-state decode picture under FPGA attention (row B) predicts zero AMX visits. That matches the measured decode result at prompt 1024 (no AMX gain under AoF, 2026-09-21/22 page) and makes the warm long-prompt decode gains (+2 to +14 %, n=1) a question the counter settles: they need pages that are not HBM-resident and are scored on the CPU as dense pages.</li>
</ul>
<div class="fig">{chart_shares()}</div>
<p class="cap">Chart A. Closed-form share of K tokens scored per path (est., exec/counter-20260922/closed_form.py): one user, KV page 64, prompt chunk 128, no prefix cache, no HBM exhaustion; the FPGA rows assume DMA keeps up (prefill: the previous chunks are resident at plan time; decode: a 4-token lag). Prefill at prompt 1024 is {pct(r1["pre_amx"], r1["pre_tot"])} % AMX under CPU attention because the own-chunk triangle is {pct(r1["pre_avx"], r1["pre_tot"])} % of the work; decode is {pct(r1["dec_amx"], r1["dec_tot"])} % AMX because only the tail page is AVX. Under FPGA attention AMX gets nothing in both phases unless DMA lags.</p>
{share_table()}
<p class="cap">Table 1. The numbers behind Chart A. Visits are per KV head (an 8-KV-head model makes 8 visits per (query, page)). "forwards" = number of forward() calls. The AoF rows are the ideal case; measured values will differ by the DMA lag and by HBM fallbacks.</p>
<p class="take">Takeaway: report "K tokens scored per path" per decode step and per prefill, plus a per-token path-set table (how many of the 256 tokens used {{FPGA, AVX}}, {{AMX, AVX}}, {{AMX}} ...). That is the well-posed form of the question.</p>

<h2 id="q3">3. Layers: the same path in every layer only for uniform models</h2>
<div class="ok"><p><b>Premise in the question:</b> "when a token is generated through a path at one layer, it took the same path at all layers."</p>
<p><b>Answer:</b> yes for llama-3.1-8b, llama-3.3-70b, mixtral-8x7b and qwen-3-4b; no for gpt-oss-120b, gemma-4 and EAGLE draft models.</p></div>
<ul class="tight">
<li>Everything that decides the split is computed once per forward and shared by all layers: the ranged mask with its software/hardware boundary, the hw_plan (one per minibatch, reused by every operation), the page table with page.count(), the pending/ready set and the engagement point [model.hpp:2242-2248, 2503-2519; self_attention.hpp:1103-1118].</li>
<li>The per-operation decision compute_operation_uses_hw excludes sliding-window layers, EAGLE models, non-candidate kernels and operations whose scale is not the configured hardware scale [self_attention.hpp:487-495]. In gpt-oss-120b the sliding-window layers never use the FPGA and the window truncates the page set, so the path differs by layer.</li>
<li>AMX eligibility is per attention geometry (head 128, kv_mul 4, bf16 activations) [h/tron/kernels/amx_attn_iface.hpp:148-165]. Models with one geometry are uniform; gemma-4 has several.</li>
<li>No per-layer cap on FPGA attention was found: cfg.max_layers is the loaded layer count, and kv_slot_extent is the index of the last full-attention layer plus one [model.hpp:1440-1530].</li>
</ul>
<div class="tw"><table><tr><th>Model</th><th>head size</th><th>Q heads / KV heads = kv_mul</th><th>window layers</th><th>FPGA attention default</th><th>AMX eligible</th><th>same path in every layer</th><th>confidence</th></tr>
<tr><td>llama-3.1-8b (handwritten llama.hpp)</td><td class="n">128</td><td>32 / 8 = 4</td><td>none</td><td>off (USE_HW_ATTN unset)</td><td>yes</td><td>yes</td><td>verified in source</td></tr>
<tr><td>qwen-3-4b (ingested)</td><td class="n">128</td><td>32 / 8 = 4</td><td>none</td><td>on</td><td>yes</td><td>yes</td><td>geometry from a test comment and the HF config, not from a header in this checkout</td></tr>
<tr><td>mixtral-8x7b</td><td class="n">128</td><td>32 / 8 = 4</td><td>none</td><td>off</td><td>yes</td><td>yes</td><td>verified in source (llama.hpp:1584-1597)</td></tr>
<tr><td>llama-3.3-70b</td><td class="n">128</td><td>64 / 8 = 8</td><td>none</td><td>off</td><td>no (kv_mul 8)</td><td>yes (AVX or FPGA only)</td><td>verified in source</td></tr>
<tr><td>qwen-3-32b</td><td class="n">128</td><td>64 / 8 = 8</td><td>none</td><td>on</td><td>no (kv_mul 8)</td><td>yes</td><td>test comment</td></tr>
<tr><td>qwen3-30b-a3b (ingested)</td><td class="n">128 (est.)</td><td>32 / 4 = 8 (est.)</td><td>none</td><td>on</td><td>no (est.)</td><td>yes</td><td>4 KV heads from t/t_hwattention_batch.cpp:59-60; Q heads not in the checkout</td></tr>
<tr><td>gpt-oss-120b</td><td class="n">64</td><td>64 / 8 = 8</td><td>alternating sliding-window layers</td><td>on for full layers only</td><td>no (head 64)</td><td>no</td><td>window pattern from the HF config, not in the checkout</td></tr>
<tr><td>gemma-4</td><td>several</td><td>several</td><td>yes</td><td>-</td><td>per geometry</td><td>no</td><td>heterogeneous_kv_cache.hpp</td></tr>
</table></div>

<h2 id="today">4. What tron measures today, and the gaps</h2>
<div class="tw"><table><tr><th>Instrument</th><th>What it gives</th><th>What it does not give</th><th>Where</th></tr>
<tr><td>PR0 page-share counters (TRON_PAGE_SHARE_COUNTERS, exit report)</td><td>page visits, query tokens per visit, pending-pass visits, a 7-slot histogram</td><td>no AMX / AVX tag (the hook increments the same counter for both returns), no FPGA work, no time, never prints under platformd (API stop, no normal exit)</td><td>h/tron/kernels/page_share_counters.hpp; hooks self_attention.hpp:1426-1428, 1539-1546, 1566-1568</td></tr>
<tr><td>perfetto spans</td><td>"forward" per step (n_token_jobs, n_tokens); "Attention Ready/Pending" per section with relevant q tokens, dot products, pages; "hwattention" prepare / launch / join wait; Save K / Save V with a layer argument</td><td>no path tag, no layer id on the section span, no per-layer span in llama.hpp; needs a trace session</td><td>model.hpp:1622; self_attention.hpp:1389-1398, 539, 642, 1078; README.perfetto.md; repo skill .agents/skills/analyze-tron-perfetto-trace</td></tr>
<tr><td>attention busy time (rdtsc)</td><td>per attention worker per job: both passes plus the join, excluding the upstream K/V wait</td><td>consumed only by attn_time_estimator (thread-split heuristic); never printed, not per layer, not wall time</td><td>self_attention.hpp:774-806; h/tron/plugins/llama.hpp:774-775</td></tr>
<tr><td>runtron log lines</td><td>per request: prompt parse rate, generation rate, TTFT, TTLT</td><td>no per-token time (LOG_TOKEN_TIMES is commented out)</td><td>h/runtron/stream_generate.hpp:249-256, 759-761</td></tr>
<tr><td>rinzler FUSE leaves</td><td>tokens/s, avg_ttft_ms, sw_fallback_total per HBM shard, allocator free_total / free_max</td><td>no inter-token latency, no per-query fallback</td><td>src/rinzler.cpp:4271; README.stats.md</td></tr>
<tr><td>EXE.AMX_BUSY perf event (external)</td><td>proof that AMX ran, cycles with tiles busy, per process or thread</td><td>no attribution to pages, layers or phases</td><td>perf stat -e cpu/event=0xb7,umask=0x02/ on the engine pid (validated 2026-09-17)</td></tr>
<tr><td>2026-09-01 phase probe (fence branch, TRON_ATTN_PHASE=1, not merged)</td><td>units by path (AMX / dotter / empty), K tokens on the dotter, pages, ranges, Q packs, and rdtsc cycles per phase: QK, softmax, PV, state, Q pack, tile region, range, ready pass, pending pass, upstream wait, joins, barrier</td><td>exported as worker-0 stamps for one experiment; no FPGA work; not on main</td><td>~/workspace/ai-runs/tron-fence-amx @ 8fd1e7798d, self_attention.hpp:223-260 (attn_phase)</td></tr>
</table></div>
<p class="take">Gap: no instrument on main says which path a visit took, how much the FPGA scored, or how long attention, a layer or a decode step took. The probe on the fence branch already has most of the CPU-side counters.</p>

<h2 id="design">5. Proposed counters and timers (v1)</h2>
<div class="fig">{fig_hooks()}</div>
<p class="cap">Figure 3. Hook sites. The solid chain is one attention worker: forward() runs the plugin, which runs run_attention_job per (layer, minibatch), which runs apply_page_range per (KV head, page range, pass), which calls apply_page_tok per (query, page). The three return sites of apply_page_tok are the only zero-ambiguity places to tag the path: the AMX return follows apply_dense_amx_page, the AVX return follows the dotter loop, and the empty return means the range belonged to the FPGA or fell outside the window. The FPGA work is counted on the main thread where the plan is programmed. Timers are same-thread rdtsc deltas.</p>
<h3 id="counters">5.1 Counters</h3>
<p class="sub">Section 9 says, for every row here and in sections 5.2, 6 and 7, whether it belongs behind the build option, the environment variable or a perfetto argument.</p>
<div class="tw"><table><tr><th>Counter</th><th>Unit</th><th>Path</th><th>Hook (main 0a51385e95)</th><th>Bucket</th><th>What it answers</th></tr>
<tr><td>amx_visits, amx_k_tokens</td><td>visits; K tokens (64 per visit)</td><td>AMX</td><td>self_attention.hpp:1768, inside the AMX branch before <code>return {{int(page::page_size), range_hint}};</code></td><td>per (worker, layer), ready / pending, forward class</td><td>how much CPU attention work the AMX kernel served; must read 0 with TRON_AMX_DISABLE=1</td></tr>
<tr><td>avx_visits, avx_k_tokens</td><td>visits; K tokens (relevant_k_tokens)</td><td>AVX</td><td>:1852 before <code>return {{relevant_k_tokens, range_hint}};</code></td><td>same</td><td>how much ran on the dotter: tail pages, prefill own-chunk pages, boundary pages, everything when AMX is off</td></tr>
<tr><td>avx_full_page_visits</td><td>visits with relevant_k_tokens == 64</td><td>AVX</td><td>:1852, same block</td><td>same</td><td>AMX-eligible volume that did not take AMX; in the kill-switch arm it must equal amx_visits of the AMX-on arm (same-binary A/B check)</td></tr>
<tr><td>empty_visits</td><td>visits</td><td>none</td><td>:1820 before <code>return {{0, range_hint}};</code></td><td>same</td><td>page walks that did no software work (FPGA-owned range, window-excluded page): pure overhead count</td></tr>
<tr><td>fpga_k_tokens, fpga_query_passes</td><td>K tokens (tok_ix + 1 per (pass, query)); pairs</td><td>FPGA</td><td>:600 in prepare_uniform_hw_attention, after <code>tok_ix_arr[qi] = relative_hw_tok_ix(...)</code>, behind the :540-542 gate</td><td>per layer</td><td>how much of each query's context the card scored in this layer; the third share</td></tr>
<tr><td>fpga_queries</td><td>token jobs</td><td>FPGA</td><td>model.hpp:2519 next to <code>queries.push_back(hw_query{{...}})</code></td><td>per forward</td><td>distinct token jobs with FPGA work (each query is in at most one hw_plan_entry, ranged_mask.cpp:71-73)</td></tr>
<tr><td>token_jobs[class][path set]</td><td>token jobs</td><td>bitmask FPGA / AMX / AVX</td><td>bits per visit after the apply_page_tok call (:1539-1546), keyed by token_job_id; FPGA bit at model.hpp:2519; folded after <code>plugin_state.run(q_batches);</code> (model.hpp:1706)</td><td>per class (decode-like, prompt / mixed)</td><td>your question 2 in token form: of the generated tokens, how many used {{AMX, AVX}}, {{FPGA, AVX}}, {{FPGA, AMX, AVX}}, {{AVX}} ...</td></tr>
<tr><td>forwards[class]</td><td>forward() calls</td><td>-</td><td>full.hpp:1993-2004 around <code>state.forward(...)</code> and <code>metrics.forward_passes++</code></td><td>per class</td><td>denominator: decode steps versus prefill or mixed forwards; class = decode-like when listener_notifications.size() == token_jobs.size() (a proxy: a one-token final chunk counts as decode)</td></tr>
<tr><td>attn_jobs</td><td>run_attention_job calls</td><td>-</td><td>:806-807 before <code>return attn_elapsed;</code></td><td>per (worker, layer)</td><td>denominator for time per attention job</td></tr>
</table></div>
<h3 id="timers">5.2 Timers</h3>
<div class="tw"><table><tr><th>Timer</th><th>Start</th><th>End</th><th>Definition</th><th>Bucket</th></tr>
<tr><td>T1 forward_wall</td><td>full.hpp:1993 before <code>state.forward(...)</code></td><td>after it returns (:1995)</td><td>wall time of one forward on the work-queue thread: minibatch build, plan, all layers, logits, listener delivery. In the decode class this is the decode-step time for all users in the batch. Same span as the perfetto "forward" slice.</td><td>per class: sum, count, max, log2 histogram</td></tr>
<tr><td>T2 attn_busy</td><td>:774 <code>attn_elapsed -= rdtsc()</code> (exists)</td><td>:806 (exists); record before :807</td><td>busy time of one worker for one job: both passes plus the join. Includes the FPGA join wait (:796), excludes the upstream K/V wait (:784) and the Q wait (:765-767).</td><td>per (worker, layer); sum over workers per layer</td></tr>
<tr><td>T3 attn_wall_w0</td><td>:755 entry of run_attention_job, worker 0</td><td>:806</td><td>wall time of the attention operation as worker 0 sees it, waits included; the per-layer attention time histogram you asked for</td><td>per layer: sum, count, log2 histogram</td></tr>
<tr><td>T4 layer_period_w0</td><td>:755, worker 0, layer L</td><td>:755, worker 0, layer L+1</td><td>entry-to-entry interval = wall time of one whole layer (attention of L plus the main thread's matmuls and FFN of L+1 that worker 0 waits for). The last layer's FFN and the logits fall outside. Ingested plugins have no layer loop, so this is the plugin-independent layer clock.</td><td>per layer</td></tr>
<tr><td>T5 hw_join_wait</td><td>around the poll loop in stream_hw_joins after <code>if (progressed) continue;</code> (:1075)</td><td>same loop (:1078 span)</td><td>CPU time an attention worker spends waiting for FPGA pass completion; splits T2 into compute and waiting on the card</td><td>per (worker, layer)</td></tr>
</table></div>
<ul class="tight">
<li>All deltas are same-thread rdtsc, converted with cycles_to_ns [h/system/system.hpp:267-274]; never subtract a worker timestamp from a main-thread timestamp (the scheduler avoids cross-core skew for the same reason, src/system/system.cpp:1746-1750).</li>
<li>For the llama plugin a main-thread span per (layer, minibatch) is also available at the layer loop [h/tron/plugins/llama.hpp:652-695]; for ingested plugins key everything on operation.binding.model_layer.</li>
<li>Tallies are plain integers per apply_page_range call, added once per call into rows indexed [attention worker][layer] that only the owning worker writes; the report sums them. This is the one change to the PR0 shape, and it removes the shared-cache-line fetch_add per call.</li>
<li>Report header: amx_compiled (#ifdef TRON_AMX_DISPATCH), amx_available (amx_attn_h128g4::available()), n_kv_heads, kv_mul, number of FPGA layers. Without it a zero AMX count is misread: the nightly deb has no AMX code at all until PR #4505 lands.</li>
<li>Self-checks to print: (amx_k_tokens + avx_k_tokens) x kv_mul == the planner's k_dot_products per section (except EAGLE and window skips) [self_attention.hpp:1396-1397; model.hpp:2426]; kill-switch arm: amx_visits == 0 and avx_full_page_visits == the AMX-on arm's amx_visits; EXE.AMX_BUSY &gt; 0 if and only if amx_visits &gt; 0.</li>
<li>apply_page_tok gets one required trailing pointer parameter (nullptr when off); the direct test caller t/t_llama_unit.cpp:2136-2140 passes nullptr. No default argument (PR 1 review removed one).</li>
</ul>

<h2 id="phases">6. Timing QK, the softmax step and PV per path (your follow-up question)</h2>
<p>Yes, and it was done once. The 2026-09-01 single-attention measurement put rdtsc stamps at exactly those boundaries inside apply_dense_amx_page and the dotter loop, and ran three arms (AVX kill switch, canonical AMX, mirror AMX) at prompts 256, 2048 and 8192 with a forced 510-token generation on delphi-3bda [exec/results/single-attn-20260901/summary.json; probe commit 8fd1e7798d, self_attention.hpp:223-260]. The four phases and their code sites on main:</p>
<div class="tw"><table><tr><th>Phase</th><th>AMX path (apply_dense_amx_page)</th><th>AVX path (apply_page_tok dotter)</th><th>FPGA path</th></tr>
<tr><td>QK (S = Q K^T over one 64-token page)</td><td>qk_rowmajor_128x4 [self_attention.hpp:1654]</td><td>per K token, dotter dot products for the 4 heads [:1800-1815]</td><td>inside the card command; the host sees launch to completion only</td></tr>
<tr><td>softmax step (scale or softcap, max, exp, sum, correction)</td><td>[:1659-1672]</td><td>[:1822-1836]</td><td>inside the card; the join re-applies the host scale</td></tr>
<tr><td>PV (P V)</td><td>weights_times_v_128x4 [:1680]</td><td>page.scaled_v [:1840-1848]</td><td>inside the card</td></tr>
<tr><td>state update (v*, s*, m*)</td><td>[:1685-1700]</td><td>folded into the same loop as the softmax step [:1837-1849]</td><td>join_page_ranges on the CPU</td></tr>
</table></div>
<div class="fig">{chart_phases()}</div>
<p class="cap">Chart B. Measured microseconds per unit (one query x one KV page x one KV head) by phase, prompt 8192, worker 0, 2026-09-01, delphi-3bda [exec/results/single-attn-20260901/summary.json]. The AMX kernels cut QK by {qk_ratio:.2f}x and PV by {pv_ratio:.2f}x; the whole unit is {tot_ratio:.2f}x faster ({ph("disable-8192","total"):.2f} to {ph("canon-8192","total"):.2f} us). The softmax step and state update are 0.11 to 0.31 us, 4 % of an AVX unit and 7-12 % of an AMX unit. The AVX probe folds the state update into the softmax phase.</p>
{phase_table()}
<p class="cap">Table 2. All three prompt lengths. At prompt 256 the pages are cache-resident and the AMX unit is {ph("canon-256","total"):.2f} us; at 8192 QK and PV are memory-limited and the unit grows to {ph("canon-8192","total"):.2f} us. Fixed per-operation cost (joins plus barrier) was 9 to 13 us per attention operation, 320 to 480 us per token, larger than the whole page loop at prompt 256 (memory note single-attention-measurement).</p>
<h3 id="phases-rec">6.1 Recommendation for per-phase timers</h3>
<ul class="tight">
<li><b>Keep them as a lab-build option, not in the production counter.</b> A phase timer needs 4 rdtsc reads per visit. One read costs 7.25 ns on this workstation (AMD Ryzen 9 9950X, 1e8 reads, exec/counter-20260922/rdtsc_cost.c); on delphi-3bda it is unmeasured (est. 10-30 ns, Intel documents rdtsc at about 20-40 cycles). Four reads add about 30-120 ns to a 2.9 us AMX unit (1-4 %, est.), and the 2026-09-01 probe measured 0-5 % overhead on the per-token wall. That is acceptable for an experiment and not for the counter that ships in every build.</li>
<li>rdtsc is not a serializing instruction, so sub-microsecond phase boundaries blur under out-of-order execution; rdtscp or lfence+rdtsc fixes the order at a higher cost (13.8 and 12.2 ns per read here). The 2026-09-01 numbers used plain rdtsc and phases covered 83-98 % of the worker wall; treat the per-phase split as accurate to a few percent, not better.</li>
<li>Promote the fence-branch probe to main as a second compile-time option (for example TRON_ATTN_PHASE_TIMERS, default OFF) that reuses the v1 counter rows and adds cycles per phase per path. Its counter set (units_amx, units_dotter, units_empty, k_tokens_dotter, pages, ranges, qpacks, cyc_region) is the same as section 5.1 minus the FPGA side, so the two options share one header.</li>
<li>For the FPGA, per-phase time is Insufficient data from the host: QK, softmax and PV run inside one card command. What the host can measure is the pass latency from launch_hw_attn to the completion callback (attn_launcher_cb, self_attention.hpp:680) and the CPU join wait (T5). Per-phase card timing would need the FPGA team's on-card counters.</li>
<li>Cheaper cross-check with no code: perf stat on the engine pid with EXE.AMX_BUSY (tile-busy cycles) and FP_ARITH_INST_RETIRED.512B_PACKED_SINGLE (AVX-512 FMA count) gives the AMX-busy time and the AVX work volume per arm; it cannot attribute them to phases.</li>
</ul>

<h2 id="more">7. Other counters worth adding</h2>
<div class="tw"><table><tr><th>Counter</th><th>Why</th><th>Hook</th></tr>
<tr><td>AVX visits by reason: partial tail page / range boundary inside the page (prefix-cache branch or query event) / window edge / young query below 127 / FPGA boundary page</td><td>says why AMX-eligible work fell to AVX; the reasons have different fixes (page alignment, mask merging, DMA pacing)</td><td>the dense predicate's five terms at :1609-1611, evaluated once per visit that fails it</td></tr>
<tr><td>hollow tile regions: apply_page_range calls with amx_on and zero AMX visits</td><td>every call pays begin_region (tile config load) and end_region (TILERELEASE) even when no dense page exists, which is the common case in steady-state decode under FPGA attention</td><td>:1440-1464 amx_on / begin_region, :1566 flush</td></tr>
<tr><td>Q packs per token per call (qpacks / distinct tokens)</td><td>shows how well the lazy Q pack amortizes (one pack per (token, kv_head) per call, reused across pages)</td><td>packed_amx_query :1576-1590</td></tr>
<tr><td>DMA lag per decode step: query position minus last_hw_token_pos, as a histogram</td><td>the one quantity that fixes the FPGA share and that no closed form gives</td><td>model.hpp:2519 (hw_query built) or full.hpp:2757-2759</td></tr>
<tr><td>HBM fallback per forward: shards without HBM in this plan</td><td>today only a per-shard cumulative leaf exists; per forward it explains sudden CPU spikes</td><td>src/tron/gof.cpp:73-79</td></tr>
<tr><td>per-worker imbalance per layer: max / mean of T2 across attention workers, and the serial join fold time (run_joins)</td><td>the join fold into worker 0 is serial (a balanced tree is only a TODO, self_attention.hpp:1257); imbalance and fold time bound the attention wall, not the kernel speed</td><td>run_joins :1129-1230</td></tr>
<tr><td>attention share of the layer: T3 / T4</td><td>tells how much of a layer is attention versus matmuls and FFN, per prompt length</td><td>derived from T3 and T4</td></tr>
<tr><td>per-user inter-token latency</td><td>does not exist in runtron or rinzler (only mean TTFT); needed to turn T1 into a per-user number when forwards mix users and prompt chunks</td><td>listener delivery, model.hpp:3100-3122</td></tr>
<tr><td>pending versus ready split for every path counter</td><td>separates the current-chunk (prefill) and new-token (decode) work from the context work; PR0 already has pending_visits without a path tag</td><td>the pending argument of apply_page_range (:1384)</td></tr>
<tr><td>prefill accounting per request: forwards per prompt, prefix-cache tokens reused</td><td>turns the prefill counters into a per-request TTFT decomposition</td><td>src/tron/generation/context.cpp:41-75</td></tr>
</table></div>

<h2 id="gating">8. Gating and reporting: the decision to make</h2>
<div class="tw"><table><tr><th>Option</th><th>Where the numbers come out</th><th>Cost when off</th><th>Fits</th><th>Judge scores (engineering / user, of 40)</th></tr>
<tr><td>D1 compile-time option, PR0 shape (TRON_ATTN_PATH_COUNTERS, default OFF) + exit report</td><td>stderr at normal exit; runtron yes, rinzler under platformd no (API stop, no normal exit)</td><td>zero, the production binary is byte-identical</td><td>the precedent the approving reviewer accepted for PR0; reviewers asked for small topical PRs</td><td>31 / 29</td></tr>
<tr><td>D2 run-time env var (TRON_ATTN_STATS=1, exactly "1") + casual FUSE leaves under /model/&lt;id&gt;/attention/</td><td>cat the leaves live, difference before and after a cell; works on the CI machine under platformd through /etc/rinzler/instance-N.env</td><td>one predictable branch per visit in every build, unmeasured (est. below 0.1 %)</td><td>issue #4303 as written; the same deb serves every arm</td><td>30 / 34</td></tr>
<tr><td>D3 perfetto arguments on existing spans + offline SQL script</td><td>trace files, analysed with the repo's trace-processor skill</td><td>one category check per event</td><td>per-step distributions, DMA-boundary inspection; not live, not production</td><td>29 / 29</td></tr>
</table></div>
<ul class="tight">
<li><b>Recommendation:</b> split by hook frequency, counter by counter (section 9). The per-visit tallies of section 5.1 (AMX / AVX / empty visits, per-token path sets) go behind a compile-time option (D1), published as casual FUSE leaves under that option (make_file + set_read_callback, expert_stats.hpp:142-198 precedent, weak_ptr capture because runtron's unmount guard outlives the models, src/runtron.cpp:485), so a counting deb works under platformd for CI-harness campaigns. The per-job, per-pass and per-forward counters and all five timers are cheap enough for the always-compiled environment-variable switch (D2) once the A/A run of section 10 has measured the off-state cost; until then they ship under the same compile option. Take the two free perfetto one-liners from D3: a "layer" argument on the Attention Ready/Pending span (:1389-1398) and "n_listeners" on the forward span (model.hpp:1622-1623).</li>
<li>Which gating the reviewers accept for a hook in the hottest loop is their decision, not a derivation; ask before implementing. PR 4424 (VNNI K) touches the same lines, so pick the base branch at the same time.</li>
<li>Per-model rows: a rinzler process can host several models; rows must live on the model object, not in process-wide atomics.</li>
</ul>

<h2 id="control">9. Which switch for which counter: build option, environment variable or perfetto</h2>
<div class="wrong"><p><b>Superseded on 2026-09-24 for the per-visit rows (section 13).</b> jhan chose the environment variable for every counter and timer of sections 5.1 and 5.2, with a build option only as the fallback if the measured off-state cost is obvious. The rows below that say "build option" for the per-visit tallies and the per-token path sets record the 2026-09-22 rule; the phase timers of section 6 keep the build-option recommendation. The kill-switch identity stated in this section and in section 10 is also corrected in section 13: the kill-switch arm's avx_full_page_visits equals the AMX-on arm's amx_visits plus its avx_full_page_visits (full pages written in the current forward take the AVX path even with AMX on).</p></div>
<p>The decision rule has three parts. It follows from how often each hook runs, not from what it measures.</p>
<ul class="tight">
<li><b>Build option</b> (CMake, default OFF, the PR0 pattern): every hook that runs once per visit, that is per (query token, KV page, KV head) call of apply_page_tok. Visits per decode step per user = layers x KV heads x pages, for example 32 x 8 x 18 = 4,608 at context 1100 on llama-3.1-8b, and prefill multiplies that by the chunk size. A branch there is in the hottest loop, so the production binary stays byte-identical and a counting build is made for campaigns. Two options: TRON_ATTN_PATH_COUNTERS (path tallies, per-token path sets) and TRON_ATTN_PHASE_TIMERS (rdtsc per phase, lab only).</li>
<li><b>Environment variable</b> (TRON_ATTN_STATS, exactly "1", read once like TRON_AMX_DISABLE, always compiled, published as FUSE leaves): every hook that runs once per apply_page_range call, per attention job, per FPGA pass or per forward. Those are hundreds of sites per forward instead of thousands per user, and the off-state cost is one predictable branch per site, to be confirmed by the A/A run of section 10. This is the switch that works on the CI machine under platformd, because the same deb serves every arm and the leaves are read live.</li>
<li><b>Perfetto</b> (arguments on spans that already exist, or one new span; no switch of its own): values needed as a per-step distribution, or for correlating attention with the rest of the forward offline. When no trace session is active the macro evaluates only a category check [h/common/perfetto.hpp:44-58]. Perfetto cannot carry per-visit events (tens of thousands per forward), but it can carry per-section sums as end arguments once the build option computes them.</li>
</ul>
<p>What each switch alone gives: the environment variable alone gives the CPU-versus-FPGA share (planner estimate plus FPGA plan), the five timers, the forward classes and the DMA lag. The build option adds the AMX-versus-AVX split and the per-token path sets. Perfetto adds per-step distributions and the join with the rest of the trace.</p>
<div class="tw"><table><tr><th>Counter or timer</th><th>Section</th><th>Hook site and frequency</th><th>Control</th><th>Output</th><th>Why this switch</th></tr>
<tr><td>amx_visits, amx_k_tokens</td><td>5.1</td><td>apply_page_tok :1768, per visit</td><td><b>build option</b> TRON_ATTN_PATH_COUNTERS</td><td>exit report; FUSE leaves under the same option</td><td>per-visit hook in the hottest loop; zero cost when not compiled</td></tr>
<tr><td>avx_visits, avx_k_tokens</td><td>5.1</td><td>apply_page_tok :1852, per visit</td><td><b>build option</b></td><td>same</td><td>same</td></tr>
<tr><td>avx_full_page_visits</td><td>5.1</td><td>apply_page_tok :1852, per visit (one compare)</td><td><b>build option</b></td><td>same</td><td>same; the kill-switch cross-check needs it in the same build as amx_visits</td></tr>
<tr><td>empty_visits</td><td>5.1</td><td>apply_page_tok :1820, per visit</td><td><b>build option</b></td><td>same</td><td>same</td></tr>
<tr><td>token_jobs[class][path set]</td><td>5.1</td><td>bits per visit (:1539-1546), fold per forward (model.hpp:1706)</td><td><b>build option</b></td><td>same</td><td>the bits are set per visit; the fold alone would be cheap, but without the bits it has nothing to fold</td></tr>
<tr><td>fpga_k_tokens, fpga_query_passes</td><td>5.1</td><td>prepare_uniform_hw_attention :600, per (pass, query) per FPGA layer, main thread</td><td><b>environment variable</b>; also a perfetto argument on launch_hw_attn (:642)</td><td>FUSE leaves per layer; trace argument</td><td>tens of adds per layer per forward, off the attention workers; the CPU-versus-FPGA share needs no per-visit code</td></tr>
<tr><td>fpga_queries</td><td>5.1</td><td>construct_hw_plan model.hpp:2519, per hw_query per minibatch</td><td><b>environment variable</b></td><td>FUSE leaf per forward class</td><td>a few increments per forward</td></tr>
<tr><td>planned CPU dot products per forward (new: sum of work_estimate.k_dot_products)</td><td>5.1 self-check</td><td>estimate_attention_work model.hpp:1787-1865, per section, main thread</td><td><b>environment variable</b></td><td>FUSE leaf per forward class</td><td>the planner already computes it; publishing the sum gives the CPU total without touching the hot loop and is the reference for the invariant</td></tr>
<tr><td>forwards[class]</td><td>5.1</td><td>full.hpp:1993-2004, per forward</td><td><b>environment variable</b>; class also as the perfetto argument n_listeners on the forward span</td><td>FUSE leaf; trace argument</td><td>one compare and one store per forward</td></tr>
<tr><td>attn_jobs</td><td>5.1</td><td>run_attention_job :806-807, per (worker, layer, minibatch)</td><td><b>environment variable</b></td><td>FUSE rows [worker][layer]</td><td>one increment per job into a worker-owned row</td></tr>
<tr><td>T1 forward_wall</td><td>5.2</td><td>full.hpp:1993-1995, per forward</td><td><b>environment variable</b> for the live sum, count, max and histogram; the perfetto "forward" span already exists for per-step values</td><td>FUSE leaves; trace slices</td><td>two rdtsc per forward; the distribution per step is a trace question</td></tr>
<tr><td>T2 attn_busy per (worker, layer)</td><td>5.2</td><td>:774-806 (the value exists today), record at :807, per job</td><td><b>environment variable</b></td><td>FUSE rows [worker][layer]</td><td>the rdtsc reads already run in every build; only the store is new</td></tr>
<tr><td>T3 attn_wall_w0 per layer</td><td>5.2</td><td>:755 to :806 on worker 0, per job</td><td><b>environment variable</b> for the histogram; a new perfetto "attention op" span at :762-765 gives the same value per step</td><td>FUSE histogram per layer; trace slices</td><td>two rdtsc per job on one worker</td></tr>
<tr><td>T4 layer_period_w0</td><td>5.2</td><td>:755 entry to entry on worker 0, per job</td><td><b>environment variable</b></td><td>FUSE per layer</td><td>reuses the T3 entry timestamp</td></tr>
<tr><td>T5 hw_join_wait</td><td>5.2</td><td>stream_hw_joins :1075-1078, per job</td><td><b>environment variable</b>; the perfetto "attention: join wait" span already exists</td><td>FUSE rows; trace slices</td><td>two rdtsc per job; only under FPGA attention</td></tr>
<tr><td>phase timers: QK, softmax step, PV, state, Q pack, tile region</td><td>6</td><td>apply_dense_amx_page :1654-1700 and the dotter :1800-1849, 4 rdtsc per visit</td><td><b>build option</b> TRON_ATTN_PHASE_TIMERS (lab builds only), never the environment variable</td><td>exit report or the fence-branch stamp export</td><td>1 to 4 % of a unit (est.) even when the numbers are wanted, 0 to 5 % measured on 2026-09-01; unacceptable as an always-compiled branch</td></tr>
<tr><td>FPGA pass latency (launch to completion callback)</td><td>6.1</td><td>launch_hw_attn :642 to attn_launcher_cb :680, per pass</td><td><b>environment variable</b>; perfetto has the launch span and the callback instants today</td><td>FUSE histogram; trace</td><td>a few passes per layer</td></tr>
<tr><td>AVX visits by reason (tail page, range boundary, window edge, young query, FPGA boundary page)</td><td>7</td><td>the dense predicate :1609-1611, per visit that fails it</td><td><b>build option</b></td><td>exit report; FUSE under the option</td><td>per-visit classification</td></tr>
<tr><td>hollow tile regions (calls with amx_on and zero AMX visits)</td><td>7</td><td>apply_page_range :1440-1464 and :1566, per call</td><td><b>build option</b></td><td>same</td><td>per call, but it needs the per-visit AMX tally to know the count was zero</td></tr>
<tr><td>Q packs per token per call</td><td>7</td><td>packed_amx_query :1576-1590, per pack</td><td><b>build option</b></td><td>same</td><td>the pack site is inside the per-visit loop; keep the production loop untouched</td></tr>
<tr><td>DMA lag per decode step (query position minus last_hw_token_pos)</td><td>7</td><td>model.hpp:2519 per hw_query, or full.hpp:2757-2759</td><td><b>environment variable</b> for the histogram; also a perfetto argument on launch_hw_attn</td><td>FUSE histogram; trace argument</td><td>a few values per forward on the main thread; the one quantity that fixes the FPGA share</td></tr>
<tr><td>HBM fallback per forward</td><td>7</td><td>src/tron/gof.cpp:73-79, per shard placement</td><td><b>environment variable</b></td><td>FUSE per forward class (the per-shard cumulative leaf exists today)</td><td>rare event, main thread</td></tr>
<tr><td>per-worker imbalance (max / mean of T2) and serial join fold time</td><td>7</td><td>derived from the T2 rows; run_joins :1129-1230 timed per job</td><td><b>environment variable</b></td><td>FUSE, computed in the read callback</td><td>derived from per-job values</td></tr>
<tr><td>attention share of the layer (T3 / T4)</td><td>7</td><td>derived</td><td><b>environment variable</b></td><td>FUSE, computed in the read callback</td><td>derived</td></tr>
<tr><td>per-user inter-token latency</td><td>7</td><td>listener delivery model.hpp:3100-3122, per token per user</td><td><b>perfetto</b> today (the notify_listener span exists); <b>environment variable</b> + FUSE if a live number is needed</td><td>trace; FUSE per model</td><td>per token per user is cheap, but the distribution per user is what matters, which the trace already carries</td></tr>
<tr><td>pending versus ready split of every path counter</td><td>7</td><td>the pending argument of apply_page_range (:1384), a dimension of the tallies</td><td><b>build option</b> (it is a dimension of the per-visit tallies); perfetto already splits by span name</td><td>same channel as the tallies</td><td>no separate hook</td></tr>
<tr><td>prefill accounting per request (forwards per prompt, prefix-cache tokens reused)</td><td>7</td><td>src/tron/generation/context.cpp:41-75, per request; metrics.tokens_reused exists</td><td><b>environment variable</b></td><td>FUSE per model</td><td>per request; part of it is a scheduler metric already</td></tr>
<tr><td>"layer" on the Attention Ready/Pending span; "n_listeners" on the forward span</td><td>8</td><td>self_attention.hpp:1389-1398; model.hpp:1622-1623</td><td><b>perfetto</b> (no switch)</td><td>trace arguments</td><td>one integer annotation per existing event; nothing when tracing is off</td></tr>
<tr><td>report header: amx_compiled, amx_available, n_kv_heads, kv_mul, FPGA layers</td><td>5</td><td>once per process or per model load</td><td><b>environment variable</b> (always available when the leaves are on); also printed by the build-option report</td><td>FUSE summary leaf; exit report first line</td><td>constant values, no hot path</td></tr>
</table></div>
<p class="take">Takeaway: the AMX-versus-AVX split and the per-token path sets are the only items that must be a build option. Everything per job, per pass or per forward can be an environment-variable switch in every build once the A/A run has measured the off-state cost. Perfetto is the channel for per-step distributions, not a substitute for either.</p>

<h2 id="measure">10. Measurements to run first, and acceptance tests</h2>
<ol>
<li>Off-state cost (D2 only): A/A on the p0perf shape (llama-3.1-8b, 8 users x prompt 1024, CI harness, our half of 3bda), pre-patch binary versus patched binary with the switch unset; accept if the TPS delta is inside the 09-11 A/A band.</li>
<li>On-state cost: the same shape, counters on versus off; report the delta with its band. Also count apply_page_range calls per forward to size the flush cost (unknown today: n_attn_workers x n_kv_heads x 2 passes x n_layers).</li>
<li>Kill-switch cross-check: run the AMX-on arm and the TRON_AMX_DISABLE=1 arm with perf stat EXE.AMX_BUSY on the engine pid; amx_visits and AMX_BUSY must both be zero in the kill-switch arm and both non-zero otherwise; avx_full_page_visits (kill switch) must equal amx_visits (AMX on).</li>
<li>Invariant: per section (amx_k_tokens + avx_k_tokens) x kv_mul == the planner's dot products, except EAGLE (63 versus 64) and window skips.</li>
<li>Prefill claim: one user, a 256-token prompt (two chunks), CPU attention, AMX on: pending-pass amx_visits must be 0 and ready-pass amx_visits must be 2 x 128 per KV head. This also settles whether a full pending decode page (N mod 64 == 0) takes AMX.</li>
<li>FPGA steady state: qwen-3-4b, USE_HW_ATTN default, prompt 1024, 256 tokens: amx_visits per decode step (predicted 0), avx_k_tokens per step (predicted a few), the DMA lag histogram, and how often the boundary falls on a page edge. Then the warm 8192 cell, where the AMX build was faster under AoF: the counter shows whether non-resident pages were scored on the CPU with AMX.</li>
<li>n_attn_workers on 3bda for the campaign configs (depends on the CPU list platformd hands over; not in the repo): read it from the process so per-worker rows can be interpreted.</li>
</ol>

<h2 id="open">11. Open points (Insufficient data)</h2>
<ul class="tight">
<li>Whether a full pending decode page is dense in the same forward (measurement 5 resolves it).</li>
<li>The steady-state DMA lag in GOFs during decode and between prefill forwards (measurement 6; or log query position minus dma_last_abs per step, full.hpp:2757-2759).</li>
<li>The inclusive-versus-count semantics of relative_hw_tok_ix (libpos.hpp:453-455 versus self_attention.hpp:565, 583): the FPGA K-token counter may be off by one per query until the device semantics are read.</li>
<li>rdtsc cost on delphi-3bda (Granite Rapids): measure with the 1e8-read loop before adding per-visit timers.</li>
<li>Whether the CI harness shares a cached system prompt across users: it creates ready pages in a user's first forward and changes the prefill split.</li>
<li>Issue #4303 and #4338 texts are not in the checkout; read them on GitHub before naming the env var and the leaf path.</li>
</ul>

<h2 id="sources">12. Sources</h2>
<ul class="tight">
<li>Code: tron main 0a51385e95, read-only worktree ~/workspace/ai-runs/tron-counters-ro. All file:line citations refer to it.</li>
<li>Verification workflow wf_a8e982c8-1b8 (8 readers, 16 refuters, 3 designs, 2 judges, 1 critic): result saved as exec/counter-20260922/workflow-wf_a8e982c8-1b8-result.json (facts with status, designs, judge scores, critic).</li>
<li>Closed-form numbers: exec/counter-20260922/closed_form.py. Phase timings: exec/results/single-attn-20260901/summary.json (measured 2026-09-01 on delphi-3bda, probe commit 8fd1e7798d in ~/workspace/ai-runs/tron-fence-amx). rdtsc cost: exec/counter-20260922/rdtsc_cost.c (this workstation only).</li>
<li>Earlier pages: PR3879/make-sense-amx-vs-avx.html section 7.2.1 (single attention), CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html (FPGA versus CPU attention by prompt length), PR3879/new-PRs/PR0/respond-2-Wade-PR0.html (FUSE counters assessment).</li>
</ul>
{section13()}
</main></body></html>
"""

def main():
    html = HTML
    bad = [c for c in html if ord(c) > 127]
    assert not bad, f"non-ASCII characters in output: {set(bad)}"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(html)
    print(OUT, len(html), "bytes; ASCII ok")
    for N in (1024, 8192):
        r = ROWS[N]
        print(N, "prefill", fmt(r["pre_tot"]), "AMX", pct(r["pre_amx"], r["pre_tot"]), "decode", fmt(r["dec_tot"]), "ratio", f'{r["pre_tot"]/r["dec_tot"]:.2f}')

if __name__ == "__main__":
    main()
