#!/usr/bin/env python3
"""Two-level attribution for the pfgate campaign (report table, §6).

Level 1: whole decode step (derived from TPS) split into the MEASURED
inter-fwd-pass window (gap-clustered slice activity) and the derived
remainder (forward pass: layers 0-35 attention+MLP, not visible to the
gated trace). Reconciliation residual = ΔT_step - (Δwindow + Δremainder)
is zero by construction at level 1 (remainder is derived), so the honest
reconciliation figure is Δwindow / ΔT_step.

Level 2: within the window, split into union-coverage classes
(coordinator work / listener wait (B: fill+waiting_for_logits) /
tx+rx driver waits / all-idle) plus the per-span table with corr vs TPS.

Usage: attribution.py <campaign_root> <out_json>
"""

import csv
import json
import math
import statistics
import sys

OUT = "/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out"
TSC_GHZ = 2.7


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def load_gaps(draw):
    rows = list(csv.DictReader(open(f"{OUT}/{draw}/{draw}.gaps.csv")))
    return {
        "span": [float(r["span_us"]) for r in rows],
        "work": [float(r["work_cov_us"]) for r in rows],
        "wait": [float(r["wait_cov_us"]) for r in rows],
        "idle": [float(r["idle_us"]) for r in rows],
        "big": [float(r["biggest_gap_us"]) for r in rows],
    }


def main():
    root, out_json = sys.argv[1], sys.argv[2]
    tps = {}
    for r in csv.DictReader(open(f"{root}/results.csv")):
        if r["status"] == "ok":
            tps[r["draw"]] = float(r["generate_tok_s"])
    draws = sorted(tps)
    order = sorted(draws, key=lambda d: tps[d])
    slow4, fast4 = order[:4], order[-4:]

    g = {d: load_gaps(d) for d in draws}
    step_us = {d: 1e6 / tps[d] for d in draws}
    win_us = {d: statistics.mean(g[d]["span"]) for d in draws}

    def mean4(dset, key):
        return statistics.mean(statistics.mean(g[d][key]) for d in dset)

    f_step = statistics.mean(step_us[d] for d in fast4)
    s_step = statistics.mean(step_us[d] for d in slow4)
    f_win = statistics.mean(win_us[d] for d in fast4)
    s_win = statistics.mean(win_us[d] for d in slow4)
    dt = s_step - f_step

    level1 = {
        "step_us": {"fast4": round(f_step, 1), "slow4": round(s_step, 1), "delta": round(dt, 1)},
        "window_us": {"fast4": round(f_win, 1), "slow4": round(s_win, 1),
                      "delta": round(s_win - f_win, 1),
                      "share_of_dT_pct": round(100 * (s_win - f_win) / dt, 1)},
        "remainder_derived_us": {"fast4": round(f_step - f_win, 1),
                                 "slow4": round(s_step - s_win, 1),
                                 "delta": round((s_step - s_win) - (f_step - f_win), 1),
                                 "share_of_dT_pct": round(100 * ((s_step - s_win) - (f_step - f_win)) / dt, 1)},
        "corr_window_vs_tps": round(pearson([win_us[d] for d in order], [tps[d] for d in order]), 3),
    }

    level2 = {}
    for key, label in (("work", "host work spans (union)"),
                       ("wait", "wait spans (union, incl. B fill/stream)"),
                       ("idle", "all-idle (no span on any thread)"),
                       ("big", "largest single all-idle gap")):
        f4, s4 = mean4(fast4, key), mean4(slow4, key)
        xs = [statistics.mean(g[d][key]) for d in order]
        level2[label] = {
            "fast4_us": round(f4, 1), "slow4_us": round(s4, 1),
            "delta_us": round(s4 - f4, 1),
            "share_of_level1_pct": round(100 * (s4 - f4) / (s_win - f_win), 1),
            "corr_vs_tps": round(pearson(xs, [tps[d] for d in order]), 3),
        }
    resid = (s_win - f_win) - sum(v["delta_us"] for k, v in level2.items()
                                  if not k.startswith("largest"))
    result = {
        "n_draws": len(draws),
        "tps": {d: tps[d] for d in order},
        "fast4": fast4, "slow4": slow4,
        "level1": level1,
        "level2": level2,
        "level2_residual_us": round(resid, 1),
        "note": "us per decode step; TSC 2.7 GHz: 1 us = 2700 cycles",
    }
    json.dump(result, open(out_json, "w"), indent=1)
    print(json.dumps(result["level1"], indent=1))
    print(json.dumps(level2, indent=1))
    print("level2 residual:", result["level2_residual_us"], "us")


if __name__ == "__main__":
    main()
