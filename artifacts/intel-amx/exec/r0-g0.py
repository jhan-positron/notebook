#!/usr/bin/env python3
"""G0 gate computation (pre-registered: exec/results/router/G0-preregistration.md).

Inputs:
  - analysis-u{U}-ctx{CTX}.json (r0-analyze.py v3): A_stall_ns[], T_step_ns[], M[]
  - p0b-microbench.txt: RESULT lines in rep blocks
      rep 1 header: "# P0b router-kernel microbench"
      reps 2/3:     "# P0b realistic-regime repetition N"

Rules (verbatim from the pre-registration):
  1. STOP if upper 95% bootstrap bound of mean g(s) < 1% in ALL four configs,
     g(s) = (A(s) - C(s)) / T_step(s),
     C(s) = L * t_bench(best CPU arm, n, M(s), cyclic) [mean of 3 reps;
     sensitivity row: max of 3 and disrupted regime].
  2. AMX candidacy: adv = t_bestAVX - t_AMX at the measured M distribution;
     proceed with AMX only if upper bound of adv >= 0.10 * t_bestAVX
     OR L * adv >= 0.005 * median T_step.
Bootstrap: 10,000 resamples, percentile method, seed 20260823.
"""
import argparse
import json
import random
import statistics
import sys

OUT = "/home/jhan/workspace/intel-AMX/exec/results/router"
MB = OUT + "/p0b-microbench.txt"
_ap = argparse.ArgumentParser()
_ap.add_argument("--model", choices=["20b", "120b"], default="20b")
_args = _ap.parse_args()
if _args.model == "20b":
    L, N, PREFIX = 24, 32, "analysis"
else:
    L, N, PREFIX = 36, 128, "analysis120b"
CONFIGS = [(1, 2048), (1, 8192), (8, 2048), (8, 8192)]
ARMS = ["avx_fp32", "avx_bf16", "amx_bf16"]
MS = [1, 2, 4, 8, 16]


def parse_bench():
    """-> cells[(arm,n,m,regime)] = [us_per_layer_call per rep]"""
    cells = {}
    rep = None
    for line in open(MB):
        if line.startswith("# P0b router-kernel microbench"):
            rep = 1
        elif line.startswith("# P0b realistic-regime repetition"):
            rep = int(line.split("repetition")[1].split(",")[0])
        elif line.startswith("RESULT"):
            kv = dict(x.split("=", 1) for x in line.split()[1:])
            if int(kv["workers"]) != 1:
                continue
            key = (kv["arm"], int(kv["n"]), int(kv["m"]), kv["regime"])
            cells.setdefault(key, []).append(float(kv["us_per_layer_call"]))
    return cells


def t_interp(cells, arm, n, m, regime, agg):
    """us for fractional m by linear interpolation over measured M points."""
    pts = []
    for mm in MS:
        v = cells.get((arm, n, mm, regime))
        if v:
            pts.append((mm, agg(v)))
    if not pts:
        return None
    if m <= pts[0][0]:
        return pts[0][1]
    for (m0, v0), (m1, v1) in zip(pts, pts[1:]):
        if m0 <= m <= m1:
            return v0 + (v1 - v0) * (m - m0) / (m1 - m0)
    return pts[-1][1]


def bootstrap_ci(vals, stat=statistics.mean, n=10000, seed=20260823):
    rng = random.Random(seed)
    k = len(vals)
    res = sorted(stat([vals[rng.randrange(k)] for _ in range(k)]) for _ in range(n))
    return res[int(0.025 * n)], res[int(0.975 * n)]


def main():
    cells = parse_bench()
    reps_ok = all(len(cells.get(("avx_bf16", 32, m, "cyclic"), [])) >= 3 for m in MS)
    print("# bench cells parsed: %d keys; 3-rep coverage on realistic cells: %s"
          % (len(cells), reps_ok))
    if not reps_ok:
        print("# WARN: <3 reps on some realistic cells — CI degraded, reported as range")

    overall_pass = False
    rows = []
    amx_inputs = []
    for U, CTX in CONFIGS:
        f = "%s/%s-u%d-ctx%d.json" % (OUT, PREFIX, U, CTX)
        try:
            d = json.load(open(f))
        except FileNotFoundError:
            print("MISSING %s — config skipped (report as gap)" % f)
            continue
        A = d["A_stall_ns"]
        T = d["T_step_ns"]
        M = [m if m is not None else float(U) for m in d["M"]]
        med_T = statistics.median(T)

        # best CPU arm at this config's M distribution (mean-of-reps, cyclic)
        arm_cost = {}
        for arm in ARMS:
            per_step = [t_interp(cells, arm, N, m, "cyclic", statistics.mean)
                        for m in M]
            if None in per_step:
                continue
            arm_cost[arm] = per_step
        if not arm_cost:
            print("FATAL: no bench data for any arm"); sys.exit(2)
        best_arm = min(arm_cost, key=lambda a: statistics.mean(arm_cost[a]))

        def gseries(agg, regime):
            g = []
            for a, t, m in zip(A, T, M):
                tb = t_interp(cells, best_arm, N, m, regime, agg)
                c_ns = L * tb * 1000.0
                g.append((a - c_ns) / t)
            return g

        g_primary = gseries(statistics.mean, "cyclic")
        lo, hi = bootstrap_ci(g_primary)
        g_sens = gseries(max, "disrupted")
        lo_s, hi_s = bootstrap_ci(g_sens)
        dec = "PROCEED-ELIGIBLE" if hi >= 0.01 else "below-threshold"
        if hi >= 0.01:
            overall_pass = True
        # --- corrected gate (pre-reg DEVIATION section): the driving-thread
        # block lands at "start_reading topk_snd_channel"; A_corr sums
        # stall + topk_read + wait_indices. CPU-world residual block R is
        # modeled from the measured helper kernel-entry offset E and the
        # across-workers topk span SP (both meas), with the CPU router's
        # logits available at t_cpu(M) (+2us channel ops in the primary
        # variant; +0 in the conservative variant).
        AC = d.get("A_corr_ns")
        g_corr = g_corr_ci = g_cons_ci = None
        if AC:
            eo, sp = [], []
            for st in d["per_step_layers"]:
                for r in st:
                    if r.get("helper_entry_off") is not None:
                        eo.append(r["helper_entry_off"] / 1000.0)
                    if r.get("topk_start") and r.get("topk_end"):
                        sp.append((r["topk_end"] - r["topk_start"]) / 1000.0)
            E = statistics.mean(eo) if eo else 0.0
            SP = statistics.mean(sp) if sp else 0.5

            def corr_series(extra_arrival):
                g = []
                for ac, t, m in zip(AC, T, M):
                    tc = t_interp(cells, best_arm, N, m, "cyclic", statistics.mean)
                    r_us = max(0.0, E + SP - (tc + extra_arrival))
                    g.append((ac - L * tc * 1000.0 - L * r_us * 1000.0) / t)
                return g

            g_corr = corr_series(2.0)
            g_corr_ci = bootstrap_ci(g_corr)
            g_cons_ci = bootstrap_ci(corr_series(0.0))
            print("  corrected [DEVIATION]: A_corr=%.0fus E=%.1fus SP=%.1fus | "
                  "g_corr mean=%.3f%% CI95=[%.3f%%, %.3f%%] | conservative "
                  "CI95=[%.3f%%, %.3f%%] -> %s"
                  % (statistics.mean(AC) / 1000, E, SP,
                     100 * statistics.mean(g_corr), 100 * g_corr_ci[0],
                     100 * g_corr_ci[1], 100 * g_cons_ci[0], 100 * g_cons_ci[1],
                     "PROCEED-ELIGIBLE(corr)" if g_corr_ci[1] >= 0.01 else "below-threshold(corr)"))

        rows.append(dict(cfg="u%d/ctx%d" % (U, CTX), steps=len(A),
                         best_arm=best_arm,
                         A_us=statistics.mean(A) / 1000,
                         T_us=statistics.mean(T) / 1000,
                         M_mean=statistics.mean(M),
                         g_mean=statistics.mean(g_primary), g_lo=lo, g_hi=hi,
                         g_sens_mean=statistics.mean(g_sens), g_sens_hi=hi_s,
                         g_corr_mean=(statistics.mean(g_corr) if g_corr else None),
                         g_corr_ci=g_corr_ci, g_cons_ci=g_cons_ci,
                         decision=dec))
        print("%-12s steps=%d best_arm=%s A=%.1fus T=%.1fus M=%.2f | "
              "g mean=%.4f%% CI95=[%.4f%%, %.4f%%] | sens(max,disrupted) "
              "g=%.4f%% hi=%.4f%% | %s"
              % (rows[-1]["cfg"], len(A), best_arm, rows[-1]["A_us"],
                 rows[-1]["T_us"], rows[-1]["M_mean"],
                 100 * rows[-1]["g_mean"], 100 * lo, 100 * hi,
                 100 * rows[-1]["g_sens_mean"], 100 * hi_s, dec))
        amx_inputs.append((M, med_T))

    print()
    if overall_pass:
        print("G0 RULE 1: at least one config has upper95(g) >= 1%% -> gate OPEN")
    else:
        print("G0 RULE 1: upper95(g) < 1% in ALL analyzed configs -> STOP "
              "(write numbers into rampup doc, close item, hand trace to "
              "FPGA team / Note [Expert matmuls] owners)")

    # Rule 2: AMX vs best-AVX at the measured M distributions (only meaningful
    # if rule 1 opened the gate; computed and reported regardless).
    all_M = [m for Ms_, _ in amx_inputs for m in Ms_]
    med_T_all = statistics.median([t for _, t in amx_inputs]) if amx_inputs else 0
    if all_M:
        def arm_at_dist(arm, regime, agg):
            vals = [t_interp(cells, arm, N, m, regime, agg) for m in all_M]
            return statistics.mean(vals) if None not in vals else None

        for regime in ("cyclic", "disrupted"):
            t_amx_mean = arm_at_dist("amx_bf16", regime, statistics.mean)
            t_amx_min = arm_at_dist("amx_bf16", regime, min)
            best_avx = None
            for arm in ("avx_fp32", "avx_bf16"):
                v = arm_at_dist(arm, regime, statistics.mean)
                if v is not None and (best_avx is None or v < best_avx[1]):
                    best_avx = (arm, v, arm_at_dist(arm, regime, max))
            if t_amx_mean is None or best_avx is None:
                continue
            adv_mean = best_avx[1] - t_amx_mean
            adv_upper = best_avx[2] - t_amx_min  # conservative range bound
            thr1 = 0.10 * best_avx[1]
            thr2_us = 0.005 * med_T_all / 1000.0 / L  # per-layer threshold
            verdict = ("AMX-CANDIDATE" if (adv_upper >= thr1 or adv_upper >= thr2_us)
                       else "AVX-ONLY (defer P1b)")
            print("G0 RULE 2 [%s]: bestAVX=%s %.2fus amx=%.2fus adv=%.2fus "
                  "(upper %.2f) thr10%%=%.2fus thr0.5%%step=%.2fus/layer -> %s"
                  % (regime, best_avx[0], best_avx[1], t_amx_mean, adv_mean,
                     adv_upper, thr1, thr2_us, verdict))

    outname = "g0-decision.json" if _args.model == "20b" else "g0-decision-120b.json"
    with open("%s/%s" % (OUT, outname), "w") as f:
        json.dump({"model": _args.model, "rows": rows, "gate_open": overall_pass},
                  f, indent=1)
    print("wrote %s/%s" % (OUT, outname))


if __name__ == "__main__":
    main()
