#!/usr/bin/env python3
"""Analysis of the q4b-swattn campaign (qwen3-4b Saturday plan sections 7 and 9; copied 2026-09-19 from
exec/l8b-levers-20260919/analyze.py, verdict blocks replaced).

Reads exec/results/q4b-swattn-20260919/<arm>-pass<k>/perf.json (arm = base|canon, k = 1..3), pairs pass k of base with
pass k of canon, and writes summary.json + summary.txt into the results directory:
  * per config (one prompt length at 2 users per engine): base and canon TPS mean per pass, gain % (mean canon over mean
    base, minus 1), paired t over the passes with both arms (t = mean(d) / (sd(d, ddof 1) / sqrt(n)), d = canon - base TPS
    per pass), resolved = |t| >= 4.303 and |gain| >= 1 % (n = 3; with fewer passes the 95 % limit is 12.706 for n = 2 and
    the config is 'incomplete' and never resolved), TTFT, slowest sample (min TPS), p05, cell wall time, anomalous-sample lines, per-engine
    request counts, AMX-busy cycles, the measured server overhead (server-counted prompt tokens minus prompt_length),
    the USE_HW_ATTN=0 verdict of every run and rinzler's FUSE limits;
  * the pre-registered verdicts of plan section 7: band_p1024 (+5.4 to +11.4 % at prompt 1024), curve (every resolved
    cell gains at least the previous resolved cell's gain minus 2 points, in prompt-length order), crossing (the shortest
    prompt length whose gain is resolved and at least +10 %).
Only configs with all passes on both arms are used for the verdicts; others are listed as incomplete. With no pass record
an empty summary is written (the check-only state), so gen_report.py can still render.
usage: analyze.py [RESULTS_DIR]
"""
import glob
import json
import math
import os
import re
import sys

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/q4b-swattn-20260919"
T_LIMIT = {3: 4.303, 2: 12.706}   # 95 % two-sided Student t limits for n-1 degrees of freedom
MIN_CHANGE_PCT = 1.0
CFG_REF = "ingested_qwen_3_4b_instruct_2507_tp2_8u_p1024"   # the nightly's own config (prompt 1024, 2 users per engine)
BAND_P1024 = (5.4, 11.4)      # plan section 7: p0perf-20260913 measured +8.4 % (140.61 -> 152.46 TPS) at this load; +8.4 plus or minus 3 points
MONOTONE_TOL_POINTS = 2.0     # plan section 7 curve rule
CROSSING_MIN_GAIN = 10.0      # plan section 7 crossing rule
USERS_PER_ENGINE = {8: 2}


def plen_of(name):
    return int(re.search(r"_p(\d+)$", name).group(1))


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
                           "hwattn_ok": raw.get("hwattn_ok"), "fuse_limits": raw.get("fuse_limits"),
                           "prompt_tokens_min": min(raw["prompt_tokens"]) if raw.get("prompt_tokens") else None,
                           "prompt_tokens_max": max(raw["prompt_tokens"]) if raw.get("prompt_tokens") else None})
    return out


def main():
    passes = load_passes()
    if not passes:
        print("no pass records found under", RES, "- writing an empty summary (check-only state)")
        empty = {"results_dir": RES, "passes_found": [], "identity": {}, "configs": {}, "incomplete": [],
                 "verdicts": {"band_p1024": {"gain": None, "band": list(BAND_P1024), "inside": None},
                              "curve": {"resolved_cells": [], "breaks": [], "verdict": "undecided: no pass record"},
                              "crossing": {"prompt_length": None, "verdict": "undecided: no pass record"}}}
        with open(os.path.join(RES, "summary.json"), "w") as f:
            json.dump(empty, f, indent=1)
        with open(os.path.join(RES, "summary.txt"), "w") as f:
            f.write("q4b-swattn summary: no pass record yet\n")
        return 0
    arms = sorted({a for a, _ in passes})
    ks = sorted({k for _, k in passes})
    tables = {key: per_config(rec) for key, rec in passes.items()}
    planned = {c["name"] for rec in passes.values() for c in rec.get("configs", []) if c.get("name")}   # every cell the driver was given, even one without a result in any pass (plan 2a: report every dropped cell)
    names = sorted({n for t in tables.values() for n in t} | planned, key=lambda n: (int(re.search(r"_(\d+)u_", n).group(1)), int(re.search(r"_p(\d+)$", n).group(1))))
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
        ovh = [pv["prompt_tokens_mean"] - plen_of(n) for pv in rows.values() if pv.get("prompt_tokens_mean")]
        entry = {"per_pass": rows, "paired_passes": pairs, "n_pairs": len(pairs), "prompt_length": plen_of(n),
                 "users_per_engine": USERS_PER_ENGINE.get(int(re.search(r"_(\d+)u_", n).group(1))),
                 "overhead_tokens_mean": mean(ovh) if ovh else None,
                 "hwattn_ok_all": all(pv.get("hwattn_ok") is True for pv in rows.values()) if rows else None,
                 "hwattn_ok_runs": {k: pv.get("hwattn_ok") for k, pv in rows.items()}}
        if pairs:
            b = [tables[("base", k)][n]["tps_mean"] for k in pairs]
            c = [tables[("canon", k)][n]["tps_mean"] for k in pairs]
            d = [ci - bi for bi, ci in zip(b, c)]
            gain = 100.0 * (mean(c) / mean(b) - 1.0)
            t = paired_t(d)
            lim = T_LIMIT.get(len(pairs))
            resolved = (len(pairs) == 3 and t is not None and lim is not None and abs(t) >= lim and abs(gain) >= MIN_CHANGE_PCT)   # only a complete cell (3 pairs) can be resolved (plan section 7)
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

    # ---- plan section 7 verdicts (pre-registered)
    # band at prompt 1024: the one earlier measurement of this exact load (p0perf-20260913, CI harness, 2 users per engine, USE_HW_ATTN=0,
    # kill switch against AMX on, our half) gave +8.4 %; band = +8.4 plus or minus 3 points
    gr = gain_of(CFG_REF)
    summary["verdicts"]["band_p1024"] = {"gain": gr, "band": list(BAND_P1024), "inside": (BAND_P1024[0] <= gr <= BAND_P1024[1]) if gr is not None else None,
                                         "reference": "p0perf-20260913 CI layout tp2: 140.61 -> 152.46 TPS (+8.4 %), USE_HW_ATTN=0, our half of the machine",
                                         "verdict": ("undecided: the prompt-1024 cell is incomplete" if gr is None else
                                                     ("inside: the whole-machine, two-deb setup reproduces the earlier result" if BAND_P1024[0] <= gr <= BAND_P1024[1] else
                                                      "outside: reported; the two campaigns differ in binary (one build with a kill switch there, two debs here) and in machine half"))}
    # curve: in prompt-length order, every resolved cell gains at least the previous resolved cell's gain minus 2 points
    res_cells = [(plen_of(n), summary["configs"][n]["gain_pct"]) for n in names if summary["configs"][n].get("resolved") and summary["configs"][n].get("n_pairs") == 3]
    res_cells.sort()
    breaks = [{"prompt_length": p, "gain": g, "previous_prompt_length": pp, "previous_gain": gp}
              for (pp, gp), (p, g) in zip(res_cells, res_cells[1:]) if g < gp - MONOTONE_TOL_POINTS]
    if len(res_cells) < 2:
        cv = "undecided: fewer than 2 resolved cells"
    elif not breaks:
        cv = "PASS: every resolved cell gains at least the previous resolved cell's gain minus 2 points (the context lever holds for this model)"
    else:
        cv = "FAIL: " + "; ".join(f"prompt {b['prompt_length']} ({b['gain']:+.2f} %) is more than 2 points below prompt {b['previous_prompt_length']} ({b['previous_gain']:+.2f} %)" for b in breaks)
    summary["verdicts"]["curve"] = {"resolved_cells": res_cells, "breaks": breaks, "tolerance_points": MONOTONE_TOL_POINTS,
                                    "unresolved_cells": [plen_of(n) for n in names if summary["configs"][n].get("n_pairs") == 3 and not summary["configs"][n].get("resolved")],
                                    "verdict": cv}
    # crossing: the shortest prompt length whose gain is resolved and at least +10 %
    cross = [p for p, g in res_cells if g >= CROSSING_MIN_GAIN]
    summary["verdicts"]["crossing"] = {"prompt_length": min(cross) if cross else None, "min_gain_pct": CROSSING_MIN_GAIN,
                                       "verdict": (f"prompt {min(cross)} is the shortest prompt length with a resolved gain of at least +{CROSSING_MIN_GAIN:.0f} %" if cross else
                                                   ("none: no resolved cell reaches +10 %" if res_cells else "undecided: no resolved cell"))}

    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=str)
    lines = [f"q4b-swattn summary  passes: {', '.join(summary['passes_found'])}",
             f"{'config':45s} {'n':>1s} {'base TPS':>9s} {'canon TPS':>9s} {'gain %':>7s} {'t':>7s} {'res':>4s} {'TTFT b/c ms':>12s} {'min b/c':>15s} {'wall s':>7s} {'ovh':>5s} {'hw0':>4s}"]
    for n, e in summary["configs"].items():
        if e.get("n_pairs"):
            t = e["paired_t"]
            fr = [k for k, v in e["per_pass"].items() if v.get("from_raw")]
            if fr:
                lines.append(f"   ({n}: rebuilt from raw samples in {', '.join(fr)})")
            lines.append(f"{n:45s} {e['n_pairs']:>1d} {e['base_tps_mean']:9.2f} {e['canon_tps_mean']:9.2f} {e['gain_pct']:+7.2f} {(f'{t:7.2f}' if t is not None and math.isfinite(t) else str(t)):>7s} {('yes' if e['resolved'] else ('inc' if e['n_pairs'] < 3 else 'no')):>4s} {e['base_ttft_ms_mean']:5.0f}/{e['canon_ttft_ms_mean']:<6.0f} {e['base_min_tps']:7.2f}/{e['canon_min_tps']:<7.2f} {(e['wall_s_mean'] or 0):7.0f} {(e['overhead_tokens_mean'] if e['overhead_tokens_mean'] is not None else float('nan')):5.0f} {str(e['hwattn_ok_all']):>4s}")
        else:
            lines.append(f"{n:45s} 0 (no paired pass)")
    lines.append("incomplete: " + (", ".join(f"{i['name']} ({i['n_pairs']} pairs)" for i in summary["incomplete"]) or "none"))
    flagged = [(n, e["uneven_spread_runs"], e["caddy_health_event_runs"], e["anomalous_samples_total"]) for n, e in summary["configs"].items() if e.get("n_pairs")
               and (e["uneven_spread_runs"] or e["caddy_health_event_runs"] or e["anomalous_samples_total"])]
    lines.append("flags (uneven Caddy spread / Caddy health events / anomalous samples): " + ("; ".join(f"{n}: spread {u or '-'} health {c or '-'} anomalous {a}" for n, u, c, a in flagged) or "none"))
    for k, v in summary["verdicts"].items():
        lines.append(f"{k}: {json.dumps(v, default=str)}")
    txt = "\n".join(lines)
    with open(os.path.join(RES, "summary.txt"), "w") as f:
        f.write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
