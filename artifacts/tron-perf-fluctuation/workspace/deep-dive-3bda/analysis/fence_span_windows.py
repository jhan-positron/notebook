#!/usr/bin/env python3
"""Named-span content of the exactly-cut [Fence 1 -> Fence 3] windows.

Joins the trace-sync-points session's fence window boundaries (fencepf CSV:
t_f1_ns, f1f3_ns) with a full slice dump of the same trace, and emits
per-window named-span totals plus work/wait/idle union coverage, all clipped
to the exact fence window.

Usage: fence_span_windows.py <trace> <fence_csv> <out_prefix>
"""

import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from window_gaps import WAIT_SPANS  # noqa: E402

TP = "/scratch/jhan/tools/trace_processor"
DUMP_SQL = """
SELECT s.ts, s.dur, s.name, s.category, th.tid AS tid, th.name AS thread_name
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread th USING (utid)
ORDER BY s.ts;
"""

KEY_SPANS = [
    "fill_logits_buffer", "waiting_for_logits", "notify_listener",
    "setup_logits", "compute_forward_args", "construct_minibatches",
    "finalize_ranges", "add_tokens", "assemble attention plan",
    "matmul enqueue", "Prepare hardware matmul job", "Launch hardware matmul job",
    "legacy hw_prepare", "legacy tx_launch",
    "tx submitting activation DMA request", "rx collecting results",
    "Free scratchpads",
]


def dump(trace, out_csv):
    if os.path.exists(out_csv) and os.path.getsize(out_csv) > 0:
        return
    sql = out_csv + ".sql"
    open(sql, "w").write(DUMP_SQL)
    with open(out_csv, "w") as f:
        subprocess.run([TP, "-q", sql, trace], stdout=f,
                       stderr=subprocess.DEVNULL, check=True)
    os.unlink(sql)


def main():
    trace, fence_csv, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    slices_csv = prefix + ".slices.csv"
    dump(trace, slices_csv)

    wins = []
    for r in csv.DictReader(open(fence_csv)):
        f1 = int(r["t_f1_ns"])
        wins.append((f1, f1 + int(r["f1f3_ns"])))
    wins.sort()

    rows = []
    for r in csv.DictReader(open(slices_csv)):
        try:
            ts, dur = int(r["ts"]), int(r["dur"])
        except (ValueError, KeyError):
            continue
        rows.append((ts, max(dur, 0), r["name"]))
    rows.sort()

    import bisect
    starts = [w[0] for w in wins]
    acc = [{"n": 0, "spans": {}, "work": [], "wait": []} for _ in wins]
    for ts, dur, name in rows:
        i = bisect.bisect_right(starts, ts) - 1
        if i < 0:
            continue
        w0, w1 = wins[i]
        if ts >= w1 or name in ("fence 1", "fence 3", "forward"):
            continue
        e = min(ts + dur, w1)
        a = acc[i]
        a["n"] += 1
        key = name if name in KEY_SPANS else "other"
        a["spans"][key] = a["spans"].get(key, 0) + (e - ts)
        (a["wait"] if name in WAIT_SPANS else a["work"]).append((ts, e))

    def merged_len(ivs, hi):
        ivs = sorted(ivs)
        tot, cur_s, cur_e = 0, None, None
        for s, e in ivs:
            e = min(e, hi)
            if cur_e is None or s > cur_e:
                if cur_e is not None:
                    tot += cur_e - cur_s
                cur_s, cur_e = s, e
            else:
                cur_e = max(cur_e, e)
        if cur_e is not None:
            tot += cur_e - cur_s
        return tot

    out = []
    for (w0, w1), a in zip(wins, acc):
        span = (w1 - w0) / 1000.0
        work = merged_len(a["work"], w1) / 1000.0
        allc = merged_len(a["work"] + a["wait"], w1) / 1000.0
        row = {"f1_ts": w0, "f1f3_us": round(span, 2), "n_slices": a["n"],
               "work_us": round(work, 2), "wait_us": round(allc - work, 2),
               "idle_us": round(span - allc, 2)}
        for k in KEY_SPANS + ["other"]:
            row[f"us:{k}"] = round(a["spans"].get(k, 0) / 1000.0, 2)
        out.append(row)

    with open(prefix + ".fspans.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    import statistics as st
    spans = [o["f1f3_us"] for o in out]
    print(f"{prefix}: {len(out)} windows, f1f3 med {st.median(spans):.0f}us, "
          f"idle med {st.median([o['idle_us'] for o in out]):.1f}us")


if __name__ == "__main__":
    main()
