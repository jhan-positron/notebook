#!/usr/bin/env python3
"""gdn-20261120: predict what each proposed change would do for Qwen3.5 4B, from measured time shares.

Words used here:
- pass: one forward computation. A prefill pass processes one prompt chunk of every user (128 tokens per user).
  A decode step is a pass with one token per user.
- T1: mean wall time of a pass (attention statistics, field wall_cycles / forwards).
- attention busy time: the time of the attention jobs of the 8 full-attention layers on one attention worker in one
  pass, without the worker's waits for Q, K and V. Measured as T2 (field busy_cycles, summed over the workers) divided
  by the number of attention workers. T2 holds the scoring of the pages stored before the pass (full pages), the
  scoring of the pages that the pass itself writes (AVX-512 with or without AMX), the join, and the join wait.
- join wait: T5 (field join_wait_cycles), the time a worker waits in the join for the other workers. T5 is inside T2.
- full-page time: the part of the prefill busy time that grows with the K tokens in stored pages. Per user count, a
  least-squares line through the cells: T2 - T5 = fixed + c x (K tokens of the ready pass per pass). The full-page
  time is c x K tokens. The prefill factor of the attention kernel divides this time only. The decode factor is a
  ratio of whole attention times, so it divides the whole busy time of a decode step.
- attention wait: T3 (field wall_cycles_w0: wall time of the attention jobs on attention worker 0, waits included)
  minus the busy time. It holds the waits of worker 0 for Q and for K and V, and the difference between the busy time
  of worker 0 and the mean. tron has no timer for one of these waits alone. It stays in the rest.
- GDN wall: time from the first worker's start to the last worker's end of each of the 24 GDN operations, summed.
  Measured in a Perfetto trace (slice "GatedDeltaNet"); the attention statistics do not see GDN.
- rest: T1 - GDN wall - attention busy time. FPGA matrix multiplies, small host kernels and the attention wait.
- s: speedup factor of a kernel (old time / new time). Every s below is an ESTIMATE; see ASSUMPTIONS.

Model (critical-path form of Amdahl's law). The layers of a pass run one after another. In a GDN layer the FPGA
projections, the host work and the next FPGA projection run one after another, so a time saved in the GDN wall
shortens the pass by the same amount. In an attention layer the scoring of the full pages starts when Q is ready and
can run while the FPGA cards produce K and V of the pass. Assumption: with Part B on, this scoring still ends after
K and V are ready. Then a time saved in attention shortens the pass by the same amount too:
    T1_new = T1 - GDN_wall * (1 - 1/s_gdn) - attention_scaled * (1 - 1/s_attn) + rest * tax + attention_other * tax_attn
    attention_scaled = full-page time (prefill), attention busy time (decode)
    attention_other  = attention busy time - full-page time - join wait (prefill, Part B only): the AVX-512 scoring of
                       the pages of the pass, and the join. Under Part B the same workers run it at the AMX clock.
    TTFT_new = TTFT - passes * (T1 - T1_new)          (time between passes unchanged)
    ms_per_token_new = ms_per_token - (T1 - T1_new)   (time between decode steps unchanged)
"tax" is the slowdown of the other work of the 16 GDN threads when AMX lowers their core clock (measured on
delphi-3b35: 2.70 GHz under AVX-512, 2.40 GHz in tile phases, 1.90 GHz with live 512-bit values or in short turns of
tile and 512-bit work).

Scenarios:
  reorder   GDN prefill: chain replay by column half (AVX-512 only, bit-identical). No AMX.
  amx_gdn   GDN prefill: AMX block kernel (replaces reorder).
  amx_attn  attention kernel for 256-wide heads (prefill and decode).
  amx_both  amx_gdn + amx_attn.
  reorder_attn  reorder + amx_attn.

Inputs : exec/results/gdn-20261120/collected.json (written by collect.py)
Output : exec/results/gdn-20261120/predictions.json and a text table.
"""
import json
import sys

RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"

# Every factor here is an estimate (est.). "lo" and "hi" bound the plausible range, "mid" is the working value.
# The arithmetic behind each value is in design_numbers.py and on the page (section 4).
ASSUMPTIONS = {
    # Speedup of one GDN group step (convolution + recurrence on 2 value heads + norm and gate) in prefill.
    # Step today on a 2.70 GHz thread: 6.4 us (trace). See design_numbers.py for the arithmetic of each value.
    # reorder lo 1.4: the ratio timed on another CPU (design-checks/verify-cost/bench_gdn.run*.out), on today's step.
    "s_gdn_reorder": {"lo": 1.4, "mid": 2.1, "hi": 2.4},
    "s_gdn_amx": {"lo": 2.0, "mid": 3.2, "hi": 3.7},
    # GDN decode: a one-token chain has no block form; 1 or 2 of 16 tile rows would carry data; the state is FP32.
    "s_gdn_decode": {"lo": 1.0, "mid": 1.0, "hi": 1.0},
    # Attention kernel for 256-wide heads on delphi-3b35 (clock under AMX included).
    # prefill: 2.95 to 3.05 on delphi-3bda (fit of measured prefill times, design-checks/review/attn_prefill_fit.out),
    # times the clock ratio 0.76 or 0.96: mid 3.0 x 0.76, hi 3.05 x 0.96.
    # lo 1.6: a 256-wide page (64 KiB of K and V) does not fit L1; instruction and cache-line count
    # (design-checks/review/attn_256_l2_count.out).
    "s_attn_prefill": {"lo": 1.6, "mid": 2.3, "hi": 2.9},
    # decode: whole attention time 1.02 to 1.22 times shorter on delphi-3bda; the data wait does not follow the clock.
    "s_attn_decode": {"lo": 0.9, "mid": 1.0, "hi": 1.17},
    # Slowdown of the rest of a prefill pass when the 16 GDN threads run at the AMX clock (share of "rest").
    # 21 % of the rest is CPU work on the 16 GDN threads (est.); clock 2.40 GHz (mid) or 1.90 GHz (lo) instead of 2.70.
    "tax_rest_amx_gdn": {"lo": 0.088, "mid": 0.026, "hi": 0.0},
    # Slowdown of the other attention work of a prefill pass under Part B (busy time - full-page time - join wait).
    # The attention workers run it in the same job as the tile work, so it runs at the clock of the kernel:
    # 1.90 GHz (lo and mid: 2.70 / 1.90 - 1) or 2.40 GHz (hi: 2.70 / 2.40 - 1). The join wait is not CPU work of this kind.
    "tax_attn_other": {"lo": 0.421, "mid": 0.421, "hi": 0.125},
}
if len(sys.argv) > 1:
    ASSUMPTIONS.update(json.load(open(sys.argv[1])))

TRACE_OF = {
    "q35-tp4-1u-p1024": "t-1u-p1024", "q35-tp4-8u-p1024": "t-8u-p1024",
    "q35-tp4-1u-p4096": "t-1u-p4096", "q35-tp4-8u-p4096": "t-8u-p4096",
    "q35-tp4-1u-p8192": "t-1u-p8192", "q35-tp4-8u-p8192": "t-8u-p8192",
}
SCEN = {  # name -> (gdn factor key or None, attention on?, tax?)
    "reorder": ("s_gdn_reorder", False, False),
    "amx_gdn": ("s_gdn_amx", False, True),
    "amx_attn": (None, True, False),
    "reorder_attn": ("s_gdn_reorder", True, False),
    "amx_both": ("s_gdn_amx", True, True),
}


def cell_median(cells, cell, path):
    """Median over the runs of both arms of one value that collect.py derived."""
    vals = []
    for a in ("on", "off"):
        if a in cells[cell]:
            d = cells[cell][a]
            for k in path:
                d = d[k]
            vals.extend(d["values"])
    vals.sort()
    n = len(vals)
    return (vals[(n - 1) // 2] + vals[n // 2]) / 2.0


def full_page_times(col):
    """Prefill, per cell: (full-page time, join wait), in ms per pass and attention worker.
    Per user count, a least-squares line through the cells: busy time - join wait = fixed + c x K, where K is the number
    of K tokens that the ready pass scores per pass (pages stored before the pass). The full-page time is c x K."""
    cells, runs = col["cells"], col["runs"]
    pts = {}
    for cell in cells:
        names = [n for a in ("on", "off") if a in cells[cell] for n in cells[cell][a]["runs"]]
        k = {runs[n]["attn"]["prompt_or_mixed"]["totals"]["ready_avx_k_tokens"] / runs[n]["attn"]["prompt_or_mixed"]["forwards"]["forwards"] for n in names}
        assert len(k) == 1, (cell, k)   # a count: equal in every run of a cell
        workers = cell_median(cells, cell, ["prompt_or_mixed", "attn_workers"])
        busy = cell_median(cells, cell, ["prompt_or_mixed", "attn_busy_cpu_ms_per_forward"]) / workers
        join = cell_median(cells, cell, ["prompt_or_mixed", "attn_join_wait_cpu_ms_per_forward"]) / workers
        pts[cell] = (k.pop(), busy - join, join)
    out = {}
    for users in {cells[c]["on"]["users"] for c in cells}:
        group = [c for c in cells if cells[c]["on"]["users"] == users]
        assert len(group) >= 2, users
        mx = sum(pts[c][0] for c in group) / len(group)
        my = sum(pts[c][1] for c in group) / len(group)
        slope = sum((pts[c][0] - mx) * (pts[c][1] - my) for c in group) / sum((pts[c][0] - mx) ** 2 for c in group)
        for c in group:
            out[c] = (slope * pts[c][0], pts[c][2])
    return out


def main():
    col = json.load(open(RES + "/collected.json"))
    cells, traces = col["cells"], col["traces"]
    full_page = full_page_times(col)
    out = {"assumptions": ASSUMPTIONS, "cells": {}}
    print(f"{'cell':18} {'T1 pf':>7} {'GDN%':>5} {'att%':>5} {'rest%':>5} | {'TTFT s':>7} | {'reorder':>16} | {'amx_gdn':>16} | {'amx_attn':>16} | {'amx_both':>16} || "
          f"{'T1 dec':>6} {'GDN%':>5} {'att%':>5} | {'TPS':>6} | {'amx_attn':>18}")
    for cell in sorted(cells, key=lambda c: (cells[c]["on"]["users"], cells[c]["on"]["prompt_tokens"])):
        # the two arms run the same code path on this model (AMX never dispatches), so both are baseline samples
        arms = [a for a in ("on", "off") if a in cells[cell]]

        def med(path):
            vals = []
            for a in arms:
                d = cells[cell][a]
                for k in path:
                    d = d[k]
                vals.extend(d["values"])
            vals.sort()
            n = len(vals)
            return (vals[(n - 1) // 2] + vals[n // 2]) / 2.0, min(vals), max(vals), n

        users = cells[cell][arms[0]]["users"]
        prompt = cells[cell][arms[0]]["prompt_tokens"]
        t1_pf, _, _, n = med(["prompt_or_mixed", "forward_wall_ms"])
        t1_dec = med(["decode_like", "forward_wall_ms"])[0]
        n_attn = med(["prompt_or_mixed", "attn_workers"])[0]
        t3_pf = med(["prompt_or_mixed", "attn_w0_wall_ms_per_forward"])[0]
        t3_dec = med(["decode_like", "attn_w0_wall_ms_per_forward"])[0]
        attn_pf = med(["prompt_or_mixed", "attn_busy_cpu_ms_per_forward"])[0] / n_attn
        attn_dec = med(["decode_like", "attn_busy_cpu_ms_per_forward"])[0] / n_attn
        passes = med(["prompt_or_mixed", "forwards"])[0]
        ttft, ttft_lo, ttft_hi, _ = med(["ttft_max_s"])
        tps, tps_lo, tps_hi, _ = med(["decode_tps_per_user"])
        tr = traces.get(TRACE_OF.get(cell, ""), {}).get("kinds", {})
        if "prefill" not in tr or "decode" not in tr:
            print(f"{cell:18} no trace summary yet")
            continue
        gdn_pf = tr["prefill"]["gdn"]["wall_span_ms_per_pass"]
        gdn_dec = tr["decode"]["gdn"]["wall_span_ms_per_pass"]
        rest_pf = t1_pf - gdn_pf - attn_pf
        attn_full_pf, join_pf = full_page[cell]
        attn_other_pf = attn_pf - attn_full_pf - join_pf
        join_dec = med(["decode_like", "attn_join_wait_cpu_ms_per_forward"])[0] / n_attn
        rec = {
            "users": users, "prompt": prompt, "samples": n,
            "prefill": {"t1_ms": t1_pf, "gdn_ms": gdn_pf, "attn_ms": attn_pf, "attn_t3_ms": t3_pf, "attn_wait_ms": t3_pf - attn_pf,
                        "attn_full_ms": attn_full_pf, "attn_join_ms": join_pf, "attn_other_ms": attn_other_pf,
                        "rest_ms": rest_pf, "passes": passes,
                        "gdn_step_slow_us": tr["prefill"]["gdn"].get("slowest_thread_step_us"),
                        "gdn_step_median_us": tr["prefill"]["gdn"].get("median_thread_step_us"),
                        "gdn_per_thread_us": tr["prefill"]["gdn"].get("per_thread_step_us"),
                        "gdn_trace_share_pct": tr["prefill"]["gdn"]["wall_span_pct_of_pass"],
                        "ttft_s": ttft, "ttft_min_s": ttft_lo, "ttft_max_s": ttft_hi,
                        "trace_pass_ms": tr["prefill"]["mean_pass_ms"], "gdn_step_us": tr["prefill"]["gdn"]["cpu_us_per_group_step"],
                        "gdn_cpu_ms": tr["prefill"]["gdn"]["cpu_ms_per_pass"]},
            "decode": {"t1_ms": t1_dec, "gdn_ms": gdn_dec, "attn_ms": attn_dec, "attn_t3_ms": t3_dec, "attn_wait_ms": t3_dec - attn_dec,
                       "attn_join_ms": join_dec,
                       "rest_ms": t1_dec - gdn_dec - attn_dec,
                       "gdn_step_slow_us": tr["decode"]["gdn"].get("slowest_thread_step_us"),
                       "gdn_step_median_us": tr["decode"]["gdn"].get("median_thread_step_us"),
                       "gdn_per_thread_us": tr["decode"]["gdn"].get("per_thread_step_us"),
                       "gdn_trace_share_pct": tr["decode"]["gdn"]["wall_span_pct_of_pass"],
                       "tps": tps, "tps_min": tps_lo, "tps_max": tps_hi, "ms_per_token": 1000.0 / tps,
                       "trace_pass_ms": tr["decode"]["mean_pass_ms"], "gdn_step_us": tr["decode"]["gdn"]["cpu_us_per_group_step"],
                       "gdn_cpu_ms": tr["decode"]["gdn"]["cpu_ms_per_pass"]},
            "pred": {},
        }
        mst = 1000.0 / tps
        for level in ("lo", "mid", "hi"):
            p = {}
            for name, (gkey, attn_on, tax_on) in SCEN.items():
                d_pf = 0.0
                if gkey:
                    d_pf += gdn_pf * (1 - 1 / ASSUMPTIONS[gkey][level])
                if attn_on:
                    d_pf += attn_full_pf * (1 - 1 / ASSUMPTIONS["s_attn_prefill"][level])
                    d_pf -= attn_other_pf * ASSUMPTIONS["tax_attn_other"][level]
                if tax_on:
                    d_pf -= rest_pf * ASSUMPTIONS["tax_rest_amx_gdn"][level]
                d_dec = attn_dec * (1 - 1 / ASSUMPTIONS["s_attn_decode"][level]) if attn_on else 0.0
                p[name] = {"t1_prefill_ms": t1_pf - d_pf, "ttft_s": ttft - passes * d_pf / 1e3, "tps": 1000.0 / (mst - d_dec),
                           "t1_decode_ms": t1_dec - d_dec}
            rec["pred"][level] = p
        out["cells"][cell] = rec
        pc = lambda new, old: 100.0 * (new - old) / old
        P = rec["pred"]
        f = lambda s: f"{pc(P['mid'][s]['ttft_s'], ttft):+4.0f}% ({pc(P['lo'][s]['ttft_s'], ttft):+.0f}..{pc(P['hi'][s]['ttft_s'], ttft):+.0f})"
        print(f"{cell:18} {t1_pf:7.2f} {100 * gdn_pf / t1_pf:4.1f}% {100 * attn_pf / t1_pf:4.1f}% {100 * rest_pf / t1_pf:4.1f}% | {ttft:7.3f} | {f('reorder'):>16} | {f('amx_gdn'):>16} | "
              f"{f('amx_attn'):>16} | {f('amx_both'):>16} || {t1_dec:6.2f} {100 * gdn_dec / t1_dec:4.1f}% {100 * attn_dec / t1_dec:4.1f}% | {tps:6.1f} | "
              f"{pc(P['mid']['amx_attn']['tps'], tps):+5.1f}% ({pc(P['lo']['amx_attn']['tps'], tps):+.1f}..{pc(P['hi']['amx_attn']['tps'], tps):+.1f})")
    json.dump(out, open(RES + "/predictions.json", "w"), indent=1)


if __name__ == "__main__":
    main()
