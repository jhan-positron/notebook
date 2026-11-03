#!/usr/bin/env python3
"""Parse the attention-stats exit reports of campaign pr5047-20261020 and print per-arm means
for the two phases (prompt_or_mixed = prefill, decode_like = decode) of the llama prompt-8192 cells."""
import json, re, sys, statistics as st
path = sys.argv[1]
runs = {}
cur = None
for line in open(path):
    m = re.match(r"^## (\S+)$", line)
    if m:
        cur = m.group(1); runs[cur] = {}; continue
    if cur is None: continue
    m = re.match(r"\[attn-stats\] (\S+) totals: (\{.*\})", line)
    if m: runs[cur][m.group(1) + "/totals"] = json.loads(m.group(2)); continue
    m = re.match(r"\[attn-stats\] (\S+) forwards: (\{.*\})", line)
    if m: runs[cur][m.group(1) + "/forwards"] = json.loads(m.group(2)); continue
    m = re.match(r"\[attn-stats\] model \S+: (\{.*\})", line)
    if m: runs[cur]["model"] = json.loads(m.group(1))
PRE = "prompt_or_mixed/some_jobs_without_listener"
DEC = "decode_like/all_jobs_with_listener"
def arm_runs(cell, arm):
    return [v for k, v in runs.items() if k.startswith(cell + "__cpu__" + arm + "__rep") and PRE + "/totals" in v]
def mean(xs): return st.mean(xs)
def report(cell, arm):
    rs = arm_runs(cell, arm)
    if not rs: print(f"{cell} {arm}: no runs"); return None
    out = {"n": len(rs)}
    for ph, tag in ((PRE, "prefill"), (DEC, "decode")):
        t = [r[ph + "/totals"] for r in rs]; f = [r[ph + "/forwards"] for r in rs]
        hz = mean(r["model"]["tsc_hz"] for r in rs)
        visits_avx = mean(x["ready_avx_visits"] + x["pending_avx_visits"] for x in t)
        visits_amx = mean(x["ready_amx_visits"] + x["pending_amx_visits"] for x in t)
        ktok_avx = mean(x["ready_avx_k_tokens"] + x["pending_avx_k_tokens"] for x in t)
        ktok_amx = mean(x["ready_amx_k_tokens"] + x["pending_amx_k_tokens"] for x in t)
        busy = mean(x["busy_cycles"] for x in t)
        busy_sd = st.pstdev([x["busy_cycles"] for x in t]) if len(t) > 1 else 0
        wall_w0 = mean(x["wall_cycles_w0"] for x in t)
        joinw = mean(x["join_wait_cycles"] for x in t)
        fwall = mean(x["wall_cycles"] for x in f)
        fwd = mean(x["forwards"] for x in f)
        workers = mean(x["n_attn_workers_max"] for x in f)
        out[tag] = dict(tsc_hz=hz, visits_avx=visits_avx, visits_amx=visits_amx, ktok_avx=ktok_avx, ktok_amx=ktok_amx,
                        busy=busy, busy_sd=busy_sd, wall_w0=wall_w0, join_wait=joinw, fwd_wall=fwall, forwards=fwd, workers=workers)
    return out
def show(cell, a, b):
    A, B = report(cell, a), report(cell, b)
    if not A or not B: return
    print(f"\n=== {cell}: {b} (head) vs {a} (base), n={A['n']}/{B['n']} ===")
    for tag in ("prefill", "decode"):
        x, y = A[tag], B[tag]; hz = x["tsc_hz"]
        print(f"-- {tag}: forwards {x['forwards']:.0f}, attention workers {x['workers']:.0f}, TSC {hz/1e9:.3f} GHz")
        print(f"   visits: AVX {x['visits_avx']:,.0f}  AMX {x['visits_amx']:,.0f}   K tokens: AVX {x['ktok_avx']:,.0f}  AMX {x['ktok_amx']:,.0f}")
        print(f"   base busy {x['busy']/1e9:,.1f} G TSC cycles (sd {x['busy_sd']/1e9:.1f})  head busy {y['busy']/1e9:,.1f} (sd {y['busy_sd']/1e9:.1f})  delta {(y['busy']-x['busy'])/1e9:,.1f} G = {100*(y['busy']-x['busy'])/x['busy']:+.2f} %")
        print(f"   forward wall: base {x['fwd_wall']/hz:.2f} s  head {y['fwd_wall']/hz:.2f} s  delta {(y['fwd_wall']-x['fwd_wall'])/hz:+.3f} s")
        print(f"   worker-0 attention wall: base {x['wall_w0']/hz:.2f} s  head {y['wall_w0']/hz:.2f} s  delta {(y['wall_w0']-x['wall_w0'])/hz:+.3f} s")
        print(f"   join wait (sum over workers): base {x['join_wait']/1e9:.1f} G  head {y['join_wait']/1e9:.1f} G")
        va = x["visits_avx"]; ka = x["ktok_avx"]
        if va:
            print(f"   base busy per AVX visit {x['busy']/(va+x['visits_amx']):,.0f} TSC cycles ({x['busy']/(va+x['visits_amx'])/hz*1e9:.0f} ns) [all visits]")
            print(f"   delta per AVX visit {(y['busy']-x['busy'])/va:,.1f} TSC cycles ({(y['busy']-x['busy'])/va/hz*1e9:.1f} ns);  delta per AVX K token {(y['busy']-x['busy'])/ka:,.2f} TSC cycles ({(y['busy']-x['busy'])/ka/hz*1e9:.2f} ns)")
            print(f"   base busy per AVX K token (all busy / AVX K tokens) {x['busy']/ka:,.1f} TSC cycles" if not x['visits_amx'] else "")
show("l8b-tp2-8u-p8192-off", "baseoff", "headoff")
show("l8b-tp2-8u-p8192-cpu", "base", "head")
show("l8b-tp2-8u-p8192-cpu", "basev", "headv")
show("l8b-tp2-8u-p1024-cpu", "base", "head")
