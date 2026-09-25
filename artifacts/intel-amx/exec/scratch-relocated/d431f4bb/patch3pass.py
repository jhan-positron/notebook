import re
P = "gen_page.py"
s = open(P).read()
def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (n, old[:100])
    s = s.replace(old, new)

# ---- section 5 bullets
rep("against FPGA attention {c_fc:,.0f} ms with the AMX build and {c_fb:,.0f} ms with the AVX build (n = 1 each).",
    "against FPGA attention {c_fc:,.0f} ms with the AMX build and {c_fb:,.0f} ms with the AVX build (n = {n('fpgacanon', 8192, 'cold')} each, the two cold runs of one arm within 30 ms).")
rep("FPGA attention {c4_fc:,.0f} ms (AMX build) and {c4_fb:,.0f} ms (AVX build). No cold CPU-attention cell exists at 4096",
    "FPGA attention {c4_fc:,.0f} ms (AMX build) and {c4_fb:,.0f} ms (AVX build), n = {n('fpgacanon', 4096, 'cold')} each. No cold CPU-attention cell exists at 4096")
rep("The warm cells at 4096 to 6144 are hybrids of FPGA and CPU attention (the card\\'s K/V space was exhausted, subsection below), and the 8192 cells are hybrids from round 7 or 8 of 10 on. So the clean long-prompt comparison is the cold one: 6,743 against 12,743 ms at 8192. With one FPGA pass per cell, the direction is resolved (more than 5 CPU-side sd) at 2048, 4096, 7168 and 8192, and weak at 1536, 3000 and 5120 (1.3 to 2.9 sd).",
    "The warm cells at 4096 to 6144 are hybrids of FPGA and CPU attention in every pass (the card\\'s K/V space was exhausted, subsection below), the 7168 cells in 2 of 6 pass-cells, and the 8192 cells from round 6 to 8 of 10 on. So the clean long-prompt comparison is the cold one: {m('fpgacanon', 8192, 'cold'):,.0f} against {m('canon', 8192, 'cold'):,.0f} ms at 8192. With three FPGA passes and four CPU passes per warm cell, the Welch t of FPGA against CPU is {wt_str}: resolved (|t| above 4.3, the two-sided 5 % bound at 2 degrees of freedom) at {wt_res}, weak at {wt_weak}.")
rep("The nightly-deb FPGA value at 1024 (555 ms, one pass, platformd 0.11) is 27 to 45 ms above the same cell\\'s history (528 ms on 2026-09-18, 509.5 +/- 7.2 ms over 13 nights). With those values the 1024 ratio is 1.3x. Passes 2 and 3 will show whether 555 ms is an outlier.",
    "The nightly-deb FPGA value at 1024 ({m('fpgabase', 1024, 'cold'):,.0f} ms, mean of three passes that agree within 2 ms, platformd 0.11) is 25 to 45 ms above the same cell\\'s history (528 ms on 2026-09-18, 509.5 +/- 7.2 ms over 13 nights). The agreement across passes makes it a systematic offset of this layout and client, not an outlier (hypothesis: the test proxy on port 80 or the client host; not measured). With the history values the 1024 ratio is 1.3x.")
# Welch t list computed before the bullets: insert after the S dict is built. Find the line that defines pc() helper and add after it.
rep("""    def pc(x, y):
""", """    rows6 = FS.load()
    def wt(p):
        a = [r["ttft_harness_ms"] for r in rows6 if r["arm"] == "canon" and r["prompt_length"] == p and not r["cold"]]
        b = [r["ttft_harness_ms"] for r in rows6 if r["arm"] == "fpgacanon" and r["prompt_length"] == p and not r["cold"]]
        return FS.welch(a, b)
    wts = {p: wt(p) for p in (1536, 2048, 3000, 4096, 5120, 6144, 7168, 8192)}
    wt_str = ", ".join(f"{p}: {t:+.1f}" for p, t in wts.items() if t is not None)
    wt_res = ", ".join(str(p) for p, t in wts.items() if t is not None and abs(t) > 4.3)
    wt_weak = ", ".join(str(p) for p, t in wts.items() if t is not None and abs(t) <= 4.3)
    def pc(x, y):
""")
# Reading paragraph after the record table
rep("The CPU build moves the cold FPGA prefill by 2 to 6 % (the AMX build is faster in all three cold pairs, n = 1 each), so the card sets most of the cold number, not all of it. The warm FPGA numbers at 4096 to 6144 are hybrids of FPGA and CPU attention (the card\\'s K/V space was exhausted, subsection above), and the 8192 cells are hybrids from round 7 or 8 of 10 on. So the cold cells are the ones to quote for long prompts.",
    "The CPU build moves the cold FPGA prefill by 2 to 8 % (the AMX build is faster in all seven cold pass-pairs: n = 3 at 1024, n = 2 at 4096 and 8192). So the card sets most of the cold number, not all of it. The warm FPGA numbers at 4096 to 6144 are hybrids of FPGA and CPU attention in every pass (the card\\'s K/V space was exhausted, subsection above), the 7168 numbers in 2 of 6 pass-cells, and the 8192 numbers from round 6 to 8 of 10 on. So the cold cells are the ones to quote for long prompts.")
# Figure 3 caption
rep("Squares mark cold cells (a single-cell driver run on fresh engines): the FPGA arms at 4096 and 8192, and the canonical CPU arm at 8192 (the 2026-09-19 check cell).",
    "Squares mark cold cells (single-cell driver runs on fresh engines, mean of two runs for the FPGA arms): the FPGA arms at 4096 and 8192, and the canonical CPU arm at 8192 (the 2026-09-19 check cell, one run).")

# ---- the mechanisms paragraph
a = s.index("    H.append('<p class=\"hyp\">Why the AMX build helps only the warm cells under FPGA attention: two candidate mechanisms")
b = s.index("\n", a) + 1
new_hyp = '''    c6 = {(c["prompt"], c["kind"]): c for c in FS.amx_vs_avx_rows(rows6)}
    wl = [c6[(p, "warm")] for p in (4096, 5120, 6144, 7168, 8192)]
    wl_lo, wl_hi = min(c["ttft_pct"] for c in wl), max(c["ttft_pct"] for c in wl)
    wl_all = [v for c in wl for v in c["ttft_pcts"]]
    c2k, c15, c30, c71 = c6[(2048, "warm")], c6[(1536, "warm")], c6[(3000, "warm")], c6[(7168, "warm")]
    cold6 = [c6[k] for k in ((1024, "cold"), (4096, "cold"), (8192, "cold")) if k in c6]
    H.append(f'<p class="hyp">Why the AMX build helps only the warm cells under FPGA attention: two candidate mechanisms, neither proven for every cell. The measurements first (means of the per-pass deltas over 3 paired passes per cell, section 6). The AMX build lowers the warm TTFT by {abs(wl_hi):.0f} to {abs(wl_lo):.0f} % from prompt 4096 up, and in every one of the {len(wl_all)} paired passes ({min(wl_all):+.0f} to {max(wl_all):+.0f} %). At 2048 it lowers it by {abs(c2k["ttft_pct"]):.0f} % on average ({", ".join(f"{v:+.1f}" for v in c2k["ttft_pcts"])} % per pass). At 1536 and 3000 the means are {c15["ttft_pct"]:+.1f} and {c30["ttft_pct"]:+.1f} %, with Welch t {c15["t_ttft"]:+.1f} and {c30["t_ttft"]:+.1f}, so not resolved. In the cold cells it lowers TTFT by {abs(max(c["ttft_pct"] for c in cold6)):.0f} to {abs(min(c["ttft_pct"] for c in cold6)):.0f} % (n = 2 to 3 per cell). Mechanism 1, measured as a co-occurrence (next subsection): in every pass the 4096, 5120 and 6144 cells ran with the card\\'s K/V space exhausted from round 1 until 60 to 99 % of the cell. Part of those cells\\' attention therefore ran on the CPU. On the CPU the AMX kernel replaces the AVX loop. Mechanism 1 cannot explain three cases. The 2048 cells had no exhaustion warning in any pass and still read {c2k["ttft_pct"]:+.0f} % on average. The 7168 cells had no warning in 4 of the 6 pass-cells and read {", ".join(f"{v:+.1f}" for v in c71["ttft_pcts"])} % in the three pairs. At 8192 the first warning of either arm came in round 6 to 8 of 10, and in the first pass the AMX build\\'s TTFT over rounds 1 to 6 was 3,695 ms against 5,545 ms (-33 %, means of the harness\\'s per-round values, 8 users per round). Mechanism 2, a hypothesis: in a warm request the K/V pages (64-token blocks) that come from the prefix cache are scored on the CPU while the card\\'s copy lags (the DMA-lag rule of section 4), and the AMX kernel covers that work. Evidence in the same direction, not proof: in the first FPGA pass the pre-cell AMX probe (defined under Words used here) read 16 to 21 billion AMX-busy cycles in the five warm-state windows that had no exhaustion warning, against 10.6 to 13.4 billion on fresh engines and 32.6 and 32.3 billion in the two windows where the card was full (fpgacanon arm, one 20 s window per cell, more cycles = more attention work ran through the AMX kernel). The probe measures its own 4 requests, not the cell. Test that would settle it: a perfetto trace of one warm 2048 request, AMX build against kill switch. The per-card fallback counter, recorded per cell since the second launch, confirms the exhaustion counts but cannot separate the two mechanisms.</p>')
'''
s = s[:a] + new_hyp + s[b:]

# ---- hbm_subsection: aggregated over passes
a = s.index("def hbm_subsection():")
b = s.index("def section6_amx_vs_aof(rows):")
new_fn = r'''def hbm_load():
    return json.load(open(HBM_JSON)) if os.path.exists(HBM_JSON) else None


def hbm_group(d, arm, prompt, kind):
    """The cells of one arm at one prompt length, warm (inside a pass) or cold (single-cell runs), sorted by tag."""
    return sorted([c for c in d["cells"] if c["tag"].startswith(arm) and c["prompt"] == prompt and (("cold" in c["tag"]) == (kind == "cold"))], key=lambda c: c["tag"])


def hbm_subsection():
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
    H.append(f'<p>The engine journal (the systemd log of the four rinzler engines) of the two campaign windows (2026-09-21 22:30 to 2026-09-22 01:30 UTC and 2026-09-22 13:00 to 16:30 UTC) holds {d["total_lose"]:,} warnings of the form "HBM bypass space exhausted, caller degrades to SW attention" followed by "shard base tok_ix N: 36 of 36 slots lose HW attention" [exec/results/q4b-fpga-20260921/hbm-journal-20260921.txt, hbm-journal-20260922.txt]. HBM is the card\'s memory. A shard is the card-side copy of 1024 tokens of one request\'s K/V, placed on one of the engine\'s two cards. One warning means one shard could not be placed on its card, and that shard\'s attention ran on the CPU instead. {d["inside_cells"]:,} warnings fall inside cells (between the harness\'s start and end time of a cell). The other {n_gap:,} fall in the 30 s gaps between cells of the {n_passes} FPGA passes: after the 3000, 4096 and 5120 cells in every pass ({len(gap_after.get(3000, []))}, {len(gap_after.get(4096, []))} and {len(gap_after.get(5120, []))} of {n_passes} passes), after the 6144 cell in {len(gap_after.get(6144, []))} passes, never after 7168. In those gaps our campaign driver (the script that provisions the engines and runs the harness cells) runs the pre-cell AMX probe, which sends 4 streaming requests of its own (about 1,100 tokens each). The gap warnings name only shard bases 0 and 1024. So they are the probe\'s own requests, which could not place even their first shard. They show that the card was already full when each 3000 cell ended and stayed full to the start of the 6144 cell. The first warning of the first window is at 22:45:30 UTC, 12 s after the prompt-3000 cell of the first FPGA pass ended and 19 s before the first round of its prompt-4096 cell. None of the warnings fall in the CPU-attention pass or in the {n_cold} cold cells. None appear in any earlier FPGA-attention run at prompt 1024: 0 warnings in the 190 runtron logs of issue 4500, wedperf, wedperf-attr and vnnik4-models, and 0 in the 9 engine logs of the p0perf-20260913 CI cells.</p>')
    H.append('<div class="tw"><table class="num"><thead><tr><th>cell</th><th>passes</th><th>warnings per pass</th><th>fallback counter per pass (recorded from the second launch on)</th><th>share of the cell\'s shard placements (est.)</th><th>first warning (round of 10)</th><th>last warning (% of the cell)</th><th>free space after the cell, lowest card (MiB)</th><th>reading</th></tr></thead><tbody>')
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
                if not any(w):
                    reading = "clean: fresh engines, every shard on the card" if kind == "cold" else "clean: every shard on the card"
                elif all(w) and all(x == 1 for x in fr) and min(lp) >= 95:
                    reading = "exhausted through the whole cell in every pass"
                elif all(w) and all(x == 1 for x in fr):
                    reading = f"exhausted from round 1 until {min(lp)} to {max(lp)} % of the cell"
                elif not all(w):
                    reading = f"exhausted in {sum(1 for x in w if x)} of {len(w)} passes (from round {min(fr)}, until {min(lp)} to {max(lp)} % of the cell)"
                else:
                    reading = f"clean until round {min(fr) - 1} to {max(fr) - 1}, exhausted after"
                share = "-" if not any(w) else f'{min(c["share_est_pct"] for c in cs if c["lose"]):.0f} to {max(c["share_est_pct"] for c in cs if c["lose"]):.0f} % of {cs[0]["shards_est"]}'
                H.append(f'<tr><td>{esc(FS.ARM_LABEL.get(arm, arm))}, prompt {p}, {kind}</td><td>{len(cs)}</td><td>{fmt_list(w)}</td><td>{fmt_list([c.get("fallback_counter") for c in cs])}</td><td>{share}</td><td>{fmt_list([c["first_round"] for c in cs])}</td><td>{fmt_list([c["last_pct"] for c in cs])}</td><td>{fmt_list([None if c.get("free_min_after") is None else round(c["free_min_after"] / MiB) for c in cs], "{:,}")}</td><td>{reading}</td></tr>')
    H.append('</tbody></table></div>')
    H.append('<p class="cap">Passes in tag order (pass 1, 2, 3 for warm cells, the two single-cell runs for cold cells). One warning per shard per engine (a shard sits on one card). Fallback counter = the engines\' sw_fallback_total FUSE stat, summed over the 4 engines x 2 cards, as the difference across the cell. It is recorded from the second launch on (passes 2 and 3 and the second cold cells); a dash = not recorded. Share (est.) = warnings divided by the cell\'s shard placements, est. as 80 requests x ceil((prompt + 1536 generated tokens) / 1024) shards of 1024 tokens. First warning = the round (of 10) in which the first warning of the cell fell. Last warning = its position as a percentage of the cell\'s wall time. Free space = the allocator\'s free_total after the cell on the card with the least, in MiB (56 MiB = 59,113,472 B = the residue of a full card). Cells with 0 warnings ran with every shard on the card. Source: exec/prefill-amx-vs-fpga-20260921/hbm-exhaustion-cells.json (hbm_cells.py maps the journal lines and the recorded counters onto the perf.json cell windows).</p>')
    # free space on fresh engines, from the second-launch cold cells: free after the cell + the cell's own shards
    fresh = []
    for c in d["cells"]:
        if c["tag"].startswith("fpga") and "cold2" in c["tag"] and c.get("free_min_after"):
            shards = 20 * -(-(c["prompt"] + d["gen_tokens"]) // d["shard_tokens"])
            per_card = shards * 144 * MiB / 2
            fresh += [(c["free_min_after"] + per_card) / 1e9, (c["free_max_after"] + per_card) / 1e9]
    fresh_lo, fresh_hi = (min(fresh), max(fresh)) if fresh else (None, None)
    cap_gb = 2 ** 35 / 1e9
    H.append(f'<p>What the card holds (tron source at 30c4ac82cb, read 2026-09-22, and the recorded counters). The card-side K/V allocator (the code that hands out card memory to shards) manages one 1 GiB address range, fixed at compile time. Every allocation occupies that range on each of the card\'s 32 memory channels (the card\'s independent memory ports). So a card offers 32 GiB of K/V space, which is what the engines\' FUSE stats report (FUSE = Filesystem in Userspace, the file-like interface through which an engine exposes its counters; capacity 34,359,738,368 bytes on every device). The FPGA weights share that space. One 1024-token shard of qwen3-4b (36 layers) takes 4.5 MiB per channel, which is 144 MiB per card. If the weights took none of the space, a card would hold 227 shards (1 GiB / 4.5 MiB), about 232,000 tokens (est.). The recorded free space after the four second-launch cold cells gives the real figure: about {fresh_lo:.0f} to {fresh_hi:.0f} GB free per card on fresh engines (est.: free_total after the cell plus that cell\'s own shards, 20 requests x ceil((prompt + 1536) / 1024) x 144 MiB per engine over its two cards), out of {cap_gb:.1f} GB. So the weights and fixed allocations take about {cap_gb - fresh_hi:.1f} to {cap_gb - fresh_lo:.1f} GB per card (est.), and a card holds about {fresh_lo * 1e9 / (144 * MiB):.0f} to {fresh_hi * 1e9 / (144 * MiB):.0f} shards (est.), roughly 200,000 to 215,000 tokens. A shard is released only when the host prefix cache evicts its tree node (the prefix cache stores prompt prefixes as a tree, one node per stored prefix). A request ending does not release its shard. Every warning names the largest free block at that moment: 0x3000 (12 KiB) on the lower-numbered card of every engine and 0x5800 (22 KiB) on the other ({av.get("0x3000", 0):,} and {av.get("0x5800", 0):,} lines), constant through both windows. The recorded free_total in the exhausted cells is 59,113,472 B (56.4 MiB) on every card that warned, in every pass. 56 MiB free in blocks of at most 22 KiB, against 144 MiB per shard, means the space was full. Fragmentation played no part (the first version of this subsection left "full or fragmented" open). No environment variable or config changes the space or the shard size. The fallback counter (sw_fallback_total per device), recorded per cell from the second launch on, equals the journal\'s warning count in every cell [src/pos/driver.cpp:884-894; src/tron/gof.cpp:34-39, 64-103; h/pos/device.hpp:459-479; h/tron/shard.hpp:8-31; src/pos/alloc.cpp:350-387; h/pos/alloc.hpp:87-93; src/rinzler.cpp:4258-4283].</p>')
    def free_after(p):
        v = [c["free_min_after"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, p, "warm") if c.get("free_min_after")]
        return (min(v) / 1e9, max(v) / 1e9) if v else (None, None)
    f10, f15, f20, f30, f71 = free_after(1024), free_after(1536), free_after(2048), free_after(3000), free_after(7168)
    n71 = [c["lose"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 7168, "warm")]
    n81 = [c for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 8192, "warm") if c["lose"]]
    sh_ex = [c["share_est_pct"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120) for c in hbm_group(d, arm, p, "warm")]
    lp61 = [c["last_pct"] for arm in ("fpgabase", "fpgacanon") for c in hbm_group(d, arm, 6144, "warm") if c["lose"]]
    H.append(f'<p>Reading. Inside a pass the harness reuses the same conversation seeds (the fixed prompt texts each simulated user starts from). The prefix cache therefore keeps the K/V of earlier requests alive. Their shards stay on the card as well. The recorded free space shows the fill (passes 2 and 3, the card with the least): {f10[0]:.0f} to {f10[1]:.0f} GB after the 1024 cell, {f15[0]:.0f} to {f15[1]:.0f} GB after 1536, {f20[0]:.0f} to {f20[1]:.0f} GB after 2048 and {f30[0]:.1f} to {f30[1]:.1f} GB after 3000. By the end of the 3000 cell the card is full: the probe requests in the gap before 4096 could not place their first shard, in every pass. In the 4096 and 5120 cells the space stayed full through the whole cell in every pass (first warning in round 1, last at 97 to 99 % of the cell, {min(sh_ex):.0f} to {max(sh_ex):.0f} % of the cells\' shard placements failed, est.). In the 6144 cells it was full from round 1 until {min(lp61)} to {max(lp61)} % of the cell. In the 7168 cells the space had come free in {sum(1 for x in n71 if x == 0)} of the {len(n71)} pass-cells ({f71[0]:.0f} to {f71[1]:.0f} GB free after the cell) and was exhausted in {sum(1 for x in n71 if x)} ({", ".join(str(x) for x in n71 if x)} warnings). In the 8192 cells it filled again from round {min(c["first_round"] for c in n81)} to {max(c["first_round"] for c in n81)} ({min(c["share_est_pct"] for c in n81):.0f} to {max(c["share_est_pct"] for c in n81):.0f} % of placements failed, est.). The release during the 6144 and 7168 cells is not measured (hypothesis: the host prefix cache evicted the oldest seeds\' nodes during the long 6144 cell, which released their shards). So the warm FPGA numbers at 4096 to 6144 are hybrids of FPGA and CPU attention in every pass, the 7168 numbers are hybrids in {sum(1 for x in n71 if x)} pass-cells of {len(n71)}, and the 8192 numbers are hybrids in their last rounds. The cold cells (fresh engines, no warning) are the clean FPGA-attention numbers at every length. What this does and does not explain about the AMX build\'s warm gains is in the paragraph before this subsection.</p>')
    return H


'''
s = s[:a] + new_fn + s[b:]

# ---- section 6: whole function
a = s.index("def section6_amx_vs_aof(rows):")
b = s.index("# ---------------------------------------------------------------- page")
new6 = r'''def section6_amx_vs_aof(rows):
    """jhan, 2026-09-22 01:5x UTC: 'is it a pattern that AMX + AoF perf > AoF alone perf? For both decode TPS and prefill.'"""
    cells = FS.amx_vs_avx_rows(rows)
    warm = [c for c in cells if c["kind"] == "warm"]
    cold = [c for c in cells if c["kind"] == "cold"]
    warm_long = [c for c in warm if c["prompt"] >= 4096]
    def rng(xs, key):
        v = [x[key] for x in xs if x.get(key) is not None]
        return (min(v), max(v)) if v else (None, None)
    def rng_all(xs, key):
        v = [y for x in xs for y in x[key]]
        return (min(v), max(v)) if v else (None, None)
    def by(p, kind):
        return [c for c in cells if c["prompt"] == p and c["kind"] == kind][0]
    def plist(c, key="ttft_pcts"):
        return ", ".join(f"{v:+.1f}" for v in c[key]) + " %"
    def lst(xs, key, fmt):
        return ", ".join(f"{c['prompt']}: {c[key]:{fmt}} %" for c in xs)
    tl_lo, tl_hi = rng(warm_long, "ttft_pct"); tla_lo, tla_hi = rng_all(warm_long, "ttft_pcts")
    tt_lo, tt_hi = rng(warm_long, "t_ttft")
    pl_lo, pl_hi = rng(warm_long, "tps_pct"); pla_lo, pla_hi = rng_all(warm_long, "tps_pcts")
    tc_lo, tc_hi = rng(cold, "ttft_pct"); pc_lo, pc_hi = rng(cold, "tps_pct")
    c1024, c1536, c2048, c3000, c7168 = by(1024, "cold"), by(1536, "warm"), by(2048, "warm"), by(3000, "warm"), by(7168, "warm")
    c4c, c8c = by(4096, "cold"), by(8192, "cold")
    exh = [c for c in warm if c["prompt"] in (4096, 5120, 6144)]
    ex_t_lo, ex_t_hi = rng(exh, "ttft_pct"); ex_p_lo, ex_p_hi = rng(exh, "tps_pct")
    sign_mixed = [c["prompt"] for c in warm_long if min(c["tps_pcts"]) < 0 < max(c["tps_pcts"])]
    n_pairs_long = sum(c["n"] for c in warm_long)
    wc = []
    for w in warm:
        for c in cold:
            if c["prompt"] == w["prompt"]:
                wc += [100.0 * (w["tps_avx"] - c["tps_avx"]) / c["tps_avx"], 100.0 * (w["tps_amx"] - c["tps_amx"]) / c["tps_amx"]]
    wc_lo, wc_hi = (min(wc), max(wc)) if wc else (None, None)
    prior_earlier = [p for i, p in enumerate(FS.PRIOR_1024) if i != 2]   # this campaign's own 1024 pair is already a cell above
    pe_t = [100.0 * (p[4] - p[5]) / p[5] for p in prior_earlier]
    pe_p = [100.0 * (p[6] - p[7]) / p[7] for p in prior_earlier]
    hb = hbm_load()
    def lose_list(arm, p):
        return [c["lose"] for c in hbm_group(hb, arm, p, "warm")] if hb else []
    ex_lose = [c["lose"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120, 6144) for c in (hbm_group(hb, arm, p, "warm") if hb else [])]
    ex_share = [c["share_est_pct"] for arm in ("fpgabase", "fpgacanon") for p in (4096, 5120, 6144) for c in (hbm_group(hb, arm, p, "warm") if hb else [])]
    l71 = lose_list("fpgabase", 7168) + lose_list("fpgacanon", 7168)
    H = []
    H.append("<h2>6. Is AMX plus FPGA attention better than FPGA attention alone?</h2>")
    H.append("<p>Question (jhan, 2026-09-22): from the data so far, is it a pattern that the AMX build with attention on the FPGA beats the AVX build with attention on the FPGA, for both prefill and decode? The comparison below holds the attention mode fixed (FPGA) and changes only the CPU build: canonical AMX deb against the nightly deb (no AMX code). The two arms ran as separate passes on the same evening or afternoon, and the comparison pairs pass 1 with pass 1, pass 2 with pass 2, pass 3 with pass 3 (three warm passes per arm, two or three cold runs per arm and length). The VNNI-K deb is listed separately at the end.</p>")
    H.append('<div class="short"><p><b>Answer.</b></p>')
    H.append(f"<p><b>Prefill: yes in warm cells from prompt 4096 up, resolved over three passes. In cold cells the AMX build is faster by 2 to 8 %. At 1536 and 3000 the difference is not resolved.</b> In the warm cells at 4096 to 8192 the AMX build prefilled {abs(tl_hi):.0f} to {abs(tl_lo):.0f} % faster than the AVX build (means of the per-pass deltas, 3 paired passes per cell). It was faster in every one of the {n_pairs_long} paired passes (per-pass range {tla_lo:+.1f} to {tla_hi:+.1f} %). The Welch t over the three pass means per arm is {tt_lo:+.1f} to {tt_hi:+.1f}. At 2048 the mean is {c2048['ttft_pct']:+.1f} % ({plist(c2048)} per pass, t {c2048['t_ttft']:+.1f}): the AMX build faster in all three passes, by a varying margin. At 1536 the mean is {c1536['ttft_pct']:+.1f} % ({plist(c1536)}, t {c1536['t_ttft']:+.1f}) and at 3000 {c3000['ttft_pct']:+.1f} % ({plist(c3000)}, t {c3000['t_ttft']:+.1f}). Neither is resolved. In the cold cells the AMX build is faster in every run: {c1024['ttft_pct']:+.1f} % at 1024 (n = 3, t {c1024['t_ttft']:+.1f}), {c4c['ttft_pct']:+.1f} % at 4096 and {c8c['ttft_pct']:+.1f} % at 8192 (n = 2 each). At prompt 1024 the pairs of the earlier campaigns read {min(pe_t):+.1f} % to {max(pe_t):+.1f} % (n = 1 to 6), and at tp4 the AVX build was faster in both pairs (+1.6 %, resolved in runtron with Welch t +3.7). So at 1024 the sign depends on the campaign and on tp. The cause of the warm gain is not settled (section 5). At 4096 to 6144 it co-occurs in every pass with the card\\'s K/V space running out, which moved {min(ex_share):.0f} to {max(ex_share):.0f} % of those cells\\' shard placements to the CPU (est.), where the AMX kernel replaces the AVX loop. That is a measured co-occurrence, not a measured cause. The gain also appears where nothing fell back: at 2048 ({c2048['ttft_pct']:+.1f} %, 0 warnings in all 6 pass-cells) and at 7168 ({plist(c7168)} in the three pairs, 0 warnings in {sum(1 for x in l71 if x == 0)} of the 6 pass-cells).</p>")
    H.append(f"<p><b>Decode: no at prompt 1024 and in cold cells. Not resolved in warm long-prompt cells.</b> At prompt 1024 the two builds differ by at most 2 % in every pair ({min(pe_p):+.1f} % to {max(pe_p):+.1f} % in the earlier campaigns, {plist(c1024, 'tps_pcts')} in this campaign\\'s three cold runs). In the cold cells at 4096 and 8192 the difference is {pc_lo:+.1f} to {pc_hi:+.1f} % (n = 2 each). In the warm cells from 4096 up the means favour the AMX build by {pl_lo:+.1f} to {pl_hi:+.1f} % TPS. The per-pass deltas, however, run from {pla_lo:+.1f} to {pla_hi:+.1f} % and change sign inside {len(sign_mixed)} of the 5 cells ({', '.join(str(p) for p in sign_mixed)}). So the warm decode direction is not resolved with three passes. The warm TPS itself lies {abs(wc_hi):.0f} to {abs(wc_lo):.0f} % below the cold TPS at the same prompt length. The VNNI-K build is the opposite case: it decodes 4 to 13 % slower under FPGA attention (issue 4500, the GitHub issue on the VNNI-K decode loss under FPGA attention).</p></div>")
    H.append(f'<div class="fig">{FS.fig_amx_vs_avx(cells)}<p class="cap">Figure 4. AMX build minus AVX build, both with FPGA attention, as a percentage of the AVX build. Rows above the horizontal line are this campaign\'s cells (fpgacanon = the canonical AMX deb with FPGA attention, against fpgabase = the nightly deb with FPGA attention, paired by pass number: 3 passes for warm cells, 3 runs at 1024 and 2 runs at 4096 and 8192 for cold cells). The dot is the mean of the per-pass deltas, the pale bar their range. Rows below the line are the prompt-1024 pairs of earlier campaigns: the whole-machine CI cells of 2026-09-18 (canon-ci against the same-night nightly) and the runtron cells of 2026-09-16 (n = 6 each). Exact values in the tables below.</p></div>')
    H.append("<ul>")
    H.append(f"<li><b>Prefill, warm cells.</b> {lst(warm, 'ttft_pct', '+.1f')} (means of the per-pass deltas). From 4096 up every one of the {n_pairs_long} paired passes favours the AMX build. At 2048 and 1536 all three passes favour it, by margins from {abs(max(c2048['ttft_pcts'] + c1536['ttft_pcts'])):.0f} to {abs(min(c2048['ttft_pcts'] + c1536['ttft_pcts'])):.0f} %. At 3000 the sign changes between passes ({plist(c3000)}).</li>")
    H.append(f"<li><b>Prefill, cold cells.</b> {lst(cold, 'ttft_pct', '+.1f')} (n = 3 at 1024, n = 2 at 4096 and 8192, the AMX build faster in every run). The AVX-side 1024 value ({c1024['ttft_avx']:,.0f} ms, three runs within 2 ms) is 25 to 45 ms above that cell\\'s history (section 5). Prompt-1024 pairs from the earlier campaigns: {', '.join(f'{v:+.1f} %' for v in pe_t)}.</li>")
    dec_list = ", ".join(f"{c['prompt']} {c['kind']}: {c['tps_pct']:+.1f} %" for c in cells)
    H.append(f"<li><b>Decode, all cells.</b> {dec_list} (means of the per-pass deltas; per-pass values in the table). Prompt-1024 pairs from the earlier campaigns: {', '.join(f'{v:+.1f} %' for v in pe_p)}.</li>")
    H.append(f"<li><b>Reading.</b> The warm cells at 4096 to 6144 ran with the card\\'s K/V space exhausted in every pass (section 5). tron logged {min(ex_lose)} to {max(ex_lose)} \\\"lose HW attention\\\" warnings per pass-cell there (one per shard per engine, HW = the FPGA), and the recorded fallback counter agrees with those counts. The affected shards were scored on the CPU for both prefill and decode. On the CPU the AMX kernel replaces the AVX loop. So in those three cells the AMX build\\'s gains ({abs(ex_t_hi):.0f} to {abs(ex_t_lo):.0f} % lower TTFT, {ex_p_lo:+.0f} to {ex_p_hi:+.0f} % TPS on average) include AMX against AVX on the share of attention that moved to the CPU. That share is not a gain of the FPGA path itself. The gains at 2048 ({c2048['ttft_pct']:+.1f} %, 0 warnings in all 6 pass-cells) and at 7168 ({c7168['ttft_pct']:+.1f} %, 0 warnings in {sum(1 for x in l71 if x == 0)} of 6 pass-cells) are not explained by fallback (hypothesis in section 5: cached-prefix pages scored on the CPU). At 8192 the two arms also differ in how much fell back ({', '.join(str(x) for x in lose_list('fpgabase', 8192))} warnings per pass in the AVX arm against {', '.join(str(x) for x in lose_list('fpgacanon', 8192))} in the AMX arm). That difference adds noise to the 8192 comparison. In the cold cells (no warning) the card holds every shard. The CPU keeps only the own-chunk triangle (each query\\'s own 128-token chunk, section 4). The CPU build then lowers TTFT by {abs(tc_hi):.0f} to {abs(tc_lo):.0f} % and changes TPS by at most {max(abs(v) for c in cold for v in c['tps_pcts']):.1f} %. Under FPGA attention the warm decode is {abs(wc_hi):.0f} to {abs(wc_lo):.0f} % slower than the cold decode at the same prompt length. Hypothesis: the fallback to CPU attention causes part of that loss. Test: a perfetto trace of one warm 2048 request, AMX build against kill switch.</li>")
    H.append("</ul>")
    H.append("<h3>The record</h3>")
    H.append(FS.table_amx_vs_avx(cells))
    H.append('<p class="cap">Top: this campaign\'s cells (client-side TTFT and decode TPS per user, harness means over 8 users x 10 rounds per pass; mean and sd over the passes per arm; the change columns are the mean of the per-pass deltas and the per-pass deltas themselves; Welch t over the pass means of the two arms). Middle: canonical-AMX against AVX pairs at prompt 1024 with FPGA attention on both sides (this campaign\'s cold cells included as one row with their three-run means). Bottom: the VNNI-K deb against the AVX deb at prompt 1024, where the decode loss of issue 4500 shows. Sources are in the source column and in section 8 (Data files).</p>')
    return H


'''
s = s[:a] + new6 + s[b:]

# ---- Short version sentence 3
rep("""Under FPGA attention the AMX build lowers the warm TTFT by 22 to 47 % from prompt 2048 up (one pass each, cause not settled: the card\\'s K/V space ran out in the 4096 to 6144 cells, but the gain also appears where it did not), and at prompt 1024 and in cold cells the two builds are within 7 % on TTFT and 2 % on decode (section 6).""",
    """Under FPGA attention the AMX build lowers the warm TTFT by 33 to 49 % from prompt 4096 up in every one of three passes (cause not settled: the card\\'s K/V space ran out in the 4096 to 6144 cells of every pass, but the gain also appears at 2048 and 7168 where it did not), and at prompt 1024 and in cold cells the two builds are within 8 % on TTFT and 2 % on decode (section 6).""")
# ---- section 3 and 8 sentences
rep("At longer prompts with a warm prefix cache the AMX build changes it by 22 to 47 % (section 6). The cause of that warm gain is not settled (section 5 names two candidate mechanisms).",
    "At longer prompts with a warm prefix cache the AMX build lowers it by 33 to 49 % from 4096 up (means over three passes, section 6). The cause of that warm gain is not settled (section 5 names two candidate mechanisms).")
rep("section 6 shows 22 to 47 % in warm cells at longer prompts, one pass each, with the two candidate causes in section 5)",
    "section 6 shows 33 to 49 % in warm cells from 4096 up, three passes each, with the two candidate causes in section 5)")
rep("FPGA-attention cells above prompt 1024 (sections 5 and 6) are one pass per arm so far. Their warm values depend",
    "FPGA-attention cells above prompt 1024 (sections 5 and 6) are three passes per arm, run on 2026-09-21 evening and 2026-09-22 afternoon (UTC), with pass-to-pass sd of 16 to 128 ms below 4096 and 118 to 793 ms from 4096 up. Their warm values depend")
# ---- section 7 bullets
rep("Cold cells = single-cell driver runs at 4096 and 8192 for both FPGA arms.</li>",
    "Cold cells = single-cell driver runs at 4096 and 8192 for both FPGA arms, two per arm and length.</li>")
a = s.index('    H.append("<li>Remaining: passes 2 and 3 of the two FPGA arms')
b = s.index("\n", a) + 1
s = s[:a] + '''    H.append("<li>Done after the 2026-09-22 nightly (13:20 to 16:25 UTC): passes 2 and 3 of the two FPGA arms and a second cold cell per arm at 4096 and 8192, with the card allocator free space and the software-fallback count recorded per cell (they confirm the exhaustion reading, section 5). Running: the runtron campaign exec/q4b-rt8u-20260922/ (8 users on one engine on our half, prompts 1024 to 8192, plus 2 users at 4096 and 8192, both attention modes and both builds, 3 repetitions, started 2026-09-22 16:58 UTC; its results go into a new section). Not measured and not planned: a cold CPU-attention cell at 4096, a cold AVX cell at 8192, and the VNNI-K deb under FPGA attention at long prompts (optional arm fpgavnnik).</li>")
''' + s[b:]
a = s.index('    H.append("<li>Noise: with one pass per FPGA arm no run-to-run sd exists yet')
b = s.index("\n", a) + 1
s = s[:a] + '''    H.append(f"<li>Noise: three passes per FPGA arm. The pass-to-pass sd of the warm TTFT is 16 to 128 ms below 4096 and 118 to 793 ms from 4096 up (the AVX arm is the noisier one from 4096 up, sd 282 to 793 ms against 118 to 411 ms). The two cold runs of one arm at one length agree within 1 to 29 ms. The CPU series' 3-pass sd was 1 to 25 ms at 1024 and 350 to 1230 ms at 8192.</li>")
''' + s[b:]
open(P, "w").write(s)
print("gen_page patched", len(s))
