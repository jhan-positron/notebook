#!/usr/bin/env python3
"""Aggregate per-draw pfgate window stats and correlate with decode TPS.

Reads results.csv (draw -> TPS) and analysis/out/<draw>/<draw>.windows.csv,
computes per-draw per-span mean-per-window totals, Pearson corr vs TPS,
fast4/slow4 means, and window-duration texture (median/p90).

fill_logits_buffer repair: in ~11% of windows the fill slice is unfinished
(dur=-1, end dropped) while its wrapper notify_listener closed; use
max(fill, notify_listener - 12us) as the repaired fill value per window.

Usage: aggregate_draws.py <campaign_root> <out_json>
"""

import csv
import json
import math
import statistics
import sys

OUT_DIR = "/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis/out"

SPANS = [
    "fill_logits_buffer",  # repaired; ~ segment B (stream wait + consume)
    "waiting_for_logits",
    "notify_listener",
    "setup_logits",
    "compute_forward_args",
    "construct_minibatches",
    "finalize_ranges",
    "add_tokens",
    "forward args",
    "matmul enqueue",
    "Prepare hardware matmul job",
    "Launch hardware matmul job",
    "legacy hw_prepare",
    "legacy tx_launch",
    "tx submitting activation DMA request",
    "rx collecting results",
    "work_queue::do_work get_work",
    "Free scratchpads",
    "other",
]


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def pctl(vals, p):
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))]


def load_draw(draw):
    rows = list(csv.DictReader(open(f"{OUT_DIR}/{draw}/{draw}.windows.csv")))
    per_span = {k: [] for k in SPANS}
    win_spans = []  # per-window "window span" = repaired busy extent proxy
    for r in rows:
        fill = float(r["us:fill_logits_buffer"])
        notify = float(r["us:notify_listener"])
        repaired = max(fill, max(notify - 12.0, 0.0))
        for k in SPANS:
            if k == "fill_logits_buffer":
                per_span[k].append(repaired)
            else:
                per_span[k].append(float(r.get(f"us:{k}", 0)))
        win_spans.append(float(r["dur_us"]))
    return rows, per_span, win_spans


def main():
    root, out_json = sys.argv[1], sys.argv[2]
    draws = {}
    for r in csv.DictReader(open(f"{root}/results.csv")):
        if r["status"] == "ok":
            draws[r["draw"]] = float(r["generate_tok_s"])

    per_draw = {}
    for draw, tps in sorted(draws.items()):
        try:
            rows, per_span, win_spans = load_draw(draw)
        except FileNotFoundError:
            continue
        per_draw[draw] = {
            "tps": tps,
            "n_windows": len(rows),
            "span_mean_us": {k: round(statistics.mean(v), 2) for k, v in per_span.items()},
            "span_median_us": {k: round(statistics.median(v), 2) for k, v in per_span.items()},
            "span_p90_us": {k: round(pctl(v, 90), 2) for k, v in per_span.items()},
        }

    order = sorted(per_draw, key=lambda d: per_draw[d]["tps"])
    slow4, fast4 = order[:4], order[-4:]
    tps_list = [per_draw[d]["tps"] for d in order]

    summary = {
        "campaign_root": root,
        "n_draws": len(per_draw),
        "tps": {
            "min": min(tps_list), "max": max(tps_list),
            "mean": round(statistics.mean(tps_list), 2),
            "cv_pct": round(100 * statistics.stdev(tps_list) / statistics.mean(tps_list), 2),
            "gap_pct": round(100 * (max(tps_list) - min(tps_list)) / max(tps_list), 2),
        },
        "fastest": order[-1], "slowest": order[0],
        "fast4": fast4, "slow4": slow4,
        "spans": {},
        "per_draw": per_draw,
    }
    for k in SPANS:
        xs = [per_draw[d]["span_mean_us"][k] for d in order]
        f4 = statistics.mean(per_draw[d]["span_mean_us"][k] for d in fast4)
        s4 = statistics.mean(per_draw[d]["span_mean_us"][k] for d in slow4)
        summary["spans"][k] = {
            "fast4_us": round(f4, 2),
            "slow4_us": round(s4, 2),
            "delta_us": round(s4 - f4, 2),
            "corr_vs_tps": round(pearson(xs, tps_list), 3) if pearson(xs, tps_list) is not None else None,
        }
    json.dump(summary, open(out_json, "w"), indent=1)
    print(json.dumps({"n_draws": summary["n_draws"], "tps": summary["tps"],
                      "fastest": summary["fastest"], "slowest": summary["slowest"]}))
    print(f"{'span':<40} {'fast4':>8} {'slow4':>8} {'delta':>8} {'corr':>6}")
    for k in SPANS:
        s = summary["spans"][k]
        print(f"{k:<40} {s['fast4_us']:>8} {s['slow4_us']:>8} {s['delta_us']:>8} {s['corr_vs_tps']}")


if __name__ == "__main__":
    main()
