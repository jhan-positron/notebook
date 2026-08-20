#!/usr/bin/env python3
"""Summarize a deepdive campaign's results.csv: per-draw TPS, CV, best/worst.

Usage: tps_summary.py <results.csv> [<results.csv> ...]
"""
import csv
import statistics
import sys


def summarize(path):
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("status") != "ok":
                continue
            try:
                rows.append((r["draw"], float(r["generate_tok_s"]), r.get("token_sha256", "")))
            except (ValueError, KeyError):
                pass
    if not rows:
        print(f"{path}: no successful draws")
        return
    vals = [v for _, v, _ in rows]
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
    cv = 100.0 * sd / mean if mean else 0.0
    best = max(rows, key=lambda x: x[1])
    worst = min(rows, key=lambda x: x[1])
    gap = 100.0 * (best[1] - worst[1]) / best[1]
    hashes = {h for _, _, h in rows if h}
    print(f"{path}")
    print(f"  n={len(vals)} mean={mean:.3f} sd={sd:.3f} CV={cv:.2f}% ")
    print(f"  best={best[0]} {best[1]:.3f} tok/s | worst={worst[0]} {worst[1]:.3f} tok/s | gap={gap:.2f}%")
    print(f"  token hashes distinct={len(hashes)} (expect 1 with --pay-for-determinism)")
    for d, v, _ in rows:
        bar = "#" * int((v - min(vals)) / (max(vals) - min(vals) + 1e-9) * 40)
        print(f"    {d} {v:9.3f} {bar}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        summarize(p)
