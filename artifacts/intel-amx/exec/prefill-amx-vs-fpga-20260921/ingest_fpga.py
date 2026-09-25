#!/usr/bin/env python3
"""Rows for the prefill page from the CI-harness campaign files.

Reads every <tag>/perf.json under
  exec/results/q4b-swattn-20260919/   (2026-09-20: base = nightly deb + CPU attention, canon = canonical deb + CPU attention)
  exec/results/q4b-fpga-20260921/     (2026-09-21/22: fpgabase, fpgacanon, canon, cold cells, optional vnnik arms)
and writes fpga-campaign-rows.json next to this script: one row per (tag, cell) with the harness TTFT mean, the per-request
TTFT list summarised (median, p95), the decode TPS, the prefix-cache share, the per-engine request spread, the Caddy health
events, the attention-mode verdicts and the deb version.  gen_page.py reads that file.

Words: TTFT = time to first token, client side (ms); cold = the first cell of a driver run (fresh engines, empty prefix cache).
"""
import glob
import json
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
R = "/home/jhan/workspace/intel-AMX/exec/results"
CAMPAIGNS = {
    "q4b-swattn-20260919": {"base": ("cpu", "avx", "nightly deb 2026.09.18-3faba6d0"), "canon": ("cpu", "canon", "canonical deb 0594dc54")},
    "q4b-fpga-20260921": {"base": ("cpu", "avx", "nightly deb 2026.09.18-3faba6d0"), "canon": ("cpu", "canon", "canonical deb 0594dc54"),
                          "vnnik": ("cpu", "vnnik", "VNNI-K deb 29a8a547"),
                          "fpgabase": ("fpga", "avx", "nightly deb 2026.09.18-3faba6d0"), "fpgacanon": ("fpga", "canon", "canonical deb 0594dc54"),
                          "fpgavnnik": ("fpga", "vnnik", "VNNI-K deb 29a8a547")},
}


def pct(xs, q):
    if not xs:
        return None
    ys = sorted(xs)
    k = (len(ys) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (k - lo)


def main():
    rows = []
    for camp, arms in CAMPAIGNS.items():
        for pj in sorted(glob.glob(f"{R}/{camp}/*/perf.json")):
            tag = os.path.basename(os.path.dirname(pj))
            if tag.endswith("-failed1") or tag.startswith("prev-") or tag == "check-mode":
                continue
            if tag.startswith("check-8u-p"):      # the 2026-09-19 check cell: canon deb, CPU attention, 8 users, one cold cell
                arm = "canon"
            else:
                arm = tag.split("-")[0]
            if arm not in arms:
                continue
            attention, kernel, deb = arms[arm]
            d = json.load(open(pj))
            ver = (d.get("versions") or {}).get("Tron (package)")
            cold_tag = "-cold" in tag or tag.startswith("check-8u-p")
            m = re.search(r"-pass(\d+)$", tag)
            pass_no = int(m.group(1)) if m else None
            results = {x["name"]: x for x in d.get("results", [])}
            for i, r in enumerate(d.get("raw", [])):
                tt = [float(x) for x in (r.get("ttfts_ms") or [])]
                if not tt:
                    continue
                pt = r.get("prompt_tokens") or []
                ct = r.get("cached_tokens") or []
                cache = (100.0 * sum(ct) / sum(pt)) if pt and sum(pt) else None
                res = results.get(r["name"], {})
                rows.append(dict(
                    campaign=camp, tag=tag, arm=arm, pass_no=pass_no, attention=attention, kernel=kernel, deb=deb, tron_version=ver,
                    started=r.get("started"), prompt_length=r["prompt_length"], n_requests=len(tt),
                    cold=bool(cold_tag or i == 0),   # the first cell of a run meets fresh engines
                    ttft_mean_ms=round(statistics.mean(tt), 1), ttft_median_ms=round(statistics.median(tt), 1),
                    ttft_p95_ms=round(pct(tt, 0.95), 1), ttft_min_ms=min(tt), ttft_max_ms=max(tt),
                    ttft_harness_ms=res.get("ttft_mean"),
                    tps_mean=round(res["tps_mean"], 2) if res.get("tps_mean") is not None else None,
                    cache_hit_pct=round(cache, 2) if cache is not None else None,
                    prompt_tokens_mean=round(statistics.mean(pt), 1) if pt else None,
                    engine_requests=r.get("engine_requests"), caddy_health_events=r.get("caddy_health_events"),
                    anomalous_samples=r.get("anomalous_samples"), wall_seconds=r.get("wall_seconds"),
                    hwattn_ok=r.get("hwattn_ok"), hwattn_unset_ok=r.get("hwattn_unset_ok"), amx_busy_cycles=r.get("amx_busy_cycles"),
                    file=pj.replace("/home/jhan/workspace/intel-AMX/", ""),
                ))
    out = os.path.join(HERE, "fpga-campaign-rows.json")
    json.dump(rows, open(out, "w"), indent=1)
    print(out, len(rows), "rows")
    for x in rows:
        print(f'{x["campaign"][:10]} {x["tag"]:22s} {x["attention"]:4s} {x["kernel"]:5s} p={x["prompt_length"]:>5} cold={int(x["cold"])} '
              f'ttft mean {x["ttft_mean_ms"]:>8} med {x["ttft_median_ms"]:>8} p95 {x["ttft_p95_ms"]:>8} harness {x["ttft_harness_ms"]} '
              f'tps {x["tps_mean"]} cache {x["cache_hit_pct"]} eng {x["engine_requests"]} hw0={x["hwattn_ok"]} hwunset={x["hwattn_unset_ok"]}')


if __name__ == "__main__":
    main()
