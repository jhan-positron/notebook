import re
def load(p): return open(p).read()
def save(p, s): open(p, "w").write(s)
def rep(s, old, new, count=1):
    n = s.count(old); assert n == count, (n, old[:100]); return s.replace(old, new)

# ================= fpga_section.py
s = load("fpga_section.py")
s = rep(s, '"CI harness", 3, 3, 512, 554, 186.25, 185.12,', '"CI harness", 3, 3, 512.3, 554.0, 186.25, 185.12,')
s = rep(s, """        dt = [100.0 * (y - x) / x for x, y in zip(ta, tb)]
        dp = [100.0 * (y - x) / x for x, y in zip(pa, pb)]
""", """        dt = [100.0 * (y - x) / x for x, y in zip(ta, tb)]
        dp = [100.0 * (y - x) / x for x, y in zip(pa, pb)]
        # per uncached prompt token: TTFT / (prompt tokens x (1 - prefix-cache hit share)), then the same paired delta
        def per_tok(x):
            return x["ttft_harness_ms"] / (x["prompt_tokens_mean"] * (1.0 - x["cache_hit_pct"] / 100.0))
        dk = [100.0 * (per_tok(y) - per_tok(x)) / per_tok(x) for x, y in zip(a, b)]
""")
s = rep(s, """                        ttft_pcts=dt, tps_pcts=dp, ttft_pct=mean(dt), tps_pct=mean(dp),""",
           """                        ttft_pcts=dt, tps_pcts=dp, ttft_pct=mean(dt), tps_pct=mean(dp), tok_pcts=dk, tok_pct=mean(dk),
                        cache_avx_pcts=[x["cache_hit_pct"] for x in a], cache_amx_pcts=[x["cache_hit_pct"] for x in b],""")
s = rep(s, """<th>Welch t (TTFT)</th><th>decode TPS, AVX build</th>""", """<th>Welch t (TTFT)</th><th>TTFT change per uncached prompt token, mean (per pass)</th><th>decode TPS, AVX build</th>""")
s = rep(s, """<td>{"-" if r.get("t_ttft") is None else f"{r[chr(116)+chr(95)+chr(116)+chr(116)+chr(102)+chr(116)]:+.1f}"}</td><td>{r["tps_avx"]:.1f}</td>""",
           """<td>{"-" if r.get("t_ttft") is None else f"{r[chr(116)+chr(95)+chr(116)+chr(116)+chr(102)+chr(116)]:+.1f}"}</td><td>{r["tok_pct"]:+.1f} % ({", ".join(f"{v:+.1f}" for v in r.get("tok_pcts", []))})</td><td>{r["tps_avx"]:.1f}</td>""")
s = rep(s, """<th>prefix-cache hits AVX / AMX (%)</th></tr></thead><tbody>']""", """<th>prefix-cache hits AVX / AMX (%, per pass)</th></tr></thead><tbody>']""")
s = rep(s, """<td>{r["cache_avx"]} / {r["cache_amx"]}</td></tr>')""", """<td>{", ".join(f"{v:.0f}" for v in r.get("cache_avx_pcts", []))} / {", ".join(f"{v:.0f}" for v in r.get("cache_amx_pcts", []))}</td></tr>')""")
save("fpga_section.py", s)

# ================= rt8u_section.py
s = load("rt8u_section.py")
s = rep(s, "For CPU attention yes (runtron, section 5 of the earlier campaigns), for FPGA attention no.", "For CPU attention yes (runtron, 8 users at prompt 8192, the vnnik-20260914 campaign, not shown on this page), for FPGA attention no.")
s = rep(s, "Cells: 8 users at prompt 1024, 2048, 4096 and 8192, and 2 users at 4096 and 8192, 256 generated tokens per user.", "Cells: 8 users at prompt 1024, 2048, 4096 and 8192, and 2 users at 4096 and 8192, 256 generated tokens requested per user (runtron counts 253 generated tokens in every run, the last 3 are the stop sequence).")
s = rep(s, "The campaign took over idle production serving through platformd at 16:58 UTC and gave it back at 18:12 UTC.</p>",
           "At 16:58 UTC the campaign stopped the idle production engines through platformd (after the guard\\'s 10-minute idle check). At 18:12 UTC it started them again through platformd. One earlier attempt at 16:36 UTC was stopped by the campaign\\'s own watcher after 10 s, because platformd had restarted the engines that the guard had stopped with systemctl. That attempt is excluded. Every one of the 72 kept runs is complete.</p>")
s = rep(s, """decode {min(ca_p):+.0f} to {max(ca_p):+.0f} %, every paired t above 20 in magnitude.""", """decode {min(ca_p):+.1f} to {max(ca_p):+.1f} %, every paired t above 20 in magnitude.""")
s = rep(s, """The paired t reaches -7.9 to -17 at 2048 to 8192 with 8 users, so those 1 to 2 % prefill gains are real, and small. Decode does not change (|t| at most 4.5, all changes within 1.2 %). Without a warm prefix cache the AMX build brings the FPGA path 1 to 2 % on prefill and nothing on decode.""",
           """The paired t is -7.9 to -17 at 2048 to 8192 with 8 users and -13.4 at 2 users and 8192. Those 1 to 2 % prefill gains are therefore resolved, and small. The 1024 cell (-0.3 %, t -0.7) and the 2-user 4096 cell (+0.3 %, t +1.8) show no resolved difference. Decode changes by at most 1.2 % in every cell. Five decode cells are not resolved (|t| at most 3.2). One (2 users, prompt 4096) is resolved at -0.5 % (t -4.5), a change too small to matter. Without a warm prefix cache the AMX build brings the FPGA path 0 to 2 % on prefill and nothing on decode.""")
s = rep(s, """including 8 users at 8192 (80 shards of 1024 tokens per engine, about 11.5 GB over the two cards, est.).""",
           """including 8 users at 8192 (72 shards of 1024 tokens per engine: 9 per user for 8192 prompt plus 256 generated tokens, 36 per card, about 10.9 GB over the two cards, est.).""")
s = rep(s, """mean of 3 repetitions. The prefill time is runtron\\'s""", """mean of 3 repetitions (256 generated tokens requested, 253 counted). The prefill time is runtron\\'s""")
save("rt8u_section.py", s)

# ================= gen_page.py
s = load("gen_page.py")
# rounding helper (half up for magnitude ranges) next to rs()
s = rep(s, "def rs(lo, hi, fmt=\"{:.0f}\"):\n", "def r0(x):\n    \"\"\"Magnitude rounded half up to a whole number (48.5 -> 49), for ranges quoted in prose.\"\"\"\n    return int(math.floor(abs(x) + 0.5))\n\n\ndef rs(lo, hi, fmt=\"{:.0f}\"):\n")

# ---- section 5 intro paragraph
a = s.index("    H.append(f'<p>Measured 2026-09-21 22:35 to 2026-09-22 01:17 UTC on the whole of delphi-3bda")
b = s.index("\n", a) + 1
new_intro = """    uneven = [r for r in rows6 if r["arm"] in ("fpgabase", "fpgacanon") and r.get("engine_requests") and any(v is None for v in r["engine_requests"].values())]
    uneven_txt = "; ".join(f"{FS.ARM_LABEL[r['arm']]} pass {FS.pass_no(r['tag'])} at prompt {r['prompt_length']} (spread {' / '.join('not recorded' if v is None else str(v) for v in r['engine_requests'].values())}, {r.get('caddy_health_events') or 0} Caddy health events, {r['ttft_harness_ms']:,.0f} ms)" for r in uneven)
    n_fpga_cells = sum(1 for r in rows6 if r["arm"] in ("fpgabase", "fpgacanon") and not r["cold"]) + sum(1 for r in rows6 if r["arm"] in ("fpgabase", "fpgacanon") and r["cold"])
    H.append(f'<p>Measured on the whole of delphi-3bda in the nightly layout (platformd 0.11, 4 tp2 engines behind the test proxy, 2 users per engine, 1536 generated tokens) with the same harness, prompts and cells as the 2026-09-20 CPU-attention series, in two windows: 2026-09-21 22:35 to 2026-09-22 01:17 UTC (pass 1 and the first cold cells) and 2026-09-22 13:29 to 16:25 UTC (passes 2 and 3 and the second cold cells). FPGA-attention driver runs: {n_fb} with the nightly deb, {n_fc} with the canonical AMX deb (three 9-cell passes and four single cold cells each). The CPU-attention arms are the 2026-09-20 series (3 passes each) plus one canonical pass of 2026-09-22 and the cold check cell of 2026-09-19, not re-run further (jhan). Every engine\\'s environment was checked after each provisioning: no USE_HW_ATTN=0 in the FPGA arms, exactly one in the CPU arms. {n_fpga_cells - len(uneven)} of the {n_fpga_cells} FPGA-arm cells spread their 80 requests 20 / 20 / 20 / 20 over the four engines. {len(uneven)} did not, because one engine restarted during the cell (its request counters start again from zero and its card is nearly empty afterwards): {uneven_txt}. Those cells stay in the means, and pass 1 is the only pass without such a restart on either arm. The canonical CPU pass of 2026-09-22 has the same kind of exception: engine default-1 restarted before its prompt-3000 cell (spread 22 / not recorded / 20 / 22, 3 Caddy health events, 2,296 ms). That cell stays in the n = 4 mean and is flagged in the table caption. The measurements took three launches: the first ran fpgabase pass 1 and stopped at the switch to the canonical deb (an idle-test bug in dut.sh, see the runbook\\'s incident log), the relaunch at 23:37 UTC ran fpgacanon pass 1, the canonical CPU pass and the first four cold cells, and the third launch after the 2026-09-22 nightly ran passes 2 and 3 of both FPGA arms and the second cold cells. The binary check of every run shows the intended deb.</p>')
"""
s = s[:a] + new_intro + s[b:]
# rows6 must exist before the intro: move the rows6 definition up (it is defined later near pc()); define it at the top of section5_measured instead
s = rep(s, """    rows6 = FS.load()
    def wt(p):""", """    def wt(p):""")
s = rep(s, """def section5_measured(agg):
""", """def section5_measured(agg):
    rows6 = FS.load()
""")
# ---- cold 8192 bullet
s = rep(s, "(n = {n('fpgacanon', 8192, 'cold')} each, the two cold runs of one arm within 30 ms).", "(n = {n('fpgacanon', 8192, 'cold')} each, the two cold runs of one arm 17 ms apart for the AMX build and 41 ms for the AVX build).")
# ---- record table caption: computed 3000 figures
s = rep(s, """Without them the row reads 1,758 ms (n = 2) and the FPGA-vs-CPU figure at 3000 is -18 % instead of -26 %. Source:""",
           """Without them the row reads {c3000_low:,.0f} ms (n = 2) and the FPGA-vs-CPU figure at 3000 is {pc(m('fpgacanon', 3000, 'warm'), c3000_low)} instead of {pc(m('fpgacanon', 3000, 'warm'), m('canon', 3000, 'warm'))}. Source:""")
s = rep(s, """    H.append('<p class="cap">Client-side TTFT in ms, harness mean over 8 users x 10 rounds. "warm mean (passes)" """,
           """    c3000_low = statistics.mean(sorted(agg["canon"][3000]["warm"])[:2])
    H.append(f'<p class="cap">Client-side TTFT in ms, harness mean over 8 users x 10 rounds. "warm mean (passes)" """)
s = rep(s, """at 8192: 121 TPS with FPGA attention and the AMX build against 60 TPS with AMX on the CPU).</p>')""",
           """at 8192: {statistics.mean(agg["fpgacanon"][8192]["tps"]) if False else tps_fc8k:.0f} TPS with FPGA attention and the AMX build, mean of three passes, against 60 TPS with AMX on the CPU).</p>')""")
s = rep(s, """    H.append('<p>Reading. Both the AMX kernel and the FPGA remove the quadratic attention cost""",
           """    tps_fc8k = statistics.mean([r["tps_mean"] for r in rows6 if r["arm"] == "fpgacanon" and r["prompt_length"] == 8192 and not r["cold"]])
    H.append(f'<p>Reading. Both the AMX kernel and the FPGA remove the quadratic attention cost""")
s = rep(s, """{statistics.mean(agg["fpgacanon"][8192]["tps"]) if False else tps_fc8k:.0f}""", """{tps_fc8k:.0f}""")
if "import statistics" not in s:
    s = rep(s, "import sys\n", "import statistics\nimport sys\n")

# ---- mechanisms paragraph: full rewrite
a = s.index("    c6 = {(c[\"prompt\"], c[\"kind\"]): c for c in FS.amx_vs_avx_rows(rows6)}")
b = s.index("    H.extend(hbm_subsection())")
new_hyp = '''    c6 = {(c["prompt"], c["kind"]): c for c in FS.amx_vs_avx_rows(rows6)}
    wl = [c6[(p, "warm")] for p in (4096, 5120, 6144, 7168, 8192)]
    wl_lo, wl_hi = min(c["ttft_pct"] for c in wl), max(c["ttft_pct"] for c in wl)
    wl_all = [v for c in wl for v in c["ttft_pcts"]]
    tk_lo, tk_hi = min(c["tok_pct"] for c in wl), max(c["tok_pct"] for c in wl)
    c2k, c15, c30, c71 = c6[(2048, "warm")], c6[(1536, "warm")], c6[(3000, "warm")], c6[(7168, "warm")]
    cold6 = [c6[k] for k in ((1024, "cold"), (4096, "cold"), (8192, "cold")) if k in c6]
    hb = hbm_load()
    def share_new(p):
        v = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(hb, arm, p, "warm") if c["lose"] and c.get("share_new_pct") is not None]
        return (min(v), max(v)) if v else (None, None)
    s45 = share_new(4096) + share_new(5120); s61 = share_new(6144)
    cpu_gain = {p: 100.0 * (m("canon", p, "warm") - m("base", p, "warm")) / m("base", p, "warm") for p in (4096, 5120, 6144)}
    # pre-cell AMX probe of the canonical FPGA arm: windows grouped by the state of the card (gap warnings before the cell)
    gaps = {(g["tag"], g["before_prompt"]): g["lose"] for g in (hb.get("gaps", []) if hb else [])}
    pr_fresh, pr_clean, pr_full = [], [], []
    for r in rows6:
        if r["arm"] != "fpgacanon" or r.get("amx_busy_cycles") is None:
            continue
        v = r["amx_busy_cycles"] / 1e9
        (pr_fresh if r["cold"] else (pr_clean if gaps.get((r["tag"], r["prompt_length"]), 0) == 0 else pr_full)).append(v)
    H.append(f'<p class="hyp">Why the AMX build helps the warm cells under FPGA attention far more than the cold cells: two candidate mechanisms, neither proven for every cell. The measurements first (means of the per-pass deltas over 3 paired passes per cell, section 6). The AMX build lowers the warm TTFT by {r0(wl_hi)} to {r0(wl_lo)} % from prompt 4096 up, and in every one of the {len(wl_all)} paired passes ({min(wl_all):+.0f} to {max(wl_all):+.0f} %). Per uncached prompt token (the two arms did not see the same prefix-cache share in a paired cell) the same gains are {r0(tk_hi)} to {r0(tk_lo)} %. At 2048 it lowers the TTFT by {r0(c2k["ttft_pct"])} % on average ({", ".join(f"{v:+.1f}" for v in c2k["ttft_pcts"])} % per pass). At 1536 and 3000 the means are {c15["ttft_pct"]:+.1f} and {c30["ttft_pct"]:+.1f} %, with Welch t {c15["t_ttft"]:+.1f} and {c30["t_ttft"]:+.1f}, so not resolved. In the cold cells it lowers TTFT by {r0(max(c["ttft_pct"] for c in cold6))} to {r0(min(c["ttft_pct"] for c in cold6))} % (n = 2 to 3 per cell). Mechanism 1, measured as a co-occurrence (next subsection): in every pass the 4096, 5120 and 6144 cells ran with the card\\'s K/V space exhausted from round 1 until 60 to 99 % of the cell. At 4096 and 5120 nearly every new shard placement failed ({r0(min(s45))} to {r0(max(s45))} % of the new placements, est.), at 6144 {r0(s61[0])} to {r0(s61[1])} %. So in those cells both arms scored nearly all new context on the CPU, where the AMX kernel replaces the AVX loop. The AMX gain there ({r0(c6[(4096, "warm")]["ttft_pct"])} % at 4096, {r0(c6[(5120, "warm")]["ttft_pct"])} % at 5120) is then the CPU-attention gain in another guise: the canonical CPU arm beats the AVX CPU arm by {r0(cpu_gain[4096])} % and {r0(cpu_gain[5120])} % in the same warm cells. Mechanism 1 cannot explain the 2048 cells. They had no exhaustion warning in any pass, no earlier cell of any pass had one either, and they still read {c2k["ttft_pct"]:+.0f} % on average. The 7168 cells and the first rounds of the 8192 cells are not counter-examples: a shard that fell back keeps running on the CPU for as long as the prefix cache keeps its tree node, and it warns only once, when it is created [h/tron/shard.hpp:8-31; src/tron/gof.cpp:70-103; h/tron/scheduler/full.hpp:2400-2428, Note "Retrying a degraded shard"]. A request that inherits such a shard through the prefix cache runs part of its attention on the CPU without a new warning. So the absence of new warnings at 7168 ({", ".join(f"{v:+.1f}" for v in c71["ttft_pcts"])} % in the three pairs) and in rounds 1 to 6 at 8192 does not show the absence of CPU attention there. Mechanism 2, a hypothesis: in a warm request the K/V pages (64-token blocks) that come from the prefix cache are scored on the CPU while the card\\'s copy lags (the DMA-lag rule of section 4), and the AMX kernel covers that work. Evidence in the same direction, not proof. The pre-cell AMX probe (Words used here) counts AMX-busy cycles in one 20 s window before each cell. More cycles mean more attention work ran through the AMX kernel. On fresh engines it read {min(pr_fresh):.1f} to {max(pr_fresh):.1f} billion ({len(pr_fresh)} windows, canonical FPGA arm, all three passes and the cold cells). In the warm windows without an exhaustion warning it read {min(pr_clean):.1f} to {max(pr_clean):.1f} billion ({len(pr_clean)} windows). In the windows where the card was full it read {min(pr_full):.1f} to {max(pr_full):.1f} billion ({len(pr_full)} windows). The groups overlap at about 21 billion, so the probe separates fresh from warm engines but not a clean warm card from a full one. It measures its own request streams, not the cell. Test that would settle it: a perfetto trace of one warm 2048 request, AMX build against kill switch. The per-card fallback counter, recorded per cell since the third launch, confirms the exhaustion counts but cannot separate the two mechanisms.</p>')
'''
s = s[:a] + new_hyp + s[b:]

# ---- hbm_subsection: rewrite whole function
a = s.index("def hbm_subsection():")
b = s.index("def section6_amx_vs_aof(rows):")
new_fn = r'''def hbm_subsection():
    """The card's K/V space ran out in the warm long-prompt cells: counts per cell from the engine journal (hbm_cells.py), aggregated per arm and prompt over the passes."""
    d = hbm_load()
    if not d:
        return []
    gaps = d.get("gaps", [])
    gap_after = {}
    for g in gaps:
        if g["lose"]:
            gap_after.setdefault(g["after_prompt"], []).append(g["lose"])
    n_gap = sum(g["lose"] for g in gaps)
    n_passes = len({c["tag"] for c in d["cells"] if c["tag"].startswith("fpga") and "pass" in c["tag"]})
    n_cold = len({c["tag"] for c in d["cells"] if c["tag"].startswith("fpga") and "cold" in c["tag"]})
    av = d.get("avail_counts", {})
    MiB = 2 ** 20
    H = []
    H.append("<h3>The card ran out of K/V space in the warm long-prompt cells</h3>")
    H.append(f'<p>The engine journal (the systemd log of the four rinzler engines) of the two campaign windows (2026-09-21 22:30 to 2026-09-22 01:30 UTC and 2026-09-22 13:00 to 16:30 UTC) holds {d["total_lose"]:,} warnings of the form "HBM bypass space exhausted, caller degrades to SW attention" followed by "shard base tok_ix N: 36 of 36 slots lose HW attention" [exec/results/q4b-fpga-20260921/hbm-journal-20260921.txt, hbm-journal-20260922.txt]. HBM is the card\'s memory. A shard is the card-side copy of 1024 tokens of one request\'s K/V, placed on one of the engine\'s two cards. One warning means one new shard could not be placed on its card, and that shard\'s attention ran on the CPU instead. A shard warns once, when it is created. It keeps its CPU-attention state for as long as the prefix cache keeps its tree node, and a later request that inherits it through the prefix cache runs that part of its attention on the CPU without a new warning [h/tron/shard.hpp:8-31; h/tron/scheduler/full.hpp:2400-2428]. So the counts below measure new failures, not the total share of CPU attention in a cell. {d["inside_cells"]:,} warnings fall inside cells (between the harness\'s start and end time of a cell). The other {n_gap:,} fall in the 30 s gaps between cells of the {n_passes} FPGA passes: after the 3000, 4096 and 5120 cells in every pass ({len(gap_after.get(3000, []))}, {len(gap_after.get(4096, []))} and {len(gap_after.get(5120, []))} of {n_passes} passes), after the 6144 cell in {len(gap_after.get(6144, []))} passes, never after 7168. In those gaps our campaign driver (the script that provisions the engines and runs the harness cells) runs the pre-cell AMX probe, which keeps 4 request streams of its own running for 20 s (Words used here). The gap warnings name only shard bases 0 and 1024. So they are the probe\'s own requests, which could not place even their first shard. They show that the card was already full when each 3000 cell ended and stayed full to the start of the 6144 cell. The first warning of the first window is at 22:45:30 UTC, 12 s after the prompt-3000 cell of the first FPGA pass ended and 19 s before the first round of its prompt-4096 cell. None of the warnings fall in the CPU-attention pass or in the {n_cold} cold cells. None appear in any earlier FPGA-attention run at prompt 1024: 0 warnings in every runtron log of the issue-4500, wedperf, wedperf-attr and vnnik4-models campaigns (358 files) and in the engine logs of the p0perf-20260913 CI cells.</p>')
    H.append('<div class="tw"><table class="num"><thead><tr><th>cell</th><th>passes</th><th>warnings per pass</th><th>fallback counter per pass (recorded from the third launch on)</th><th>share of the cell\'s new shard placements (est.)</th><th>first warning (round of 10)</th><th>last warning (% of the cell)</th><th>free space after the cell, lowest card (MiB)</th><th>reading</th></tr></thead><tbody>')
    def fmt_list(xs, f="{}"):
        return ", ".join("-" if x is None else f.format(x) for x in xs)
    for arm in ("fpgabase", "fpgacanon"):
        for kind in ("warm", "cold"):
            for p in (1024, 1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192):
                cs = hbm_group(d, arm, p, kind)
                if not cs:
                    continue
                w = [c["lose"] for c in cs]
                fr = [c["first_round"] for c in cs if c["lose"]]
                lp = [c["last_pct"] for c in cs if c["lose"]]
                if not any(w) and kind == "cold":
                    reading = "clean: fresh engines, every shard on the card"
                elif not any(w) and p <= 3000:
                    reading = "clean: every shard on the card (no earlier exhaustion in the pass)"
                elif not any(w):
                    reading = "no new shard failed; inherited degraded shards not measured"
                elif all(w) and all(x == 1 for x in fr) and min(lp) >= 95:
                    reading = "exhausted through the whole cell in every pass"
                elif all(w) and all(x == 1 for x in fr):
                    reading = f"exhausted from round 1 until {rs(min(lp), max(lp))} % of the cell"
                elif not all(w):
                    reading = f"new shards failed in {sum(1 for x in w if x)} of {len(w)} passes (from round {rs(min(fr), max(fr))}, until {rs(min(lp), max(lp))} % of the cell), on the engine that had restarted earlier in that pass"
                else:
                    reading = f"clean of new failures until round {rs(min(fr) - 1, max(fr) - 1)}, exhausted after"
                sh = [c["share_new_pct"] for c in cs if c["lose"] and c.get("share_new_pct") is not None]
                share = "-" if not sh else f"{rs(min(sh), max(sh))} %"
                H.append(f'<tr><td>{esc(FS.ARM_LABEL.get(arm, arm))}, prompt {p}, {kind}</td><td>{len(cs)}</td><td>{fmt_list(w)}</td><td>{fmt_list([c.get("fallback_counter") for c in cs])}</td><td>{share}</td><td>{fmt_list([c["first_round"] for c in cs])}</td><td>{fmt_list([c["last_pct"] for c in cs])}</td><td>{fmt_list([None if c.get("free_min_after") is None else round(c["free_min_after"] / MiB) for c in cs], "{:,}")}</td><td>{reading}</td></tr>')
    H.append('</tbody></table></div>')
    H.append('<p class="cap">Passes in tag order (pass 1, 2, 3 for warm cells, the two single-cell runs for cold cells). One warning per new shard per engine (a shard sits on one card). Fallback counter = the engines\' sw_fallback_total FUSE stat, summed over the 4 engines x 2 cards, as the difference across the cell. It is recorded from the third launch on (passes 2 and 3 and the second cold cells); a dash = not recorded. Share (est.) = warnings divided by the cell\'s new shard placements, est. per request as ceil((prompt tokens not served from the prefix cache + 1536 generated tokens) / 1024), summed over the 80 requests from the harness\'s usage data. Values above 100 % mean the estimate of new placements is low (the probe\'s own requests between cells are not in it). First warning = the round (of 10) in which the first warning of the cell fell. Last warning = its position as a percentage of the cell\'s wall time. Free space = the allocator\'s free_total after the cell on the card with the least, in MiB (56 MiB = 59,113,472 B = the residue of a full card). Source: exec/prefill-amx-vs-fpga-20260921/hbm-exhaustion-cells.json (hbm_cells.py maps the journal lines and the recorded counters onto the perf.json cell windows).</p>')
    fb = [c["free_before_min"] for c in d["cells"] if c["tag"].startswith("fpga") and c.get("free_before_min") and (c["prompt"] == 1024 or "cold" in c["tag"])]
    fbx = [c["free_before_max"] for c in d["cells"] if c["tag"].startswith("fpga") and c.get("free_before_max") and (c["prompt"] == 1024 or "cold" in c["tag"])]
    fr_lo, fr_hi = min(fb) / 1e9, max(fbx) / 1e9
    cap_gb = 2 ** 35 / 1e9
    # cells whose exhaustion lasted to the end of the cell vs cells where the space came free before the end
    ended_full = [c for c in d["cells"] if c["tag"].startswith("fpga") and c["lose"] and c.get("free_min_after") and c["last_pct"] >= 94]
    ended_free = [c for c in d["cells"] if c["tag"].startswith("fpga") and c["lose"] and c.get("free_min_after") and c["last_pct"] < 94]
    H.append(f'<p>What the card holds (tron source at 30c4ac82cb, read 2026-09-22, and the recorded counters). The card-side K/V allocator (the code that hands out card memory to shards) manages one 1 GiB address range, fixed at compile time. Every allocation occupies that range on each of the card\'s 32 memory channels (the card\'s independent memory ports). So a card offers 32 GiB of K/V space, which is what the engines\' FUSE stats report (FUSE = Filesystem in Userspace, the file-like interface through which an engine exposes its counters; capacity 34,359,738,368 bytes on every device). The FPGA weights share that space. One 1024-token shard of qwen3-4b (36 layers) takes 4.5 MiB per channel, which is 144 MiB per card. If the weights took none of the space, a card would hold 227 shards (1 GiB / 4.5 MiB), about 232,000 tokens (est.). The recorded free space gives the real figure: before the first cell of each third-launch run, on freshly provisioned engines that had served only the harness\'s warm-up requests, the allocator reported {fr_lo:.1f} to {fr_hi:.1f} GB free per card (8 runs x 8 cards) out of {cap_gb:.1f} GB. So the weights and fixed allocations take about {cap_gb - fr_hi:.1f} to {cap_gb - fr_lo:.1f} GB per card, and a card holds about {fr_lo * 1e9 / (144 * MiB):.0f} to {fr_hi * 1e9 / (144 * MiB):.0f} shards, roughly 205,000 to 210,000 tokens (est.: the warm-up requests\' shards are counted as used). A shard is released only when the host prefix cache evicts its tree node (the prefix cache stores prompt prefixes as a tree, one node per stored prefix). A request ending does not release its shard. Every warning names the largest free block at that moment: 0x3000 (12 KiB) on the lower-numbered card of every engine and 0x5800 (22 KiB) on the other ({av.get("0x3000", 0):,} and {av.get("0x5800", 0):,} lines), constant through both windows. In every recorded pass-cell that was still exhausted when it ended (last warning at 94 % of the cell or later: {len(ended_full)} pass-cells at 4096, 5120, 6144 and 8192) the free_total after the cell is 59,113,472 B (56.4 MiB) on the card with the least. 56 MiB free in blocks of at most 22 KiB, against 144 MiB per shard, means the space was full. Fragmentation played no part there. In the {len(ended_free)} recorded pass-cells where the space came free before the cell ended (6144 and 7168 in passes 2 and 3) the reading after the cell is {min(c["free_min_after"] for c in ended_free) / 1e9:.1f} to {max(c["free_min_after"] for c in ended_free) / 1e9:.1f} GB, and the constant largest-free-block value in their warning lines is the only evidence about the state at warning time. No environment variable or config changes the space or the shard size. The fallback counter (sw_fallback_total per device), recorded per cell from the third launch on, equals the journal\'s warning count in every cell [src/pos/driver.cpp:884-894; src/tron/gof.cpp:34-39, 64-103; h/pos/device.hpp:459-479; h/tron/shard.hpp:8-31; src/pos/alloc.cpp:350-387; h/pos/alloc.hpp:87-93; src/rinzler.cpp:4258-4283].</p>')
    def free_after(p):
        v = [c["free_min_after"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, p, "warm") if c.get("free_min_after")]
        return (min(v) / 1e9, max(v) / 1e9) if v else (None, None)
    f10, f15, f20, f30 = free_after(1024), free_after(1536), free_after(2048), free_after(3000)
    c71 = [c for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 7168, "warm")]
    f71_clean = [c["free_min_after"] / 1e9 for c in c71 if c["lose"] == 0 and c.get("free_min_after")]
    n81 = [c for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 8192, "warm") if c["lose"]]
    sh_ex = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120) for c in hbm_group(d, arm, p, "warm") if c.get("share_new_pct") is not None]
    sh61 = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 6144, "warm") if c.get("share_new_pct") is not None]
    lp61 = [c["last_pct"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 6144, "warm") if c["lose"]]
    H.append(f'<p>Reading. Inside a pass the harness reuses the same conversation seeds (the fixed prompt texts each simulated user starts from). The prefix cache therefore keeps the K/V of earlier requests alive. Their shards stay on the card as well. The recorded free space shows the fill (passes 2 and 3, the card with the least): {rs(*f10)} GB after the 1024 cell, {rs(*f15)} GB after 1536, {rs(*f20)} GB after 2048 and {rs(*f30, fmt="{:.1f}")} GB after 3000. By the end of the 3000 cell the card is full: the probe requests in the gap before 4096 could not place their first shard, in every pass. In the 4096 and 5120 cells the space stayed full through the whole cell in every pass (first warning in round 1, last at 97 to 99 % of the cell, {rs(min(sh_ex), max(sh_ex))} % of the cells\' new shard placements failed, est.). In the 6144 cells it was full from round 1 until {rs(min(lp61), max(lp61))} % of the cell ({rs(min(sh61), max(sh61))} % of the new placements failed). In the 7168 cells no new shard failed in {sum(1 for c in c71 if c["lose"] == 0)} of the {len(c71)} pass-cells ({rs(min(f71_clean), max(f71_clean), fmt="{:.1f}")} GB free after the cell in the recorded ones). In the other {sum(1 for c in c71 if c["lose"])} ({", ".join(str(c["lose"]) for c in c71 if c["lose"])} warnings) every warning came from the one engine that had restarted earlier in that pass (fpgabase pass 2 at 2048, fpgacanon pass 3 at 1536), whose card filled later than the others (hypothesis, from the per-engine counters). In the 8192 cells new shards failed again from round {rs(min(c["first_round"] for c in n81), max(c["first_round"] for c in n81))} ({rs(min(c["share_new_pct"] for c in n81), max(c["share_new_pct"] for c in n81))} % of new placements, est.). The release during the 6144 and 7168 cells is not measured (hypothesis: the host prefix cache evicted the oldest seeds\' nodes during the long 6144 cell, which released their shards). So the warm FPGA numbers at 4096 to 6144 are hybrids of FPGA and CPU attention in every pass, with nearly all new context on the CPU at 4096 and 5120. At 7168 and 8192 the new shards were mostly placed, but shards inherited from the exhausted cells through the prefix cache kept their CPU attention without a new warning, so the CPU share there is not measured. The cold cells (fresh engines, no warning) are the clean FPGA-attention numbers at every length. What this does and does not explain about the AMX build\'s warm gains is in the paragraph before this subsection.</p>')
    return H


'''
s = s[:a] + new_fn + s[b:]

# ---- section 6 targeted edits
s = rep(s, """With 8 users on one engine and no prefix-cache reuse (runtron, section 7) the AMX build prefills 0.3 to 2.0 % faster under FPGA attention (n = 3 per cell, paired t -0.7 to -17). The cause of the warm gain is not settled (section 5). At 4096 to 6144 it co-occurs in every pass with the card's K/V space running out, which moved {min(ex_share):.0f} to {max(ex_share):.0f} % of those cells' shard placements to the CPU (est.), where the AMX kernel replaces the AVX loop. That is a measured co-occurrence, not a measured cause. The gain also appears where nothing fell back: at 2048 ({c2048['ttft_pct']:+.1f} %, 0 warnings in all 6 pass-cells) and at 7168 ({plist(c7168)} in the three pairs, 0 warnings in {sum(1 for x in l71 if x == 0)} of the 6 pass-cells).</p>""",
           """With 8 or 2 users on one engine and no prefix-cache reuse (runtron, section 7) the two builds prefill within 2 % of each other under FPGA attention (-2.0 to +0.3 %, n = 3 per cell). The AMX build is faster in 5 of the 6 cells there. The paired t is -7.9 to -17 in four cells and -0.7 and +1.8 in the other two. The two arms did not see the same prefix-cache share in a paired warm cell (table below). Per uncached prompt token the warm gains from 4096 up are {r0(tk_hi)} to {r0(tk_lo)} % ({r0(tl_hi)} to {r0(tl_lo)} % raw). The cause of the warm gain is not settled (section 5). At 4096 and 5120 it co-occurs in every pass with the card's K/V space running out. There nearly every new shard placement failed ({r0(min(ex_share45))} to {r0(max(ex_share45))} % of the new placements, est.), so both arms scored nearly all new context on the CPU, where the AMX kernel replaces the AVX loop. At 6144 {r0(min(ex_share61))} to {r0(max(ex_share61))} % of the new placements failed. That is a measured co-occurrence, not a measured cause. The gain also appears at 2048 ({c2048['ttft_pct']:+.1f} %), where no shard had failed in any pass and none could have been inherited. At 7168 ({plist(c7168)} in the three pairs) shards inherited from the exhausted cells may have kept their CPU attention without a new warning (section 5), so that cell settles nothing.</p>""")
s = rep(s, """    ex_share = [c["share_est_pct"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120, 6144) for c in (hbm_group(hb, arm, p, "warm") if hb else [])]
""", """    ex_share45 = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120) for c in (hbm_group(hb, arm, p, "warm") if hb else []) if c.get("share_new_pct") is not None]
    ex_share61 = [c["share_new_pct"] for arm in ("fpgabase", "fpgacanon") for c in (hbm_group(hb, arm, 6144, "warm") if hb else []) if c.get("share_new_pct") is not None]
    tk_lo, tk_hi = rng(warm_long, "tok_pct")
""")
s = rep(s, """The gains at 2048 ({c2048['ttft_pct']:+.1f} %, 0 warnings in all 6 pass-cells) and at 7168 ({c7168['ttft_pct']:+.1f} %, 0 warnings in {sum(1 for x in l71 if x == 0)} of 6 pass-cells) are not explained by fallback (hypothesis in section 5: cached-prefix pages scored on the CPU). At 8192 the two arms also differ in how much fell back""",
           """The gain at 2048 ({c2048['ttft_pct']:+.1f} %) is not explained by fallback: no shard had failed before or during any 2048 cell (hypothesis in section 5: cached-prefix pages scored on the CPU). At 7168 ({c7168['ttft_pct']:+.1f} %, no new failure in {sum(1 for x in l71 if x == 0)} of 6 pass-cells) inherited degraded shards may have run CPU attention without a warning, so that cell is not evidence either way. Three FPGA-arm cells had one engine restart during the cell (fpgabase pass 2 at 2048, fpgabase pass 3 at 7168, fpgacanon pass 3 at 1536, section 5), which adds noise to those pairs. At 8192 the two arms also differ in how much fell back""")
s = rep(s, """So in those three cells the AMX build's gains ({abs(ex_t_hi):.0f} to {abs(ex_t_lo):.0f} % lower TTFT, {ex_p_lo:+.0f} to {ex_p_hi:+.0f} % TPS on average) include AMX against AVX on the share of attention that moved to the CPU.""",
           """So in those three cells the AMX build's gains ({r0(ex_t_hi)} to {r0(ex_t_lo)} % lower TTFT, {ex_p_lo:+.1f} to {ex_p_hi:+.1f} % TPS on average) include AMX against AVX on the share of attention that moved to the CPU.""")
s = rep(s, """In the warm cells at 4096 to 8192 the AMX build prefilled {abs(tl_hi):.0f} to {abs(tl_lo):.0f} % faster than the AVX build""", """In the warm cells at 4096 to 8192 the AMX build prefilled {r0(tl_hi)} to {r0(tl_lo)} % faster than the AVX build""")
s = rep(s, """Welch t over the pass means of the two arms). Middle:""",
           """Welch t over the pass means of the two arms; the per-uncached-token column divides each pass\\'s TTFT by its prompt tokens not served from the prefix cache before taking the delta, because the two arms saw different prefix-cache shares in the same cell). Middle:""")
# ---- Short version: three short sentences + key numbers
a = s.index("        H.append(f'<p>At prompt 1024, prefill takes about the same time with the AMX kernel on the CPU as with attention on the FPGA (every matched pair within")
b = s.index("(sections 6 and 7).</p></div>')\n", a) + len("(sections 6 and 7).</p></div>')\n")
new_sv = """        rowsA = FS.load()
        t5120 = FS.welch([r["ttft_harness_ms"] for r in rowsA if r["arm"] == "canon" and r["prompt_length"] == 5120 and not r["cold"]], [r["ttft_harness_ms"] for r in rowsA if r["arm"] == "fpgacanon" and r["prompt_length"] == 5120 and not r["cold"]])
        c_fb = FS.mean(agg0.get("fpgabase", {}).get(8192, {}).get("cold", []))
        H.append(f'<p>At prompt 1024, prefill takes about the same time with the AMX kernel on the CPU as with attention on the FPGA. '
                 f'From prompt 2048 up the FPGA is faster, up to {c_cpu / c_fc:.1f}x at a cold 8192-token prompt, and the AMX kernel on the CPU is itself {w_b / w_c:.1f}x faster than the old AVX kernel at that length. '
                 f'Under FPGA attention the AMX build lowers the warm TTFT by 33 to 49 % from prompt 4096 up (cause not settled, section 5), but without a warm prefix cache it changes prefill by at most 8 % and decode by at most 2 % (sections 6 and 7).</p></div>')
        H.append('<p class="cap"><b>Key numbers behind the Short version.</b></p><ul>')
        H.append(f'<li>Prompt 1024 (sections 1 to 3): every matched pair of the canonical build is within {ca_lo:+.1f} % to {ca_hi:+.1f} % (FPGA minus CPU).</li>')
        H.append(f'<li>Cold 8192-token prefill, CI harness, 2 users per engine (section 5): {c_fc / 1000:.1f} s on the FPGA with the AMX build, {c_fb / 1000:.1f} s with the AVX build, {c_cpu / 1000:.1f} s with the AMX kernel on the CPU (one run of 2026-09-19). FPGA against CPU AMX: {c_cpu / c_fc:.1f}x.</li>')
        H.append(f'<li>8 prompts of 8192 tokens at once on one engine, runtron (section 7): {rt8k["fc"]:.0f} s on the FPGA, {rt8k["cc"]:.0f} s with the AMX kernel on the CPU, {rt8k["cb"]:.0f} s with the old AVX kernel. FPGA against CPU AMX: {rt8k["cc"] / rt8k["fc"]:.1f}x. AMX against AVX on the CPU: {rt8k["cb"] / rt8k["cc"]:.1f}x.</li>')
        H.append(f'<li>Warm 8192 cells, CI harness (section 5): AVX on the CPU {w_b / 1000:.1f} s, AMX on the CPU {w_c / 1000:.1f} s ({w_b / w_c:.1f}x). The FPGA is faster than the CPU AMX kernel at every warm length from 2048 up; the 5120 pair alone is not resolved (Welch t {t5120:+.1f}).</li>')
        H.append('<li>AMX build against AVX build under FPGA attention (sections 6 and 7): warm cells from 4096 up 33 to 49 % lower TTFT in every one of three passes, cold CI cells 2 to 8 % lower, runtron cells -2.0 to +0.3 %, decode within 2 % everywhere except the warm CI cells, where three passes do not resolve it. The card\\'s K/V space ran out in the 4096 to 6144 cells of every pass (section 5), which explains the gain there but not at 2048.</li>')
        H.append('</ul>')
"""
s = s[:a] + new_sv + s[b:]
# ---- section 8 and 9 bullets
s = rep(s, "The two cold runs of one arm at one length agree within 1 to 29 ms.", "The two cold runs of one arm at one length are 10 to 41 ms apart (sd 7 to 29 ms).")
s = rep(s, """    H.append("<li>No campaign interleaved CPU-attention and FPGA-attention repetitions. runtron ran them in blocks 8 minutes to about 2 hours apart""",
           """    H.append("<li>Before 2026-09-22 no campaign interleaved CPU-attention and FPGA-attention repetitions. The runtron campaign of that day (section 7) did, inside each of its 3 repetitions, and reports the attention-mode comparison as ratios of means. Earlier, runtron ran them in blocks 8 minutes to about 2 hours apart""")
s = rep(s, """No paired t for attention mode exists. The Welch t values above compare separate blocks.</li>")""", """No paired t for attention mode exists in sections 1 to 5. The Welch t values there compare separate blocks.</li>")""")
s = rep(s, """    H.append("<li>FPGA-side n is small: one pass in canon-ci and the nightly,""", """    H.append("<li>At prompt 1024 in the earlier campaigns (sections 1 to 3) the FPGA-side n is small: one pass in canon-ci and the nightly,""")
s = rep(s, """Only wedperf-attr (n = 6) and p0perf-20260913 (n = 3) have repeats. The four wedperf pairs""", """Only wedperf-attr (n = 6) and p0perf-20260913 (n = 3) have repeats there. The 2026-09-21/22 campaigns of sections 5 to 7 have 3 passes or repetitions per arm. The four wedperf pairs""")
s = rep(s, """    H.append("<li>The runtron 8-user TTFT is the batched prefill of 8 prompts (8 forwards of 1024 tokens each).""", """    H.append("<li>At prompt 1024 (sections 1 to 3) the runtron 8-user TTFT is the batched prefill of 8 prompts of 1024 tokens.""")
s = rep(s, """Their ratio (about 4.3x at tp2, 2.6x at tp4) is a layout effect, not an attention-path effect.</li>")""", """Their ratio there (about 4.3x at tp2, 2.6x at tp4) is a layout effect, not an attention-path effect. Section 7 uses the same runtron measure at 2048 to 8192 and never mixes it with CI-harness values.</li>")""")
# ---- Words entries
s = rep(s, """pre-cell AMX probe = before every cell our campaign driver reads the EXE.AMX_BUSY hardware counter on the engine processes for 20 s while it sends 4 streaming requests of its own (about 1,100 tokens each). The count is proof that AMX instructions ran. It measures the probe\\'s own traffic in the state the engines are in at that moment, not the cell that follows.""",
           """pre-cell AMX probe = before every cell our campaign driver counts EXE.AMX_BUSY (the CPU\\'s count of cycles in which the AMX unit was busy) on the engine processes for 20 s. During that window it keeps 4 request streams of its own running. Each stream repeats a 6,000-character prompt (about 1,100 tokens, est.) with 256 generated tokens. The count is proof that AMX instructions ran. It measures the probe\\'s own traffic in the state the engines are in at that moment, not the cell that follows.""")
s = rep(s, """repetition = one full round of all cells, arms and attention modes of the runtron campaign (section 7); the campaign ran 3, interleaved, so drift in the machine touches every arm alike. paired t = the mean of the per-repetition differences (repetition k of one arm minus repetition k of the other) divided by their standard error. runtron.pre3879 = runtron built from main before PR 3879 (eb2de0265a, the AVX build); runtron.main0916 = runtron built from main on 2026-09-16 (c7844ca2ce, the canonical AMX build).""",
           """repetition = one full round of all cells, arms and attention modes of the runtron campaign (section 7). The campaign ran 3 repetitions, interleaved. A slow change of the machine\\'s state during the campaign therefore affects every arm alike. paired t = the mean of the per-repetition differences (repetition k of one arm minus repetition k of the other) divided by their standard error. runtron.pre3879 = runtron built from main before PR 3879 (eb2de0265a, the AVX build). runtron.main0916 = runtron built from main on 2026-09-16 (c7844ca2ce, the canonical AMX build).""")
save("gen_page.py", s)
print("patched all three files")
