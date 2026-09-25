"""Section 7 of the prefill page: the runtron campaign q4b-rt8u-20260922 (8 or 2 users on one tp2 engine, prompts 1024 to 8192,
CPU attention against FPGA attention, AVX build against canonical AMX build, 3 repetitions).

Reads exec/results/q4b-rt8u-20260922/summary.json (written by exec/q4b-rt8u-20260922/summarize.py): cells (mean, sd, n per
cell x attention x arm), paired (canon minus base per attention, paired by repetition). TTFT here = runtron's server-side
"Parsing the prompt took" time = the batched prefill of all users' prompts (max over the users). TPS = decode tok/s per user.
"""
import json
import math
import os

import fpga_section as FS

SUMMARY = "/home/jhan/workspace/intel-AMX/exec/results/q4b-rt8u-20260922/summary.json"
CELLS = [("q3-4b-tp2-8u-p1024", 8, 1024), ("q3-4b-tp2-8u-p2048", 8, 2048), ("q3-4b-tp2-8u-p4096", 8, 4096), ("q3-4b-tp2-8u-p8192", 8, 8192),
         ("q3-4b-tp2-2u-p4096", 2, 4096), ("q3-4b-tp2-2u-p8192", 2, 8192)]
ARMS = [("cpu", "base", "base"), ("cpu", "canon", "canon"), ("fpga", "base", "fpgabase"), ("fpga", "canon", "fpgacanon")]   # (attn, arm, colour key)
ARM_TEXT = {"base": "AVX build + CPU attention", "canon": "AMX build + CPU attention", "fpgabase": "AVX build + FPGA attention", "fpgacanon": "AMX build + FPGA attention"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load():
    if not os.path.exists(SUMMARY):
        return None
    d = json.load(open(SUMMARY))
    cells = {(c["cell"], c["attn"], c["arm"]): c for c in d["cells"]}
    paired = {(p["cell"], p["attn"]): p for p in d["paired"]}
    return dict(cells=cells, paired=paired, raw=d)


def cell(d, name, attn, arm):
    return d["cells"].get((name, attn, arm))


def fig(d):
    """Two dot panels: TTFT (s, log axis) and decode TPS per user (linear), one row per cell, one dot per arm."""
    W = 1100
    lab_w = 250
    p1l, p1r = lab_w + 10, lab_w + 400
    p2l, p2r = p1r + 60, W - 70
    row_h = 60
    top = 112
    H = top + len(CELLS) * row_h + 56
    lo, hi = math.log10(2.0), math.log10(200.0)
    def X1(v):
        return p1l + (math.log10(v) - lo) / (hi - lo) * (p1r - p1l)
    def X2(v):
        return p2l + v / 175.0 * (p2r - p2l)
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="runtron: prefill time and decode TPS per user for four arms at 8 or 2 users on one engine" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="16" y="24" font-size="15" font-weight="600" fill="{FS.INK}">One engine, 8 or 2 users at once (runtron, 2026-09-22): prefill time and decode speed for the four arms</text>')
    out.append(f'<text x="16" y="44" font-size="12" fill="{FS.INK2}">Left: prefill of all users\' prompts in one batch, seconds, log axis (shorter = better). Right: decode tokens per second per user (higher = better). Mean of 3 repetitions, sd below 1 %.</text>')
    lx = 16
    for attn, arm, key in ARMS:
        out.append(f'<circle cx="{lx + 6}" cy="64" r="5" fill="{FS.ARM_COL[key]}"/>')
        out.append(f'<text x="{lx + 16}" y="68" font-size="11" fill="{FS.INK}">{esc(ARM_TEXT[key])}</text>')
        lx += 250
    for (xl, xr, title) in ((p1l, p1r, "prefill time of the batch, seconds (log axis)"), (p2l, p2r, "decode TPS per user")):
        out.append(f'<text x="{(xl + xr) / 2:.1f}" y="{top - 26}" font-size="12" font-weight="600" fill="{FS.INK}" text-anchor="middle">{title}</text>')
    for v in (2, 5, 10, 20, 50, 100, 200):
        x = X1(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 12}" x2="{x:.1f}" y2="{H - 44}" stroke="{FS.GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 30}" font-size="10" fill="{FS.INK3}" text-anchor="middle">{v}</text>')
    for v in range(0, 176, 25):
        x = X2(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 12}" x2="{x:.1f}" y2="{H - 44}" stroke="{FS.GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 30}" font-size="10" fill="{FS.INK3}" text-anchor="middle">{v}</text>')
    y = top
    for name, users, prompt in CELLS:
        out.append(f'<text x="{lab_w}" y="{y + 26}" font-size="11" fill="{FS.INK}" text-anchor="end">{users} users, prompt {prompt}</text>')
        out.append(f'<line x1="{p1l}" y1="{y + row_h - 4}" x2="{p2r}" y2="{y + row_h - 4}" stroke="{FS.GRID}" stroke-width="1"/>')
        for i, (attn, arm, key) in enumerate(ARMS):
            c = cell(d, name, attn, arm)
            if not c:
                continue
            yy = y + 8 + i * 12
            for X, v, fmt in ((X1, c["ttft_mean"], "{:.1f} s"), (X2, c["tps_mean"], "{:.0f}")):
                x = X(v)
                out.append(f'<circle cx="{x:.1f}" cy="{yy}" r="4.5" fill="{FS.ARM_COL[key]}" stroke="{FS.SURF}" stroke-width="1.5"><title>{esc(ARM_TEXT[key])}, {users} users, prompt {prompt}: {v:.2f}</title></circle>')
                out.append(f'<text x="{x + 8:.1f}" y="{yy + 3.5}" font-size="9.5" fill="{FS.INK}">{fmt.format(v)}</text>')
        y += row_h
    out.append(f'<text x="{(p1l + p2r) / 2:.1f}" y="{H - 10}" font-size="11" fill="{FS.INK3}" text-anchor="middle">Within a row the four dots are the four arms, in legend order from top to bottom. Source: exec/results/q4b-rt8u-20260922/summary.json.</text>')
    out.append('</svg>')
    return "\n".join(out)


def pm(v, s, f="{:.1f}"):
    return f.format(v) + (f" +/- {f.format(s)}" if s is not None else "")


def table_cells(d):
    h = ['<div class="tw"><table class="num"><thead><tr><th>cell</th>']
    for attn, arm, key in ARMS:
        h.append(f'<th>{esc(ARM_TEXT[key])}<br>prefill s / TPS per user</th>')
    h.append('</tr></thead><tbody>')
    for name, users, prompt in CELLS:
        h.append(f'<tr><td>{users} users, prompt {prompt}</td>')
        for attn, arm, key in ARMS:
            c = cell(d, name, attn, arm)
            h.append(f'<td>{pm(c["ttft_mean"], c["ttft_sd"], "{:.2f}")} / {pm(c["tps_mean"], c["tps_sd"])} (n = {c["n"]})</td>' if c else '<td>-</td>')
        h.append('</tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)


def comparisons(d):
    """Per cell: FPGA+AMX against CPU+AMX (ratios), AMX against AVX under CPU attention and under FPGA attention (paired by repetition)."""
    rows = []
    for name, users, prompt in CELLS:
        cc, cb = cell(d, name, "cpu", "canon"), cell(d, name, "cpu", "base")
        fc, fb = cell(d, name, "fpga", "canon"), cell(d, name, "fpga", "base")
        pc, pf = d["paired"].get((name, "cpu")), d["paired"].get((name, "fpga"))
        rows.append(dict(
            users=users, prompt=prompt,
            fpga_vs_cpu_ttft=cc["ttft_mean"] / fc["ttft_mean"], fpga_vs_cpu_tps=fc["tps_mean"] / cc["tps_mean"],
            fpga_vs_avx_ttft=cb["ttft_mean"] / fc["ttft_mean"],
            cpu_amx_ttft_pct=100.0 * (cc["ttft_mean"] - cb["ttft_mean"]) / cb["ttft_mean"], cpu_amx_tps_pct=100.0 * (cc["tps_mean"] - cb["tps_mean"]) / cb["tps_mean"],
            cpu_t_ttft=pc["ttft_s"]["t"], cpu_t_tps=pc["tps"]["t"],
            fpga_amx_ttft_pct=100.0 * (fc["ttft_mean"] - fb["ttft_mean"]) / fb["ttft_mean"], fpga_amx_ttft_ms=1000.0 * (fc["ttft_mean"] - fb["ttft_mean"]),
            fpga_amx_tps_pct=100.0 * (fc["tps_mean"] - fb["tps_mean"]) / fb["tps_mean"],
            fpga_t_ttft=pf["ttft_s"]["t"], fpga_t_tps=pf["tps"]["t"],
            hbm=sum(c["hbm_lose_mean"] for c in (cc, cb, fc, fb)),
        ))
    return rows


def table_comparisons(rows):
    h = ['<div class="tw"><table class="num"><thead><tr><th>cell</th><th>FPGA + AMX build against CPU + AMX build: prefill (x faster)</th><th>same: decode TPS (x faster)</th><th>FPGA + AMX build against CPU + AVX build: prefill (x faster)</th><th>AMX build against AVX build, CPU attention: prefill / TPS (paired t)</th><th>AMX build against AVX build, FPGA attention: prefill / TPS (paired t)</th><th>HBM exhaustion warnings (all 12 runs of the cell)</th></tr></thead><tbody>']
    for r in rows:
        h.append(f'<tr><td>{r["users"]} users, prompt {r["prompt"]}</td><td>{r["fpga_vs_cpu_ttft"]:.2f}x</td><td>{r["fpga_vs_cpu_tps"]:.2f}x</td><td>{r["fpga_vs_avx_ttft"]:.2f}x</td>'
                 f'<td>{r["cpu_amx_ttft_pct"]:+.1f} % (t {r["cpu_t_ttft"]:+.0f}) / {r["cpu_amx_tps_pct"]:+.1f} % (t {r["cpu_t_tps"]:+.0f})</td>'
                 f'<td>{r["fpga_amx_ttft_pct"]:+.1f} % = {r["fpga_amx_ttft_ms"]:+,.0f} ms (t {r["fpga_t_ttft"]:+.1f}) / {r["fpga_amx_tps_pct"]:+.1f} % (t {r["fpga_t_tps"]:+.1f})</td><td>{r["hbm"]:.0f}</td></tr>')
    h.append('</tbody></table></div>')
    return "\n".join(h)


def section():
    d = load()
    if not d:
        return []
    rows = comparisons(d)
    r8 = {r["prompt"]: r for r in rows if r["users"] == 8}
    r2 = {r["prompt"]: r for r in rows if r["users"] == 2}
    c = lambda name, attn, arm: cell(d, name, attn, arm)
    c8k = {k: c("q3-4b-tp2-8u-p8192", *a) for k, a in (("cb", ("cpu", "base")), ("cc", ("cpu", "canon")), ("fb", ("fpga", "base")), ("fc", ("fpga", "canon")))}
    fa_t = [r["fpga_amx_ttft_pct"] for r in rows]; fa_p = [r["fpga_amx_tps_pct"] for r in rows]
    ca_t = [r["cpu_amx_ttft_pct"] for r in rows]; ca_p = [r["cpu_amx_tps_pct"] for r in rows]
    n_runs = d["raw"].get("n_rt_records", 0) - len(d["raw"].get("excluded", {}).get("failed_or_stopped", []))
    H = []
    H.append("<h2>7. Eight users on one engine: the runtron campaign of 2026-09-22</h2>")
    H.append("<p>Question (jhan, 2026-09-22): was a 4096- or 8192-token prompt with 8 users per engine tested? For CPU attention yes (runtron, 8 users at prompt 8192, the vnnik-20260914 campaign, not shown on this page), for FPGA attention no. This campaign fills that gap with both attention modes and both builds in one interleaved run: exec/q4b-rt8u-20260922/campaign.sh on our half of delphi-3bda (one tp2 engine, cards 90 and 93), 3 repetitions, each repetition running every cell for the AVX build and the AMX build under CPU attention and under FPGA attention before the next repetition starts. Cells: 8 users at prompt 1024, 2048, 4096 and 8192, and 2 users at 4096 and 8192, 256 generated tokens requested per user (runtron counts 253 generated tokens in every run, the last 3 are the stop sequence). Builds: the AVX build is tron at eb2de0265a (main before PR 3879, runtron.pre3879), the AMX build is main at c7844ca2ce (runtron.main0916). USE_HW_ATTN=0 selects CPU attention. At 16:58 UTC the campaign stopped the idle production engines through platformd (after the guard\'s 10-minute idle check). At 18:12 UTC it started them again through platformd. One earlier attempt at 16:36 UTC was stopped by the campaign\'s own watcher after 10 s, because platformd had restarted the engines that the guard had stopped with systemctl. That attempt is excluded. Every one of the 72 kept runs is complete.</p>")
    H.append(f'<div class="fig">{fig(d)}<p class="cap">Figure 5. runtron on one engine: prefill time of the whole batch (log axis) and decode TPS per user, four arms, mean of 3 repetitions (256 generated tokens requested, 253 counted). The prefill time is runtron\'s "Parsing the prompt took" value, the wall time of the batched prefill of all users\' prompts (the users\' values agree to the millisecond). It is not the CI harness\'s per-request TTFT of sections 1 to 6 (Words used here).</p></div>')
    H.append("<ul>")
    H.append(f"<li><b>FPGA attention against AMX on the CPU, same AMX build.</b> Prefill at 8 users: {r8[1024]['fpga_vs_cpu_ttft']:.2f}x at 1024 (the FPGA is 2 % slower), {r8[2048]['fpga_vs_cpu_ttft']:.2f}x at 2048, {r8[4096]['fpga_vs_cpu_ttft']:.2f}x at 4096 and {r8[8192]['fpga_vs_cpu_ttft']:.2f}x at 8192 ({c8k['cc']['ttft_mean']:.1f} s against {c8k['fc']['ttft_mean']:.1f} s for 8 prompts of 8192 tokens). At 2 users: {r2[4096]['fpga_vs_cpu_ttft']:.2f}x at 4096 and {r2[8192]['fpga_vs_cpu_ttft']:.2f}x at 8192. Decode at 8 users: {r8[1024]['fpga_vs_cpu_tps']:.1f}x at 1024 to {r8[8192]['fpga_vs_cpu_tps']:.1f}x at 8192 ({c8k['fc']['tps_mean']:.1f} against {c8k['cc']['tps_mean']:.1f} TPS per user). The same picture as the CI harness (section 5): equal at 1024, the FPGA ahead from 2048 up, most at 8192.</li>")
    H.append(f"<li><b>AMX build against AVX build, CPU attention.</b> Prefill {min(ca_t):+.0f} to {max(ca_t):+.0f} % ({c8k['cb']['ttft_mean']:.1f} s to {c8k['cc']['ttft_mean']:.1f} s at 8 users and 8192, {c8k['cb']['ttft_mean'] / c8k['cc']['ttft_mean']:.1f}x), decode {min(ca_p):+.1f} to {max(ca_p):+.1f} %, every paired t above 20 in magnitude. This is the AMX gain jhan recalled (2x at 8192), measured again with 8 users on one engine and 3 repetitions.</li>")
    H.append(f"<li><b>AMX build against AVX build, FPGA attention.</b> Prefill {min(fa_t):+.1f} to {max(fa_t):+.1f} % ({min(r['fpga_amx_ttft_ms'] for r in rows):+,.0f} to {max(r['fpga_amx_ttft_ms'] for r in rows):+,.0f} ms on batches of 3 to 30 s), decode {min(fa_p):+.1f} to {max(fa_p):+.1f} %. The paired t is -7.9 to -17 at 2048 to 8192 with 8 users and -13.4 at 2 users and 8192. Those 1 to 2 % prefill gains are therefore resolved, and small. The 1024 cell (-0.3 %, t -0.7) and the 2-user 4096 cell (+0.3 %, t +1.8) show no resolved difference. Decode changes by at most 1.2 % in every cell. Five decode cells are not resolved (|t| at most 3.2). One (2 users, prompt 4096) is resolved at -0.5 % (t -4.5), a change too small to matter. Without a warm prefix cache the AMX build brings the FPGA path 0 to 2 % on prefill and nothing on decode. This is the runtron counterpart of the cold CI-harness cells of section 6 (2 to 8 % there) and of the decode &quot;no&quot;.</li>")
    H.append(f"<li><b>No HBM exhaustion.</b> All {n_runs} runs logged 0 &quot;lose HW attention&quot; warnings, including 8 users at 8192 (72 shards of 1024 tokens per engine: 9 per user for 8192 prompt plus 256 generated tokens, 36 per card, about 10.9 GB over the two cards, est.). Every runtron process starts with an empty prefix cache and sends one batch, so no older shards occupy the card. The exhaustion of section 5 is an effect of the warm prefix cache holding shards of earlier requests, not of the request size.</li>")
    H.append("</ul>")
    H.append("<h3>The record</h3>")
    H.append(table_cells(d))
    H.append('<p class="cap">Mean +/- sample sd over the 3 repetitions. Prefill in seconds (runtron &quot;Parsing the prompt took&quot;, the batched prefill of all users\' prompts), TPS = decode tokens per second per user. Source: exec/results/q4b-rt8u-20260922/summary.md and summary.json (summarize.py over rt-results.txt).</p>')
    H.append(table_comparisons(rows))
    H.append('<p class="cap">Ratios are of the means (x faster = the reference divided by the compared arm for prefill, the compared arm divided by the reference for TPS). Percentages are AMX build minus AVX build in percent of the AVX build, with the paired t over the 3 repetitions (repetition k of one arm against repetition k of the other). HBM exhaustion = the count of &quot;lose HW attention&quot; warning lines in the 12 run logs of the cell (4 arms x 3 repetitions).</p>')
    return H
