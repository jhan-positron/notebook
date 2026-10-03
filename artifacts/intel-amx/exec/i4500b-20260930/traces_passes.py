#!/usr/bin/env python3
"""From the six Perfetto traces of exec/results/i4500b-20260930/traces write (a) passes.json: per decode pass (a
'forward' span with n_token_jobs <= 8 and a positive duration) the pass duration in ms, the Save K and Save V sums
on the main thread in us and the gap from the last Save V end to the pass end in us; (b) lanes14.json: every span of
decode pass index 14 (the pass in which the first 16-token block of decode completes) with its thread class, for the
wall-clock lanes figure of gen_round2.py. Threads: main = the thread that owns the Save K spans; worker = a thread
with Attention Pending or Attention Ready spans. Usage: traces_passes.py [TRACE_DIR]"""
import json, os, sys
from perfetto.trace_processor import TraceProcessor
TD = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/i4500b-20260930/traces"
LANE_PASS = 14
out, lanes = {}, {}
for arm in ("base", "fix", "fixS1"):
    for cell in ("tp2__2u", "tp4__4u"):
        tp = TraceProcessor(trace=os.path.join(TD, f"{arm}__{cell}.perfetto-trace"))
        q = lambda s: list(tp.query(s))
        passes = q("""select s.ts ts, s.dur dur, a.int_value ntj from slice s join args a on a.arg_set_id = s.arg_set_id
                      and a.key = 'debug.n_token_jobs' where s.name = 'forward' order by s.ts""")
        dec = [p for p in passes if p.ntj <= 8 and p.dur > 0]
        sk = q("select ts, dur from slice where name = 'Save K' order by ts")
        sv = q("select ts, dur from slice where name = 'Save V' order by ts")
        rows = []
        for p in dec:
            k = sum(s.dur for s in sk if p.ts <= s.ts < p.ts + p.dur) / 1000
            v = sum(s.dur for s in sv if p.ts <= s.ts < p.ts + p.dur) / 1000
            vs = [s for s in sv if p.ts <= s.ts < p.ts + p.dur]
            gap = (p.ts + p.dur - (vs[-1].ts + vs[-1].dur)) / 1000 if vs else 0
            rows.append({"pass_ms": p.dur / 1e6, "save_k_us": k, "save_v_us": v, "end_gap_us": gap})
        out[f"{arm}__{cell}"] = rows
        thr = {}
        for r in q("""select t.utid utid, s.name sname, count(*) n from slice s join thread_track tt on s.track_id = tt.id
                      join thread t on tt.utid = t.utid group by t.utid, s.name"""):
            thr.setdefault(r.utid, set()).add(r.sname)
        main = {u for u, s in thr.items() if "Save K" in s}
        work = {u for u, s in thr.items() if "Attention Pending" in s or "Attention Ready" in s}
        p = dec[LANE_PASS]
        sp = q(f"""select s.ts ts, s.dur dur, s.name name, tt.utid utid from slice s join thread_track tt on s.track_id = tt.id
                   where s.ts >= {p.ts} and s.ts < {p.ts + p.dur} and s.dur > 0 order by s.ts""")
        lanes[f"{arm}__{cell}"] = {"pass_index": LANE_PASS, "dur_ms": p.dur / 1e6, "n_workers": len(work),
            "spans": [{"t_us": (s.ts - p.ts) / 1000, "dur_us": s.dur / 1000, "name": s.name, "utid": s.utid,
                       "thread": "main" if s.utid in main else "worker" if s.utid in work else "other"} for s in sp]}
        tp.close()
        print(arm, cell, "passes", len(rows), "lane pass dur %.3f ms, %d spans, %d workers" % (p.dur / 1e6, len(lanes[f"{arm}__{cell}"]["spans"]), len(work)))
json.dump(out, open(os.path.join(TD, "passes.json"), "w"), indent=0)
json.dump(lanes, open(os.path.join(TD, "lanes14.json"), "w"))
