#!/usr/bin/env python3
"""A/B verdict for the wcls-bypass experiment.

Inputs: two dirs of per-draw fence3_dump CSVs (control arm, bypass arm), plus
each campaign's results.csv (TPS per draw). Cycles at 2.70 GHz (delphi TSC).

PRE-REGISTERED CRITERIA (fixed 2026-08-14 before seeing bypass data):
  M1 within-draw F1F3 spread: per-draw (p90-p10); compare median across draws.
  M2 cross-draw F1F3 level: spread (max-min) of per-draw F1F3 medians.
  M3 within-draw F3F3 period spread: per-draw (p90-p10); median across draws.
  M4 cross-draw TPS: coefficient of variation over the 16 draws.
  M5 drift amplitude: per-draw (Q4 median - Q1 median) of F1F3 by token
     quartile; median of |amplitude| across draws.
  COLLAPSE = bypass < 25% of control; PERSIST = > 75%; else PARTIAL.

Usage: ab_verdict.py ctl_dumps byp_dumps ctl_results.csv byp_results.csv out.json
"""
import csv
import glob
import json
import os
import sys

import numpy as np

CYC_PER_US = 2700.0


def load_arm(dumps_dir, results_csv):
    draws = {}
    for f in sorted(glob.glob(os.path.join(dumps_dir, "f1f3-draw*.csv"))):
        name = "draw_" + os.path.basename(f).split("draw")[-1][:2]
        draws[name] = np.genfromtxt(f, delimiter=",", names=True)
    tps = {}
    with open(results_csv) as fh:
        for row in csv.DictReader(fh):
            if row["status"] == "ok" and row["draw"].startswith("draw"):
                tps[row["draw"]] = float(row["generate_tok_s"])
    return draws, tps


def arm_metrics(draws, tps):
    m = {"per_draw": {}}
    f1f3_meds, f1f3_spreads, per_spreads, drifts = [], [], [], []
    for name, a in sorted(draws.items()):
        f = a["F1F3"] / CYC_PER_US
        per = a["F3period"]
        per = per[~np.isnan(per)] / CYC_PER_US
        q = np.array_split(f, 4)
        drift = float(np.median(q[3]) - np.median(q[0]))
        d = {
            "n": int(len(f)),
            "f1f3_p10": float(np.percentile(f, 10)),
            "f1f3_p50": float(np.percentile(f, 50)),
            "f1f3_p90": float(np.percentile(f, 90)),
            "f1f3_p99": float(np.percentile(f, 99)),
            "f1f3_max": float(f.max()),
            "f1f3_spread_p90_p10": float(np.percentile(f, 90) - np.percentile(f, 10)),
            "per_p50": float(np.percentile(per, 50)),
            "per_spread_p90_p10": float(np.percentile(per, 90) - np.percentile(per, 10)),
            "per_p99": float(np.percentile(per, 99)),
            "drift_q4_q1": drift,
            "tps": tps.get(name),
        }
        m["per_draw"][name] = d
        f1f3_meds.append(d["f1f3_p50"])
        f1f3_spreads.append(d["f1f3_spread_p90_p10"])
        per_spreads.append(d["per_spread_p90_p10"])
        drifts.append(abs(drift))
    tv = list(tps.values())
    m["M1_f1f3_spread_med_us"] = float(np.median(f1f3_spreads))
    m["M2_f1f3_med_range_us"] = float(max(f1f3_meds) - min(f1f3_meds))
    m["M3_period_spread_med_us"] = float(np.median(per_spreads))
    m["M4_tps_cv_pct"] = float(np.std(tv) / np.mean(tv) * 100) if tv else None
    m["M4_tps_min_max"] = [min(tv), max(tv)] if tv else None
    m["M5_drift_med_us"] = float(np.median(drifts))
    return m


def classify(c, b):
    r = b / c if c > 0 else float("inf")
    return ("COLLAPSE" if r < 0.25 else "PERSIST" if r > 0.75 else "PARTIAL"), r


def main():
    ctl_draws, ctl_tps = load_arm(sys.argv[1], sys.argv[3])
    byp_draws, byp_tps = load_arm(sys.argv[2], sys.argv[4])
    ctl, byp = arm_metrics(ctl_draws, ctl_tps), arm_metrics(byp_draws, byp_tps)
    out = {"control": ctl, "bypass": byp, "verdicts": {}}
    for k in ["M1_f1f3_spread_med_us", "M2_f1f3_med_range_us",
              "M3_period_spread_med_us", "M4_tps_cv_pct", "M5_drift_med_us"]:
        v, r = classify(ctl[k], byp[k])
        out["verdicts"][k] = {"control": ctl[k], "bypass": byp[k],
                              "ratio": round(r, 4), "class": v}
    with open(sys.argv[5], "w") as f:
        json.dump(out, f, indent=1)
    for k, v in out["verdicts"].items():
        print(f"{k}: ctl={v['control']:.2f} byp={v['bypass']:.2f} "
              f"ratio={v['ratio']:.3f} -> {v['class']}")


if __name__ == "__main__":
    main()
