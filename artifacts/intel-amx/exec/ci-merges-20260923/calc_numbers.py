#!/usr/bin/env python3
"""Compute every number used by the CI merge report (2026-09-23).

Inputs (same folder):
  perf_all.csv      delphi-3bda nightly rows 09-14..09-23 (parse_perf.sh over GitHub run logs)
  perf_amd_all.csv  andoria-b1a3 nightly rows 09-16, 09-18..09-23
  ../ci-amx-row-20260923/amx_row.json   per-sample stats of the 32-user row (this morning's session)
  ../results/l8b-8u4k-20260920/summary.json  our 09-20 same-code AMX A/B campaign
Output: numbers.json
"""
import csv, json, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
EXEC = os.path.dirname(HERE)

def load(path):
    d = {}
    order = []
    for night, pkg, model, users, prompt, gen, ttft, tps in csv.reader(open(path)):
        if not tps:
            continue
        key = (model, users, prompt)
        if key not in order:
            order.append(key)
        d[(key, night)] = dict(pkg=pkg, ttft=float(ttft), tps=float(tps))
    return d, order

def summarize(d, order, base_nights, new_night):
    rows = []
    for key in order:
        base = [d[(key, n)] for n in base_nights if (key, n) in d]
        new = d.get((key, new_night))
        if not base or not new:
            continue
        r = dict(model=key[0], users=int(key[1]), prompt=int(key[2]), n_base=len(base))
        for m in ("tps", "ttft"):
            vals = [b[m] for b in base]
            mu = st.mean(vals)
            r[m] = dict(mean=mu, min=min(vals), max=max(vals), new=new[m],
                        pct=100 * (new[m] / mu - 1),
                        lo_pct=100 * (min(vals) / mu - 1), hi_pct=100 * (max(vals) / mu - 1),
                        where=("above" if new[m] > max(vals) else "below" if new[m] < min(vals) else "inside"),
                        nights={n: d[(key, n)][m] for n in base_nights + [new_night] if (key, n) in d})
        rows.append(r)
    return rows

intel, intel_order = load(os.path.join(HERE, "perf_all.csv"))
amd, amd_order = load(os.path.join(HERE, "perf_amd_all.csv"))
out = {
    "intel_base_nights": ["0918", "0919", "0920", "0921", "0922"],
    "amd_base_nights": ["a0919", "a0920", "a0921", "g0922"],
    "amd_excluded": "a0918 (run 35302120794 was cancelled; most rows 20-45 % low)",
}
out["intel"] = summarize(intel, intel_order, out["intel_base_nights"], "0923")
out["amd"] = summarize(amd, amd_order, out["amd_base_nights"], "g0923")
out["intel_packages"] = sorted({(n, v["pkg"]) for (k, n), v in intel.items()})
out["amd_packages"] = sorted({(n, v["pkg"]) for (k, n), v in amd.items()})

row = json.load(open(os.path.join(EXEC, "ci-amx-row-20260923", "amx_row.json")))
camp = json.load(open(os.path.join(EXEC, "results", "l8b-8u4k-20260920", "summary.json")))
pp = camp["configs"]["llama_3_1_8b_instruct_good_tp2_32u_p4096"]["per_pass"]
def arm(prefix):
    ps = [v for k, v in sorted(pp.items()) if k.startswith(prefix)]
    return dict(tps=[p["tps_mean"] for p in ps], ttft=[p["ttft_ms"] for p in ps],
                tps_mean=st.mean(p["tps_mean"] for p in ps), ttft_mean=st.mean(p["ttft_ms"] for p in ps))
base, canon = arm("base-"), arm("canon-")
ci22, ci23 = row["3bda-0922"], row["3bda-0923"]
g22, g23 = row["genoa-0922"], row["genoa-0923"]
h = dict(
    ci22_tps=ci22["tps_mean"], ci23_tps=ci23["tps_mean"],
    ci22_ttft=ci22["ttft_mean_ms"], ci23_ttft=ci23["ttft_mean_ms"],
    ci22_prefill=ci22["prefill"], ci23_prefill=ci23["prefill"],
    base_tps=base["tps_mean"], canon_tps=canon["tps_mean"],
    base_tps_passes=base["tps"], canon_tps_passes=canon["tps"],
    base_ttft=base["ttft_mean"], canon_ttft=canon["ttft_mean"],
    base_ttft_passes=base["ttft"], canon_ttft_passes=canon["ttft"],
    base_prefill=4096 / (base["ttft_mean"] / 1000), canon_prefill=4096 / (canon["ttft_mean"] / 1000),
    amd22_tps=g22["tps_mean"], amd23_tps=g23["tps_mean"],
    amd22_ttft=g22["ttft_mean_ms"], amd23_ttft=g23["ttft_mean_ms"],
    amd22_prefill=g22["prefill"], amd23_prefill=g23["prefill"],
    campaign_gain_pct=camp["verdicts"]["cell"]["gain_pct"], campaign_t=camp["verdicts"]["cell"]["paired_t"],
)
h["ci_gain_tps"] = h["ci23_tps"] - h["ci22_tps"]
h["ci_gain_pct"] = 100 * (h["ci23_tps"] / h["ci22_tps"] - 1)
h["ab_gain_tps"] = h["canon_tps"] - h["base_tps"]
h["ab_gain_pct"] = 100 * (h["canon_tps"] / h["base_tps"] - 1)
h["resid_tps"] = h["ci23_tps"] - h["canon_tps"]
h["resid_pct_of_canon"] = 100 * (h["ci23_tps"] / h["canon_tps"] - 1)
h["base_agree_tps"] = h["ci22_tps"] - h["base_tps"]
h["base_agree_pct"] = 100 * (h["ci22_tps"] / h["base_tps"] - 1)
h["gain_diff_tps"] = h["ci_gain_tps"] - h["ab_gain_tps"]
h["ci_ttft_pct"] = 100 * (h["ci23_ttft"] / h["ci22_ttft"] - 1)
h["ab_ttft_pct"] = 100 * (h["canon_ttft"] / h["base_ttft"] - 1)
h["ttft_vs_canon_pct"] = 100 * (h["ci23_ttft"] / h["canon_ttft"] - 1)
h["ttft22_vs_base_pct"] = 100 * (h["ci22_ttft"] / h["base_ttft"] - 1)
h["ci_prefill_pct"] = 100 * (h["ci23_prefill"] / h["ci22_prefill"] - 1)
h["ab_prefill_pct"] = 100 * (h["canon_prefill"] / h["base_prefill"] - 1)
h["amd_tps_pct"] = 100 * (h["amd23_tps"] / h["amd22_tps"] - 1)
h["amd_ttft_pct"] = 100 * (h["amd23_ttft"] / h["amd22_ttft"] - 1)
h["amd_prefill_pct"] = 100 * (h["amd23_prefill"] / h["amd22_prefill"] - 1)
# Estimated counter updates per 10 us of waiting per thread (src/system/mwaitx.cpp at 3faba6d0):
# Intel RTM path returns from monitor_and_wait after tsx_pause_budget = 2048 TSC cycles;
# the code comment gives 2048 cycles ~ 760 ns at 2.7 GHz. AMD MWAITX sleeps up to the full timeout.
h["rtm_budget_ns_est"] = 2048 / 2.7
h["intel_updates_per_10us_est"] = 10000 / (2048 / 2.7)
out["headline"] = h
json.dump(out, open(os.path.join(HERE, "numbers.json"), "w"), indent=1)
for k, v in h.items():
    print(f"{k:28s} {v}")

# "Clearly moved": the new value lies outside the same-package range by more than
# the range's own width, and the change is at least 1 % of the mean. With n base
# nights a value falls outside [min, max] by chance with probability 2/(n+1)
# (33 % for 5 nights), so "outside the range" alone is weak evidence.
def flag(m):
    width = m["max"] - m["min"]
    if m["new"] > m["max"]:
        dist = m["new"] - m["max"]
    elif m["new"] < m["min"]:
        dist = m["min"] - m["new"]
    else:
        dist = 0.0
    # TTFT is logged in whole ms; ignore changes within 3 ms (e.g. 53 -> 54 ms).
    big_enough = abs(m["pct"]) >= 1.0 and abs(m["new"] - m["mean"]) >= (3.0 if m is not None and m.get("unit") == "ms" else 0.0)
    return dist > width and big_enough

for mach in ("intel", "amd"):
    for r in out[mach]:
        r["ttft"]["unit"] = "ms"
        for m in ("tps", "ttft"):
            r[m]["clearly_moved"] = (r["n_base"] > 1) and flag(r[m])
json.dump(out, open(os.path.join(HERE, "numbers.json"), "w"), indent=1)
