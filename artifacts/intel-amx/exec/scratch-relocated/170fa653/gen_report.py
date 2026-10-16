#!/usr/bin/env python3
"""Generate CI-AMX-regression-20261009.html from report_numbers.json (all numbers come from the JSON)."""
import json, html, os, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
N = json.load(open(os.path.join(HERE, 'report_numbers.json')))
OUT = os.path.expanduser('~/workspace/intel-AMX/CI-test/status/CI-AMX-regression-20261009.html')

BLUE, ORANGE, AQUA, GRAY, GRID, AXIS, INK, INK2, MUTED, SURF, RED = '#2a78d6', '#eb6834', '#1baf7a', '#b4b2aa', '#e1e0d9', '#c3c2b7', '#0b0b0b', '#52514e', '#898781', '#fcfcfb', '#e34948'

def esc(s): return html.escape(str(s))
def fmt(n): return f"{n:,.0f}"

# ---------- Figure 1: TTFT per night (emphasis on 10-09), baseline band, monitor limit ----------
def fig_history():
    H = N['amx_history']; B = N['amx_baseline']; lim = N['monitor']['ttft_at_prefill_min']
    W, Hh, L, R, T, Bm = 760, 330, 64, 24, 28, 56
    ys = [h['ttft'] for h in H]
    ymin, ymax = 11400, 12000
    def X(i): return L + i * (W - L - R) / (len(H) - 1)
    def Y(v): return T + (ymax - v) * (Hh - T - Bm) / (ymax - ymin)
    parts = [f'<svg viewBox="0 0 {W} {Hh}" role="img" aria-labelledby="f1t" class="chart"><title id="f1t">Time to first token per night, AMX row</title>']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="{SURF}"/>')
    # baseline band (min..max of the 13 nights)
    parts.append(f'<rect x="{L}" y="{Y(B["ttft_max"]):.1f}" width="{W-L-R}" height="{Y(B["ttft_min"])-Y(B["ttft_max"]):.1f}" fill="{BLUE}" opacity="0.10"/>')
    for v in range(11400, 12001, 200):
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end" class="tick">{fmt(v)}</text>')
    parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(ymin):.1f}" y2="{Y(ymin):.1f}" stroke="{AXIS}"/>')
    # monitor limit line
    parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(lim):.1f}" y2="{Y(lim):.1f}" stroke="{INK}" stroke-width="2" stroke-dasharray="6 4"/>')
    parts.append(f'<text x="{L+6}" y="{Y(B["ttft_min"])+17:.1f}" class="note" fill="{INK}">dashed line: email limit, prefill 353 tok/s = TTFT {fmt(lim)} ms</text>')
    parts.append(f'<text x="{L+6}" y="{Y(B["ttft_max"])-6:.1f}" class="note" fill="{BLUE}">13-night range {fmt(B["ttft_min"])}–{fmt(B["ttft_max"])} ms (mean {fmt(B["ttft_mean"])}, sd {B["ttft_sd"]:.0f})</text>')
    # line + dots
    pts = ' '.join(f'{X(i):.1f},{Y(h["ttft"]):.1f}' for i, h in enumerate(H))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{GRAY}" stroke-width="2"/>')
    for i, h in enumerate(H):
        last = (i == len(H) - 1)
        col = BLUE if last else GRAY
        parts.append(f'<circle cx="{X(i):.1f}" cy="{Y(h["ttft"]):.1f}" r="{6 if last else 4.5}" fill="{col}" stroke="{SURF}" stroke-width="2" class="mark" data-tip="{esc(h["day"])} · {esc(h["pkg"])} · TTFT {fmt(h["ttft"])} ms · prefill {h["prefill"]:.0f} tok/s · {h["tps"]:.2f} TPS"/>')
        lab = h['day'][5:]
        if i % 2 == 0 or last:
            parts.append(f'<text x="{X(i):.1f}" y="{Hh-Bm+18}" text-anchor="middle" class="tick">{lab}</text>')
    # direct labels: first, 10-08 and 10-09
    for i in (0, len(H) - 2, len(H) - 1):
        h = H[i]; dy = -12 if i != len(H) - 2 else 22
        parts.append(f'<text x="{X(i):.1f}" y="{Y(h["ttft"])+dy:.1f}" text-anchor="middle" class="vlabel" fill="{INK}">{fmt(h["ttft"])}</text>')
    d = N['deltas']
    parts.append(f'<text x="{X(len(H)-1)-10:.1f}" y="{Y(H[-1]["ttft"])+4:.1f}" text-anchor="end" class="callout" fill="{BLUE}">+{fmt(d["ttft_ms"])} ms vs 10-08 (+{d["ttft_pct"]:.1f} %)</text>')
    parts.append(f'<text x="{L}" y="{Hh-6}" class="axis-title">night (2026, UTC date of the Slack report)</text>')
    parts.append(f'<text transform="translate(14,{(T+Hh-Bm)/2:.0f}) rotate(-90)" text-anchor="middle" class="axis-title">TTFT, ms (32 users, 4,096-token prompt)</text>')
    parts.append('</svg>')
    return '\n'.join(parts)

# ---------- Figure 2: every row, % change in TTFT 10-09 vs 10-08 with its 8-night range ----------
def fig_rows():
    rows = [r for r in N['all_rows'] if r['ttft_base_min'] > 0 and r['tps_base_min'] > 0]
    def pct(a, b): return 100 * (b / a - 1)
    data = []
    for r in rows:
        base_mu = (r['ttft_base_min'] + r['ttft_base_max']) / 2  # midpoint only for range drawing
        data.append(dict(row=r['row'], new=pct(r['ttft_1008'], r['ttft_1009']),
                         lo=pct(r['ttft_1008'], r['ttft_base_min']), hi=pct(r['ttft_1008'], r['ttft_base_max']),
                         t08=r['ttft_1008'], t09=r['ttft_1009'], bmin=r['ttft_base_min'], bmax=r['ttft_base_max'], prompt=r['prompt']))
    data.sort(key=lambda d: -abs(d['new']))
    W, rowh, L, R, T = 840, 26, 350, 24, 30
    Hh = T + rowh * len(data) + 48
    xmin, xmax = -14, 14
    def X(v): return L + (v - xmin) * (W - L - R) / (xmax - xmin)
    parts = [f'<svg viewBox="0 0 {W} {Hh}" role="img" aria-labelledby="f2t" class="chart"><title id="f2t">TTFT change per row, 10-09 vs 10-08, with each row\'s 8-night range</title>']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="{SURF}"/>')
    for v in range(-12, 13, 4):
        parts.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T-6}" y2="{Hh-40}" stroke="{GRID if v else AXIS}" stroke-width="1"/>')
        parts.append(f'<text x="{X(v):.1f}" y="{Hh-24}" text-anchor="middle" class="tick">{v:+d} %</text>')
    for i, d in enumerate(data):
        y = T + i * rowh + rowh / 2
        amx = '@32u' in d['row'] and d['row'].startswith('llama-3.1-8b')
        col = BLUE if amx else GRAY
        lo, hi = max(xmin, min(d['lo'], d['hi'])), min(xmax, max(d['lo'], d['hi']))
        parts.append(f'<rect x="{X(lo):.1f}" y="{y-6:.1f}" width="{max(2, X(hi)-X(lo)):.1f}" height="12" rx="4" fill="{col}" opacity="0.22"/>')
        parts.append(f'<circle cx="{X(max(xmin, min(xmax, d["new"]))):.1f}" cy="{y:.1f}" r="5.5" fill="{col}" stroke="{SURF}" stroke-width="2" class="mark" data-tip="{esc(d["row"])} · prompt {esc(d["prompt"])} · TTFT {fmt(d["t08"])} → {fmt(d["t09"])} ms ({d["new"]:+.1f} %) · 8-night range {fmt(d["bmin"])}–{fmt(d["bmax"])} ms"/>')
        parts.append(f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" class="rowlabel" fill="{INK if amx else INK2}">{esc(d["row"])}</text>')
        if amx:
            parts.append(f'<text x="{X(d["new"])+10:.1f}" y="{y+4:.1f}" class="callout" fill="{BLUE}">{d["new"]:+.1f} %, outside its range</text>')
    parts.append(f'<text x="16" y="{Hh-6}" class="axis-title">TTFT change from 10-08 to 10-09, per cent. Bar: the 10-01..10-08 nights relative to 10-08.</text>')
    parts.append('</svg>')
    return '\n'.join(parts)

# ---------- Figure 3: TTFT by service rank ----------
def fig_rank():
    R_ = N['rank_profile']
    W, Hh, L, R, T, Bm = 760, 360, 64, 24, 28, 56
    ymin, ymax = 6000, 14000
    def X(r): return L + (r - 1) * (W - L - R) / 31
    def Y(v): return T + (ymax - v) * (Hh - T - Bm) / (ymax - ymin)
    parts = [f'<svg viewBox="0 0 {W} {Hh}" role="img" aria-labelledby="f3t" class="chart"><title id="f3t">TTFT by order of first token within a round, 10-08 and 10-09</title>']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="{SURF}"/>')
    for v in range(6000, 14001, 2000):
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}"/>')
        parts.append(f'<text x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end" class="tick">{fmt(v)}</text>')
    parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(ymin):.1f}" y2="{Y(ymin):.1f}" stroke="{AXIS}"/>')
    for key, col, name in (('t1008', ORANGE, '10-08 (be0d5565)'), ('t1009', BLUE, '10-09 (26b6df7d)')):
        pts = ' '.join(f'{X(r["rank"]):.1f},{Y(r[key]):.1f}' for r in R_)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>')
        for r in R_:
            parts.append(f'<circle cx="{X(r["rank"]):.1f}" cy="{Y(r[key]):.1f}" r="4" fill="{col}" stroke="{SURF}" stroke-width="1.5" class="mark" data-tip="{name} · first-token order {r["rank"]} of 32 · mean TTFT {fmt(r[key])} ms · delta {r["t1009"]-r["t1008"]:+d} ms"/>')
    for r in (1, 8, 16, 24, 32):
        parts.append(f'<text x="{X(r):.1f}" y="{Hh-Bm+18}" text-anchor="middle" class="tick">{r}</text>')
    # direct labels
    parts.append(f'<text x="{X(32)-4:.1f}" y="{Y(R_[31]["t1009"])-10:.1f}" text-anchor="end" class="vlabel" fill="{BLUE}">10-09: {fmt(R_[31]["t1009"])}</text>')
    parts.append(f'<text x="{X(32)-4:.1f}" y="{Y(R_[31]["t1008"])+18:.1f}" text-anchor="end" class="vlabel" fill="{ORANGE}">10-08: {fmt(R_[31]["t1008"])}</text>')
    d9 = st.mean(r['t1009'] - r['t1008'] for r in R_[:9]); d32 = st.mean(r['t1009'] - r['t1008'] for r in R_[11:])
    parts.append(f'<text x="{X(17):.1f}" y="{Y(7600):.1f}" text-anchor="middle" class="callout" fill="{INK2}">users 1 to 9: mean delta {d9:+.0f} ms ({100*d9/st.mean(r["t1008"] for r in R_[:9]):+.1f} %)</text>')
    parts.append(f'<text x="{X(22):.1f}" y="{Y(R_[21]["t1008"])+40:.1f}" text-anchor="middle" class="callout" fill="{BLUE}">12th onward: mean delta {d32:+.0f} ms, flat</text>')
    parts.append(f'<text x="{L}" y="{Hh-6}" class="axis-title">order in which the 32 users got their first token (1 = earliest); mean over the 10 rounds</text>')
    parts.append(f'<text transform="translate(14,{(T+Hh-Bm)/2:.0f}) rotate(-90)" text-anchor="middle" class="axis-title">TTFT, ms</text>')
    parts.append('</svg>')
    return '\n'.join(parts)

# ---------- Figure 4: same package, different day (dot plot rows) ----------
def fig_samepkg():
    S = N['same_package']
    rows = [S[0], S[2], S[1], S[3], S[4]]  # order: be0d5565 nightly, be0d5565 campaign today, 26b6df7d nightly, PR4424 x2
    W, rowh, L, R, T = 800, 40, 330, 96, 30
    Hh = T + rowh * len(rows) + 64
    xmin, xmax = 11300, 12000
    def X(v): return L + (v - xmin) * (W - L - R) / (xmax - xmin)
    parts = [f'<svg viewBox="0 0 {W} {Hh}" role="img" aria-labelledby="f4t" class="chart"><title id="f4t">The same package measured on different days</title>']
    parts.append(f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="{SURF}"/>')
    for v in range(11300, 12001, 100):
        parts.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T-6}" y2="{Hh-52}" stroke="{GRID}"/>')
        parts.append(f'<text x="{X(v):.1f}" y="{Hh-38}" text-anchor="middle" class="tick">{fmt(v)}</text>')
    # connector between the two be0d5565 points
    y0 = T + rowh / 2; y1 = T + rowh + rowh / 2
    parts.append(f'<line x1="{X(S[0]["ttft"]):.1f}" x2="{X(S[2]["ttft"]):.1f}" y1="{(y0+y1)/2:.1f}" y2="{(y0+y1)/2:.1f}" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="3 3"/>')
    parts.append(f'<text x="{(X(S[0]["ttft"])+X(S[2]["ttft"]))/2:.1f}" y="{(y0+y1)/2-6:.1f}" text-anchor="middle" class="callout" fill="{ORANGE}">same package, +{S[2]["ttft"]-S[0]["ttft"]} ms in 33 h</text>')
    for i, s in enumerate(rows):
        y = T + i * rowh + rowh / 2
        col = ORANGE if s['pkg'] == '2026.10.08-be0d5565' else (BLUE if s['pkg'].startswith('2026.10.09') else AQUA)
        parts.append(f'<circle cx="{X(s["ttft"]):.1f}" cy="{y:.1f}" r="6" fill="{col}" stroke="{SURF}" stroke-width="2" class="mark" data-tip="{esc(s["label"])} · {esc(s["pkg"])} · TTFT {fmt(s["ttft"])} ms · {s["tps"]:.2f} TPS · {esc(s["when"])}"/>')
        parts.append(f'<text x="{X(s["ttft"])+12:.1f}" y="{y+4:.1f}" class="vlabel" fill="{INK}">{fmt(s["ttft"])} ms</text>')
        parts.append(f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" class="rowlabel" fill="{INK2}">{esc(s["label"])}</text>')
    parts.append(f'<text x="16" y="{Hh-20}" class="axis-title">TTFT, ms (llama-3.1-8b tp2, 32 users, 4,096-token prompt). Decode TPS is in the hover text.</text>')
    parts.append(f'<text x="16" y="{Hh-6}" class="axis-title">Orange: package be0d5565. Blue: 26b6df7d. Green: be0d5565 + PR 4424.</text>')
    parts.append('</svg>')
    return '\n'.join(parts)

B = N['amx_baseline']; D = N['deltas']; E = N['email']; M = N['monitor']
rows_tbl = ''.join(
    f"<tr><td>{esc(r['row'])}</td><td class='num'>{esc(r['prompt'])}</td><td class='num'>{r['tps_1008']:.2f}</td><td class='num'>{r['tps_1009']:.2f}</td><td class='num'>{r['tps_base_min']:.2f}–{r['tps_base_max']:.2f}</td><td class='num'>{fmt(r['ttft_1008'])}</td><td class='num'>{fmt(r['ttft_1009'])}</td><td class='num'>{fmt(r['ttft_base_min'])}–{fmt(r['ttft_base_max'])}</td></tr>"
    for r in N['all_rows'] if r['tps_base_min'] > 0)

hist_tbl = ''.join(f"<tr><td>{esc(h['day'])}</td><td>{esc(h['pkg'])}</td><td class='num'>{h['tps']:.2f}</td><td class='num'>{h['prefill']:.0f}</td><td class='num'>{fmt(h['ttft'])}</td></tr>" for h in N['amx_history'])

MERGES = [
 ('4709','feat(rinzler): wire Qwen protocol into HF token processor','positron-mark','10-08 03:12','src/rinzler.cpp, rinzler/hf-token-processor.cpp, rinzler-config.hpp, tests','partly: the request path of rinzler (the serving program) for every model, but the new branches are Qwen-specific','low'),
 ('3906','Export: separate Ministral query scaling from RoPE and refuse unloaded parameters','ishapira-positron','10-08 03:30','ingest/export/*.py, ingest/runtime/*','no: model conversion tooling (Python)','none'),
 ('4719','Name the threads, stripes and lanes of host kernels','mitchelldalvirosen-positron','10-08 15:17','h/tron/models/kernel_strategy.hpp, ingest/src/TronCpp.hs, t/','no: kernel_strategy.hpp is included only by generated plugins (ingested-* models), not by the hand-written llama plugin','none'),
 ('4723','Run striped host kernel loops through tron::striped_loop','mitchelldalvirosen-positron','10-08 15:57','kernel_strategy.hpp, TronCpp.hs, t/, config/test-benchmarks.json','no: same reason as 4719; test-benchmarks.json is unit-test timing data','none'),
 ('4784','Skip the weight-command lock when TX has nothing to post','mitchelldalvirosen-positron','10-08 16:19','src/pos/worker.cpp (42+/39−)','yes: the FPGA matmul launch path (tx_launch) used by every model; changes when a request\'s weight commands are posted while another request is being prepared on the same card','2'),
 ('3907','Ingest: reach RopeParameters by name, not by position','ishapira-positron','10-08 16:40','ingest/src/*.hs, ingest/test/*','no: ingest compiler internals (Haskell)','none'),
 ('4366','Round BF16 stores to nearest even','rbjarnason-positron','10-08 18:01','h/tron/simd/bf16.hpp, h/tron/kernels/wide.hpp, h/tron/tensor/v_vnni.hpp, h/common/numerics/bf16.hpp, emulation/matmul.hpp, mixture_of_experts.hpp, TronCpp.hs, tests','yes: the FP32-to-BF16 store used by the llama host kernels (RMSNorm, residual adds) and the V-cache row writes on the AMX attention path; numerics change for every CPU store','1'),
 ('4801','help python find the correct packages directory','positron-arya','10-08 18:09','nix/perfetto-config-schema.nix','no: build tooling','none'),
 ('4782','Launch one card\'s expert matmul jobs','mitchelldalvirosen-positron','10-08 18:46','h/tron/models/mixture_of_experts.hpp, t/','no: mixture-of-experts only; llama-3.1-8b is a dense model','none'),
 ('3393','Ingest: represent Ministral query scaling in RoPE metadata','ishapira-positron','10-08 21:48','ingest/src/*.hs, ingest/test/*','no: ingest compiler internals (Haskell)','none'),
]
merge_rows = ''.join(f"<tr class='{ 'cand' if m[6] in ('1','2') else ''}'><td><a href='https://github.com/positron-ai/tron/pull/{m[0]}'>#{m[0]}</a></td><td>{esc(m[1])}</td><td>{esc(m[2])}</td><td>{esc(m[3])}</td><td class='files'>{esc(m[4])}</td><td>{esc(m[5])}</td><td class='num'>{esc(m[6])}</td></tr>" for m in MERGES)

below_min = [(r['row'], 100*(r['tps_1009']/r['tps_base_min']-1)) for r in N['all_rows'] if r['tps_base_min'] > 0 and r['tps_1009'] < r['tps_base_min']]
below_items = ''.join(f"<li>{esc(n)}: {p:+.1f} % against its eight-night minimum</li>" for n, p in below_min)

page = f"""<title>AMX Nightly Regression 2026-10-09</title>
<style>
/* Layout: one 760 px reading column; figures sit on a lighter chart surface inside the page plane. Single light theme by the owner's house rule. */
:root {{ color-scheme: light;
  --page:#f9f9f7; --surface:{SURF}; --ink:{INK}; --ink2:{INK2}; --muted:{MUTED}; --grid:{GRID}; --axis:{AXIS};
  --blue:{BLUE}; --orange:{ORANGE}; --aqua:{AQUA}; --gray:{GRAY}; --red:{RED}; --band:rgba(42,120,214,0.10);
  --font:system-ui,-apple-system,"Segoe UI",sans-serif; --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace; }}
body {{ background:var(--page); color:var(--ink); font-family:var(--font); font-size:15px; line-height:1.5; margin:0; padding-block:24px 64px; padding-inline:16px; }}
main {{ max-width:800px; margin:0 auto; }}
h1 {{ font-size:28px; line-height:1.2; margin:0 0 6px; text-wrap:balance; font-weight:650; }}
h2 {{ font-size:20px; margin:40px 0 10px; font-weight:650; text-wrap:balance; }}
h3 {{ font-size:16px; margin:22px 0 6px; font-weight:650; }}
p, li {{ max-width:70ch; }}
.sub {{ color:var(--ink2); margin:0 0 18px; }}
.short {{ background:var(--surface); border:1px solid var(--grid); border-left:4px solid var(--blue); padding:14px 18px; margin:18px 0 8px; }}
.short h2 {{ margin:0 0 6px; font-size:16px; }}
.short p {{ margin:0; }}
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px; margin:14px 0 6px; }}
.kpi {{ background:var(--surface); border:1px solid var(--grid); padding:12px 14px; }}
.kpi .lab {{ font-size:12px; color:var(--ink2); text-transform:uppercase; letter-spacing:0.04em; }}
.kpi .val {{ font-size:26px; font-weight:650; margin-top:2px; }}
.kpi .d {{ font-size:13px; color:var(--ink2); }}
.kpi.bad .val {{ color:var(--red); }}
figure {{ margin:16px 0 6px; }}
.cw {{ overflow-x:auto; }}
.chart {{ width:100%; min-width:600px; height:auto; display:block; border:1px solid var(--grid); box-sizing:border-box; }}
figcaption {{ font-size:13px; color:var(--ink2); margin-top:8px; max-width:none; }}
.tick {{ font-size:11px; fill:var(--muted); font-variant-numeric:tabular-nums; }}
.note {{ font-size:11px; fill:var(--ink2); }}
.vlabel {{ font-size:12px; font-weight:600; font-variant-numeric:tabular-nums; }}
.callout {{ font-size:12px; font-weight:650; }}
.rowlabel {{ font-size:12px; }}
.axis-title {{ font-size:11px; fill:var(--muted); }}
.mark {{ cursor:default; }}
#tip {{ position:fixed; pointer-events:none; background:var(--ink); color:#fff; font-size:12px; padding:6px 9px; border-radius:3px; max-width:320px; display:none; z-index:9; }}
table {{ border-collapse:collapse; width:100%; font-size:13px; margin:10px 0; }}
.tw {{ overflow-x:auto; }}
th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--grid); vertical-align:top; }}
th {{ color:var(--ink2); font-weight:600; }}
td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
td.files {{ font-family:var(--mono); font-size:11.5px; }}
tr.cand td {{ background:rgba(42,120,214,0.07); }}
code {{ font-family:var(--mono); font-size:0.92em; background:rgba(11,11,11,0.05); padding:1px 4px; border-radius:2px; overflow-wrap:anywhere; }}
p, li, dd, figcaption, td {{ overflow-wrap:anywhere; }}
main {{ min-width:0; }}
dl {{ display:grid; grid-template-columns:max-content 1fr; gap:4px 14px; font-size:14px; }}
dt {{ font-weight:600; }} dd {{ margin:0; max-width:70ch; }}
.legend {{ display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color:var(--ink2); margin:6px 0 0; }}
.legend span::before {{ content:""; display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:-1px; background:var(--c); }}
.ok {{ color:#006300; font-weight:600; }} .bad {{ color:var(--red); font-weight:600; }}
a {{ color:var(--blue); }}
@media (max-width:480px) {{ dl {{ grid-template-columns:1fr; }} h1 {{ font-size:24px; }} }}
</style>
<main>
<h1>AMX nightly regression, 2026-10-09</h1>
<p class="sub">Why the monitor emailed "AMX CI/CD perf regressed", how large the change is, and which of the ten tron merges between the two nightly packages could explain it. Written 2026-10-09 by Claude for jhan. All times UTC.</p>

<div class="short"><h2>Short version</h2>
<p>The email fired on the AMX row's prefill number, 343 tokens per second against the monitor's minimum of 353. The only metric that moved is that test's time to first token, up from 11,517 ms to 11,931 ms (+3.6 %), with decode and every other row inside their normal ranges. Two merges touch this code path (#4366, #4784), but the old package re-measured today was also slow (11,814 ms), so a back-to-back A/B of the two packages on delphi-3bda must decide between code and machine.</p></div>

<h2>Words used here</h2>
<dl>
<dt>AMX row</dt><dd>The nightly test "llama-3.1-8b-instruct-good-tp2 @32u per machine (AMX benchmark)": 32 concurrent users, 4,096-token prompts, 1,536 generated tokens, on delphi-3bda (the Intel Xeon 6 CI machine). AMX is Intel Advanced Matrix Extensions, the CPU matrix instructions tron's attention kernel uses for this model shape.</dd>
<dt>TTFT</dt><dd>Time to first token, in ms: how long a user waits for the first generated token. It covers the queue wait plus the prompt processing (prefill).</dd>
<dt>prefill≈</dt><dd>The Slack report's prompt-processing rate, computed as prompt length / TTFT (4,096 tokens / TTFT). It is the same measurement as TTFT in another unit.</dd>
<dt>TPS</dt><dd>Decode rate: generated tokens per second per user, averaged over the run.</dd>
<dt>nightly, package</dt><dd>The System CI run of positron-ai/systems_test that starts at about 03:45 UTC. It installs that day's tron Debian package, named by date and tron main commit, for example 2026.10.09-26b6df7d.</dd>
<dt>be0d5565, 26b6df7d</dt><dd>The tron main commits of the 10-08 and 10-09 packages. The ten merges listed below are the commits between them.</dd>
<dt>the monitor</dt><dd>The 07:00 PDT cron job in ~/workspace/random/amx-ci-monitor/check.py. It reads the Slack line and emails "regressed" when decode TPS &lt; 32.3 or prefill &lt; 353 tok/s.</dd>
<dt>campaign</dt><dd>One of jhan's own measurement runs on delphi-3bda (exec/pr4424ci-20261009). It drives the nightly's own client code (systems_test at commit 14f0ce4, the same as the 10-09 nightly) from claude-agentsrv against engines started by platformd, exactly as the nightly does.</dd>
<dt>first-token order</dt><dd>Within one round of 32 simultaneous requests, the position in which a request received its first token (1 = earliest, 32 = last).</dd>
</dl>

<h2>1. What the email measured</h2>
<div class="kpis">
<div class="kpi bad"><div class="lab">prefill≈ (email trigger)</div><div class="val">343 tok/s</div><div class="d">10-08: 356 · monitor minimum 353 · <span class="bad">below</span></div></div>
<div class="kpi"><div class="lab">TTFT</div><div class="val">11,931 ms</div><div class="d">10-08: 11,517 · +{fmt(D['ttft_ms'])} ms (+{D['ttft_pct']:.1f} %)</div></div>
<div class="kpi"><div class="lab">decode TPS</div><div class="val">32.56</div><div class="d">10-08: 32.71 ({D['tps_pct']:+.1f} %) · monitor min 32.3 · CI threshold 31.00 · <span class="ok">pass</span></div></div>
<div class="kpi"><div class="lab">slowest user TPS</div><div class="val">32.05</div><div class="d">10-08: 32.41 · CI threshold 30.50 · <span class="ok">pass</span></div></div>
</div>
<p>The nightly's own thresholds passed (105 % of 31.00 TPS). The email came from the monitor's stricter prefill minimum. The two numbers are one measurement: prefill 343 tok/s is 4,096 tokens divided by a TTFT of 11.93 s.</p>
<figure><div class="cw">{fig_history()}</div>
<figcaption>Figure 1. TTFT of the AMX row for the 14 nights the monitor has stored (2026-09-25 to 10-09). The shaded band is the range of the first 13 nights. The dashed line is where the monitor's prefill minimum sits once converted to TTFT. The 10-09 point is {fmt(D['ttft_vs_base_mean'])} ms above the 13-night mean, about {D['ttft_sd_units']:.0f} standard deviations. Hover a point for its package and numbers.</figcaption></figure>
<p>One side finding about the monitor itself. Its prefill minimum of 353 tok/s equals a TTFT of {fmt(M['ttft_at_prefill_min'])} ms. The slowest normal night (10-01) had 11,612 ms, or 352.7 tok/s. It passed only through the Slack line's rounding to 353. The minimum therefore has about 0.1 % of headroom over the observed normal range. A night that is 1 standard deviation slow would also email.</p>

<h2>2. Nothing else moved</h2>
<figure><div class="cw">{fig_rows()}</div>
<figcaption>Figure 2. For every perf row, the change of TTFT from 10-08 to 10-09 (dot) and where the eight nights 10-01 to 10-08 fell relative to 10-08 (bar). Only the AMX row sits outside its own range. The 70b tp2 4-user row is omitted. Its TTFT varies by 50 % from night to night, and one baseline night failed.</figcaption></figure>
<p>Decode rates tell the same story. The AMX row's 32.56 TPS is inside its 13-night range (32.40 to 32.78). Three rows ended slightly below their eight-night minimum:</p><ul>{below_items}</ul><p>With eight baseline nights, a new value lands outside the range about one time in five by chance. Three such rows out of 14 is therefore not a signal.</p>
<p>The same model's 8-user test with 1,024-token prompts did not move at all: TTFT 660 ms on both nights, 143.37 to 142.56 TPS.</p>
<div class="tw"><table><thead><tr><th>row</th><th class="num">prompt</th><th class="num">TPS 10-08</th><th class="num">TPS 10-09</th><th class="num">TPS range 10-01..08</th><th class="num">TTFT 10-08</th><th class="num">TTFT 10-09</th><th class="num">TTFT range 10-01..08</th></tr></thead><tbody>{rows_tbl}</tbody></table></div>

<h2>3. Where inside the test the time went</h2>
<figure><div class="cw">{fig_rank()}</div>
<figcaption>Figure 3. Each round sends 32 requests at once. Sorting each round's TTFTs and averaging over the 10 rounds gives the TTFT of the 1st, 2nd, ... 32nd user to receive a first token. The first nine users were within about 1 to 2 % of 10-08. From about the 12th user on, every user waited a nearly constant 500 ms longer.</figcaption></figure>
<div class="legend"><span style="--c:{ORANGE}">10-08, package be0d5565</span><span style="--c:{BLUE}">10-09, package 26b6df7d</span></div>
<p>This shape excludes a uniform slowdown of prompt processing. A uniform 3.6 % would have delayed the first user by about 250 ms as well. Instead, the extra 500 ms appears late in the batch. By then the contexts are long, and the early users are already decoding while the later ones are still being prefilled. Both a code change in the mixed prefill-plus-decode phase and a slower machine during that phase fit this shape.</p>

<h2>4. Machine or code?</h2>
<figure><div class="cw">{fig_samepkg()}</div>
<figcaption>Figure 4. TTFT of the AMX test under different packages and days. The two orange points are the <em>same</em> package (be0d5565): 11,517 ms in the 10-08 nightly, 11,814 ms when jhan's campaign re-ran it today with the nightly's own client code. The green points are the campaign's PR 4424 build, which is based on be0d5565 and does not contain the ten merges. Hover for the time of each run.</figcaption></figure>
<p>The campaign method is comparable to the nightly. On 2026-09-20 the same method measured 11,472 to 11,485 ms for an AMX build. The nightlies of the following week measured 11,505 to 11,535 ms. So the method read 20 to 60 ms low then, not 300 ms high. Today it read the old package 297 ms higher than the 10-08 nightly did. Every measurement on this machine after 04:00 UTC on 10-09 lies between 11,794 and 11,931 ms, whatever the package. Every measurement before that lies between 11,470 and 11,612 ms.</p>
<p>That points at the machine, but the evidence is indirect, and the checks below found nothing wrong. All were read on 2026-10-09 between 19:00 and 19:25 UTC while the campaign kept the machine under its normal four-engine load.</p>
<div class="tw"><table><thead><tr><th>check</th><th>result</th></tr></thead><tbody>
<tr><td>Reboot or firmware event</td><td>none: up since 2026-09-15, IPMI event log empty since then</td></tr>
<tr><td>CPU frequency policy</td><td>unchanged: governor performance, energy preference "performance" on all 288 logical CPUs, limits 0.8 to 4.4 GHz, turbo on, Intel Speed Select two-tier policy verified (clos0 = 224, clos3 = 64 CPUs)</td></tr>
<tr><td>Thermal or power limiting now</td><td>none: busy cores at 3,922 MHz on both sockets, package power 376 W and 365 W against a 500 W limit, package temperatures 88 °C and 82 °C, throttle counters unchanged over 15 min under load</td></tr>
<tr><td>Kernel log since 10-08 00:00</td><td>no thermal, machine-check, memory-error, out-of-memory or PCIe messages</td></tr>
<tr><td>FPGA cards</td><td>all 8 links at 16 GT/s x16, no downgrade</td></tr>
<tr><td>Packages installed by the nightly</td><td>only tron differs on the Positron side; Ubuntu updates were tailscale, vault, snapd, sudo, libpng (10-08) and libxml2, libarchive (10-09)</td></tr>
<tr><td>CI harness (systems_test)</td><td>64135b5 → 14f0ce4: perf and MMLU thresholds, soak log collection; no change to the benchmark client</td></tr>
<tr><td>Engine provisioning</td><td>identical log lines on both nights (4 engines default-0..3, platformd v0.11.0+sst.88b2d3da)</td></tr>
<tr><td>Other users on the machine</td><td>none: Bill's share marker absent, last non-jhan login 2026-09-29; jhan's own 5-minute poller opens a 1 s ssh session</td></tr>
</tbody></table></div>
<p>Insufficient data on two points. The CPU frequency and temperature <em>during</em> the 10-09 nightly test (04:19 to 04:30 UTC) were not recorded. The thermal throttle counters (706 and 630 package events since the 2026-09-15 boot) carry no timestamps.</p>

<h2>5. The ten merges between the two packages</h2>
<p>tron main first-parent commits be0d5565..26b6df7d, in merge order. "Touches this test" means the change is compiled into code that runs the llama-3.1-8b tp2 test on delphi-3bda. That code is the hand-written llama plugin, the AMX attention kernel, the FPGA worker, and rinzler.</p>
<div class="tw"><table><thead><tr><th>PR</th><th>title</th><th>author</th><th>merged (UTC)</th><th>files</th><th>touches this test?</th><th class="num">rank</th></tr></thead><tbody>{merge_rows}</tbody></table></div>
<h3>#4366, Round BF16 stores to nearest even (candidate 1)</h3>
<ul>
<li>Changes every CPU conversion from FP32 to BF16 from truncation to round-to-nearest-even, using the CPU's AVX-512 BF16 instruction. The llama plugin's RMSNorm and residual kernels store BF16 this way, and the V-cache row writes of the AMX attention path go through the changed <code>append_v_row</code> [h/tron/tensor/v_vnni.hpp].</li>
<li>The AMX kernel's own conversion of softmax weights already used the rounding instruction and is unchanged [src/tron/kernels/amx_attn.cpp:239].</li>
<li>The PR measured itself on an AMD host with 4 prompts of 2,048 tokens: prompt processing −0.25 % for ingested-llama-3.1-8b, within noise. It was not measured at 32 users and 4,096 tokens, and not on the Intel AMX path.</li>
<li>The numerics change is visible in the 10-09 nightly: two golden-response functional tests that passed on 10-08 failed on 10-09 (llama-3.1-8b tp4 and qwen-2.5-32b tp4, "response differed from expected"). This shows the change is active in the package. It does not show a speed effect.</li>
</ul>
<h3>#4784, Skip the weight-command lock when TX has nothing to post (candidate 2)</h3>
<ul>
<li>In the FPGA worker, the launch step no longer takes the per-card weight-command mutex when the request's weight commands were already posted at prepare time [src/pos/worker.cpp:2182-2232].</li>
<li>The PR describes the effect as more weight prefetch when one request is prepared while another is launched on the same card. That is exactly the mixed phase in Figure 3, where the late users' extra 500 ms appears. The PR body reports no measurement.</li>
</ul>
<h3>The other eight</h3>
<p>#4719 and #4723 change host-kernel loop helpers that only the generated plugins (ingested-* models) include. #4782 is mixture-of-experts code. #3906, #3907 and #3393 change the ingest compiler. #4801 changes a nix file. #4709 changes rinzler's request path, but every new branch is behind a Qwen check. It stays a low-probability candidate.</p>

<h2>6. What decides it</h2>
<ol>
<li><strong>Back-to-back A/B on delphi-3bda.</strong> Both packages are already saved on the machine as <code>/var/tmp/jhan/pr4424ci-20261009/nightly.deb</code> (be0d5565) and <code>restore.deb</code> (26b6df7d). Run the two llama-3.1-8b configs (8 users / 1,024 and 32 users / 4,096) in the order new, old, new, old with the campaign driver. One pass is about 15 min, so the four passes take about one hour. If 26b6df7d is about 400 ms slower than be0d5565 in the same hour, the code is the cause. If both read about 11.8 s, the machine changed. The running pr4424ci campaign ends at about 20:30 UTC today. The machine is then free until the nightly hold at 01:40 UTC. It is free again after the 10-10 nightly (about 13:40 UTC), where merge4737-precheck2 is already queued at 13:00 UTC.</li>
<li><strong>If the code is the cause,</strong> bisect with two builds of 26b6df7d: one with #4366 reverted, one with #4784 reverted. Each build is one <code>make deb</code> on the machine.</li>
<li><strong>Tomorrow's nightly (10-10)</strong> is one more data point. If its AMX-row TTFT is back near 11,550 ms with a package that still contains the ten merges, the 10-09 value was a machine effect.</li>
<li><strong>Monitor threshold.</strong> Consider lowering the prefill minimum to 350 tok/s (TTFT 11,703 ms, about 4 standard deviations above the mean), or basing it on TTFT directly. Then a normal night does not email.</li>
</ol>

<h2>7. The AMX row, every stored night</h2>
<div class="tw"><table><thead><tr><th>night</th><th>tron package</th><th class="num">TPS</th><th class="num">prefill≈ tok/s</th><th class="num">TTFT ms</th></tr></thead><tbody>{hist_tbl}</tbody></table></div>
<p>The 10-06 package name is missing from the stored Slack text. The 10-04 report was not found by the monitor that day.</p>

<h2>Sources</h2>
<ul>
<li>Monitor logs: ~/workspace/random/amx-ci-monitor/logs/2026-*-fetch.json (full Slack reports) and 2026-10-09-email.json.</li>
<li>Nightly run logs: GitHub Actions runs 37724297930 (10-08) and 37880831014 (10-09) of positron-ai/systems_test, workflow system_ci_granite_rapids_72_rinzler_OCI.yaml. Per-request TTFTs are the "Done (TTFT=...)" lines of the 32-user test.</li>
<li>tron merges: <code>git log --first-parent be0d5565..26b6df7d</code> in ~/workspace/ai-runs/tron-main-ro, and PR bodies and diffs via gh.</li>
<li>Campaign results: ~/workspace/intel-AMX/exec/results/pr4424ci-20261009/{{base-pass1,target-pass1,target-pass2}}/summary.txt and ~/workspace/intel-AMX/exec/results/l8b-8u4k-20260920/canon-pass*/driver.log.</li>
<li>Machine state: read over ssh on delphi-3bda on 2026-10-09 19:00-19:25 UTC (sysfs cpufreq and thermal_throttle, turbostat, lspci, journalctl, intel-speed-select-state verify, ipmitool sel).</li>
<li>Chart colors are the dataviz skill's validated default palette (slots 1 to 3 plus neutral gray). No colors were added.</li>
</ul>
</main>
<div id="tip" role="tooltip"></div>
<script>
(function(){{
  var tip=document.getElementById('tip');
  document.querySelectorAll('.mark').forEach(function(m){{
    m.addEventListener('mouseenter',function(e){{tip.textContent=m.getAttribute('data-tip');tip.style.display='block';}});
    m.addEventListener('mousemove',function(e){{var x=e.clientX+14,y=e.clientY+14;if(x+330>window.innerWidth)x=e.clientX-330;tip.style.left=x+'px';tip.style.top=y+'px';}});
    m.addEventListener('mouseleave',function(){{tip.style.display='none';}});
  }});
}})();
</script>
"""
open(OUT, 'w').write(page)
print(OUT, len(page), 'bytes')
