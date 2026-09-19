#!/usr/bin/env python3
"""Extract, from one Perfetto trace, the spans of one layer of one pass on every thread
(main, main helpers, attention workers) for a wall-clock lanes figure: t = 0 at the Save K
start of that layer; every span as (thread class, thread label, name, start_us, dur_us).
Also the same for one decode step. Writes <trace>.lanes.json next to the trace.
Usage: lanes.py TRACE [prefill_pass_index=2] [layer=10]
"""
import json
import sys

from perfetto.trace_processor import TraceProcessor

path = sys.argv[1]
PASS_IX = int(sys.argv[2]) if len(sys.argv) > 2 else 2
LAYER = int(sys.argv[3]) if len(sys.argv) > 3 else 10
tp = TraceProcessor(trace=path)
q = lambda s: list(tp.query(s))
passes = q("select s.ts ts, s.dur dur, a.int_value ntj from slice s join args a on a.arg_set_id=s.arg_set_id and a.key='debug.n_token_jobs' where s.name='forward' order by s.ts")
thr = {}
for r in q("""select t.utid utid, t.name tname, s.name sname, count(*) n from slice s join thread_track tt on s.track_id=tt.id
              join thread t on tt.utid=t.utid group by t.utid, s.name"""):
    thr.setdefault(r.utid, {"name": r.tname, "spans": {}})["spans"][r.sname] = r.n
main = {u for u, d in thr.items() if "Save K" in d["spans"]}
attn = {u for u, d in thr.items() if "Attention Pending" in d["spans"] or "Attention Ready" in d["spans"]}
helpers = {u for u, d in thr.items() if u not in attn and u not in main and any(k.startswith("kernel_") for k in d["spans"])}
def cls(u):
    return "main" if u in main else "attention" if u in attn else "helper" if u in helpers else "other"

def layer_window(p, layer):
    sk = q(f"select s.ts ts, s.dur dur from slice s where s.name='Save K' and s.ts>={p.ts} and s.ts<{p.ts+p.dur} order by s.ts")
    if layer >= len(sk):
        layer = len(sk) - 1
    k = sk[layer]
    # window: from 1 ms before this layer's Save K to the next layer's Save K (or +6 ms)
    t_end = sk[layer + 1].ts if layer + 1 < len(sk) else k.ts + 6_000_000
    t0 = k.ts - 1_500_000
    rows = q(f"""select s.name name, s.ts ts, s.dur dur, tt.utid utid from slice s join thread_track tt on s.track_id=tt.id
                 where s.depth <= 1 and s.name != 'forward' and s.ts < {t_end} and s.ts + s.dur > {t0} order by s.ts""")
    spans = [{"cls": cls(r.utid), "thread": thr[r.utid]["name"], "utid": r.utid, "name": r.name,
              "start_us": (r.ts - k.ts) / 1e3, "dur_us": r.dur / 1e3} for r in rows]
    return {"pass_index": PASS_IX, "n_token_jobs": p.ntj, "pass_ms": p.dur / 1e6, "layer": layer,
            "save_k_us": k.dur / 1e3, "window_us": [(t0 - k.ts) / 1e3, (t_end - k.ts) / 1e3], "spans": spans}

pre = [p for p in passes if p.ntj > 8]
dec = [p for p in passes if p.ntj <= 8]
out = {"trace": path, "threads": {"main": len(main), "attention": len(attn), "helpers": len(helpers)},
       "prefill": layer_window(pre[min(PASS_IX, len(pre) - 1)], LAYER) if pre else None,
       "decode": layer_window(dec[min(3, len(dec) - 1)], LAYER) if dec else None}
with open(path + ".lanes.json", "w") as f:
    json.dump(out, f)
w = out["prefill"]
print(f"{path}: prefill pass {w['pass_index']} layer {w['layer']} Save K {w['save_k_us']:.0f} us, {len(w['spans'])} spans; threads {out['threads']}")
