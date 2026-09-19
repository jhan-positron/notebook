#!/usr/bin/env python3
"""Spread of the single Save K spans (one per prefill layer) over the whole traced run:
count, mean, population standard deviation, min, max, in us. analysis.json keeps only
per-pass means; section 2.2 of shared-save-animation.html quotes these single-span numbers.
Run on claude-box (python perfetto TraceProcessor); writes savek_spans.json next to this script.
Usage: savek_spans.py  (traces: exec/results/vnnik2-trace-20260915/{vnni0,ab,b,a}-tp2)"""
import json, os, statistics
from perfetto.trace_processor import TraceProcessor
RES = "/home/jhan/workspace/intel-AMX/exec/results"
out = {}
for d, n in [("vnnik2-trace-20260915", "vnni0-tp2"), ("vnnik2-trace-20260915", "ab-tp2"), ("vnnik2-trace-20260915", "b-tp2"), ("vnnik2-trace-20260915", "a-tp2")]:
    tp = TraceProcessor(trace=f"{RES}/{d}/{n}.perfetto-trace")
    q = lambda s: list(tp.query(s))
    passes = q("select s.ts ts, s.dur dur, a.int_value ntj from slice s join args a on a.arg_set_id=s.arg_set_id and a.key='debug.n_token_jobs' where s.name='forward' order by s.ts")
    spans = []
    for p in [p for p in passes if p.ntj > 8]:
        spans += [r.dur / 1e3 for r in q(f"select dur from slice where name='Save K' and ts>={p.ts} and ts<{p.ts+p.dur}")]
    out[n] = {"n": len(spans), "mean": statistics.mean(spans), "sd": statistics.pstdev(spans), "min": min(spans), "max": max(spans)}
    print(n, out[n])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "savek_spans.json"), "w"), indent=1)
