#!/usr/bin/env python3
"""Generate ~/workspace/intel-AMX/tron-amx-distilled.html from the rampup corpus.

Skeleton source: Notion page "Distilled" (Daily notes > Intel AMX > Generate
design md from my HTML), 2026-08-21. Sections are transplanted verbatim from
the consensus-reviewed docs; new content = TL;DR (user-provided verbatim),
the per-instruction "function" column, three Q&A blocks, and the test-result
charts. Rerun after editing any source section to re-sync.
"""
import re, os, sys

ROOT = os.path.expanduser("~/workspace/intel-AMX")
R = os.path.join(ROOT, "rampup")

def load(name):
    return open(os.path.join(R, name)).read()

D01 = load("01-amx-rampup.html")
D02 = load("02-tron-decode-amx-plan.html")
PR  = load("pr-rampup.html")
ST  = load("2026-08-19-amx-status.html")

def cut(src, start, end):
    a = src.find(start)
    assert a >= 0, f"start marker not found: {start[:60]}"
    if end is None:
        return src[a:]
    b = src.find(end, a)
    assert b > a, f"end marker not found after start: {end[:60]}"
    return src[a:b]

def strip_first_heading(frag):
    # Remove the fragment's own leading <h2 ...>...</h2> (the skeleton owns titles).
    return re.sub(r"^\s*<h2[^>]*>.*?</h2>", "", frag, count=1, flags=re.S)

def fix_hrefs(frag):
    # Local doc links now live under rampup/ relative to the output location.
    return re.sub(r'href="(?!https?://|#|rampup/)([A-Za-z0-9._-]+\.html)',
                  r'href="rampup/\1', frag)

def provenance(text):
    return f'<p class="prov">Transplanted from {text} (generator: exec/gen_distilled.py).</p>'

# ---------------- fragments ----------------
f_intro    = strip_first_heading(cut(D01, '<h2 id="what">',       '<h2 id="isa">'))
f_isa      = strip_first_heading(cut(D01, '<h2 id="isa">',        '<h2 id="throughput">'))
f_tput     = strip_first_heading(cut(D01, '<h2 id="throughput">', '<h2 id="gemm">'))
f_gemm     = strip_first_heading(cut(D01, '<h2 id="gemm">',       '<h2 id="layout">'))
# remove "Minimal intrinsics skeleton" (h3 to end of the section fragment)
a = f_gemm.find('<h3>Minimal intrinsics skeleton</h3>')
assert a >= 0
f_gemm = f_gemm[:a]

f_pairs    = strip_first_heading(cut(D02, '<h2 id="pairs">',      '<h2 id="targets">'))
f_design   = strip_first_heading(cut(D02, '<h2 id="design">',     '<h2 id="transpose">'))
a = f_design.find('<h3>Design decisions')
assert a >= 0
f_design = f_design[:a]           # drop the Design-decisions h3 + table (ends the fragment)
f_transpose = cut(D02, '<h2 id="transpose">', '<h2 id="batching">')   # keep own heading (4b)
f_transpose = f_transpose.replace('<h2 id="transpose">', '<h3 id="transpose">', 1).replace('</h2>', '</h3>', 1)
f_perf     = strip_first_heading(cut(D02, '<h2 id="perf">',       '<h2 id="precision">'))
f_precision= strip_first_heading(cut(D02, '<h2 id="precision">',  '<h2 id="plan">'))

f_system   = strip_first_heading(cut(D01, '<h2 id="system">',     '<h2 id="tradeoffs">'))
f_tradeoffs= strip_first_heading(cut(D01, '<h2 id="tradeoffs">',  '<h2 id="llm">'))

f_arch     = strip_first_heading(cut(D02, '<h2 id="arch">',       '<h2 id="swattn">'))
f_swattn   = strip_first_heading(cut(D02, '<h2 id="swattn">',     '<h2 id="pairs">'))
f_problem  = strip_first_heading(cut(PR,  '<h2>1. The problem being solved</h2>', '<h2>2. Intel AMX</h2>'))
f_changes  = strip_first_heading(cut(PR,  '<h2>3. What the PR actually changes</h2>', '<h2>4. The safety model'))
f_mirror_st= strip_first_heading(cut(ST,  '<h2>4. Deep-dive: the mirror layout penalty', '<h2>5. Gate 5'))
f_whytwok  = cut(PR, '<h3 id="why-two-k"', '<h2>5. The evidence')
f_hwmode   = cut(PR, '<h3 id="hwmode"',    '<h3 id="why-two-k"')
f_geometry = cut(PR, '<h3 id="geometry"',  '<h3 id="hwmode"')

f_evidence = strip_first_heading(cut(PR, '<h2>5. The evidence', '<h3 style="font-size:15px;">5.1 Model coverage'))
# remove the decode table (replaced by charts); keep the prefill line + bullets
a = f_evidence.find('<table>'); b = f_evidence.find('</table>') + len('</table>')
assert 0 <= a < b
f_evidence_rest = f_evidence[:a] + f_evidence[b:]
f_llama    = cut(PR, '<h3 style="font-size:15px;">5.1 Model coverage', '<h2>6. Glossary')

f_terms    = strip_first_heading(cut(D01, '<h2 id="terms">',    '<h2 id="what">'))
f_gloss01  = strip_first_heading(cut(D01, '<h2 id="glossary">', '<h2 id="sources">'))
f_glosspr  = strip_first_heading(cut(PR,  '<h2>6. Glossary',    None))
f_gloss02  = strip_first_heading(cut(D02, '<h2 id="glossary">', '<h2 id="sources">'))

# ---------------- transforms ----------------
# 6.4 per-instruction table: insert a "Function" column.
FUNC = {
    "LDTILECFG":  "load the 64 B tile configuration (all 8 tiles&#x27; shapes) from memory",
    "STTILECFG":  "store the current tile configuration to memory",
    "TILERELEASE":"reset tiles + configuration to the INIT state",
    "TILEZERO":   "zero one tile register",
    "TILELOADD":  "load one tile (up to 1 KB) from memory",
    "TILESTORED": "store one tile to the first-level cache",
    "TDPBF16PS":  "the matrix multiply: C[16&#xd7;16] fp32 += A &#xb7; B over bf16 pairs",
}
def add_function_column(frag):
    hdr_old = ("<tr><th>Instruction</th><th>Intel Table 20-2 (latency / throughput, cycles)\n"
               '  <span class="cite">opt-manual:31320-31329</span></th>')
    assert hdr_old in frag, "6.4 table header not found"
    frag = frag.replace(hdr_old,
        "<tr><th>Instruction</th><th>Function</th>"
        "<th>Intel Table 20-2 (latency / throughput, cycles)\n"
        '  <span class="cite">opt-manual:31320-31329</span></th>', 1)
    for name, desc in FUNC.items():
        pat = re.compile(r"(<tr><td><code>" + name + r"</code>[^<]*</td>)")
        frag, n = pat.subn(r"\1<td>" + desc + "</td>", frag, count=1)
        assert n == 1, f"6.4 row not found for {name}"
    return frag
f_system = add_function_column(f_system)

# ---------------- charts (Test results) ----------------
DECODE = {  # % gain vs true clean binary, results/t4/t4-suite.txt via pr-rampup sec 5
    "1u/2K": (3.8, 4.5), "1u/8K": (15.2, 19.6), "8u/2K": (19.0, 22.8), "8u/8K": (17.5, 28.1)}
PREFILL = {  # % gain vs clean, computed from results/t4/t4-suite.txt parse rates
    "1u/2K": (44.9, 46.7), "1u/8K": (102.7, 105.2), "8u/2K": (41.3, 43.6), "8u/8K": (90.4, 100.0)}

def barchart(title, data, unit_max, tick_step, note):
    # horizontal grouped bars, canonical (violet) + mirror (green), axis from 0
    left, width = 90, 470
    scale = width / unit_max
    rows = []
    y = 40
    for cell, (canon, mirr) in data.items():
        rows.append(f'<text x="{left-8}" y="{y+21}" font-size="11.5" fill="#0b0b0b" text-anchor="end">{cell}</text>')
        for i, (v, color) in enumerate(((canon, "#7570b3"), (mirr, "#1b9e77"))):
            by = y + i * 15
            w = v * scale
            rows.append(f'<rect x="{left}" y="{by}" width="{w:.1f}" height="12" fill="{color}"/>')
            rows.append(f'<text x="{left + w + 5:.1f}" y="{by+10}" font-size="10.5" fill="{color}">+{v}%</text>')
        y += 42
    axis_y = y + 2
    ticks = []
    t = 0
    while t <= unit_max:
        x = left + t * scale
        ticks.append(f'<line x1="{x:.1f}" y1="{axis_y}" x2="{x:.1f}" y2="{axis_y+4}" stroke="#898781"/>')
        ticks.append(f'<text x="{x:.1f}" y="{axis_y+16}" font-size="10" fill="#898781" text-anchor="middle">+{t}%</text>')
        t += tick_step
    h = axis_y + 26
    legend = (f'<rect x="{left}" y="18" width="10" height="10" fill="#7570b3"/>'
              f'<text x="{left+14}" y="27" font-size="10.5" fill="#52514e">canonical (default)</text>'
              f'<rect x="{left+150}" y="18" width="10" height="10" fill="#1b9e77"/>'
              f'<text x="{left+164}" y="27" font-size="10.5" fill="#52514e">arena-mirror (opt-in)</text>')
    return (f'<figure><div class="svgwrap"><svg viewBox="0 0 640 {h}" width="640" height="{h}" role="img" '
            f'aria-label="{title}" font-family="system-ui,sans-serif">'
            f'<text x="12" y="14" font-size="12.5" font-weight="600" fill="#0b0b0b">{title}</text>'
            f'{legend}'
            f'<line x1="{left}" y1="36" x2="{left}" y2="{axis_y}" stroke="#d8d6d0"/>'
            f'<line x1="{left}" y1="{axis_y}" x2="{left+width}" y2="{axis_y}" stroke="#d8d6d0"/>'
            + "".join(rows) + "".join(ticks) +
            f'</svg></div><figcaption>{note}</figcaption></figure>')

chart_decode = barchart(
    "Decode gain vs the true clean binary (qwen-3-4b-tp2, T4 suite, 3 reps/cell)",
    DECODE, 30, 10,
    'Same-binary kill-switch A/B against the all-flags-off clean build; axis starts at 0. '
    'Replication with 8 reps/cell and 95% CIs: canonical +15.3&#xb1;0.4 / +17.7&#xb1;0.2, '
    'mirror +19.7&#xb1;0.3 / +27.8&#xb1;0.8 at 1u/8K / 8u/8K &#x2014; all CIs exclude zero. '
    '<span class="cite">exec/results/t4/t4-suite.txt</span> '
    '<span class="cite">exec/results/t4/t4-reps.txt</span>')
chart_prefill = barchart(
    "Prefill (prompt parsing) gain vs the true clean binary (same suite)",
    PREFILL, 110, 20,
    'Per-user prompt-parse rate averaged over requests and 3 reps; the 8192-token prompt '
    'parses in about half the time. '
    '<span class="cite">exec/results/t4/t4-suite.txt</span>')

# ---------------- new content ----------------
TLDR = """
<ul>
<li>AMX is a per-physical-core matrix-multiply-accumulation unit. One instruction computes
<b>C[16&#xd7;16] += A[16&#xd7;32] &#xd7; B[32&#xd7;16]</b> on bf16 data (fp32 accumulation) held in
eight 1&#x2009;KB tile registers.</li>
<li>Peak: 512 MAC/cycle/core - 8x AVX-512 BF16</li>
<li>The B operand must be stored in a <b>pair-interleaved (&quot;VNNI&quot;) layout</b></li>
<li>The OS must grant permission per process (<code>arch_prctl</code>). delphi-3bda has everything
needed: AMX-TILE/BF16/INT8 <i>and</i> AMX-FP16, kernel 6.8</li>
</ul>
"""

HWMODE_QA = """
<div class="take"><b>Q (jhan): does this mean the AMX solution needs no change when hw_attention
is enabled?</b><br>
Yes &#x2014; no code change is needed. The AMX dispatch sits inside the software page loop, and
that loop runs in BOTH modes: hardware mode still routes part of the work to it (positions below
127, sliding-window and software-only layers, hw-ineligible configurations), and every full,
fully-visible page inside that subset takes the AMX path exactly as in all-software mode
(<code>self_attention.hpp</code>: <code>run_visible_in_software</code>, the dispatch has no
<code>uses_hw</code> check). What DOES change is the payoff, not the code: all measured end-to-end
gains (+15&#x2013;28% decode) are from all-software mode; in hardware mode the CPU&#x27;s share of
attention is smaller, so the end-to-end effect of AMX is proportionally smaller and has not been
measured separately.</div>
"""

GEOMETRY_QA = """
<div class="take"><b>Q (jhan): we found the two gpt-oss models can work with AMX after some
changes. From a pure KV-head-width point of view, is that a similar solution to llama-68m and
llama-3.2-1b, which have the same head width (64)?</b><br>
Partially. The shared part: all three have 64-wide heads, so they would share the head-64 kernel
family (<code>qk/pv_64xN</code>: a K row is 128 B, a 64-token K page is 8 KB, and the reduction
runs over 64 dims instead of 128). The part that is NOT shared is the guaranteed decode width,
which is the query-heads-per-KV-head ratio (<code>kv_mul</code>) &#x2014; it decides how many of
the 16 tile rows carry real work in private decode:
<ul>
<li><b>gpt-oss-20b/120b</b>: 64Q/8KV, head 64 &#x2192; kv_mul 8; one GQA group = 8 &#xd7; 64 =
512 bf16 = a FULL tile operand &#x2014; the same &quot;tile identity&quot; as today&#x27;s
4 &#xd7; 128 shape, full utilization. This is why the gpt-oss port is worth doing (new kernels +
2 gate sites; sinks and sliding windows already need zero AMX changes &#x2014; code-verified in
<a href="rampup/gptoss-estimate.html">gptoss-estimate.html</a>).</li>
<li><b>llama-3.2-1b</b>: 32Q/8KV, head 64 &#x2192; kv_mul 4; a group fills only 4 &#xd7; 64 = 256
bf16 = HALF a tile operand &#x2014; the same kernels would run with half the rows as padding, so
at best half the AMX utilization of the gpt-oss case (<code>h/tron/plugins/llama.hpp:1539</code>).</li>
<li><b>llama-68m</b>: 12Q/12KV, head 64 &#x2192; kv_mul 1 (no grouping at all); guaranteed decode
width 1 sits BELOW the measured AVX crossover (Nq=2), so the dispatcher would correctly leave
private decode on AVX &#x2014; not a candidate (<code>h/tron/plugins/llama.hpp:1531</code>).</li>
</ul>
So: one shared head-64 kernel family, three different payoffs &#x2014; full-tile for gpt-oss,
half-tile for llama-3.2-1b, none for llama-68m private decode (prefill and shared-prefix batching,
where width comes from token count rather than kv_mul, could still engage for the small llamas).</div>
"""


WORKED_EXAMPLE = """
<h4 id="pair-worked">Worked example: why B must be pair-interleaved (mock 3&#xd7;4 &#xb7; 4&#xd7;4)</h4>
<p class="prov">New for this document (jhan&#x27;s Scratch page, 2026-08-21); semantics per the
panel above and <span class="cite">sdm-vol-1:8002</span>; the mapping is exercised numerically by
<code>t/t_amx_numerics.cpp</code> (PV output matches an exact reference to ~6e-8).</p>
<p>Every value below is chosen to be exactly representable in bf16 (integers with at most 8
significant bits; B&#x27;s columns scale by 8 so each column lives in its own magnitude band),
and every sum is exact in the fp32 accumulator &#x2014; so a real TDPBF16PS execution reproduces
this table bit-exactly, with no rounding anywhere.</p>
<p>Conceptual (mathematical) layout &#x2014; what C = A &#xb7; B means:</p>
<div class="tablewrap"><table>
<tr><th>A (3&#xd7;4)</th><th>B (4&#xd7;4)</th><th>C = A&#xb7;B (3&#xd7;4)</th></tr>
<tr>
<td class="mono" style="text-align:left">1&#xa0;&#xa0;&#xa0;2&#xa0;&#xa0;&#xa0;3&#xa0;&#xa0;&#xa0;4<br>10&#xa0;&#xa0;20&#xa0;&#xa0;30&#xa0;&#xa0;40<br>100 200 300 400</td>
<td class="mono" style="text-align:left">1&#xa0;&#xa0;8&#xa0;&#xa0;&#xa0;64&#xa0;&#xa0;&#xa0;512<br>2&#xa0;&#xa0;16&#xa0;&#xa0;128&#xa0;&#xa0;1024<br>3&#xa0;&#xa0;24&#xa0;&#xa0;192&#xa0;&#xa0;1536<br>4&#xa0;&#xa0;32&#xa0;&#xa0;256&#xa0;&#xa0;2048</td>
<td class="mono" style="text-align:left">30&#xa0;&#xa0;&#xa0;240&#xa0;&#xa0;&#xa0;1920&#xa0;&#xa0;&#xa0;15360<br>300&#xa0;&#xa0;2400&#xa0;&#xa0;19200&#xa0;&#xa0;153600<br>3000 24000 192000 1536000</td>
</tr></table></div>
<p>Target for one output: <code>C[0,0] = 1&#xb7;1 + 2&#xb7;2 + 3&#xb7;3 + 4&#xb7;4 = 30</code>
&#x2014; the reduction walks DOWN B&#x27;s column 0 (1, 2, 3, 4).</p>
<p><b>What the hardware consumes.</b> As the panel above says, the smallest unit TDPBF16PS eats is
a PAIR of adjacent bf16 values: per step, each fp32 accumulator lane takes one 32-bit element
(= two adjacent bf16) from A and one 32-bit element (= two adjacent bf16) from B, and adds both
products at once. A&#x27;s pairs come
free &#x2014; its reduction axis runs along the row, so (1,&#x2009;2) and (3,&#x2009;4) are already
adjacent in memory. B&#x27;s reduction axis runs down a COLUMN: the value that must pair with the
1 in column 0 is the 2 one row below &#x2014; four elements away in row-major storage. So B is
stored with conceptual rows 2k and 2k+1 zipped together: stored row k holds, for every output
column n, the pair (B[2k][n],&#x2009;B[2k+1][n]) side by side:</p>
<div class="tablewrap"><table>
<tr><th>stored B (2 rows &#xd7; 4 pairs)</th><th>pair for n=0</th><th>n=1</th><th>n=2</th><th>n=3</th></tr>
<tr><td class="mono">row 0 (conceptual rows 0+1)</td><td class="mono">1&#xa0;2</td><td class="mono">8&#xa0;16</td><td class="mono">64&#xa0;128</td><td class="mono">512&#xa0;1024</td></tr>
<tr><td class="mono">row 1 (conceptual rows 2+3)</td><td class="mono">3&#xa0;4</td><td class="mono">24&#xa0;32</td><td class="mono">192&#xa0;256</td><td class="mono">1536&#xa0;2048</td></tr>
</table></div>
<p><b>The instruction&#x27;s walk for C[0,0]</b> (all four output columns run simultaneously, each
lane using its own pair from the SAME stored row):</p>
<ul>
<li>step k=0: A pair (1,&#x2009;2) &#xd7; stored-row-0 pair (1,&#x2009;2) &#x2192;
    1&#xb7;1 + 2&#xb7;2 = 5</li>
<li>step k=1: A pair (3,&#x2009;4) &#xd7; stored-row-1 pair (3,&#x2009;4) &#x2192;
    3&#xb7;3 + 4&#xb7;4 = 25</li>
<li>sum: <b>30</b> &#x2014; the conceptual dot product, completed in two pair steps.</li>
</ul>
<div class="take"><b>The trap the Scratch page hit.</b> Its stored bytes were RIGHT &#x2014; read
linearly, a correctly interleaved stream is exactly the stored rows above. The wrong number comes
from then multiplying that stored block as if it were an ordinary matrix: reshape the eight pairs
into a 4&#xd7;4 scalar matrix ([1,2,8,16] / [64,128,512,1024] / [3,4,24,32] / [192,256,1536,2048])
and dot A&#x27;s row against its first column, and you get 1&#xb7;1 + 2&#xb7;64 + 3&#xb7;3 +
4&#xb7;192 = 906 &#x2260; 30. The stored tile is not the original logical 4&#xd7;4 scalar
matrix: physically it has two rows of four 32-bit pair lanes, so reshaping its eight bf16 pairs
into an ordinary 4&#xd7;4 scalar matrix and dotting a stored scalar column applies the wrong
interpretation. Its logical meaning is defined by TDP&#x27;s pair consumption along the reduction
axis. The interleave exists precisely so that the ONE stored row the instruction reads per step
carries, for all output columns at once, the two B values that multiply A&#x27;s next two
elements.</div>
<p>Scale note: the toy has K=4, so 2 stored rows of 4 pairs; a real tile step is K=32
(16 stored rows of 64 bytes, 16 pairs each), and a 128-dim reduction chains 4 such steps. In
tron&#x27;s data this pairing is over the reduction axis of each GEMM: V pairs adjacent TOKENS
(the PV reduction), and the K mirror pairs adjacent HEAD DIMS (the mirror-QK reduction) &#x2014;
the two panels above.</p>
"""

NO_TRANSPOSE = """
<h4 id="no-transpose">4.4 Why no K transpose was needed before AMX (jhan&#x27;s question)</h4>
<p class="prov">New for this document (jhan&#x27;s question, 2026-08-24); code-verified in the PR
worktree: <code>self_attention.hpp:1568&#x2013;1589</code>, <code>dotter.hpp:176</code>,
<code>model.hpp:2784</code>.</p>
<p>&#xA7;4.3 raises a follow-up: software attention computes S = Q&#xB7;K<sup>T</sup> and existed
long before AMX &#x2014; so where was the K transpose then? Was it done on the FPGA when the FPGA
did the matmul, sparing the CPU? No, on both counts: <b>the pre-AMX CPU path never materialized a
transposed K, and the FPGA is not the reason.</b> The transpose in Q&#xB7;K<sup>T</sup> exists
only on paper &#x2014; a dot-product kernel absorbs it in its loop order:</p>
<figure><div class="svgwrap"><svg viewBox="0 0 980 390" width="980" height="390" role="img"
aria-label="Left: the mathematical view, S equals Q times K transposed, reading down one column of K transposed. Right: the code view, a loop over K rows in storage order, one dot product per row, each result landing in score slot i. A connector shows column i and row i are the same 128 contiguous values."
font-family="system-ui,sans-serif">
<text x="14" y="22" font-size="12.5" font-weight="600" fill="#0b0b0b">The transpose in S = Q&#xB7;K&#x1D40; is performed by the loop index &#x2014; no K bytes ever move</text>
<text x="14" y="48" font-size="11" font-weight="600" fill="#898781">mathematical view</text>
<rect x="14" y="64" width="120" height="16" fill="#fdeee1" stroke="#d95f02" stroke-width="1.2"/>
<text x="74" y="76" font-size="10.5" fill="#0b0b0b" text-anchor="middle">q &#x2014; 1&#xD7;128</text>
<text x="146" y="78" font-size="14" fill="#0b0b0b" text-anchor="middle">&#xB7;</text>
<text x="218" y="58" font-size="10.5" fill="#52514e" text-anchor="middle">K&#x1D40; (128 &#xD7; 64 tokens)</text>
<rect x="162" y="64" width="112" height="144" fill="#ffffff" stroke="#898781" stroke-width="1.2"/>
<line x1="176" y1="64" x2="176" y2="208" stroke="#d8d6d0" stroke-width="1"/>
<line x1="190" y1="64" x2="190" y2="208" stroke="#d8d6d0" stroke-width="1"/>
<line x1="204" y1="64" x2="204" y2="208" stroke="#d8d6d0" stroke-width="1"/>
<line x1="218" y1="64" x2="218" y2="208" stroke="#d8d6d0" stroke-width="1"/>
<line x1="232" y1="64" x2="232" y2="208" stroke="#d8d6d0" stroke-width="1"/>
<line x1="246" y1="64" x2="246" y2="208" stroke="#d8d6d0" stroke-width="1"/>
<line x1="260" y1="64" x2="260" y2="208" stroke="#d8d6d0" stroke-width="1"/>
<rect x="190" y="64" width="14" height="144" fill="#eae9f4" stroke="#7570b3" stroke-width="1.8"/>
<text x="152" y="136" font-size="9.5" fill="#898781" text-anchor="middle" transform="rotate(-90 152 136)">128 head dims</text>
<text x="130" y="226" font-size="10.5" fill="#7570b3" text-anchor="middle">column i = token i&#x27;s key</text>
<text x="14" y="262" font-size="11" fill="#0b0b0b">S[i] = q &#xB7; (column i of K&#x1D40;)</text>
<text x="14" y="278" font-size="10.5" fill="#52514e">on paper the reduction walks DOWN a column</text>
<line x1="308" y1="40" x2="308" y2="290" stroke="#d8d6d0" stroke-width="1.2" stroke-dasharray="4 3"/>
<path d="M 197 212 C 197 252 340 171 420 171" fill="none" stroke="#7570b3" stroke-width="1.5" stroke-dasharray="4 3"/>
<path d="M 426 171 l -8 -3.5 v 7 z" fill="#7570b3"/>
<text x="285" y="244" font-size="9.5" fill="#7570b3" text-anchor="middle">the same 128 contiguous values</text>
<text x="320" y="48" font-size="11" font-weight="600" fill="#898781">what the code executes &#x2014; one dot product per stored row (self_attention.hpp:1568)</text>
<rect x="430" y="62" width="310" height="20" fill="#fdeee1" stroke="#d95f02" stroke-width="1.2"/>
<text x="585" y="76" font-size="10.5" fill="#0b0b0b" text-anchor="middle">q &#x2014; loaded ONCE into registers (dot_q, :1502)</text>
<rect x="430" y="104" width="310" height="22" fill="#eae9f4" stroke="#7570b3" stroke-width="1.2"/>
<text x="585" y="119" font-size="10.5" fill="#0b0b0b" text-anchor="middle">K row 0 &#x2014; token 0&#x27;s key: 128 contiguous bf16 (256 B)</text>
<rect x="430" y="132" width="310" height="22" fill="#eae9f4" stroke="#7570b3" stroke-width="1.2"/>
<text x="585" y="147" font-size="10.5" fill="#0b0b0b" text-anchor="middle">K row 1 &#x2014; token 1&#x27;s key</text>
<rect x="430" y="160" width="310" height="22" fill="#eae9f4" stroke="#7570b3" stroke-width="2.2"/>
<text x="585" y="175" font-size="10.5" font-weight="600" fill="#0b0b0b" text-anchor="middle">K row i &#x2014; token i&#x27;s key</text>
<text x="585" y="198" font-size="12" fill="#52514e" text-anchor="middle">&#x22EE;</text>
<rect x="430" y="204" width="310" height="22" fill="#eae9f4" stroke="#7570b3" stroke-width="1.2"/>
<text x="585" y="219" font-size="10.5" fill="#0b0b0b" text-anchor="middle">K row 63</text>
<line x1="414" y1="104" x2="414" y2="230" stroke="#52514e" stroke-width="1.8"/>
<path d="M 414 236 l -3.5 -8 h 7 z" fill="#52514e"/>
<text x="406" y="118" font-size="11" font-weight="600" fill="#0b0b0b" text-anchor="end">for i = 0&#x2026;63</text>
<text x="406" y="132" font-size="10" fill="#52514e" text-anchor="end">storage order,</text>
<text x="406" y="145" font-size="10" fill="#52514e" text-anchor="end">one dot per row</text>
<text x="770" y="97" font-size="9.5" fill="#52514e" text-anchor="middle">dot with q (reused)</text>
<line x1="744" y1="115" x2="790" y2="115" stroke="#52514e" stroke-width="1.4"/>
<path d="M 798 115 l -8 -3.5 v 7 z" fill="#52514e"/>
<line x1="744" y1="143" x2="790" y2="143" stroke="#52514e" stroke-width="1.4"/>
<path d="M 798 143 l -8 -3.5 v 7 z" fill="#52514e"/>
<line x1="744" y1="171" x2="790" y2="171" stroke="#52514e" stroke-width="1.4"/>
<path d="M 798 171 l -8 -3.5 v 7 z" fill="#52514e"/>
<line x1="744" y1="215" x2="790" y2="215" stroke="#52514e" stroke-width="1.4"/>
<path d="M 798 215 l -8 -3.5 v 7 z" fill="#52514e"/>
<rect x="802" y="104" width="70" height="22" fill="#ffffff" stroke="#52514e" stroke-width="1.2"/>
<text x="837" y="119" font-size="10.5" fill="#0b0b0b" text-anchor="middle">s[0]</text>
<rect x="802" y="132" width="70" height="22" fill="#ffffff" stroke="#52514e" stroke-width="1.2"/>
<text x="837" y="147" font-size="10.5" fill="#0b0b0b" text-anchor="middle">s[1]</text>
<rect x="802" y="160" width="70" height="22" fill="#ffffff" stroke="#52514e" stroke-width="2.2"/>
<text x="837" y="175" font-size="10.5" font-weight="600" fill="#0b0b0b" text-anchor="middle">s[i]</text>
<text x="837" y="198" font-size="12" fill="#52514e" text-anchor="middle">&#x22EE;</text>
<rect x="802" y="204" width="70" height="22" fill="#ffffff" stroke="#52514e" stroke-width="1.2"/>
<text x="837" y="219" font-size="10.5" fill="#0b0b0b" text-anchor="middle">s[63]</text>
<text x="430" y="252" font-size="10" fill="#52514e">each dot: 4 contiguous 64-byte loads + _mm512_dpbf16_ps &#x2014; dotter.hpp:176</text>
<text x="430" y="266" font-size="10" fill="#52514e">:1586 reads the row &#x2192; :1588 writes the score into slot i</text>
<text x="14" y="312" font-size="11.5" font-weight="600" fill="#0b0b0b">row i of K (as save_k stored it, model.hpp:2784) IS column i of K&#x1D40; &#x2014; landing each result in s[i] performs the transpose via the loop index.</text>
<text x="14" y="329" font-size="10.5" fill="#52514e">zero bytes are rearranged: no transposed copy of K exists anywhere in memory, and every load the kernel issues is contiguous.</text>
<text x="14" y="356" font-size="11" font-weight="600" fill="#b34413">why AMX cannot do the same: TDPBF16PS reads its B operand as whole tiles of consecutive bytes in a fixed pair-interleaved layout &#x2014;</text>
<text x="14" y="372" font-size="11" font-weight="600" fill="#b34413">a tile instruction has no per-token loop whose index could absorb the transpose, so the rearranged K must exist physically in memory: the mirror (&#xA7;4.3).</text>
</svg></div><figcaption>The AVX fallback&#x27;s QK step &#x2014; the only software K consumer
before AMX. The loop (<code>self_attention.hpp:1568</code>) walks K rows in storage order;
<code>dotter&lt;bf16,128&gt;</code> (<code>dotter.hpp:176</code>) holds q in four 512-bit registers
and issues only contiguous loads. Schematic: a real page is 64 rows &#xD7; 256 B; the loop&#x27;s
visibility and sliding-window skips are omitted.</figcaption></figure>
<p>In code: the fallback loop (<code>self_attention.hpp:1568</code>) visits stored tokens in
storage order; each iteration reads ONE K row &#x2014; token i&#x27;s key, 128 contiguous bf16,
exactly as the save path wrote it (<code>model.hpp:2784</code>) &#x2014; and computes one dot
product against q (<code>:1586</code> reads the row, <code>:1588</code> writes the score).
<code>dotter&lt;bf16,128&gt;</code> keeps q in four 512-bit registers for the whole page and issues
four contiguous 64-byte loads plus <code>_mm512_dpbf16_ps</code> per row. Row i of K <i>is</i>
column i of K<sup>T</sup>; writing the result into <code>s[i]</code> is the entire transpose,
performed by the loop index at zero data movement.</p>
<p>Why the FPGA cannot be the explanation:</p>
<ul>
<li><b>Disjoint work.</b> With hardware attention on, the CPU computes scores only for the queries
the query mask marks software-required (&#xA7;4.2, <a href="#hwmode">next section</a>) &#x2014;
and it computes those scores entirely by itself, from the K pages in the KV cache. No intermediate
result flows from the card back into the CPU&#x27;s QK arithmetic.</li>
<li><b>One-way, byte-for-byte traffic.</b> The card receives the row-form K pages verbatim over
DMA (&#xA7;4.3: the layout is a hardware contract; <code>gof.hpp:33</code>,
<code>full.hpp:2382</code>). Whatever rearrangement the card&#x27;s internal matmul dataflow uses
happens inside the card, is not observable from the host, and changes nothing for the CPU
path.</li>
</ul>
<p class="take"><b>So the correct history:</b> before AMX, <i>no</i> consumer ever paid for a K
transpose &#x2014; the FPGA reads K rows as a byte contract, and every CPU kernel folds the
transpose into its loop index for free. TDPBF16PS is the first consumer in the stack that needs
the transpose to exist as bytes in memory, because a tile instruction loads whole tiles from
consecutive addresses and has no loop order to hide the transpose in. That is the entire reason
the mirror (<a href="#why-two-k">&#xA7;4.3</a>) exists &#x2014; and why nothing like it was needed
before.</p>
"""

# ---------------- mirror upkeep cost: authored section (2026-08-24) ----------------
# Answers jhan's review question: why does the new mirror-arena code not slow
# serving - is it pipelining/concurrency? Numbers: slot = measured 8K prefill
# 1060.87 tok/s (t4-suite.txt line 138) -> 942.6 us/token / 36 layers = 26.2 us
# per (token, layer); scatter = 70.9 ns/row re-measured 2026-08-24
# (bench-scatter-20260824.txt) x 8 KV heads = 0.57 us.

def lanes_mirror_write():
    # wall-clock lanes: one average (token, layer) slot during 8K prefill.
    slot_us = 26.2          # derived: 1/1060.87 s / 36 layers (measured tok/s)
    scatter_us = 0.567      # measured: 8 kv_heads x 70.9 ns/row
    left, width = 150, 540
    px = width / slot_us
    scatter_px = scatter_us * px
    ly = {"compute": 52, "fpga": 100, "rx": 148}
    bh = 20
    axis_y = 196
    # RX callback cluster (schematic widths except the scatter tick)
    cb_x = left + 9.0 * px
    rope_w, save_w = 34, 34
    sk_x = cb_x + rope_w
    sc_x = sk_x + save_w
    sv_x = sc_x + scatter_px
    ticks = []
    for t in range(0, 26, 5):
        x = left + t * px
        ticks.append(f'<line x1="{x:.1f}" y1="{axis_y}" x2="{x:.1f}" y2="{axis_y+4}" stroke="#898781"/>')
        ticks.append(f'<text x="{x:.1f}" y="{axis_y+16}" font-size="10" fill="#898781" text-anchor="middle">{t}</text>')
    return f'''<figure><div class="svgwrap"><svg viewBox="0 0 760 268" width="760" height="268" role="img"
 aria-label="Wall-clock lanes: where the mirror write sits in one (token, layer) slot"
 font-family="system-ui,sans-serif">
<text x="12" y="16" font-size="12.5" font-weight="600" fill="#0b0b0b">One average (token, layer) slot during 8K prefill &#x2014; conceptual execution lanes</text>
<text x="{left-8}" y="{ly['compute']+13}" font-size="11" fill="#0b0b0b" text-anchor="end">compute workers</text>
<rect x="{left}" y="{ly['compute']}" width="{width}" height="{bh}" fill="#b3b0d9"/>
<text x="{left+width/2:.0f}" y="{ly['compute']+14}" font-size="10" fill="#0b0b0b" text-anchor="middle">software attention (page loop) + everything else CPU-side (composition schematic)</text>
<text x="{left-8}" y="{ly['fpga']+13}" font-size="11" fill="#0b0b0b" text-anchor="end">FPGA + DMA</text>
<rect x="{left}" y="{ly['fpga']}" width="{width*0.55:.1f}" height="{bh}" fill="#9fc9c0"/>
<text x="{left+width*0.275:.0f}" y="{ly['fpga']+14}" font-size="10" fill="#0b0b0b" text-anchor="middle">layer matmuls; DMA of finished K/V rows to host (schematic)</text>
<rect x="{left+width*0.55:.1f}" y="{ly['fpga']}" width="{width*0.45:.1f}" height="{bh}" fill="none" stroke="#898781" stroke-dasharray="4 3"/>
<text x="{left+width*0.775:.0f}" y="{ly['fpga']+14}" font-size="10" fill="#52514e" text-anchor="middle">next layer&#x27;s work (schematic)</text>
<text x="{left-8}" y="{ly['rx']+7}" font-size="11" fill="#0b0b0b" text-anchor="end">RX worker</text>
<text x="{left-8}" y="{ly['rx']+19}" font-size="9.5" fill="#52514e" text-anchor="end">(per card)</text>
<rect x="{left}" y="{ly['rx']}" width="{cb_x-left:.1f}" height="{bh}" fill="none" stroke="#898781" stroke-dasharray="4 3"/>
<text x="{left+(cb_x-left)/2:.0f}" y="{ly['rx']+14}" font-size="10" fill="#52514e" text-anchor="middle">waiting for DMA completions</text>
<rect x="{cb_x:.1f}" y="{ly['rx']}" width="{rope_w}" height="{bh}" fill="#d9d7cf"/>
<text x="{cb_x+rope_w/2:.1f}" y="{ly['rx']+14}" font-size="9.5" fill="#0b0b0b" text-anchor="middle">rope_k</text>
<rect x="{sk_x:.1f}" y="{ly['rx']}" width="{save_w}" height="{bh}" fill="#d9d7cf"/>
<text x="{sk_x+save_w/2:.1f}" y="{ly['rx']+14}" font-size="9.5" fill="#0b0b0b" text-anchor="middle">save_k</text>
<rect x="{sc_x:.1f}" y="{ly['rx']}" width="{scatter_px:.1f}" height="{bh}" fill="#d95f02"/>
<rect x="{sv_x:.1f}" y="{ly['rx']}" width="{save_w}" height="{bh}" fill="#d9d7cf"/>
<text x="{sv_x+save_w/2:.1f}" y="{ly['rx']+14}" font-size="9.5" fill="#0b0b0b" text-anchor="middle">save_v</text>
<rect x="{sv_x+save_w:.1f}" y="{ly['rx']}" width="{left+width-(sv_x+save_w):.1f}" height="{bh}" fill="none" stroke="#898781" stroke-dasharray="4 3"/>
<text x="{(sv_x+save_w+left+width)/2:.0f}" y="{ly['rx']+14}" font-size="10" fill="#52514e" text-anchor="middle">waiting (block widths and positions schematic)</text>
<line x1="{sc_x+scatter_px/2:.1f}" y1="{ly['rx']-4}" x2="{sc_x+scatter_px/2:.1f}" y2="{ly['rx']-16}" stroke="#d95f02" stroke-width="1.4"/>
<text x="{sc_x+scatter_px/2:.1f}" y="{ly['rx']-22}" font-size="10.5" font-weight="600" fill="#d95f02" text-anchor="middle">scatter_k_mirror: 0.567 us derived = 8 KV heads x 70.9 ns/row measured in isolation</text>
<line x1="{left}" y1="{axis_y}" x2="{left+width}" y2="{axis_y}" stroke="#d8d6d0"/>
{''.join(ticks)}
<text x="{left+width+8}" y="{axis_y+16}" font-size="10" fill="#898781">us (wall clock)</text>
<text x="14" y="{axis_y+40}" font-size="11" font-weight="600" fill="#d95f02">Within the RX callback lane, only the orange tick is new recurring work: 0.567 us per (token, layer) = 2.2% of the 26.2 us slot; x36 layers = ~20.4 us serial-equivalent per prefill token.</text>
<text x="14" y="{axis_y+56}" font-size="10.5" fill="#52514e">20.4 us is aggregate serial-equivalent work, not a prediction of added wall time; RX is on the per-layer critical chain, so the system A/B below is the ground truth for the net effect.</text>
</svg></div><figcaption>Conceptual execution lanes, not an execution trace. To scale
horizontally: the 26.2 us slot (derived: measured 1060.87 tok/s prompt parse
<span class="cite">exec/results/t4/t4-suite.txt</span> = 942.6 us/token, divided by 36 layers) and
the 0.567 us width of the orange scatter tick (derived: 8 KV heads &#xd7; 70.9 ns/row measured in
isolation <span class="cite">exec/results/bench-scatter-20260824.txt</span> &#x2014; a conservative
bound that places all eight head writes serially on one RX worker, not an RX-lane trace
measurement). Schematic: the tick&#x27;s position, all other block widths and positions, callback
interleaving, waiting intervals, and lane composition. Filled blocks denote work in the
illustrated slot; dashed outlines are schematic context and do not uniformly denote waiting.
tp2 has two cards&#x27; RX workers sharing the writes.</figcaption></figure>'''

MIRROR_COST = """
<p class="prov">New section (2026-08-24), answering a review question; not a transplant
(generator: <code>exec/gen_distilled.py</code>).</p>
<p>The mirror adds two things: one arena allocation at book construction, and one additional
destination-row write for every stored K row. The end-to-end suite shows no observed net
slowdown. The accounting has three parts, and only one of them recurs:</p>
<ul>
<li><b>Allocation: once, at startup.</b> When AMX is available, the mirror arena is allocated
once as ordinary RAM (<code>kv_bytes/2</code>) at KV-book construction, before any request is
served (<code>kv_cache.hpp</code>, <code>maybe_allocate_mirror_arena</code>; on non-AMX hosts and
under the kill switch nothing is allocated). No allocation, resize, or free occurs on the
serving path, so there is no steady-state allocator work at all.</li>
<li><b>Reads: nothing else changed.</b> This is the parallel arena&#x27;s whole point
(&#xA7;&#x201C;Deep-dive&#x201D; above): <code>kv_block</code> keeps its dense 2-plane K+V layout,
so every pre-existing consumer &#x2014; the AVX fallback, the FPGA&#x27;s DMA reads, the
kill-switch path &#x2014; touches exactly the bytes it always did. Measured: the kill-switch arm
of the mirror binary runs at clean-binary speed (&#x2212;1.3..+3.3%)
<span class="cite">exec/results/t4/p2-inc3-arena.txt</span>.</li>
<li><b>The write: the only recurring cost.</b> Every stored K row is scattered once into the
mirror. The rest of this section prices that write.</li>
</ul>
<p><b>Where the write runs, and what it costs.</b> The write-through sits on the per-card driver
RX workers &#x2014; the threads that run DMA-completion callbacks (<code>rope_k</code>,
<code>save_k</code>, <code>save_v</code>) when the card finishes a group of K/V rows. The scatter
runs inside <code>save_k</code>, immediately after the canonical K store, while the source row is
still L1-hot &#x2014; avoiding an expected lower-cache or DRAM refetch. The recurring work writes
one scattered 256-byte destination row per (layer, KV head, token); the isolated benchmark
includes that scatter&#x27;s source loads and destination stores. Measured in isolation:
<b>70.9 ns per row</b> (five retained repetitions across two otherwise idle cores, range
70.8&#x2013;71.0 ns; one 107.7 ns interference result recorded separately while serving remained
active) <span class="cite">exec/results/bench-scatter-20260824.txt</span>. Per token that is
36 layers &#xd7; 8 KV heads &#xd7; 70.9 ns &#x2248; <b>20.4 us serial-equivalent</b>: about 2.2%
of the derived 942.6 us prefill wall per token. Applied mechanically to the measured single-user
decode-step durations, the same 20.4 us serial-equivalent work is approximately 0.2&#x2013;0.4%
of a decode step (estimate, not measured added latency).</p>
""" + lanes_mirror_write() + """
<div class="take"><b>Q (jhan): is the write hidden by pipelining or concurrency?</b><br>
Some of it may overlap, but this experiment does not quantify how much. RX callbacks execute on
workers distinct from the FPGA and the CPU compute workers, so their work <i>can</i> run
concurrently with other activity, and the writes are spread across the per-card RX workers. The
scatter itself is not deferred: it is a plain synchronous store inside <code>save_k</code>,
placed there deliberately because that is the moment the K row is L1-hot (see
Note [K mirror coherence] in <code>kv_cache.hpp</code>), and the RX callback remains on the
per-layer critical chain &#x2014; so the write is <i>not</i> hidden by construction. The robust
explanation is its small measured size (a 0.567 us tick in a 26.2 us slot), potentially aided by
ordinary pipeline concurrency; the 20.4 us per-token figure is aggregate serial-equivalent work,
not a prediction of 20.4 us added wall time, and the system A/B below determines the net
effect.</div>
<p><b>The system A/B is the ground truth for net serving performance in this suite &#x2014; not
for the write&#x27;s standalone contribution.</b> Because the mirror build also changes the QK
kernel, the A/B cannot separately measure how much mirror-write latency reaches wall clock; what
it establishes is the net result. Among the tested modes, prefill has the highest K-row write
rate (prompt tokens are processed much faster, so the write is a larger fraction of elapsed
time), and even there the integrated mirror build shows no observed net regression: it parses
prompts faster than the write-free canonical build in every tested cell &#x2014; +46.7% vs
+44.9%, +105.2% vs +102.7%, +43.6% vs +41.3%, +100.0% vs +90.4% over clean at 1u/2K, 1u/8K,
8u/2K, 8u/8K (3 reps/cell, no prefill confidence intervals captured)
<span class="cite">exec/results/t4/t4-suite.txt</span>. Decode shows the same net picture
(+19.7% vs +15.3% at 1u/8K, 95% CIs excluding zero
<span class="cite">exec/results/t4/t4-reps.txt</span>).</p>
"""

# ---------------- arena never grows: authored section (2026-08-24) ----------------
# Answers jhan's review question: the KV cache "keeps growing" with new
# tokens - why does the mirror arena not grow, and does scatter_k_mirror
# allocate? Facts verified in kv_cache.hpp on branch jhan-amx-p0.

ARENA_NO_GROW = """
<p class="prov">New section (2026-08-24), answering a review question; not a transplant
(generator: <code>exec/gen_distilled.py</code>).</p>
<p>A natural reading of "the KV cache grows as tokens arrive" suggests the mirror must grow
with it - and raises the question of whether <code>scatter_k_mirror</code> allocates memory
for each new row. Neither happens, because growth works differently than the premise
assumes: <b>each KV-cache book is a fixed-capacity allocation, and the mirror arena is sized
to that same fixed capacity when the book is built.</b></p>
<ul>
<li><b>Each book is a fixed pool, allocated at its construction.</b> The <code>book</code>
constructor allocates DMA memory for its full page capacity in one call; <code>n_pages</code>
is fixed for the book&#x27;s lifetime (<code>kv_cache.hpp</code>: &quot;The capacity of this
book in pages. Does not change during the lifetime of the book&quot;). As tokens are added,
the book&#x27;s <i>occupancy</i> grows within storage allocated at construction; the K/V arena
never resizes. Cache-level growth, when needed, happens by creating additional
fixed-capacity books (<code>try_create</code>, the &quot;cache growth&quot; factory in
<code>kv_cache.hpp</code>), and allocation failure there is handled by the higher-level
KV-OOM path (the <code>t/t_kv_oom_*</code> tests).</li>
<li><b>The mirror arena gets one capacity-sized allocation attempt per book.</b> During each
book&#x27;s construction, after the fixed-size K/V arena has been allocated, the constructor
calls <code>maybe_allocate_mirror_arena</code> once: if <code>amx_attn::available()</code>, it
attempts a single non-throwing allocation of <code>kv_bytes / 2</code> - one mirror plane for
EVERY (storage slot, KV head, page) the book could ever hold, occupied or not. If that
allocation fails, the arena stays null and consumers fall back. A <code>kv_block</code> is
two equal-sized planes (K + V) and its mirror is one plane - hence exactly half of
<code>kv_bytes</code>.</li>
<li><b>Where a new row lands is pure address arithmetic.</b> The
<code>k_mirror_data</code> accessor delegates to <code>book::mirror_at_storage</code>
(<code>kv_cache.hpp</code>), which computes a pointer into the existing mirror arena:
<code>mirror_arena_.get() + byte_base + (kv_head * n_pages + pg) * plane_bytes</code> -
the same fixed slot/head/page addressing the canonical planes use inside
<code>arena_data</code>.</li>
<li><b><code>scatter_k_mirror</code> is stores only.</b> Its whole body computes destination
offsets inside the supplied plane and writes one row: <code>head_size / 2</code> bf16 pairs =
<code>2 * head_size</code> bytes (for a 128-dim head: 64 pairs, 128 bf16 values, 256 bytes).
It is <code>noexcept</code>, performs no allocation or other fallible resource operation, and
- given the valid plane and row pointers its callers null-check before invoking it - only
computes offsets and stores; that is what makes it suitable for the RX worker&#x27;s
DMA-completion callback (write site 1 of Note [K mirror coherence]). The mirror arena&#x27;s
entire heap lifecycle is one aligned allocation attempt per book construction and one
matching aligned delete at destruction - the pairing <code>t/t_amx_arena_leak.cpp</code>
pins.</li>
</ul>
<pre>each book construction
  arena_data:
    one K plane + one V plane for every
    (physical storage slot, KV head, page)      = kv_bytes
  mirror_arena_ (when AMX available and the allocation succeeds):
    one K-mirror plane for every
    (physical storage slot, KV head, page)      = kv_bytes / 2

each stored K row (RX worker; stores only, never an allocation)
  canonical store  -&gt; preallocated K plane
  scatter_k_mirror -&gt; preallocated mirror plane</pre>
<p class="take">The trade-off this buys: a capacity-sized ordinary host-memory allocation
attempt for each mirror-enabled book, even before any token slot is occupied. Its size is
<code>kv_bytes / 2</code>, separate from the DMA K/V allocation, so enabling the mirror does
not change the book&#x27;s configured <code>n_pages</code> or its DMA-budget-derived page
capacity (see Note [K mirror parallel arena] in <code>kv_cache.hpp</code>; the 32u/48u
capacity probe at ctx 8192 measured no difference
<span class="cite">exec/results/t4/cap-sweep.txt</span>). With the measured qwen-3-4b-tp2
configuration&#x27;s KV budget this attempt is roughly 32 GB of plain RAM on the 1.58 TB
host.</p>
"""

# ---------------- id dedup + href fixes ----------------
DESIGN_LABELS_NOTE = ('<p class="prov">Labels like (D1), (D6) below refer to the design-decisions '
 'table deliberately omitted here per the skeleton; see '
 '<a href="rampup/02-tron-decode-amx-plan.html#design">doc 02 &#xa7;4</a> for the table or '
 '<code>amx-design.md</code> for the chosen-vs-rejected decision record.</p>')

# (heading html, fragment or None, demote_internals: transplant h3->h4 when the
#  skeleton item itself is an h3)
PARTS = [
 ("<h2>TL;DR</h2>", TLDR, False),
 ("<h2>What AMX is</h2>", None, False),
 ("<h3>Introduction</h3>" + provenance("01-amx-rampup.html &#xa7;1 + &#xa7;1.1"), f_intro, True),
 ("<h3>Instruction set</h3>" + provenance("01-amx-rampup.html &#xa7;2"), f_isa, True),
 ("<h3>Throughput</h3>" + provenance("01-amx-rampup.html &#xa7;3"), f_tput, True),
 ("<h3>Matrix/tile mapping</h3>" + provenance("01-amx-rampup.html &#xa7;4, minus the intrinsics skeleton"), f_gemm, True),
 ("<h3>VNNI B-operand layout</h3>" + provenance("02-tron-decode-amx-plan.html &#xa7;2b"), f_pairs + WORKED_EXAMPLE, True),
 ("<h3>Pair interleave in the AMX kernel</h3>" + provenance("02-tron-decode-amx-plan.html &#xa7;4 (minus the design-decisions table) + &#xa7;4b") + DESIGN_LABELS_NOTE, f_design + f_transpose, True),
 ("<h3>Performance model</h3>" + provenance("02-tron-decode-amx-plan.html &#xa7;6"), f_perf, True),
 ("<h3>Precision</h3>" + provenance("02-tron-decode-amx-plan.html &#xa7;6b"), f_precision, True),
 ("<h3>What AMX requires from the system</h3>" + provenance("01-amx-rampup.html &#xa7;6 (with a new per-instruction Function column)"), f_system, True),
 ("<h3>Trade-offs and pitfalls</h3>" + provenance("01-amx-rampup.html &#xa7;7"), f_tradeoffs, True),
 ("<h2>The problem being solved</h2>", None, False),
 ("<h3>Decode architecture</h3>" + provenance("02-tron-decode-amx-plan.html &#xa7;1&#x2013;2, then pr-rampup.html &#xa7;1"), f_arch + f_swattn + f_problem, True),
 ("<h2>What the PR actually changes</h2>" + provenance("pr-rampup.html &#xa7;3"), f_changes, False),
 ("<h3>Deep-dive: the mirror layout</h3>" + provenance("2026-08-19-amx-status.html &#xa7;4 + pr-rampup.html &#xa7;4.3"), f_mirror_st + f_whytwok + NO_TRANSPOSE, True),
 ("<h3>The cost of maintaining the mirror</h3>", MIRROR_COST, True),
 ("<h3>Why the arena never grows</h3>", ARENA_NO_GROW, True),
 ("<h2>FPGA attention and AMX</h2>" + provenance("pr-rampup.html &#xa7;4.2"), f_hwmode + HWMODE_QA, False),
 ("<h2>Test results</h2>" + provenance("pr-rampup.html &#xa7;5 (table replaced by charts) + &#xa7;5.1"),
  chart_decode + chart_prefill + f_evidence_rest + f_llama, False),
 ("<h2>Supported geometry and model coverage</h2>" + provenance("pr-rampup.html &#xa7;4.1"), f_geometry + GEOMETRY_QA, False),
 ("<h2>Glossary</h2>", None, False),
 ("<h3>Terminology for the numbers</h3>" + provenance("01-amx-rampup.html &#xa7;0"), f_terms, True),
 ("<h3>Glossary (doc 01)</h3>" + provenance("01-amx-rampup.html &#xa7;9"), f_gloss01, True),
 ("<h3>Glossary in plain words (PR ramp-up)</h3>" + provenance("pr-rampup.html &#xa7;6"), f_glosspr, True),
 ("<h3>Glossary (doc 02)</h3>" + provenance("02-tron-decode-amx-plan.html &#xa7;11"), f_gloss02, True),
]

body = []
seen_ids = set()
toc_entries = []
for head, frag, demote in PARTS:
    # give the skeleton heading an id and collect it for the TOC
    m = re.match(r"<h([23])>(.*?)</h\1>", head, flags=re.S)
    if m:
        level, title = m.group(1), m.group(2)
        slug = "toc-" + re.sub(r"[^a-z0-9]+", "-",
            re.sub(r"&#x[0-9a-f]+;|&[a-z]+;", " ", title.lower())).strip("-")[:40]
        head = f'<h{level} id="{slug}">{title}</h{level}>' + head[m.end():]
        toc_entries.append((int(level), re.sub(r"<[^>]+>", "", title), slug))
    body.append(head)
    if frag is None:
        continue
    frag = fix_hrefs(frag)
    if demote:  # transplant internals sit one level below their h3 skeleton item
        frag = frag.replace("<h3", "<h4").replace("</h3>", "</h4>")
    # dedupe element ids across transplants (keep first, suffix later ones)
    def _dedupe(m):
        i = m.group(1)
        if i in seen_ids:
            return f'id="{i}-2"'
        seen_ids.add(i)
        return m.group(0)
    frag = re.sub(r'id="([A-Za-z0-9_-]+)"', _dedupe, frag)
    body.append(frag)

# single stylesheet: doc 01's sheet is the base; pull ONLY rules for selectors the
# other docs use that 01 does not define (first definition wins, no duplicates).
def style_of(doc):
    return cut(doc, "<style>", "</style>")[len("<style>"):]
def rules_of(css):
    out = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel = " ".join(m.group(1).split())
        if sel not in out:
            out[sel] = m.group(2).strip()
    return out
base = rules_of(style_of(D01))
for other in (D02, PR, ST):
    for sel, body_css in rules_of(style_of(other)).items():
        if sel not in base:
            base[sel] = body_css
base["h4"] = "font-size:13.5px; margin-top:16px;"
base[".prov"] = "font-size:11px; color:#898781; margin:2px 0 10px 0;"
base.setdefault(".toc", "font-size:14px; line-height:1.9; background:#fcfcfb; border:1px solid #e1e0d9; border-radius:10px; padding:12px 18px;")
# doc 01 centers content via a <main> wrapper this assembled doc does not have;
# put the column on <body> instead (modest side padding per jhan 2026-08-21).
assert "margin: 0; padding: 0;" in base["body"]
base["body"] = base["body"].replace(
    "margin: 0; padding: 0;", "max-width: 980px; margin: 24px auto; padding: 0 24px;")
CSS = "\n".join(f"{sel} {{ {b} }}" for sel, b in base.items())

HEADER = f"""<meta charset="utf-8">
<title>Tron AMX Distilled</title>
<style>{CSS}</style>
<h1>Tron AMX distilled</h1>
<p class="sub">The single distilled design document for the AMX software-attention work
(draft PR <a href="https://github.com/positron-ai/tron/pull/3879">positron-ai/tron#3879</a>),
assembled per the Notion skeleton &quot;Distilled&quot; (2026-08-21) from the consensus-reviewed
corpus in <a href="rampup/index.html">rampup/</a>. Regenerate with
<code>python3 exec/gen_distilled.py</code> after editing any source section.
Lineage note: &quot;mirror&quot; names the formulation from Bill&#x27;s PR #2934 (a second,
VNNI-layout copy of K); the implementation and all measurements here are ours.</p>
"""

toc_html = ['<h2 id="toc">Contents</h2>', '<div class="toc">']
for level, title, slug in toc_entries:
    indent = "" if level == 2 else "&#xa0;&#xa0;&#xa0;&#xa0;"
    toc_html.append(f'{indent}<a href="#{slug}">{title}</a><br>')
toc_html.append("</div>")
body.insert(0, "\n".join(toc_html))

assembled = "\n".join(body)
present_ids = set(re.findall(r'id="([A-Za-z0-9_-]+)"', assembled))
id_home = {}
for src, fname in ((D01, "01-amx-rampup.html"), (D02, "02-tron-decode-amx-plan.html"),
                   (PR, "pr-rampup.html"), (ST, "2026-08-19-amx-status.html")):
    for i in re.findall(r'id="([A-Za-z0-9_-]+)"', src):
        id_home.setdefault(i, fname)
def fix_anchor(m):
    anchor = m.group(1)
    if anchor in present_ids:
        return m.group(0)
    home = id_home.get(anchor)
    return f'href="rampup/{home}#{anchor}"' if home else m.group(0)
assembled = re.sub(r'href="#([A-Za-z0-9_-]+)"', fix_anchor, assembled)

out = HEADER + assembled + """
<p class="sub" style="margin-top:28px">Sources and dated records: see each transplanted
section&#x27;s citations; raw data under <code>exec/results/</code>. Decision record (chosen vs
rejected alternatives): <code>amx-design.md</code>.</p>
"""
dst = os.path.join(ROOT, "tron-amx-distilled.html")
open(dst, "w").write(out)
print(f"wrote {dst}: {len(out)} bytes; ids deduped: ok")
# basic sanity
assert "Minimal intrinsics" not in out
assert "Design decisions (with the consensus corrections baked in)" not in out
non_ascii = {c for c in out if ord(c) > 127}
print("non-ascii chars present:", sorted(non_ascii) if non_ascii else "none")
