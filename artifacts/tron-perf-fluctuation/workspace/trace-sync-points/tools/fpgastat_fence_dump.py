#!/usr/bin/env python3
"""Per-token fence-flip FPGA counter dump for one draw's kvwait.bin (arm B).

Implements the analysis rules pre-registered in RUNBOOK-fpgastat-armB.md §3:
  - count-prefixed (t0,dur,tag) parse with truncation rejection;
  - preamble drop (t0 <= 1e12);
  - closing-fence ownership: a +20 group closed at F3_i belongs to
    [F1_i -> F3_i] of token i; a +40 group closed at F1_i belongs to
    [F3_(i-1) -> F1_i] (REST-OF-CYCLE, not the intra-pass span);
  - first +40 group per device dropped (no matching window start);
  - per-field completeness (7 fields) required per (token, dev, seg);
  - counter invariants and clock-identity residuals per group;
  - freeze detection (>50 ms holes between consecutive F3 stamps);
  - decode flag (a tag-0 layer-0 record inside the rest-of-cycle window).

Output: <out>.csv (one row per token x device x segment, absolute cycles AND
shares) and <out>.validation.json (machine-readable summary + exposure-
weighted aggregates: ratios of sums, not means of ratios).

Usage: fpgastat_fence_dump.py kvwait.bin out_prefix
"""
import json
import sys

import numpy as np

TSC_HZ = 2.700e9        # validated on 3bda
MM_HZ = 550.0e6
HBM_HZ = 368.75e6
PREAMBLE_TSC = 10**12
FREEZE_HOLE_S = 0.050
SAT32 = 2**32 - 1
FIELDS = ("hbm_timer", "hbm_read", "mm_timer", "mm_bp",
          "mm_in_prog", "mm_rmem_bp", "mm_wmem_bp")
SEGS = {20: "f1f3", 40: "restcycle"}
NDEV = 4


def load(path):
    raw = np.fromfile(path, dtype=np.uint64)
    if raw.size < 4:
        sys.exit("FAIL kvwait.bin missing or empty")
    n = int(raw[0])
    body = raw[1:1 + 3 * ((raw.size - 1) // 3)].reshape(-1, 3)
    if body.shape[0] < n:
        sys.exit(f"FAIL truncated: header count {n}, present {body.shape[0]}")
    recs = body[:n]
    return recs[recs[:, 0] > PREAMBLE_TSC].astype(np.int64)


def fence_groups(recs, seg):
    """(t0, dev, seg) -> {field: value}; returns per-dev list sorted by t0."""
    out = [dict() for _ in range(NDEV)]
    m = (recs[:, 2] >= 8000) & (recs[:, 2] < 8000 + NDEV * 100)
    for t0, dur, tag in recs[m]:
        rel = int(tag) - 8000
        dev, off = divmod(rel, 100)
        if not (seg <= off < seg + 7):
            continue
        out[dev].setdefault(int(t0), {})[off - seg] = int(dur)
    return [sorted(d.items()) for d in out]


def main():
    kvwait, out_prefix = sys.argv[1], sys.argv[2]
    recs = load(kvwait)
    t0, dur, tag = recs[:, 0], recs[:, 1], recs[:, 2]

    f1 = np.stack([t0[tag == 7601], t0[tag == 7601] + dur[tag == 7601]], 1)
    f1 = f1[np.argsort(f1[:, 0])]           # columns: start, end
    f3 = np.sort(t0[tag == 7600])
    q0 = np.sort(t0[tag == 0])              # layer-0 starts (decode marker)
    ntok = min(len(f1), len(f3))
    if ntok < 100:
        sys.exit(f"FAIL too few fences: F1={len(f1)} F3={len(f3)}")

    holes = int(np.sum(np.diff(f3) / TSC_HZ > FREEZE_HOLE_S))

    g20 = fence_groups(recs, 20)
    g40 = fence_groups(recs, 40)

    val = {"tokens": ntok, "freeze_holes_over_50ms": holes,
           "f1_count": len(f1), "f3_count": len(f3),
           "dropped_incomplete": 0, "dropped_misaligned": 0,
           "invariant_violations": 0, "saturated_timers": 0,
           "group_counts": {f"dev{d}": {"+20": len(g20[d]), "+40": len(g40[d])}
                            for d in range(NDEV)}}
    rows = []

    for dev in range(NDEV):
        for segoff, groups, fences in ((20, g20[dev], f3),
                                       (40, g40[dev], f1[:, 1])):
            seg = SEGS[segoff]
            for i in range(min(len(groups), ntok)):
                gt0, fields = groups[i]
                if segoff == 40 and i == 0:
                    continue                       # no matching window start
                if len(fields) != 7:
                    val["dropped_incomplete"] += 1
                    continue
                # ordinal join sanity: flip must follow its closing fence and
                # precede the next same-type fence.
                fence_t = int(fences[i])
                nxt = int(fences[i + 1]) if i + 1 < len(fences) else None
                # +40 closes at F1_i: flip(1) runs after the 7601 stamp but
                # before the same token's F3 stamp.
                hi = int(f3[i]) if segoff == 40 and i < len(f3) else nxt
                if gt0 < fence_t or (hi is not None and gt0 >= hi):
                    val["dropped_misaligned"] += 1
                    continue
                f = [fields[k] for k in range(7)]
                hbm_t, hbm_r, mm_t, mm_bp, mm_ip, mm_rbp, mm_wbp = f
                if mm_t in (0, SAT32) or hbm_t in (0, SAT32):
                    val["saturated_timers"] += 1
                    continue
                bad = (hbm_r > hbm_t or mm_ip > mm_t or mm_bp > mm_t)
                # rmem+wmem approximate split may slightly exceed mm_bp
                # (documented) — not an invariant violation.
                if bad:
                    val["invariant_violations"] += 1
                    continue
                if segoff == 20:
                    wall = (int(f3[i]) - int(f1[i, 1])) / TSC_HZ
                    rc_lo, rc_hi = int(f1[i, 1]), int(f3[i])
                else:
                    wall = (int(f1[i, 1]) - int(f3[i - 1])) / TSC_HZ
                    rc_lo, rc_hi = int(f3[i - 1]), int(f1[i, 1])
                j = np.searchsorted(q0, rc_lo)
                decode = int(j < len(q0) and q0[j] < rc_hi)
                mm_s, hbm_s = mm_t / MM_HZ, hbm_t / HBM_HZ
                rows.append((i, dev, seg, hbm_t, hbm_r, mm_t, mm_bp, mm_ip,
                             mm_rbp, mm_wbp, wall, mm_s, hbm_s,
                             (mm_s - wall) * 1e6, (hbm_s - mm_s) * 1e6,
                             mm_ip / mm_t, mm_bp / mm_t, mm_wbp / mm_t,
                             mm_rbp / mm_t, hbm_r / hbm_t, decode))

    hdr = ("token_ix,dev,seg,hbm_timer,hbm_read,mm_timer,mm_bp,mm_in_prog,"
           "mm_rmem_bp,mm_wmem_bp,wall_s,mm_timer_s,hbm_timer_s,"
           "residual_mm_vs_wall_us,residual_hbm_vs_mm_us,"
           "share_in_prog,share_bp,share_wmem_bp,share_rmem_bp,hbm_duty,decode")
    with open(out_prefix + ".csv", "w") as fh:
        fh.write(hdr + "\n")
        for r in rows:
            fh.write(",".join(f"{x:.6g}" if isinstance(x, float) else str(x)
                              for x in r) + "\n")

    # exposure-weighted aggregates: ratios of sums (pre-registered rule)
    agg = {}
    for dev in range(NDEV):
        for seg in SEGS.values():
            sel = [r for r in rows if r[1] == dev and r[2] == seg]
            if not sel:
                continue
            s = lambda ix: float(sum(r[ix] for r in sel))
            agg[f"dev{dev}.{seg}"] = {
                "tokens": len(sel),
                "share_in_prog": s(7) / s(5),
                "share_bp": s(6) / s(5),
                "share_wmem_bp": s(9) / s(5),
                "hbm_duty": s(4) / s(3),
                "median_residual_mm_vs_wall_us":
                    float(np.median([r[13] for r in sel])),
            }
    val["exposure_weighted"] = agg
    with open(out_prefix + ".validation.json", "w") as fh:
        json.dump(val, fh, indent=1)
    print(json.dumps({k: v for k, v in val.items()
                      if k != "exposure_weighted"}, indent=1))
    for k, v in agg.items():
        print(k, {kk: round(vv, 4) for kk, vv in v.items()})


if __name__ == "__main__":
    main()
