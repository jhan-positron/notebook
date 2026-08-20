#!/usr/bin/env python3
# Generates rampup/pr-walkthrough.html: file-by-file map of PR #3879 tied to
# the concepts in pr-rampup.html. One diff-map SVG, collision-audited.
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
        boxes.append((x0, y - size * 0.8, x0 + w, y + size * 0.2, plain[:26]))
    n = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[0] < b[2] - 2 and b[0] < a[2] - 2 and a[1] < b[3] - 2 and b[1] < a[3] - 2:
                n += 1; print('OVERLAP:', a[4], 'vs', b[4])
        if boxes[i][2] > width - 4: print('OVERFLOW:', boxes[i][4])
    return n

el = []
def t(x, y, s, size=11.5, fill=INK, anchor='middle', bold=False):
    w = ' font-weight="600"' if bold else ''
    el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{w}>{s}</text>')
def r(x, y, w, h, fill, stroke, sw=1.4, rx=6):
    el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

layers = [
    ('Build &amp; flags', PUR, T_PUR, '&#xA7;4 (safety gates)',
     [('src/tron/CMakeLists.txt', 26)]),
    ('The kernels', TEAL, T_TEAL, '&#xA7;2&#x2013;3 (AMX, the two multiplies)',
     [('h/&#x2026;/amx_attn_iface.hpp', 63), ('src/&#x2026;/amx_attn.cpp', 192)]),
    ('Storage &amp; arena', MAG, T_MAG, '&#xA7;3 (the mirror fork)',
     [('h/&#x2026;/kv_cache.hpp', 192)]),
    ('Dispatch &amp; write-through', ORA, T_ORA, '&#xA7;3&#x2013;4 (eligibility, gates)',
     [('h/&#x2026;/self_attention.hpp', 161), ('h/&#x2026;/model.hpp', 14)]),
    ('Tests &amp; instruments', INK2, PALE, '&#xA7;5 (the evidence)',
     [('t/t_amx_mirror.cpp', 80), ('t/t_amx_logit_ab.cpp', 56), ('t/t_llama_unit.cpp', 27),
      ('t/CMakeLists.txt', 2), ('h/&#x2026;/p1_share_counters.hpp', 77), ('src/amx_fused_bench.cpp', 622)]),
]
t(14, 22, 'The 12 changed files, grouped by layer (box height follows lines changed; +1,506 lines total)',
  size=12.5, anchor='start', bold=True)
colw, gap, x = 178, 15, 14
max_bottom = 0
for name, stroke, fill, sect, files in layers:
    t(x + colw / 2, 48, name, size=11.5, bold=True, fill=stroke if stroke != INK2 else INK)
    y = 60
    for fname, loc in files:
        h = max(26, min(64, 20 + loc / 9))
        r(x, y, colw, h, fill, stroke, 1.5)
        t(x + colw / 2, y + h / 2 - 3, fname, size=9, fill=INK)
        t(x + colw / 2, y + h / 2 + 10, f'+{loc}', size=9, fill=INK2)
        y += h + 7
    t(x + colw / 2, y + 10, sect, size=9.5, fill=INK2)
    max_bottom = max(max_bottom, y + 16)
    x += colw + gap
H = int(max_bottom + 10)
assert audit(el, 980) == 0
diffmap = (f'<svg viewBox="0 0 980 {H}" width="980" height="{H}" role="img" '
           f'aria-label="The 12 changed files grouped into five layers: build flags, kernels, storage '
           f'and arena, dispatch and write-through, tests and instruments; box heights follow lines '
           f'changed; each column notes which ramp-up section explains it" '
           f'font-family="system-ui,sans-serif">\n' + '\n'.join(el) + '\n</svg>')

rows = [
 ('src/tron/CMakeLists.txt', '+26', 'The two options (both default OFF), the one -mamx translation unit, the PUBLIC defines, and the FATAL_ERROR dependency check.', '&#xA7;4', 'Flags default OFF; ONLY amx_attn.cpp gets -mamx flags; the retired diagnostic flag is gone.'),
 ('h/tron/kernels/amx_attn_iface.hpp', '+63', 'The intrinsics-free interface every other file talks to: availability check, Q packs, the three kernels, the tile-region bracket.', '&#xA7;2&#x2013;3', 'Contracts in comments: 16-row output buffers (tile stores always write 16 rows), UNSCALED scores, pair layouts.'),
 ('src/tron/kernels/amx_attn.cpp', '+192', 'The only file with AMX instructions: runtime detection (CPUID/XCR0/arch_prctl + kill switch), tile config, canonical QK + transposing store, PV, mirror QK, Q packs.', '&#xA7;2&#x2013;3', 'Detection order; the width-4 transpose emits only 4 of 16 stage-2 output paths; every _tile_stored target holds 16 rows.'),
 ('h/tron/models/kv_cache.hpp', '+192', 'The mirror arena: a book-owned ordinary-RAM allocation (half of kv_bytes) existing only when AMX is available; the scatter primitive; rebuilds at random-fill and at the single page-move funnel (copy_storage_slot). kv_block itself is UNCHANGED (still dense 2-plane).', '&#xA7;3', 'kv_block layout untouched; arena null-checks everywhere; the defrag rebuild reads the destination&#x27;s own canonical K (coherent by construction).'),
 ('h/tron/models/self_attention.hpp', '+161', 'Dispatch: the per-(token, head) lazy Q pack, the dense-page eligibility test, the QK fast path (canonical or mirror), the AMX epilogue for PV, and the chunk-size #error guard.', '&#xA7;3&#x2013;4', 'The eligibility conditions match &#xA7;4&#x27;s gate chain; did_amx=false always falls into the unchanged dotter loop; the epilogue math mirrors the existing code line for line.'),
 ('h/tron/models/model.hpp', '+14', 'save_k write-through: after the canonical K store, one call scatters the row into the mirror (gated on runtime availability; no-op when the arena is absent).', '&#xA7;3', 'Runs on the RX driver worker; measured 70 ns per token-row (&#x2248;20 &#xB5;s per prefill token across all layers/heads); the system A/B shows prefill net positive despite it.'),
 ('t/t_amx_mirror.cpp', '+80', 'Byte-equivalence of the mirror scatter against its layout contract, both head sizes, scrambled write order, single-token-rewrite isolation.', '&#xA7;5', '24,576 assertions; compiles to a skip-test when the flag is off.'),
 ('t/t_llama_unit.cpp', '+27', 'Mirror-coherence checks added to the existing append/defrag test; the hard-coded 2-plane size assertion now uses the shared constant.', '&#xA7;5', 'Skips visibly (WARN) when the arena is absent, e.g. non-AMX CI hosts.'),
 ('t/t_amx_logit_ab.cpp', '+56', 'Per-step logit dump tool for numerics A/Bs: long forced generation (so full pages actually engage AMX), tokens optionally from a golden file.', '&#xA7;5', 'This produced the 956-step TVD evidence; needs USE_HW_ATTN=0 to exercise the CPU path at decode positions.'),
 ('t/CMakeLists.txt', '+2', 'Registers the two new tests.', '&#xA7;5', 'Labels: fake (host-only) for t_amx_mirror; fpga for the logit tool.'),
 ('h/tron/kernels/p1_share_counters.hpp', '+77', 'Flag-gated (TRON_P1_COUNTERS) page-sharing counters used to size the batching opportunity; zero cost when off.', 'status report &#xA7;1 (P1)', 'Compiled out by default; no hot-path effect.'),
 ('src/amx_fused_bench.cpp', '+622', 'The standalone, self-validating whole-path benchmark that produced the kernel-level evidence and validated every kernel against a scalar reference before integration.', '&#xA7;5', 'Not wired into any build target; reference material. Its self-check caught a real transpose bug during development.'),
]
table = '\n'.join(
    f'<tr><td><code>{f}</code></td><td>{loc}</td><td>{what}</td><td>{sect}</td><td>{check}</td></tr>'
    for f, loc, what, sect, check in rows)

html = f'''<meta charset="utf-8">
<title>AMX PR Walkthrough</title>
<style>
body {{ background:#ffffff; color:#0b0b0b; font-family:system-ui,sans-serif;
       max-width:1080px; margin:24px auto; padding:0 20px; line-height:1.55; }}
h1 {{ font-size:23px; margin-bottom:2px; }}
h2 {{ font-size:17px; margin-top:30px; border-bottom:1px solid #e1e0d9; padding-bottom:6px; }}
p.sub {{ color:{INK2}; margin-top:0; }}
figure {{ margin:12px 0 4px 0; overflow-x:auto; }}
figcaption {{ font-size:12.5px; color:{INK2}; }}
table {{ border-collapse:collapse; font-size:13px; width:100%; }}
th,td {{ border:1px solid #d8d6d0; padding:5px 8px; text-align:left; vertical-align:top; }}
th {{ background:{PALE}; }}
code {{ background:{PALE}; padding:1px 4px; font-size:12px; }}
ol li {{ margin-bottom:6px; }}
.take {{ background:{PALE}; border-left:4px solid {ORA}; padding:8px 12px; font-size:14px; margin:12px 0; }}
</style>
<h1>Walkthrough of PR #3879, file by file</h1>
<p class="sub">Companion to <a href="pr-rampup.html">pr-rampup.html</a> (read that first &#x2014; the
&#xA7; references below point into it). The PR:
<a href="https://github.com/positron-ai/tron/pull/3879">positron-ai/tron#3879</a> (draft), branch
<code>jhan-amx-p0</code> on main <code>1407f48dd</code> &#x2014; snapshot as of 2026-08-19: 12 files,
+1,506 lines. If the PR has newer pushes, re-check the file list there.</p>

<h2>1. The shape of the diff</h2>
<figure>{diffmap}<figcaption>Everything is additive (6 new files, 6 edited; only 6 lines deleted
repo-wide). The big benchmark file is reference material, not built by default.</figcaption></figure>

<h2>2. Every file: what it does, and what to check</h2>
<table>
<tr><th style="width:20%">File</th><th>+/&#x2212;</th><th style="width:36%">What it does</th><th>Ramp-up</th><th style="width:32%">What a reviewer should check</th></tr>
{table}
</table>

<h2>3. A suggested reading order</h2>
<ol>
<li><code>amx_attn_iface.hpp</code> &#x2014; the contracts, no intrinsics. 5 minutes.</li>
<li><code>amx_attn.cpp</code> &#x2014; detection, then the three kernels against those contracts.</li>
<li><code>self_attention.hpp</code> &#x2014; where the kernels are called: the eligibility test and the
fall-through to unchanged code. This is the file that decides &quot;is production behavior safe&quot;.</li>
<li><code>kv_cache.hpp</code> + <code>model.hpp</code> &#x2014; the mirror arena and its two write
paths (save-time scatter, page-move rebuild).</li>
<li>The tests, then skim the benchmark if curious about the evidence chain.</li>
</ol>
<div class="take"><b>The review checklist</b> (the first four each caught or prevented a real bug
during development):
(1) every tile-store destination holds 16 rows even when only 4 matter;
(2) the AMX epilogue&#x27;s fp32 math matches the existing epilogue line for line;
(3) all mirror consumers handle a null arena (allocation failure falls back safely);
(4) every page-move path goes through <code>copy_storage_slot</code>, where the mirror is rebuilt from
the destination&#x27;s own K;
(5) AMX eligibility requires the exact supported shape AND a full, fully-visible 64-token page -
partial or masked pages must stay on AVX-512;
(6) every <code>did_amx == false</code> outcome reaches the old dotter path with no partially written
state;
(7) the QK kernels emit UNSCALED scores and scaling happens exactly once, in the unchanged epilogue;
(8) tile permission: <code>arch_prctl(ARCH_REQ_XCOMP_PERM)</code> is granted per PROCESS on Linux
(requested once before the worker pool spawns), but each thread loads its own tile configuration -
check the begin/end region bracket is balanced on all control-flow paths, including waits;
(9) mirror coherence must cover every path that changes canonical K - today that is save_k and the
page-move funnel; if a reviewer finds another K-mutation path, that is a finding.</div>

<h2>4. What is deliberately NOT in this PR</h2>
<p>No default flips (both options OFF), no storage-format changes to today&#x27;s KV cache, no
scheduler or worker changes, no batching of shared KV pages (a planned later phase), and no change to
the repository&#x27;s numerics acceptance policy &#x2014; the opt-in AMX path has exactly the measured
rounding differences described in the ramp-up&#x27;s &#xA7;5, nothing else. The consensus plan
(<a href="04-amx-action-plan.html">doc 04</a>) gates any default change on the remaining
qualification work (fallback-path tests, CI integration of the byte-equivalence tests, replication).</p>
'''
open('rampup/pr-walkthrough.html', 'w').write(html)
assert all(ord(c) < 128 for c in html)
print('pr-walkthrough.html written')
