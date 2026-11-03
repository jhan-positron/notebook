#!/usr/bin/env python3
"""glimci-20261017 summary: the three arms (base = nightly deb, amxoff = branch deb + kill switch, amxon = branch deb)
of the nightly's Glimmer tp4 @ 8 users cell, every pass, against the nightly's own run of 2026-10-17.

Reads exec/results/glimci-20261017/<tag>/perf.json (the driver's record: raw[0] holds the 80 per-request samples) and
exec/glimci-20261017/nightly-20261017-glimmer.json (the 80 samples parsed from the nightly log). Writes summary.md and
summary.json next to the results. Statistics: per pass the mean and the sample standard deviation over the 80 samples
(8 users x 10 rounds) of decode TPS per user and of TTFT (ms); per arm the mean over passes; the arm difference is
reported with the paired-by-pass t statistic (n = passes) when every arm has the same pass count, else as a plain
difference of means. Prefill proxy = prompt_length / TTFT, the nightly's own definition (testlib/tps.py)."""
import glob, json, os, re, statistics as st, sys

H = os.path.dirname(os.path.abspath(__file__))
RES = os.environ.get("RES", "/home/jhan/workspace/intel-AMX/exec/results/glimci-20261017")
ARMS = ["base", "amxoff", "amxon"]
NIGHTLY = json.load(open(os.path.join(H, "nightly-20261017-glimmer.json")))


def mean_sd(xs):
    xs = [float(x) for x in xs if x is not None]
    if not xs:
        return None, None, 0
    return st.mean(xs), (st.stdev(xs) if len(xs) > 1 else 0.0), len(xs)


def load_pass(tag):
    p = os.path.join(RES, tag, "perf.json")
    if not os.path.exists(p):
        return None
    r = json.load(open(p))
    raw = [x for x in r.get("raw", []) if x.get("model") == "ingested-meta-models--Muse-Glimmer-30B-tp4"]
    if not raw:
        return {"tag": tag, "status": "no raw record", "stop": r.get("stop")}
    x = raw[0]
    tps = x.get("tpss") or []
    ttft = x.get("ttfts_ms") or []
    pt = x.get("prompt_tokens") or []
    ct = x.get("cached_tokens") or []
    jp = os.path.join(RES, tag, "journal-prompts.txt")
    jtok = []
    jpre = []
    if os.path.exists(jp):
        for line in open(jp, errors="replace"):
            m = re.search(r"Request with (\d+) tokens in", line)
            if m:
                jtok.append(int(m.group(1)))
            m = re.search(r"Parsing the prompt took ([\d.]+) s", line)
            if m:
                jpre.append(float(m.group(1)))
    return {"tag": tag, "arm": tag.split("-")[0], "status": "ok" if len(tps) == 80 else f"{len(tps)} samples",
            "stop": r.get("stop"), "started": x.get("started"), "wall_s": x.get("wall_seconds"),
            "tps_mean": mean_sd(tps)[0], "tps_sd": mean_sd(tps)[1], "n": len(tps),
            "ttft_mean": mean_sd(ttft)[0], "ttft_sd": mean_sd(ttft)[1],
            "prefill_proxy": (1024.0 / (mean_sd(ttft)[0] / 1000.0)) if ttft else None,
            "prompt_tokens_mean": mean_sd(pt)[0], "prompt_tokens_min": min(pt) if pt else None, "prompt_tokens_max": max(pt) if pt else None,
            "cached_tokens_mean": mean_sd(ct)[0],
            "amx_busy_cycles": x.get("amx_busy_cycles"), "engine_requests": x.get("engine_requests"),
            "binary_check_ok": x.get("binary_check_ok"), "hwattn_unset_ok": x.get("hwattn_unset_ok"),
            "journal_prompt_tokens_mean": mean_sd(jtok)[0], "journal_prompt_tokens_n": len(jtok),
            "journal_prefill_s_mean": mean_sd(jpre)[0], "journal_prefill_s_n": len(jpre),
            "tps": tps, "ttft_ms": ttft}


def main():
    tags = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(RES, "*-pass*", "perf.json")))
    passes = [load_pass(t) for t in tags]
    passes = [p for p in passes if p]
    out = {"nightly": {k: NIGHTLY[k] for k in ("run", "date", "tps_mean", "tps_sd", "ttft_mean", "ttft_sd")}, "passes": passes, "arms": {}}
    lines = ["# glimci-20261017 summary", "",
             "Nightly reference (run %s, %s): TPS per user %.2f (sd %.2f over 80 samples), TTFT %.0f ms (sd %.0f), prefill proxy %.1f tok/s"
             % (NIGHTLY["run"], NIGHTLY["date"], NIGHTLY["tps_mean"], NIGHTLY["tps_sd"], NIGHTLY["ttft_mean"], NIGHTLY["ttft_sd"], 1024.0 / (NIGHTLY["ttft_mean"] / 1000.0)), "",
             "| pass | status | TPS per user mean (sd) | TTFT ms mean (sd) | prefill proxy tok/s | prompt tokens (server usage) mean [min-max] | journal prompt tokens mean (n) | journal prefill s mean (n) | AMX busy cycles (20 s probe) | requests per engine | binary ok | HW attn unset ok |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in passes:
        if p.get("status") not in ("ok",) and p.get("tps_mean") is None:
            lines.append("| %s | %s | | | | | | | | | | |" % (p["tag"], p.get("status")))
            continue
        lines.append("| %s | %s | %.2f (%.2f) | %.0f (%.0f) | %.1f | %.0f [%s-%s] | %s (%d) | %s (%d) | %s | %s | %s | %s |" % (
            p["tag"], p["status"], p["tps_mean"], p["tps_sd"], p["ttft_mean"], p["ttft_sd"], p["prefill_proxy"],
            p["prompt_tokens_mean"] or 0, p["prompt_tokens_min"], p["prompt_tokens_max"],
            ("%.0f" % p["journal_prompt_tokens_mean"]) if p["journal_prompt_tokens_mean"] else "-", p["journal_prompt_tokens_n"],
            ("%.3f" % p["journal_prefill_s_mean"]) if p["journal_prefill_s_mean"] else "-", p["journal_prefill_s_n"],
            f"{p['amx_busy_cycles']:,}" if isinstance(p["amx_busy_cycles"], int) else p["amx_busy_cycles"],
            p["engine_requests"], p["binary_check_ok"], p["hwattn_unset_ok"]))
    lines += ["", "## Arms (mean over passes)", "", "| arm | passes | TPS per user | sd over passes | TTFT ms | prefill proxy tok/s | vs nightly TPS | vs nightly TTFT |", "|---|---|---|---|---|---|---|---|"]
    for a in ARMS:
        ps = [p for p in passes if p.get("arm") == a and p.get("tps_mean") is not None]
        if not ps:
            continue
        tm = st.mean([p["tps_mean"] for p in ps]); tsd = st.stdev([p["tps_mean"] for p in ps]) if len(ps) > 1 else 0.0
        ttm = st.mean([p["ttft_mean"] for p in ps])
        out["arms"][a] = {"passes": [p["tag"] for p in ps], "tps_mean": tm, "tps_sd_passes": tsd, "ttft_mean": ttm, "prefill_proxy": 1024.0 / (ttm / 1000.0)}
        lines.append("| %s | %d | %.2f | %.2f | %.0f | %.1f | %+.1f %% | %+.1f %% |" % (a, len(ps), tm, tsd, ttm, 1024.0 / (ttm / 1000.0),
                     100.0 * (tm / NIGHTLY["tps_mean"] - 1), 100.0 * (ttm / NIGHTLY["ttft_mean"] - 1)))
    lines += ["", "## Differences", ""]
    def pair(a, b):
        pa = [p for p in passes if p.get("arm") == a and p.get("tps_mean") is not None]
        pb = [p for p in passes if p.get("arm") == b and p.get("tps_mean") is not None]
        if not pa or not pb:
            return None
        ma, mb = st.mean([p["tps_mean"] for p in pa]), st.mean([p["tps_mean"] for p in pb])
        ta, tb = st.mean([p["ttft_mean"] for p in pa]), st.mean([p["ttft_mean"] for p in pb])
        d = {"a": a, "b": b, "tps_delta_pct": 100.0 * (mb / ma - 1), "ttft_delta_pct": 100.0 * (tb / ta - 1), "tps_a": ma, "tps_b": mb, "ttft_a": ta, "ttft_b": tb}
        if len(pa) == len(pb) and len(pa) > 1:
            diffs = [y["tps_mean"] - x["tps_mean"] for x, y in zip(pa, pb)]
            sd = st.stdev(diffs)
            d["paired_t"] = (st.mean(diffs) / (sd / len(diffs) ** 0.5)) if sd > 0 else float("inf")
            d["n"] = len(diffs)
        return d
    for a, b in (("base", "amxoff"), ("amxoff", "amxon"), ("base", "amxon")):
        d = pair(a, b)
        if d:
            out.setdefault("diffs", []).append(d)
            lines.append("- %s -> %s: TPS %.2f -> %.2f (%+.1f %%), TTFT %.0f -> %.0f ms (%+.1f %%)%s" % (
                a, b, d["tps_a"], d["tps_b"], d["tps_delta_pct"], d["ttft_a"], d["ttft_b"], d["ttft_delta_pct"],
                (", paired t over %d passes = %.1f" % (d["n"], d["paired_t"])) if "paired_t" in d else ""))
    open(os.path.join(RES, "summary.md"), "w").write("\n".join(lines) + "\n")
    json.dump(out, open(os.path.join(RES, "summary.json"), "w"), indent=1, default=str)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
