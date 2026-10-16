#!/usr/bin/env python3
"""bench_page.py <out.html> <csv> [<csv> ...]: the chart page of the tail-row micro-benchmark (tail_bench).

Sections: Short version, Words used here, the per-step budget chart (the measured gap against what the tail
visits cost in every cache scenario), small multiples of ns per visit by live rows for every arm and scenario
(kv_mul 4, then kv_mul 8), the comparison with main (dumbbell, 2026-10-13 data chained with round 2), the
exact tables, correctness, method and lineage. Light theme only. Colors = the Okabe-Ito set used by
gen_report.py. The CSVs are repeat runs; every cell is the median over the runs of the run's median.
"""
import html
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_tables  # noqa: E402

ARMS = ['dotter', 'reader', 'rowbat', 'xpose', 'tmpblk']
ARM_LABEL = {'dotter': 'dotter (the fix)', 'reader': 'reader (PR 3)', 'rowbat': 'rowbat (candidate)',
             'xpose': 'xpose (candidate)', 'tmpblk': 'tmpblk (candidate)'}
COLOR = {'dotter': '#0072B2', 'reader': '#E69F00', 'rowbat': '#009E73', 'xpose': '#CC79A7', 'tmpblk': '#000000',
         'PR 3': '#E69F00', 'PR 4': '#D55E00', 'fix': '#0072B2', 'main': '#009E73', 'gap': '#D55E00'}
DASH = {'dotter': '', 'reader': '', 'rowbat': '6 3', 'xpose': '2 3', 'tmpblk': '8 3 2 3'}
SCEN = [('hot', 'hot: block and query in the core\'s own L1 cache'),
        ('step', 'step: another core wrote the newest token, the rest comes from L3 (one decode step)'),
        ('alldirty', 'alldirty: another core wrote all live tokens just before the visit'),
        ('flush', 'flush: the block\'s 64 cache lines were flushed to memory')]
SCEN_SHORT = dict(SCEN)

# Comparison with main (kill switch, CPU attention, qwen-3-4b, 8 users, 3 repetitions). Measured rows from
# exec/results/pr4off-E-cpu/summary.md (2026-10-13, main 72308ec90c); the fix row is chained from round 2
# (fixoff vs newoff, exec/results/i4934-E2-cpu) onto newoff vs baseoff and is an estimate.
MAIN_CELLS = ['tp2, prompt 1024', 'tp2, prompt 8192', 'tp4, prompt 1024']
MAIN_TPS = {'PR 3': [4.1, 5.5, -0.0], 'PR 4': [0.7, 2.7, -0.5], 'fix': [2.8, 5.2, 0.1]}
MAIN_TTFT = {'PR 3': [-2.1, -4.5, -3.4], 'PR 4': [-2.0, -4.1, -2.7], 'fix': [-2.0, -4.2, -2.7]}
MAIN_EST = {'fix'}


def esc(s):
    return html.escape(str(s), quote=True)


def signed(v, d=0):
    return ('+' if v >= 0 else '-') + f'{abs(v):.{d}f}'


def med(cells, sc, arm, kv, n):
    v = cells.get((sc, arm, kv, n), [])
    return statistics.median(v) if v else None


def mean_over_n(cells, sc, arm, kv):
    vals = [med(cells, sc, arm, kv, n) for n in range(1, 16)]
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def spread_pct(cells, sc, arm, kv, n):
    v = cells.get((sc, arm, kv, n), [])
    if len(v) < 2:
        return 0.0
    return (max(v) - min(v)) / statistics.median(v) * 100


def budget_chart(cells):
    """Horizontal bars, us per decode step: the measured gap against the tail visits' cost difference."""
    rows = [('measured gap, fix vs PR 3 (round 2)', bench_tables.STEP['gap_us'], 'gap', False)]
    for sc, _ in SCEN:
        d = mean_over_n(cells, sc, 'dotter', 4) - mean_over_n(cells, sc, 'reader', 4)
        rows.append((f'tail visits, scenario {sc}', d * bench_tables.STEP['visits_per_worker'] / 1000, 'dotter', True))
    W, L, R, row_h, top = 760, 240, 300, 30, 20
    H = top + row_h * len(rows) + 56
    lo, hi = min(min(r[1] for r in rows), 0) - 15, max(r[1] for r in rows) + 15
    x = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="per-step budget: the measured gap against the tail visits">']
    s.append(f'<line x1="{x(0):.1f}" y1="{top - 8}" x2="{x(0):.1f}" y2="{top + row_h * len(rows)}" stroke="#5b6470"/>')
    for i, (label, v, c, est) in enumerate(rows):
        y = top + row_h * i
        x0, x1 = sorted((x(0), x(v)))
        s.append(f'<text x="{L - 10}" y="{y + row_h / 2 + 4}" text-anchor="end" font-size="12" fill="#1b1f23">{esc(label)}</text>')
        s.append(f'<rect x="{x0:.1f}" y="{y + 6}" width="{max(x1 - x0, 1):.1f}" height="{row_h - 12}" fill="{COLOR[c]}"/>')
        lx, anchor = x1 + 6, 'start'
        unit = ' us per step' + (' (dotter minus reader, est. from the benchmark)' if est else ' (measured)')
        s.append(f'<text x="{lx:.1f}" y="{y + row_h / 2 + 4}" text-anchor="{anchor}" font-size="12" fill="#1b1f23">{signed(v, 1)}{unit}</text>')
    ay = top + row_h * len(rows) + 10
    s.append(f'<line x1="{L}" y1="{ay}" x2="{W - R}" y2="{ay}" stroke="#d0d7de"/>')
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        s.append(f'<line x1="{x(v):.1f}" y1="{ay}" x2="{x(v):.1f}" y2="{ay + 4}" stroke="#d0d7de"/>'
                 f'<text x="{x(v):.1f}" y="{ay + 16}" text-anchor="middle" font-size="10" fill="#5b6470">{v:.0f}</text>')
    s.append(f'<text x="{W - R}" y="{ay + 30}" text-anchor="end" font-size="11" fill="#5b6470">us per decode step per attention worker (57.6 tail visits per worker per step)</text>')
    s.append('</svg>')
    return ''.join(s)


def lines_panel(cells, sc, kv, ymax):
    W, H, L, R, T, B = 480, 300, 52, 130, 28, 36
    x = lambda n: L + (n - 1) / 14 * (W - L - R)
    y = lambda v: T + (1 - v / ymax) * (H - T - B)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="scenario {esc(sc)}, kv_mul {kv}: ns per visit by live rows">']
    s.append(f'<text x="{L}" y="16" font-size="13" font-weight="600" fill="#1b1f23">scenario {esc(sc)}, kv_mul {kv}</text>')
    for k in range(5):
        v = ymax * k / 4
        s.append(f'<line x1="{L}" y1="{y(v):.1f}" x2="{W - R}" y2="{y(v):.1f}" stroke="#eceff2"/>'
                 f'<text x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="10" fill="#5b6470">{v:,.0f}</text>')
    for n in (1, 5, 10, 15):
        s.append(f'<text x="{x(n):.1f}" y="{H - B + 14}" text-anchor="middle" font-size="10" fill="#5b6470">{n}</text>')
    s.append(f'<text x="{(L + W - R) / 2:.1f}" y="{H - 6}" text-anchor="middle" font-size="11" fill="#5b6470">live rows n in the tail block (1 to 15)</text>')
    s.append(f'<text transform="translate(12,{(T + H - B) / 2:.0f}) rotate(-90)" text-anchor="middle" font-size="11" fill="#5b6470">ns per visit (median)</text>')
    ends = []
    for arm in ARMS:
        pts = [(n, med(cells, sc, arm, kv, n)) for n in range(1, 16)]
        pts = [(n, v) for n, v in pts if v is not None]
        if not pts:
            continue
        d = ' '.join(f'{x(n):.1f},{y(min(v, ymax)):.1f}' for n, v in pts)
        dash = f' stroke-dasharray="{DASH[arm]}"' if DASH[arm] else ''
        width = 2.5 if arm in ('dotter', 'reader') else 1.6
        s.append(f'<polyline points="{d}" fill="none" stroke="{COLOR[arm]}" stroke-width="{width}"{dash}>'
                 f'<title>{esc(ARM_LABEL[arm])}: ' + ', '.join(f'n={n} {v:.0f} ns' for n, v in pts) + '</title></polyline>')
        ends.append((arm, pts[-1][1]))
    # direct labels at the right end, pushed apart so they do not overlap
    ends.sort(key=lambda e: e[1])
    ys = [y(min(v, ymax)) for _, v in ends]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + 13) if ys[i] < ys[i - 1] + 13 else ys[i]
    for i in range(len(ys) - 1, -1, -1):
        pass
    ys = ys[::-1]
    for i in range(1, len(ys)):
        if ys[i] > ys[i - 1] - 13:
            ys[i] = ys[i - 1] - 13
    ys = ys[::-1]
    for (arm, v), yy in zip(ends, ys):
        s.append(f'<text x="{W - R + 6}" y="{yy + 4:.1f}" font-size="11" fill="{COLOR[arm]}">{esc(arm)} {v:,.0f}</text>')
    dm, rm = mean_over_n(cells, sc, 'dotter', kv), mean_over_n(cells, sc, 'reader', kv)
    s.append(f'<text x="{W - R - 4}" y="{T + 12}" text-anchor="end" font-size="11" fill="none" stroke="#fff" stroke-width="4">dotter minus reader, mean over n: {signed(dm - rm)} ns</text>')
    s.append(f'<text x="{W - R - 4}" y="{T + 12}" text-anchor="end" font-size="11" fill="#1b1f23">dotter minus reader, mean over n: {signed(dm - rm)} ns</text>')
    s.append('</svg>')
    return ''.join(s)


def dumbbell(title, data, unit_note):
    W, L, R, row_h, top = 900, 150, 330, 34, 24
    H = top + row_h * len(MAIN_CELLS) + 58
    vals = [v for vs in data.values() for v in vs]
    lo, hi = min(vals + [0]) - 1.0, max(vals + [0]) + 1.0
    x = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">']
    s.append(f'<text x="{L}" y="14" font-size="13" font-weight="600" fill="#1b1f23">{esc(title)}</text>')
    s.append(f'<line x1="{x(0):.1f}" y1="{top - 4}" x2="{x(0):.1f}" y2="{top + row_h * len(MAIN_CELLS)}" stroke="{COLOR["main"]}" stroke-width="2"/>')
    s.append(f'<text x="{x(0):.1f}" y="{top + row_h * len(MAIN_CELLS) + 14}" text-anchor="middle" font-size="11" fill="{COLOR["main"]}">main = 0</text>')
    for i, cell in enumerate(MAIN_CELLS):
        yy = top + row_h * i + row_h / 2
        s.append(f'<text x="{L - 10}" y="{yy + 4}" text-anchor="end" font-size="12" fill="#1b1f23">{esc(cell)}</text>')
        xs = [x(data[a][i]) for a in data]
        s.append(f'<line x1="{min(xs):.1f}" y1="{yy}" x2="{max(xs):.1f}" y2="{yy}" stroke="#d0d7de" stroke-width="2"/>')
        labels = []
        for a in data:
            v = data[a][i]
            est = a in MAIN_EST
            fill = '#fff' if est else COLOR[a]
            s.append(f'<g><title>{esc(a)}: {signed(v, 1)} % vs main{" (est.)" if est else ""}</title>'
                     f'<circle cx="{x(v):.1f}" cy="{yy}" r="6" fill="{fill}" stroke="{COLOR[a]}" stroke-width="2.5"/></g>')
            labels.append(f'{a} {signed(v, 1)} %{" est." if est else ""}')
        s.append(f'<text x="{W - R + 8}" y="{yy + 4}" font-size="11" fill="#1b1f23">{esc(", ".join(labels))}</text>')
    ay = top + row_h * len(MAIN_CELLS) + 26
    s.append(f'<line x1="{L}" y1="{ay}" x2="{W - R}" y2="{ay}" stroke="#d0d7de"/>')
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        s.append(f'<line x1="{x(v):.1f}" y1="{ay}" x2="{x(v):.1f}" y2="{ay + 4}" stroke="#d0d7de"/>'
                 f'<text x="{x(v):.1f}" y="{ay + 15}" text-anchor="middle" font-size="10" fill="#5b6470">{(v if abs(v) >= 0.5 else 0.0):+.0f}</text>')
    s.append(f'<text x="{(L + W - R) / 2:.1f}" y="{ay + 30}" text-anchor="middle" font-size="11" fill="#5b6470">{esc(unit_note)}</text>')
    s.append('</svg>')
    return ''.join(s)


def table_html(cells, sc, kv, paths):
    h = ['<table><thead><tr><th>n</th>' + ''.join(f'<th>{esc(a)}</th>' for a in ARMS) + '<th>dotter minus reader</th><th>run spread</th></tr></thead><tbody>']
    for n in range(1, 16):
        vals = {a: med(cells, sc, a, kv, n) for a in ARMS}
        if all(v is None for v in vals.values()):
            continue
        sp = max(spread_pct(cells, sc, a, kv, n) for a in ARMS)
        d = vals['dotter'] - vals['reader']
        h.append(f'<tr><td>{n}</td>' + ''.join(f'<td>{vals[a]:,.0f}</td>' if vals[a] is not None else '<td>-</td>' for a in ARMS)
                 + f'<td>{signed(d)}</td><td>{sp:.0f} %</td></tr>')
    means = {a: mean_over_n(cells, sc, a, kv) for a in ARMS}
    h.append('<tr class="mean"><td>mean over n</td>' + ''.join(f'<td>{means[a]:,.0f}</td>' for a in ARMS)
             + f'<td>{signed(means["dotter"] - means["reader"])}</td><td></td></tr>')
    h.append('</tbody></table>')
    return ''.join(h)


CSS = """
  :root { --bg:#ffffff; --ink:#1b1f23; --muted:#5b6470; --line:#d0d7de; --panel:#f6f8fa; --short:#f3f7fb; color-scheme: light; }
  html { background:var(--bg); }
  body { margin:0; padding-block:24px; padding-inline:16px; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; max-width:1040px; margin-inline:auto; }
  h1 { font-size:24px; margin:0 0 8px; } h2 { font-size:19px; margin:32px 0 8px; border-top:1px solid var(--line); padding-top:16px; } h3 { font-size:15px; margin:14px 0 6px; }
  .short { background:var(--short); border-left:4px solid #0072B2; padding:10px 14px; margin:12px 0 18px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(440px, 1fr)); gap:14px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px; }
  .panel svg, .wide svg { width:100%; height:auto; display:block; }
  .wide { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px; }
  .take { margin:8px 0 0; font-size:14px; color:var(--ink); }
  table { border-collapse:collapse; font-size:13px; margin:8px 0 14px; width:100%; }
  th, td { border:1px solid var(--line); padding:3px 7px; text-align:right; white-space:nowrap; } th:first-child, td:first-child { text-align:left; }
  tr.mean td { font-weight:600; background:var(--short); }
  .legend span { display:inline-block; margin-right:14px; font-size:13px; } .legend i { display:inline-block; width:22px; height:3px; vertical-align:middle; margin-right:5px; }
  ul { padding-left:22px; } li { margin:3px 0; }
  code { background:var(--panel); padding:1px 4px; border-radius:3px; font-size:13px; }
  details summary { cursor:pointer; font-weight:600; margin:10px 0; }
"""


def main():
    out, paths = sys.argv[1], sys.argv[2:]
    cells, checks, header = bench_tables.load(paths)
    step = bench_tables.STEP
    d_step = {sc: mean_over_n(cells, sc, 'dotter', 4) - mean_over_n(cells, sc, 'reader', 4) for sc, _ in SCEN}
    per_step = {sc: d * step['visits_per_worker'] / 1000 for sc, d in d_step.items()}
    best = {}
    for sc, _ in SCEN:
        cands = {a: mean_over_n(cells, sc, a, 4) for a in ('rowbat', 'xpose', 'tmpblk')}
        best[sc] = min(cands, key=cands.get)
    ymax4 = max(med(cells, sc, a, 4, n) or 0 for sc, _ in SCEN for a in ARMS for n in range(1, 16))
    ymax8 = max(med(cells, sc, a, 8, n) or 0 for sc, _ in SCEN for a in ARMS for n in range(1, 16))
    ymax4 = (int(ymax4 * 1.12 / 500) + 1) * 500
    ymax8 = (int(ymax8 * 1.12 / 500) + 1) * 500
    worst_check = max(float(v) for v in checks.values())
    legend = '<p class="legend">' + ''.join(
        f'<span><i style="background:{COLOR[a]}"></i>{esc(ARM_LABEL[a])}</span>' for a in ARMS) + '</p>'

    h = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>Tail-row micro-benchmark</title><style>{CSS}</style></head><body>']
    h.append('<h1>Issue #4934: the tail-row score paths, measured one visit at a time</h1>')
    h.append('<p style="color:var(--muted)">tail_bench on delphi-3bda, 2026-10-16 13:18 to 13:22 UTC, two runs. Page generated by exec/i4934-20261015/bench/bench_page.py from exec/results/i4934-tailbench/.</p>')
    h.append('<div class="short"><strong>Short version.</strong> '
             'The fix scores the row-major tail rows of a KV page one row at a time (the dotter path), and this benchmark measures that path against PR 3\'s block reader for the same tail block. '
             f'The dotter path is cheaper per visit in every cache scenario, by {signed(d_step["hot"])} ns when hot and by {signed(d_step["step"])} ns in the one-decode-step scenario, '
             f'which is {signed(per_step["hot"], 1)} to {signed(per_step["flush"], 1)} us per decode step in the fix\'s favour against a measured gap of +{step["gap_us"]:.0f} us. '
             'So the tail-row scoring does not cause the remaining 1.1 % decode loss, and a 16-row tail-block kernel has nothing to recover: the best candidate equals the dotter path within '
             f'{abs(mean_over_n(cells, "step", best["step"], 4) - mean_over_n(cells, "step", "dotter", 4)):.0f} ns.</div>')

    h.append('<h2>Words used here</h2><ul>'
             '<li><strong>tron</strong>: the inference program under test. <strong>qwen-3-4b</strong>: the model of every number here (36 layers, 8 KV heads, 4 query heads per KV head).</li>'
             '<li><strong>KV page</strong>: 64 tokens of a user\'s K and V state. <strong>Block</strong>: 16 tokens of a page. <strong>Tail block</strong>: the page\'s newest, incomplete block. <strong>Live rows n</strong>: how many of its 16 tokens exist (1 to 15).</li>'
             '<li><strong>VNNI block</strong>: a block stored in the layout the AVX-512 (Advanced Vector Extensions, 512-bit vectors) bf16 dot-product instruction reads, one token per vector lane, 64 cache lines of 64 bytes. <strong>Row-major row</strong>: one token\'s K vector stored as it is, 256 bytes, 4 cache lines.</li>'
             '<li><strong>PR 3</strong> (#4898): every token is written into its VNNI block at once, so the tail block is always a VNNI block. <strong>PR 4</strong> (#4901): tail blocks stay row-major until complete, then convert. <strong>The fix</strong> (branch jhan-vnnik-5-i4934, head b87d20dd81): PR 4 plus the issue #4934 repairs.</li>'
             '<li><strong>Kill switch</strong>: TRON_AMX_DISABLE=1, the AMX (Advanced Matrix Extensions) kernels off at run time, the AVX reader runs. All decode numbers here are kill-switch numbers.</li>'
             '<li><strong>kv_mul</strong>: query heads per KV head (4 for qwen-3-4b, 8 shown as a second case). <strong>Visit</strong>: one worker scoring one tail block against one KV head\'s query group for one user.</li>'
             '<li><strong>Arms</strong>: <code>dotter</code> = the fix\'s path (kv_mul dot-product objects built per visit, one row at a time). <code>reader</code> = PR 3\'s path (k_vnni::qk_group on the VNNI block, all 16 lanes). '
             '<code>rowbat</code> = candidate: row loaded once, dot products into per-head accumulators. <code>xpose</code> = candidate: rows transposed in registers into VNNI order, then scored like the reader, no memory write. '
             '<code>tmpblk</code> = candidate: rows packed into a temporary VNNI block in memory, then the reader.</li>'
             '<li><strong>TPS</strong>: decode tokens per second per user. <strong>TTFT</strong>: time to the first token (prefill). <strong>est.</strong>: an estimate, not a measurement.</li>'
             '</ul>')

    h.append('<h2>1. The per-step budget: what the gap needs against what the tail visits cost</h2>')
    h.append(f'<p>Round 2 measured the fix {step["gap_pct"]} % below PR 3 in decode TPS at tp2 prompt 1024 (kill switch). One decode step takes {step["forward_us"]:,.0f} us there, so the gap is {step["gap_us"]:.0f} us per step. '
             f'Each attention worker makes {step["visits_per_worker"]:.1f} tail visits per step ({step["layers"]} layers x {step["kv_heads_per_engine"]} KV heads per engine x {step["users"]} users / {step["workers"]} workers). '
             f'For the tail-row scoring to explain the gap alone, the dotter path would have to cost {step["gap_us"] / step["visits_per_worker"] * 1000:,.0f} ns more per visit than the reader. The benchmark measures the opposite sign in every scenario.</p>')
    h.append(f'<div class="wide">{budget_chart(cells)}<p class="take">The red bar is the measured loss. The blue bars are what the fix\'s tail visits cost relative to PR 3\'s, converted to one decode step: they are negative in every scenario, so the tail visits save time. The 1.1 % comes from somewhere else.</p></div>')

    h.append('<h2>2. ns per visit by live rows, kv_mul 4 (qwen-3-4b)</h2>')
    h.append('<p>One line per arm. The reader\'s cost does not depend on n: it always reads the whole 4 KB block. The dotter path grows by about 20 ns per live row when hot. Shared y axis across the four scenarios.</p>' + legend)
    h.append('<div class="grid">')
    for sc, desc in SCEN:
        d = d_step[sc]
        h.append(f'<div class="panel">{lines_panel(cells, sc, 4, ymax4)}<p class="take">{esc(desc)}. Mean over n: dotter {mean_over_n(cells, sc, "dotter", 4):,.0f} ns, reader {mean_over_n(cells, sc, "reader", 4):,.0f} ns, '
                 f'difference {signed(d)} ns per visit = {signed(per_step[sc], 1)} us per step. Fastest candidate: {best[sc]} at {mean_over_n(cells, sc, best[sc], 4):,.0f} ns.</p></div>')
    h.append('</div>')

    h.append('<h2>3. ns per visit by live rows, kv_mul 8</h2>')
    h.append('<p>The same with 8 query heads per KV head (llama-class models). Twice the dot products per row, the same picture.</p>' + legend)
    h.append('<div class="grid">')
    for sc, desc in SCEN:
        dm, rm = mean_over_n(cells, sc, 'dotter', 8), mean_over_n(cells, sc, 'reader', 8)
        h.append(f'<div class="panel">{lines_panel(cells, sc, 8, ymax8)}<p class="take">Mean over n: dotter {dm:,.0f} ns, reader {rm:,.0f} ns, difference {signed(dm - rm)} ns per visit.</p></div>')
    h.append('</div>')

    h.append('<h2>4. Comparison with main (kill switch, CPU attention, 3 repetitions)</h2>')
    h.append('<p>No campaign of this issue ran a main arm. The 2026-10-13 campaign did (main 72308ec90c, PR 3 and PR 4 binaries, same cells, exec/results/pr4off-E-cpu). '
             'The fix row is chained: fix vs PR 4 from round 2 (2026-10-16) applied on PR 4 vs main (2026-10-13). The two PR 4 samples differ by at most 0.07 TPS, so the chaining error is small, but the row is an estimate (hollow dots).</p>')
    h.append(f'<div class="wide">{dumbbell("Decode TPS vs main, percent (right of the green line = faster than main)", MAIN_TPS, "decode TPS, percent vs main (hollow dot = est.)")}'
             f'{dumbbell("Prefill TTFT vs main, percent (left of the green line = faster than main)", MAIN_TTFT, "prefill TTFT, percent vs main (hollow dot = est.)")}'
             '<p class="take">Under the kill switch the fix is est. above main in decode TPS in every cell and est. equal to PR 4 in TTFT. AMX on vs main at these cells: insufficient data. No AMX-on main arm exists at these cells. A base and baseoff arm in the next whole-machine round would measure it, about 1 h of machine time.</p></div>')
    h.append('<table><thead><tr><th>vs main</th>' + ''.join(f'<th>{esc(c)}</th>' for c in MAIN_CELLS) + '</tr></thead><tbody>')
    for a in ('PR 3', 'PR 4', 'fix'):
        e = ' (est.)' if a in MAIN_EST else ''
        h.append(f'<tr><td>{a} TPS{e}</td>' + ''.join(f'<td>{signed(v, 1)} %</td>' for v in MAIN_TPS[a]) + '</tr>')
    for a in ('PR 3', 'PR 4', 'fix'):
        e = ' (est.)' if a in MAIN_EST else ''
        h.append(f'<tr><td>{a} TTFT{e}</td>' + ''.join(f'<td>{signed(v, 1)} %</td>' for v in MAIN_TTFT[a]) + '</tr>')
    h.append('</tbody></table>')

    h.append('<h2>5. Exact numbers</h2>')
    h.append(f'<p>Median ns per visit, median over {len(paths)} runs. "run spread" = the largest run-to-run difference of a cell in that row, in percent of its median. Spreads above 10 % occur only in the alldirty and flush scenarios, where the cost is memory traffic.</p>')
    for kv in (4, 8):
        for sc, _ in SCEN:
            h.append(f'<details{" open" if kv == 4 else ""}><summary>scenario {esc(sc)}, kv_mul {kv}</summary>{table_html(cells, sc, kv, paths)}</details>')

    h.append('<h2>6. Correctness</h2>')
    h.append(f'<p>Every arm\'s scores were compared with a double-precision reference for every n before timing. The largest relative error over all arms, both kv_mul values and both runs is {worst_check:.2e} '
             '(bf16 inputs, fp32 accumulation, so a few parts per million is the expected rounding). No arm wrote a score into a dead lane.</p>')
    h.append('<table><thead><tr><th>arm</th><th>kv_mul</th><th>run</th><th>max relative error</th></tr></thead><tbody>')
    for (arm, kv, p), v in sorted(checks.items()):
        h.append(f'<tr><td>{esc(arm)}</td><td>{esc(kv)}</td><td>{esc(p.rsplit("/", 1)[-1])}</td><td>{float(v):.2e}</td></tr>')
    h.append('</tbody></table>')

    h.append('<h2>7. Method and lineage</h2><ul>')
    h.append('<li>Program exec/i4934-20261015/bench/tail_bench.cpp, compiled with the compiler and flags of the fix tree\'s own test t_k_vnni_layout.cpp (clang 19, -O3, -mavx512bf16, the AMX and VNNI defines) inside the nix shell of /var/tmp/jhan/tron-i4934 at b87d20dd81. It includes the tree\'s real kernels: k_vnni::qk_group, dotter, row_major_row, store_row, store_row_major, store_block.</li>')
    h.append(f'<li>{esc(header[0] if header else "")}. The reader core and the writer core are first hyperthreads of socket 1 (our half of the machine) whose siblings were idle. Timing by rdtscp. Per cell the median, p10 and p90 of 20,000 iterations (hot) or 3,000 iterations (other scenarios), the first tenth discarded as warm-up.</li>')
    h.append('<li>Machine state: the nightly CI had released its lease at 13:16 UTC. Two rinzler (production server) processes left by the nightly were running (load average 127 on 288 logical CPUs), pinned to other cores. 13 core pairs of socket 1 were idle. This is not a quiet machine, which is why the cold scenarios show run spreads up to 43 %. The sign of every difference is the same in both runs.</li>')
    h.append('<li>The step scenario is the one that matches decode: the newest token\'s K was just written by another core (the main thread\'s Save K), the older live rows come from L3. For the reader arm the writer uses PR 3\'s per-token scatter store into the VNNI block (store_row), for the row arms the fix\'s row store (store_row_major).</li>')
    h.append('<li>What the benchmark does not cover: the softmax and PV (probability times V) work after the scores, the conversion of a completed block (3.6 us per block, pooled, measured in round 1 traces), the Save K write cost on the main thread (hidden under the workers in both arms, round-1 traces), and any effect of code layout in the full binary.</li>')
    h.append('<li>First launch at 04:11 UTC failed at the link step after the lease was released (libgcc_s not on the command line, undefined _Unwind_Resume). bench-run.sh gained -lgcc_s, and the second launch at 13:17 UTC compiled in 17 s and ran both runs in 97 s each.</li>')
    h.append('</ul>')
    h.append('<h2>8. What this means for the open 1.1 %</h2><ul>')
    h.append('<li>Refuted: the hypothesis that scoring the row-major tail rows one at a time costs the 1.1 % (the round-1 ablation a1 attributed 1.2 % to it). The tail visits are cheaper in the fix than in PR 3 in every cache state measured here.</li>')
    h.append('<li>Why the ablation disagreed, as a labelled hypothesis: ablation a1 forced every live token through the reader, which made the dotter code dead and let the compiler lay out the attention loop differently. The attribution would then be a code-layout effect, not a scoring cost. Test: build the fix with the split decided at run time (an environment variable) so the code stays, and measure a1 again.</li>')
    h.append('<li>Where else to look, with the measurement for each: the round-1 traces put the loss inside the workers\' attention spans (+4.8 ms summed over 20 workers per step at prompt 1024, +215 us on the slowest worker) with the same instruction count and lower IPC, so it is spread over all page visits (about 20,000 per step), not the 1,152 tail visits. Candidate: more cache misses per page visit. Test: perf stat of L2 and LLC misses per attention worker, fix against PR 3 against PR 4, and a count of the page-object cache lines each arm touches per visit.</li>')
    h.append('<li>Option (b), a 16-row tail-block kernel, is not worth building for this gap: rowbat equals the dotter path within 2 to 41 ns per visit, xpose and tmpblk are slower than the dotter path for most n.</li>')
    h.append('</ul>')
    h.append('</body></html>')
    open(out, 'w').write('\n'.join(h))
    print(f'wrote {out}: {os.path.getsize(out):,} bytes')


if __name__ == '__main__':
    main()
