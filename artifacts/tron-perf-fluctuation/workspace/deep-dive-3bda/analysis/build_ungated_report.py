#!/usr/bin/env python3
"""Build the ungated-campaign HTML: runtron command line, env vars, fastest/slowest."""

import csv
import glob
import re
import statistics as st

BASE = "/home/jhan/workspace/perf-fluctuation/deep-dive-3bda"
ROOT = open(f"{BASE}/CURRENT_CAMPAIGN_UNGATED").read().strip()
OUT = f"{BASE}/2026-08-12-08-3bda-ungated-run.html"

INK, INK2 = "#0b0b0b", "#52514e"
C_BLUE, C_RED, C_GREEN = "#2a78d6", "#e34948", "#008300"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


tps = {}
for r in csv.DictReader(open(f"{ROOT}/results.csv")):
    if r["status"] == "ok":
        tps[r["draw"]] = float(r["generate_tok_s"])
order = sorted(tps, key=lambda d: tps[d])
slowest, fastest = order[0], order[-1]
vals = [tps[d] for d in order]
mean = st.mean(vals)
cv = 100 * st.stdev(vals) / mean
gap = 100 * (max(vals) - min(vals)) / max(vals)

# command line: verify identical across draws modulo the per-draw tokens.out path
cmds = {}
for f in sorted(glob.glob(f"{ROOT}/results/draw_*/runtron-command.txt")):
    d = f.split("/")[-2]
    c = open(f).read().strip()
    cmds[d] = c
norm = {d: re.sub(r"--output-token-file \S+", "--output-token-file <draw>/tokens.out", c)
        for d, c in cmds.items()}
uniq = set(norm.values())
cmd_display = norm[fastest] if len(uniq) == 1 else None

envs = {}
for f in sorted(glob.glob(f"{ROOT}/results/draw_*/runtron-environment.txt")):
    d = f.split("/")[-2]
    envs[d] = open(f).read().strip()
env_uniq = set(re.sub(r"LD_LIBRARY_PATH=\S+", "LD_LIBRARY_PATH=<install>/lib", e)
               for e in envs.values())
env_display = envs[fastest]

# identity.env facts
ident = dict(line.split("=", 1) for line in open(f"{ROOT}/identity.env").read().splitlines() if "=" in line)

# token hashes
import subprocess
h = subprocess.run(["bash", "-c", f"sha256sum {ROOT}/results/draw_*/tokens.out {ROOT}/smoke/tokens.out | awk '{{print $1}}' | sort -u"],
                   capture_output=True, text=True).stdout.split()
tok_note = f"all {len(glob.glob(f'{ROOT}/results/draw_*/tokens.out')) + 1} runs bit-identical: {h[0][:8]}…{h[0][-4:]}" if len(h) == 1 else f"WARNING: {len(h)} distinct hashes"

# strip plot of the 20 draws
W, H, lx, rx = 980, 150, 70, 30
lo, hi = min(vals) - 1, max(vals) + 1
sc = (W - lx - rx) / (hi - lo)
sv = [f'<svg viewBox="0 0 {W} {H}" width="{W}" font-family="system-ui,sans-serif">']
for t in range(int(lo) + 1, int(hi) + 1, 2):
    x = lx + (t - lo) * sc
    sv.append(f'<line x1="{x:.0f}" y1="34" x2="{x:.0f}" y2="86" stroke="#eeede8"/>')
    sv.append(f'<text x="{x:.0f}" y="102" font-size="10" fill="{INK2}" text-anchor="middle">{t}</text>')
sv.append(f'<text x="{(lx+W-rx)/2:.0f}" y="120" font-size="11" fill="{INK2}" text-anchor="middle">decode throughput (tok/s), one dot per draw</text>')
for d in order:
    x = lx + (tps[d] - lo) * sc
    col = C_RED if d == slowest else C_GREEN if d == fastest else C_BLUE
    r = 7 if d in (slowest, fastest) else 5
    sv.append(f'<circle cx="{x:.1f}" cy="60" r="{r}" fill="{col}" fill-opacity="0.75" stroke="#fff" stroke-width="1.2"><title>{d}: {tps[d]:.2f} tok/s</title></circle>')
for d, lab, col in ((slowest, "slowest", C_RED), (fastest, "fastest", C_GREEN)):
    x = lx + (tps[d] - lo) * sc
    sv.append(f'<text x="{x:.0f}" y="30" font-size="11" font-weight="700" fill="{col}" text-anchor="middle">{lab}: {d} · {tps[d]:.2f}</text>')
sv.append("</svg>")
strip = "\n".join(sv)

rows_html = []
for d in sorted(tps, key=lambda x: -tps[x]):
    cls = ' class="fast"' if d == fastest else ' class="slow"' if d == slowest else ""
    trace = f"{ROOT}/results/{d}/trace.pftrace"
    import os
    sz = os.path.getsize(trace) / 1e6 if os.path.exists(trace) else 0
    rows_html.append(f"<tr{cls}><td>{d}</td><td>{tps[d]:.3f}</td><td>{sz:.0f} MB</td></tr>")
rows_html = "\n".join(rows_html)

env_rows = "\n".join(f"<tr><td><code>{esc(line.split('=',1)[0])}</code></td><td><code>{esc(line.split('=',1)[1]) if '=' in line else ''}</code></td></tr>"
                     for line in env_display.splitlines())

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3bda ungated perfetto run — command, environment, results</title>
<style>
 body {{ background:#fcfcfb; color:{INK}; font-family: system-ui, -apple-system, sans-serif;
        margin: 24px auto; max-width: 1080px; padding: 0 20px; line-height:1.45; }}
 h1 {{ font-size: 21px; margin-bottom:2px }} h2 {{ font-size:16.5px; margin-top:30px; border-bottom:1px solid #e4e3dd; padding-bottom:4px }}
 .sub {{ color:{INK2}; font-size:13px }}
 pre {{ background:#f4f3ee; border:1px solid #e4e3dd; border-radius:8px; padding:12px 14px;
       font-size:12.5px; white-space:pre-wrap; word-break:break-all }}
 table {{ border-collapse: collapse; font-size: 13px; margin: 10px 0 }}
 th, td {{ border: 1px solid #e4e3dd; padding: 4px 10px; text-align:right }}
 th {{ background:#f4f3ee; font-weight:600 }} td:first-child, th:first-child {{ text-align:left }}
 td code {{ font-size:12px }}
 tr.fast td {{ background:#eef7ee; font-weight:600 }}
 tr.slow td {{ background:#fdeeee; font-weight:600 }}
 .figwrap {{ overflow-x:auto; border:1px solid #eeede8; border-radius:8px; padding:10px; margin:10px 0; background:#fff }}
 .take {{ font-size:13.5px; background:#f4f8f4; border-left:4px solid {C_GREEN}; padding:8px 12px; margin:8px 0 }}
 code {{ background:#f4f3ee; padding:1px 4px; border-radius:4px; font-size:12px }}
 .cap {{ font-size:12px; color:{INK2}; margin-top:4px }}
</style></head><body>

<h1>Normal (ungated) perfetto capture — 20 draws on delphi-3bda</h1>
<div class="sub">perf-fluctuation deep dive &#183; campaign <code>{esc(ROOT.split('/')[-1])}</code> &#183;
binary = stock trunk 12804a812 + Mike&#8217;s <code>&#8220;data ready&#8221;</code> marker only (no trace gate) &#183;
full-run tracing from <code>~/workspace/common/perfetto.cfg-template</code></div>

<h2>Result: fastest and slowest draw</h2>
<div class="figwrap">{strip}</div>
<div class="take"><b>Fastest: {fastest} = {tps[fastest]:.3f} tok/s &#183; slowest: {slowest} = {tps[slowest]:.3f} tok/s.</b>
{len(tps)}/20 draws ok; campaign mean {mean:.1f} tok/s, CV {cv:.2f}%, worst-vs-best gap {gap:.2f}%. Token output {tok_note}.</div>
<p class="cap"><b>Context for the absolute numbers:</b> full-run tracing costs roughly a third of decode throughput
(bare campaigns on this machine run 170&#8211;190 tok/s; traced draws run 107&#8211;129). The launch lottery still rolls
under tracing. Mike&#8217;s <code>&#8220;data ready&#8221;</code> instant marker (activations ready at each hardware launch, TX
thread) is present at full rate: 1,084,816 instants in the smoke trace alone (~every launch of all 36 layers,
vs 20 per token window in the gated capture).</p>

<h2>runtron command line</h2>
<p class="cap">Captured from <code>/proc/&lt;pid&gt;/cmdline</code> of every draw by the harness;
{"identical across all draws except the per-draw tokens.out path" if cmd_display else "WARNING: command lines differ across draws"}.</p>
<pre>{esc(cmd_display or chr(10).join(sorted(uniq)))}</pre>
<table>
<thead><tr><th>flag</th><th>meaning</th></tr></thead><tbody>
<tr><td><code>-m ingested-qwen-3-4b-instruct-2507-tp4</code></td><td>model, tensor-parallel 4 (4 cards)</td></tr>
<tr><td><code>--instance 0,2</code></td><td>hardware instance placement (cards 10/13/38/3b)</td></tr>
<tr><td><code>-s 2954953865</code></td><td>fixed sampling seed (deterministic token sequence)</td></tr>
<tr><td><code>--dont-stop</code></td><td>ignore end-of-sequence token; always generate the full length</td></tr>
<tr><td><code>--threshold_p 0</code></td><td>disable top-p filtering</td></tr>
<tr><td><code>--pay-for-determinism</code></td><td>deterministic reduction order (same tokens every run)</td></tr>
<tr><td><code>--output-token-file &lt;draw&gt;/tokens.out</code></td><td>write generated tokens for hash comparison</td></tr>
<tr><td><code>--prompt-length 1024 &#183; -l 4096 &#183; --shared-system-prompt-length 256</code></td><td>1024-token prompt, 4096 generated tokens, 256-token shared system prompt</td></tr>
<tr><td><code>-u 1</code></td><td>one user (single stream decode)</td></tr>
</tbody></table>

<h2>Environment variables</h2>
<p class="cap">Captured from <code>/proc/&lt;pid&gt;/environ</code> per draw (the harness records this
tron-relevant subset); {"identical across all draws" if len(env_uniq) == 1 else "WARNING: environments differ across draws"}.
Launched via <code>run-benchmark.sh</code> with <code>SYSTEM_CONFIG</code> explicitly unset.</p>
<table><thead><tr><th>variable</th><th>value</th></tr></thead><tbody>
{env_rows}
</tbody></table>

<h2>All 20 draws</h2>
<table><thead><tr><th>draw</th><th>decode tok/s</th><th>trace size</th></tr></thead><tbody>
{rows_html}
</tbody></table>
<p class="cap">Green = fastest, red = slowest. Full-run traces (~1&#8201;GB) cover 25&#8201;s from model-load completion
(RING_BUFFER, write_into_file). Per-draw artifacts (runtron.log, metrics.json, perfetto.cfg, power.tsv,
runtron-command.txt, runtron-environment.txt, tokens.out, trace.pftrace) under
<code>{esc(ROOT)}/results/&lt;draw&gt;/</code>.</p>

<h2>Traceability</h2>
<p class="cap">
Binary: <code>{esc(ident.get('BIN',''))}</code> sha256 <code>{esc(ident.get('BIN_SHA256','')[:16])}&#8230;</code>
(stock trunk 12804a812 + the 6-line &#8220;data ready&#8221; TRACE_EVENT_INSTANT in tx_launch, nothing else)
&#183; perfetto categories {esc(ident.get('PERFETTO_CATEGORIES',''))};
capture {esc(ident.get('TRACE_DURATION_MS',''))}&#8201;ms, buffer {esc(ident.get('TRACE_BUFFER_KB',''))}&#8201;kB
{esc(ident.get('TRACE_FILL_POLICY',''))} &#183; harness copy <code>{esc(ROOT)}/harness.sh</code>
(tools-u1 v4 + --pay-for-determinism/--output-token-file + the early-SIGUSR1 fix) &#183; machine restored to the
serving trio after the campaign.<br>
Campaign history: attempt 1 (<code>ungated-tp4-20260812T164757Z</code>) froze in smoke &#8212; runtron&#8217;s SIGUSR1
timed tracer calls TrackEvent::Flush() 10&#8201;s after the signal, and flushing during an active full-rate capture
stalls the trace writers until every thread blocks on the shared memory buffer (only seen at -u 1, whose event rate
is ~7&#215; the -u 4 rate of all earlier full captures). Fix, harness-only: send SIGUSR1 during model load (gated on
runtron&#8217;s &#8220;pos_startup() completed&#8221; line &#8212; the handler installs at the end of pos_startup) so the
flush completes before the capture session exists. Attempt 2 (<code>&#8230;T171457Z-r2</code>, stock binary) validated
the fix (smoke + draw_01 ok) and was stopped deliberately because it lacked the &#8220;data ready&#8221; marker; this
campaign (r3) is the marker build. Both aborted roots remain on /scratch for reference.
</p>
</body></html>
"""
open(OUT, "w").write(html)
print(f"wrote {OUT}: {len(html)} bytes; fastest={fastest} {tps[fastest]:.3f}, slowest={slowest} {tps[slowest]:.3f}, cv={cv:.2f}%, gap={gap:.2f}%")
