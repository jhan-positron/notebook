#!/usr/bin/env python3
"""Transfer the pr1b-20261010 results into exec/pr1-20261010/pr-body-v2.md (the numbers of the a711aeee83 run are replaced).
Usage: python3 fill-body.py   (asserts that every expected old string is present exactly as often as expected)"""
import pathlib, re, statistics, sys
E = pathlib.Path('/home/jhan/workspace/intel-AMX/exec')
RES = E / 'results' / 'pr1b-20261010'; CELLS = E / 'results' / 'pr1b-E-cpu'
body_p = E / 'pr1-20261010' / 'pr-body-v2.md'; body = body_p.read_text()

# ---- cells: parse summary.md (per-arm rows and pair rows) ----
summ = (CELLS / 'summary.md').read_text().splitlines()
arms = {}   # (prompt, arm) -> dict(tps, tps_sd, ttft, ttft_sd, n)
pairs = {}  # (prompt, a, b) -> dict(tps_pct, ttft_pct, ttft_ms, tps_mean, tps_sd, tps_n, tps_t, ttft_mean, ttft_sd, ttft_n, ttft_t)
for line in summ:
    c = [x.strip() for x in line.strip().strip('|').split('|')]
    if len(c) == 14 and c[0].startswith('q3-4b-tp2-8u-p') and c[1] == 'cpu':
        prompt = int(c[0].split('-p')[1]); arms[(prompt, c[5])] = dict(n=int(c[6]), tps=float(c[7]), tps_sd=float(c[8]), ttft=float(c[9]), ttft_sd=float(c[10]))
    if len(c) == 8 and c[0].startswith('q3-4b-tp2-8u-p') and c[1] == 'cpu' and ' vs ' in c[2]:
        prompt = int(c[0].split('-p')[1]); a, b = c[2].split(' vs ')
        m = re.match(r'([+-][\d.]+) \(([\d.]+), (\d+), ([+-][\d.]+)\)', c[6]); m2 = re.match(r'([+-]?\d+) \((\d+), (\d+), ([+-][\d.]+)\)', c[7])
        pairs[(prompt, a, b)] = dict(tps_pct=float(c[3]), ttft_pct=float(c[4]), ttft_ms=int(c[5]), tps_mean=float(m.group(1)), tps_sd=float(m.group(2)), tps_n=int(m.group(3)), tps_t=float(m.group(4)), ttft_mean=int(m2.group(1)), ttft_sd=int(m2.group(2)), ttft_n=int(m2.group(3)), ttft_t=float(m2.group(4)))
assert len(arms) == 8 and len(pairs) == 8, (len(arms), len(pairs))
def band(prompt, a, b):
    bt = max(2 * max(arms[(prompt, a)]['tps_sd'], arms[(prompt, b)]['tps_sd']), 0.4)
    bf = max(2 * max(arms[(prompt, a)]['ttft_sd'], arms[(prompt, b)]['ttft_sd']), 0.15)
    return bt, bf
def inside(v, band): return 'inside' if abs(v) <= band else 'beyond'
def ttft_str(ms, pct, t):
    if abs(ms) >= 1000: return f"{ms/1000:+.1f} s ({pct:+.1f} %, t {t:+.1f})"
    return f"{ms:+d} ms ({pct:+.1f} %, t {t:+.1f})"
# per-arm table rows
rows = []
for prompt in (1024, 8192):
    for arm in ('base', 'new', 'newoff', 'baseoff'):
        a = arms[(prompt, arm)]
        rows.append(f"| {prompt} | {arm} | {a['tps']:.2f} ({a['tps_sd']:.2f}) | {a['ttft']:.3f} ({a['ttft_sd']:.3f}) |")
old_rows = body[body.index('| 1024 | base |'):body.index('| 8192 | baseoff |')]
old_rows = old_rows + body[body.index('| 8192 | baseoff |'):].split('\n', 1)[0]
body = body.replace(old_rows, '\n'.join(rows))
# pair table rows
prows = []
for prompt in (1024, 8192):
    for a, b in (('new', 'base'), ('newoff', 'baseoff'), ('newoff', 'new'), ('baseoff', 'base')):
        p = pairs[(prompt, a, b)]; bt, bf = band(prompt, a, b)
        prows.append(f"| {prompt} | {a} vs {b} | {p['tps_pct']:+.1f} % ({p['tps_mean']:+.2f} TPS, t {p['tps_t']:+.1f}), {inside(p['tps_mean'], bt)} | {ttft_str(p['ttft_ms'], p['ttft_pct'], p['ttft_t'])}, {inside(p['ttft_ms']/1000, bf)} | {bt:.2f} TPS / {bf:.2f} s |")
start = body.index('| 1024 | new vs base |'); end = body.index('\n', body.index('| 8192 | baseoff vs base |'))
body = body[:start] + '\n'.join(prows) + body[end:]
# prose numbers: targeted replacements, old (a711 run) -> new
P = lambda pr, a, b, k: pairs[(pr, a, b)][k]
repl = [
 ("-6.2 % at prompt length 1,024 tokens and -11.0 % at 8,192 tokens", f"{P(1024,'new','base','tps_pct'):+.1f} % at prompt length 1,024 tokens and {P(8192,'new','base','tps_pct'):+.1f} % at 8,192 tokens"),
 ("TTFT increases by approximately 26 % and 123 %, respectively.", f"TTFT increases by approximately {round(P(1024,'new','base','ttft_pct'))} % and {round(P(8192,'new','base','ttft_pct'))} %, respectively."),
 ("-15.3 % TPS and approximately +133 % TTFT against `base`", f"{P(1024,'baseoff','base','tps_pct'):+.1f} % and {P(8192,'baseoff','base','tps_pct'):+.1f} % TPS and approximately {round(P(1024,'baseoff','base','ttft_pct')):+d} % and {round(P(8192,'baseoff','base','ttft_pct')):+d} % TTFT against `base`"),
 ("Their sum is -5.49 TPS at prompt length 1,024 tokens and -1.86 TPS at 8,192 tokens. The measured `new` minus `base` is -5.06 TPS and -1.90 TPS. The residuals, +0.43 TPS and -0.04 TPS, equal `new` minus `newoff`, which is inside the band in both cells.",
  f"Their sum is {P(1024,'baseoff','base','tps_mean')+P(1024,'newoff','baseoff','tps_mean'):+.2f} TPS at prompt length 1,024 tokens and {P(8192,'baseoff','base','tps_mean')+P(8192,'newoff','baseoff','tps_mean'):+.2f} TPS at 8,192 tokens. The measured `new` minus `base` is {P(1024,'new','base','tps_mean'):+.2f} TPS and {P(8192,'new','base','tps_mean'):+.2f} TPS. The residuals, {P(1024,'new','base','tps_mean')-P(1024,'baseoff','base','tps_mean')-P(1024,'newoff','baseoff','tps_mean'):+.2f} TPS and {P(8192,'new','base','tps_mean')-P(8192,'baseoff','base','tps_mean')-P(8192,'newoff','baseoff','tps_mean'):+.2f} TPS, equal `new` minus `newoff`, which is {inside(P(1024,'newoff','new','tps_mean'), band(1024,'newoff','new')[0])} the band at 1,024 tokens and {inside(P(8192,'newoff','new','tps_mean'), band(8192,'newoff','new')[0])} it at 8,192 tokens."),
 ("- Decode TPS increases by 4.4 % and 5.3 %. Both changes exceed the band.", f"- Decode TPS increases by {P(1024,'newoff','baseoff','tps_pct'):.1f} % and {P(8192,'newoff','baseoff','tps_pct'):.1f} %. Both changes exceed the band." if inside(P(1024,'newoff','baseoff','tps_mean'), band(1024,'newoff','baseoff')[0]) == 'beyond' and inside(P(8192,'newoff','baseoff','tps_mean'), band(8192,'newoff','baseoff')[0]) == 'beyond' else "- Decode TPS changes by {:+.1f} % and {:+.1f} % (see the band column of the table).".format(P(1024,'newoff','baseoff','tps_pct'), P(8192,'newoff','baseoff','tps_pct'))),
 ("- TTFT decreases by 1.1 % and 5.1 %. The first is inside the band. The second exceeds it.", f"- TTFT changes by {P(1024,'newoff','baseoff','ttft_pct'):+.1f} % and {P(8192,'newoff','baseoff','ttft_pct'):+.1f} %. The first is {inside(P(1024,'newoff','baseoff','ttft_ms')/1000, band(1024,'newoff','baseoff')[1])} the band. The second is {inside(P(8192,'newoff','baseoff','ttft_ms')/1000, band(8192,'newoff','baseoff')[1])} it."),
 ("TPS changes remain inside the band: -0.6 % at prompt length 1,024 tokens and +0.3 % at 8,192 tokens.", f"TPS changes are {inside(P(1024,'newoff','new','tps_mean'), band(1024,'newoff','new')[0])} the band at 1,024 tokens ({P(1024,'newoff','new','tps_pct'):+.1f} %) and {inside(P(8192,'newoff','new','tps_mean'), band(8192,'newoff','new')[0])} it at 8,192 tokens ({P(8192,'newoff','new','tps_pct'):+.1f} %)."),
 ("- Prompt length 1,024 tokens: 61 ms, or 1.5 %. This is inside the 0.15 s band.", f"- Prompt length 1,024 tokens: {abs(P(1024,'newoff','new','ttft_ms'))} ms, or {abs(P(1024,'newoff','new','ttft_pct')):.1f} %. This is {inside(P(1024,'newoff','new','ttft_ms')/1000, band(1024,'newoff','new')[1])} the {band(1024,'newoff','new')[1]:.2f} s band."),
 ("- Prompt length 8,192 tokens: 669 ms, or 0.6 %. This exceeds the 0.38 s band. Paired t is -5.8.", f"- Prompt length 8,192 tokens: {abs(P(8192,'newoff','new','ttft_ms'))} ms, or {abs(P(8192,'newoff','new','ttft_pct')):.1f} %. This is {inside(P(8192,'newoff','new','ttft_ms')/1000, band(8192,'newoff','new')[1])} the {band(8192,'newoff','new')[1]:.2f} s band. Paired t is {P(8192,'newoff','new','ttft_t'):+.1f}."),
 ("- Against `main` at `72308ec90c`, decode TPS falls 6.2 % at prompt length 1,024 tokens and 11.0 % at 8,192 tokens. TTFT increases by approximately 26 % and 123 %.", f"- Against `main` at `72308ec90c`, decode TPS falls {abs(P(1024,'new','base','tps_pct')):.1f} % at prompt length 1,024 tokens and {abs(P(8192,'new','base','tps_pct')):.1f} % at 8,192 tokens. TTFT increases by approximately {round(P(1024,'new','base','ttft_pct'))} % and {round(P(8192,'new','base','ttft_pct'))} %."),
]
for old, new in repl:
    assert body.count(old) == 1, ('prose', old[:60], body.count(old)); body = body.replace(old, new)
# the kill-switch subsection's direction words ("TTFT decreases with the switch:") stay only if both deltas are negative
assert P(1024,'newoff','new','ttft_ms') < 0 and P(8192,'newoff','new','ttft_ms') < 0, "kill-switch TTFT direction changed; edit the subsection by hand"
# ---- smokes ----
def first_diff(cell, a, b):
    t = (RES / 'smoke' / cell / 'smoke.txt').read_text()
    m = re.findall(rf"^{a} vs {b}: (identical for (\d+) tokens|first difference at generated token (\d+) of (\d+))", t, re.M)
    assert m, (cell, a, b); m = m[-1]
    return f"identical, {m[1]} of {m[1]} tokens" if m[1] else f"first difference at generated token {m[2]}"
def verdict(cell): return (RES / 'smoke' / cell / 'smoke.done').read_text().strip()
assert all(verdict(c) == 'ok' for c in ('cpu-p1024', 'cpu-p8192', 'fpga-p1024')), [verdict(c) for c in ('cpu-p1024', 'cpu-p8192', 'fpga-p1024')]
srow = {('cpu-p1024', 'CPU attention, prompt length 1024 tokens'), ('cpu-p8192', 'CPU attention, prompt length 8192 tokens'), ('fpga-p1024', 'FPGA attention, prompt length 1024 tokens')}
for cell, label in srow:
    start = body.index(f"| {label} |"); end = body.index('\n', start)
    body = body[:start] + f"| {label} | {first_diff(cell,'new','new2')} | {first_diff(cell,'newoff','new')} | {first_diff(cell,'new','base')} |" + body[end:]
d1 = first_diff('cpu-p1024', 'new', 'base'); d3 = first_diff('fpga-p1024', 'new', 'base'); d2 = first_diff('cpu-p8192', 'new', 'base')
old = "- At prompt length 1,024 tokens, both CPU and FPGA attention first differ from `main` at generated token 83 of 256.\n- At prompt length 8,192 tokens with CPU attention, all 256 generated tokens match. [Verification above]"
assert body.count(old) == 1
tok1 = re.search(r'token (\d+)', d1); tok3 = re.search(r'token (\d+)', d3)
if tok1 and tok3 and tok1.group(1) == tok3.group(1) and d2.startswith('identical'):
    new = f"- At prompt length 1,024 tokens, both CPU and FPGA attention first differ from `main` at generated token {tok1.group(1)} of 256.\n- At prompt length 8,192 tokens with CPU attention, all 256 generated tokens match. [Verification above]"
else:
    new = f"- CPU attention, prompt length 1,024 tokens: {d1}. FPGA attention, prompt length 1,024 tokens: {d3}. CPU attention, prompt length 8,192 tokens: {d2}. [Verification above]"
body = body.replace(old, new)
# ---- host suite ----
h = (RES / 'host-suite-pr1.txt').read_text()
m = re.search(r'(\d+) passed, (\d+) skipped, (\d+) failed\s+•\s+makespan ([\d.]+)s', h); assert m, 'host summary line'
passed, skipped, failed, mk = m.group(1), m.group(2), m.group(3), float(m.group(4))
assert (passed, skipped, failed) == ('93', '1', '1') and 'failed: t_proxy_llama31' in h, (passed, skipped, failed)
old = "- Total elapsed suite time was 110 s."; assert body.count(old) == 1; body = body.replace(old, f"- Total elapsed suite time was {mk:.0f} s.")
body_p.write_text(body)
print("filled; arms:", {k: v['tps'] for k, v in arms.items()})
