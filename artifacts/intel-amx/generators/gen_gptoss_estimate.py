#!/usr/bin/env python3
# Generates rampup/gptoss-estimate.html: engineering estimate for adding
# gpt-oss support to the AMX software-attention fast path (PR #3879).
# All repo facts verified 2026-08-19 against ~/workspace/tron-amx (branch
# jhan-amx-p0): gate self_attention.hpp:1356+1534, window predicate :1537,
# sink epilogue :77+:1184, plugin ingested_gpt_oss_20b.hpp.
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
    def r(self, x, y, w, h, fill, stroke, sw=1.4, rx=4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
    def render(self, w, h, aria):
        assert audit(self.el, w) == 0
        return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{aria}" '
                f'font-family="system-ui,sans-serif">\n' + '\n'.join(self.el) + '\n</svg>')

# ---------- numbers (computed, not hand-typed) ----------
B = 2
qwen_mb = 36 * 8 * 8192 * 128 * 2 * B / 1e6          # 1208 MB
oss_full_mb = 12 * 8 * 8192 * 64 * 2 * B / 1e6       # 201.3 MB
oss_win_mb = 12 * 8 * 128 * 64 * 2 * B / 1e6         # 3.15 MB
oss_mb = oss_full_mb + oss_win_mb
ratio = qwen_mb / oss_mb
step_q_clean, step_q_amx = 1000 / 105.7, 1000 / 126.5
attn_q = step_q_clean * 0.64
attn_q_amx = step_q_amx - (step_q_clean - attn_q)
attn_cut = 1 - attn_q_amx / attn_q                    # 25.7%
step_o = 1000 / 199.2
attn_o = attn_q * oss_mb / qwen_mb
share_o = attn_o / step_o                             # 20.4%
ceiling = step_o / (step_o - attn_o * attn_cut) - 1   # +5.5%
lo = step_o / (step_o - attn_o * 0.7 * attn_cut) - 1
hi = step_o / (step_o - attn_o * 1.3 * attn_cut) - 1
attn_cb = attn_q / 3                                  # compute-bound case: 12 vs 36 full layers
share_cb = attn_cb / step_o
gain_cb = step_o / (step_o - attn_cb * attn_cut) - 1  # ~+11.5%
assert abs(ceiling - 0.055) < 0.005 and abs(share_o - 0.204) < 0.01

# ---------- Figure A: the 24-layer map ----------
f = S()
f.t(14, 20, 'gpt-oss-20b: 24 layers, two kinds of attention, strictly alternating', size=12.5, anchor='start', bold=True)
bw, gap, y0, h = 36, 3.5, 36, 46
for i in range(24):
    x = 14 + i * (bw + gap)
    win = (i % 2 == 0)
    f.r(x, y0, bw, h, T_ORA if win else T_PUR, ORA if win else PUR, 1.4)
    f.t(x + bw / 2, y0 + 19, str(i), size=10, fill=INK2)
    f.t(x + bw / 2, y0 + 35, 'W' if win else 'F', size=11, bold=True, fill=ORA if win else PUR)
lx = 14
f.r(lx, y0 + h + 16, 14, 14, T_ORA, ORA, 1.4)
f.t(lx + 22, y0 + h + 27, 'W = sliding window 128: reads at most the last 128 tokens; marked software_only '
    '(always runs on the CPU, even in FPGA mode)', size = 10.5, anchor='start', fill=INK2)
f.r(lx, y0 + h + 40, 14, 14, T_PUR, PUR, 1.4)
f.t(lx + 22, y0 + h + 51, 'F = full attention: reads the whole context (8,192 tokens in our test point); '
    'FPGA-capable in production, CPU when USE_HW_ATTN=0', size=10.5, anchor='start', fill=INK2)
f.t(lx, y0 + h + 76, 'Every layer also carries learned attention sinks (one value per query head) and scale 0.125 = 1/'
    '&#x221A;64.', size=10.5, anchor='start', fill=MUT)
fig_a = f.render(980, 188, 'gpt-oss-20b has 24 layers alternating sliding-window-128 attention on even '
                 'layers, which are software only, and full attention on odd layers, which are FPGA capable')

# ---------- Figure B: one tile, two slicings ----------
f = S()
f.t(14, 20, 'The same full AMX tile (16 rows &#xD7; 64 bytes = 512 bf16), sliced two ways', size=12.5, anchor='start', bold=True)
def tile_panel(f, x0, title, n_heads, rows_per_head, hue, tint, foot):
    f.t(x0, 44, title, size=11.5, anchor='start', bold=True)
    y, rh, tw = 54, 13, 320
    for hd in range(n_heads):
        fill = tint if hd % 2 == 0 else PALE
        for rw in range(rows_per_head):
            f.r(x0, y, tw, rh - 1.5, fill, hue, 1)
            y += rh
        f.t(x0 + tw + 10, y - rh * rows_per_head / 2 + 4,
            f'query head {hd}', size=9.5, anchor='start', fill=INK2)
    f.t(x0, y + 16, foot, size=10, anchor='start', fill=MUT)
tile_panel(f, 14, 'today: 4 query heads &#xD7; 128 numbers', 4, 4, PUR, T_PUR,
           '4 heads &#xD7; 4 rows each (128 numbers = 4 chunks of 32)')
tile_panel(f, 510, 'gpt-oss: 8 query heads &#xD7; 64 numbers', 8, 2, TEAL, T_TEAL,
           '8 heads &#xD7; 2 rows each (64 numbers = 2 chunks of 32)')
f.t(14, 300, 'Both slicings fill the tile exactly: head width &#xD7; heads sharing one K/V head = 512 in both models. '
    'No padding, no wasted rows.', size=11, anchor='start', fill=INK, bold=True)
fig_b = f.render(980, 314, 'One 16-row AMX tile shown twice: sliced as 4 query heads of 128 numbers, '
                 'todays shape, and as 8 query heads of 64 numbers, the gpt-oss shape; both fill the '
                 'tile exactly')

# ---------- Figure C: where the work is ----------
f = S()
f.t(14, 20, 'KV bytes the CPU must read per generated token (ctx 8192, USE_HW_ATTN=0, computed from the geometry)',
    size=12.5, anchor='start', bold=True)
X0, XW, VMAX = 250.0, 620.0, 1300.0
def X(v): return X0 + v / VMAX * XW
rows_y = {'qwen': 44, 'oss': 84}
f.t(X0 - 10, rows_y['qwen'] + 14, 'qwen-3-4b (36 layers, head 128)', size=10.5, anchor='end', fill=INK2)
f.r(X(0), rows_y['qwen'], X(qwen_mb) - X(0), 20, T_MAG, MAG)
f.t(X(qwen_mb) + 8, rows_y['qwen'] + 14, f'{qwen_mb:.0f} MB', size=11, anchor='start', fill=MAG, bold=True)
f.t(X0 - 10, rows_y['oss'] + 14, 'gpt-oss-20b (12 F + 12 W layers)', size=10.5, anchor='end', fill=INK2)
f.r(X(0), rows_y['oss'], X(oss_full_mb) - X(0), 20, T_PUR, PUR)
f.r(X(oss_full_mb), rows_y['oss'], X(oss_full_mb + oss_win_mb) - X(oss_full_mb), 20, ORA, ORA)
f.t(X(oss_mb) + 8, rows_y['oss'] + 14,
    f'{oss_mb:.0f} MB ({oss_full_mb:.0f} full-attn + {oss_win_mb:.1f} window)', size=11, anchor='start', fill=PUR, bold=True)
f.t(14, 132, f'gpt-oss reads {ratio:.1f}&#xD7; fewer KV bytes per token &#x2014; attention is a much thinner slice of '
    f'its decode step (est. &#x2248;{share_o:.0%} vs the measured 64% on qwen).', size=11, anchor='start', fill=INK, bold=True)
f.t(14, 150, 'Bars computed from layer geometry; the qwen 64% share is measured; the gpt-oss share is est. (byte-ratio scaling).',
    size=10, anchor='start', fill=MUT)
fig_c = f.render(980, 162, 'KV bytes read per generated token: qwen 1208 megabytes versus gpt-oss 204 '
                 'megabytes, of which only 3 megabytes come from the twelve sliding window layers')

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Adding gpt-oss to the AMX fast path: an estimate</title>
<style>
body {{ font-family: system-ui, sans-serif; color: {INK}; background: #ffffff;
       max-width: 1010px; margin: 24px auto; padding: 0 16px; line-height: 1.55; }}
h1 {{ font-size: 22px; }} h2 {{ font-size: 17px; margin-top: 30px; }}
table {{ border-collapse: collapse; margin: 12px 0; font-size: 13.5px; }}
th, td {{ border: 1px solid #d8d6d0; padding: 5px 10px; text-align: left; vertical-align: top; }}
th {{ background: {PALE}; }}
code, pre {{ background: {PALE}; border-radius: 4px; font-size: 13px; }}
code {{ padding: 1px 5px; }} pre {{ padding: 10px 14px; overflow-x: auto; }}
figure {{ margin: 16px 0; }} figcaption {{ font-size: 12.5px; color: {INK2}; margin-top: 6px; }}
.take {{ background: {T_TEAL}; border: 1.5px solid {TEAL}; border-radius: 8px; padding: 12px 16px; margin: 14px 0; }}
.warn {{ background: {T_ORA}; border: 1.5px solid {ORA}; border-radius: 8px; padding: 12px 16px; margin: 14px 0; }}
.meta {{ color: {MUT}; font-size: 12.5px; }}
svg {{ max-width: 100%; height: auto; }}
dl dt {{ font-weight: 600; margin-top: 8px; }} dl dd {{ margin-left: 0; color: {INK2}; }}
</style>
</head>
<body>
<h1>Adding gpt-oss to the AMX fast path: what it takes, what it buys</h1>
<p class="meta">2026-08-19 &#xB7; estimate on top of draft PR #3879 &#xB7; repo facts verified against
branch jhan-amx-p0 (file:line citations inline) &#xB7; companion docs:
<a href="pr-rampup.html">PR ramp-up</a>, <a href="pr-rampup.html#geometry">geometry audit &#xA7;4.1</a></p>

<div class="take"><b>Verdict in three sentences.</b> Feasible and clean: gpt-oss&#x27;s attention shape
(8 query heads sharing each 64-wide K/V head) fills an AMX tile exactly as well as today&#x27;s
supported shape, and the two hard-looking features &#x2014; attention sinks and sliding windows
&#x2014; already live <i>outside</i> the code the AMX path replaces, so they need <b>zero</b> changes
(verified in code, &#xA7;4). The work is one new kernel family plus a two-shape gate: est. about one
engineering week plus one or two measurement nights. The payoff is modest: est. <b>+4 to +7% decode</b>
at 1 user / ctx 8192 in the all-software mode (vs +19.7% measured on qwen), because gpt-oss reads
{ratio:.1f}&#xD7; fewer KV bytes per token, leaving attention an est. {share_o:.0%} slice of its
decode step (vs the measured 64% on qwen); in production FPGA-attention mode the gain is
est. &#x2248;0. Measure before committing: a one-slot decode profile pins the real
attention share (&#xA7;6).</div>

<h2>1. What gpt-oss looks like inside tron today</h2>
<p>Both gpt-oss models run in tron now (registry level &quot;working&quot;, tagged production+test)
and both have the same attention geometry: <b>64 query heads, 8 K/V heads, heads 64 numbers wide</b>
&#x2014; so 8 query heads share each K/V head (ratio 8), where the current fast path requires 4 sharing
a 128-wide head. The 20b has 24 layers (12 window + 12 full), the 120b has 36 (18 + 18, verified in
its plugin). The kernel and gate work below applies to both models unchanged; the traffic and payoff
numbers are computed for the 20b &#x2014; the 120b would need its own payoff arithmetic on its own
baseline.</p>
<figure>{fig_a}<figcaption>Layer plan read from the generated plugin
(<code>gen/src/tron/h/tron/plugins/ingested_gpt_oss_20b.hpp</code>): window size 128 and
<code>software_only</code> on even layers, full attention on odd layers, per-layer sink tensors
(<code>tensor&lt;64&gt; self_attn_sinks</code>).</figcaption></figure>
<p>Today, with the current PR in the tree, gpt-oss simply never enters the fast path &#x2014; the shape
gate routes every page to the unchanged AVX code. That is the measured &#x2212;0.3% to &#x2212;1.6%
(within noise) in the <a href="pr-rampup.html">PR ramp-up &#xA7;5.1</a>.</p>

<h2>2. Why the current kernels do not fire: two compile-time numbers</h2>
<pre>constexpr bool amx_shape_ok =
    geometry.kv.head_size == 128 &amp;&amp; geometry.kv_mul() == 4;   // self_attention.hpp:1356
...
if constexpr (operation_kv_mul == 4 &amp;&amp; operation_head_size == 128) // :1534, the page-loop twin</pre>
<p>Those two sites are the <i>only</i> places that hard-code the shape. Everything else in the dispatch
&#x2014; the build flag, the CPUID/OS check, the kill switch, the full-page check, the visibility check,
and (already!) the sliding-window check &#x2014; is shape-independent.</p>

<h2>3. Why the gpt-oss shape fits AMX just as well</h2>
<figure>{fig_b}<figcaption>The packed query group for one K/V head: today 4 heads &#xD7; 4 chunk-rows,
for gpt-oss 8 heads &#xD7; 2 chunk-rows. Head width &#xD7; sharing ratio = 512 in both, so the same
16-row &#xD7; 64-byte tile budget holds with no padding.</figcaption></figure>
<p>The arithmetic carries through the whole kernel recipe: the reduction over the 64 head numbers is
2 chunks of 32 instead of 4, so each (K/V head, page) costs <b>8 tile multiplies instead of 16</b>
&#x2014; exactly matching the halved bytes. The score tile even gets <i>wider</i> use (8 query columns
instead of 4). New kernels <code>qk_st_64x8</code> and <code>pv_64x8</code> follow the same recipe as
the existing <code>qk_st_128x4</code> / <code>pv_128x4</code> (transposing store and all); the V
storage is consumed as-is because its token-pair interleave does not depend on head width.</p>

<h2>4. What needs NO change (code-verified, this is the good news)</h2>
<table>
<tr><th>feature</th><th>where it lives</th><th>why the AMX path never sees it</th></tr>
<tr><td><b>attention sinks</b> (a learned &quot;always there&quot; score per query head)</td>
<td><code>attention_sink_update_for</code> (self_attention.hpp:77) applied by
<code>apply_attn_sinks</code> (:1184) on the final running totals</td>
<td>applied once per token <i>after</i> the page loop, in the fp32 epilogue the AMX path leaves
untouched &#x2014; the kernels only fill raw scores and multiply weights by values</td></tr>
<tr><td><b>sliding window</b> (recent-128 masking on even layers)</td>
<td>whole-page skip at :1386; the dense-path predicate <i>already</i> contains
<code>q_position &#x2212; k_position &lt; sliding_window_size</code> (:1537); per-token skip in the
AVX loop at :1578</td>
<td>window handling happens in page selection, before any multiply; a page fully inside the window
takes the fast path, a page straddling the window edge falls back to the AVX loop &#x2014; the same
partial-page fallback that exists today</td></tr>
<tr><td><b>mirror scatter for 64-wide heads</b> (only relevant if the opt-in mirror were wanted)</td>
<td><code>scatter_k_mirror&lt;page_size, head_size&gt;</code>, already a template</td>
<td>the PR&#x27;s byte-equivalence test (t/t_amx_mirror.cpp) already instantiates and passes head
width 64</td></tr>
<tr><td><b>MoE / MXFP4 experts</b></td><td>FFN, on the FPGA</td>
<td>not attention; the KV cache the CPU reads is plain bf16 like every other model</td></tr>
</table>

<h2>5. The work list (est.)</h2>
<table>
<tr><th>#</th><th>piece</th><th>file (same map as the PR)</th><th>size (est.)</th></tr>
<tr><td>1</td><td>kernels <code>pack_q_group_64x8</code>, <code>qk_st_64x8</code>,
<code>pv_64x8</code> + a second tile-configuration constant chosen in
<code>begin_region</code> by shape (one process serves one model, so no switching cost)</td>
<td>amx_attn.cpp / amx_attn_iface.hpp</td><td>200&#x2013;300 lines, 2&#x2013;3 days incl. kernel unit
tests</td></tr>
<tr><td>2</td><td>generalize the two gate sites to a two-shape list and template the pack-buffer
size (today <code>amx_qpack.resize(items.size() * (4*16*32))</code>)</td>
<td>self_attention.hpp</td><td>&lt;50 lines, half a day</td></tr>
<tr><td>3</td><td>byte-equivalence + AVX-vs-AMX A/B unit tests for the 64x8 shape (clones of the
existing tests)</td><td>t/</td><td>1 day</td></tr>
<tr><td>4</td><td>T1 numerics chain for gpt-oss: HF fp32/bf16 reference logits (the MXFP4 experts
dequantize in HF), then the same TVD comparison used for qwen</td><td>exec harness</td>
<td>1 day setup + reruns</td></tr>
<tr><td>5</td><td>kill-switch A/B measurement campaign (existing T4 harness, new model)</td>
<td>exec scripts</td><td>1 machine night</td></tr>
</table>
<p><b>Deliberately out of scope for v1</b>: a 64x8 mirror. The mirror&#x27;s edge grows with attention
share, and gpt-oss&#x27;s share is small (&#xA7;6) &#x2014; canonical-only keeps the work at one week.
The mirror formulation traces to Bill&#x27;s PR #2934; the implementation and every number in these
docs are ours.</p>

<h2>6. What it buys (est.) &#x2014; and the measurement that would firm this up</h2>
<figure>{fig_c}<figcaption>Computed from layer geometry: 36 &#xD7; 8 &#xD7; 8192 &#xD7; 128 numbers
&#xD7; K+V &#xD7; 2 bytes for qwen vs (12 &#xD7; 8192 + 12 &#xD7; 128) &#xD7; 8 &#xD7; 64 &#xD7; K+V
&#xD7; 2 bytes for gpt-oss.</figcaption></figure>
<p>Chain of reasoning, each step labeled:</p>
<ul>
<li>On qwen at 1u/8K, attention is 64% of the decode step (<b>measured</b>) and AMX cut attention
time by {attn_cut:.0%} (<b>derived</b> from the measured step times {step_q_clean:.2f} &#x2192;
{step_q_amx:.2f} ms and the measured 64% share, assuming the non-attention remainder is
unchanged).</li>
<li>gpt-oss reads {ratio:.1f}&#xD7; fewer KV bytes per token (<b>computed</b> from geometry, bars
above). Scaling qwen&#x27;s measured attention time by that byte ratio puts gpt-oss attention at
&#x2248;{attn_o:.1f} ms of its {step_o:.2f} ms step &#x2014; a {share_o:.0%} share (<b>est.</b>).
This rests on TWO assumptions: equal effective memory bandwidth, and that attention stays
bandwidth-bound the way qwen&#x27;s decode-phase counters showed (LLC-miss-dominated). The
multiply arithmetic shrinks only &#x2248;3&#xD7;, not 5.9&#xD7; (12 vs 36 full layers; per-layer
multiply work per attended token is equal: 32 heads &#xD7; 128 = 64 heads &#xD7; 64 = 4,096 query
numbers) &#x2014; so in the compute-bound worst case the share would be nearer {share_cb:.0%} and
the estimate nearer +{gain_cb:.0%}.</li>
<li>Applying the same {attn_cut:.0%} attention cut to that slice (assumes the 64x8 kernels achieve
the same relative cut): <b>decode +{ceiling:.1%} (est.)</b> at 1u/8K; if the true share is &#xB1;30% off, the range is +{lo:.1%} to +{hi:.1%}. At short contexts
the share shrinks further &#x2014; expect low single digits or nothing.</li>
<li><b>Production FPGA-attention mode: est. &#x2248;0.</b> There the CPU only runs the 12 window
layers (they are <code>software_only</code>) plus queries at positions below 127, and the window work is the
3&#x2005;MB orange sliver in the chart &#x2014; those full in-window pages WOULD take the fast
path, but scaled through the same model that is under 0.1% of a step. The practical case for
gpt-oss support is the all-software operating mode.</li>
<li>Prefill: <code>Insufficient data</code> &#x2014; the full-attention layers should benefit the way
qwen prefill did (+29% to +105% measured there), but we have no gpt-oss attention-share profile for
prefill; the same one-slot measurement below resolves it.</li>
</ul>
<div class="warn"><b>Before committing the week: spend one machine slot first.</b> A decode-phase
<code>perf</code> attach on a gpt-oss run with USE_HW_ATTN=0 (same method as the layout deep-dive in
the <a href="2026-08-19-amx-status.html">status report &#xA7;4</a>) pins the real attention share.
If it comes back &#x2248;{share_o:.0%} as estimated, the estimate stands at the
+{lo:.1%}&#x2013;{hi:.1%} above and the priority call is a product question; if it comes back near
the compute-bound case (&#x2248;{share_cb:.0%}), the estimate rises to &#x2248;+{gain_cb:.0%}.</div>

<h2>7. Where the same generalization leads (one paragraph, no commitment)</h2>
<p>The tile identity &quot;head width &#xD7; sharing ratio = 512&quot; has a third member in the
registry: <b>256-wide heads with ratio 2</b> &#x2014; gemma-2-2b/9b, gemma-3-4b, gemma-4-12b. The same
kernel recipe (2 heads &#xD7; 8 chunk-rows) would serve them; gemma&#x27;s score softcap, like the
sinks, lives in the untouched epilogue. And qwen-3-32b / qwen-3-30b-a3b / the 70b llamas (128-wide,
ratio 8) need <i>two</i> tiles per query group &#x2014; doable but a different, heavier recipe. Worth a
separate estimate only if one of those models becomes a priority.</p>

<h2>8. Glossary (plain words)</h2>
<dl>
<dt>Attention sink</dt><dd>A learned per-head score that always participates in the softmax, as if
there were one extra token every query can attend to. Keeps the distribution stable when a window
hides old tokens.</dd>
<dt>Sliding window</dt><dd>The layer only looks at the most recent N tokens (N=128 here) instead of
the whole history.</dd>
<dt>software_only</dt><dd>The plugin marks these layers as always computed on the CPU, even when FPGA
attention is enabled.</dd>
<dt>Query group</dt><dd>The query heads that share one stored K/V head and are therefore multiplied
against the same page together: 4 heads today, 8 for gpt-oss.</dd>
<dt>Chunk</dt><dd>32 numbers &#x2014; the slice of a head that fits one 64-byte tile row as bf16.</dd>
<dt>Mirror</dt><dd>The opt-in pre-rearranged second copy of K (formulation from Bill&#x27;s PR #2934;
implementation and numbers ours). Not proposed for gpt-oss v1.</dd>
</dl>
<p class="meta">Estimate method: geometry bytes computed by script; qwen anchors are measured
(replicated, 95% CIs in the <a href="2026-08-19-amx-status.html">status report</a>); every derived
number is labeled est. or derived and traced to its assumption. Code citations refer to branch
jhan-amx-p0.</p>
</body>
</html>
'''
assert all(ord(c) < 128 for c in html), [c for c in html if ord(c) > 127][:5]
open('rampup/gptoss-estimate.html', 'w').write(html)
print('gptoss-estimate.html written')
