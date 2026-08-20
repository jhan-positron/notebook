#!/usr/bin/env python3
"""fence3 campaign analyzer (probe v10, tag 7600 = Fence 3 bracket).

Splits the old C.rest (callback end -> next layer-0 Q-wait) at the definitive
sync point (Fence 3 = listeners_notified.wait() return, model.hpp:3082-3083):

  cbF3  = 7600.end - 7400.end   listener count-downs + scheduler futex wake
  F3end = next q0.t0 - 7600.end single-threaded next-step construction
  F3wait= 7600.dur              scheduler wait (starts ~fence-2 return)

Boundary gap bracketing and decode filter are positional, same as
boundary_v7.py: gap = tag-2035 end -> next tag-0 t0, valid if 0 < gap < 50M
cycles and the tag-2035 end falls after the previous tag-0 record.

Hygiene (standing rules):
  - drop preamble records with t0 <= 1e12 (v9-style) before any processing
  - freeze filter: holes > 50 ms (135M cycles @ 2.7 GHz TSC) between
    consecutive records mark the draw as polluted; polluted draws are
    reported separately and excluded from fast4/slow4 + corr

Usage: fence3_split.py CAMPAIGN_ROOT [out_csv]
Reads  CAMPAIGN_ROOT/results.csv (TPS) + results/draw_*/kvwait.bin.
Writes per-draw CSV + prints summary (fast4/slow4 means, Pearson corr vs TPS).
corr = Pearson correlation of per-draw segment mean vs decode TPS across the
campaign's clean draws (-1 = longer exactly when slower, 0 = no relationship).
"""
import bisect
import csv
import os
import sys

import numpy as np

TSC_HZ = 2_700_000_000  # 3c51 tron cores CLOS3-capped 2.7 GHz; TSC 2.7 GHz
FREEZE_HOLE_CYC = int(0.050 * TSC_HZ)  # 50 ms
GAP_MAX_CYC = 50_000_000  # same decode-gap validity bound as boundary_v7.py

SEGS = ["A1", "A2", "B", "Cpre", "Ccb", "cbF3", "F3end", "F3wait", "Crest",
        "gap", "step", "F3period", "openF1", "F1wait", "F1F3",
        "F1wcls", "wclsF3"]


def load_recs(fn):
    raw = np.fromfile(fn, dtype=np.uint64)
    n = int(raw[0])
    recs = raw[1:1 + 3 * ((len(raw) - 1) // 3)].reshape(-1, 3)
    n = min(n, recs.shape[0])
    recs = recs[:n]
    recs = recs[recs[:, 0] > 10**12]  # drop v9-style preamble records
    return recs


def freeze_holes(recs):
    ts = np.sort(recs[:, 0])
    d = np.diff(ts)
    holes = d[d > FREEZE_HOLE_CYC]
    return len(holes), float(holes.sum()) / TSC_HZ * 1000.0  # count, total ms


def analyze_draw(fn):
    recs = load_recs(fn)
    t0 = recs[:, 0]
    dur = recs[:, 1]
    tag = recs[:, 2]

    nholes, holes_ms = freeze_holes(recs)

    def series(sel_tag, use_end=False):
        m = tag == sel_tag
        s = t0[m] + (dur[m] if use_end else 0)
        d = dur[m]
        order = np.argsort(s)
        return s[order].tolist(), d[order].tolist()

    q0s, _ = series(0)
    b35es, _ = series(2035, use_end=True)
    al_s, al_d = series(7100)
    fi_s, fi_d = series(7000)
    cb_s, cb_d = series(7400)
    f3_s, f3_d = series(7600)
    n7600 = len(f3_s)
    have_f3 = n7600 > 0  # validation mode on pre-v10 campaigns: no 7600 tags
    # Fence-1 stamps (v10b): the scheduler can ENTER the join wait before the
    # tag-2035 barrier end, so index 7601 records by their END timestamp.
    f1_e, f1_d = series(7601, use_end=True)
    n7601 = len(f1_e)
    have_f1 = n7601 > 0
    # TX dispatch instants (tag 3000+dev): the first one after Fence 1 is the
    # wcls launch — at F1 the hardware pipeline is empty, so it cuts F1->F3
    # into the serial enqueue/prepare part vs the streaming part.
    m3 = (tag >= 3000) & (tag < 3100)
    tx_s = np.sort(t0[m3]).tolist()

    per_gap = []  # rows of segment values, cycles
    nb_dropped = 0
    for qi in range(1, len(q0s)):
        g1 = q0s[qi]
        prev_q0 = q0s[qi - 1]
        bi = bisect.bisect_left(b35es, g1) - 1
        if bi < 0:
            continue
        g0 = b35es[bi]
        if not (prev_q0 < g0 < g1):
            continue
        if not (0 < g1 - g0 < GAP_MAX_CYC):
            continue
        i = bisect.bisect_left(al_s, g0)
        j = bisect.bisect_left(fi_s, g0)
        if not (i < len(al_s) and al_s[i] < g1
                and j < len(fi_s) and fi_s[j] < g1):
            nb_dropped += 1
            continue
        if have_f3:
            k3 = bisect.bisect_left(f3_s, g0)
            if not (k3 < len(f3_s) and f3_s[k3] < g1):
                nb_dropped += 1
                continue
        a0, ad = al_s[i], al_d[i]
        f0, fd = fi_s[j], fi_d[j]
        fe = f0 + fd
        k = bisect.bisect_left(cb_s, fe - 1000)
        if not (k < len(cb_s) and cb_s[k] < g1):
            nb_dropped += 1
            continue
        c0, cd = cb_s[k], cb_d[k]
        cbe = c0 + cd
        nan = float("nan")
        if have_f3:
            f30, f3dur = f3_s[k3], f3_d[k3]
            f3e = f30 + f3dur
            # Fence-3-to-Fence-3 period: one complete token cycle (phase 2 of
            # this window + next forward pass + phase 1 of next window). The
            # token cycle's only definitive sync point -> exact per-token total.
            if k3 + 1 < len(f3_s):
                period = (f3_s[k3 + 1] + f3_d[k3 + 1]) - f3e
                if not (0 < period < GAP_MAX_CYC):
                    period = nan
            else:
                period = nan
            f3_vals = dict(cbF3=f3e - cbe, F3end=g1 - f3e, F3wait=f3dur,
                           F3period=period)
        else:
            f3_vals = dict(cbF3=nan, F3end=nan, F3wait=nan, F3period=nan)
        f1_vals = dict(openF1=nan, F1wait=nan, F1F3=nan,
                       F1wcls=nan, wclsF3=nan)
        if have_f1 and have_f3:
            k1 = bisect.bisect_left(f1_e, g0)
            if k1 < len(f1_e) and f1_e[k1] < g1:
                f1e = f1_e[k1]
                f3e_this = f3_s[k3] + f3_d[k3]
                f1_vals.update(openF1=f1e - g0, F1wait=f1_d[k1],
                               F1F3=f3e_this - f1e)
                kw = bisect.bisect_left(tx_s, f1e)
                if kw < len(tx_s) and tx_s[kw] < f3e_this:
                    f1_vals.update(F1wcls=tx_s[kw] - f1e,
                                   wclsF3=f3e_this - tx_s[kw])
        vals = dict(
            A1=a0 - g0, A2=ad, B=fd, Cpre=max(0, c0 - fe), Ccb=cd,
            Crest=g1 - cbe, gap=g1 - g0, step=g1 - prev_q0,
            **f3_vals, **f1_vals)
        if any(v < 0 for v in vals.values()):
            nb_dropped += 1
            continue
        per_gap.append(vals)

    row = dict(nb=len(per_gap), dropped=nb_dropped, n7600=n7600, n7601=n7601,
               holes=nholes, holes_ms=round(holes_ms, 1))
    for s in SEGS:
        v = np.array([g[s] for g in per_gap], dtype=float)
        v = v[~np.isnan(v)]  # F3period is nan on the last gap
        row[s] = v.mean() if len(v) else float("nan")
        row[s + "_med"] = float(np.median(v)) if len(v) else float("nan")
        row[s + "_p90"] = float(np.percentile(v, 90)) if len(v) else float("nan")
    return row


def pearson(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def main():
    root = sys.argv[1]
    out_csv = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        root, "fence3-per-draw.csv")
    draws = []
    with open(os.path.join(root, "results.csv")) as f:
        for r in csv.DictReader(f):
            if r["status"] != "ok":
                print(f'{r["draw"]}: status={r["status"]} ({r["reason"]}) — skipped')
                continue
            kv = os.path.join(r["result_dir"], "kvwait.bin")
            if not os.path.isfile(kv):
                print(f'{r["draw"]}: kvwait.bin missing — skipped')
                continue
            row = analyze_draw(kv)
            row["draw"] = r["draw"]
            row["tps"] = float(r["generate_tok_s"])
            draws.append(row)
            print(f'{r["draw"]}: tps={row["tps"]:.3f} nb={row["nb"]} '
                  f'n7600={row["n7600"]} n7601={row["n7601"]} '
                  f'holes={row["holes"]} ({row["holes_ms"]}ms) '
                  f'dropped={row["dropped"]}')

    cols = (["draw", "tps", "nb", "dropped", "n7600", "n7601", "holes",
             "holes_ms"]
            + SEGS + [s + "_med" for s in SEGS] + [s + "_p90" for s in SEGS])
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in draws:
            w.writerow({c: row.get(c) for c in cols})
    print(f"wrote {out_csv}")

    clean = [d for d in draws if d["holes"] == 0]
    polluted = [d for d in draws if d["holes"] > 0]
    if polluted:
        print("\nFREEZE-POLLUTED (excluded from stats): "
              + ", ".join(f'{d["draw"]} ({d["holes"]} holes, {d["holes_ms"]}ms)'
                          for d in polluted))
    if len(clean) < 8:
        print(f"only {len(clean)} clean draws — fast4/slow4 unreliable")
    clean.sort(key=lambda d: d["tps"], reverse=True)
    fast4, slow4 = clean[:4], clean[-4:]
    tps = [d["tps"] for d in clean]
    print(f'\nclean draws: {len(clean)}, TPS {min(tps):.3f}-{max(tps):.3f}, '
          f'fast4 mean {np.mean([d["tps"] for d in fast4]):.3f}, '
          f'slow4 mean {np.mean([d["tps"] for d in slow4]):.3f}')
    dt = (TSC_HZ / np.mean([d["tps"] for d in slow4])
          - TSC_HZ / np.mean([d["tps"] for d in fast4]))
    print(f'TPS-derived delta: {dt/1000:.0f}k cycles/token slow4-vs-fast4')
    hdr = f'{"seg":8s} {"fast4":>10s} {"slow4":>10s} {"delta":>10s} {"corr":>6s}'
    print("\n" + hdr + "\n" + "-" * len(hdr))
    for s in SEGS:
        fm = np.mean([d[s] for d in fast4])
        sm = np.mean([d[s] for d in slow4])
        c = pearson([d[s] for d in clean], tps)
        print(f'{s:8s} {fm:10.0f} {sm:10.0f} {sm-fm:+10.0f} {c:6.2f}')
    ck = np.mean([d["cbF3"] + d["F3end"] - d["Crest"] for d in clean])
    print(f'\nreconciliation: mean(cbF3 + F3end - Crest) = {ck:.1f} cycles '
          f'(exact split of old C.rest by construction)')


if __name__ == "__main__":
    main()
