#!/usr/bin/env python3
"""Per-token [Fence 1 -> Fence 3] windows from a gated perfetto trace.

Uses the fence instants (v11 build, category "model") to cut windows exactly
at the two definitive sync points -- no derived window edges. Also collects
the per-card wcls "data ready" instants (label='wcls') inside each window.

Usage: fence_windows.py trace.pftrace out.csv
Writes one row per window: ix, t_f1_ns, f1f3_ns, period_ns (F3->F3),
dr_first_ns, dr_last_ns (wcls data-ready relative to F1; blank if not 4).

Provenance: reconstructed verbatim 2026-08-14 into deep-dive/tools/ after the
/tmp scratchpad copy was lost to cleanup (ops rule: durable artifacts' tools
live on /scratch or in the workspace). Re-validated against the
fence13pf-tp4-20260813T210954Z smoke trace: 3733 windows, median 479.0us,
mean 547.1us, all windows with 4 wcls data-ready instants.
"""
import csv
import subprocess
import sys
import tempfile

import numpy as np

TP = "/scratch/jhan/tools/trace_processor"


def query(trace, sql):
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as f:
        f.write(sql)
        path = f.name
    out = subprocess.run([TP, "query", "-f", path, trace],
                         capture_output=True, text=True, check=True)
    rows = list(csv.reader(out.stdout.strip().splitlines()))
    return rows[0], rows[1:]


def main():
    trace, out_path = sys.argv[1], sys.argv[2]
    _, fences = query(trace, (
        "SELECT ts, name FROM slice WHERE name IN ('fence 1','fence 3') "
        "ORDER BY ts;"))
    _, drs = query(trace, (
        "SELECT ts FROM slice WHERE name = 'data ready' "
        "AND EXTRACT_ARG(arg_set_id, 'debug.label') = 'wcls' ORDER BY ts;"))
    dr = np.array([int(r[0]) for r in drs], dtype=np.int64)

    # pair each fence 1 with the first fence 3 after it; skip unpaired tails
    rows = []
    f3_ts_prev = None
    pend_f1 = None
    for ts, name in ((int(r[0]), r[1]) for r in fences):
        if name == "fence 1":
            pend_f1 = ts  # a later fence 1 before any fence 3 would replace
        elif pend_f1 is not None:
            f1, f3 = pend_f1, ts
            pend_f1 = None
            i0, i1 = np.searchsorted(dr, f1), np.searchsorted(dr, f3)
            n_dr = i1 - i0
            dr_first = dr[i0] - f1 if n_dr == 4 else ""
            dr_last = dr[i1 - 1] - f1 if n_dr == 4 else ""
            period = f3 - f3_ts_prev if f3_ts_prev is not None else ""
            rows.append((len(rows), f1, f3 - f1, period, dr_first, dr_last,
                         n_dr))
            f3_ts_prev = f3

    with open(out_path, "w") as f:
        f.write("ix,t_f1_ns,f1f3_ns,period_ns,dr_first_ns,dr_last_ns,n_wcls_dr\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")

    v = np.array([r[2] for r in rows], dtype=float)
    n4 = sum(1 for r in rows if r[6] == 4)
    print(f"{len(rows)} windows -> {out_path}; "
          f"median {np.median(v)/1e3:.1f}us mean {v.mean()/1e3:.1f}us "
          f"p90 {np.percentile(v,90)/1e3:.1f}us; windows with 4 wcls dr: {n4}")


if __name__ == "__main__":
    main()
