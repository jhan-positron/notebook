#!/usr/bin/env python3
# Daily status report 2026-08-19 -> ~/workspace/intel-AMX/status-reports/.
# Section 1 = position against the overall plan; then today's results.
# Compilation of already-consensus'd numbers; sources linked, no corrections
# narrative. Charts: computed coordinates, validated palette, zero-based axes.

PUR, TEAL, ORA, MAG = '#7570b3', '#1b9e77', '#d95f02', '#e7298a'
T_PUR, T_MAG = '#eae9f4', '#fdeaf3'
INK2, MUT = '#52514e', '#898781'

def gain_chart():
    # (label, decode gain % vs AVX baseline, prefill gain %)
    rows = [
        ('1 user, ctx 2048', 4.5, 46.2),
        ('1 user, ctx 8192', 16.1, 105.3),
        ('8 users, ctx 2048', 23.0, 44.4),
        ('8 users, ctx 8192', 28.4, 99.8),
    ]
    X0, XW, VMAX = 200.0, 560.0, 110.0
    def X(v): return X0 + v / VMAX * XW
    H = 40 + len(rows) * 62 + 34
    s = [f'<svg viewBox="0 0 980 {H}" width="980" height="{H}" role="img" '
         f'aria-label="AMX gains over the AVX baseline per workload: decode +4.5 to +28.4 '
         f'percent, prefill +44 to +105 percent" font-family="system-ui,sans-serif" font-size="12">']
    for t in (0, 25, 50, 75, 100):
        s.append(f'<line x1="{X(t):.1f}" y1="26" x2="{X(t):.1f}" y2="{H - 30}" stroke="#e1e0d9"/>')
        s.append(f'<text x="{X(t):.1f}" y="{H - 14}" text-anchor="middle" fill="{MUT}" font-size="11">+{t}%</text>')
    s.append(f'<rect x="{X0 - 190}" y="8" width="12" height="12" fill="{MAG}"/>'
             f'<text x="{X0 - 172}" y="18" fill="{INK2}" font-size="11.5">decode (token generation)</text>')
    s.append(f'<rect x="{X0 + 20}" y="8" width="12" height="12" fill="{TEAL}"/>'
             f'<text x="{X0 + 38}" y="18" fill="{INK2}" font-size="11.5">prefill (prompt parsing)</text>')
    for i, (label, dec, pre) in enumerate(rows):
        y = 42 + i * 62
        parts = label.split(', ')
        s.append(f'<text x="{X0 - 12}" y="{y + 10}" text-anchor="end" fill="#0b0b0b" font-weight="600">{parts[0]}</text>')
        s.append(f'<text x="{X0 - 12}" y="{y + 24}" text-anchor="end" fill="{INK2}" font-size="11">{parts[1]}</text>')
        s.append(f'<rect x="{X0}" y="{y}" width="{X(dec) - X0:.1f}" height="15" fill="{MAG}"/>')
        s.append(f'<text x="{X(dec) + 6:.1f}" y="{y + 12}" fill="{MAG}" font-weight="700">+{dec}%</text>')
        s.append(f'<rect x="{X0}" y="{y + 19}" width="{X(pre) - X0:.1f}" height="15" fill="{TEAL}"/>')
        s.append(f'<text x="{X(pre) + 6:.1f}" y="{y + 31}" fill="{TEAL}" font-weight="700">+{pre}%</text>')
    s.append('</svg>')
    return '\n'.join(s)

def chip(state):
    color = {'DONE': '#0ca30c', 'DECIDED': '#0ca30c', 'IN PROGRESS': ORA,
             'FIRST PASS DONE': ORA, 'QUEUED': MUT, 'BLOCKED ON SLOT': '#d03b3b'}[state]
    return (f'<span style="background:{color};color:#ffffff;border-radius:9px;'
            f'padding:1px 9px;font-size:11.5px;font-weight:600;white-space:nowrap;">{state}</span>')

plan_rows = [
    ('P0 &#x2014; microbenchmarks + baselines', 'DONE',
     'Attention is the qwen decode wall at long context (share &#x2248;14/30/64% at ctx 256/2K/8K). Kernel grid measured across width &#xD7; residency; 4+4 PV blocking adopted; AMX clock-license cost &#x2248;8%.'),
    ('P1 &#x2014; sharing instrumentation', 'DONE',
     'Prefill work is 99.9% shared (avg width 110.9); private decode is GQA-only (width 1.02); shared-prompt decode width 5.06. Verdict: P4 batching is justified for shared-prompt + prefill only.'),
    ('P2 &#x2014; kernels inside the real tron code', 'DONE',
     'Three increments shipped behind default-off flags + runtime kill switch: QK on AMX, PV on AMX, and the K-mirror orientation. Formulation DECIDED (Sol consensus): canonical-K is the supported default; mirror is a gated opt-in for pinned AMX hosts. Byte-equivalence unit tests pass.'),
    ('P3 &#x2014; fp32 v* numerics policy', 'QUEUED',
     'Separately flagged change; untouched by the AMX work so far.'),
    ('P4 &#x2014; shared-KV batching (width &#x2265; 8)', 'QUEUED',
     'Justified by P1 data for shared-prompt + prefill. The mirror-vs-canonical default is re-evaluated here with capacity-adjusted, end-to-end results.'),
    ('P5 &#x2014; tuning experiments', 'QUEUED',
     'Per-experiment T4 verdicts. New candidate from this week: move the mirror plane to a separate arena (expected to remove the layout penalty and unlock the mirror kernel&#x27;s full &#x2248;14%).'),
    ('T1 &#x2014; logit tolerance (gate for enable-by-default)', 'FIRST PASS DONE',
     'Full first pass on qwen vs an HF fp32 reference: AMX-vs-AVX max TVD 0.054 (median 0.0000) &#x2014; passes the repo criterion; AMX adds no error on top of tron&#x27;s existing distance from HF. Remaining: T1-owner review of the engine-level HF gap, more prompts/seeds.'),
    ('T2/T3 &#x2014; dispatch/OS tests, CI strategy', 'QUEUED',
     'Before any enable-by-default; needs a non-AMX host for the fallback cases.'),
    ('T4 &#x2014; formal end-to-end A/B', 'BLOCKED ON SLOT',
     'Needs the quiet-machine slot (2 FPGAs, serving down) &#x2014; coordination with Rhys pending.'),
]
plan_html = '\n'.join(
    f'<tr><td>{name}</td><td>{chip(state)}</td><td>{note}</td></tr>'
    for name, state, note in plan_rows)

html = f'''<meta charset="utf-8">
<title>AMX Status 2026-08-19</title>
<style>
body {{ background:#ffffff; color:#0b0b0b; font-family:system-ui,sans-serif;
       max-width:1000px; margin:24px auto; padding:0 20px; line-height:1.55; }}
h1 {{ font-size:24px; margin-bottom:2px; }}
h2 {{ font-size:18px; margin-top:30px; border-bottom:1px solid #e1e0d9; padding-bottom:6px; }}
p.sub {{ color:{INK2}; margin-top:0; }}
table {{ border-collapse:collapse; font-size:13.5px; width:100%; }}
th,td {{ border-bottom:1px solid #e1e0d9; padding:7px 10px 7px 0; text-align:left; vertical-align:top; }}
th {{ color:{INK2}; }}
figure {{ margin:14px 0 4px 0; overflow-x:auto; }}
figcaption {{ font-size:12.5px; color:{INK2}; }}
.take {{ background:#f4f3ef; border-left:4px solid {MAG}; padding:8px 12px; font-size:14px; margin:12px 0; }}
code {{ background:#f4f3ef; padding:1px 4px; font-size:12.5px; }}
.links li {{ font-size:13.5px; }}
</style>
<h1>AMX &#xD7; tron software attention &#x2014; status, 2026-08-19</h1>
<p class="sub">Target: decode throughput of <code>ingested-qwen-3-4b-instruct-2507-tp2</code> on the
Xeon 6 6962P (delphi-3bda), software (CPU) attention only. All numbers below are measured (3 repeats
unless noted) and previously reviewed; sources at the bottom.</p>

<h2>1. Where we are against the overall plan</h2>
<table>
<tr><th style="width:34%">Phase / gate (doc 04)</th><th style="width:13%">State</th><th>Standing</th></tr>
{plan_html}
</table>
<div class="take"><b>One-line position:</b> the kernel phases (P0&#x2013;P2) are complete with the
formulation decided; the work has moved to the qualification gates (T1 under way, T2&#x2013;T4 queued)
and the batching/tuning phases (P4/P5) that decide how far the gains extend.</div>

<h2>2. Measured AMX gains to date (real qwen, same-binary kill-switch A/B)</h2>
<figure>{gain_chart()}</figure>
<figcaption>Gains of the best measured configuration (mirror kernel) over the AVX-512 baseline, per
workload. Decode at 8 users/ctx 8192 = aggregate 114.4 &#x2192; 146.9 tok/s; the 8192-token prompt
parses in half the time. Axis starts at 0. Exact numbers and per-increment breakdowns:
<a href="../rampup/p2-inc1b.html">p2-inc1b.html</a>, <a href="../rampup/p2-inc2.html">p2-inc2.html</a>.</figcaption>

<h2>3. What today added</h2>
<ul>
<li><b>PV on AMX (increment 1b) measured</b>: decode +4.4/+12.0/+16.9% over baseline at 1u/2K, 1u/8K,
8u/2K &#x2014; roughly double the QK-only gains, as modeled.</li>
<li><b>K-mirror orientation (increment 2) built and measured in one night</b>: adds up to +7.7% decode
on top of increment 1b, and the advantage grows with attention share. Its two system costs are now
quantified &#x2014; one third fewer KV pages in the same byte budget, and a slower AVX fallback caused
by the 3-plane block layout alone (root-caused via a layout-only control build + decode-phase
counters: LLC-miss driven, not TLB). A mitigation with a clear mechanism is queued: move the mirror
plane to a separate arena, which should unlock the mirror kernel&#x27;s full &#x2248;14% same-layout gain.</li>
<li><b>Formulation decision closed (Claude + Sol consensus)</b>: canonical-K stays the supported
default; the mirror ships only as a documented opt-in for pinned AMX deployments &#x2014; its kill
switch does not restore canonical-layout AVX performance, and it costs KV capacity.</li>
<li><b>First full T1 numerics pass, on qwen, against an HF fp32 reference</b>: AMX-vs-AVX max TVD
0.054, median 0.0000, 1/148 steps above 0.05 &#x2014; inside the repo&#x27;s own tolerance criterion.
Both arms sit at an identical distance from the HF reference: AMX adds no error on top of the
engine&#x27;s existing gap. Reusable goldens + tooling now exist for future T1 runs.</li>
<li><b>Test obligations advanced</b>: save_k&#x2192;mirror byte-equivalence tests written and passing
(32K+ assertions); per-step logit A/B tool added (<code>t/t_amx_logit_ab.cpp</code>).</li>
<li><b>Documentation</b>: doc 02 gained &#xA7;4b (the transpose in practice, with a three-panel figure)
and &#xA7;6b (precision: what each engine computes, with a data-type diagram) &#x2014; both
Sol-reviewed; all result pages now live in <code>rampup/</code> with a linked index.</li>
</ul>

<h2>4. Next (in order)</h2>
<ul>
<li>Parallel-arena mirror storage (removes the layout penalty; unlocks &#x2248;14%) &#x2014; next window.</li>
<li>Capacity-limit measurements (max users at fixed KV budget, behavior near capacity) &#x2014; needs a quiet slot.</li>
<li>T1 extension (more prompts/seeds; hand the engine-vs-HF gap question to the T1 owners) and T2/T3.</li>
<li>T4 end-to-end A/B &#x2014; waiting on the quiet-machine slot (Rhys).</li>
</ul>

<h2>Sources</h2>
<ul class="links">
<li>Living plan + dated record: <a href="../rampup/04-amx-action-plan.html">04-amx-action-plan.html</a>;
task queue: <code>exec/QUEUE.md</code></li>
<li>Results pages: <a href="../rampup/p2-inc1b.html">increments 1+1b</a> &#xB7;
<a href="../rampup/p2-inc2.html">increment 2 + costs</a> &#xB7;
<a href="../rampup/fused-sweep.html">P0 kernel grid</a> &#xB7;
<a href="../rampup/p0-baseline.html">P0 baseline</a></li>
<li>Design docs: <a href="../rampup/02-tron-decode-amx-plan.html">doc 02</a> (&#xA7;4b transpose,
&#xA7;6b precision) &#xB7; <a href="../rampup/index.html">index</a></li>
<li>Raw data: <code>exec/results/slot1/</code> (txt, logs, logit dumps); T1 goldens:
<code>/scratch/jhan/t1-goldens</code></li>
</ul>
<p style="font-size:12px;color:{MUT}">Compiled 2026-08-19 &#x2248;02:30 UTC from consensus-reviewed
results (Claude Fable 5 + GPT-5.6-Sol via PAL). Mirror naming: the formulation originates from
Bill&#x27;s PR #2934; every implementation and number here is ours (worktree <code>jhan-amx-p0</code>).</p>
'''
import os
os.makedirs('/home/jhan/workspace/intel-AMX/status-reports', exist_ok=True)
out = '/home/jhan/workspace/intel-AMX/status-reports/2026-08-19-amx-status.html'
open(out, 'w').write(html)
bad = sum(1 for b in open(out, 'rb').read() if b > 127)
print('written', out, '| non-ascii:', bad)
