#!/usr/bin/env python3
"""Read the Perfetto traces of exec/results/issue4500-20260918/traces (block m3) with the python
TraceProcessor (works on claude-agentsrv, not on 3bda) and measure, per decode pass, where the time
of the FPGA-attention decode step goes, base vs headoff vs vnni.

Words used here: pass = one scheduler forward() call ('forward' span, category scheduler, argument
n_token_jobs: 1024 = a prefill pass of one user's prompt, <= 8 = one decode step of the batch); main =
the thread that owns the 'Save K' spans (the plugin's run() thread); attention workers = threads with
'Attention Pending' / 'Attention Ready' spans; burst pass = a decode pass with gof_rodeo spans (a GOF =
group of four tokens completed for every user: every 4th step in runtron); hw wait = the workers'
spin on the FPGA result ('attention: hw wait'); coop drain = 'wait_coop_gof' on main at forward end.
Per trace and per decode pass the script records: pass duration; Save K / Save V sums (main); the gap
from the last Save V end to the forward end; wait_coop_gof; gof_rodeo count and sum by thread class;
gof_populate count and sum (category B traces only); Attention Pending / Ready sums and the max per
worker; 'attention: hw wait' sum and max; prep_hw_attn / launch_hw_attn sums; construct_hw_plan.
Output: analysis.json and analysis.md next to the traces, plus lanes-<trace>-<pass>.json (every span of
one burst pass and one non-burst pass, for the wall-clock lanes figure).
Usage: trace_analyze.py [TRACE_DIR]
"""
import glob
import json
import os
import statistics
import sys

from perfetto.trace_processor import TraceProcessor

TD = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/issue4500-20260918/traces"
NAMES = ["Save K", "Save V", "wait_coop_gof", "gof_rodeo", "gof_populate", "xfer_gof", "prepare_for_dma",
         "Attention Pending", "Attention Ready", "attention: join", "attention: hw wait", "prep_hw_attn",
         "launch_hw_attn", "attn_launcher_cb", "construct_hw_plan", "poll_dma_completions", "compute_forward_args",
         "finalize_ranges", "Free scratchpads", "assemble attention plan"]


def mean(xs):
    return statistics.fmean(xs) if xs else None


def analyze(path):
    tp = TraceProcessor(trace=path)
    q = lambda s: list(tp.query(s))
    passes = q("""select s.ts ts, s.dur dur, a.int_value ntj from slice s
                  join args a on a.arg_set_id = s.arg_set_id and a.key = 'debug.n_token_jobs'
                  where s.name = 'forward' order by s.ts""")
    thr = {}
    for r in q("""select t.utid utid, t.tid tid, t.name tname, s.name sname, count(*) n
                  from slice s join thread_track tt on s.track_id = tt.id
                  join thread t on tt.utid = t.utid group by t.utid, s.name"""):
        thr.setdefault(r.utid, {"name": r.tname, "tid": r.tid, "spans": {}})["spans"][r.sname] = r.n
    main = {u for u, d in thr.items() if "Save K" in d["spans"]}
    attn = {u for u, d in thr.items() if "Attention Pending" in d["spans"] or "Attention Ready" in d["spans"]}

    def cls(utid):
        if utid in main:
            return "main"
        if utid in attn:
            return "worker"
        return "other:" + str(thr.get(utid, {}).get("name"))
    names_sql = ",".join("'%s'" % n.replace("'", "''") for n in NAMES)
    spans = q(f"""select s.ts ts, s.dur dur, s.name name, tt.utid utid from slice s
                  join thread_track tt on s.track_id = tt.id where s.name in ({names_sql}) order by s.ts""")
    out = {"trace": os.path.basename(path), "n_passes": len(passes), "threads": {"main": len(main), "workers": len(attn)}, "passes": []}
    decode = [p for p in passes if p.ntj is not None and p.ntj <= 8]
    for i, p in enumerate(decode):
        t0, t1 = p.ts, p.ts + p.dur
        inside = [s for s in spans if s.ts >= t0 and s.ts < t1]
        rec = {"index": i, "ts": t0, "dur_ms": p.dur / 1e6, "ntj": p.ntj}
        by = {}
        for s in inside:
            k = (s.name, cls(s.utid))
            d = by.setdefault(k, {"n": 0, "sum_us": 0.0, "max_us": 0.0, "per_thread": {}})
            d["n"] += 1; d["sum_us"] += s.dur / 1e3; d["max_us"] = max(d["max_us"], s.dur / 1e3)
            d["per_thread"][s.utid] = d["per_thread"].get(s.utid, 0.0) + s.dur / 1e3
        rec["spans"] = {f"{k[0]}@{k[1]}": {"n": v["n"], "sum_us": v["sum_us"], "max_us": v["max_us"],
                                         "max_thread_us": max(v["per_thread"].values()) if v["per_thread"] else 0.0,
                                         "n_threads": len(v["per_thread"])} for k, v in by.items()}
        savev = [s for s in inside if s.name == "Save V" and s.utid in main]
        rec["save_v_end_to_pass_end_us"] = (t1 - max(s.ts + s.dur for s in savev)) / 1e3 if savev else None
        rec["burst"] = any(s.name == "gof_rodeo" for s in inside)
        out["passes"].append(rec)
    # per-kind means
    def agg(sel):
        rows = [r for r in out["passes"] if sel(r)]
        keys = set(k for r in rows for k in r["spans"])
        res = {"n_passes": len(rows), "dur_ms": mean([r["dur_ms"] for r in rows])}
        for k in sorted(keys):
            res[k] = {"sum_us": mean([r["spans"].get(k, {}).get("sum_us", 0.0) for r in rows]),
                      "n": mean([r["spans"].get(k, {}).get("n", 0) for r in rows]),
                      "max_thread_us": mean([r["spans"].get(k, {}).get("max_thread_us", 0.0) for r in rows])}
        res["save_v_end_to_pass_end_us"] = mean([r["save_v_end_to_pass_end_us"] for r in rows if r["save_v_end_to_pass_end_us"] is not None])
        return res
    out["decode_all"] = agg(lambda r: True)
    out["decode_burst"] = agg(lambda r: r["burst"])
    out["decode_quiet"] = agg(lambda r: not r["burst"])
    # lanes dumps: first burst pass after index 4 and the following quiet pass
    lanes = {}
    for kind, sel in (("burst", lambda r: r["burst"] and r["index"] >= 4), ("quiet", lambda r: not r["burst"] and r["index"] >= 5)):
        cand = [r for r in out["passes"] if sel(r)]
        if cand:
            r = cand[0]; t0 = r["ts"]; t1 = t0 + int(r["dur_ms"] * 1e6)
            lanes[kind] = {"pass_index": r["index"], "dur_ms": r["dur_ms"],
                           "spans": [{"t_us": (s.ts - t0) / 1e3, "dur_us": s.dur / 1e3, "name": s.name, "thread": cls(s.utid), "utid": s.utid}
                                     for s in spans if s.ts >= t0 and s.ts < t1]}
    return out, lanes


def main_():
    results = []
    for path in sorted(glob.glob(os.path.join(TD, "*.perfetto-trace"))):
        try:
            out, lanes = analyze(path)
        except Exception as e:  # keep going over the other traces
            results.append({"trace": os.path.basename(path), "error": str(e)}); continue
        results.append(out)
        for kind, d in lanes.items():
            json.dump(d, open(os.path.join(TD, f"lanes-{os.path.basename(path).replace('.perfetto-trace', '')}-{kind}.json"), "w"))
    json.dump(results, open(os.path.join(TD, "analysis.json"), "w"), indent=1)
    lines = ["# issue4500 trace analysis", "", "Per trace, mean over decode passes (n_token_jobs <= 8): pass ms; Save K / Save V sums on main (us); wait_coop_gof (us); gof_rodeo count and sum by thread class; Attention Pending / Ready max per worker (us); hw wait max (us).", "",
             "| trace | passes | burst | pass ms | SaveK us | SaveV us | SaveV end->pass end us | coop us | rodeo n (main/worker) | rodeo us (main/worker) | populate n | populate us | Pending max/worker us | Ready max/worker us | hw wait max us | launch us |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    def fmt(v, nd=0):
        return "-" if v is None else f"{v:.{nd}f}"
    for r in results:
        if "error" in r:
            lines.append(f"| {r['trace']} | error: {r['error'][:80]} |"); continue
        for kind in ("decode_all", "decode_burst", "decode_quiet"):
            a = r[kind]
            def g(k, f="sum_us"):
                return fmt(a.get(k, {}).get(f))
            lines.append(f"| {r['trace']} | {a['n_passes']} | {kind.split('_')[1]} | {fmt(a['dur_ms'], 3)} | {g('Save K@main')} | {g('Save V@main')} | {fmt(a['save_v_end_to_pass_end_us'])} | {g('wait_coop_gof@main')} | {g('gof_rodeo@main','n')}/{g('gof_rodeo@worker','n')} | {g('gof_rodeo@main')}/{g('gof_rodeo@worker')} | {g('gof_populate@main','n')}+{g('gof_populate@worker','n')} | {g('gof_populate@main')}+{g('gof_populate@worker')} | {g('Attention Pending@worker','max_thread_us')} | {g('Attention Ready@worker','max_thread_us')} | {g('attention: hw wait@worker','max_thread_us')} | {g('launch_hw_attn@main')} |")
    open(os.path.join(TD, "analysis.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


main_()
