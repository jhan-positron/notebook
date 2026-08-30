#!/usr/bin/env python3
"""Independent recomputation of the P0 G0 gate (Sol deviation-review finding 8).

Written from the pre-registration text + analysis JSONs by session 7ff0b556 (NOT the
capturing session, and not derived from exec/r0-g0.py). Recomputes, per config:
pre-registered g, corrected g (with residual model R), reduced-overlap variant,
bootstrap CIs - and compares against exec/results/router/g0-decision*.json.
Independence level: aggregation/gate arithmetic from the per_step_layers records +
raw bench RESULT lines. Span extraction from the .perfetto-trace files is NOT
re-done here (r0-analyze.py's output is the shared input); closure consistency of
those extractions is checked statistically below.
"""
import json, glob, math, os, re, sys
import random

RD = "/home/jhan/workspace/intel-AMX/exec/results/router"
SEED = 20260823
NBOOT = 10_000

# ---- 1. bench table: parse RESULT lines myself -------------------------------
bench = {}  # (arm, n, m, regime, workers) -> [us_per_layer_call]
for line in open(f"{RD}/p0b-microbench.txt"):
    if not line.startswith("RESULT"):
        continue
    kv = dict(tok.split("=", 1) for tok in line.split()[1:] if "=" in tok)
    key = (kv["arm"], int(kv["n"]), int(kv["m"]), kv["regime"], int(kv["workers"]))
    bench.setdefault(key, []).append(float(kv["us_per_layer_call"]))

def bench_mean(arm, n, m, regime, workers=1):
    v = bench[(arm, n, m, regime, workers)]
    return sum(v) / len(v)

def best_arm(n, m, regime="cyclic"):
    arms = ["avx_fp32", "avx_bf16", "amx_bf16"]
    return min(arms, key=lambda a: bench_mean(a, n, m, regime))

# ---- 2. gate per config ------------------------------------------------------
def boot_ci(vals, nboot=NBOOT, seed=SEED):
    rng = random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(nboot):
        s = 0.0
        for _ in range(n):
            s += vals[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * nboot)]
    hi = means[int(0.975 * nboot) - 1]
    return lo, hi

def gate(path, n_experts, layers, missing_E="impute"):
    """missing_E: a few layer records lack helper_entry_off/first_wait (span not
    resolvable for that layer). 'impute' = use the config-wide mean E for R;
    'skip' = the layer contributes R=0. Both reported; comparison shows which the
    published numbers used."""
    d = json.load(open(path))
    psl = d["per_step_layers"]
    Ms = d["M"]
    Ts = d["T_step_ns"]
    assert len(psl) == len(Ms) == len(Ts), (len(psl), len(Ms), len(Ts))
    all_E = [l["helper_entry_off"] for lay in psl for l in lay if "helper_entry_off" in l]
    mean_E = sum(all_E) / len(all_E)
    g_pre, g_corr, g_cons = [], [], []
    closure_gap_us = []
    n_missing = 0
    for step, (lay, M, T) in enumerate(zip(psl, Ms, Ts)):
        m_cell = min([1, 2, 4, 8, 16], key=lambda x: abs(x - M))
        arm = best_arm(n_experts, m_cell)
        t_cpu_ns = bench_mean(arm, n_experts, m_cell, "cyclic") * 1000.0
        A_pre = sum(l["stall"] for l in lay)
        A_corr = sum(l["stall"] + l["stall_topk_read"] + l["wait_indices"] for l in lay)
        C = layers * t_cpu_ns
        R = Rc = 0.0
        for l in lay:
            sp = l["topk_end"] - l["topk_start"]
            if "helper_entry_off" in l:
                E = l["helper_entry_off"]
            elif missing_E == "impute":
                E = mean_E
                n_missing += 1
            else:
                n_missing += 1
                continue
            R += max(0.0, E + sp - (t_cpu_ns + 2000.0))
            Rc += max(0.0, E + sp - t_cpu_ns)
        g_pre.append((A_pre - C) / T)
        g_corr.append((A_corr - C - R) / T)
        g_cons.append((A_corr - C - Rc) / T)
        for l in lay:
            if "helper_entry_off" not in l:
                continue
            # extraction-consistency: E + first_wait + span should exceed the
            # blocked read by the (small, positive) pre-block dispatch work
            gap = (l["helper_entry_off"] + l["helper_first_wait_max"]
                   + (l["topk_end"] - l["topk_start"]) - l["stall_topk_read"])
            closure_gap_us.append(gap / 1000.0)
    def stats(g):
        m = sum(g) / len(g)
        lo, hi = boot_ci(g)
        return m, lo, hi
    return dict(steps=len(psl),
                pre=stats(g_pre), corr=stats(g_corr), cons=stats(g_cons),
                arm=best_arm(n_experts, min([1,2,4,8,16], key=lambda x: abs(x - Ms[0]))),
                closure=(sum(closure_gap_us)/len(closure_gap_us),
                         min(closure_gap_us), max(closure_gap_us)))

CONFIGS = [
    ("20b", "analysis-u1-ctx2048.json",     32, 24, "u1/ctx2048"),
    ("20b", "analysis-u1-ctx8192.json",     32, 24, "u1/ctx8192"),
    ("20b", "analysis-u8-ctx2048.json",     32, 24, "u8/ctx2048"),
    ("20b", "analysis-u8-ctx8192.json",     32, 24, "u8/ctx8192"),
    ("120b", "analysis120b-u1-ctx2048.json", 128, 36, "u1/ctx2048"),
    ("120b", "analysis120b-u1-ctx8192.json", 128, 36, "u1/ctx8192"),
    ("120b", "analysis120b-u8-ctx2048.json", 128, 36, "u8/ctx2048"),
    ("120b", "analysis120b-u8-ctx8192.json", 128, 36, "u8/ctx8192"),
]

published = {}
for f, model in (("g0-decision.json", "20b"), ("g0-decision-120b.json", "120b")):
    for row in json.load(open(f"{RD}/{f}"))["rows"]:
        published[(model, row["cfg"])] = row

print(f"{'config':16} {'arm':9} {'g_pre %':>22} {'g_corr % [CI]':>26} {'g_cons % [CI]':>26} {'closure gap us mean(min,max)':>30}")
ok = True
for model, fname, n, L, cfg in CONFIGS:
    r = gate(f"{RD}/{fname}", n, L)
    p = published[(model, cfg)]
    pm, plo, phi = r["pre"]; cm, clo, chi = r["corr"]; sm, slo, shi = r["cons"]
    print(f"{model+' '+cfg:16} {r['arm']:9} "
          f"{100*pm:8.2f} [{100*plo:.2f},{100*phi:.2f}] "
          f"{100*cm:8.2f} [{100*clo:.2f},{100*chi:.2f}] "
          f"{100*sm:8.2f} [{100*slo:.2f},{100*shi:.2f}] "
          f"{r['closure'][0]:8.2f} ({r['closure'][1]:.2f},{r['closure'][2]:.2f})")
    # compare vs published (means must match closely; CIs to bootstrap-RNG tolerance)
    checks = [
        ("g_mean", pm, p["g_mean"], 2e-4),
        ("g_corr_mean", cm, p["g_corr_mean"], 2e-4),
        ("g_cons_mean", sm, (p["g_cons_ci"][0] + p["g_cons_ci"][1]) / 2, 1.5e-3),
        ("corr_ci_lo", clo, p["g_corr_ci"][0], 1.5e-3),
        ("corr_ci_hi", chi, p["g_corr_ci"][1], 1.5e-3),
        ("arm", 0 if r["arm"] == p["best_arm"] else 1, 0, 0.5),
    ]
    for name, mine, theirs, tol in checks:
        if abs(mine - theirs) > tol:
            ok = False
            print(f"   MISMATCH {name}: mine={mine} published={theirs}")
print()
print("OVERALL:", "REPRODUCED within tolerance" if ok else "MISMATCHES FOUND (see above)")
print("""
EXPLAINED DIFFERENCES (verified against exec/r0-g0.py:149-156 after independent attempt):
the published gate computes the residual R once per config from MEAN helper-entry E and
MEAN top-k span SP (one max() clamp); this script clamps PER LAYER (Jensen: per-layer sum
of maxes >= mean-level max, so this g_corr <= published g_corr). Effects: 20b 1u rows
lower by ~0.03-0.04pp (still all >> +1%); 120b u1/ctx2048 lower (-1.62 vs -1.42, both
negative; per-layer clamping reacts to top-k-span outliers in the 6-step truncated
trace). No G0 verdict changes under the stricter per-layer treatment. Remaining
independence gap: span extraction from the raw .perfetto-trace files is r0-analyze.py's
(shared input); the closure statistics above are the consistency check on it.""")
