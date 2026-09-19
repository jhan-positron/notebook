#!/usr/bin/env python3
"""Read the Perfetto traces of exec/results/vnnik-trace-20260914 (or another
directory) and measure the K store of the main thread against the attention
workers' sections.

Words used here: pass = one scheduler forward() call (span "forward" with the
argument n_token_jobs; 1024 = a prefill pass of one user's prompt, 8 = one
decode step of the 8 users); Save K / Save V = the spans of model.hpp
save_k_impl / save_v_impl on the main thread (one per layer per pass);
Attention Pending = an attention worker's section over the pages written in
this pass (it starts only after Save K and Save V of the layer); Attention
Ready = a section over pages written in earlier passes; attention: join = the
per-KV-head fold of the workers' partial results.

Per trace and per pass kind (prefill / decode) the script reports:
  save_k_ms_per_pass   sum of Save K over the pass's layers (mean over passes)
  save_k_us_per_layer  mean Save K span
  save_k_ns_per_row    Save K per (token, KV head) row: span / (n_token_jobs * 8)
  save_v_*             the same for Save V
  pass_ms              forward span (mean over passes)
  save_k_share         save_k_ms_per_pass / pass_ms
  workers_busy_in_save_k  fraction of attention-worker threads with any span
                       overlapping a Save K window (0 = all idle = the store is
                       serial on the critical path)
  helpers_busy_in_save_k  the same for the main-helper threads (kernel_* spans)
  pending_gap_us       per layer: first Attention Pending start on any worker
                       minus Save V end (the hand-off latency after the saves)
Output: analysis.json and analysis.md in the results directory.
Usage: analyze.py [RESULTS_DIR]
"""
import glob
import json
import os
import statistics
import sys

from perfetto.trace_processor import TraceProcessor

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/vnnik-trace-20260914"
N_KV_HEADS = 8


def mean(xs):
    return statistics.fmean(xs) if xs else float("nan")


def analyze(path):
    tp = TraceProcessor(trace=path)
    q = lambda s: list(tp.query(s))
    passes = q("""select s.ts ts, s.dur dur, a.int_value ntj from slice s
                  join args a on a.arg_set_id = s.arg_set_id and a.key = 'debug.n_token_jobs'
                  where s.name = 'forward' order by s.ts""")
    # thread classes: main = the thread that owns the Save K spans; attention
    # workers = threads with Attention Pending/Ready spans; helpers = threads
    # with kernel_* spans that are not attention workers
    thr = {}
    for r in q("""select t.utid utid, t.name tname, s.name sname, count(*) n
                  from slice s join thread_track tt on s.track_id = tt.id
                  join thread t on tt.utid = t.utid group by t.utid, s.name"""):
        thr.setdefault(r.utid, {"name": r.tname, "spans": {}})["spans"][r.sname] = r.n
    main = [u for u, d in thr.items() if "Save K" in d["spans"]]
    attn = sorted(u for u, d in thr.items() if "Attention Pending" in d["spans"] or "Attention Ready" in d["spans"])
    helpers = sorted(u for u, d in thr.items() if u not in attn and u not in main and any(k.startswith("kernel_") for k in d["spans"]))
    spans = {}
    for name in ("Save K", "Save V", "Attention Pending", "Attention Ready", "attention: join"):
        spans[name] = q(f"""select s.ts ts, s.dur dur, tt.utid utid from slice s
                           join thread_track tt on s.track_id = tt.id where s.name = '{name}' order by s.ts""")
    kernel = q("""select s.ts ts, s.dur dur, tt.utid utid from slice s
                  join thread_track tt on s.track_id = tt.id where s.name like 'kernel_%' order by s.ts""")
    worker_spans = [r for name in ("Attention Pending", "Attention Ready", "attention: join") for r in spans[name]]
    worker_spans.sort(key=lambda r: r.ts)
    helper_spans = [r for r in kernel if r.utid in set(helpers)]

    def within(rows, t0, t1):
        return [r for r in rows if r.ts >= t0 and r.ts < t1]

    def overlapping_threads(rows, t0, t1):
        return {r.utid for r in rows if r.ts < t1 and r.ts + r.dur > t0}

    out = {"trace": os.path.basename(path), "n_passes": len(passes),
           "threads": {"main": len(main), "attention_workers": len(attn), "main_helpers": len(helpers)},
           "kinds": {}}
    for kind, sel in (("prefill", lambda p: p.ntj > 8), ("decode", lambda p: p.ntj <= 8)):
        ps = [p for p in passes if sel(p)]
        if not ps:
            continue
        per_pass = []
        for p in ps:
            t0, t1 = p.ts, p.ts + p.dur
            sk = within(spans["Save K"], t0, t1)
            sv = within(spans["Save V"], t0, t1)
            pend = within(spans["Attention Pending"], t0, t1)
            wb, hb, gaps = [], [], []
            for k in sk:
                wb.append(len(overlapping_threads(worker_spans, k.ts, k.ts + k.dur)) / max(1, len(attn)))
                hb.append(len(overlapping_threads(helper_spans, k.ts, k.ts + k.dur)) / max(1, len(helpers)))
            for v in sv:
                nxt = [x.ts for x in pend if x.ts >= v.ts + v.dur]
                if nxt:
                    gaps.append((min(nxt) - (v.ts + v.dur)) / 1e3)
            per_pass.append({
                "ts": p.ts, "n_token_jobs": p.ntj, "pass_ms": p.dur / 1e6, "n_layers": len(sk),
                "save_k_ms": sum(x.dur for x in sk) / 1e6, "save_v_ms": sum(x.dur for x in sv) / 1e6,
                "save_k_us_per_layer": mean([x.dur / 1e3 for x in sk]),
                "save_v_us_per_layer": mean([x.dur / 1e3 for x in sv]),
                "save_k_ns_per_row": mean([x.dur / (p.ntj * N_KV_HEADS) for x in sk]),
                "save_v_ns_per_row": mean([x.dur / (p.ntj * N_KV_HEADS) for x in sv]),
                "workers_busy_in_save_k": mean(wb), "helpers_busy_in_save_k": mean(hb),
                "pending_gap_us": mean(gaps),
                "attention_pending_ms_per_worker": sum(x.dur for x in pend) / 1e6 / max(1, len(attn)),
            })
        agg = {}
        for key in per_pass[0]:
            if key in ("ts",):
                continue
            vals = [pp[key] for pp in per_pass]
            agg[key] = mean(vals)
            if key in ("pass_ms", "save_k_ms", "save_k_us_per_layer"):
                agg[key + "_sd"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        agg["n_passes"] = len(per_pass)
        agg["save_k_share"] = agg["save_k_ms"] / agg["pass_ms"]
        agg["save_kv_share"] = (agg["save_k_ms"] + agg["save_v_ms"]) / agg["pass_ms"]
        agg["passes"] = per_pass
        out["kinds"][kind] = agg
    return out


def main_():
    traces = sorted(glob.glob(os.path.join(RES, "*.perfetto-trace")))
    results = [analyze(t) for t in traces]
    with open(os.path.join(RES, "analysis.json"), "w") as f:
        json.dump(results, f, indent=1)
    lines = ["# vnnik-trace analysis", "",
             "Per trace and pass kind: mean over passes. Rows = tokens x 8 KV heads. Busy fractions: share of "
             "threads with a span overlapping the Save K window (0 = idle).", ""]
    for kind in ("prefill", "decode"):
        lines += [f"## {kind}", "",
                  "| trace | passes | pass ms | Save K ms/pass | Save K us/layer | ns/row | Save V ms/pass | Save V us/layer | K share % | K+V share % | workers busy | helpers busy | gap after Save V us |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in results:
            a = r["kinds"].get(kind)
            if not a:
                continue
            lines.append(f"| {r['trace']} | {a['n_passes']} | {a['pass_ms']:.1f} | {a['save_k_ms']:.2f} | {a['save_k_us_per_layer']:.1f} | "
                         f"{a['save_k_ns_per_row']:.1f} | {a['save_v_ms']:.2f} | {a['save_v_us_per_layer']:.1f} | {100*a['save_k_share']:.2f} | "
                         f"{100*a['save_kv_share']:.2f} | {a['workers_busy_in_save_k']:.3f} | {a['helpers_busy_in_save_k']:.3f} | {a['pending_gap_us']:.1f} |")
        lines.append("")
    lines += ["## threads", ""]
    for r in results:
        lines.append(f"- {r['trace']}: main {r['threads']['main']}, attention workers {r['threads']['attention_workers']}, main helpers {r['threads']['main_helpers']}, passes {r['n_passes']}")
    md = "\n".join(lines) + "\n"
    with open(os.path.join(RES, "analysis.md"), "w") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main_()
