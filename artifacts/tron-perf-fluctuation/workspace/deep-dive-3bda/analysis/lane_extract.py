#!/usr/bin/env python3
"""Extract one window's slices as per-thread lanes JSON for the HTML figure.

Usage: lane_extract.py <slices_csv> <window_index> <out_json> [--gap-us 1500]

Output: {"window": i, "start_ts": ..., "extent_us": ...,
         "lanes": {thread: [{off_us, dur_us, name, kind(work|wait|instant),
                             truncated(bool)}]}}
Spans are capped at the window extent (see window_gaps.py for the artifact
rationale); spans whose raw end exceeded the extent are marked truncated.
"""

import csv
import json
import sys

sys.path.insert(0, "/home/jhan/workspace/perf-fluctuation/deep-dive-3bda/analysis")
from window_gaps import WAIT_SPANS, load, segment  # noqa: E402

EXTENT_BOUND_NS = 2_500_000


def main():
    slices_csv, widx, out_json = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    rows = load(slices_csv)
    wins = list(segment(rows))
    win = wins[widx]
    w0 = win[0][0]
    cap = wins[widx + 1][0][0] if widx + 1 < len(wins) else None

    wend = w0
    for ts, dur, name, thr in win:
        if name in ("forward", "data ready") or dur < 0 or dur >= EXTENT_BOUND_NS:
            continue
        e = min(ts + dur, cap) if cap is not None else ts + dur
        if name in ("fill_logits_buffer", "notify_listener") or name not in WAIT_SPANS:
            wend = max(wend, e)

    lanes = {}
    for ts, dur, name, thr in win:
        if name == "forward":
            # keep as a marker of next-step dispatch start
            kind, e, trunc = "work", min(ts + 1000, wend), True
        elif name == "data ready":
            kind, e, trunc = "instant", ts, False
        else:
            raw_end = ts + max(dur, 0)
            e = min(raw_end, wend)
            trunc = raw_end > wend or dur < 0
            kind = "wait" if name in WAIT_SPANS else "work"
        if ts > wend:
            continue
        lanes.setdefault(thr.strip(), []).append({
            "off_us": round((ts - w0) / 1000, 2),
            "dur_us": round(max(e - ts, 0) / 1000, 2),
            "name": name,
            "kind": kind,
            "truncated": bool(trunc),
        })
    for v in lanes.values():
        v.sort(key=lambda s: s["off_us"])
    json.dump({"window": widx, "start_ts": w0,
               "extent_us": round((wend - w0) / 1000, 1),
               "lanes": lanes}, open(out_json, "w"), indent=1)
    print(f"window {widx}: extent {(wend - w0)/1000:.0f}us, "
          f"{sum(len(v) for v in lanes.values())} slices, {len(lanes)} lanes")


if __name__ == "__main__":
    main()
