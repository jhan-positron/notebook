import json, glob, os, statistics as st
R = "/home/jhan/workspace/intel-AMX/exec/results"
tags = {}
for camp in ("q4b-swattn-20260919", "q4b-fpga-20260921"):
    for pj in sorted(glob.glob(f"{R}/{camp}/*/perf.json")):
        tag = os.path.basename(os.path.dirname(pj))
        tags[(camp, tag)] = json.load(open(pj))
print("tags found:")
for k in tags:
    print("  ", k)
print()

def arm_of(camp, tag):
    if tag.startswith("check-8u-p"):
        return "canon"
    return tag.split("-")[0]

cells = {}  # (arm, prompt) -> list of (tag, harness ttft, tps, cache pct, engine_requests, hw0, hwunset, cold, started)
for (camp, tag), d in tags.items():
    if tag in ("check-mode",) or tag.startswith("prev-") or tag.endswith("-failed1"):
        print("skip", camp, tag, "raw cells:", len(d.get("raw", [])))
        continue
    arm = arm_of(camp, tag)
    res = {x["name"]: x for x in d.get("results", [])}
    ver = (d.get("versions") or {}).get("Tron (package)")
    print(f"--- {camp}/{tag} arm={arm} ver={ver} raw={len(d.get('raw', []))} results={len(res)}")
    for i, r in enumerate(d.get("raw", [])):
        tt = r.get("ttfts_ms") or []
        if not tt:
            print("   (no ttfts)", r.get("name"))
            continue
        pt, ct = r.get("prompt_tokens") or [], r.get("cached_tokens") or []
        cache = 100.0 * sum(ct) / sum(pt) if pt and sum(pt) else None
        rr = res.get(r["name"], {})
        cold = ("-cold" in tag) or tag.startswith("check-8u-p") or i == 0
        row = (tag, rr.get("ttft_mean"), rr.get("tps_mean"), cache, r.get("engine_requests"), r.get("hwattn_ok"), r.get("hwattn_unset_ok"), cold, r.get("started"), len(tt), st.mean(tt))
        cells.setdefault((arm, r["prompt_length"]), []).append(row)
        print(f"   p={r['prompt_length']:>5} cold={int(cold)} harness_ttft={rr.get('ttft_mean')} mean(ttfts)={st.mean(tt):.1f} n={len(tt)} tps={rr.get('tps_mean')} cache={cache if cache is None else round(cache,1)} eng={r.get('engine_requests')} hw0={r.get('hwattn_ok')} hwunset={r.get('hwattn_unset_ok')} started={r.get('started')} caddy={r.get('caddy_health_events')}")

print("\n=== per arm/prompt warm means (harness ttft) and cold ===")
PROMPTS = [1024, 1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192]
agg = {}
for (arm, p), rows in cells.items():
    warm = [x[1] for x in rows if not x[7]]
    cold = [x[1] for x in rows if x[7]]
    agg[(arm, p)] = (warm, cold)
for arm in ("base", "canon", "fpgabase", "fpgacanon"):
    for p in PROMPTS:
        warm, cold = agg.get((arm, p), ([], []))
        w = f"{st.mean(warm):,.0f} +/- {st.stdev(warm):.0f} ({len(warm)})" if len(warm) > 1 else (f"{warm[0]:,.0f} (1)" if warm else "-")
        c = f"{st.mean(cold):,.0f} ({len(cold)})" if cold else "-"
        print(f"{arm:10s} p={p:>5} warm={w:28s} cold={c}")

def m(arm, p, key):
    warm, cold = agg.get((arm, p), ([], []))
    xs = warm if key == "warm" else cold
    return st.mean(xs) if xs else None

print("\n=== figure 3 end labels (8192 warm means /1000) ===")
for arm in ("base", "canon", "fpgabase", "fpgacanon"):
    v = m(arm, 8192, "warm")
    print(arm, f"{v:,.0f} ms -> {v/1000:.1f} s")

print("\n=== short version numbers ===")
c_cpu, c_fc, c_fb = m("canon", 8192, "cold"), m("fpgacanon", 8192, "cold"), m("fpgabase", 8192, "cold")
w_b, w_c, w_fc, w_fb = m("base", 8192, "warm"), m("canon", 8192, "warm"), m("fpgacanon", 8192, "warm"), m("fpgabase", 8192, "warm")
print(f"cold 8192: canon CPU {c_cpu:.0f}, fpgacanon {c_fc:.0f}, fpgabase {c_fb:.0f}; ratio {c_cpu/c_fc:.2f}x ; pct {100*(c_fc-c_cpu)/c_cpu:+.1f} % ; fc vs fb {100*(c_fc-c_fb)/c_fb:+.1f} %")
print(f"warm 8192: base {w_b:.0f}, canon {w_c:.0f}, fpgacanon {w_fc:.0f}, fpgabase {w_fb:.0f}; base/canon {w_b/w_c:.2f}x ; canon/fpgacanon {w_c/w_fc:.2f}x ; base/fpgacanon {w_b/w_fc:.2f}x")
print(f"1024 cold: canon {m('canon',1024,'cold'):.0f} fpgacanon {m('fpgacanon',1024,'cold'):.0f} pct {100*(m('fpgacanon',1024,'cold')-m('canon',1024,'cold'))/m('canon',1024,'cold'):+.2f} %")
print(f"1024 cold: base {m('base',1024,'cold'):.0f} fpgabase {m('fpgabase',1024,'cold'):.0f} pct {100*(m('fpgabase',1024,'cold')-m('base',1024,'cold'))/m('base',1024,'cold'):+.2f} %")

print("\n=== canon 8192 warm: 3-pass (q4b-swattn only) vs 4-pass ===")
rows = cells[("canon", 8192)]
three = [x[1] for x in rows if not x[7] and x[0] in ("canon-pass1", "canon-pass2", "canon-pass3") and x[8] and x[8].startswith("2026-09-2") and "fpga" not in x[0]]
print("all canon 8192 rows:", [(x[0], x[1], x[7], x[8]) for x in rows])

print("\n=== 3-pass sd of the 2026-09-20 CPU series (q4b-swattn only) ===")
for arm in ("base", "canon"):
    for p in (1024, 8192):
        xs = []
        for (camp, tag), d in tags.items():
            if camp != "q4b-swattn-20260919" or not tag.startswith(arm + "-pass"):
                continue
            res = {x["name"]: x for x in d.get("results", [])}
            for r in d.get("raw", []):
                if r["prompt_length"] == p:
                    xs.append(res[r["name"]]["ttft_mean"])
        print(f"{arm} p={p}: n={len(xs)} mean={st.mean(xs):.1f} sd={st.stdev(xs):.1f}  values={[round(x,1) for x in xs]}")

print("\n=== per prompt FPGA vs CPU (warm) and fpgacanon vs fpgabase ===")
for p in PROMPTS:
    key = "cold" if p == 1024 else "warm"
    wc, wf = m("canon", p, key), m("fpgacanon", p, key)
    wb, wfb = m("base", p, key), m("fpgabase", p, key)
    s = f"p={p:>5}"
    if wc and wf: s += f"  canon: {100*(wf-wc)/wc:+.1f} %"
    if wb and wfb: s += f"  base: {100*(wfb-wb)/wb:+.1f} %  base/fpgabase {wb/wfb:.2f}x"
    if wf and wfb: s += f"  fpgacanon vs fpgabase ({key}): {100*(wf-wfb)/wfb:+.1f} %"
    cf, cfb = m("fpgacanon", p, "cold"), m("fpgabase", p, "cold")
    if p != 1024 and cf and cfb: s += f"  cold fc vs fb: {100*(cf-cfb)/cfb:+.1f} %"
    print(s)

print("\n=== cache hit pct ranges ===")
warm_cache = [x[3] for rows in cells.values() for x in rows if not x[7] and x[3] is not None]
print(f"warm cells cache pct: min {min(warm_cache):.1f} max {max(warm_cache):.1f}")
cold_cache = [x[3] for rows in cells.values() for x in rows if x[7] and x[3] is not None]
print(f"cold cells cache pct: min {min(cold_cache):.1f} max {max(cold_cache):.1f}")
print("canon 4096 warm cache pcts:", [round(x[3], 1) for x in cells[("canon", 4096)] if not x[7]])
for arm in ("base", "canon", "fpgabase", "fpgacanon"):
    print(arm, "warm cache by prompt:", {p: [round(x[3],1) for x in cells.get((arm,p),[]) if not x[7]] for p in PROMPTS})

print("\n=== TPS at 8192 ===")
for arm in ("base", "canon", "fpgabase", "fpgacanon"):
    print(arm, [(x[0], x[2]) for x in cells.get((arm, 8192), [])])

print("\n=== engine_requests and hwattn flags over the q4b-fpga campaign ===")
for (camp, tag), d in tags.items():
    if camp != "q4b-fpga-20260921" or tag == "check-mode":
        continue
    for r in d.get("raw", []):
        print(f"{tag:22s} p={r['prompt_length']:>5} eng={r.get('engine_requests')} hw0={r.get('hwattn_ok')} hwunset={r.get('hwattn_unset_ok')} n_ttft={len(r.get('ttfts_ms') or [])}")
print("\nkeys in a raw cell:", sorted(tags[("q4b-fpga-20260921", "fpgacanon-pass1")]["raw"][0].keys()))
print("top-level keys:", sorted(tags[("q4b-fpga-20260921", "fpgacanon-pass1")].keys()))
