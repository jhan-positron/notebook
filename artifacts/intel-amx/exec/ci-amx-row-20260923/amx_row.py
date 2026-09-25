#!/usr/bin/env python3
"""AMX-benchmark row (llama-3.1-8b tp2, 32 users, prompt 4096) statistics from the four nightly logs -> amx_row.json.
p05 = linear interpolation (systems_test testlib/perf_metrics.py calculate_p05_tps); prefill = 4096 / round(mean TTFT ms) * 1000
(systems_test scripts/perf.py:396-397, identical at 7327184 and 5b2250b9)."""
import json, re, statistics as st
import numpy as np
LOGS = {"3bda-0922": "nightly-35683952944.log", "3bda-0923": "nightly-35815209295.log",
        "genoa-0922": "nightly-genoa-35682128668.log", "genoa-0923": "nightly-genoa-35813240282.log"}
def p05(v):
    s = sorted(v); k = (len(s) - 1) * 0.05; f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)
out = {}
for key, f in LOGS.items():
    L = open(f, encoding="utf-8", errors="replace").read().splitlines()
    i0 = [i for i, l in enumerate(L) if "n_users=32," in l and "prompt_length=4096," in "\n".join(L[i:i + 12])][-1]
    tps, ttft, ts = [], [], []
    for l in L[i0 + 1:]:
        if re.search(r"n_users=\d+,", l): break
        m = re.search(r"Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)", l)
        if m:
            ttft.append(int(m.group(1))); tps.append(float(m.group(2)))
            t = re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)", l); ts.append(t.group(1) if t else None)
    pkg = re.findall(r"Setting up tron \(([^)]+)\)", "\n".join(L[:2000]))
    ttft_r = round(st.mean(ttft))
    out[key] = dict(log=f, config_line=i0 + 1, n=len(tps), tps_mean=float(np.mean(tps)), tps_sd=st.pstdev(tps), p05=p05(tps),
                    tps_min=min(tps), tps_max=max(tps), ttft_mean_ms=st.mean(ttft), ttft_rounded_ms=ttft_r,
                    prefill=4096 / (ttft_r / 1000), first_done=ts[0], last_done=ts[-1], package=pkg[0] if pkg else None)
json.dump(out, open("amx_row.json", "w"), indent=1)
for k, v in out.items(): print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
