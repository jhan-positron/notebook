#!/usr/bin/env python3
"""peakbw campaign analysis (RUNBOOK-peakbw.md section 5).

Per draw:
  H1  DDR burst utilization: 10 ms CAS windows vs the in-campaign calibrated
      same-counter ceiling (per socket; worst socket reported).
  H2  RPQ pressure: occupancy per raw read-CAS (relative latency units,
      est. - inserts derived from cas_count_read; no RPQ_INSERTS encoding on
      GNR), compared against the saturation calibration reference.
  H0  CPU memory-bound share: topdown-mem-bound / slots on tron cores.
  H3  HBM fine windows (kvwait tags 8060-8066, device 0): read-duty
      distribution, coverage, and totals cross-check against the known
      per-token constants.

Usage: peakbw_analyze.py <campaign_root> <out_prefix>
Writes <out_prefix>-perdraw.csv and <out_prefix>-summary.json.
"""
import csv
import glob
import json
import os
import sys

import numpy as np

HBM_HZ = 368.75e6
TSC = 2.7e9
CAS_BYTES = 64  # perf scale unit per CAS count (nominal; ratios cancel)


def perf_rows(path):
    out = []
    for row in csv.reader(open(path)):
        if not row or row[0].startswith("#") or len(row) < 6:
            continue
        out.append(row)
    return out


def cas_series(path):
    """-> {socket: (t[], read_MiB[], write_MiB[])} per interval."""
    d = {}
    for r in perf_rows(path):
        t, sock, val, ev = float(r[0]), r[1], r[3], r[5]
        if "cas_count" not in ev:
            continue
        try:
            v = float(val)
        except ValueError:
            continue
        key = "read" if "read" in ev else "write"
        d.setdefault(sock, {}).setdefault(key, []).append((t, v))
    return d


def rpq_series(path):
    d = {}
    for r in perf_rows(path):
        t, sock, val, ev = float(r[0]), r[1], r[3], r[5]
        if "rpq_occ" not in ev:
            continue
        try:
            v = float(val)
        except ValueError:
            continue
        d.setdefault(sock, []).append((t, v))
    return d


def draw_metrics(dd, ceil_rate, sat_lat):
    m = {}
    cas = cas_series(os.path.join(dd, "ddr-cas-10ms.csv"))
    # H1: per-10ms utilization (worst socket)
    per_sock_util = {}
    per_sock_read = {}
    for sock, ch in cas.items():
        t = np.array([x[0] for x in ch["read"]])
        v = np.array([x[1] for x in ch["read"]])
        dt = np.diff(np.concatenate([[t[0] - 0.01], t]))
        dt[dt <= 0] = 0.01
        rate = v / dt  # MiB/s
        per_sock_util[sock] = rate / ceil_rate[sock]
        per_sock_read[sock] = (t, v)
    u = np.concatenate(list(per_sock_util.values()))
    worst = max(per_sock_util, key=lambda s: per_sock_util[s].max())
    uw = per_sock_util[worst]
    m.update(ddr_util_mean=float(u.mean()), ddr_util_p99=float(np.percentile(uw, 99)),
             ddr_util_max=float(uw.max()),
             ddr_windows_ge70=int((u >= 0.70).sum()), ddr_windows=int(u.size))
    # H2: occupancy per raw read CAS, 100 ms bins
    rpq = rpq_series(os.path.join(dd, "ddr-rpq-100ms.csv"))
    lat = []
    for sock, occ in rpq.items():
        if sock not in per_sock_read:
            continue
        ot = np.array([x[0] for x in occ])
        ov = np.array([x[1] for x in occ])
        rt, rv = per_sock_read[sock]
        # sum 10ms read MiB into each 100ms occupancy bin
        idx = np.searchsorted(ot, rt)
        reads = np.zeros(len(ot))
        for i, val in zip(idx, rv):
            if i < len(reads):
                reads[i] += val
        raw = reads * 1024 * 1024 / CAS_BYTES
        ok = raw > 1e5
        lat.append(ov[ok] / raw[ok])
    lat = np.concatenate(lat) if lat else np.array([np.nan])
    m.update(rpq_lat_mean=float(np.nanmean(lat)), rpq_lat_p99=float(np.nanpercentile(lat, 99)),
             rpq_lat_vs_sat=float(np.nanmean(lat) / sat_lat))
    # H0: memory-bound share
    slots = mem = 0.0
    for r in perf_rows(os.path.join(dd, "cpu-memstall.csv")):
        ev, val = r[3], r[1]
        try:
            v = float(val)
        except ValueError:
            continue
        if ev == "slots":
            slots += v
        elif ev == "topdown-mem-bound":
            mem += v
    m["cpu_membound_share"] = mem / slots if slots else float("nan")
    # H3: HBM fine windows, device 0
    raw = np.fromfile(os.path.join(dd, "kvwait.bin"), dtype=np.uint64)
    n = int(raw[0])
    r = raw[1:1 + 3 * ((raw.size - 1) // 3)].reshape(-1, 3)[:n].astype(np.int64)
    r = r[r[:, 0] > 10**12]
    groups = {}
    msk = (r[:, 2] >= 8060) & (r[:, 2] <= 8066)
    for t0, dur, tag in r[msk]:
        groups.setdefault(int(t0), {})[int(tag) - 8060] = int(dur)
    g = sorted((t, f) for t, f in groups.items() if len(f) == 7)
    if not g:  # control draws: window mode off
        m["hbm_windows"] = 0
        m["hbm_burst_maxlen_ge50"] = 0
        return m
    ht = np.array([f[0] for _, f in g], dtype=float)
    hr = np.array([f[1] for _, f in g], dtype=float)
    ok = ht > 0
    duty = hr[ok] / ht[ok]
    ts = np.array([t for t, _ in g], dtype=float)[ok]
    span = (ts.max() - ts.min()) / TSC
    m.update(hbm_windows=int(duty.size),
             hbm_win_us_mean=float((ht[ok] / HBM_HZ).mean() * 1e6),
             hbm_duty_mean=float(hr[ok].sum() / ht[ok].sum()),
             hbm_duty_p99=float(np.percentile(duty, 99)),
             hbm_duty_max=float(duty.max()),
             hbm_windows_ge90=int((duty >= 0.90).sum()),
             hbm_coverage=float(ht[ok].sum() / HBM_HZ / span),
             hbm_read_total=float(hr[ok].sum()))
    # burst length: consecutive windows above 50% duty
    hi = duty >= 0.50
    best = cur = 0
    for x in hi:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    m["hbm_burst_maxlen_ge50"] = int(best)
    return m


def main():
    root, outp = sys.argv[1], sys.argv[2]
    # calibration: plateau per-socket read rate + saturation latency units
    cal = cas_series(os.path.join(root, "ceiling-imc-rpq.csv"))
    calr = rpq_series(os.path.join(root, "ceiling-imc-rpq.csv"))
    ceil_rate, sat_lats = {}, []
    for sock, ch in cal.items():
        v = np.array([x[1] for x in ch["read"]])
        top = np.sort(v)[-8:]  # plateau seconds
        ceil_rate[sock] = float(top.mean())  # MiB per ~1s interval
        occ = np.array([x[1] for x in calr[sock]])
        occ_top = np.sort(occ)[-8:].mean()
        sat_lats.append(occ_top / (top.mean() * 1024 * 1024 / CAS_BYTES))
    sat_lat = float(np.mean(sat_lats))
    tps = {}
    for row in csv.DictReader(open(os.path.join(root, "results.csv"))):
        if row["status"] == "ok":
            tps[row["draw"]] = float(row["generate_tok_s"])
    rows = []
    for dd in sorted(glob.glob(os.path.join(root, "results", "*"))):
        name = os.path.basename(dd)
        if name not in tps:
            continue
        m = draw_metrics(dd, ceil_rate, sat_lat)
        m["draw"] = name
        m["tps"] = tps[name]
        m["is_control"] = name.startswith("control")
        rows.append(m)
        print(f"{name} tps={m['tps']:.1f} ddr_util mean={m['ddr_util_mean']:.3f} "
              f"p99={m['ddr_util_p99']:.3f} max={m['ddr_util_max']:.3f} ge70={m['ddr_windows_ge70']} | "
              f"rpq_lat/sat={m['rpq_lat_vs_sat']:.3f} | membound={m['cpu_membound_share']:.3f} | "
              f"hbm duty mean={m.get('hbm_duty_mean', float('nan')):.3f} "
              f"p99={m.get('hbm_duty_p99', float('nan')):.3f} max={m.get('hbm_duty_max', float('nan')):.3f} "
              f"ge90={m.get('hbm_windows_ge90', -1)} cover={m.get('hbm_coverage', float('nan')):.3f}")
    keys = sorted({k for r in rows for k in r})
    with open(outp + "-perdraw.csv", "w") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    summary = {"ceiling_rate_MiB_s": ceil_rate, "saturation_lat_units": sat_lat}
    json.dump(summary, open(outp + "-summary.json", "w"), indent=1)
    print("saturation reference (occ per raw read CAS):", round(sat_lat, 3))


if __name__ == "__main__":
    main()
