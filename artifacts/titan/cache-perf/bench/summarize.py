#!/usr/bin/env python3
"""summarize.py - print markdown tables from a run_crb.sh results directory.

usage: summarize.py RESULTS_DIR [--ghz 2.8]
"""
import glob
import os
import sys

LEVELS = [  # name, min size, max size (bytes) for the latency plateau pick
    ("L1", 16 << 10, 32 << 10),
    ("L2", 256 << 10, 1 << 20),
    ("L3", 8 << 20, 64 << 20),
    ("DRAM", 1 << 30, 2 << 30),
]
REGIME_BY_BYTES = {32 << 10: "L1", 1 << 20: "L2", 8 << 20: "L3", 256 << 20: "DRAM", 1 << 30: "DRAM"}
PERF_EVENTS = ["l1d_cache_refill", "l2d_cache_refill", "l3d_cache_refill",
               "ll_cache_miss_rd", "dtlb_walk", "cpu_cycles", "inst_retired"]


def parse_size(tok):
    mul = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    if tok[-1].upper() in mul:
        return int(float(tok[:-1]) * mul[tok[-1].upper()])
    return int(tok)


def fmt_size(b):
    for unit, div in (("G", 1 << 30), ("M", 1 << 20), ("K", 1 << 10)):
        if b % div == 0 or b >= div:
            v = b / div
            return ("%g%s" % (v, unit))
    return str(b)


def csv_rows(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield line.split(",")


def read_latency(path):
    """size_bytes -> (best ns/load, loads)"""
    best = {}
    if not os.path.exists(path):
        return best
    for r in csv_rows(path):
        if len(r) == 4 and r[1] == "best":
            best[int(r[0])] = (float(r[3]), int(r[2]))
    return best


def read_perf(outdir, run):
    """size_bytes -> {event: count} for the 'short' or 'long' perf run;
    perf stat -x, lines are value,unit,event,..."""
    perf = {}
    suffix = "-%s.csv" % run
    for path in glob.glob(os.path.join(outdir, "latency-perf-*" + suffix)):
        tok = os.path.basename(path)[len("latency-perf-"):-len(suffix)]
        counts = {}
        for r in csv_rows(path):
            if len(r) >= 3 and r[0].replace(".", "").isdigit():
                counts[r[2].split(":")[0]] = float(r[0])
        if counts:
            perf[parse_size(tok)] = counts
    return perf


def read_bandwidth(path):
    """(bytes, kernel, threads) -> (best aggregate GB/s, per-thread min, max of the best rep)"""
    best = {}
    if not os.path.exists(path):
        return best
    reps = {}
    for r in csv_rows(path):
        if len(r) < 9 or r[0] not in ("read", "write", "copy") or r[3] == "best":
            continue
        key = (int(r[2]), r[0], int(r[1]))
        agg = float(r[6])
        if key not in reps or agg > reps[key][0]:
            reps[key] = (agg, float(r[7]), float(r[8]))
    return reps


def table(headers, rows):
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        print("| " + " | ".join(str(c) for c in row) + " |")
    print()


def main():
    args = sys.argv[1:]
    ghz = 2.8
    if "--ghz" in args:
        i = args.index("--ghz")
        ghz = float(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        sys.exit(__doc__)
    outdir = args[0]

    lat = read_latency(os.path.join(outdir, "latency.csv"))
    # Two perf runs per size with identical setup and different timed-load
    # counts: the difference of the counts over the difference of the loads
    # is the per-load rate of the timed chase alone.
    perf = {run: read_perf(outdir, run) for run in ("short", "long")}
    perf_loads = {run: {s: v[1] for s, v in read_latency(
        os.path.join(outdir, "latency-perfrun-%s.csv" % run)).items()} for run in ("short", "long")}
    bw = read_bandwidth(os.path.join(outdir, "bandwidth.csv"))

    print("## Latency (single thread, dependent loads, CPU pinned)\n")
    print("ns/load = best (minimum) over reps; cycles = ns x %.2f GHz; refills/load = "
          "(count_long - count_short) / (loads_long - loads_short) from the two perf runs, "
          "so setup and warm-up cancel.\n" % ghz)
    headers = ["size", "ns/load", "cycles"] + [e.replace("_cache_refill", "_refill") + "/load"
                                                for e in PERF_EVENTS if e not in ("cpu_cycles", "inst_retired")]
    rows = []
    for size in sorted(lat):
        ns, _ = lat[size]
        row = [fmt_size(size), "%.2f" % ns, "%.1f" % (ns * ghz)]
        c_short, c_long = perf["short"].get(size), perf["long"].get(size)
        l_short, l_long = perf_loads["short"].get(size), perf_loads["long"].get(size)
        for e in PERF_EVENTS:
            if e in ("cpu_cycles", "inst_retired"):
                continue
            if c_short and c_long and l_short and l_long and l_long > l_short \
                    and e in c_short and e in c_long:
                row.append("%.3f" % ((c_long[e] - c_short[e]) / (l_long - l_short)))
            else:
                row.append("n/a")
        rows.append(row)
    table(headers, rows)

    print("## Bandwidth (GB = 1e9 bytes; best aggregate over reps)\n")
    for bytes_ in sorted({k[0] for k in bw}):
        regime = REGIME_BY_BYTES.get(bytes_, "bytes=" + fmt_size(bytes_))
        print("### %s regime: %s per thread\n" % (regime, fmt_size(bytes_)))
        threads = sorted({k[2] for k in bw if k[0] == bytes_})
        headers = ["kernel"] + ["%dT agg" % t for t in threads] + ["%dT per-thr min..max" % t for t in threads]
        rows = []
        for kern in ("read", "write", "copy"):
            agg = ["%.1f" % bw[(bytes_, kern, t)][0] if (bytes_, kern, t) in bw else "n/a" for t in threads]
            per = ["%.1f..%.1f" % bw[(bytes_, kern, t)][1:] if (bytes_, kern, t) in bw else "n/a" for t in threads]
            rows.append([kern] + agg + per)
        table(headers, rows)

    print("## Levels summary\n")
    rows = []
    for name, lo, hi in LEVELS:
        picks = [lat[s][0] for s in lat if lo <= s <= hi]
        ns = min(picks) if picks else None
        lat_s = "%.2f ns (%.1f cycles)" % (ns, ns * ghz) if ns else "n/a (no size in %s..%s)" % (fmt_size(lo), fmt_size(hi))
        regime_bytes = [b for b, r in REGIME_BY_BYTES.items() if r == name]
        cells = [name, lat_s]
        for kern in ("read", "write", "copy"):
            keys = [k for k in bw if k[1] == kern and k[0] in regime_bytes]
            if not keys:
                cells.append("n/a")
                continue
            kmax = max(keys, key=lambda k: bw[k][0])
            ones = [k for k in keys if k[2] == 1]
            one = bw[ones[0]] if ones else None
            cells.append("%.1f @%dT, 1T=%s" % (bw[kmax][0], kmax[2], "%.1f" % one[0] if one else "n/a"))
        rows.append(cells)
    table(["level", "latency (best)", "read GB/s", "write GB/s", "copy GB/s"], rows)


if __name__ == "__main__":
    main()
