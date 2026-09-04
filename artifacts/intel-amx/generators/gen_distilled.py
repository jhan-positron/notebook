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
# The "today vs with AMX" page-iteration zoom in doc 02 predates the shipped
# kernels. Label corrections (jhan, 2026-09-01), verified in ~/workspace/tron-amx
# @ 60d66d9c04, src/tron/kernels/amx_attn.cpp + self_attention.hpp:1568-1683:
#  - the AMX lane is the canonical-K default (the mirror lane has no transpose);
#  - PV output blocking is 4+4 (two blocks of 4 result tiles), not the design's
#    6+2 (amx-design.md D4); the TDP count (16) is unchanged;
#  - after PV the tiles are stored to a scratch buffer and folded into v* with
#    one fused multiply-add (v* = v* * corr + o); the max/exp step computes corr.
for _old, _new in [
    ('<text x="10" y="112" font-size="11.5" font-weight="600" fill="#0b0b0b">with AMX</text>',
     '<text x="10" y="112" font-size="11.5" font-weight="600" fill="#0b0b0b">with AMX</text>\n'
     '  <text x="10" y="138" font-size="9.5" fill="#52514e">(canonical-K default)</text>'),
    ('P&#xB7;V: 16 TDPs (6+2)', 'P&#xB7;V: 16 TDPs (4+4)'),
    ('<text x="379" y="113" fill="#fff">max &#xB7; exp &#xB7; rescale v*</text>',
     '<text x="379" y="113" fill="#fff">max &#xB7; exp &#xB7; corr</text>'),
    ('<rect x="620" y="94" width="86" height="30" rx="3" fill="#f7f6f3" stroke="#c3c2b7"/><text x="626" y="113" fill="#52514e">store + v* add</text>',
     '<rect x="620" y="94" width="110" height="30" rx="3" fill="#f7f6f3" stroke="#c3c2b7"/><text x="626" y="113" fill="#52514e">store &#x2192; v* fma-add</text>'),
    ('<rect x="710" y="94" width="60" height="30" rx="3" fill="#1baf7a"/><text x="717" y="113" fill="#fff">next page</text>',
     '<rect x="734" y="94" width="60" height="30" rx="3" fill="#1baf7a"/><text x="741" y="113" fill="#fff">next page</text>'),
    ('<svg viewBox="0 0 980 250" width="980" height="250" role="img" aria-label="Zoom into one page iteration of the attention kernel showing which spans AMX replaces">',
     '<svg viewBox="0 0 980 262" width="980" height="262" role="img" aria-label="Zoom into one page iteration of the attention kernel showing which spans AMX replaces">'),
    ('<text x="10" y="238" font-size="11" fill="#898781">Span widths schematic, not measured. Today',
     '<text x="70" y="222" font-size="9.5" fill="#898781">Labels updated 2026-09-01 to the shipped kernels: this lane is the canonical-K default; P&#xB7;V blocking is 4+4 (decision D4); corr = exp(m_old &#x2212; m_new) is applied in the fma-add.</text>\n'
     '  <text x="70" y="234" font-size="9.5" fill="#898781">The mirror formulation removes the transpose box; both formulations side by side: the canonical-vs-mirror figure under &quot;What the PR actually changes&quot;.</text>\n'
     '  <text x="10" y="250" font-size="11" fill="#898781">Span widths schematic, not measured. Today'),
]:
    assert f_swattn.count(_old) == 1, _old[:70]
    f_swattn = f_swattn.replace(_old, _new)
# Decode-step lanes figure ("One decode step, layer l"): expand the "CPU
# attention workers" lane (jhan, 2026-09-02). Code-verified in
# ~/workspace/tron-amx @ 60d66d9c04: self_attention.hpp:801-894
# (run_attention_job), 1025-1047 (run_sections), 1104-1192 (run_joins),
# 1553-1572 (AMX page predicate), llama.hpp:718-732 (run_pre_attn),
# src/system/mwaitx.cpp:98-190 (monitor_and_wait).
#  - the lane shows the real block order: the three waits behind "wait Q",
#    the all-roped barrier tick, ready pages, wait K/V, the pending page,
#    the per-KV-head poll, the join, the end-of-layer barrier tick;
#  - the pending page loses the AMX outline: a partial page (< 64 tokens)
#    takes the AVX path, AMX runs only on full ready pages;
#  - a zoom strip under the lanes expands one worker's 12 steps for
#    minibatch A; the figure grows from 368 to 556 px.
def _replace_once(frag, old, new):
    assert frag.count(old) == 1, old[:70]
    return frag.replace(old, new)

_a = f_arch.find('  <!-- ATTENTION lane (y 264..302)')
assert _a >= 0, "attention lane comment not found"
_b = f_arch.find('</g>', _a)
assert _b > _a
_b += len('</g>')
ATTN_LANE_NEW = '''  <!-- ATTENTION lane (y 264..302): orange A #eb6834, pale B #f7c4ad; block order from run_attention_job (detail added 2026-09-02, see zoom strip) -->
  <g font-size="9.5">
    <rect x="160" y="264" width="52" height="38" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/><text x="164" y="279" fill="#898781">wait Q</text><text x="164" y="293" fill="#898781">(zoom 1&#x2013;3)</text>
    <rect x="216" y="264" width="52" height="38" rx="3" fill="#eb6834"/><text x="221" y="286" fill="#fff">rope Q A</text>
    <rect x="272" y="264" width="12" height="38" rx="2" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <rect x="288" y="264" width="136" height="38" rx="3" fill="#eb6834" stroke="#d03b3b" stroke-width="2.5"/><text x="294" y="279" fill="#fff">ready pages (old KV):</text><text x="294" y="294" fill="#fff">per-page m*, s*, v* update</text>
    <rect x="428" y="264" width="40" height="38" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/><text x="432" y="279" fill="#898781">wait</text><text x="432" y="293" fill="#898781">K/V &#x2113;</text>
    <rect x="472" y="264" width="44" height="38" rx="3" fill="#eb6834"/><text x="476" y="279" fill="#fff">pending</text><text x="476" y="294" fill="#fff">page</text>
    <rect x="520" y="264" width="28" height="38" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/><text x="524" y="286" fill="#898781">poll</text>
    <rect x="552" y="264" width="44" height="38" rx="3" fill="#eb6834"/><text x="556" y="279" fill="#fff">join &#x2192;</text><text x="556" y="294" fill="#fff">vo(A)</text>
    <rect x="600" y="264" width="12" height="38" rx="2" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <rect x="616" y="264" width="48" height="38" rx="3" fill="#f7c4ad"/><text x="620" y="286" fill="#0b0b0b">rope Q B</text>
    <rect x="668" y="264" width="12" height="38" rx="2" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <rect x="684" y="264" width="108" height="38" rx="3" fill="#f7c4ad" stroke="#d03b3b" stroke-width="2.5"/><text x="690" y="279" fill="#0b0b0b">attention B: ready</text><text x="690" y="294" fill="#0b0b0b">+ pending</text>
    <rect x="796" y="264" width="26" height="38" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/><text x="800" y="286" fill="#898781">poll</text>
    <rect x="826" y="264" width="42" height="38" rx="3" fill="#f7c4ad"/><text x="830" y="279" fill="#0b0b0b">join &#x2192;</text><text x="830" y="294" fill="#0b0b0b">vo(B)</text>
    <rect x="872" y="264" width="12" height="38" rx="2" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <rect x="888" y="264" width="64" height="38" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/><text x="892" y="279" fill="#898781">idle until</text><text x="892" y="293" fill="#898781">&#x2113;+1 Q</text>
  </g>'''
f_arch = f_arch[:_a] + ATTN_LANE_NEW + f_arch[_b:]

ZOOM_STRIP = '''  <!-- ZOOM strip (added 2026-09-02): one attention worker, minibatch A, the 12 steps of run_pre_attn + run_attention_job -->
  <g stroke="#898781" stroke-dasharray="3 2" fill="none">
    <line x1="160" y1="304" x2="160" y2="334"/>
    <line x1="596" y1="304" x2="952" y2="334"/>
  </g>
  <g font-size="11" font-weight="600" fill="#0b0b0b">
    <text x="10" y="358">Zoom: one attention</text>
    <text x="10" y="372">worker, minibatch A</text>
  </g>
  <text x="10" y="386">
    <tspan font-size="9.5" fill="#898781">the orange A span above</tspan>
  </text>
  <g font-size="9">
    <rect x="160" y="336" width="52" height="58" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <text x="164" y="348" fill="#898781">1. barrier:</text><text x="164" y="360" fill="#898781">all arrive,</text><text x="164" y="372" fill="#898781">scratchpads</text><text x="164" y="384" fill="#898781">reset</text>
    <rect x="215" y="336" width="58" height="58" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <text x="219" y="348" fill="#898781">2. wait for</text><text x="219" y="360" fill="#898781">main to open</text><text x="219" y="372" fill="#898781">layer &#x2113;</text><text x="219" y="384" fill="#898781">Q phase</text>
    <rect x="276" y="336" width="43" height="58" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <text x="280" y="348" fill="#898781">3. wait:</text><text x="280" y="360" fill="#898781">WQ row</text><text x="280" y="372" fill="#898781">lands</text>
    <rect x="322" y="336" width="50" height="58" rx="3" fill="#eb6834"/>
    <text x="326" y="348" fill="#fff">4. rope Q</text><text x="326" y="360" fill="#fff">my tokens</text><text x="326" y="372" fill="#fff">only</text>
    <rect x="375" y="336" width="50" height="58" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <text x="379" y="348" fill="#898781">5. barrier:</text><text x="379" y="360" fill="#898781">all Q</text><text x="379" y="372" fill="#898781">roped</text>
    <rect x="428" y="336" width="150" height="58" rx="3" fill="#eb6834" stroke="#d03b3b" stroke-width="2.5"/>
    <text x="433" y="348" fill="#fff">6. ready pages (old KV):</text><text x="433" y="360" fill="#fff">per page QK &#x2192; scale &#x2192;</text><text x="433" y="372" fill="#fff">max&#xB7;exp&#xB7;corr &#x2192; PV &#x2192; m*, s*, v*</text><text x="433" y="384" fill="#fff">(running-softmax state update)</text>
    <rect x="581" y="336" width="46" height="58" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <text x="585" y="348" fill="#898781">7. wait:</text><text x="585" y="360" fill="#898781">K/V &#x2113;</text><text x="585" y="372" fill="#898781">latch</text>
    <rect x="630" y="336" width="60" height="58" rx="3" fill="#eb6834"/>
    <text x="634" y="348" fill="#fff">8. pending</text><text x="634" y="360" fill="#fff">page: partial</text><text x="634" y="372" fill="#fff">&#x2192; AVX path</text>
    <rect x="693" y="336" width="66" height="58" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <text x="697" y="348" fill="#898781">9. spin: wait</text><text x="697" y="360" fill="#898781">for slowest</text><text x="697" y="372" fill="#898781">worker on</text><text x="697" y="384" fill="#898781">my KV heads</text>
    <rect x="762" y="336" width="116" height="58" rx="3" fill="#eb6834"/>
    <text x="766" y="348" fill="#fff">10. join: fold the</text><text x="766" y="360" fill="#fff">others&#x27; (m*, s*, v*)</text><text x="766" y="372" fill="#fff">into worker 0;</text><text x="766" y="384" fill="#fff">v*/s* &#x2192; vo (my tokens)</text>
    <rect x="881" y="336" width="12" height="58" rx="2" fill="#eb6834"/>
    <rect x="896" y="336" width="56" height="58" rx="3" fill="none" stroke="#898781" stroke-dasharray="3 2"/>
    <text x="900" y="348" fill="#898781">12. barrier:</text><text x="900" y="360" fill="#898781">wait slowest</text><text x="900" y="372" fill="#898781">worker</text><text x="900" y="384" fill="#898781">layer done</text>
  </g>
  <g font-size="9.5" fill="#898781">
    <text x="10" y="410">Zoom key. Every attention worker runs the same 12 steps (handwritten llama.hpp schedule); dashed = waiting. No wait sleeps in the OS: latch waits are monitored spins (mwaitx.cpp), step 9 is a bare spin.</text>
    <text x="10" y="423">Barriers (steps 1, 5, 12) need every attention worker to arrive, so each waits for the slowest. Step 12 comes after the vo latch count-down (thin sliver, step 11), so it does not delay main&#x27;s Wo launch.</text>
    <text x="10" y="436">Step 6, the running-softmax update, per page and token: corr = exp(m_old &#x2212; m_new); v* = v*&#xB7;corr + P&#xB7;V; s* = s*&#xB7;corr + &#x3A3;p; m* = m_new, in the worker&#x27;s own scratchpad (attn[worker], never copied out).</text>
    <text x="10" y="449">Step 9: each finished section (one KV head, a run of pages) decrements the atomic sections_left[KV head]; a KV head&#x27;s join starts only when its counter is 0, so the slowest worker on that head gates it.</text>
    <text x="10" y="462">Step 10 is a serial fold, not a tree: per (KV head, token) this worker owns, the other workers&#x27; (m*, s*, v*) merge one by one into worker 0&#x27;s scratchpad, then vo = v*/s* is written (a tree is only a TODO).</text>
    <text x="10" y="475">Step 8: the pending page holds this step&#x27;s new token, so it is partial (&lt; 64 tokens) and takes the AVX path; the AMX kernels run only on full ready pages (step 6).</text>
    <text x="10" y="488">Ingested plugins (the qwen-3-4b runs) skip step 4 on the attention workers (rope Q is a main-stream kernel) and run one minibatch; steps 6-12 are the same code. Detail added 2026-09-02, tron 60d66d9c04.</text>
  </g>
'''
f_arch = _replace_once(f_arch, '  <!-- critical path arrows -->', ZOOM_STRIP + '  <!-- critical path arrows -->')
f_arch = _replace_once(f_arch,
    '<path d="M 310 248 C 335 258 380 260 402 262" marker-end="url(#arrR)"/>',
    '<path d="M 310 248 C 340 258 400 260 430 262" marker-end="url(#arrR)"/>')
f_arch = _replace_once(f_arch,
    '<path d="M 542 292 C 640 300 640 182 488 176" marker-end="url(#arrR)"/>',
    '<path d="M 596 292 C 690 300 690 182 488 176" marker-end="url(#arrR)"/>')
f_arch = _replace_once(f_arch,
    '<text x="160" y="326" font-size="11" fill="#d03b3b" font-weight="600">critical chain:',
    '<text x="160" y="508" font-size="11" fill="#d03b3b" font-weight="600">critical chain:')
f_arch = _replace_once(f_arch,
    '<text x="10" y="346" font-size="10.5" fill="#898781">Schematic: block order and dependencies from',
    '<text x="10" y="528" font-size="10.5" fill="#898781">Schematic: block order and dependencies from')
f_arch = _replace_once(f_arch,
    '<text x="10" y="362" font-size="10.5" fill="#898781">Red-outlined blocks are where the AMX kernels go.',
    '<text x="10" y="544" font-size="10.5" fill="#898781">Red-outlined blocks are where the AMX kernels go.')
f_arch = _replace_once(f_arch,
    '<svg viewBox="0 0 980 368" width="980" height="368" role="img" aria-label="Wall-clock lanes: one decode layer across five actors - CPU main and helpers, per-card TX workers, FPGA, per-card RX workers, CPU attention workers - two minibatches interleaved">',
    '<svg viewBox="0 0 980 556" width="980" height="556" role="img" aria-label="Wall-clock lanes: one decode layer across five actors - CPU main and helpers, per-card TX workers, FPGA, per-card RX workers, CPU attention workers - two minibatches interleaved; plus a zoom strip expanding one attention worker&#x27;s twelve steps for minibatch A">')
f_arch = _replace_once(f_arch,
    '<text x="10" y="294">rope Q + attention</text>',
    '<text x="10" y="294">rope Q &#xB7; pages &#xB7; join</text>')
f_arch = _replace_once(f_arch,
    '<rect x="620" y="40" width="12" height="10" fill="none" stroke="#d03b3b" stroke-width="2"/><text x="636" y="49">AMX target</text>',
    '<rect x="620" y="40" width="12" height="10" fill="none" stroke="#d03b3b" stroke-width="2"/><text x="636" y="49">AMX target</text>\n'
    '    <rect x="720" y="40" width="6" height="10" fill="none" stroke="#898781" stroke-dasharray="3 2"/><text x="732" y="49">narrow tick: barrier (all attention workers)</text>')
f_arch = _replace_once(f_arch,
    'note the RX workers are also on\nthat critical chain.</figcaption>',
    'note the RX workers are also on\nthat critical chain. The zoom strip under the lanes (added 2026-09-02) expands the orange minibatch-A span for one attention\n'
    'worker into its 12 steps: the three separate waits behind &quot;wait Q&quot;, RoPE on the worker&#x27;s own tokens, the all-workers-roped\n'
    'barrier, the per-page running-softmax update (m*, s*, v*) over the ready pages, the wait for this layer&#x27;s K/V, the partial\n'
    'pending page, the per-KV-head spin that waits for the slowest worker holding a section of that head, the serial fold that writes\n'
    'vo, the vo latch count-down that releases main, and the end-of-layer barrier. Code: <span class="cite">self_attention.hpp:801-894\n'
    'run_attention_job; 1025-1047 run_sections; 1104-1192 run_joins; llama.hpp:718-732 run_pre_attn</span> (tron 60d66d9c04).</figcaption>')


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

# 6.4 measured-column header: say AT the table which half of Intel's
# "latency / throughput" pair the back-to-back measurement compares with
# (jhan 2026-08-31: on first read he compared it against the latency half).
_MEAS_HDR = ('Measured 6962P, back-to-back cycles/op (2 reps unless noted) '
             '<span class="pill meas">measured</span>')
assert f_system.count(_MEAS_HDR) == 1, "6.4 measured-column header not found"
f_system = f_system.replace(_MEAS_HDR, _MEAS_HDR +
    ' &#x2014; a repeat interval: compare it with the <i>throughput</i> half of the'
    ' Intel pair where one exists (<a href="#lat-tput">explained below</a>)', 1)

# 6.4 sub-subsection: what "latency / throughput" mean, and what the
# back-to-back benchmark actually measures (jhan's question, 2026-08-31).
# Facts: opt-manual ch. 20.3 text + Table 20-2 (read on delphi-3bda,
# /scratch/jhan/Intel_vs_AMD/refs/opt-manual-v1-rev050-248966.txt:31300-31329),
# isa-extensions-progref.txt:7127 (LDTILECFG zeroes TILEDATA), and
# exec/bench_amx_overhead.cpp modes (tdp_lat / tdp_tput / ldtilecfg).
LAT_TPUT = """
<p class="prov">New sub-subsection (2026-08-31), answering a question on the column semantics;
not a transplant (generator: <code>exec/gen_distilled.py</code>).</p>
<p id="lat-tput"><b>Reading &quot;latency / throughput&quot;: the two columns count different
things.</b> In Intel&#x27;s table, <b>latency</b> is the number of cycles from an
instruction&#x27;s start (its operands ready) until its result can be used by a dependent
instruction &#x2014; the result-to-consumer delay. <b>Throughput</b> is reciprocal throughput:
the minimum number of cycles between starting two <i>independent</i> instructions of the same
kind &#x2014; the sustained repeat interval. The two differ because the unit is pipelined: one
<code>TDPBF16PS</code> takes 52 cycles to produce its C tile, but a new <code>TDPBF16PS</code>
may start every 16 cycles as long as it writes a different C tile. 52 &#xf7; 16 &#x2248; 3.25,
so by Intel&#x27;s numbers &#x2265;4 independent accumulator tiles are needed to keep the
multiplier busy; the kernels in this PR cycle four (tmm0&#x2013;tmm3,
<a href="#instr-sequence">&#xa7;&quot;The instruction sequence in practice&quot;</a>). On the
6962P even one dependent chain measured no stall (the TDPBF16PS bullet below), so the four
accumulators are Intel&#x27;s guidance plus headroom, not a measured requirement here.</p>
<figure>
<div class="svgwrap">
<svg viewBox="0 0 980 324" width="980" height="324" role="img"
 aria-label="Timeline drawn to scale: four TDPBF16PS instructions writing tmm0 to tmm3 start 16 cycles apart, the reciprocal throughput, and each finishes 52 cycles after it starts, the latency; a TILESTORED of tmm0 waits until cycle 52. Notes carry the measured cycles per op."
 font-family="system-ui,sans-serif">
<text x="14" y="18" font-size="12.5" font-weight="600" fill="#0b0b0b">Latency vs reciprocal throughput &#x2014; Intel&#x27;s TDPBF16PS row (latency 52 / throughput 16), cycle axis to scale</text>

<!-- latency measure -->
<line x1="170" y1="36" x2="170" y2="48" stroke="#d03b3b" stroke-width="1.4"/>
<line x1="560" y1="36" x2="560" y2="48" stroke="#d03b3b" stroke-width="1.4"/>
<line x1="177" y1="42" x2="553" y2="42" stroke="#d03b3b" stroke-width="1.4"/>
<path d="M177,38 L170,42 L177,46 z" fill="#d03b3b"/>
<path d="M553,38 L560,42 L553,46 z" fill="#d03b3b"/>
<text x="365" y="32" font-size="10.5" font-weight="600" fill="#d03b3b" text-anchor="middle">latency = 52 cycles: from start until the result is usable by a consumer</text>

<!-- TDP lanes -->
<text x="162" y="71" font-size="10.5" fill="#0b0b0b" text-anchor="end">TDP &#x2192; tmm0</text>
<rect x="170" y="58" width="390" height="18" fill="#eae9f4" stroke="#7570b3"/>
<text x="365" y="71" font-size="9.5" fill="#0b0b0b" text-anchor="middle">TDP #1 &#x2014; 52 cycles in flight</text>
<circle cx="560" cy="67" r="3" fill="#1b9e77"/>
<text x="568" y="71" font-size="9.5" fill="#1b9e77">C0 ready</text>

<text x="162" y="101" font-size="10.5" fill="#0b0b0b" text-anchor="end">TDP &#x2192; tmm1</text>
<rect x="290" y="88" width="390" height="18" fill="#eae9f4" stroke="#7570b3"/>
<text x="485" y="101" font-size="9.5" fill="#0b0b0b" text-anchor="middle">TDP #2</text>
<circle cx="680" cy="97" r="3" fill="#1b9e77"/>
<text x="688" y="101" font-size="9.5" fill="#1b9e77">C1 ready</text>

<text x="162" y="131" font-size="10.5" fill="#0b0b0b" text-anchor="end">TDP &#x2192; tmm2</text>
<rect x="410" y="118" width="390" height="18" fill="#eae9f4" stroke="#7570b3"/>
<text x="605" y="131" font-size="9.5" fill="#0b0b0b" text-anchor="middle">TDP #3</text>
<circle cx="800" cy="127" r="3" fill="#1b9e77"/>
<text x="808" y="131" font-size="9.5" fill="#1b9e77">C2 ready</text>

<text x="162" y="161" font-size="10.5" fill="#0b0b0b" text-anchor="end">TDP &#x2192; tmm3</text>
<rect x="530" y="148" width="390" height="18" fill="#eae9f4" stroke="#7570b3"/>
<text x="725" y="161" font-size="9.5" fill="#0b0b0b" text-anchor="middle">TDP #4</text>
<circle cx="920" cy="157" r="3" fill="#1b9e77"/>
<text x="920" y="143" font-size="9.5" fill="#1b9e77" text-anchor="end">C3 ready</text>

<!-- throughput measure -->
<line x1="170" y1="76" x2="170" y2="188" stroke="#1c5cab" stroke-width="0.8" stroke-dasharray="3 3"/>
<line x1="290" y1="106" x2="290" y2="188" stroke="#1c5cab" stroke-width="0.8" stroke-dasharray="3 3"/>
<line x1="177" y1="182" x2="283" y2="182" stroke="#1c5cab" stroke-width="1.4"/>
<path d="M177,178 L170,182 L177,186 z" fill="#1c5cab"/>
<path d="M283,178 L290,182 L283,186 z" fill="#1c5cab"/>
<text x="300" y="179" font-size="10" font-weight="600" fill="#1c5cab">reciprocal throughput = 16 cycles:</text>
<text x="300" y="191" font-size="10" fill="#1c5cab">a new independent TDP may start this often</text>

<!-- the 52-cycle guide -->
<line x1="560" y1="50" x2="560" y2="246" stroke="#d03b3b" stroke-width="0.8" stroke-dasharray="3 3"/>

<!-- store lane -->
<text x="162" y="223" font-size="10.5" fill="#0b0b0b" text-anchor="end">TILESTORED tmm0</text>
<rect x="170" y="210" width="390" height="18" fill="none" stroke="#898781" stroke-dasharray="4 3"/>
<text x="365" y="223" font-size="9" fill="#52514e" text-anchor="middle">waiting for C0 &#x2014; the 52-cycle latency</text>
<rect x="560" y="210" width="120" height="18" fill="#e9f7f1" stroke="#1b9e77"/>
<text x="620" y="223" font-size="9" fill="#0b0b0b" text-anchor="middle">store</text>

<!-- axis -->
<line x1="170" y1="246" x2="950" y2="246" stroke="#c3c2b7"/>
<line x1="170" y1="246" x2="170" y2="251" stroke="#898781"/><text x="170" y="262" font-size="10" fill="#898781" text-anchor="middle">0</text>
<line x1="290" y1="246" x2="290" y2="251" stroke="#898781"/><text x="290" y="262" font-size="10" fill="#898781" text-anchor="middle">16</text>
<line x1="410" y1="246" x2="410" y2="251" stroke="#898781"/><text x="410" y="262" font-size="10" fill="#898781" text-anchor="middle">32</text>
<line x1="530" y1="246" x2="530" y2="251" stroke="#898781"/><text x="530" y="262" font-size="10" fill="#898781" text-anchor="middle">48</text>
<line x1="560" y1="246" x2="560" y2="252" stroke="#d03b3b" stroke-width="1.4"/><text x="560" y="273" font-size="10" font-weight="700" fill="#d03b3b" text-anchor="middle">52</text>
<line x1="650" y1="246" x2="650" y2="251" stroke="#898781"/><text x="650" y="262" font-size="10" fill="#898781" text-anchor="middle">64</text>
<line x1="770" y1="246" x2="770" y2="251" stroke="#898781"/><text x="770" y="262" font-size="10" fill="#898781" text-anchor="middle">80</text>
<line x1="890" y1="246" x2="890" y2="251" stroke="#898781"/><text x="890" y="262" font-size="10" fill="#898781" text-anchor="middle">96</text>
<text x="950" y="262" font-size="10" fill="#898781" text-anchor="end">cycles</text>

<text x="14" y="296" font-size="10.5" font-weight="600" fill="#0b0b0b">52 &#xf7; 16 &#x2248; 3.25 &#x2192; by Intel&#x27;s numbers, four independent C tiles (tmm0&#x2013;tmm3) keep the multiplier accepting new work every 16 cycles.</text>
<text x="14" y="312" font-size="10" fill="#52514e">Measured on the 6962P: 16.2&#x2013;16.4 cycles/op for both the 4-independent-accumulator loop and a dependent same-C chain &#x2014; see the TDPBF16PS bullet below.</text>
</svg>
</div>
<figcaption>Drawn to scale on the cycle axis from Intel&#x27;s published numbers (52 / 16,
<span class="cite">opt-manual:31320-31329</span>); the store block is drawn at its 16-cycle
issue interval &#x2014; its completion in the cache happens later. Schematic: the real kernels
interleave <code>TILELOADD</code>s between the TDPs
(<a href="#instr-sequence">&#xa7;&quot;The instruction sequence in practice&quot;</a>).</figcaption>
</figure>
<p><b>What the measured column is.</b> The benchmark
(<span class="mono">exec/bench_amx_overhead.cpp</span>) runs one instruction in a tight loop and
divides total cycles by iterations, with a null-loop baseline subtracted. That is a repeat-interval
measurement &#x2014; a <i>throughput</i>-style number, because the loop lets consecutive
instructions overlap &#x2014; and where Intel publishes a throughput it matches: TILELOADD 8.4
vs 8, TDPBF16PS 16.2&#x2013;16.4 vs 16, TILESTORED 16.1 vs 16 (TILEZERO is discussed in the
closing paragraph). It is <i>not</i> a latency measurement. Two rows still say something about
latency:</p>
<ul>
<li><b>TDPBF16PS:</b> the <span class="mono">tdp_lat</span> mode chains every TDP through the
<i>same</i> C tile &#x2014; a deliberate dependency chain, the standard latency probe &#x2014;
yet it also measured 16.2&#x2013;16.4 cycles/op. So the effective C&#x2192;C dependency
completes in &#x2264;16 cycles, consistent with internal forwarding of the accumulator. On this
reading, Intel&#x27;s 52 cycles would be the delay to <i>other</i> consumers of the result (for
example <code>TILESTORED</code> reading C); this suite did not measure that path, so 52 remains
the published number, not a confirmed one.</li>
<li><b>LDTILECFG:</b> its back-to-back repeat interval measured 182&#x2013;216 cycles (4 of 5
reps at ~182) &#x2014; the same magnitude as Intel&#x27;s published 204-cycle <i>latency</i>,
and about 11% below it (the published table is Sapphire-Rapids-era, so the 6962P&#x27;s own
latency may be nearer 182). An interval this close to the latency means consecutive
<code>LDTILECFG</code>s gain little or nothing from pipelining &#x2014; each applies the
configuration, which also zeroes all tile data
<span class="cite">isa-extensions-progref:7127</span> &#x2014; so for this non-pipelined
instruction the repeat interval and the latency roughly coincide.</li>
</ul>
<p><b>Latency and the memory hierarchy; the &quot;&#x2014;&quot; cells.</b> For the
memory-touching instructions, a fixed published latency must assume a fixed cache level; Intel
does not state which, and the usual convention is a first-level hit &#x2014; our own TILELOADD
measurement was taken L1-hot. A miss adds the ordinary L2/L3/DRAM latency on top, which the
table does not model. TILESTORED writes into the DCU (the Data Cache Unit &#x2014; the
first-level cache) <span class="cite">opt-manual:31300-31310</span>. Intel marks the remaining
cells &quot;Not Relevant&quot; without giving reasons; our reading: TILESTORED has no latency
entry since no register-side instruction consumes a store&#x27;s result, and the three
configuration instructions (LDTILECFG, STTILECFG, TILERELEASE) have no throughput entry since a
real kernel issues them once per region rather than in a stream. TILEZERO&#x27;s published
throughput of 0 is conventionally read as the zeroing being handled before the execution units;
we measured 0.50 cycles/op &#x2014; two per cycle &#x2014; consistent with that reading rather
than a literal 0.</p>
"""
_LAT_TPUT_MARKER = ('&quot;wait&quot; required between AMX instructions '
                    'beyond these pipelined costs.</p>')
assert f_system.count(_LAT_TPUT_MARKER) == 1, "6.4 latency/throughput anchor not found"
f_system = f_system.replace(_LAT_TPUT_MARKER, _LAT_TPUT_MARKER + LAT_TPUT, 1)

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

# ---------------- instruction sequence: authored subsection (2026-08-31) ----------------
# Answers jhan's question: for typical AMX usage (tron), what is the sequence
# to execute the instructions (config, load, calculate, store, ...)?
# Facts verified in the PR worktree ~/workspace/tron-amx, branch jhan-amx-p0
# @ 60d66d9c04: src/tron/kernels/amx_attn.cpp (all intrinsics),
# h/tron/models/self_attention.hpp:1380/1480 (region), :1568-1680 (dispatch).

INSTR_SEQ = """
<h4 id="instr-sequence">The instruction sequence in practice (tron&#x27;s kernels)</h4>
<p class="prov">New for this document (jhan&#x27;s question, 2026-08-31); code-verified in the PR
worktree: <code>src/tron/kernels/amx_attn.cpp</code> (the only translation unit with tile
intrinsics), <code>self_attention.hpp:1380&#x2013;1680</code>; branch jhan-amx-p0 @ 60d66d9c04.</p>
<p>The table above lists the instructions one by one; this subsection shows the order in which a
real kernel issues them. Typical AMX usage &#x2014; and tron&#x27;s attention kernels specifically
&#x2014; nests the instructions at four frequencies: an OS grant once per process, one
configuration instruction per region, a zero &#x2192; load &#x2192; multiply &#x2192; store cycle
per matmul, and a release when the region ends. A <b>region</b> is the span between
<code>LDTILECFG</code> and <code>TILERELEASE</code>; in tron it is one worker thread&#x27;s whole
loop over KV pages (a KV page is a 64-token block of the key/value cache). tron runs two matmuls
per page: <b>QK</b> (the score matmul, S = Q&#xb7;K&#x1d40;) and <b>PV</b> (the output matmul,
O = P&#xb7;V, where P holds the exponentiated scores). AMX has no elementwise instructions
&#x2014; the table above is complete: configure, load, store, zero, multiply-accumulate &#x2014;
so the arithmetic between the two matmuls (scaling, softmax) must leave the tile registers, run
on AVX-512 (the CPU&#x27;s ordinary 512-bit vector instructions), and re-enter through a fresh
tile load.</p>
<figure>
<div class="svgwrap">
<svg viewBox="0 0 980 460" width="980" height="460" role="img"
 aria-label="Component diagram: system RAM feeds operand tiles tmm4 to tmm6 through the caches; the TMUL unit multiplies them into accumulator tiles tmm0 to tmm3; tile stores write fp32 results back to RAM; a dashed loop shows the AVX-512 softmax between the QK and PV matmuls. Circled numbers 1 to 8 mark the instruction sequence."
 font-family="system-ui,sans-serif">
<defs>
<marker id="iseq-a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="#52514e"/></marker>
<marker id="iseq-g" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="#1b9e77"/></marker>
</defs>
<text x="14" y="20" font-size="12.5" font-weight="600" fill="#0b0b0b">One AMX region in tron&#x27;s attention page loop &#x2014; hardware components and the numbered instruction sequence</text>

<!-- one-time strip -->
<rect x="14" y="36" width="296" height="56" fill="#ffffff" stroke="#898781"/>
<circle cx="32" cy="64" r="9" fill="#1c5cab"/><text x="32" y="68" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">1</text>
<text x="48" y="52" font-size="10.5" font-weight="600" fill="#0b0b0b">once per process &#x2014; the OS grant (&#xa7;6.1)</text>
<text x="48" y="66" font-size="9.5" fill="#52514e">CPUID + XGETBV probe, then the arch_prctl</text>
<text x="48" y="79" font-size="9.5" fill="#52514e">(ARCH_REQ_XCOMP_PERM, XTILEDATA) system call</text>

<rect x="326" y="36" width="296" height="56" fill="#ffffff" stroke="#898781"/>
<circle cx="344" cy="64" r="9" fill="#1c5cab"/><text x="344" y="68" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">2</text>
<text x="360" y="52" font-size="10.5" font-weight="600" fill="#0b0b0b">once per region &#x2014; begin_region()</text>
<text x="360" y="66" font-size="9.5" fill="#52514e">LDTILECFG reads a 64 B config struct:</text>
<text x="360" y="79" font-size="9.5" fill="#52514e">all 8 tiles become 16 rows &#xd7; 64 B</text>
<line x1="420" y1="94" x2="420" y2="136" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>

<rect x="638" y="36" width="328" height="56" fill="#ffffff" stroke="#898781"/>
<circle cx="656" cy="64" r="9" fill="#1c5cab"/><text x="656" y="68" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">8</text>
<text x="672" y="52" font-size="10.5" font-weight="600" fill="#0b0b0b">region exit &#x2014; end_region()</text>
<text x="672" y="66" font-size="9.5" fill="#52514e">TILERELEASE resets tiles to INIT, so context</text>
<text x="672" y="79" font-size="9.5" fill="#52514e">switches can skip the 8 KB tile state (&#xa7;6.2)</text>
<line x1="700" y1="116" x2="700" y2="96" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>

<!-- RAM sources -->
<rect x="14" y="130" width="200" height="220" fill="none" stroke="#898781"/>
<text x="24" y="148" font-size="10.5" font-weight="600" fill="#0b0b0b">system RAM</text>
<text x="24" y="161" font-size="9" fill="#52514e">(reached through L2 &#x2192; L1)</text>
<rect x="24" y="172" width="180" height="40" fill="#fdeee1" stroke="#d95f02"/>
<text x="114" y="188" font-size="10" fill="#0b0b0b" text-anchor="middle">packed Q group &#x2014; A of QK</text>
<text x="114" y="202" font-size="9" fill="#52514e" text-anchor="middle">4 KB thread-local buffer</text>
<rect x="24" y="222" width="180" height="54" fill="#eae9f4" stroke="#7570b3"/>
<text x="114" y="236" font-size="10" fill="#0b0b0b" text-anchor="middle">KV page &#x2014; B operands:</text>
<text x="114" y="249" font-size="9" fill="#52514e" text-anchor="middle">QK: K-mirror panels</text>
<text x="114" y="262" font-size="9" fill="#52514e" text-anchor="middle">PV: pair-interleaved V rows</text>
<rect x="24" y="286" width="180" height="40" fill="#fdeee1" stroke="#d95f02" stroke-dasharray="4 3"/>
<text x="114" y="302" font-size="10" fill="#0b0b0b" text-anchor="middle">P = exp(s) as bf16 &#x2014; A of PV</text>
<text x="114" y="316" font-size="9" fill="#52514e" text-anchor="middle">16 rows &#xd7; 64 bf16 values (step 7)</text>

<!-- core container -->
<rect x="300" y="118" width="430" height="240" fill="none" stroke="#898781" stroke-dasharray="5 4"/>
<text x="310" y="134" font-size="10.5" font-weight="600" fill="#52514e">one physical core</text>
<rect x="316" y="142" width="170" height="22" fill="#ffffff" stroke="#898781"/>
<text x="401" y="157" font-size="9.5" fill="#0b0b0b" text-anchor="middle">TILECFG state (64 B)</text>

<rect x="316" y="176" width="150" height="144" fill="none" stroke="#52514e"/>
<text x="391" y="190" font-size="9.5" font-weight="600" fill="#0b0b0b" text-anchor="middle">operand tiles</text>
<rect x="324" y="198" width="134" height="24" fill="#fdeee1" stroke="#d95f02"/>
<text x="391" y="214" font-size="9.5" fill="#0b0b0b" text-anchor="middle">tmm4 &#x2014; A</text>
<rect x="324" y="228" width="134" height="24" fill="#eae9f4" stroke="#7570b3"/>
<text x="391" y="244" font-size="9.5" fill="#0b0b0b" text-anchor="middle">tmm5 &#x2014; B (panels 0, 2)</text>
<rect x="324" y="258" width="134" height="24" fill="#eae9f4" stroke="#7570b3"/>
<text x="391" y="274" font-size="9.5" fill="#0b0b0b" text-anchor="middle">tmm6 &#x2014; B (panels 1, 3)</text>
<rect x="324" y="288" width="134" height="24" fill="none" stroke="#898781" stroke-dasharray="3 3"/>
<text x="391" y="304" font-size="8.5" fill="#52514e" text-anchor="middle">tmm7 &#x2014; configured, unused</text>

<rect x="506" y="176" width="90" height="144" fill="#ffffff" stroke="#d95f02" stroke-width="1.6"/>
<circle cx="551" cy="164" r="9" fill="#1c5cab"/><text x="551" y="168" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">5</text>
<text x="551" y="222" font-size="12" font-weight="700" fill="#0b0b0b" text-anchor="middle">TMUL</text>
<text x="551" y="240" font-size="8.5" fill="#52514e" text-anchor="middle">TDPBF16PS</text>
<text x="551" y="254" font-size="8.5" fill="#52514e" text-anchor="middle">C += A &#xb7; B</text>
<text x="551" y="268" font-size="8.5" fill="#52514e" text-anchor="middle">8192 MACs/instr</text>

<rect x="636" y="176" width="80" height="144" fill="none" stroke="#52514e"/>
<circle cx="676" cy="164" r="9" fill="#1c5cab"/><text x="676" y="168" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">3</text>
<text x="676" y="190" font-size="9.5" font-weight="600" fill="#0b0b0b" text-anchor="middle">C tiles</text>
<rect x="644" y="198" width="64" height="26" fill="#e9f7f1" stroke="#1b9e77"/>
<text x="676" y="215" font-size="9.5" fill="#0b0b0b" text-anchor="middle">tmm0</text>
<rect x="644" y="228" width="64" height="26" fill="#e9f7f1" stroke="#1b9e77"/>
<text x="676" y="245" font-size="9.5" fill="#0b0b0b" text-anchor="middle">tmm1</text>
<rect x="644" y="258" width="64" height="26" fill="#e9f7f1" stroke="#1b9e77"/>
<text x="676" y="275" font-size="9.5" fill="#0b0b0b" text-anchor="middle">tmm2</text>
<rect x="644" y="288" width="64" height="26" fill="#e9f7f1" stroke="#1b9e77"/>
<text x="676" y="305" font-size="9.5" fill="#0b0b0b" text-anchor="middle">tmm3</text>

<text x="316" y="346" font-size="9" fill="#52514e">each tile 1 KB (16 rows &#xd7; 64 B); the 8-tile file is the 8 KB TILEDATA state (&#xa7;6.2)</text>

<!-- RAM destinations -->
<rect x="766" y="130" width="200" height="220" fill="none" stroke="#898781"/>
<text x="776" y="148" font-size="10.5" font-weight="600" fill="#0b0b0b">system RAM</text>
<text x="776" y="161" font-size="9" fill="#52514e">(the same memory, drawn twice)</text>
<rect x="776" y="172" width="180" height="52" fill="#e9f7f1" stroke="#1b9e77"/>
<text x="866" y="188" font-size="10" fill="#0b0b0b" text-anchor="middle">s &#x2014; fp32 scores (QK out)</text>
<text x="866" y="202" font-size="9" fill="#52514e" text-anchor="middle">16 rows &#xd7; 64 tokens,</text>
<text x="866" y="215" font-size="9" fill="#52514e" text-anchor="middle">thread-local scratch</text>
<rect x="776" y="236" width="180" height="52" fill="#e9f7f1" stroke="#1b9e77"/>
<text x="866" y="252" font-size="10" fill="#0b0b0b" text-anchor="middle">o &#x2014; fp32 attn out (PV out)</text>
<text x="866" y="266" font-size="9" fill="#52514e" text-anchor="middle">16 rows &#xd7; 128 dims; caller</text>
<text x="866" y="279" font-size="9" fill="#52514e" text-anchor="middle">merges into running totals</text>

<!-- flow arrows -->
<line x1="204" y1="192" x2="312" y2="210" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>
<line x1="204" y1="249" x2="312" y2="245" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>
<circle cx="240" cy="227" r="9" fill="#1c5cab"/><text x="240" y="231" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">4</text>
<text x="254" y="231" font-size="9" fill="#52514e">TILELOADD</text>
<line x1="466" y1="212" x2="502" y2="222" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>
<line x1="466" y1="252" x2="502" y2="262" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>
<line x1="596" y1="240" x2="632" y2="240" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>
<line x1="716" y1="198" x2="772" y2="198" stroke="#52514e" stroke-width="1.6" marker-end="url(#iseq-a)"/>
<circle cx="744" cy="184" r="9" fill="#1c5cab"/><text x="744" y="188" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">6</text>

<!-- QK -> PV return loop -->
<path d="M 866 352 L 866 414 L 714 414" fill="none" stroke="#1b9e77" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#iseq-g)"/>
<path d="M 380 414 L 114 414 L 114 330" fill="none" stroke="#1b9e77" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#iseq-g)"/>
<rect x="380" y="386" width="330" height="56" fill="#ffffff" stroke="#1b9e77"/>
<circle cx="398" cy="414" r="9" fill="#1c5cab"/><text x="398" y="418" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">7</text>
<text x="414" y="406" font-size="10" font-weight="600" fill="#0b0b0b">between QK and PV &#x2014; AVX-512, not tiles:</text>
<text x="414" y="420" font-size="9.5" fill="#52514e">scale &#xb7; running max &#xb7; exp on the stored s rows,</text>
<text x="414" y="433" font-size="9.5" fill="#52514e">then fp32&#x2192;bf16 pack into P (the next A operand)</text>
</svg>
</div>
<figcaption>Schematic (components not to scale). TMUL is the tile matrix-multiply unit
&#x2014; the per-core execution unit that runs <code>TDPBF16PS</code>. Circled numbers are the
steps of the list below; solid arrows carry the QK matmul&#x27;s data, and the dashed green loop
is the QK&#x2192;PV hand-off between the two matmuls. In the PV matmul the A-tile loads read P
(bottom-left box) instead of the packed Q, the B tiles read the pair-interleaved V rows, and the
store lands in <code>o</code> instead of <code>s</code>. Mirror-flavor operand roles shown;
the canonical flavor swaps them (see the note after the list). Code:
<code>src/tron/kernels/amx_attn.cpp</code>, <code>self_attention.hpp:1380&#x2013;1680</code>.</figcaption>
</figure>
<ol>
<li><b>Once per process &#x2014; the OS grant.</b> Before any tile instruction,
<code>detect_and_request()</code> (<code>amx_attn.cpp:54&#x2013;68</code>) checks the
<code>TRON_AMX_DISABLE</code> kill switch, CPUID leaf 7.0 (AMX-BF16 + AMX-TILE), and XCR0 bits
17:18 (the OS tile-state enable), then calls
<code>arch_prctl(ARCH_REQ_XCOMP_PERM, XFEATURE_XTILEDATA)</code>. The result is computed once and
cached for the process lifetime (<code>available()</code>, <code>:72&#x2013;82</code>). Measured
cost: about 0.9 &#xb5;s for the system call, plus a one-time 4&#x2013;9 &#xb5;s trap on each
thread&#x27;s first TILEDATA-touching instruction &#x2014; a tile load, store, zero, or multiply;
<code>LDTILECFG</code> alone does not trap (<a href="#overhead">&#xa7;6.4</a>).</li>
<li><b>Once per region &#x2014; configure.</b> <code>begin_region()</code>
(<code>amx_attn.cpp:84&#x2013;92</code>) fills a 64-byte <code>tile_config</code> struct
(palette 1 &#x2014; the only tile layout the ISA currently defines &#x2014; with all 8 tiles set to
16 rows &#xd7; 64 B) and issues <code>LDTILECFG</code>. tron calls it once before a
worker&#x27;s page loop (<code>self_attention.hpp:1380</code>), so the roughly 200-cycle cost
(measured 182&#x2013;216, <a href="#overhead">&#xa7;6.4</a>) is amortized over every page the
worker visits.</li>
<li><b>Per matmul, first &#x2014; clear the accumulators.</b> <code>TILEZERO</code> clears the four
fp32 accumulator tiles tmm0&#x2013;tmm3 (e.g. <code>amx_attn.cpp:243&#x2013;246</code>); no memory
traffic. Four accumulators give the multiplier four independent dependency chains. Intel&#x27;s
timing table (the Throughput section below) recommends &#x2265;3&#x2013;4 such chains to cover the
52-cycle latency of <code>TDPBF16PS</code> (written TDP below); the &#xa7;6.4 microbenchmark
measured no added stall even on one dependent chain, so on the 6962P this is Intel guidance, not
a measured requirement.</li>
<li><b>Per 32-dim reduction step &#x2014; load operands.</b> <code>TILELOADD</code> fills the
operand tiles: one load of the operand all four TDPs in the step share (the packed Q group in QK,
the bf16 P rows in PV; tmm4 in the figure), then four loads of the per-block KV operand, one per
accumulator &#x2014; in QK the K-mirror panels (a panel = one 16-token &#xd7; 32-dim block of the
page&#x27;s pair-interleaved K copy; the mirror flavor is defined in the note after this list), in
PV the V pair-rows. Each load moves up to 1 KB as 16 row reads
of 64 B through the ordinary cache hierarchy (8.4 cycles/load measured L1-hot,
<a href="#overhead">&#xa7;6.4</a>). The KV loads alternate between two tiles (tmm5/tmm6 in the
figure) so a load never overwrites the tile a still-in-flight TDP is reading.</li>
<li><b>Per step, interleaved with the loads &#x2014; multiply.</b> <code>TDPBF16PS</code>
accumulates C += A &#xb7; B into each accumulator tile in turn (16&#xd7;16&#xd7;32 = 8192
multiply-accumulate operations (MACs) per instruction; 16.2&#x2013;16.4 cycles/op measured
back-to-back). In QK each accumulator holds one
16-token block of the 64-token page; the step loop is <code>amx_attn.cpp:249&#x2013;263</code>.</li>
<li><b>Per matmul, last &#x2014; store the result.</b> <code>TILESTORED</code> writes each
accumulator tile to an ordinary fp32 buffer: the 16&#xd7;64 score block <code>s</code> after QK
(<code>amx_attn.cpp:264&#x2013;267</code>), the 16&#xd7;128 output <code>o</code> after PV
(<code>:225&#x2013;228</code>). A tile store is the only way results leave the tile file.</li>
<li><b>Between the two matmuls &#x2014; AVX-512, inside the region.</b> The softmax arithmetic
(scale, running max, exp &#x2014; the streaming-softmax update of the per-worker (m*, s*, v*)
scratchpad described in the Decode architecture section) runs on AVX-512 against the stored
<code>s</code> rows (<code>self_attention.hpp:1642&#x2013;1657</code>),
and the PV kernel packs the resulting exp rows to bf16 pairs (<code>P</code>,
<code>amx_attn.cpp:190&#x2013;199</code>) before they re-enter as the next A tile. The tile
configuration stays loaded throughout &#x2014; mixing vector and tile instructions needs no fence
or reconfiguration (<a href="#overhead">&#xa7;6.4</a>).</li>
<li><b>Region exit &#x2014; release.</b> <code>end_region()</code> issues <code>TILERELEASE</code>
(<code>self_attention.hpp:1480</code>), returning the tile file to its INIT state so context
switches can skip saving the 8 KB TILEDATA (&#xa7;6.2); about 15 cycles measured.</li>
</ol>
<p><b>Instruction counts, counted from the kernel loops.</b> One QK call (one 64-token page
&#xd7; one GQA group &#x2014; the query heads that share one KV head, four of them in the geometry
these kernels serve, per the kv_mul = 4 gate of the Supported geometry section) issues 44 tile
instructions: 4 <code>TILEZERO</code> + 20 <code>TILELOADD</code> + 16 <code>TDPBF16PS</code> +
4 <code>TILESTORED</code> (<code>amx_attn.cpp:241&#x2013;268</code>). One PV call issues 52:
8 + 20 + 16 + 8, because the 128-dim output is produced in two 64-dim halves
(<code>:201&#x2013;229</code>). With the loads overlapped, the 16 TDPs bound each call at roughly
16 &#xd7; 16.2 &#x2248; 260 core cycles (<span class="est">est.</span>, from the
<a href="#overhead">&#xa7;6.4</a> back-to-back measurements).</p>
<p class="takeaway">Operand roles per build flavor: the <b>mirror</b> QK kernel
(<code>qk_mirror_128x4</code>) uses zero-padded Q rows as A and the page&#x27;s VNNI
(pair-interleaved) K-mirror panels as B, so C is S = Q&#xb7;K&#x1d40; directly &#x2014; the tile
assignment the figure shows. The <b>canonical</b> QK kernel (<code>qk_canonical_128x4</code>)
swaps the roles &#x2014; the K page as stored is A (alternating through tmm4/tmm5), the
VNNI-packed Q group is B (tmm6) &#x2014; producing S&#x1d40;, which an AVX-512 transpose then
flips (<code>amx_attn.cpp:151&#x2013;180</code>); its tile-instruction sequence and counts are
identical. PV uses the figure&#x27;s assignment in both flavors. Q is packed once per
(token, KV head) and reused across all pages of the region
(<code>self_attention.hpp:1426&#x2013;1447</code>).</p>
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

# ---------------- canonical vs mirror: authored subsection (2026-09-01) ----------------
# jhan's request after the Q&A on the zoom diagram: the same page-iteration
# view, once per shipped QK formulation, plus the mirror's write-side cost.
# Facts verified in ~/workspace/tron-amx (branch jhan-amx-p0 @ 60d66d9c04):
# src/tron/kernels/amx_attn.cpp (qk_canonical_128x4 115-176, weights_times_v_128x4
# 178-230, qk_mirror_128x4 236-268), h/tron/models/self_attention.hpp:1568-1683
# (dispatch, PV epilogue), h/tron/kernels/amx_attn_iface.hpp Note [Mirror
# orientation], h/tron/models/kv_cache.hpp Note [K mirror parallel arena];
# timings: amx-design.md D1 (results/slot1/fused-sweep-v2.txt).

def lanes_qk_formulations():
    RED = 'fill="#fdf0ea" stroke="#d03b3b" stroke-width="2"'
    GRAY = 'fill="#f7f6f3" stroke="#c3c2b7"'
    GREEN = 'fill="#1baf7a"'
    WRITE = 'fill="#e4f2ed" stroke="#1b9e77" stroke-width="1.6"'
    PLAIN = 'fill="#f4f3ef" stroke="#52514e"'
    h = 30
    def box(x, y, w, style, text, fill_text):
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" {style}/>'
                f'<text x="{x+7}" y="{y+19}" fill="{fill_text}">{text}</text>')
    T_RED, T_GRAY, T_WHITE, T_INK = "#a12e2e", "#52514e", "#fff", "#0b0b0b"
    y1, y2, y3 = 52, 116, 180
    canon = [
        (150, 118, RED,  'S&#x1D40; = K&#xB7;Q&#x1D40;: 16 TDPs', T_RED),
        (272,  80, GRAY, 'store 4 tiles', T_GRAY),
        (356, 172, GRAY, 'AVX-512 transpose &#x2192; 4 score rows', T_GRAY),
        (532, 140, GREEN,'scale &#xB7; max &#xB7; exp &#xB7; corr', T_WHITE),
        (676, 106, RED,  'P&#xB7;V: 16 TDPs (4+4)', T_RED),
        (786, 102, GRAY, 'store 8 tiles &#x2192; o', T_GRAY),
        (892,  72, GREEN,'v* fma-add', T_WHITE),
    ]
    mirror = [
        (150, 118, RED,  'S = Q&#xB7;K&#x1D40;: 16 TDPs', T_RED),
        (272, 256, GRAY, 'store 4 tiles &#x2192; score rows (no transpose)', T_GRAY),
        (532, 140, GREEN,'scale &#xB7; max &#xB7; exp &#xB7; corr', T_WHITE),
        (676, 106, RED,  'P&#xB7;V: 16 TDPs (4+4)', T_RED),
        (786, 102, GRAY, 'store 8 tiles &#x2192; o', T_GRAY),
        (892,  72, GREEN,'v* fma-add', T_WHITE),
    ]
    write = [
        (150, 100, PLAIN, 'K norm + RoPE', T_INK),
        (254, 200, PLAIN, 'save_k &#x2192; canonical K plane (both)', T_INK),
        (458, 340, WRITE, 'scatter_k_mirror &#x2192; mirror plane: 256 B VNNI row, ~70 ns/row', T_INK),
    ]
    parts = []
    for (x, w, st, tx, ft) in canon:  parts.append(box(x, y1, w, st, tx, ft))
    for (x, w, st, tx, ft) in mirror: parts.append(box(x, y2, w, st, tx, ft))
    for (x, w, st, tx, ft) in write:  parts.append(box(x, y3, w, st, tx, ft))
    boxes = "".join(parts)
    return (
'<figure><div class="svgwrap"><svg viewBox="0 0 980 300" width="980" height="300" role="img"\n'
' aria-label="Three lanes: canonical-K page iteration with a transpose step; mirror page iteration without it; the mirror write-side scatter on the RX worker"\n'
' font-family="system-ui,sans-serif">\n'
'<text x="10" y="18" font-size="13" font-weight="600" fill="#0b0b0b">One (page, kv_head) iteration in each shipped QK formulation &#x2014; and where the mirror pays instead</text>\n'
'<g font-size="10" fill="#52514e">\n'
'  <rect x="10" y="28" width="12" height="10" fill="#fdf0ea" stroke="#d03b3b" stroke-width="1.5"/><text x="26" y="37">tile multiply (TDPBF16PS)</text>\n'
'  <rect x="160" y="28" width="12" height="10" fill="#f7f6f3" stroke="#c3c2b7"/><text x="176" y="37">AMX-specific data movement</text>\n'
'  <rect x="330" y="28" width="12" height="10" fill="#1baf7a"/><text x="346" y="37">unchanged AVX-512 code</text>\n'
'  <rect x="500" y="28" width="12" height="10" fill="#e4f2ed" stroke="#1b9e77"/><text x="516" y="37">mirror-only work</text>\n'
'</g>\n'
f'<text x="10" y="{y1+14}" font-size="11.5" font-weight="600" fill="#7570b3">canonical-K</text>\n'
f'<text x="10" y="{y1+27}" font-size="9.5" fill="#52514e">(default)</text>\n'
f'<text x="10" y="{y2+14}" font-size="11.5" font-weight="600" fill="#1b9e77">mirror</text>\n'
f'<text x="10" y="{y2+27}" font-size="9.5" fill="#52514e">(TRON_AMX_K_MIRROR)</text>\n'
f'<text x="10" y="{y3+8}" font-size="11.5" font-weight="600" fill="#1b9e77">mirror, write side</text>\n'
f'<text x="10" y="{y3+20}" font-size="9.5" fill="#52514e">RX worker, per stored K row</text>\n'
f'<text x="10" y="{y3+31}" font-size="9.5" fill="#52514e">(not per page)</text>\n'
f'<g font-size="10">{boxes}</g>\n'
f'<text x="806" y="{y3+19}" font-size="9.5" fill="#52514e">arena = kv_bytes / 2, plain RAM</text>\n'
'<text x="10" y="236" font-size="10.5" fill="#52514e">&#x2022; Lanes 1 and 2 differ only in the QK stage: the mirror has no score transpose. Everything from the softmax on is the same code and the same 16 P&#xB7;V TDPs.</text>\n'
'<text x="10" y="252" font-size="10.5" fill="#52514e">&#x2022; Measured whole path per page (L2, width 4): canonical 1250 ns, mirror 686 ns (results/slot1/fused-sweep-v2.txt); transpose and score round trip not isolated.</text>\n'
'<text x="10" y="268" font-size="10.5" fill="#52514e">&#x2022; Lane 3 runs once per stored K row when the mirror is built and its arena exists; canonical-K builds do only the first two boxes.</text>\n'
'<text x="10" y="290" font-size="10" fill="#898781">Code: amx_attn.cpp (qk_canonical_128x4, weights_times_v_128x4, qk_mirror_128x4), self_attention.hpp:1568&#x2013;1683; branch jhan-amx-p0 @ 60d66d9c04.</text>\n'
'</svg></div><figcaption>The page-iteration zoom from &quot;The problem being solved&quot;, drawn once per shipped QK\n'
'formulation; span widths are schematic, not measured. '
'Red = AMX tile multiplies; gray = AMX-specific data movement; green = the unchanged AVX-512\n'
'softmax and running-result code; light green = work that exists only in the mirror build.</figcaption></figure>')

KERNEL_LANES = """
<p class="prov">New for this document (jhan&#x27;s request, 2026-09-01); code-verified in the PR worktree
<code>~/workspace/tron-amx</code> @ 60d66d9c04: <code>src/tron/kernels/amx_attn.cpp</code>,
<code>self_attention.hpp:1568&#x2013;1683</code>, the notes [Mirror orientation] and
[K mirror parallel arena]; not a transplant (generator: <code>exec/gen_distilled.py</code>).</p>
<p>The PR ships two kernels for the score matmul (QK) and one kernel for the output matmul (PV).
Both QK kernels compute the same 64 &#xD7; 4 scores for one page and one GQA group; they differ in
which matrix is the tile multiply&#x27;s left operand (A, plain row-major) and which is the right
operand (B, which must be in the VNNI pair-interleaved layout). That choice decides whether the
result comes out sideways.</p>
""" + lanes_qk_formulations() + """
<ul>
  <li><b>Canonical-K (default).</b> A = the K page exactly as stored (64 token rows &#xD7; 128 dims,
      loaded as 4 row blocks of 16 tokens), B = the query group packed into VNNI pairs (a 4 KB buffer,
      packed once per query per pass and reused for every page). The 4 result tiles hold
      S&#x1D40; = K &#xB7; Q&#x1D40;, 64 token rows by 16 columns of which 4 are real query heads. The kernel
      stores them to a stack buffer and an AVX-512 shuffle network transposes them into the 4 score
      rows the softmax code expects <span class="cite">amx_attn.cpp:115&#x2013;176</span>. That transpose
      is the &quot;transpose 64&#xD7;4&quot; box of the earlier figure.</li>
  <li><b>Mirror (build option <code>TRON_AMX_K_MIRROR</code>).</b> A = the 4 query rows, copied
      unchanged into a 16-row buffer whose rows 4&#x2013;15 stay zero; B = the page&#x27;s K-mirror panels,
      a second copy of K already in the VNNI layout, read from the parallel arena the book allocates
      next to its DMA arena. The 4 result tiles hold S = Q &#xB7; K&#x1D40; (rows = query heads, columns
      = tokens) and are stored straight into row-major score rows; the 4 real rows are then copied
      contiguously into <code>s_pages</code> (1 KB), no transpose
      <span class="cite">amx_attn.cpp:236&#x2013;268; self_attention.hpp:1575&#x2013;1589</span>.
      The transpose&#x27;s cost moves to write time: when the RX worker saves a K row it also scatters
      that row into the mirror plane (lane 3; 70 ns per row, measured) <span class="cite">kv_cache.hpp
      Note [K mirror parallel arena]</span>. If the arena is absent (allocation failed, AMX
      unavailable, kill switch), the page falls through to the AVX-512 dotter, not to canonical-K.</li>
  <li><b>P&#xB7;V, identical in both.</b> A = P, the exponentiated scores converted to bf16 (16 rows
      &#xD7; 64 tokens, rows 0&#x2013;3 real); B = the V page as stored, whose pair-interleaved layout is
      already the B format. 128 output dims are 8 result tiles, more than the 8 tile registers can
      hold together with A and B, so the output is computed in two blocks of 4 tiles (dims 0&#x2013;63,
      then 64&#x2013;127), each block 2 token steps of 32: 2 &#xD7; 4 &#xD7; 2 = 16 TDPs
      <span class="cite">amx_attn.cpp:178&#x2013;230</span>. The design figure&#x27;s &quot;6+2&quot; was the
      Intel-manual blocking (6 result tiles + 1 A + 1 B, then 2); the shipped 4+4 keeps 7 registers
      live and double-buffers the V tile (decision D4, <code>amx-design.md</code>). The TDP count is
      the same either way.</li>
  <li><b>&quot;store &#x2192; v* fma-add&quot;, identical in both.</b> The 8 result tiles are stored to a
      16 &#xD7; 128 fp32 scratch buffer (TILESTORED always writes 16 rows). AVX-512 code then folds
      rows 0&#x2013;3 into the running attention state with the running-max softmax rule:
      v* = v* &#xB7; corr + o, s* = s* &#xB7; corr + &#x2211;p, m* = m_new, where
      corr = exp(m_old &#x2212; m_new) <span class="cite">self_attention.hpp:1661&#x2013;1683</span>.
      Accumulation across pages happens in memory, never in tiles: the result tiles are zeroed at the
      start of every page (D6). Nothing about V is transposed.</li>
</ul>
<table>
<tr><th></th><th>canonical-K (default)</th><th>mirror (opt-in)</th></tr>
<tr><td>QK operands</td><td>A = K page as stored; B = packed Q (VNNI pairs)</td><td>A = Q rows, zero-padded to 16; B = K-mirror panels (parallel arena)</td></tr>
<tr><td>QK result tiles</td><td>S&#x1D40;: 64 tokens &#xD7; 16 (4 real columns)</td><td>S: 16 (4 real rows) &#xD7; 64 tokens</td></tr>
<tr><td>After the QK TDPs</td><td>store to stack buffer; AVX-512 transpose into 4 score rows</td><td>store straight into score rows; copy 4 rows (1 KB)</td></tr>
<tr><td>Extra memory</td><td>none</td><td>arena of kv_bytes / 2 plain RAM per book (not DMA; page capacity unchanged)</td></tr>
<tr><td>Extra write work</td><td>none</td><td>scatter one 256 B VNNI row per stored K row, ~70 ns</td></tr>
<tr><td>P&#xB7;V and epilogue</td><td colspan="2">identical: 16 TDPs in two 4-tile blocks; tile store; v* = v* &#xB7; corr + o</td></tr>
<tr><td>Fallback</td><td>dense-page predicate fails &#x2192; AVX-512 dotter</td><td>same, plus arena absent &#x2192; AVX-512 dotter</td></tr>
<tr><td>Whole path per page, L2, width 4</td><td>1250 ns</td><td>686 ns</td></tr>
</table>
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
 ("<h3>Instruction set</h3>" + provenance("01-amx-rampup.html &#xa7;2"), f_isa + INSTR_SEQ, True),
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
 ("<h3>Canonical vs mirror: one page iteration in each QK formulation</h3>", KERNEL_LANES, True),
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
# Naming rule (CLAUDE.md, 2026-09-01): the prompt length is written "prompt N",
# never "ctx N". The source docs still say ctx; this pass converts prose and
# figure labels. Raw-data identifiers ("ctx=") have no space and are untouched.
out = re.sub(r"\bctx (\d)", r"prompt \1", out)
out = out.replace(
    "&quot;ctx&quot; = context: how many tokens of history each step reads.",
    "&quot;prompt N&quot; = the prompt length in tokens; each run then generates a fixed number of "
    "tokens, so the history a decode step reads is the prompt plus the tokens generated so far.")
dst = os.path.join(ROOT, "tron-amx-distilled.html")
open(dst, "w").write(out)
print(f"wrote {dst}: {len(out)} bytes; ids deduped: ok")
# basic sanity
assert "Minimal intrinsics" not in out
assert "Design decisions (with the consensus corrections baked in)" not in out
non_ascii = {c for c in out if ord(c) > 127}
print("non-ascii chars present:", sorted(non_ascii) if non_ascii else "none")
