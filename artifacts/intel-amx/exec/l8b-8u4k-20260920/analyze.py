#!/usr/bin/env python3
"""Analysis of the l8b-8u4k campaign (plan CI-test/status/llama-3.1-8b-8u-4k-plan.md, sections 7 and 9).
Copied from exec/l8b-levers-20260919/analyze.py; the per-config statistics are unchanged, the Saturday-specific verdicts
(16K pair, 8K triple, two bands) are replaced by the one-cell verdict of this plan.

Reads exec/results/l8b-8u4k-20260920/<arm>-pass<k>/perf.json (arm = base|canon, k = 1..3), pairs pass k of base with pass k
of canon, and writes summary.json + summary.txt into the results directory:
  * per config: clean (base) and canon TPS mean per pass, gain % (mean canon over mean base, minus 1), paired t over the
    passes with both arms (t = mean(d) / (sd(d, ddof 1) / sqrt(n)), d = canon - base TPS per pass), resolved = |t| >= 4.303
    and |gain| >= 1 % (n = 3; with fewer passes the 95 % limit is 12.706 for n = 2 and the config is 'incomplete'),
    TTFT, slowest sample (min TPS), p05, cell wall time, anomalous-sample lines, per-engine request counts, AMX-busy cycles;
  * the verdict of plan section 7 for the one cell (8 users per engine x prompt 4096): resolved or not, the pre-registered
    band +11 % to +21 %, the reading (inside / below / above), and the clean arm's candidate goal values (mean TPS,
    slowest sample, p05);
  * the three Saturday reference cells (8 users per engine x 1024 and x 2048, 2 users per engine x 4096), read from
    exec/results/l8b-levers-20260919/summary.json (never retyped), as 'reference' rows;
  * with fewer than 2 pairs the numbers are reported without a verdict (plan section 2a).
usage: analyze.py [RESULTS_DIR] [REFERENCE_SUMMARY_JSON]
"""
import glob
import json
import math
import os
import re
import sys

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/l8b-8u4k-20260920"
REF_SUMMARY = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/summary.json"
T_LIMIT = {3: 4.303, 2: 12.706}   # 95 % two-sided Student t limits for n-1 degrees of freedom
MIN_CHANGE_PCT = 1.0
CELL = "llama_3_1_8b_instruct_good_tp2_32u_p4096"       # the one cell: 8 users per engine x prompt 4096
BAND = (11.0, 21.0)                                      # plan section 7, pre-registered expected gain band in percent
REF_CELLS = ["llama_3_1_8b_instruct_good_tp2_32u_p1024",   # Saturday: 8 users per engine x 1024 (T1)
             "llama_3_1_8b_instruct_good_tp2_32u_p2048",   # Saturday: 8 users per engine x 2048
             "llama_3_1_8b_instruct_good_tp2_8u_p4096"]    # Saturday: 2 users per engine x 4096
REF_ALL_8U = ["llama_3_1_8b_instruct_good_tp2_32u_p1024", "llama_3_1_8b_instruct_good_tp2_32u_p2048"]
REF_ALL_2U = ["llama_3_1_8b_instruct_good_tp2_8u_p1024", "llama_3_1_8b_instruct_good_tp2_8u_p2048",
              "llama_3_1_8b_instruct_good_tp2_8u_p3000", "llama_3_1_8b_instruct_good_tp2_8u_p4096"]   # the 2-users series, for the chart's scale
USERS_PER_ENGINE = {4: 1, 8: 2, 16: 4, 32: 8}


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def sd1(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def paired_t(d):
    """t statistic of paired differences d (n >= 2); None when the sd is 0 or n < 2."""
    n = len(d)
    s = sd1(d)
    if n < 2 or s is None:
        return None
    if s == 0:
        return math.inf if mean(d) != 0 else 0.0
    return mean(d) / (s / math.sqrt(n))


def load_passes():
    passes = {}
    for path in sorted(glob.glob(os.path.join(RES, "*-pass[0-9]", "perf.json"))):
        tag = os.path.basename(os.path.dirname(path))
        m = re.fullmatch(r"(base|canon)-pass(\d+)", tag)
        if not m:
            continue
        try:
            rec = json.load(open(path))
        except Exception as exc:
            print(f"cannot read {path}: {exc}", file=sys.stderr)
            continue
        passes[(m.group(1), int(m.group(2)))] = rec
    return passes


def p05(values):
    """The harness's calculate_p05_tps (testlib/perf_metrics.py): linear interpolation at position 0.05 x (n - 1)."""
    v = sorted(float(x) for x in values)
    pos = (len(v) - 1) * 0.05
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def sd0(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def per_config(rec):
    """{name: {tps_mean, tps_sd, p05, min, ttft, prompt_tokens_mean, cache_hit_pct, n_samples, wall_s, engine_requests, anomalous,
    amx_busy, binary_ok, tpss}} for one pass record. record['results'] is written only when the driver finished normally;
    a run cut by a timeout or a StopPass has its completed configs only in record['raw'], so those are rebuilt from the
    raw samples with the harness's own formulas (population sd, interpolated p05, TTFT mean rounded) and flagged from_raw (D3)."""
    out = {}
    for r in rec.get("results", []):
        if not r.get("tps_results"):
            continue
        out[r["name"]] = {"tps_mean": r["tps_mean"], "tps_sd": r["tps_std_dev"], "p05": r["p05_tps"], "min": r["min_tps"],
                          "ttft_ms": r["ttft_mean"], "prompt_tokens_mean": r["prompt_tokens"], "cache_hit_pct": r["cache_hit_pct"],
                          "n_samples": len(r["tps_results"]), "tpss": r["tps_results"], "from_raw": False}
    for raw in rec.get("raw", []):
        n = raw.get("name")
        tpss = raw.get("tpss") or []
        if n and n not in out and tpss and len(tpss) == (raw.get("n_users") or 0) * (raw.get("n_rounds") or 0):
            pt = raw.get("prompt_tokens") or []
            ct = raw.get("cached_tokens") or []
            out[n] = {"tps_mean": mean(tpss), "tps_sd": sd0(tpss), "p05": p05(tpss), "min": min(tpss),
                      "ttft_ms": round(mean(raw.get("ttfts_ms") or [0])), "prompt_tokens_mean": mean(pt) if pt else None,
                      "cache_hit_pct": (100.0 * sum(ct) / sum(pt)) if pt and sum(pt) else None,
                      "n_samples": len(tpss), "tpss": tpss, "from_raw": True}
    for raw in rec.get("raw", []):
        n = raw.get("name")
        if n in out:
            reqs = raw.get("engine_requests") or {}
            expect = raw["n_users"] * raw["n_rounds"] // 4 if raw.get("n_users") and raw.get("n_rounds") else None
            even = (len(reqs) == 4 and all(v == expect for v in reqs.values())) if (reqs and expect) else None
            out[n].update({"wall_s": raw.get("wall_seconds"), "engine_requests": reqs, "spread_even": even,
                           "caddy_health_events": raw.get("caddy_health_events"),
                           "anomalous_samples": raw.get("anomalous_samples"), "started": raw.get("started"),
                           "amx_busy_cycles": raw.get("amx_busy_cycles"), "binary_check_ok": raw.get("binary_check_ok"),
                           "prompt_tokens_min": min(raw["prompt_tokens"]) if raw.get("prompt_tokens") else None,
                           "prompt_tokens_max": max(raw["prompt_tokens"]) if raw.get("prompt_tokens") else None})
    return out


def main():
    passes = load_passes()
    if not passes:
        print("no pass records found under", RES)
        return 1
    arms = sorted({a for a, _ in passes})
    ks = sorted({k for _, k in passes})
    tables = {key: per_config(rec) for key, rec in passes.items()}
    names = sorted({n for t in tables.values() for n in t}, key=lambda n: (int(re.search(r"_(\d+)u_", n).group(1)), int(re.search(r"_p(\d+)$", n).group(1))))
    identity = {f"{a}-pass{k}": {"versions": passes[(a, k)].get("versions"), "installed_sha_env": passes[(a, k)].get("installed_sha_env"),
                                 "started": passes[(a, k)].get("started"), "finished": passes[(a, k)].get("finished"),
                                 "perf_minutes": passes[(a, k)].get("perf_minutes"), "stop": passes[(a, k)].get("stop"),
                                 "amx_probes": [(p.get("model"), p.get("amx_busy_cycles")) for p in passes[(a, k)].get("amx_probes", [])],
                                 "binary_checks_bad": [b.get("bad") for b in passes[(a, k)].get("binary_checks", []) if b.get("bad")]}
                for (a, k) in sorted(passes)}
    summary = {"results_dir": RES, "passes_found": [f"{a}-pass{k}" for (a, k) in sorted(passes)], "identity": identity,
               "configs": {}, "incomplete": [], "verdicts": {}}
    complete_ks = [k for k in ks if ("base", k) in passes and ("canon", k) in passes]
    for n in names:
        rows = {}
        for k in ks:
            for a in ("base", "canon"):
                t = tables.get((a, k), {}).get(n)
                if t:
                    rows[f"{a}-pass{k}"] = {kk: vv for kk, vv in t.items() if kk != "tpss"}
        pairs = [k for k in complete_ks if n in tables.get(("base", k), {}) and n in tables.get(("canon", k), {})]
        entry = {"per_pass": rows, "paired_passes": pairs, "n_pairs": len(pairs)}
        if pairs:
            b = [tables[("base", k)][n]["tps_mean"] for k in pairs]
            c = [tables[("canon", k)][n]["tps_mean"] for k in pairs]
            d = [ci - bi for bi, ci in zip(b, c)]
            gain = 100.0 * (mean(c) / mean(b) - 1.0)
            t = paired_t(d)
            lim = T_LIMIT.get(len(pairs))
            resolved = (t is not None and lim is not None and abs(t) >= lim and abs(gain) >= MIN_CHANGE_PCT)
            entry.update({"base_tps_mean": mean(b), "canon_tps_mean": mean(c), "gain_pct": gain,
                          "gain_pct_per_pass": [100.0 * (ci / bi - 1.0) for bi, ci in zip(b, c)],
                          "diff_tps_per_pass": d, "paired_t": t, "t_limit_95": lim, "resolved": resolved,
                          "direction": ("canon faster" if gain > 0 else "canon slower") if resolved else "not resolved",
                          "base_min_tps": min(tables[("base", k)][n]["min"] for k in pairs),
                          "canon_min_tps": min(tables[("canon", k)][n]["min"] for k in pairs),
                          "base_p05_mean": mean([tables[("base", k)][n]["p05"] for k in pairs]),
                          "canon_p05_mean": mean([tables[("canon", k)][n]["p05"] for k in pairs]),
                          "base_ttft_ms_mean": mean([tables[("base", k)][n]["ttft_ms"] for k in pairs]),
                          "canon_ttft_ms_mean": mean([tables[("canon", k)][n]["ttft_ms"] for k in pairs]),
                          "wall_s_mean": mean([v for k in pairs for a in ("base", "canon") for v in [tables[(a, k)][n].get("wall_s")] if v is not None]) or None,
                          "uneven_spread_runs": [f"{a}-pass{k}" for k in pairs for a in ("base", "canon") if tables[(a, k)][n].get("spread_even") is False],
                          "caddy_health_event_runs": [f"{a}-pass{k}" for k in pairs for a in ("base", "canon") if (tables[(a, k)][n].get("caddy_health_events") or 0) > 0],
                          "anomalous_samples_total": sum((tables[(a, k)][n].get("anomalous_samples") or 0) for k in pairs for a in ("base", "canon")),
                          "amx_busy_cycles": {f"{a}-pass{k}": tables[(a, k)][n].get("amx_busy_cycles") for k in pairs for a in ("base", "canon")},
                          "engine_requests_all": {f"{a}-pass{k}": tables[(a, k)][n].get("engine_requests") for k in pairs for a in ("base", "canon")}})
        if len(pairs) < 3:
            summary["incomplete"].append({"name": n, "n_pairs": len(pairs), "present_in": sorted(rows)})
        summary["configs"][n] = entry

    def gain_of(n):
        e = summary["configs"].get(n)
        return e.get("gain_pct") if e and e.get("n_pairs") == 3 else None

    # ---- the one-cell verdict of plan section 7
    e = summary["configs"].get(CELL, {})
    n_pairs = e.get("n_pairs", 0)
    g = e.get("gain_pct")
    if n_pairs < 2:
        reading = f"no verdict: only {n_pairs} paired pass(es) (plan section 2a needs at least 2); numbers reported without a verdict"
    elif not e.get("resolved"):
        reading = "not resolved by the pre-registered rule (|t| >= %.3f and |gain| >= 1 %%)" % (e.get("t_limit_95") or 0)
    elif BAND[0] <= g <= BAND[1]:
        reading = "inside the band: the context lever keeps working at 8 users per engine; the cell is a candidate long-prompt CI shape at the recommended load"
    elif g < BAND[0]:
        reading = "below the band: the gain saturates with load at this prompt length; compare with the 2048 cell"
    else:
        reading = "above the band: more than the kernel's speed ratio explains; check the data quality (requests per engine, anomalous samples, client pressure) before believing it"
    summary["verdicts"]["cell"] = {"name": CELL, "n_pairs": n_pairs, "gain_pct": g, "paired_t": e.get("paired_t"), "t_limit_95": e.get("t_limit_95"),
                                   "resolved": e.get("resolved"), "direction": e.get("direction"), "band_pct": list(BAND),
                                   "inside_band": (BAND[0] <= g <= BAND[1]) if (g is not None and n_pairs >= 2) else None, "reading": reading,
                                   "candidate_goal_values_clean": {"tps_mean": e.get("base_tps_mean"), "slowest_sample_tps": e.get("base_min_tps"), "p05_tps_mean": e.get("base_p05_mean")} if n_pairs else None}
    # ---- the Saturday reference cells (same arms, same driver, same layout), read from the Saturday summary.json
    ref = {"source": REF_SUMMARY, "cells": {}, "series_8u": {}, "series_2u": {}}
    try:
        rs = json.load(open(REF_SUMMARY))["configs"]
        for n in set(REF_CELLS) | set(REF_ALL_8U) | set(REF_ALL_2U):
            r = rs.get(n)
            if not r or not r.get("n_pairs"):
                continue
            row = {k: r.get(k) for k in ("n_pairs", "base_tps_mean", "canon_tps_mean", "gain_pct", "gain_pct_per_pass", "paired_t", "resolved",
                                          "base_ttft_ms_mean", "canon_ttft_ms_mean", "base_min_tps", "canon_min_tps", "base_p05_mean", "canon_p05_mean", "wall_s_mean")}
            if n in REF_CELLS:
                ref["cells"][n] = row
            if n in REF_ALL_8U:
                ref["series_8u"][n] = row
            if n in REF_ALL_2U:
                ref["series_2u"][n] = row
    except Exception as exc:
        ref["error"] = repr(exc)
        print(f"reference summary not read: {exc}", file=sys.stderr)
    summary["reference"] = ref
    g2048 = (ref["cells"].get("llama_3_1_8b_instruct_good_tp2_32u_p2048") or {}).get("gain_pct")
    summary["verdicts"]["against_2048"] = {"gain_8u_p2048_saturday": g2048, "gain_8u_p4096": g,
                                            "diff_points": (g - g2048) if (g is not None and g2048 is not None) else None}

    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=str)
    lines = [f"l8b-8u4k summary  passes: {', '.join(summary['passes_found'])}",
             f"{'config':45s} {'n':>1s} {'base TPS':>9s} {'canon TPS':>9s} {'gain %':>7s} {'t':>7s} {'res':>4s} {'TTFT b/c ms':>12s} {'min b/c':>15s} {'wall s':>7s}"]
    for n, e in summary["configs"].items():
        if e.get("n_pairs"):
            t = e["paired_t"]
            fr = [k for k, v in e["per_pass"].items() if v.get("from_raw")]
            if fr:
                lines.append(f"   ({n}: rebuilt from raw samples in {', '.join(fr)})")
            lines.append(f"{n:45s} {e['n_pairs']:>1d} {e['base_tps_mean']:9.2f} {e['canon_tps_mean']:9.2f} {e['gain_pct']:+7.2f} {(f'{t:7.2f}' if t is not None and math.isfinite(t) else str(t)):>7s} {'yes' if e['resolved'] else 'no':>4s} {e['base_ttft_ms_mean']:5.0f}/{e['canon_ttft_ms_mean']:<6.0f} {e['base_min_tps']:7.2f}/{e['canon_min_tps']:<7.2f} {(e['wall_s_mean'] or 0):7.0f}")
        else:
            lines.append(f"{n:45s} 0 (no paired pass)")
    lines.append("incomplete: " + (", ".join(f"{i['name']} ({i['n_pairs']} pairs)" for i in summary["incomplete"]) or "none"))
    flagged = [(n, e["uneven_spread_runs"], e["caddy_health_event_runs"], e["anomalous_samples_total"]) for n, e in summary["configs"].items() if e.get("n_pairs")
               and (e["uneven_spread_runs"] or e["caddy_health_event_runs"] or e["anomalous_samples_total"])]
    lines.append("flags (uneven Caddy spread / Caddy health events / anomalous samples): " + ("; ".join(f"{n}: spread {u or '-'} health {c or '-'} anomalous {a}" for n, u, c, a in flagged) or "none"))
    lines.append("Saturday reference cells (exec/results/l8b-levers-20260919/summary.json):")
    for n, r in summary["reference"]["cells"].items():
        lines.append(f"  {n:45s} {r['n_pairs']:>1d} {r['base_tps_mean']:9.2f} {r['canon_tps_mean']:9.2f} {r['gain_pct']:+7.2f} {r['paired_t']:7.2f} {'yes' if r['resolved'] else 'no':>4s} {r['base_ttft_ms_mean']:5.0f}/{r['canon_ttft_ms_mean']:<6.0f} {r['base_min_tps']:7.2f}/{r['canon_min_tps']:<7.2f} {(r['wall_s_mean'] or 0):7.0f}")
    for k, v in summary["verdicts"].items():
        lines.append(f"{k}: {json.dumps(v, default=str)}")
    txt = "\n".join(lines)
    with open(os.path.join(RES, "summary.txt"), "w") as f:
        f.write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
