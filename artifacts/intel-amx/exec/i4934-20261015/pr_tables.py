#!/usr/bin/env python3
"""pr_tables.py <summary.json> --arms a,b,c --pairs x:y,... [--attn cpu|fpga] [--label arm=Label,...]

Prints the two Markdown tables of the PR body's Performance subsection from a campaign summary.json
(summarize.py output): one row per cell and binary (mean, sample sd, n), one row per cell and pair with
the difference, the band (twice the larger sd of the pair, never under 0.40 TPS or 0.15 s), the verdict
(inside, beyond, or better = beyond in the first arm's favour) and the paired t statistic.
"""
import argparse
import json

FLOOR_TPS = 0.40
FLOOR_TTFT = 0.15


def cell_name(c):
    return f"tp{c['tp']}, {c['users']} users, prompt {c['prompt']:,}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('summary')
    ap.add_argument('--arms', required=True)
    ap.add_argument('--pairs', required=True)
    ap.add_argument('--attn', default=None)
    ap.add_argument('--label', default='')
    ap.add_argument('--combined', action='store_true', help='one table: both means, the difference, the band, the verdict, t')
    a = ap.parse_args()
    arms = a.arms.split(',')
    pairs = [p.split(':') for p in a.pairs.split(',')]
    labels = dict(kv.split('=') for kv in a.label.split(',') if kv)
    d = json.load(open(a.summary))
    cells = {(c['cell'], c['attn'], c['arm']): c for c in d['cells']}
    paired = {(p['cell'], p['attn'], p['a'], p['b']): p for p in d['paired']}
    keys = sorted({(c['cell'], c['attn']) for c in d['cells'] if a.attn is None or c['attn'] == a.attn},
                  key=lambda k: (k[1], cells[(k[0], k[1], arms[0])]['tp'], cells[(k[0], k[1], arms[0])]['prompt']))
    if a.combined:
        print('| Cell | Pair | TPS per user (sd) | TPS difference (band) | Verdict | t | TTFT s (sd) | TTFT difference ms (band) | Verdict |')
        print('|---|---|---|---|---|---|---|---|---|')
        for cell, attn in keys:
            for x, y in pairs:
                cx, cy = cells.get((cell, attn, x)), cells.get((cell, attn, y))
                p = paired.get((cell, attn, x, y))
                if cx is None or cy is None or p is None:
                    continue
                dt = cx['tps_mean'] - cy['tps_mean']
                bt = max(2 * max(cx['tps_sd'], cy['tps_sd']), FLOOR_TPS)
                vt = 'inside' if abs(dt) <= bt else ('better' if dt > 0 else 'beyond')
                df = (cx['ttft_mean'] - cy['ttft_mean']) * 1000
                bf = max(2 * max(cx['ttft_sd'], cy['ttft_sd']), FLOOR_TTFT) * 1000
                vf = 'inside' if abs(df) <= bf else ('better' if df < 0 else 'beyond')
                pct = 100 * dt / cy['tps_mean']
                print(f"| {cell_name(cx)} | `{labels.get(x, x)}` vs `{labels.get(y, y)}` | {cx['tps_mean']:.2f} ({cx['tps_sd']:.2f}) vs {cy['tps_mean']:.2f} ({cy['tps_sd']:.2f}) | "
                      f"{dt:+.2f} ({pct:+.1f} %, band {bt:.2f}) | {vt} | {p['tps']['t']:+.1f} | "
                      f"{cx['ttft_mean']:.3f} ({cx['ttft_sd']:.3f}) vs {cy['ttft_mean']:.3f} ({cy['ttft_sd']:.3f}) | {int(round(df)):+d} (band {bf:.0f}) | {vf} |")
        return
    print('| Cell | Binary | Decode TPS per user (sd) | TTFT s (sd) | n |')
    print('|---|---|---|---|---|')
    for cell, attn in keys:
        for arm in arms:
            c = cells.get((cell, attn, arm))
            if c is None:
                print(f'| {cell_name(cells[(cell, attn, arms[0])])} | `{labels.get(arm, arm)}` | not run | | |')
                continue
            print(f"| {cell_name(c)} | `{labels.get(arm, arm)}` | {c['tps_mean']:.2f} ({c['tps_sd']:.2f}) | "
                  f"{c['ttft_mean']:.3f} ({c['ttft_sd']:.3f}) | {c['n']} |")
    print()
    print('| Cell | Pair | TPS difference (band) | Verdict | t | TTFT difference ms (band) | Verdict |')
    print('|---|---|---|---|---|---|---|')
    for cell, attn in keys:
        for x, y in pairs:
            cx, cy = cells.get((cell, attn, x)), cells.get((cell, attn, y))
            p = paired.get((cell, attn, x, y))
            if cx is None or cy is None or p is None:
                print(f'| {cell_name(cells[(cell, attn, arms[0])])} | `{labels.get(x, x)}` vs `{labels.get(y, y)}` | not run | | | | |')
                continue
            dt = cx['tps_mean'] - cy['tps_mean']
            bt = max(2 * max(cx['tps_sd'], cy['tps_sd']), FLOOR_TPS)
            vt = 'inside' if abs(dt) <= bt else ('better' if dt > 0 else 'beyond')
            df = (cx['ttft_mean'] - cy['ttft_mean']) * 1000
            bf = max(2 * max(cx['ttft_sd'], cy['ttft_sd']), FLOOR_TTFT) * 1000
            vf = 'inside' if abs(df) <= bf else ('better' if df < 0 else 'beyond')
            pct = 100 * dt / cy['tps_mean']
            print(f"| {cell_name(cx)} | `{labels.get(x, x)}` vs `{labels.get(y, y)}` | {dt:+.2f} ({pct:+.1f} %, band {bt:.2f}) | {vt} | "
                  f"{p['tps']['t']:+.1f} | {int(round(df)):+d} (band {bf:.0f}) | {vf} |")


if __name__ == '__main__':
    main()
