#!/usr/bin/env python3
"""spans.py - per-token span medians of the traced Tron AVX-form run (M8).

Reads exec/results/perf-model-20260903/m8-avx-1u-8192.perfetto-trace with the
perfetto trace processor and writes m8-spans.json. Medians are taken over the
decode forwards (slices named 'forward' shorter than 20 ms; the prefill forward
is longer). The main-thread split uses the two non-nesting forward-thread spans
'Prepare hardware matmul job' and 'Launch hardware matmul job' for the launch
bookkeeping, 'waiting for mbox' for the FPGA result waits, and the three logits
spans for the logits stage.
"""
import json
import os
import statistics as st

from perfetto.trace_processor import TraceProcessor

RES = os.path.expanduser("~/workspace/intel-AMX/exec/results/perf-model-20260903")
tp = TraceProcessor(trace=f"{RES}/m8-avx-1u-8192.perfetto-trace")
q = lambda s: list(tp.query(s))
out = {"source": "m8-avx-1u-8192.perfetto-trace (kill-switch run, prompt 8192, 256 tokens requested), perfetto trace processor; medians over decode forwards (dur < 20 ms)",
       "top_spans": [], "per_token_us": {}}
for r in q("SELECT name, count(*) n, sum(dur) tot, avg(dur) avgd FROM slice GROUP BY name ORDER BY tot DESC LIMIT 12"):
    out["top_spans"].append({"name": r.name, "count": r.n, "total_s": r.tot / 1e9, "avg_us": r.avgd / 1e3})
fw = sorted(r.dur for r in q("SELECT dur FROM slice WHERE name='forward'"))
out["forward_median_us"] = st.median(fw) / 1e3
out["forwards"] = len(fw)
NAMES = ("waiting for mbox", "Prepare hardware matmul job", "legacy hw_prepare", "tx submitting activation DMA request", "Launch hardware matmul job",
         "fill_logits_buffer", "notify_listener", "waiting_for_logits", "compute_forward_args", "Attention Ready", "attention: join", "Attention Pending")
for name in NAMES:
    rows = q(f"SELECT f.id fid, sum(s.dur) tot, count(*) n FROM slice f JOIN slice s ON s.ts >= f.ts AND s.ts < f.ts + f.dur AND s.name = '{name}' WHERE f.name='forward' AND f.dur < 20000000 GROUP BY f.id")
    tots = [r.tot for r in rows]
    ns = [r.n for r in rows]
    if tots:
        out["per_token_us"][name] = {"median_us": st.median(tots) / 1e3, "count_per_token": st.median(ns), "tokens": len(tots)}
tp.close()
pt = out["per_token_us"]
fpga = pt["waiting for mbox"]["median_us"]
launch = pt["Prepare hardware matmul job"]["median_us"] + pt["Launch hardware matmul job"]["median_us"]
logits = pt["fill_logits_buffer"]["median_us"] + pt["notify_listener"]["median_us"] + pt["waiting_for_logits"]["median_us"]
tot = fpga + launch + logits
out["main_thread_split"] = {
    "fpga_result_waits_us": fpga, "launch_and_prepare_us": launch, "logits_stage_us": logits,
    "shares_pct": {"fpga_waits": 100 * fpga / tot, "launch_prepare": 100 * launch / tot, "logits": 100 * logits / tot},
    "definition": "fpga = 'waiting for mbox'; launch = 'Prepare hardware matmul job' + 'Launch hardware matmul job' (non-nesting forward-thread spans; 'legacy hw_prepare' nests inside Prepare and 'tx submitting activation DMA request' is on the TX thread, both excluded); logits = fill_logits_buffer + notify_listener + waiting_for_logits",
    "note": "traced run; these spans sit on different threads, overlap in part with the attention phases and carry tracing overhead; shares are labeled est./traced",
}
json.dump(out, open(f"{RES}/m8-spans.json", "w"), indent=1)
print(json.dumps(out["main_thread_split"], indent=1))
print("forward median us", out["forward_median_us"], "forwards", out["forwards"])
