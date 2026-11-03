#!/usr/bin/env python3
"""Patch PR #5015's LIVE body: fill the Token identity section, add 'Other models with and without this PR' after
'Performance at the CI configuration', and rewrite the Open items. Reads results.json of the campaign for the perf rows.
Usage: patch-pr-body.py <live-body.md> <results.json> <out.md>"""
import json, re, sys
live, resj, out = sys.argv[1:4]
s = open(live).read(); d = json.load(open(resj))
draft = open(sys.argv[0].rsplit("/", 1)[0] + "/pr-body-sections-draft.md").read()
LABEL = {"l8b": "llama-3.1-8b", "q4b": "qwen3-4b", "gptoss": "gpt-oss-120b", "glm": "Glimmer"}
def lab(cell):
    m = re.match(r"^(l8b|q4b|gptoss|glm)-tp(\d)-8u-p(\d+)-(cpu|fpga)$", cell)
    return f"{LABEL[m[1]]} tp{m[2]}, prompt {m[3]}, {'CPU' if m[4] == 'cpu' else 'FPGA'} attention"
f = lambda x, nd=2: "-" if x is None else f"{x:.{nd}f}"
rows = []
l8b8192 = None
for r in d["perf"]:
    b, h, p = r["arms"]["base"], r["arms"]["head"], r["pair"]; st, sp = p["tps"], p["prefill"]
    verdict = {"holds": "holds", "gain": "gain"}.get(p["verdict"], p["verdict"])
    rows.append(f"| {lab(r['cell'])} | {f(b['tps_mean'])} (sd {f(b['tps_sd'])}) | {f(h['tps_mean'])} (sd {f(h['tps_sd'])}) | {f(st['mean'])} = {f(p['tps_pct'], 1)} % (band {f(p['band_tps'])}, t {f(st['t'], 1)}, n {st['n']}) | {f(b['prefill_mean'], 2)} | {f(h['prefill_mean'], 2)} ({f(p['prefill_pct'], 1)} %) | {f(b['amx_pct_mean'], 1)} % / {f(h['amx_pct_mean'], 1)} % | {verdict} |")
    if r["cell"] == "l8b-tp2-8u-p8192-cpu":
        l8b8192 = (st, sp, p)
st, sp, p = l8b8192
if p["verdict"].startswith("DEGRADATION"):
    sent = (f"One cell is beyond its band: llama-3.1-8b at prompt 8192 decodes {f(st['mean'])} tokens/s per user slower ({f(p['tps_pct'], 1)} %, t {f(st['t'], 1)} over {st['n']} paired repetitions, band {f(p['band_tps'])}) "
            f"while its prefill is {f(-sp['mean'], 2)} s shorter ({f(p['prefill_pct'], 1)} %). The decode loss is smaller than the 0.5 % floor earlier rounds used as the noise floor; its cause is not measured (the kv_mul-4 kernels are instruction-identical, see the object compare; the only code difference on this path is the thread-local addressing of the PV kernel's scratch). It is listed in [Open items].")
else:
    sent = (f"llama-3.1-8b at prompt 8192 decodes {f(-st['mean'])} tokens/s per user slower on average ({f(p['tps_pct'], 1)} %, t {f(st['t'], 1)} over {st['n']} paired repetitions; the first 4 repetitions flagged it, 4 more were added), inside its band of {f(p['band_tps'])}, with a {f(-sp['mean'], 2)} s shorter prefill ({f(p['prefill_pct'], 1)} %). "
            f"A loss of that size, if real, is below the 0.5 % noise floor earlier rounds used, and its cause is not measured (the kv_mul-4 kernels are instruction-identical; the PV kernel's thread-local scratch is addressed differently). It is listed in [Open items].")
sec = draft.replace("PERF_ROWS", "\n".join(rows)).replace("L8B8192_SENTENCE", sent)
ident, other = sec.split("### Other models with and without this PR")
ident = ident.strip() + "\n"; other = "### Other models with and without this PR" + other
# 1. token identity section: replace from '### Token identity' up to '### Performance'
a = s.index("### Token identity"); b = s.index("### Performance\n")
s = s[:a] + ident + "\n" + s[b:]
# 2. insert the other-models section before '## Open items'
oi = s.index("## Open items")
s = s[:oi] + other.strip() + "\n\n" + s[oi:]
# 3. open items: replace the token-identity item
old_ti = s[s.index("**Token identity between the arms.**"):s.index("The author decides before merging")]
new_ti = ("**Decode on llama-3.1-8b at prompt 8192.** " + ("Measured " + f"{f(p['tps_pct'], 1)} % (t {f(st['t'], 1)}, {st['n']} paired repetitions) against the merge base, beyond the band but below the 0.5 % noise floor of earlier rounds; prefill 1.2 % faster. Cause not measured. The measurement that would settle it is a perf-counter comparison (cycles and cache misses per attention worker) of the two binaries on that cell.\n\n" if p["verdict"].startswith("DEGRADATION") else f"Measured {f(p['tps_pct'], 1)} % (t {f(st['t'], 1)}, {st['n']} paired repetitions) against the merge base, inside the band of {f(p['band_tps'])} tokens/s but negative in {sum(1 for x in st['deltas'] if x < 0)} of {st['n']} repetitions; prefill {f(p['prefill_pct'], 1)} %. Cause not measured. The measurement that would settle it is a perf-counter comparison (cycles and cache misses per attention worker) of the two binaries on that cell.\n\n"))
s = s.replace(old_ti, new_ti)
s = s.replace("The author decides before merging whether either measurement is needed.", "The author decides before merging whether the kill-switch-vs-OFF-build measurement is needed.")
open(out, "w").write(s)
print("sections written; words:", len(s.split()))
