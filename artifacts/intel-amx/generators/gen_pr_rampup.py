#!/usr/bin/env python3
# Generates rampup/pr-rampup.html: project intro for readers new to the AMX
# work, aimed at reviewing PR #3879. Three computed SVGs, collision-audited.
import re

INK, INK2, MUT = '#0b0b0b', '#52514e', '#898781'
PUR, TEAL, ORA, MAG = '#7570b3', '#1b9e77', '#d95f02', '#e7298a'
T_PUR, T_TEAL, T_ORA, T_MAG = '#eae9f4', '#e4f2ed', '#fcebdd', '#fdeaf3'
PALE = '#f4f3ef'

def audit(el, width):
    boxes = []
    for e in el:
        m = re.match(r'<text x="([\d.]+)" y="([\d.]+)" font-size="([\d.]+)" fill="[^"]*" text-anchor="(\w+)"[^>]*>(.*?)</text>', e)
        if not m: continue
        x, y, size, anchor, content = m.groups()
        x, y, size = float(x), float(y), float(size)
        plain = re.sub(r'&#x[0-9A-Fa-f]+;', 'X', content)
        w = len(plain) * size * 0.55
        x0 = x - w if anchor == 'end' else (x - w / 2 if anchor == 'middle' else x)
        boxes.append((x0, y - size * 0.8, x0 + w, y + size * 0.2, plain[:24]))
    n = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[0] < b[2] - 2 and b[0] < a[2] - 2 and a[1] < b[3] - 2 and b[1] < a[3] - 2:
                n += 1; print('OVERLAP:', a[4], 'vs', b[4])
        if boxes[i][2] > width - 4: print('OVERFLOW:', boxes[i][4], boxes[i][2])
    return n

class S:
    def __init__(self): self.el = []
    def t(self, x, y, s, size=11.5, fill=INK, anchor='middle', bold=False):
        w = ' font-weight="600"' if bold else ''
        self.el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}>{s}</text>')
    def r(self, x, y, w, h, fill, stroke, sw=1.4, rx=6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
    def a(self, x1, y1, x2, y2, color=INK2, sw=1.8):
        self.el.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2 - 6:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{sw}"/>')
        self.el.append(f'<path d="M {x2:.1f} {y2:.1f} l -8 -3.5 v 7 z" fill="{color}"/>')
    def render(self, w, h, aria):
        assert audit(self.el, w) == 0
        return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{aria}" '
                f'font-family="system-ui,sans-serif">\n' + '\n'.join(self.el) + '\n</svg>')

# ---- Figure A: the problem ----
f = S()
f.t(14, 22, 'Every decode step (one output token) crosses two machines', size=12.5, anchor='start', bold=True)
f.r(40, 40, 260, 64, T_PUR, PUR)
f.t(170, 62, 'FPGA', size=12, bold=True)
f.t(170, 80, 'all the big weight multiplies', size=10.5, fill=INK2)
f.t(170, 94, '(unchanged by this PR)', size=10, fill=MUT)
f.a(306, 72, 356, 72)
f.r(360, 40, 260, 64, T_MAG, MAG)
f.t(490, 62, 'CPU: software attention', size=12, bold=True)
f.t(490, 80, 'reads every stored K/V token pair', size=10.5, fill=INK2)
f.t(490, 94, 'this PR accelerates THIS box', size=10, fill=MAG, bold=True)
f.t(60, 138, 'Why it matters: the CPU box grows with conversation length', size=12, anchor='start', bold=True)
data = [('ctx 256', 14), ('ctx 2048', 30), ('ctx 8192', 64)]
for i, (lab, pct) in enumerate(data):
    y = 156 + i * 30
    f.t(120, y + 14, lab, size=11, anchor='end', fill=INK2)
    f.r(132, y, 420, 19, PALE, MUT, 1, rx=3)
    f.r(132, y, 420 * pct / 100, 19, MAG, MAG, 1, rx=3)
    f.t(560, y + 14, f'attention &#x2248; {pct}% of the step', size=10.5, anchor='start', fill=MAG, bold=True)
f.t(132, 258, 'At long context, most of each token&#x27;s time is the CPU attention box &#x2014; measured on the target model.',
    size=10.5, anchor='start', fill=INK2)
fig_a = f.render(980, 276, 'A decode step spans the FPGA doing weight multiplies and the CPU doing '
                 'software attention; the attention share of one step grows from 14 percent at context '
                 '256 to 64 percent at context 8192')

# ---- Figure B: what the PR changes ----
f = S()
f.t(14, 22, 'Inside the CPU attention box: work happens page by page (a page = 64 stored tokens)', size=12.5, anchor='start', bold=True)
boxes = [
    (14,  120, 'KV page', 'K and V, bf16,', 'as stored today', PALE, INK2, False),
    (166, 158, 'QK multiply', 'scores = query &#xB7; keys', 'AMX tiles when eligible', T_TEAL, TEAL, True),
    (356, 138, 'softmax', 'scale, max, exp', 'unchanged fp32 code', PALE, INK2, False),
    (526, 158, 'PV multiply', 'output = weights &#xB7; values', 'AMX tiles when eligible', T_TEAL, TEAL, True),
    (716, 150, 'running result', 'v*, s*, m* update', 'unchanged fp32 code', PALE, INK2, False),
]
y0, h = 46, 74
prev_end = None
for x, w, l1, l2, l3, fill, stroke, amx in boxes:
    f.r(x, y0, w, h, fill, stroke, 1.6)
    f.t(x + w / 2, y0 + 20, l1, size=11.5, bold=True)
    f.t(x + w / 2, y0 + 38, l2, size=10, fill=INK2)
    f.t(x + w / 2, y0 + 56, l3, size=10, fill=(TEAL if amx else MUT), bold=amx)
    if prev_end is not None:
        f.a(prev_end, y0 + h / 2, x, y0 + h / 2)
    prev_end = x + w
f.t(14, y0 + h + 30, 'The PR swaps ONLY the two multiplies (teal). The page loop, the softmax, the running-result',
    size=11, anchor='start', fill=INK2)
f.t(14, y0 + h + 45, 'bookkeeping, worker scheduling, and the stored K/V format stay exactly as they are today.',
    size=11, anchor='start', fill=INK2)
f.t(14, y0 + h + 60, '(The opt-in mirror mode ADDS an auxiliary K copy next to this - see the fork below - without touching the stored format.)',
    size=10, anchor='start', fill=MUT)
fig_b = f.render(980, 200, 'The per-page attention pipeline: KV page, QK multiply, softmax, PV multiply, '
                 'running-result update; the PR replaces only the two multiply boxes with AMX tiles when '
                 'eligible, everything else unchanged')

# ---- Figure C: safety chain ----
f = S()
f.t(14, 22, 'Five gates guard every AMX call; a sixth branch applies to mirror builds only', size=12.5, anchor='start', bold=True)
gates = [
    ('build flag', 'TRON_AMX_DISPATCH', 'default OFF'),
    ('CPU + OS check', 'CPUID, XCR0,', 'arch_prctl at runtime'),
    ('kill switch', 'TRON_AMX_DISABLE=1', 'same binary'),
    ('shape check', 'head 128, GQA 4', 'compile-time constant'),
    ('page check', 'full 64-token page,', 'fully visible'),
]
mirror_gate = ('mirror branch', 'arena present?', 'mirror builds only')
bw, gap, y0, h = 148, 10, 44, 66
x = 14
for i, (l1, l2, l3) in enumerate(gates):
    f.r(x, y0, bw, h, T_ORA, ORA, 1.5)
    f.t(x + bw / 2, y0 + 18, l1, size=11, bold=True)
    f.t(x + bw / 2, y0 + 35, l2, size=9.5, fill=INK2)
    f.t(x + bw / 2, y0 + 50, l3, size=9.5, fill=INK2)
    if i < len(gates) - 1:
        f.a(x + bw, y0 + h / 2, x + bw + gap, y0 + h / 2, ORA)
    x += bw + gap
l1, l2, l3 = mirror_gate
f.r(x + 8, y0, bw, h, T_MAG, MAG, 1.5, dash='5 4')
f.t(x + 8 + bw / 2, y0 + 18, l1, size=11, bold=True, fill=MAG)
f.t(x + 8 + bw / 2, y0 + 35, l2, size=9.5, fill=INK2)
f.t(x + 8 + bw / 2, y0 + 50, l3, size=9.5, fill=MAG)
x += 8 + bw + gap
rail_y = y0 + h + 34
f.el.append(f'<line x1="20" y1="{rail_y}" x2="{x - gap - 20}" y2="{rail_y}" stroke="{PUR}" stroke-width="2.5"/>')
for i in range(len(gates)):
    gx = 14 + i * (bw + gap) + bw / 2
    f.el.append(f'<line x1="{gx}" y1="{y0 + h}" x2="{gx}" y2="{rail_y}" stroke="{PUR}" stroke-width="1.4" stroke-dasharray="4 3"/>')
f.t((x - gap + 14) / 2, rail_y + 20, 'any &quot;no&quot; anywhere &#x2192; the unchanged AVX-512 code path runs (canonical AMX never needs the mirror branch)',
    size=11, fill=PUR, bold=True)
f.t((x - gap + 14) / 2, rail_y + 36, 'measured: the kill-switch and fallback arms run at clean-binary speed', size=10, fill=INK2)
fig_c = f.render(980, rail_y + 50, 'Six chained gates: build flag off by default, runtime CPU and OS check, '
                 'kill switch, shape check, full-page check, mirror-arena null check; failing any gate falls '
                 'back to the unchanged AVX-512 path at clean-binary speed')

# Transplant doc 01 section-1 intro (paragraph, bullets, One-P-core figure,
# caption) per the Notion instruction of 2026-08-19.
doc01 = open('rampup/01-amx-rampup.html').read()
m = re.search(
    r'<h2 id="what">1\. What AMX is</h2>\n(.*?)\n<h3>Configuration lifecycle</h3>',
    doc01, re.S)
assert m, 'doc01 section 1 anchor not found'
amx_intro = m.group(1)

html = f'''<meta charset="utf-8">
<title>AMX PR Ramp-up</title>
<style>
body {{ background:#ffffff; color:#0b0b0b; font-family:system-ui,sans-serif;
       max-width:1000px; margin:24px auto; padding:0 20px; line-height:1.55; }}
h1 {{ font-size:23px; margin-bottom:2px; }}
h2 {{ font-size:17px; margin-top:30px; border-bottom:1px solid #e1e0d9; padding-bottom:6px; }}
p.sub {{ color:{INK2}; margin-top:0; }}
figure {{ margin:12px 0 4px 0; overflow-x:auto; }}
.svgwrap {{ overflow-x:auto; background:#fcfcfb; border:1px solid rgba(11,11,11,0.10); border-radius:10px; padding:14px; }}
.cite {{ font-size:11px; color:#898781; font-family:ui-monospace,Menlo,monospace; background:#eef3fa; border-radius:4px; padding:1px 6px; white-space:nowrap; }}
.pill {{ font-size:11px; border-radius:9px; padding:1px 8px; font-weight:600; }}
.pill.meas {{ background:#e4f2ed; color:#1b9e77; }}
figcaption {{ font-size:12.5px; color:{INK2}; }}
table {{ border-collapse:collapse; font-size:13.5px; }}
th,td {{ border:1px solid #d8d6d0; padding:5px 10px; text-align:right; }}
th:first-child, td:first-child {{ text-align:left; }}
th {{ background:{PALE}; }}
dl dt {{ font-weight:600; margin-top:8px; }}
dl dd {{ margin-left:0; color:{INK2}; font-size:13.5px; }}
code {{ background:{PALE}; padding:1px 4px; font-size:12.5px; }}
.take {{ background:{PALE}; border-left:4px solid {TEAL}; padding:8px 12px; font-size:14px; margin:12px 0; }}
</style>
<h1>Ramp-up for reviewing PR #3879: AMX software attention</h1>
<p class="sub">You are new to this project. This page gives you everything needed to review
<a href="https://github.com/positron-ai/tron/pull/3879">the draft PR</a>; its companion,
<a href="pr-walkthrough.html">pr-walkthrough.html</a>, then maps every changed file to the ideas here.</p>

<h2>1. The problem being solved</h2>
<p>tron serves language models by splitting each generated token&#x27;s work between an FPGA (the big
weight multiplies) and the CPU (attention: for every new token, compare its query against every stored
token&#x27;s key, then blend the stored values by those comparison weights). The CPU part reads the
whole conversation history every step, so its share of the time grows with conversation length &#x2014;
at 8K context it IS most of the step.</p>
<figure>{fig_a}<figcaption>Shares measured on the target model (qwen-3-4b, 2 FPGAs, delphi-3bda).
&quot;ctx&quot; = context: how many tokens of history each step reads.</figcaption></figure>

<h2>2. Intel AMX</h2>
{amx_intro}
<p>Two facts from the above matter most for this PR: AMX reads bf16 (the format tron&#x27;s K/V cache
already uses) and accumulates in fp32 (the precision the existing code already uses), so the stored
K/V cache needs no conversion or format change. Small temporary rearrangements do happen inside the
fast path: the 4 query rows are packed once per token, and the softmax weights are rounded to bf16
for the PV multiply, exactly as today&#x27;s AVX-512 code already rounds them. Full primer:
<a href="01-amx-rampup.html">doc 01</a>.</p>

<h2>3. What the PR actually changes</h2>
<figure>{fig_b}<figcaption>One page = 64 stored tokens of one attention head&#x27;s K and V. The page
loop visits every page per generated token.</figcaption></figure>
<div class="take"><b>The one design fork you need to know:</b> the QK multiply can read K two ways.
<b>Canonical-K</b> (the default) reads K exactly as stored today &#x2014; free, but the scores come out
sideways and need a small transpose. The <b>mirror</b> (opt-in, <code>TRON_AMX_K_MIRROR</code>) keeps a
second, pre-rearranged copy of K in a separate memory arena so no transpose is needed &#x2014; faster at
long context, at the cost of extra ordinary RAM (&#x2248;50% of the KV cache&#x27;s size, allocated at cache
setup only when mirror support is built AND the runtime AMX check passes) and more moving parts.
Generating the mirror is cheap and measured: 70 ns per token-row on this machine
(&#x2248;20 &#xB5;s per prefill token across 36 layers &#xD7; 8 heads, spread over the driver workers
&#x2014; and the system-level A/B shows prefill still nets +1&#x2013;2% ahead of a build with no
mirror writes at all; on decode it is &#x2248;0.3&#x2013;0.4% of a step). Both are in this PR; deep details with figures: doc 02
<a href="02-tron-decode-amx-plan.html#pairs">&#xA7;2b</a> (the data layouts) and
<a href="02-tron-decode-amx-plan.html#transpose">&#xA7;4b</a> (the transpose).</div>

<h2>4. The safety model &#x2014; why this is low-risk to merge</h2>
<figure>{fig_c}<figcaption>The mirror&#x27;s extra machinery (write-through at save time, rebuild on
page moves) is exercised by the byte-equivalence tests in the PR.</figcaption></figure>

<h2>5. The evidence (all measured, 2026-08-18/19)</h2>
<table>
<tr><th>decode vs clean binary (Nu = N concurrent users)</th><th>1u/2K</th><th>1u/8K</th><th>8u/2K</th><th>8u/8K</th></tr>
<tr><td>canonical (default candidate)</td><td>+3.8%</td><td>+15.2%</td><td>+19.0%</td><td>+17.5%</td></tr>
<tr><td>mirror-arena (opt-in)</td><td>+4.5%</td><td>+19.6%</td><td>+22.8%</td><td>+28.1%</td></tr>
</table>
<p>Also measured: prefill (prompt reading) up to +105% (mirror, 1 user / ctx 8192).</p>
<ul>
<li><b>Power</b>: package power is flat at 8 users / ctx 8192, yet <b>energy per token drops by
14.5% (canonical) / 21.6% (mirror)</b> &#x2014; no contradiction: energy = power
&#xD7; time. The machine draws the same watts either way, but the AMX arms finish the same tokens in
less time (+18&#x2013;28% tokens per second), so each token costs fewer joules: joules per token =
watts &#xF7; tokens per second.</li>
<li><b>Numerics</b>: two separate comparisons over the same 956 steps. (a) AMX-vs-AVX &#x2014; worst
per-step TVD 0.054 (same TVD definition and per-step comparison the repo&#x27;s golden tests use,
whose outlier cap is 0.30). (b) Each arm vs HF fp32 references &#x2014; AMX sits at the SAME distance
as AVX &#x2014; by this metric it adds no measurable error on top of the engine&#x27;s
pre-existing gap. And when both arms pick tokens
greedily (always take the single highest-scoring token), they chose the SAME token at every compared
step except two &#x2014; and at both exceptions the model&#x27;s top two candidates were nearly
tied (score gaps of 0.031 and exactly 0.000, against a typical gap of 0.27). In plain words:
across these 956 steps the rounding differences only ever tipped choices the model was
near-indifferent about; no confident choice was overturned.</li>
</ul>
<p>Full dated record: <a href="2026-08-19-amx-status.html">the status report</a>.</p>

<h3 style="font-size:15px;">5.1 Model coverage: regression testing beyond qwen</h3>
<p>Two more models ran the same kill-switch A/B (2 repeats each; these are their own measurements,
not derived from the qwen table above). <b>llama-3.1-8b-tp2</b> has the fast path&#x27;s shape
(head size 128, 4 queries per KV head), so it should gain &#x2014; and does.
<b>gpt-oss-20b-tp2</b> has a different attention geometry the fast path cannot serve, so the safety
gates route every page to the unchanged AVX code &#x2014; the right result there is &quot;no
change&quot;, and that is what was measured: the dispatch costs nothing when it cannot fire.</p>
<table>
<tr><th>model / workload</th><th>decode off &#x2192; on</th><th>&#x394;</th><th>prefill off &#x2192; on</th><th>&#x394;</th></tr>
<tr><td>llama-3.1-8b-tp2, 1u/ctx 8192</td><td>111.8 &#x2192; 128.6</td><td><b>+15.0%</b></td><td>541.8 &#x2192; 1027.1</td><td><b>+89.6%</b></td></tr>
<tr><td>llama-3.1-8b-tp2, 8u/ctx 2048</td><td>372.3 &#x2192; 445.6</td><td><b>+19.7%</b></td><td>158.1 &#x2192; 204.2</td><td><b>+29.2%</b></td></tr>
<tr><td>gpt-oss-20b-tp2, 1u/ctx 8192</td><td>199.2 &#x2192; 198.4</td><td>&#x2212;0.4%</td><td>1010.0 &#x2192; 1004.6</td><td>&#x2212;0.5%</td></tr>
<tr><td>gpt-oss-20b-tp2, 8u/ctx 2048</td><td>666.4 &#x2192; 664.2</td><td>&#x2212;0.3%</td><td>270.1 &#x2192; 265.7</td><td>&#x2212;1.6%</td></tr>
</table>

<h2>6. Glossary (plain words)</h2>
<dl>
<dt>Page</dt><dd>64 consecutive stored tokens of one attention head&#x27;s K and V &#x2014; the unit of attention work.</dd>
<dt>KV cache</dt><dd>The stored keys and values of every token seen so far; bf16; lives in host DRAM.</dd>
<dt>dotter / scaled_v</dt><dd>Today&#x27;s AVX-512 code for the QK and PV multiplies &#x2014; what AMX replaces when eligible.</dd>
<dt>Canonical-K</dt><dd>Our name for &quot;K stored the one standard way it is today&quot;, read as-is.</dd>
<dt>Mirror</dt><dd>A second copy of K, pre-rearranged for the tile instructions. The idea comes from Bill&#x27;s PR #2934; the implementation and all numbers here are ours.</dd>
<dt>Arena</dt><dd>The separate ordinary-RAM allocation holding all mirror copies &#x2014; exists only when AMX is available at runtime.</dd>
<dt>Kill switch</dt><dd><code>TRON_AMX_DISABLE=1</code>: same binary, AMX off, measured at clean-binary speed.</dd>
<dt>TVD</dt><dd>Total variation distance: how different two probability distributions are, 0 = identical, 1 = disjoint. The repo&#x27;s existing accuracy tests use it.</dd>
</dl>
<p><b>Next:</b> open <a href="pr-walkthrough.html">pr-walkthrough.html</a> &#x2014; it walks the
PR&#x27;s 12 files and says what to check in each.</p>
'''
# ---- 4.1 attention-geometry callout (jhan request 2026-08-19) ----
# (family, Q heads, KV heads, head width) - model-level constants extracted from
# h/tron/plugins/llama.hpp TRON_LLAMA_CONFIG rows and gen/src/tron/h/tron/plugins/*.hpp,
# families deduped (ingested duplicates fold into one row). mock excluded (test scaffold).
GEOM = [
    ('qwen-3-4b-instruct-2507', 32, 8, 128), ('llama-3.1-8b', 32, 8, 128),
    ('llama-3-8b', 32, 8, 128), ('mistral-7b', 32, 8, 128), ('ministral-8b', 32, 8, 128),
    ('mixtral-8x7b', 32, 8, 128), ('phi-4', 40, 10, 128), ('granite-3.3-8b', 32, 8, 128),
    ('llama-68m', 12, 12, 64), ('llama-2-7b', 32, 32, 128), ('llama-2-13b', 40, 40, 128),
    ('llama-2-70b', 64, 8, 128), ('llama-3-70b', 64, 8, 128), ('llama-3.1/3.3-70b', 64, 8, 128),
    ('llama-3.2-1b', 32, 8, 64), ('llama-3.2-3b', 24, 8, 128), ('mixtral-8x22b', 48, 8, 128),
    ('gemma-2-2b', 8, 4, 256), ('gemma-2-9b', 16, 8, 256), ('gemma-2-27b', 32, 16, 128),
    ('gemma-3-4b', 8, 4, 256), ('gemma-3-27b', 32, 16, 128),
    ('gemma-4-12b', 16, 8, 256), ('gemma-4-31b', 32, 16, 256),
    ('qwen-2.5-32b', 40, 8, 128), ('qwen-3-32b', 64, 8, 128), ('qwen-3-30b-a3b', 32, 4, 128),
    ('chinese-alpaca-2-7b', 32, 32, 128),
    ('gpt-oss-20b', 64, 8, 64), ('gpt-oss-120b', 64, 8, 64),
]
assert all(q % kv == 0 for _, q, kv, _ in GEOM)
assert len(GEOM) == 30
matches = [n for n, q, kv, hs in GEOM if hs == 128 and q // kv == 4]
assert matches == ['qwen-3-4b-instruct-2507', 'llama-3.1-8b', 'llama-3-8b', 'mistral-7b',
                   'ministral-8b', 'mixtral-8x7b', 'phi-4', 'granite-3.3-8b']
cells = {}
for n, q, kv, hs in GEOM:
    cells.setdefault((q // kv, hs), []).append(n)
mrows = []
for ratio in sorted({r for r, _ in cells}):
    tds = [f'<td style="text-align:center;"><b>{ratio}</b></td>']
    for hcol in (64, 128, 256):
        names = cells.get((ratio, hcol), [])
        if not names:
            tds.append('<td style="color:#898781;text-align:center;">&#x2014;</td>')
        elif ratio == 4 and hcol == 128:
            tds.append('<td style="background:#e4f2ed;"><b>' + ', '.join(names) + '</b></td>')
        else:
            tds.append('<td>' + ', '.join(names) + '</td>')
    mrows.append('<tr>' + ''.join(tds) + '</tr>')
matrix = ('<table>\n<tr><th>queries per K/V head</th><th>head width 64</th>'
          '<th>head width 128</th><th>head width 256</th></tr>\n'
          + '\n'.join(mrows) + '\n</table>')

# ---- 4.1.1 why kv_mul 3/5/8 are not served + forced-gate failure diagram ----
def gate_fail_411():
    HB, HH = 34, 22
    X0 = 168
    rows = [
        ("kv_mul 4", "qwen-3-4b / llama-3.1-8b / mixtral", 4,
         "served: the window IS the group"),
        ("kv_mul 3", "llama-3.2-3b", 3,
         "window overshoots into the NEXT group&#x27;s head"),
        ("kv_mul 5", "qwen-2.5-32b", 5,
         "5th head left out: never computed, never updated"),
        ("kv_mul 8", "llama-3.3-70b", 8, "half the group left out"),
    ]
    parts = []
    y = 46
    for name, models, km, verdict in rows:
        parts.append(f'<text x="8" y="{y+15}" font-size="11.5" font-weight="600" fill="#0b0b0b">{name}</text>')
        parts.append(f'<text x="8" y="{y+29}" font-size="9.5" fill="#898781">{models}</text>')
        for i in range(2 * km):
            x = X0 + i * (HB + 2)
            grp = i // km
            in_window = i < 4
            if in_window and grp == 0:
                fill, stroke = "#e4f2ed", "#1b9e77"   # correctly this group
            elif in_window and grp > 0:
                fill, stroke = "#fbe3d5", "#d95f02"   # wrong-group read
            elif grp == 0:
                fill, stroke = "#eeedea", "#898781"   # this group, skipped
            else:
                fill, stroke = "#ffffff", "#d8d6d0"
            parts.append(f'<rect x="{x}" y="{y}" width="{HB}" height="{HH}" fill="{fill}" stroke="{stroke}"/>')
            parts.append(f'<text x="{x+HB/2:.0f}" y="{y+15}" font-size="10" fill="#52514e" text-anchor="middle">q{i}</text>')
        xdiv = X0 + km * (HB + 2) - 1
        parts.append(f'<line x1="{xdiv}" y1="{y-6}" x2="{xdiv}" y2="{y+HH+6}" stroke="#0b0b0b" stroke-width="1.6"/>')
        parts.append(f'<text x="{X0}" y="{y-8}" font-size="9.5" fill="#898781">K/V head 0&#x27;s group</text>')
        parts.append(f'<text x="{xdiv+6}" y="{y-8}" font-size="9.5" fill="#898781">K/V head 1&#x27;s group</text>')
        parts.append(f'<rect x="{X0-3}" y="{y-3}" width="{4*(HB+2)+2}" height="{HH+6}" fill="none" stroke="#7570b3" stroke-width="2.4"/>')
        parts.append(f'<text x="{X0 + 16*(HB+2) + 14}" y="{y+15}" font-size="10.5" fill="#0b0b0b">{verdict}</text>')
        y += 62
    parts.append(f'<text x="{X0-3}" y="{y-14}" font-size="10.5" fill="#7570b3" font-weight="600">violet frame = the 128x4 kernels&#x27; fixed 4-head window (pack, tiles, epilogue)</text>')
    y += 16
    parts.append(f'<text x="8" y="{y+14}" font-size="11.5" font-weight="600" fill="#0b0b0b">and the epilogue&#x27;s stride:</text>')
    parts.append(f'<text x="8" y="{y+28}" font-size="9.5" fill="#898781">sp[kv_head * 4 + offset]</text>')
    SB = 17
    for i in range(24):
        x = X0 + i * (SB + 1)
        parts.append(f'<rect x="{x}" y="{y}" width="{SB}" height="18" fill="#ffffff" stroke="#d8d6d0"/>')
    for i in range(24, 32):
        x = X0 + i * (SB + 1)
        parts.append(f'<rect x="{x}" y="{y}" width="{SB}" height="18" fill="none" stroke="#d95f02" stroke-dasharray="3,2"/>')
    parts.append(f'<rect x="{X0+28*(SB+1)}" y="{y}" width="{4*(SB+1)-1}" height="18" fill="#fbe3d5" stroke="#d95f02"/>')
    parts.append(f'<text x="{X0}" y="{y+32}" font-size="9.5" fill="#898781">llama-3.2-3b has 24 query heads = 24 scratchpad entries</text>')
    parts.append(f'<text x="{X0+22*(SB+1)}" y="{y+32}" font-size="10" fill="#d95f02">K/V head 7 &#x2192; slots 28&#x2013;31: past the end (out-of-bounds write)</text>')
    h = y + 46
    svg = ('<figure><svg viewBox="0 0 980 ' + str(h) + '" width="980" height="' + str(h) + '" role="img" '
           'aria-label="What the fixed 4-head kernel window would read for kv_mul 4, 3, 5 and 8, and where the epilogue stride would write" '
           'font-family="system-ui,sans-serif">'
           '<text x="8" y="20" font-size="12.5" font-weight="600" fill="#0b0b0b">If the gate were forced open: what the fixed 4-head window would touch</text>'
           + "".join(parts) + '</svg>'
           '<figcaption>Two K/V groups shown per geometry. Green = heads the kernel would compute'
           ' correctly; orange = a NEIGHBORING group&#x27;s head read as if it were ours; grey ='
           ' heads of this group the kernel would silently skip. Bottom strip: the epilogue&#x27;s'
           ' hard-coded &#xD7;4 stride against llama-3.2-3b&#x27;s 24-entry scratchpad.</figcaption></figure>')

    text_a = """
<h3 id="gate-fail" style="font-size:14px;">4.1.1 Why the kv_mul 3 / 5 / 8 models are not served
&#x2014; and what would break if the gate were simply forced open</h3>
<p>From the nightly-CI list, llama-3.2-3b (3 query heads per K/V head), qwen-2.5-32b (5) and
llama-3.3-70b (8) all have 128-wide heads but fail the <code>kv_mul() == 4</code> half of the
gate. <b>As shipped, nothing fails on them</b>: the gate is compile-time
(<code>if constexpr</code>), so for these models the AMX branch is not even compiled into their
plugin instantiation &#x2014; they run the unchanged AVX path (that is the measured
&quot;ineligible shape&quot; class: gpt-oss showed &#x2212;0.3..&#x2212;1.6%, run-to-run noise).</p>
<p>The interesting question is what the gate is protecting against. The <code>*_128x4</code>
kernels hard-code the number 4 in three load-bearing places: the Q pack reads exactly 4
consecutive query heads starting at <code>kv_head &#xD7; kv_mul &#xD7; 128</code>; the tile
kernels compute exactly those 4 rows; and the epilogue writes exactly scratchpad entries
<code>sp[kv_head &#xD7; 4 + offset]</code>, then returns early so the AVX loop never revisits the
page. Run that machinery on a group that is not 4 heads wide and, per geometry:</p>
"""
    text_b = """
<ul>
<li><b>kv_mul 3 (llama-3.2-3b):</b> the 4-head window reads one head PAST the group &#x2014; the
next K/V head&#x27;s first query is scored against the wrong K/V data (silently wrong attention),
and for the last K/V head the pack reads past the end of the query tensor while the &#xD7;4
epilogue stride writes scratchpad slots 28&#x2013;31 of a 24-entry array: out-of-bounds read AND
write, i.e. memory corruption, not just wrong numbers.</li>
<li><b>kv_mul 5 (qwen-2.5-32b):</b> the window covers 4 of the 5 heads; the 5th head is never
computed &#x2014; and because the AMX branch returns early, the AVX loop never fills it either, so
1 in 5 heads remains uncomputed and its scratchpad entry is not updated. From the second group on,
the &#xD7;4 stride (correct would be
&#xD7;5) lands every update on the WRONG head&#x27;s scratchpad entry: in-bounds, silent, wrong.</li>
<li><b>kv_mul 8 (llama-3.3-70b):</b> half of every group is skipped, and the &#xD7;4-vs-&#xD7;8
stride mis-addresses every group after the first. (This shape could use TWO full query tiles
rather than one, but it requires a width-8 kernel variant and a generalized stride &#x2014; it
cannot be enabled by loosening the shape check.)</li>
</ul>
<p>That is the design point: the gate makes the unsupported case <i>impossible by construction</i>
rather than checked at runtime, and the failure modes above are why widening support means new
per-width kernels plus a <code>kv_mul</code>-derived stride (the planned actual-width bucketing),
never just deleting the check.</p>
"""
    return text_a + svg + text_b

geo = f'''
<h3 id="geometry" style="font-size:15px;">4.1 The attention geometry we support &#x2014; exactly,
and which models have it</h3>
<p>The fast path engages only when the model&#x27;s attention has one exact shape. The whole gate is
one line of compile-time arithmetic plus the runtime CPU check
(<code>h/tron/models/self_attention.hpp</code>):</p>
<pre>constexpr bool amx_shape_ok = geometry.kv.head_size == 128 &amp;&amp; geometry.kv_mul() == 4;
const bool amx_on = amx_shape_ok &amp;&amp; amx_attn::available();</pre>
<p>In plain words: <b>each attention head must be 128 numbers wide, and exactly 4 query heads must
share each stored K/V head</b> (<code>kv_mul()</code> is that sharing ratio; modern models store
fewer K/V heads than query heads to shrink the KV cache). Why this exact shape: one query group of
4 heads &#xD7; 128 numbers = 512 bf16 values = 1,024 bytes; the kernel packs those as
16 rows &#xD7; 32 values &#x2014; <b>exactly one full AMX tile</b> (16 rows &#xD7; 64 bytes),
no padding waste. The kernel
names carry the shape: <code>qk_canonical_128x4</code>, <code>weights_times_v_128x4</code>, <code>qk_mirror_128x4</code>.</p>
<p><b>Is tensor-parallel (tp1/tp2/tp4) part of the geometry? No.</b> The gate reads two compile-time
model constants (head width, sharing ratio). The tp mode is a separate build parameter that decides
how work is split across FPGA devices; it changes neither constant (and it divides query and K/V
head counts by the same factor, so the ratio could not change anyway). A model passes or fails this
gate identically at tp1, tp2, and tp4.</p>
<p><b>Every model family in today&#x27;s registry</b> (<code>config/models.yaml</code>, the 30
families with C++ geometry), placed by its two gate numbers &#x2014; only the green cell gets the
fast path:</p>
{matrix}
<p>Four more registry entries (deepseek-v3, seed-oss-36b, glm-4.7, minimax-m2) have no C++ plugin
yet, so there is no geometry in tron to check. A near miss worth naming: llama-3.2-1b has the right
sharing ratio (4) but 64-wide heads, so it stays on AVX. phi-4 matches with 40 query / 10 K/V heads
&#x2014; the ratio is what the gate reads (40 &#xF7; 10 = 4); the kernel loops over K/V heads, so
their count is free.</p>
<p>Honest status of the {len(matches)} matching families &#x2014; a gate pass means the fast path
<i>engages</i>; gains and numerics are <i>measured</i> so far on three of them:</p>
<table>
<tr><th>status</th><th>models</th></tr>
<tr><td>matched, measured</td><td>qwen-3-4b-instruct-2507 (decode +15&#x2013;28%),
llama-3.1-8b (decode +15.0% / +19.7%),
mixtral-8x7b (vs kill-switch baseline at 8 users: decode ctx 2048 +2.3% canonical / +1.2%
mirror; decode ctx 8192 +9.4% / +18.6%; prefill ctx 8192 +56% / +55% &#x2014;
results/ci-models/mixtral-ab.txt, 2026-08-21)</td></tr>
<tr><td>matched, not yet measured</td><td>llama-3-8b, mistral-7b, ministral-8b,
phi-4, granite-3.3-8b (registry marks its plugin as not end-to-end yet)</td></tr>
<tr><td>not matched, measured no-regression</td><td>gpt-oss-20b (&#x2212;0.3% to &#x2212;1.6%,
within run-to-run noise; see 5.1)</td></tr>
</table>
'''
geo += gate_fail_411()

# ---- 4.2 FPGA-mode composition (jhan question 2026-08-19) ----
hwmode = '''
<h3 id="hwmode" style="font-size:15px;">4.2 Does FPGA attention bypass AMX? No &#x2014; the two
compose</h3>
<p>The AMX dispatch never looks at whether FPGA attention is on. It sits <i>inside</i> the
software-attention page loop, and that loop runs in both modes: with FPGA attention on, it processes
exactly the queries the query mask marks &quot;software required&quot;
(<code>self_attention.hpp:1344</code> selects the mode, <code>:1526</code> picks
<code>sw_required</code> vs <code>visible</code> per query). Whatever attention lands on the CPU
flows through the same gates as &#xA7;4: a full, fully visible 64-token page takes the AMX kernels;
anything partial takes the unchanged AVX loop.</p>
<table>
<tr><th>CPU attention work while FPGA attention is on</th><th>does AMX fire on it?</th></tr>
<tr><td>queries early in the sequence &#x2014; any query at position below 127 always runs in
software (an FPGA constraint)</td>
<td>partly &#x2014; not every such query, and never all of its work. The query reads every stored
token from position 0 up to itself, but AMX only takes complete 64-token pages. A query in roughly
the first 64 positions has no complete page yet, so all of its work runs the AVX loop. A query at
position &#x2248;64&#x2013;126 has exactly one complete page (tokens 0&#x2013;63): AMX computes that
page, and the leftover tokens after 63 sit in a partly filled page and go through the AVX
loop.</td></tr>
<tr><td>layers the FPGA cannot serve: sliding-window layers always run in software
(<code>:1343</code>), as do layers the plugin marks <code>software_only</code> (gpt-oss&#x27;s
window layers)</td>
<td>yes, on pages fully inside the window; window-boundary pages fall to AVX</td></tr>
<tr><td>models/configs where hardware attention is ineligible at all (no hardware plan is
built)</td>
<td>every page becomes CPU work; whether AMX fires is then decided by the &#xA7;4 gates alone
&#x2014; a matching-shape model behaves exactly as under USE_HW_ATTN=0, a non-matching one stays on
AVX</td></tr>
<tr><td>token ranges the FPGA serves</td>
<td>they never reach the CPU; there is nothing to accelerate</td></tr>
</table>
<p>Practical size: for qwen-class models (no window layers), the CPU&#x27;s share in FPGA-attention
mode is just those early-position queries, so the AMX contribution there is small. The measured
+15&#x2013;28% decode gains are for the all-software operating mode (USE_HW_ATTN=0), where every
page is CPU work. No extra code is needed for the mixed mode &#x2014; it composes as-is, and the
kill switch behaves identically in both.</p>
<p><b>Testing trap (we hit it during T1):</b> the page rule above applies to any test, in any mode.
A run whose total length &#x2014; prompt plus generated tokens &#x2014; stays under 64 never
completes a page, so AMX never engages: both arms run the identical AVX code, an A/B shows nothing,
and a numerics comparison &quot;passes&quot; without ever testing the AMX path. The repo&#x27;s
canned 21-token prompts do exactly this. Any meaningful test must push the total sequence past 64
tokens (the measured campaigns use ctx 2048 and 8192).</p>
'''
# ---- 4.3 why two copies of K (Bill's question 2026-08-20) ----
billq = '''
<h3 id="why-two-k" style="font-size:15px;">4.3 Why keep two copies of K instead of just storing K
transposed? (Bill&#x27;s question)</h3>
<p>The mirror stores a second, rearranged copy of K next to the original. A fair question: why not
store K in the rearranged form <i>once</i> and drop the original? tron already does exactly that
for V &#x2014; V is stored in the tile-friendly interleaved form natively, every consumer reads it
that way, and V needs no mirror. The difference is that V has one layout every reader wants, while
the original K layout is a shared interface with three consumers that need the row form:</p>
<table>
<tr><th>who reads original K</th><th>why it needs rows</th><th>if K were stored transposed</th></tr>
<tr><td><b>FPGA attention</b>. The save path stores each roped K row into the page &quot;so HW sees
the latest K values&quot; (comment at the store, <code>model.hpp:2779</code>); hardware offload
then ships completed 4-token groups of those page bytes to the card as they fill
(<code>gof.hpp:33</code>, <code>full.hpp:2382</code>). The KV pages live in DMA-visible hugepage
memory; the mirror arena is deliberately ordinary RAM the card never sees.</td>
<td>the card&#x27;s layout is a hardware contract; the pages are shipped byte-for-byte with no
conversion step anywhere</td>
<td>the FPGA reads a layout it does not understand. The fix is either an FPGA-side change or a
convert-and-stage copy at the DMA boundary &#x2014; the transpose work does not disappear, it moves
to the transfer path and brings a staging buffer with it</td></tr>
<tr><td><b>The AVX-512 fallback</b>. <code>dotter&lt;bf16,128&gt;</code>
(<code>dotter.hpp:176</code>) consumes one K row as one contiguous 128-value vector &#x2014; the QK
reduction runs along the head dimension, which is contiguous within a row.</td>
<td>this path is not legacy; it serves everything AMX declines: group widths below the crossover,
partial and young pages (every page until its 64 tokens complete, including the partial tails of
early-position software queries in FPGA mode &#x2014; &#xA7;4.2), non-matching geometries, hosts
without AMX, and the kill switch</td>
<td>one token&#x27;s 128 values are scattered across the transposed panels 32 bytes apart (the
layout formula: <code>kv_cache.hpp</code>, mirror scatter comment), so the single-token dot product
loses its contiguous-row loads and needs strided or gather-style loads plus rearrangement instead,
unless a new family of narrow kernels is written for the transposed form</td></tr>
<tr><td><b>The rollback story</b>. <code>TRON_AMX_DISABLE</code> currently returns to the unchanged
code path at clean-binary speed (measured &#x2212;1.3% to +3.3% of a build with no AMX code at
all).</td>
<td>a reviewer can reason: flag off = old engine</td>
<td>there is no unchanged path left to return to &#x2014; disabling AMX would strand the AVX code
on a layout it was never written for</td></tr>
</table>
<p>What replacing would actually save, honestly: (a) the arena&#x27;s memory &#x2014; about half the
KV cache&#x27;s size in <i>ordinary</i> RAM (&#x2264;32 GB on this machine&#x27;s 64 GB KV
configuration, out of 1.58 TB installed &#x2014; small next to both budgets, though its traffic and
placement are still real; the scarce DMA page budget is untouched: in the measured capacity probe,
both builds admitted 32 and 48 users at ctx 8192 with no failures); (b) the mirror&#x27;s moving
parts &#x2014; the allocation/lifetime plumbing and null-check fallbacks, the defrag rebuild, the
two-copy consistency invariant across writes and page moves, and the byte-equivalence tests that
guard it all; (c) almost nothing on the write side &#x2014; the 70 ns/token-row scatter would
remain as the <i>primary</i> K store, replacing only a cheap contiguous row write.</p>
<p class="take"><b>So the two copies are not an accident:</b> the original K plane is the interface
the FPGA and every narrow/partial CPU case consume, and the transposed plane is a private view for
one kernel. Replacing rather than mirroring is a cross-stack layout migration (FPGA contract, new
narrow-width CPU kernels, loss of the rollback) purchased with savings the arena design already
made small relative to the machine&#x27;s memory and page budgets. The V cache shows when
replacement <i>is</i> right: when every consumer wants the
rearranged form. If a future card consumed transposed K natively &#x2014; or an FPGA-free build
existed &#x2014; this question should be reopened.</p>
'''
anchor = '<h2>5. The evidence (all measured, 2026-08-18/19)</h2>'
assert html.count(anchor) == 1
html = html.replace(anchor, geo + '\n' + hwmode + '\n' + billq + '\n' + anchor)
old = 'has a different attention geometry the fast path cannot serve'
assert html.count(old) == 1
html = html.replace(old, 'has a different <a href="#geometry">attention geometry</a> (64-wide heads, 8 query heads per K/V head) that the fast path cannot serve')
open('rampup/pr-rampup.html', 'w').write(html)
assert all(ord(c) < 128 for c in html)
print('pr-rampup.html written')
