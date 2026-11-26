#!/usr/bin/env python3
"""Review finding R1: what the attention timers hold, and Part B under four assumptions about the scaled time.

Words used here:
- pass: one forward computation. A prefill pass holds 128 prompt tokens per user. A decode step holds 1 token per user.
- T1: wall time of a pass (field wall_cycles of the forwards record, per pass).
- T2, busy time: field busy_cycles. Time of the attention jobs on a worker: both software passes and the join.
  It leaves out the wait for Q at the start of a job and the wait for K and V between the two software passes.
- T5, join wait: field join_wait_cycles. Time a worker waits in the join for the other workers. T5 is inside T2.
- compute: T2 minus T5 (tron's README calls it "compute plus fold").
- T3: field wall_cycles_w0. Wall time of the attention jobs on attention worker 0, every wait included.
- ready pass, pending pass: the two software passes of an attention job. The ready pass scores the pages that were
  stored before the pass. The pending pass scores the pages that the pass in progress writes.
- K token: one stored K row that a query is scored against. Counted per software pass (ready, pending).
- page visit: one query token on one KV page of one KV head (the "page unit" of the page).
- factor s: old time / new time of the AMX attention kernel (est.), low / working / high.

What it computes, per cell (users x prompt length), from the 6 runs of the cell (median, as predict.py does):
1. the timers per prefill pass and per decode step, all divided by the 40 attention workers where they are sums;
2. the K tokens and page visits of the ready pass (full pages) and of the pending pass (pages written by the pass);
3. how the join wait and the compute time change with the prompt length;
4. a line through the three prompt lengths: compute per pass = fixed + c x (K tokens in full pages per pass);
5. the Part B prediction (TTFT and decode speed) and the prediction of Parts A and B, when the factor divides
   (a) the whole busy time,
   (b) the full-page share of the busy time (share of the K tokens that the ready pass scores),
   (c) the full-page share of the compute time (the join wait stays),
   (d) the part of the compute time that grows with the full-page K tokens (line of step 4; the rest stays).
   Then the proposed model (prefill as (d), decode as (a)) and its sensitivity (prefill as (c)).
   predictions.json must equal variant (a) or the proposed model. This is the check of the script.
6. A check of the variants against a measurement: the same statistics of two other models on delphi-3bda, with the
   128-wide AMX attention kernel on and off (one run per arm, 8 users, software attention, 2026-10-02).

Inputs : exec/results/gdn-20261120/collected.json   (runs[*].attn: totals and forwards records of every run log,
                                                      cells[*]: medians per cell, traces[*]: GDN wall)
         exec/results/gdn-20261120/predictions.json (the factors, and the predicted values for the check)
         exec/results/attnstats-20261002/exit-reports.txt (step 6: the [attn-stats] lines of 12 runs on delphi-3bda)
Output : text on stdout. Nothing is written.
"""
import json
import re
import sys

RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"
AB = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/exec/results/attnstats-20261002/exit-reports.txt"
col = json.load(open(RES + "/collected.json"))
pred = json.load(open(RES + "/predictions.json"))
A = pred["assumptions"]
runs, cells, traces = col["runs"], col["cells"], col["traces"]
order = sorted(cells, key=lambda c: (cells[c]["on"]["users"], cells[c]["on"]["prompt_tokens"]))
KINDS = (("prefill", "prompt_or_mixed"), ("decode", "decode_like"))
LEVELS = ("lo", "mid", "hi")


def median(vals):
    v = sorted(vals)
    n = len(v)
    return (v[(n - 1) // 2] + v[n // 2]) / 2.0


def cell_runs(cell):
    return [runs[name] for arm in ("on", "off") for name in cells[cell][arm]["runs"]]


def per_run(cell, cls, fn):
    """fn(totals, forwards, tsc_hz) for each of the runs of the cell."""
    return [fn(r["attn"][cls]["totals"], r["attn"][cls]["forwards"], r["attn"]["summary"]["tsc_hz"]) for r in cell_runs(cell)]


def agg(cell, path):
    """Median over the runs of both arms of a value that collect.py derived (same rule as predict.py)."""
    vals = []
    for arm in ("on", "off"):
        d = cells[cell][arm]
        for k in path:
            d = d[k]
        vals.extend(d["values"])
    return median(vals)


def label(cell):
    return f"{cells[cell]['on']['users']} user{'s' if cells[cell]['on']['users'] > 1 else ' '}, prompt {cells[cell]['on']['prompt_tokens']:>5,}"


# ------------------------------------------------------------------ 1. timers, 2. K tokens
M = {}
n_runs = 0
for cell in order:
    M[cell] = {"users": cells[cell]["on"]["users"], "prompt": cells[cell]["on"]["prompt_tokens"]}
    n_runs += len(cell_runs(cell))
    for kind, cls in KINDS:
        ms = lambda cyc, f, hz: cyc / f["forwards"] / hz * 1e3
        workers = per_run(cell, cls, lambda t, f, hz: (f["n_attn_workers_min"], f["n_attn_workers_max"]))
        assert set(workers) == {(40, 40)}, workers
        assert all(per_run(cell, cls, lambda t, f, hz: t["ready_avx_visits"] == t["ready_avx_full_page_visits"])), "a ready visit is not a full page"
        assert all(per_run(cell, cls, lambda t, f, hz: t["ready_amx_k_tokens"] + t["pending_amx_k_tokens"] == 0))
        assert all(per_run(cell, cls, lambda t, f, hz: t["ready_empty_visits"] + t["pending_empty_visits"] == 0))
        m = {
            "t1": median(per_run(cell, cls, lambda t, f, hz: ms(f["wall_cycles"], f, hz))),
            "busy": median(per_run(cell, cls, lambda t, f, hz: ms(t["busy_cycles"], f, hz) / 40)),
            "join": median(per_run(cell, cls, lambda t, f, hz: ms(t["join_wait_cycles"], f, hz) / 40)),
            "t3": median(per_run(cell, cls, lambda t, f, hz: ms(t["wall_cycles_w0"], f, hz))),
            "k_ready": median(per_run(cell, cls, lambda t, f, hz: t["ready_avx_k_tokens"] / f["forwards"])),
            "k_pend": median(per_run(cell, cls, lambda t, f, hz: t["pending_avx_k_tokens"] / f["forwards"])),
            "v_ready": median(per_run(cell, cls, lambda t, f, hz: t["ready_avx_visits"] / f["forwards"])),
            "v_pend": median(per_run(cell, cls, lambda t, f, hz: t["pending_avx_visits"] / f["forwards"])),
            "v_pend_full": median(per_run(cell, cls, lambda t, f, hz: t["pending_avx_full_page_visits"] / f["forwards"])),
        }
        m["comp"] = m["busy"] - m["join"]
        m["k_full_share"] = m["k_ready"] / (m["k_ready"] + m["k_pend"])
        m["v_full_share"] = m["v_ready"] / (m["v_ready"] + m["v_pend"])
        # the same inputs as predict.py, to keep variant (a) identical to predictions.json
        m["busy_predict"] = agg(cell, [cls, "attn_busy_cpu_ms_per_forward"]) / agg(cell, ["prompt_or_mixed", "attn_workers"])
        assert abs(m["busy_predict"] - m["busy"]) < 1e-9, (cell, kind)
        M[cell][kind] = m

print(f"Source: collected.json, {n_runs} runs, 6 per cell. In every run the attention ran on 40 workers.")
print("Checked in every run and in both pass kinds: every page visit of the ready pass scored a full page (64 K tokens),")
print("the AMX kernel scored 0 K tokens, and no visit was empty.")
for kind, _ in KINDS:
    what = "one prefill pass" if kind == "prefill" else "one decode step"
    print(f"\n1. Timers of {what} (ms, median of 6 runs). busy, join wait and compute are means over the 40 workers.")
    print(f"{'cell':24} {'T1 pass':>8} {'T2 busy':>8} {'T5 join':>8} {'T5/T2':>6} {'compute':>8} {'T3 w0':>8} {'T3-T2 (page: attention wait)':>29}")
    for cell in order:
        m = M[cell][kind]
        print(f"{label(cell):24} {m['t1']:8.3f} {m['busy']:8.3f} {m['join']:8.3f} {100 * m['join'] / m['busy']:5.1f}% {m['comp']:8.3f} {m['t3']:8.3f} {m['t3'] - m['busy']:29.3f}")
for kind, _ in KINDS:
    what = "one prefill pass" if kind == "prefill" else "one decode step"
    print(f"\n2. K tokens and page visits of {what}, by software pass (counts, equal in all 6 runs of a cell).")
    print(f"{'cell':24} {'K ready (full pages)':>20} {'K pending':>10} {'full-page share of K':>21} {'visits ready':>13} {'visits pending':>15} {'of them full':>13} {'full-page share of visits':>26}")
    for cell in order:
        m = M[cell][kind]
        print(f"{label(cell):24} {m['k_ready']:20,.0f} {m['k_pend']:10,.0f} {100 * m['k_full_share']:20.2f}% {m['v_ready']:13,.1f} {m['v_pend']:15,.1f} {m['v_pend_full']:13,.1f} {100 * m['v_full_share']:25.2f}%")

# ------------------------------------------------------------------ 3. growth with the prompt length
print("\n3. Growth from prompt 1,024 to prompt 8,192 (ratio of the values of table 1).")
print(f"{'':24} {'K in full pages':>16} {'compute':>8} {'join wait':>10}")
for kind, _ in KINDS:
    for users in (1, 8):
        lo = [c for c in order if M[c]["users"] == users and M[c]["prompt"] == 1024][0]
        hi = [c for c in order if M[c]["users"] == users and M[c]["prompt"] == 8192][0]
        a, b = M[lo][kind], M[hi][kind]
        print(f"{kind + ', ' + str(users) + (' users' if users > 1 else ' user'):24} {b['k_ready'] / a['k_ready']:15.2f}x {b['comp'] / a['comp']:7.2f}x {b['join'] / a['join']:9.2f}x")

# ------------------------------------------------------------------ 4. line through the three prompt lengths
print("\n4. Line through the three prompt lengths of one user count: compute = fixed + c x (K tokens in full pages).")
print("   c is per worker. c x 40 is the CPU time per K token.")
for kind, _ in KINDS:
    for users in (1, 8):
        cs = [c for c in order if M[c]["users"] == users]
        x = [M[c][kind]["k_ready"] for c in cs]
        y = [M[c][kind]["comp"] for c in cs]
        n = len(x)
        mx, my = sum(x) / n, sum(y) / n
        slope = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sum((a - mx) ** 2 for a in x)
        fixed = my - slope * mx
        resid = [b - (fixed + slope * a) for a, b in zip(x, y)]
        two = [(y[i + 1] - y[i]) / (x[i + 1] - x[i]) for i in range(n - 1)]
        print(f"   {kind}, {users} user{'s' if users > 1 else ''}: c = {slope * 1e6:.3f} ns per K token (x 40 = {slope * 40e6:.1f} ns), fixed = {fixed:.3f} ms per pass, "
              f"largest residual {max(abs(r) for r in resid):.3f} ms; slope of each interval: {two[0] * 1e6:.3f} and {two[1] * 1e6:.3f} ns")
        for c in cs:
            m = M[c][kind]
            m["full_d"] = slope * m["k_ready"]
            m["fixed_comp_d"] = fixed
for kind, _ in KINDS:
    what = "one prefill pass" if kind == "prefill" else "one decode step"
    print(f"\n   Parts of the busy time of {what} (ms). (b), (c), (d): the time that the factor divides.")
    print(f"{'cell':24} {'(a) busy':>9} {'(b) busy x K share':>19} {'(c) compute x K share':>22} {'(d) c x K full':>15} {'(d)/(a)':>8} {'not scaled in (d)':>18} {'= join wait':>12} {'+ other':>8}")
    for cell in order:
        m = M[cell][kind]
        m["scaled"] = {"a": m["busy_predict"], "b": m["busy"] * m["k_full_share"], "c": m["comp"] * m["k_full_share"], "d": m["full_d"]}
        s = m["scaled"]
        print(f"{label(cell):24} {s['a']:9.3f} {s['b']:19.3f} {s['c']:22.3f} {s['d']:15.3f} {100 * s['d'] / s['a']:7.1f}% {s['a'] - s['d']:18.3f} {m['join']:12.3f} {s['a'] - s['d'] - m['join']:8.3f}")

# ------------------------------------------------------------------ 5. prediction under each assumption
TRACE_OF = {c: "t-" + c.split("tp4-")[1] for c in order}
pc = lambda new, old: 100.0 * (new - old) / old


def predict(cell, var_pf, var_dec):
    """TTFT (s) and decode speed (tok/s per user) for Part B alone and for Parts A and B, at lo / mid / hi."""
    p, d = M[cell]["prefill"], M[cell]["decode"]
    tr = traces[TRACE_OF[cell]]["kinds"]
    gdn_pf = tr["prefill"]["gdn"]["wall_span_ms_per_pass"]
    t1_pf = agg(cell, ["prompt_or_mixed", "forward_wall_ms"])
    rest_pf = t1_pf - gdn_pf - p["busy_predict"]
    passes = agg(cell, ["prompt_or_mixed", "forwards"])
    ttft = agg(cell, ["ttft_max_s"])
    tps = agg(cell, ["decode_tps_per_user"])
    out = {"ttft": ttft, "tps": tps}
    for lv in LEVELS:
        d_attn = p["scaled"][var_pf] * (1 - 1 / A["s_attn_prefill"][lv])
        d_both = d_attn + gdn_pf * (1 - 1 / A["s_gdn_amx"][lv]) - rest_pf * A["tax_rest_amx_gdn"][lv]
        d_dec = d["scaled"][var_dec] * (1 - 1 / A["s_attn_decode"][lv])
        out[lv] = {"amx_attn": ttft - passes * d_attn / 1e3, "amx_both": ttft - passes * d_both / 1e3, "tps": 1000.0 / (1000.0 / tps - d_dec)}
    return out


def signed(v, digits=1):
    v = 0.0 if abs(v) < 0.5 * 10 ** (-digits) else v
    return f"{v:+.{digits}f}"


def fall(vals):
    lo, hi = min(abs(v) for v in vals), max(abs(v) for v in vals)
    return f"{lo:.0f} %" if f"{lo:.0f}" == f"{hi:.0f}" else f"{lo:.0f} to {hi:.0f} %"


def report(title, var_pf, var_dec):
    P = {c: predict(c, var_pf, var_dec) for c in order}
    print(f"\n{title}")
    print(f"{'cell':24} {'TTFT today':>10} | {'Part B (s, est.)':>34} | {'Parts A and B (s, est.)':>34} | {'decode today':>12} {'decode with Part B (tok/s, est.)':>33}")
    for c in order:
        r = P[c]
        f = lambda scen: f"{r['mid'][scen]:6.2f} ({pc(r['mid'][scen], r['ttft']):+.0f} %) {pc(r['lo'][scen], r['ttft']):+.0f} to {pc(r['hi'][scen], r['ttft']):+.0f} %"
        print(f"{label(c):24} {r['ttft']:10.2f} | {f('amx_attn'):>34} | {f('amx_both'):>34} | {r['tps']:12.1f} {r['mid']['tps']:8.1f} ({signed(pc(r['mid']['tps'], r['tps']))} %) "
              f"{signed(pc(r['lo']['tps'], r['tps']))} to {signed(pc(r['hi']['tps'], r['tps']))} %")
    for scen, name in (("amx_attn", "Part B"), ("amx_both", "Parts A and B together")):
        mid = [pc(P[c]["mid"][scen], P[c]["ttft"]) for c in order]
        allv = [pc(P[c][lv][scen], P[c]["ttft"]) for c in order for lv in LEVELS]
        print(f"   {name}: TTFT falls by {fall(mid)} (est.). Range: {fall(allv)}.")
    lo = min(pc(P[c]["lo"]["tps"], P[c]["tps"]) for c in order)
    hi = max(pc(P[c]["hi"]["tps"], P[c]["tps"]) for c in order)
    print(f"   Decode: working value no change (est.). Range: {signed(lo)} % to {signed(hi)} %.")
    return P


print("\n5. Prediction when the factor divides (a), (b), (c) or (d). Factors (est.): prefill "
      f"{A['s_attn_prefill']['lo']} / {A['s_attn_prefill']['mid']} / {A['s_attn_prefill']['hi']}, decode "
      f"{A['s_attn_decode']['lo']} / {A['s_attn_decode']['mid']} / {A['s_attn_decode']['hi']}. Each cell: working value, change, low to high case.")
Pa = report("(a) the whole busy time", "a", "a")
report("(b) the full-page share of the busy time", "b", "b")
report("(c) the full-page share of the compute time; the join wait stays", "c", "c")
report("(d) the part of the compute time that grows with the full-page K tokens; the rest stays", "d", "d")
Pprop = report("Proposed working model: prefill as (d), decode as (a)", "d", "a")
report("Sensitivity of the proposed model: prefill as (c), decode as (a)", "c", "a")

# ------------------------------------------------------------------ check against predictions.json
def worst_diff(P, clock=False):
    """clock=True: add the clock cost of the other attention work that predict.py applies under Part B (tax_attn_other)."""
    w = 0.0
    for c in order:
        pf = pred["cells"][c]["prefill"]
        for lv in LEVELS:
            ref = pred["cells"][c]["pred"][lv]
            add = pf["passes"] * pf.get("attn_other_ms", 0.0) * pred["assumptions"].get("tax_attn_other", {}).get(lv, 0.0) / 1e3 if clock else 0.0
            w = max(w, abs(P[c][lv]["amx_attn"] + add - ref["amx_attn"]["ttft_s"]), abs(P[c][lv]["amx_both"] + add - ref["amx_both"]["ttft_s"]),
                    abs(P[c][lv]["tps"] - ref["amx_attn"]["tps"]))
    return w


wa, wp, wc = worst_diff(Pa), worst_diff(Pprop), worst_diff(Pprop, clock=True)
print(f"\nCheck against predictions.json (6 cells, 3 levels, Part B, Parts A and B, decode): largest difference {wa:.1e} for variant (a), "
      f"{wp:.1e} for the proposed model, {wc:.1e} for the proposed model with the clock cost of the other attention work.")
print("predictions.json holds " + ("variant (a)." if wa < 1e-9 else "the proposed model." if wp < 1e-9 else
                                   "the proposed model with the clock cost of the other attention work (predict.py, tax_attn_other)." if wc < 1e-9 else "neither."))
print("The tables of part 5 are without that clock cost. It lowers the TTFT fall of Part B by "
      + " / ".join(f"{100 * pred['cells'][c]['prefill']['passes'] * pred['cells'][c]['prefill'].get('attn_other_ms', 0.0) * pred['assumptions'].get('tax_attn_other', {}).get('mid', 0.0) / 1e3 / pred['cells'][c]['prefill']['ttft_s']:.2f}" for c in order)
      + " percentage points in the 6 cells at the working value (est.).")
assert min(wa, wp, wc) < 1e-9

# ------------------------------------------------------------------ 6. A/B measurement on delphi-3bda
ab, cur = {}, None
for raw in open(AB, errors="replace"):
    line = re.sub(r"\x1b\[[0-9;]*m", "", raw)
    if line.startswith("## "):
        cur = line[3:].strip()
        ab[cur] = {}
    m = re.search(r"\[attn-stats\] model \S+: (\{.*\})", line)
    if m and cur:
        ab[cur]["summary"] = json.loads(m.group(1))
    m = re.search(r"\[attn-stats\] (decode_like|prompt_or_mixed)\S* (totals|forwards): (\{.*\})", line)
    if m and cur:
        ab[cur].setdefault(m.group(1), {})[m.group(2)] = json.loads(m.group(3))


def ab_ms(run, cls):
    """Per pass, in ms: pass wall, and busy time and join wait summed over the attention workers."""
    r = ab[run]
    t, f, hz = r[cls]["totals"], r[cls]["forwards"], r["summary"]["tsc_hz"]
    ms = lambda cyc: cyc / f["forwards"] / hz * 1e3
    return {"t1": ms(f["wall_cycles"]), "busy": ms(t["busy_cycles"]), "join": ms(t["join_wait_cycles"]),
            "workers": (f["n_attn_workers_min"], f["n_attn_workers_max"]),
            "k_ready_amx": t["ready_amx_k_tokens"], "k_ready_avx": t["ready_avx_k_tokens"], "k_pend_amx": t["pending_amx_k_tokens"], "k_pend_avx": t["pending_avx_k_tokens"]}


print("\n6. A/B measurement on delphi-3bda, 128-wide heads, 8 users, software attention, one run per arm (exit-reports.txt).")
print("   off = kill switch set, on = AMX kernel on. Times in ms per pass. busy and join wait are SUMS over the attention workers here,")
print("   because the plugin of llama-3.1-8b changes its number of attention workers from pass to pass (column workers: smallest-largest).")
print("   qwen-3-4b has a generated plugin, like Qwen3.5 4B, and 20 attention workers in every pass.")
print(f"{'cell':22} {'kind':8} {'workers':>7} {'busy off':>10} {'busy on':>10} {'busy off/on':>11} {'join off':>9} {'join on':>9} {'compute off/on':>14} {'T1 off':>9} {'T1 on':>9} "
      f"{'AMX share of K: ready pass':>26} {'pending pass':>12}")
AB_CELLS = (("q3-4b-8u-p1024-cpu", "qwen-3-4b, p 1,024"), ("l8b-8u-p1024-cpu", "llama-3.1-8b, p 1,024"), ("l8b-8u-p8192-cpu", "llama-3.1-8b, p 8,192"))
ratio = {}
for key, name in AB_CELLS:
    for kind, cls in KINDS:
        off, on = ab_ms(f"{key}__cpu__amxoff__rep1", cls), ab_ms(f"{key}__cpu__amxon__rep1", cls)
        assert off["workers"] == on["workers"]
        ratio[key, kind] = off["busy"] / on["busy"]
        print(f"{name:22} {kind:8} {off['workers'][0]:4d}-{off['workers'][1]:<2d} {off['busy']:10.2f} {on['busy']:10.2f} {off['busy'] / on['busy']:10.3f}x {off['join']:9.2f} {on['join']:9.2f} "
              f"{(off['busy'] - off['join']) / (on['busy'] - on['join']):13.3f}x {off['t1']:9.3f} {on['t1']:9.3f} "
              f"{100 * on['k_ready_amx'] / (on['k_ready_amx'] + on['k_ready_avx']):25.2f}% {100 * on['k_pend_amx'] / (on['k_pend_amx'] + on['k_pend_avx']):11.2f}%")
off, on = ab_ms("q3-4b-8u-p1024-cpu__cpu__amxoff__rep1", "prompt_or_mixed"), ab_ms("q3-4b-8u-p1024-cpu__cpu__amxon__rep1", "prompt_or_mixed")
print(f"   qwen-3-4b, prefill pass, mean over its 20 workers: busy {off['busy'] / 20:.1f} -> {on['busy'] / 20:.1f} ms (fall {(off['busy'] - on['busy']) / 20:.1f} ms), "
      f"join wait {off['join'] / 20:.1f} -> {on['join'] / 20:.1f} ms, pass wall {off['t1']:.1f} -> {on['t1']:.1f} ms (fall {off['t1'] - on['t1']:.1f} ms).")
print(f"   qwen-3-4b, prefill: K tokens in pages of earlier passes {off['k_ready_avx']:,} (off: AVX-512) -> {on['k_ready_amx']:,} (on: AMX). "
      f"K tokens in pages of the pass in progress: {on['k_pend_avx']:,} on AVX-512 and {on['k_pend_amx']} on AMX with the kernel on.")
print("\n   Whole busy time of a prefill pass, old / new, if the kernel factor of delphi-3bda (2.95 to 3.05, est.) divides the part")
print("   that each variant names. The parts are those of OUR 8-user cell of the same prompt length (table of step 4), so this is")
print("   a check of plausibility across two models, not a fit.")
print(f"{'':28} {'measured':>9} {'(a)':>15} {'(b)':>15} {'(c)':>15} {'(d)':>15}")
for key, name in AB_CELLS:
    prompt = 1024 if "p1024" in key else 8192
    cell = [c for c in order if M[c]["users"] == 8 and M[c]["prompt"] == prompt][0]
    sc = M[cell]["prefill"]["scaled"]
    cols = []
    for v in "abcd":
        share = sc[v] / sc["a"]
        cols.append(" to ".join(f"{1 / (1 - share + share / s):.2f}" for s in (2.95, 3.05)) + "x")
    print(f"   {name:25} {ratio[key, 'prefill']:8.2f}x " + " ".join(f"{c:>15}" for c in cols))
