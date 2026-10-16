import json, html
R='/home/jhan/workspace/intel-AMX/exec/results/vnnik-trace-20260914/'
d=json.load(open(R+'base-tp2.perfetto-trace.lanes.json'))

def classify(s):
    n=s['name']
    if n in ('Save K','Save V','Free scratchpads'): return 'main'
    if n.startswith('kernel_'): return 'helper'
    return 'attention'

def figure(w, t0, t1, title, notes, red_until):
    spans=[s for s in w['spans'] if s['start_us']<t1 and s['start_us']+s['dur_us']>t0]
    # threads
    threads={}
    for s in spans:
        c=classify(s)
        threads.setdefault(s['utid'],{'cls':c,'spans':[]})['spans'].append(s)
    order=['main','helper','attention']
    utids=sorted(threads, key=lambda u:(order.index(threads[u]['cls']),u))
    W=1100; left=120; right=30; lane=11; top=60
    scale=(W-left-right)/(t1-t0)
    H=top+lane*len(utids)+90
    out=[f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font-family:system-ui,sans-serif;font-size:11px">']
    out.append(f'<text x="{left}" y="18" font-size="14" font-weight="600">{html.escape(title)}</text>')
    # axis
    import math
    step=50 if (t1-t0)<1000 else 1000
    y_axis=top+lane*len(utids)+8
    for t in range(0, int(t1)+1, step):
        x=left+(t-t0)*scale
        out.append(f'<line x1="{x:.1f}" y1="{top-4}" x2="{x:.1f}" y2="{y_axis}" stroke="#ddd"/>')
        out.append(f'<text x="{x:.1f}" y="{y_axis+14}" text-anchor="middle" fill="#555">{t if step<1000 else t//1000}</text>')
    out.append(f'<text x="{W-right}" y="{y_axis+30}" text-anchor="end" fill="#555">wall-clock time, {"us" if step<1000 else "ms"} from this layer\'s Save K start (durations to scale)</text>')
    colors={'main':'#c0392b','helper':'#2c7fb8','attention':'#41ab5d'}
    labels={'main':'main thread','helper':'main helper','attention':'attention worker'}
    # red critical band
    if red_until:
        x0=left; x1=left+(red_until-t0)*scale
        out.append(f'<rect x="{x0:.1f}" y="{top-6}" width="{x1-x0:.1f}" height="{lane*len(utids)+10}" fill="#fdecea" stroke="#c0392b" stroke-dasharray="4 3"/>')
    prev=None
    for i,u in enumerate(utids):
        c=threads[u]['cls']; y=top+i*lane
        if c!=prev:
            out.append(f'<text x="{left-6}" y="{y+9}" text-anchor="end" fill="{colors[c]}" font-weight="600">{labels[c]}{"s" if c!="main" else ""} ({sum(1 for v in threads.values() if v["cls"]==c)})</text>')
            prev=c
        # idle = dashed baseline
        out.append(f'<line x1="{left}" y1="{y+lane/2:.1f}" x2="{W-right}" y2="{y+lane/2:.1f}" stroke="#bbb" stroke-dasharray="2 3"/>')
        for s in threads[u]['spans']:
            a=max(t0,s['start_us']); b=min(t1,s['start_us']+s['dur_us'])
            x=left+(a-t0)*scale; wd=max(0.8,(b-a)*scale)
            nm=s['name']
            fill=colors[c]
            if c=='attention': fill={'Attention Ready':'#41ab5d','Attention Pending':'#006d2c','attention: join':'#a1d99b'}.get(nm,'#41ab5d')
            out.append(f'<rect x="{x:.1f}" y="{y+1}" width="{wd:.1f}" height="{lane-2}" fill="{fill}"><title>{html.escape(nm)} {s["dur_us"]:.1f} us</title></rect>')
    # notes
    yy=y_axis+48
    for n in notes:
        out.append(f'<text x="{left}" y="{yy}" fill="#222">{html.escape(n)}</text>'); yy+=15
    out.append('</svg>')
    return '\n'.join(out)

pre=d['prefill']; dec=d['decode']
f1=figure(pre,0,10545,'One prefill layer, tp2 (qwen3-4b, 8 users, prompt 1024, row-major K build 544ca05c7a, trace 2026-09-14)',
  ['Red band: Save K (272 us) then Save V (293 us) on the main thread. All 7 helpers idle (dashed = no work). The first Pending attention section starts 0.3 us after Save V ends.',
   'Then the helpers idle for the whole attention phase (to 3.6 ms) and the attention workers idle for the whole kernel phase (3.6 ms to the end). Empty stretches = CPU waits for the FPGA linear layers.'],
  574.7)
f2=figure(dec,0,345.5,'One decode layer, tp2 (same run)',
  ['Save K (4 us) and Save V (4 us) overlap the workers\' Ready sections: nothing waits for them. Helpers idle for 227 us (66 %) of the 346 us layer while attention runs on the 20 workers (all 20 busy for 125 us, then a tail).',
   'The four helper kernels (2 to 10 us each) run after attention. The two thread groups never work at the same time.'],
  None)

page=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Helper-thread sharing on main</title>
<style>:root{{--bg:#fff;--fg:#1a1a1a}}body{{background:#fff;color:#1a1a1a;font-family:system-ui,sans-serif;max-width:1140px;margin:0 auto;padding:16px;line-height:1.45}}
table{{border-collapse:collapse;margin:8px 0 16px}}td,th{{border:1px solid #ccc;padding:4px 8px;text-align:left;font-size:14px}}th{{background:#f3f3f3}}h2{{font-size:18px;margin-top:28px}}code{{background:#f3f3f3;padding:0 3px}}.sv{{background:#f6f8fa;border-left:4px solid #2c7fb8;padding:8px 12px}}</style></head><body>
<h1 style="font-size:22px">Can PR 3's helper sharing and PR 4's tail block boost tron without the VNNI layout?</h1>
<div class="sv"><b>Short version.</b> PR 3's sharing of the K store with the idle helpers is layout-independent and could be applied to main's K and V stores in an independent PR. It would shorten prefill only: est. 1.4 to 2.6 % of time to first token at tp2 and about 6 % at tp4 (qwen3-4b, 8 users, prompt 1,024 tokens), and nothing in decode. PR 4 has no technique that helps without the layout, and the stack's decode gains come from the layout-bound scoring paths of PR 1 and PR 2.</div>
<h2>Words used here</h2>
<table><tr><th>Term</th><th>Meaning</th></tr>
<tr><td>main thread, main helpers, attention workers</td><td>A generated plugin runs the schedule on one main thread. The main helpers run the per-token kernels (rmsnorm, rope, swish). The attention workers run the CPU attention sections. The split (1 + 7 + 20 at tp2) is decided once per pass by <code>recommend_n_main_helpers</code>.</td></tr>
<tr><td>Save K, Save V</td><td><code>save_k_impl</code> / <code>save_v_impl</code> in model.hpp: the main thread copies every token's K and V rows of the pass into the KV cache, once per layer.</td></tr>
<tr><td>Ready, Pending</td><td>Attention sections over pages complete before this pass (Ready) and over pages written in this pass (Pending). A Pending section cannot start before Save V ends.</td></tr>
<tr><td>tp2, tp4</td><td>The model split over 2 or 4 FPGA cards. TTFT = time to first token (the batched prefill). TPS = decode tokens per second per user.</td></tr>
<tr><td>VNNI layout</td><td>The K storage of PR 1 (#4956): one 64-byte line holds one dimension pair of 16 tokens. Main's K is row-major (one 256-byte row per token). Main's V is already VNNI-packed with even and odd tokens merged in one line.</td></tr>
<tr><td>est.</td><td>An estimate, not a measurement.</td></tr></table>
<h2>What the trace shows: who works when</h2>
{f1}
{f2}
<p>Source: <code>exec/results/vnnik-trace-20260914/base-tp2.perfetto-trace.lanes.json</code>, pass 2 layer 10 (prefill) and one decode layer. Only spans of depth 0 and 1 are in the file. The main thread's FPGA fill, launch and channel waits are not traced, so empty stretches mean "no traced CPU work".</p>
<h2>Main-thread serial work and the room it leaves</h2>
<table><tr><th>Cell</th><th>Save K + Save V per layer</th><th>Share of the pass</th><th>Helpers busy during it</th><th>Gap from Save V end to first Pending start</th></tr>
<tr><td>prefill tp2</td><td>274 + 295 us</td><td>5.2 %</td><td>0.00</td><td>286 us (Ready work still running: part of the save is hidden)</td></tr>
<tr><td>prefill tp4</td><td>281 + 295 us</td><td>7.6 %</td><td>0.00</td><td>6.5 us (the save gates the layer)</td></tr>
<tr><td>decode tp2</td><td>4.6 + 5.6 us</td><td>2.7 %</td><td>0.00</td><td>110 us (hidden behind Ready sections)</td></tr>
<tr><td>decode tp4</td><td>5.8 + 7.1 us</td><td>4.3 %</td><td>0.00</td><td>34 us (hidden)</td></tr></table>
<p>Means over 8 passes, <code>analysis.md</code> of the same record. The striping-only arm of 2026-09-15 (Save K shared, VNNI store, record <code>vnnik2-20260915</code>) turned 63 % of its removed store time into TTFT at tp2 and 107 % at tp4. Applied to main's 5.2 % and 7.6 %, with the striping ratio 858 to 175 us (tp2) and 863 to 110 us (tp4): est. 1.4 to 2.6 % at tp2 and about 6 % at tp4, K and V together. Base TTFT on 2026-10-12: 3.18 s at tp2, 2.21 s at tp4, so est. 45 to 80 ms and about 130 ms. The V half has no measurement.</p>
<h2>PR 3 by line class (712 added lines)</h2>
<table><tr><th>Class</th><th>Lines</th><th>Content</th></tr>
<tr><td>Generic sharing</td><td>352 (49 %)</td><td>window struct, work-unit cut, claim loop, join and watchdog, worker index plumbing, code-generator helper call, generator test, three-thread test</td></tr>
<tr><td>Layout-specific</td><td>277 (39 %)</td><td>16x16 register transpose, <code>store_block</code>, <code>page::set_k_block</code>, present masks, bit-identity test</td></tr>
<tr><td>Mixed / comments</td><td>83 (12 %)</td><td>Note text that describes both</td></tr></table>
<h2>PR 4</h2>
<p>Every mechanism (row bits, forward-end conversion, hardware-attention policy, dotter over tail rows, page-reuse and copy bookkeeping) either restores a property main already has or manages the state a two-layout page needs. Its FPGA-attention gains against its parent (+2.5 % at tp2, +12.1 % at tp4) return the stack to main (+0.6 % and -0.3 % against main, inside the band). Ported alone to main, the only effect would be cost (two extra atomic loads per new token, a conversion with no consumer).</p>
</body></html>'''
open('/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/helper-sharing-on-main-20261016.html','w').write(page)
print('ok', len(page))
