"""Reader for the run 5c L1 bandwidth files (bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv).

Each file holds one core's read and write kernels at 4, 8, 16 and 24 KiB, with the perf columns.
Per size the time of one pass is total_bytes / (aggregate_GBps * 1e9) / passes (elapsed_s has only
6 decimals, a 1 us step on a 30 us span, so it is not used). A straight line t_pass = a + b * bytes
over the four sizes gives a = the fixed cost per pass (ns) and 1 / b = the L1 rate (GB/s).
Reading rules from follow-up-run-plan.md section 12: fit residual under 2 % of the smallest pass
time; l1d_refill_per_line below 0.01 marks a row the L1 served.
Standard library only, so it runs under python3 -I on files from another machine.
"""
import re, sys, os

PERF = ("cycles_per_line", "l1d_refill_per_line", "l2d_refill_per_line", "l3d_refill_rd_per_line",
        "l1d_refill_hwprf_per_line", "l2d_refill_hwprf_per_line", "l2d_refill_l1dhwprf_per_line", "perf_cov")
L1_REFILL_MAX = 0.01     # refills per line at or above this: not an L1 row
RESID_MAX = 0.02         # fit residual as a share of the smallest pass time
SLOW_STATE = 0.02        # asm form: best rep's cycles per line at 16 and 24 KiB this much above the 4 and 8 KiB mean = slow-state row


def read_l1(path):
    """every numbered rep as a dict; the file's 'best' rows are checked against the reps, not kept"""
    out, meta, cols = [], {}, None
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("# bandwidth"):
            meta = dict(re.findall(r"(\w+)=(\S+)", line)); continue
        if line.startswith("#"): continue
        if line.startswith("mem,"):
            cols = line.split(","); continue
        f = dict(zip(cols, line.split(",")))
        key = (f["kernel"], int(f["bytes_per_thread"]))
        if f["rep"] == "best":
            reps = [d for d in out if (d["kernel"], d["size"]) == key]
            assert abs(max(d["agg"] for d in reps) - float(f["aggregate_GBps"])) < 5e-4, (path, key)
            continue
        passes = int(meta["passes"]); size = int(f["bytes_per_thread"]); agg = float(f["aggregate_GBps"])
        d = dict(kernel=f["kernel"], size=size, rep=int(f["rep"]), passes=passes, agg=agg,
                 asm_passes=meta.get("asm_passes") == "1", backing=None,
                 t_pass_ns=int(f["total_bytes"]) / (agg * 1e9) / passes * 1e9,
                 bytes_per_cycle=64.0 / float(f["cycles_per_line"]))
        for c in PERF: d[c] = float(f[c])
        assert int(f["total_bytes"]) == size * passes, (path, key)
        out.append(d)
    return out


def best_reps(rows):
    """(kernel, size) -> the fastest numbered rep"""
    out = {}
    for d in rows:
        k = (d["kernel"], d["size"])
        if k not in out or d["agg"] > out[k]["agg"]: out[k] = d
    return out


def fit(points):
    """least squares t = a + b * x over (x, t) pairs; returns a, b and the largest |residual|"""
    n = len(points); sx = sum(x for x, _ in points); st = sum(t for _, t in points)
    sxx = sum(x * x for x, _ in points); sxt = sum(x * t for x, t in points)
    b = (n * sxt - sx * st) / (n * sxx - sx * sx); a = (st - b * sx) / n
    return a, b, max(abs(t - (a + b * x)) for x, t in points)


def summarize(path):
    rows = read_l1(path); bests = best_reps(rows)
    form = "all passes in one assembly call" if rows[0]["asm_passes"] else "one call per pass"
    print(f"{os.path.basename(path)}: {form}, {len(rows)} reps, sizes {sorted(set(d['size'] for d in rows))}")
    result = {}
    for kernel in (k for k in ("read", "write") if any(d["kernel"] == k for d in rows)):
        pts = sorted((d["size"], d["t_pass_ns"]) for (k, _), d in bests.items() if k == kernel)
        a, b, resid = fit(pts)
        t_min = min(t for _, t in pts)
        ok = resid < RESID_MAX * t_min
        print(f"  {kernel}: per-pass cost {a:.1f} ns, L1 rate {1 / b:.1f} GB/s, largest residual {resid:.2f} ns "
              f"of {t_min:.1f} ns smallest pass ({100 * resid / t_min:.1f} %, rule {'met' if ok else 'NOT met'})")
        spread = {}
        for size, t in pts:
            d = bests[(kernel, size)]
            l1 = "L1 row" if d["l1d_refill_per_line"] < L1_REFILL_MAX else "not L1"
            reps = [r["agg"] for r in rows if r["kernel"] == kernel and r["size"] == size]
            spread[size] = (max(reps) - min(reps)) / d["agg"]   # rep spread as a share of the best rep (the run 5c reading rule)
            print(f"    {size // 1024:3d} KiB: {d['agg']:7.1f} GB/s, {t:7.1f} ns per pass, {d['cycles_per_line']:.2f} cycles per line "
                  f"({d['bytes_per_cycle']:.0f} B per cycle), l1d_refill {d['l1d_refill_per_line']:.4f} per line, {l1}, perf_cov {d['perf_cov']:.3f}, "
                  f"{len(reps)} reps spread {100 * spread[size]:.1f} % of best")
        slow = {}
        if rows[0]["asm_passes"] and all((kernel, s) in bests for s in (4096, 8192, 16384, 24576)):
            # the asm form's second check (plan section 12): a best rep that runs more cycles per line than the small rows is a slow-state row, not an L1 limit
            ref = (bests[(kernel, 4096)]["cycles_per_line"] + bests[(kernel, 8192)]["cycles_per_line"]) / 2
            for size in (16384, 24576):
                slow[size] = bests[(kernel, size)]["cycles_per_line"] / ref - 1
                print(f"    slow-state check {size // 1024} KiB: best rep {bests[(kernel, size)]['cycles_per_line']:.2f} cycles per line against {ref:.2f} at 4 and 8 KiB, "
                      f"{100 * slow[size]:+.1f} % ({'slow-state row' if slow[size] > SLOW_STATE else 'L1 rate'})")
        result[kernel] = dict(a_ns=a, rate_gbps=1 / b, resid_ns=resid, resid_ok=ok, spread=spread, slow_state=slow,
                              rows={size: bests[(kernel, size)] for size, _ in pts})
    return result


if __name__ == "__main__":
    forms = {}   # (asm_passes, kernel) -> fit, over every file given
    for p in sys.argv[1:]:
        r = summarize(p)
        for kernel, v in r.items(): forms[(read_l1(p)[0]["asm_passes"], kernel)] = v
    # plan section 12: the per-pass intercept is the whole boundary, the asm intercept the loop-exit part; their difference is call + return + register save
    for kernel in ("read", "write"):
        if (False, kernel) in forms and (True, kernel) in forms:
            f1, f2 = forms[(False, kernel)], forms[(True, kernel)]
            if f1["resid_ok"] and f2["resid_ok"]:
                print(f"{kernel}: per-pass intercept {f1['a_ns']:.1f} ns, asm intercept {f2['a_ns']:.1f} ns, difference {f1['a_ns'] - f2['a_ns']:.1f} ns = call + return + register save per pass")
            else:
                print(f"{kernel}: intercept difference not quoted, the residual rule failed on the {'per-pass' if not f1['resid_ok'] else 'asm'} fit")
