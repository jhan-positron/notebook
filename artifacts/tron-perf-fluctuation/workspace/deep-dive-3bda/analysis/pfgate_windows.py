#!/usr/bin/env python3
"""Per-window analysis of a gated pfgate trace (one draw).

The gated binary emits track events only inside the inter-fwd-pass window
(layer-35 attention end -> next step layer-0 attention entry, decode only),
so the trace is a sequence of dense slice clusters separated by silent gaps
of roughly one forward pass (~5 ms at ~180 tok/s). Windows are recovered by
gap-based clustering on the slice timeline.

Usage:
  pfgate_windows.py <trace.pftrace> <out_prefix> [--gap-us 1500] [--tp PATH]

Outputs:
  <out_prefix>.slices.csv    raw slice dump (cached; reused if present)
  <out_prefix>.windows.csv   one row per window: start/dur + per-span totals
  <out_prefix>.summary.json  window count, duration stats, per-span stats
"""

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys

DUMP_SQL = """
SELECT s.ts, s.dur, s.name, s.category, th.tid AS tid, th.name AS thread_name
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread th USING (utid)
ORDER BY s.ts;
"""

# Spans reported as their own columns in windows.csv; everything else is
# aggregated into "other". Names from the 12804a812 source inventory plus the
# generated qwen plugin kernels (matched by prefix).
KEY_SPANS = [
    "fill_logits_buffer",
    "waiting_for_logits",
    "notify_listener",
    "setup_logits",
    "finalize_minibatches",
    "construct_minibatches",
    "gather_token_data",
    "compute_forward_args",
    "forward args",
    "forward",
    "add_tokens",
    "finalize_ranges",
    "work_queue::do_work get_work",
    "poll_dma_completions",
    "matmul enqueue",
    "Prepare hardware matmul job",
    "Launch hardware matmul job",
    "legacy hw_prepare",
    "legacy tx_launch",
    "tx submitting activation DMA request",
    "rx collecting results",
    "data ready",
    "Rope Q",
    "Free scratchpads",
]


def dump_slices(tp, trace, out_csv):
    if os.path.exists(out_csv) and os.path.getsize(out_csv) > 0:
        return
    sql = out_csv + ".sql"
    with open(sql, "w") as f:
        f.write(DUMP_SQL)
    with open(out_csv, "w") as f:
        subprocess.run([tp, "-q", sql, trace], stdout=f, stderr=subprocess.DEVNULL, check=True)
    os.unlink(sql)


def load_slices(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                ts, dur = int(r["ts"]), int(r["dur"])
            except (ValueError, KeyError):
                continue
            rows.append((ts, dur, r["name"], r["category"], r["thread_name"]))
    rows.sort(key=lambda x: x[0])
    return rows


def segment(rows, gap_ns):
    """Yield lists of rows; a new window starts when the next slice STARTS
    more than gap_ns after the previous slice start. Slice ends are ignored
    for boundary detection: spans like 'forward' (and unfinished dur<0
    spans) deliberately cross the silent gap between windows and would
    otherwise bridge every gap."""
    win, prev_ts = [], None
    for row in rows:
        ts = row[0]
        if prev_ts is not None and ts - prev_ts > gap_ns:
            if win:
                yield win
            win = []
        win.append(row)
        prev_ts = ts
    if win:
        yield win


def pctl(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    i = min(len(s) - 1, max(0, int(round(p / 100 * (len(s) - 1)))))
    return s[i]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("out_prefix")
    ap.add_argument("--gap-us", type=float, default=1500.0)
    ap.add_argument("--tp", default="/scratch/jhan/tools/trace_processor")
    args = ap.parse_args()

    slices_csv = args.out_prefix + ".slices.csv"
    dump_slices(args.tp, args.trace, slices_csv)
    rows = load_slices(slices_csv)
    if not rows:
        print("no slices", file=sys.stderr)
        sys.exit(1)

    windows = list(segment(rows, int(args.gap_us * 1000)))

    span_cols = list(KEY_SPANS)
    wrows, per_span_window_totals = [], {}
    for wi, win in enumerate(windows):
        start = win[0][0]
        # Two-pass extent. Gating produces step-spanning artifacts: 'forward'
        # crosses the step by design, and unmatched END events (begins dropped
        # while the gate was closed) get attributed by trace_processor to
        # still-open slices, inflating e.g. 'Save K' to ~5 ms. Window extent
        # is therefore computed from plausibly-window-local spans only
        # (dur < EXTENT_BOUND_NS), then every contribution is capped at it.
        EXTENT_BOUND_NS = 2_500_000
        cap = windows[wi + 1][0][0] if wi + 1 < len(windows) else None
        end = start
        for ts, dur, name, cat, thr in win:
            if name == "forward" or dur < 0 or dur >= EXTENT_BOUND_NS:
                continue
            sl_end = ts + dur
            if cap is not None:
                sl_end = min(sl_end, cap)
            end = max(end, sl_end)
        totals = {}
        n_dataready = 0
        n_rope_q = 0
        threads = set()
        for ts, dur, name, cat, thr in win:
            threads.add(thr)
            if name == "data ready":
                n_dataready += 1
            if name == "Rope Q" or name.startswith("kernel_rmsnorm_rope"):
                n_rope_q += 1
            sl_end = min(ts + max(dur, 0), end)
            key = name if name in KEY_SPANS else "other"
            totals[key] = totals.get(key, 0) + max(sl_end - ts, 0)
        row = {
            "window": wi,
            "start_ts": start,
            "dur_us": (end - start) / 1000.0,
            "n_slices": len(win),
            "n_threads": len(threads),
            "n_data_ready": n_dataready,
            "n_rope_spans": n_rope_q,
        }
        for k in span_cols + ["other"]:
            v = totals.get(k, 0) / 1000.0  # us
            row[f"us:{k}"] = round(v, 3)
            per_span_window_totals.setdefault(k, []).append(v)
        wrows.append(row)

    with open(args.out_prefix + ".windows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(wrows[0].keys()))
        w.writeheader()
        w.writerows(wrows)

    durs = [r["dur_us"] for r in wrows]
    summary = {
        "trace": args.trace,
        "n_slices": len(rows),
        "n_windows": len(windows),
        "gap_us_threshold": args.gap_us,
        "window_dur_us": {
            "mean": round(statistics.mean(durs), 1),
            "median": round(statistics.median(durs), 1),
            "p90": round(pctl(durs, 90), 1),
            "p99": round(pctl(durs, 99), 1),
            "max": round(max(durs), 1),
        },
        "trace_span_s": round((rows[-1][0] - rows[0][0]) / 1e9, 2),
        "per_span_us": {
            k: {
                "windows_present": sum(1 for v in vals if v > 0),
                "median": round(statistics.median(vals), 1),
                "p90": round(pctl(vals, 90), 1),
                "total_ms": round(sum(vals) / 1000.0, 2),
            }
            for k, vals in sorted(per_span_window_totals.items())
            if any(v > 0 for v in vals)
        },
    }
    with open(args.out_prefix + ".summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps({k: summary[k] for k in
                      ("n_slices", "n_windows", "window_dur_us", "trace_span_s")}))


if __name__ == "__main__":
    main()
