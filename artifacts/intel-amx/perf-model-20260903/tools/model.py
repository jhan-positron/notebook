#!/usr/bin/env python3
"""model.py - the perf model of perf-model/action-plan.html, as arithmetic.

Inputs
  baseline : Tron's AVX-path timers (worker 0 medians). Default: the fresh M7
             run (medians.json -> m7_tron_avx); --baseline 20260901 selects
             exec/results/single-attn-20260901/ (summary.json + phases-disable-*.json).
  bench    : exec/results/perf-model-20260903/medians.json (parse.py output; the
             non-Tron measurements M1..M5 on delphi-3bda)
  constants: coverage per prompt (page geometry), bytes per unit, AVX serving clock

Output   : exec/results/perf-model-20260903/model.json (every intermediate number)
           and a printed table. --dry-run uses placeholder bench numbers.

The chain (section 3.2 of the plan), per prompt length:
  page_work_AMX = units * (cov * unit_AMX + (1 - cov) * unit_AVX) + range_overhead + amx_extras
  attention_AMX = page_work_AMX + joins + barrier + untimed_rest        (rule 1: unchanged)
  token_AMX     = other + attention_AMX                                  (rule 2: unchanged)
  boost         = period_AVX / token_AMX - 1

Unit form (section 3): unit = max(compute, memory) + (1 - eta) * min(compute, memory), where
compute = the whole unit hot in L2 (QK + PV + common work of that code path, scaled to the
serving clock), memory = 32 KiB / R_core(27). eta is the overlap efficiency the 27-thread
DRAM run implies; values outside [0, 1] are flagged (memory rate not binding).

Benchmark configuration used for prompt 8192: Tron's book layout (24 adjacent pages per
book, one arena per book; runs *-p130-t27-book24) when present, else the single-arena runs.

Calibration residual (section 7): s = Tron AVX unit / benchmark AVX unit under load.
  none          : unit_AMX = bench_AMX
  multiplicative: unit_AMX = bench_AMX * s
  additive      : unit_AMX = bench_AMX + (tron_AVX - bench_AVX)
Selection rule as pre-registered: |s-1| <= 2% -> none; else if more than 80% of the residual sits
in QK+PV and the common-work residual is within 10% of Tron's common work -> additive; else
(including no phase split) -> multiplicative. --transfer overrides it (round 2) and the
rule-selected result is kept as round 1.
Calibration gate (section 7): total within 5% at prompt 8192 (10% at 2048 and 256), QK and PV
each within 10% at prompt 8192; when the gate fails the verdict is "calibration failed" and the
AMX numbers are provisional; the acceptance-rule verdict is also computed and labeled
"if the gate is waived".
"""
import argparse
import json
import os

HOME = os.path.expanduser("~")
BASE_DIR_20260901 = f"{HOME}/workspace/intel-AMX/exec/results/single-attn-20260901"
RESULTS = f"{HOME}/workspace/intel-AMX/exec/results/perf-model-20260903"

PROMPTS = {8192: {"pages": 130, "coverage": 0.9924}, 2048: {"pages": 34, "coverage": 0.9714}, 256: {"pages": 6, "coverage": 0.8478}}
COVERAGE_SOURCE = "decode coverage from exec/results/fallback-20260901/fallback.txt (amx / total visits): 99.24 / 97.14 / 84.78 %"
MEASURED_BOOST = {8192: 17.3, 2048: 6.1, 256: 0.5}   # same-binary, 2026-09-01 (comparison only)
MEASURED_SOURCE = "single-attn-20260901/summary.json: period disable / mirror - 1 at each prompt (comparison only)"
CALIB_TOL_PCT = {8192: 5.0, 2048: 10.0, 256: 10.0}
BYTES_PER_UNIT = 32 * 1024
AVX_CLOCK_GHZ = 3.74          # AVX arm busy clock (turbostat Bzy_MHz 3744), perf-stat round 3 (2026-09-01); not re-sampled in this campaign
AVX_CLOCK_SOURCE = "turbostat during Tron's AVX arm, perf-stat round 3 of 2026-09-01 (exec/results/perfstat3-20260901/); pre-registered in the plan; not re-sampled in this campaign"
LDTILECFG_CYCLES = 204        # Intel manual Table 20-2
QPACK_US = 0.05               # est.: 1 KiB copy + tile release per run of pages


def make_baseline(period, attn, sect, joins, barrier, units, ranges, qk, common, pv, source):
    unit = qk + common + pv
    b = {
        "period_us": period, "attention_us": attn, "page_work_us": sect, "joins_us": joins, "barrier_us": barrier,
        "untimed_rest_us": attn - (sect + joins + barrier), "other_us": period - attn,
        "units_w0": units, "ranges_w0": ranges, "unit_avx_us": unit, "qk_avx_us": qk, "common_avx_us": common, "pv_avx_us": pv,
        "range_overhead_us": sect - units * unit, "source": source,
    }
    b["attention_share"] = attn / period
    b["page_work_share_of_attention"] = sect / attn
    return b


def baseline_from_20260901():
    d = json.load(open(f"{BASE_DIR_20260901}/summary.json"))
    out = {}
    for p in PROMPTS:
        r = d[f"disable-{p}"]
        ph = json.load(open(f"{BASE_DIR_20260901}/phases-disable-c{p}.json"))
        out[p] = make_baseline(r["period"], r["attn"], r["sect"], r["joins"], r["barrier"], r["units"], ph["ranges"],
                               r["qk"], r["softmax"] + r["state"], r["pv"], f"single-attn-20260901/summary.json disable-{p} (+ phases-disable-c{p}.json ranges)")
    return out


def baseline_from_m7(m7):
    out = {}
    for p in PROMPTS:
        r = m7.get(str(p)) or m7.get(p)
        if r is None:
            return None
        out[p] = make_baseline(r["period_us"], r["attn_us"], r["sect_us"], r["joins_us"], r["barrier_us"], r["units"], r["ranges"],
                               r["qk_us"], r["common_us"], r["pv_us"], "perf-model-20260903/" + r["source"])
    return out


def dry_run_bench():
    """Placeholder non-Tron inputs from the superseded 2026-08-18 one-core sweep and clocks. Flagged."""
    ub = {}
    for p, (a27, m27) in {8192: (3186.0, 1800.0), 2048: (2466.0, 1470.0), 256: (1618.0, 686.0)}.items():
        ub[p] = {"avx_t27": a27, "amx_t27": m27, "avx_hot": 1618.0, "amx_hot": 686.0, "avx_hot_t1": 1618.0, "amx_hot_t1": 686.0, "layout": "dry-run",
                 "avx_t27_split": {"qk_ns": a27 * 0.52, "common_ns": a27 * 0.04, "pv_ns": a27 * 0.44, "range_ns_per_unit": 0.0},
                 "amx_t27_split": {"qk_ns": m27 * 0.45, "softmax_ns": m27 * 0.05, "pv_ns": m27 * 0.43, "state_ns": m27 * 0.07, "range_ns_per_unit": 3.0},
                 "amx_common": m27 * 0.12, "amx_range_ns_per_unit": 3.0}
    return {"dry_run": True, "unit_bench": ub, "r_core_27_GBs": 13.9, "r_core_1_GBs": 15.9,
            "amx_clock_ghz": 3.53, "avx_bench_clock_ghz": 3.74, "amx_bench_clock_ghz": 3.53,
            "avx_hot_clock_ghz": 3.89, "amx_hot_clock_ghz": 3.59, "clock_samples": {}}


def bench_from_medians(m):
    ub = m["m3_unit_bench"]

    def cfg(name):
        return ub.get(name)

    def w0(name, field="unit_ns"):
        c = cfg(name)
        return None if c is None else c["worker0"].get(field)

    out = {"dry_run": False, "unit_bench": {}}
    for p, g in PROMPTS.items():
        pg = g["pages"]
        book = pg == 130 and cfg("avx-p130-t27-book24") and cfg("amx-p130-t27-book24")
        prim = (lambda v: f"{v}-p{pg}-t27-book24") if book else (lambda v: f"{v}-p{pg}-t27")
        row = {
            "layout": "book24 (Tron's book layout: 24 adjacent pages per book, one arena per book)" if book else "single arena [layer][head][page]",
            "avx_t27": w0(prim("avx")), "amx_t27": w0(prim("amx")),
            "avx_t27_arena": w0(f"avx-p{pg}-t27"), "amx_t27_arena": w0(f"amx-p{pg}-t27"),
            "avx_t1": w0(f"avx-p{pg}-t1"), "amx_t1": w0(f"amx-p{pg}-t1"),
            "avx_hot": w0("avx-hot-t27"), "amx_hot": w0("amx-hot-t27"),
            "avx_hot_long": w0("avx-hot-t27-long"), "amx_hot_long": w0("amx-hot-t27-long"),
            "avx_hot_t1": w0("avx-hot-t1"), "amx_hot_t1": w0("amx-hot-t1"),
            "avx_t27_shuffle": w0(f"avx-p{pg}-t27-shuf") if pg == 130 else None,
            "amx_t27_shuffle": w0(f"amx-p{pg}-t27-shuf") if pg == 130 else None,
            "avx_t27_thp": w0(f"avx-p{pg}-t27-thp") if pg == 130 else None,
            "amx_t27_thp": w0(f"amx-p{pg}-t27-thp") if pg == 130 else None,
            "avx_t27_book24": w0(f"avx-p{pg}-t27-book24") if pg == 130 else None,
            "amx_t27_book24": w0(f"amx-p{pg}-t27-book24") if pg == 130 else None,
            "avx_t27_ctl": w0(f"avx-p{pg}-t27-ctl") if pg == 130 else None,
            "amx_t27_ctl": w0(f"amx-p{pg}-t27-ctl") if pg == 130 else None,
        }
        for v in ("avx", "amx"):
            c = cfg(prim(v))
            if c:
                row[f"{v}_t27_split"] = {k: c["worker0"].get(k) for k in ("qk_ns", "softmax_ns", "pv_ns", "state_ns", "common_ns", "range_ns_per_unit")}
                row[f"{v}_t27_files"] = c["files"]
                row[f"{v}_t27_spread"] = c["worker0"].get("unit_ns_spread")
            h = cfg(f"{v}-hot-t27")
            if h:
                row[f"{v}_hot_split"] = {k: h["worker0"].get(k) for k in ("qk_ns", "softmax_ns", "pv_ns", "state_ns", "common_ns")}
        sp = row.get("amx_t27_split")
        row["amx_common"] = None if not sp else (sp.get("softmax_ns") or 0) + (sp.get("state_ns") or 0)
        row["amx_range_ns_per_unit"] = None if not sp else sp.get("range_ns_per_unit")
        out["unit_bench"][p] = row
    mr = m.get("m1_memrate", {})
    out["r_core_27_GBs"] = (mr.get("load-t27-thp") or {}).get("per_core_GBs_median")
    out["r_core_1_GBs"] = (mr.get("load-t1-thp") or {}).get("per_core_GBs_median")
    out["r_core_tile_27_GBs"] = (mr.get("tile-t27-thp") or {}).get("per_core_GBs_median")
    out["r_core_tile_1_GBs"] = (mr.get("tile-t1-thp") or {}).get("per_core_GBs_median")
    out["r_core_curve"] = {k: v["per_core_GBs_median"] for k, v in mr.items()}
    cl = m.get("m4_clocks", {})

    def clock_for(prefix):
        rows = [v for k, v in cl.items() if k.startswith(prefix) and v.get("bzy_mhz_median_busy_cores")]
        vals = sorted(v["bzy_mhz_median_busy_cores"] for v in rows)
        return (vals[len(vals) // 2] / 1000.0, sum(v["samples_in_window"] for v in rows)) if vals else (None, 0)

    out["clock_samples"] = {}
    for key, prefix in (("amx_bench_clock_ghz", "amx-p130-t27"), ("avx_bench_clock_ghz", "avx-p130-t27"),
                        ("amx_hot_clock_ghz", "amx-hot-t27-long"), ("avx_hot_clock_ghz", "avx-hot-t27-long"),
                        ("amx_hot_t1_clock_ghz", "amx-hot-t1"), ("avx_hot_t1_clock_ghz", "avx-hot-t1")):
        val, n = clock_for(prefix)
        out[key] = val
        out["clock_samples"][key] = n
    out["amx_clock_ghz"] = out["amx_bench_clock_ghz"]
    out["avx_serving_clock_ghz"] = AVX_CLOCK_GHZ
    out["avx_serving_clock_source"] = AVX_CLOCK_SOURCE
    out["latency"] = m.get("m2_latency", {})
    out["insn"] = m.get("m5_insn", {})
    return out


def chain(base, unit_amx_us, coverage, amx_extras_us=0.0, barrier_scale=1.0, joins_scale=1.0):
    """Sections 3.2 and 8 of the plan. All times in microseconds per token."""
    units = base["units_w0"]
    page_work = units * (coverage * unit_amx_us + (1 - coverage) * base["unit_avx_us"]) + base["range_overhead_us"] + amx_extras_us
    attention = page_work + base["joins_us"] * joins_scale + base["barrier_us"] * barrier_scale + base["untimed_rest_us"]
    token = base["other_us"] + attention
    return {"unit_amx_us": unit_amx_us, "coverage": coverage, "page_work_us": page_work, "attention_us": attention, "token_us": token,
            "attention_ratio": attention / base["attention_us"], "token_ratio": token / base["period_us"], "boost_pct": (base["period_us"] / token - 1) * 100}


def jb_fit(base):
    """Least-squares line J+B = a + b x page work over the three prompts (plan section 9, joins-and-barrier round)."""
    xs = [base[p]["page_work_us"] for p in PROMPTS]
    ys = [base[p]["joins_us"] + base[p]["barrier_us"] for p in PROMPTS]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    res = {p: ((a + b * base[p]["page_work_us"]) / (base[p]["joins_us"] + base[p]["barrier_us"]) - 1) * 100 for p in PROMPTS}
    return {"a_us": a, "b": b, "residual_pct_by_prompt": res, "accepted": b >= 0 and all(abs(v) <= 10 for v in res.values()),
            "points": {p: {"page_work_us": base[p]["page_work_us"], "joins_plus_barrier_us": base[p]["joins_us"] + base[p]["barrier_us"]} for p in PROMPTS}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--medians", default=f"{RESULTS}/medians.json")
    ap.add_argument("--baseline", default="fresh", choices=["fresh", "20260901"])
    ap.add_argument("--out", default=f"{RESULTS}/model.json")
    ap.add_argument("--transfer", default=None, choices=["none", "multiplicative", "additive"],
                    help="round-2 override of the transfer rule; the rule-selected choice is kept as round1 in the output")
    ap.add_argument("--transfer-reason", default="")
    a = ap.parse_args()
    medians = None if a.dry_run else json.load(open(a.medians))
    base = None
    if a.baseline == "fresh" and medians and medians.get("m7_tron_avx"):
        base = baseline_from_m7(medians["m7_tron_avx"])
        if base is None:
            print("WARNING: M7 baseline incomplete; using the 2026-09-01 baseline")
    if base is None:
        base = baseline_from_20260901()
    bench = dry_run_bench() if a.dry_run else bench_from_medians(medians)
    result = {"dry_run": bench["dry_run"], "baseline": base, "baseline_choice": base[8192]["source"], "bench": bench, "prompts": {}, "warnings": [],
              "constants": {"coverage": {p: g["coverage"] for p, g in PROMPTS.items()}, "coverage_source": COVERAGE_SOURCE,
                            "measured_boost_pct": MEASURED_BOOST, "measured_boost_source": MEASURED_SOURCE,
                            "avx_serving_clock_ghz": AVX_CLOCK_GHZ, "avx_serving_clock_source": AVX_CLOCK_SOURCE,
                            "bytes_per_unit": BYTES_PER_UNIT, "calibration_tolerance_pct": CALIB_TOL_PCT},
              "jb_fit": jb_fit(base)}
    warn = lambda s: (result["warnings"].append(s), print("WARNING:", s))

    for p, g in PROMPTS.items():
        b = base[p]
        ub = bench["unit_bench"][p]
        row = {"pages": g["pages"], "coverage": g["coverage"], "measured_boost_pct": MEASURED_BOOST[p], "layout": ub.get("layout")}
        missing = [k for k in ("avx_t27", "amx_t27", "avx_hot", "amx_hot") if ub.get(k) is None]
        if missing:
            row["verdict"] = "Insufficient data: missing " + ", ".join(missing)
            warn(f"prompt {p}: {row['verdict']}")
            result["prompts"][p] = row
            continue
        avx_bench_us = ub["avx_t27"] / 1000.0
        row["avx_bench_us"] = avx_bench_us
        row["avx_tron_us"] = b["unit_avx_us"]
        s = b["unit_avx_us"] / avx_bench_us
        row["serving_factor_s"] = s
        row["calibration_error_pct"] = (avx_bench_us / b["unit_avx_us"] - 1) * 100
        sp = ub.get("avx_t27_split") or {}
        r = None
        if sp and sp.get("qk_ns") is not None:
            r = {"qk": b["qk_avx_us"] - (sp.get("qk_ns") or 0) / 1000.0,
                 "common": b["common_avx_us"] - (sp.get("common_ns") or 0) / 1000.0,
                 "pv": b["pv_avx_us"] - (sp.get("pv_ns") or 0) / 1000.0}
            row["avx_phase_residual_us"] = r
            row["avx_phase_residual_pct"] = {k: 100 * r[k] / b[f"{k}_avx_us"] for k in r}
        reasons = []
        ce = row["calibration_error_pct"]
        if abs(ce) > CALIB_TOL_PCT[p]:
            reasons.append(f"benchmark unit {abs(ce):.1f}% {'short of' if ce < 0 else 'above'} Tron's, limit {CALIB_TOL_PCT[p]:.0f}%")
        if p == 8192:
            if r is None:
                reasons.append("no per-phase split")
            else:
                for k in ("qk", "pv"):
                    v = row["avx_phase_residual_pct"][k]
                    if abs(v) > 10:
                        reasons.append(f"{k.upper()} {abs(v):.1f}% {'short of' if v > 0 else 'above'} Tron's, limit 10%")
        row["calibration_ok"] = not reasons
        row["calibration_fail_reasons"] = reasons
        amx_bench_us = ub["amx_t27"] / 1000.0
        resid = b["unit_avx_us"] - avx_bench_us
        variants = {"none": amx_bench_us, "multiplicative": amx_bench_us * s, "additive": amx_bench_us + resid}
        if abs(s - 1) <= 0.02:
            chosen, reason = "none", "none: |s-1| <= 2%"
        elif r is None:
            chosen, reason = "multiplicative", "multiplicative: no phase split"
        else:
            common_ok = abs(r["common"]) <= 0.10 * b["common_avx_us"]
            in_qkpv = (r["qk"] + r["pv"]) / resid if resid else 0.0
            if common_ok and in_qkpv > 0.8:
                chosen, reason = "additive", f"additive: {100 * in_qkpv:.0f}% of the residual in QK+PV, common within 10%"
            else:
                chosen, reason = "multiplicative", f"multiplicative: fallback ({100 * in_qkpv:.0f}% of the residual in QK+PV, common residual {100 * r['common'] / b['common_avx_us']:+.0f}%)"
        row["s_transfer_variants_us"] = variants
        row["round1_transfer_chosen"] = chosen
        row["round1_transfer_reason"] = reason
        row["round1_unit_amx_us"] = variants[chosen]
        if a.transfer:
            chosen, reason = a.transfer, f"round 2 override (a departure from the pre-registered rule, decided after the round-1 result): {a.transfer_reason}"
        row["s_transfer_chosen"] = chosen
        row["s_transfer_reason"] = reason
        row["unit_amx_primary_us"] = variants[chosen]
        for v in ("avx", "amx"):
            if ub.get(f"{v}_t27_shuffle") and ub.get(f"{v}_t27_arena"):
                row[f"{v}_shuffle_pct"] = (ub[f"{v}_t27_shuffle"] / ub[f"{v}_t27_arena"] - 1) * 100
            if ub.get(f"{v}_t27_thp") and ub.get(f"{v}_t27_arena"):
                row[f"{v}_thp_pct"] = (ub[f"{v}_t27_thp"] / ub[f"{v}_t27_arena"] - 1) * 100
            if ub.get(f"{v}_t27_book24") and ub.get(f"{v}_t27_ctl"):
                row[f"{v}_book24_pct"] = (ub[f"{v}_t27_book24"] / ub[f"{v}_t27_ctl"] - 1) * 100
                row[f"{v}_book24_us"] = ub[f"{v}_t27_book24"] / 1000.0
                row[f"{v}_ctl_us"] = ub[f"{v}_t27_ctl"] / 1000.0
            if ub.get(f"{v}_t27_arena"):
                row[f"{v}_arena_us"] = ub[f"{v}_t27_arena"] / 1000.0
        r_core = bench.get("r_core_27_GBs")
        mem_us = BYTES_PER_UNIT / (r_core * 1e9) * 1e6 if r_core else None
        row["memory_time_us_at_r_core_27"] = mem_us
        row["r_core_27_GBs"] = r_core
        for v in ("avx", "amx"):
            hot = ub.get(f"{v}_hot")
            f_hot = bench.get(f"{v}_hot_clock_ghz")
            if f_hot is None:
                warn(f"prompt {p} {v}: hot clock missing (no turbostat sample in the hot-t27-long window); loaded-run clock substituted (est.)")
                f_hot = bench.get(f"{v}_bench_clock_ghz")
                row[f"{v}_hot_clock_source"] = "MISSING: loaded-run clock substituted (est.)"
            else:
                row[f"{v}_hot_clock_source"] = f"m4-turbostat-{v}-hot-t27-long ({bench.get('clock_samples', {}).get(f'{v}_hot_clock_ghz', 0)} samples)"
            f_serv = AVX_CLOCK_GHZ if v == "avx" else (bench.get("amx_clock_ghz") or f_hot)
            scale = (f_hot / f_serv) if (f_hot and f_serv) else 1.0
            comp_us = hot / 1000.0 * scale
            t27_us = ub[f"{v}_t27"] / 1000.0
            row[f"{v}_hot_us"] = hot / 1000.0
            row[f"{v}_hot_clock_ghz"] = f_hot
            row[f"{v}_serving_clock_ghz"] = f_serv
            row[f"{v}_compute_us"] = comp_us
            row[f"{v}_clock_scale"] = scale
            row[f"{v}_hot_t1_us"] = (ub.get(f"{v}_hot_t1") or 0) / 1000.0
            hl = ub.get(f"{v}_hot_long")
            if hl and hot:
                row[f"{v}_hot_long_vs_hot_pct"] = (hl / hot - 1) * 100
                if abs(hl / hot - 1) > 0.02:
                    warn(f"prompt {p} {v}: hot-t27-long unit differs from hot-t27 by {100 * (hl / hot - 1):+.1f}% (clock sample and time from different runs)")
            if mem_us:
                hi, lo = max(comp_us, mem_us), min(comp_us, mem_us)
                row[f"{v}_roofline_us"] = hi
                row[f"{v}_serial_us"] = comp_us + mem_us
                eta = (comp_us + mem_us - t27_us) / lo if lo else None
                row[f"{v}_eta"] = eta
                row[f"{v}_eta_in_range"] = eta is not None and 0.0 <= eta <= 1.0
                if eta is not None and eta > 1.0:
                    row[f"{v}_eta_note"] = "above 1: the 27-thread unit is shorter than max(compute, 32 KiB / R_core(27)); the 64-byte-load DRAM rate is not the binding rate (working set in L3, or a faster stream)"
                    warn(f"prompt {p} {v}: eta {eta:.2f} above 1; DRAM memory-time assumption not binding (L3-residency round trigger, plan section 9)")
                elif eta is not None and eta < 0.0:
                    row[f"{v}_eta_note"] = "below 0: the unit is slower than compute plus memory time; a cost outside both terms"
                row[f"{v}_data_wait_us"] = t27_us - comp_us
                row[f"{v}_data_wait_share"] = (t27_us - comp_us) / t27_us if t27_us else None
                row[f"{v}_unit_over_memory_floor"] = t27_us / mem_us
        clock_part = row["avx_compute_us"] * (1 - 1 / row["avx_clock_scale"]) if row.get("avx_clock_scale") else 0.0
        row["avx_residual_us"] = resid
        row["avx_residual_clock_part_us"] = clock_part
        row["avx_residual_unexplained_us"] = resid - clock_part
        row["avx_residual_unexplained_pct_of_tron"] = 100 * (resid - clock_part) / b["unit_avx_us"]
        f_amx = bench.get("amx_clock_ghz") or 3.5
        rng_per_unit_ns = ub.get("amx_range_ns_per_unit")
        units_per_run = b["units_w0"] / b["ranges_w0"] if b["ranges_w0"] else b["units_w0"] / 36.0
        if rng_per_unit_ns is not None:
            row["amx_extras_us"] = b["ranges_w0"] * (rng_per_unit_ns * units_per_run / 1000.0)
            row["amx_extras_source"] = f"measured: {b['ranges_w0']:.0f} runs/token x {rng_per_unit_ns:.1f} ns/unit x {units_per_run:.1f} units/run (unit_bench range timer)"
        else:
            row["amx_extras_us"] = b["ranges_w0"] * (LDTILECFG_CYCLES / (f_amx * 1e3) + QPACK_US)
            row["amx_extras_source"] = f"est.: {b['ranges_w0']:.0f} runs/token x (204 cycles / {f_amx:.2f} GHz + {QPACK_US} us)"
        row["ranges_w0"] = b["ranges_w0"]
        row["chain_primary"] = chain(b, row["unit_amx_primary_us"], g["coverage"], row["amx_extras_us"])
        row["chain_round1"] = chain(b, row["round1_unit_amx_us"], g["coverage"], row["amx_extras_us"])
        row["chains_by_transfer"] = {k: chain(b, u, g["coverage"], row["amx_extras_us"]) for k, u in variants.items()}
        row["chain_unexplained_carries_fully"] = chain(b, amx_bench_us + row["avx_residual_unexplained_us"], g["coverage"], row["amx_extras_us"])
        ratio = row["unit_amx_primary_us"] / b["unit_avx_us"]
        row["chain_barrier_scaled"] = chain(b, row["unit_amx_primary_us"], g["coverage"], row["amx_extras_us"], barrier_scale=ratio)
        row["chain_joins_and_barrier_scaled"] = chain(b, row["unit_amx_primary_us"], g["coverage"], row["amx_extras_us"], barrier_scale=ratio, joins_scale=ratio)
        if row.get("amx_compute_us") is not None:
            for sign, tag in ((+0.05, "clock_plus5"), (-0.05, "clock_minus5")):
                du = row["amx_compute_us"] * (1 / (1 + sign) - 1)
                row[f"chain_{tag}"] = chain(b, row["unit_amx_primary_us"] + du, g["coverage"], row["amx_extras_us"])
        if row.get("amx_compute_us") is not None and mem_us:
            comp = row["amx_compute_us"]
            hi, lo = max(comp, mem_us), min(comp, mem_us)
            row["bracket_eta1_us"], row["bracket_eta0_us"] = hi, hi + lo
            row["chain_bracket_eta1"] = chain(b, hi, g["coverage"], row["amx_extras_us"])
            row["chain_bracket_eta0"] = chain(b, hi + lo, g["coverage"], row["amx_extras_us"])
            if row.get("avx_eta") is not None:
                eta = max(0.0, min(1.0, row["avx_eta"]))
                row["unit_amx_modeled_with_avx_eta_us"] = hi + (1 - eta) * lo
                row["chain_modeled_with_avx_eta"] = chain(b, row["unit_amx_modeled_with_avx_eta_us"], g["coverage"], row["amx_extras_us"])
        common_amx = (ub.get("amx_common") or 0) / 1000.0
        row["chain_zero_matmul_ceiling"] = chain(b, common_amx, g["coverage"], row["amx_extras_us"])
        du = 0.01
        c2 = chain(b, row["unit_amx_primary_us"] + du, g["coverage"], row["amx_extras_us"])
        row["boost_pp_per_us_of_unit"] = (c2["boost_pct"] - row["chain_primary"]["boost_pct"]) / du
        cands = {f"transfer:{k}": row["chains_by_transfer"][k]["boost_pct"] for k in variants}
        cands["barrier scaled"] = row["chain_barrier_scaled"]["boost_pct"]
        cands["joins and barrier scaled"] = row["chain_joins_and_barrier_scaled"]["boost_pct"]
        for tag in ("chain_clock_plus5", "chain_clock_minus5"):
            if tag in row:
                cands[tag] = row[tag]["boost_pct"]
        lo_k, hi_k = min(cands, key=cands.get), max(cands, key=cands.get)
        row["band_pct"] = [cands[lo_k], cands[hi_k]]
        row["band_edges"] = {"low": lo_k, "high": hi_k}
        sub = {k: v for k, v in cands.items() if not k.startswith("transfer:") or k == f"transfer:{chosen}"}
        row["band_posthoc_pct"] = [min(sub.values()), max(sub.values())]
        row["band_posthoc_note"] = "post hoc, not part of the acceptance rule: the transfer variants other than the chosen one are dropped"
        err = row["chain_primary"]["boost_pct"] - MEASURED_BOOST[p]
        row["error_pp"] = err
        band_ok = abs(row["band_pct"][0] - MEASURED_BOOST[p]) <= 3 and abs(row["band_pct"][1] - MEASURED_BOOST[p]) <= 3
        v = "on par" if (abs(err) <= 3 and band_ok) else ("close" if abs(err) <= 6 else "not close")
        row["verdict_if_gate_waived"] = v
        row["verdict"] = v if row["calibration_ok"] else "calibration failed"
        if not row["calibration_ok"]:
            warn(f"prompt {p}: calibration gate failed ({'; '.join(reasons)}); AMX numbers provisional (plan section 7)")
        result["prompts"][p] = row

    result["calibration_ok"] = all(r.get("calibration_ok", False) for r in result["prompts"].values())
    json.dump(result, open(a.out, "w"), indent=1)
    print(f"wrote {a.out}  (dry_run={result['dry_run']}, baseline={result['baseline_choice']})")
    print(f"{'prompt':>7} {'layout':>8} {'AVX tron':>9} {'AVX bench':>10} {'calib%':>7} {'s':>6} {'xfer':>14} | {'AMX bench':>10} {'AMX unit':>9} | {'boost':>7} {'meas':>6} {'band':>16} {'posthoc':>16} gate/verdict")
    for p, r in result["prompts"].items():
        if "chain_primary" not in r:
            print(f"{p:>7} {r['verdict']}")
            continue
        c = r["chain_primary"]
        print(f"{p:>7} {str(r['layout'])[:8]:>8} {r['avx_tron_us']:9.3f} {r['avx_bench_us']:10.3f} {r['calibration_error_pct']:+7.1f} {r['serving_factor_s']:6.3f} {r['s_transfer_chosen']:>14} | "
              f"{r['s_transfer_variants_us']['none']:10.3f} {r['unit_amx_primary_us']:9.3f} | {c['boost_pct']:+6.1f}% {r['measured_boost_pct']:+5.1f}% [{r['band_pct'][0]:+5.1f},{r['band_pct'][1]:+5.1f}] [{r['band_posthoc_pct'][0]:+5.1f},{r['band_posthoc_pct'][1]:+5.1f}] {r['verdict']} / {r['verdict_if_gate_waived']}")
    r = result["prompts"].get(8192, {})
    for k in ("s_transfer_reason", "round1_transfer_chosen", "round1_unit_amx_us", "avx_compute_us", "amx_compute_us", "memory_time_us_at_r_core_27", "avx_eta", "amx_eta",
              "avx_data_wait_us", "amx_data_wait_us", "amx_unit_over_memory_floor", "amx_extras_us", "boost_pp_per_us_of_unit", "avx_phase_residual_pct", "band_edges",
              "avx_shuffle_pct", "amx_shuffle_pct", "avx_thp_pct", "amx_thp_pct", "avx_book24_pct", "amx_book24_pct", "avx_arena_us", "amx_arena_us",
              "avx_residual_us", "avx_residual_clock_part_us", "avx_residual_unexplained_us", "avx_residual_unexplained_pct_of_tron", "calibration_fail_reasons"):
        if k in r:
            print(f"  {k:36s} {r[k]}")
    for k in ("chain_round1", "chain_unexplained_carries_fully", "chain_barrier_scaled", "chain_joins_and_barrier_scaled", "chain_clock_plus5", "chain_clock_minus5", "chain_bracket_eta1", "chain_bracket_eta0"):
        if k in r:
            print(f"  {k:36s} boost {r[k]['boost_pct']:+.1f}%  unit {r[k]['unit_amx_us']:.3f}")
    print("  jb_fit", json.dumps(result["jb_fit"]))


if __name__ == "__main__":
    main()
