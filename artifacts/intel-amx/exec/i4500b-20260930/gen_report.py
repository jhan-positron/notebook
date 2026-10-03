#!/usr/bin/env python3
"""Build VNNIed-K-in-place/issue4500/policy-4500.html from the i4500b-20260930 results: the rinzler cells
(summary.json + the per-cell perf-e0.json for TTFT), the smoke token rows, the unit tests, the decode traces
(traces/analysis.md) and, when present, the perf reports of exec/results/i4500c-20260930.
Light theme, ASCII only, inline SVG dumbbell charts (one row per cell, one dot per arm, values in a column).
Usage: gen_report.py [RES_DIR] [OUT_HTML]"""
import glob, html, json, math, os, re, statistics, sys
RES = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/exec/results/i4500b-20260930"
RESC = "/home/jhan/workspace/intel-AMX/exec/results/i4500c-20260930"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4500/policy-4500.html"
ARMS = [("base", "canonical AMX (main 3faba6d0fd, row-major K)", "#2a78d6"), ("fix", "the 09-29 fix (row-major tail block, converted at the forward end)", "#eb6834"),
        ("fixS1", "the fix + the policy (decode blocks stay row-major under FPGA attention)", "#1f9d55"),
        ("basekill", "base with TRON_AMX_DISABLE=1", "#9bbde8"), ("fixS1kill", "fixS1 with TRON_AMX_DISABLE=1", "#8fd1a8")]
def esc(x): return html.escape(str(x))
def T(n): return {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78}.get(n, 2.0)
summary = json.load(open(os.path.join(RES, "summary.json")))
cells, pairs = summary["cells"], summary["pairs"]
groups = {}
for key, reps in cells.items():
    model, tp, users, prompt, arm = key.split("__")
    g = groups.setdefault((model, int(tp), int(users), int(prompt)), {})
    tps = {int(r): v["tps"] for r, v in reps.items()}
    ttft = {int(r): v["ttft"] for r, v in reps.items()}
    g[arm] = {"tps": tps, "ttft": ttft, "mean": statistics.mean(tps.values()), "n": len(tps), "min": min(tps.values()), "max": max(tps.values()),
              "sd": statistics.stdev(tps.values()) if len(tps) > 1 else 0.0, "ttft_mean": statistics.mean(ttft.values()), "amx": [v.get("amx") for v in reps.values()]}
def paired(g, a, b, metric):
    if a not in g or b not in g: return None
    common = sorted(set(g[a][metric]) & set(g[b][metric]))
    if len(common) < 2: return None
    if metric == "tps":
        d = [1000 / g[a][metric][r] - 1000 / g[b][metric][r] for r in common]
    else:
        d = [g[a][metric][r] - g[b][metric][r] for r in common]
    m = statistics.mean(d); sd = statistics.stdev(d); t = m / (sd / math.sqrt(len(d))) if sd else float("inf")
    pct = 100 * (statistics.mean(g[a][metric][r] for r in common) / statistics.mean(g[b][metric][r] for r in common) - 1)
    return {"n": len(d), "mean": m, "sd": sd, "t": t, "pct": pct, "resolved": abs(t) >= T(len(d))}
def cell_label(model, tp, users, prompt):
    name = {"qwen3-4b": "qwen-3-4b", "llama-8b": "llama-3.1-8b"}.get(model, model)
    attn = "FPGA attention" if model.startswith("qwen") else "CPU attention"
    return f"{name} tp{tp}, {users} users per engine, prompt {prompt} ({attn})"
def chart(metric, title, unit, better):
    rows = sorted(groups); arms = [a for a in ("base", "fix", "fixS1") ]
    W, LEFT, RIGHT, RH, TOP = 1240, 470, 300, 92, 44
    H = TOP + RH * len(rows) + 50
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font-family:system-ui,sans-serif;font-size:13px" role="img" aria-label="{esc(title)}">',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>']
    for i, key in enumerate(rows):
        g = groups[key]; y = TOP + i * RH + RH / 2
        present = [(a, g[a]) for a in arms if a in g]
        vals = [g[a]["mean" if metric == "tps" else "ttft_mean"] for a, _ in present]
        lo, hi = min(vals), max(vals); span = max(hi - lo, (0.02 * hi)); lo -= span * 0.6; hi += span * 0.6
        def x(v): return LEFT + (v - lo) / (hi - lo) * (W - LEFT - RIGHT)
        out.append(f'<line x1="{LEFT}" y1="{y + 22}" x2="{W - RIGHT}" y2="{y + 22}" stroke="#ddd"/>')
        for tick in (lo + (hi - lo) * f for f in (0.0, 0.5, 1.0)):
            out.append(f'<text x="{x(tick):.1f}" y="{y + 36}" text-anchor="middle" fill="#888" font-size="11">{tick:.0f}</text>')
        out.append(f'<text x="{LEFT - 12}" y="{y - 8}" text-anchor="end" fill="#222">{esc(cell_label(*key))}</text>')
        xs = [x(v) for v in vals]
        out.append(f'<line x1="{min(xs):.1f}" y1="{y:.1f}" x2="{max(xs):.1f}" y2="{y:.1f}" stroke="#bbb" stroke-width="3"/>')
        for (a, v), xv in zip(present, xs):
            col = next(c for aa, _, c in ARMS if aa == a)
            out.append(f'<circle cx="{xv:.1f}" cy="{y:.1f}" r="7" fill="{col}"/>')
        for k, ((a, v), val) in enumerate(zip(present, vals)):
            col = next(c for aa, _, c in ARMS if aa == a)
            out.append(f'<text x="{W - RIGHT + 16}" y="{y - 22 + 17 * k:.0f}" fill="{col}">{a} {val:.1f} {unit} (n = {v["n"]})</text>')
        p = paired(g, "fixS1", "base", metric)
        if p:
            txt = f'fixS1 vs base: {p["pct"]:+.1f} % ({p["mean"]:+.3f} ms{" per step" if metric == "tps" else ""}, paired t {p["t"]:+.1f}, {"resolved" if p["resolved"] else "n.r."})'
            out.append(f'<text x="{LEFT - 12}" y="{y + 12}" text-anchor="end" fill="#1f9d55">{esc(txt)}</text>')
    lx = 40
    for a, label, col in ARMS[:3]:
        out.append(f'<circle cx="{lx + 6}" cy="{TOP - 28}" r="6" fill="{col}"/><text x="{lx + 16}" y="{TOP - 24}" fill="#333">{a}</text>')
        lx += 90
    out.append(f'<text x="{lx + 10}" y="{TOP - 24}" fill="#666">{esc(title)}: {esc(better)}; each row has its own axis</text>')
    out.append("</svg>")
    return "\n".join(out)
def cells_table():
    h = ["<table><tr><th>cell</th><th>arm</th><th>n</th><th>TPS mean</th><th>sd</th><th>min / max</th><th>step ms</th><th>TTFT ms mean</th><th>AMX-busy cycles per rep (20 s)</th></tr>"]
    for key in sorted(groups):
        g = groups[key]
        for a, label, _ in ARMS:
            if a not in g: continue
            v = g[a]
            h.append(f"<tr><td>{esc(cell_label(*key))}</td><td>{a}</td><td>{v['n']}</td><td>{v['mean']:.2f}</td><td>{v['sd']:.2f}</td><td>{v['min']:.2f} / {v['max']:.2f}</td><td>{1000 / v['mean']:.3f}</td><td>{v['ttft_mean']:.0f}</td><td>{esc('/'.join(str(x) for x in v['amx']))}</td></tr>")
    h.append("</table>")
    return "\n".join(h)
PAIRS = [("fixS1", "base"), ("fix", "base"), ("fixS1", "fix"), ("basekill", "base"), ("fixS1kill", "fixS1")]
def pairs_table(metric):
    unit = "ms per step (a minus b)" if metric == "tps" else "ms TTFT (a minus b)"
    h = [f"<table><tr><th>cell</th><th>a</th><th>b</th><th>n</th><th>{unit}</th><th>%</th><th>paired t</th><th>resolved</th></tr>"]
    for key in sorted(groups):
        g = groups[key]
        for a, b in PAIRS:
            p = paired(g, a, b, metric)
            if not p: continue
            h.append(f"<tr><td>{esc(cell_label(*key))}</td><td>{a}</td><td>{b}</td><td>{p['n']}</td><td>{p['mean']:+.3f} (sd {p['sd']:.3f})</td><td>{p['pct']:+.2f}</td><td>{p['t']:+.2f}</td><td>{'yes' if p['resolved'] else 'no'}</td></tr>")
    h.append("</table>")
    return "\n".join(h)
def pre(path, n=60, grep=None):
    if not os.path.exists(path): return "<p>(not available)</p>"
    lines = open(path, errors="replace").read().splitlines()
    if grep: lines = [l for l in lines if re.search(grep, l)]
    return "<pre>" + esc("\n".join(lines[-n:])) + "</pre>"
def trace_table():
    p = os.path.join(RES, "traces", "analysis.md")
    if not os.path.exists(p): return "<p>(no trace analysis)</p>"
    rows = [l for l in open(p) if "| all |" in l]
    h = ["<table><tr><th>trace (arm, cell)</th><th>decode passes</th><th>pass ms</th><th>Save K on main, us per pass</th><th>Save V</th><th>last Save V end to pass end, us</th><th>Pending max per worker, us</th><th>hw wait max, us</th></tr>"]
    for l in rows:
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        h.append(f"<tr><td>{esc(c[0].replace('.perfetto-trace', '').replace('__', ' '))}</td><td>{c[1]}</td><td>{c[3]}</td><td>{c[4]}</td><td>{c[5]}</td><td>{c[6]}</td><td>{c[12]}</td><td>{c[14]}</td></tr>")
    h.append("</table>")
    return "\n".join(h)
def requirement_table():
    h = ["<table><tr><th>cell</th><th>TPS fixS1 vs canonical</th><th>TTFT fixS1 vs canonical</th><th>verdict</th></tr>"]
    for key in sorted(groups):
        g = groups[key]; pt = paired(g, "fixS1", "base", "tps"); pf = paired(g, "fixS1", "base", "ttft")
        def word(p, better_sign):
            if not p: return "-"
            s = f"{p['pct']:+.2f} % (t {p['t']:+.1f}, {'resolved' if p['resolved'] else 'n.r.'})"
            if not p["resolved"]: return s + " = not worse (within noise)"
            return s + (" = better" if (p["pct"] * better_sign) > 0 else " = worse")
        tw, fw = word(pt, +1), word(pf, -1)
        bad = [w for w in (tw, fw) if "= worse" in w]
        if bad and pf and "= worse" in fw and abs(pf["pct"]) < 0.5:
            verdict = f"TPS better; TTFT resolved but {pf['pct']:+.2f} % ({pf['mean']:+.0f} ms of {g['base']['ttft_mean'] / 1000:.1f} s): the strict reading is not met, the size is jhan's call"
        elif bad: verdict = "NOT met"
        elif "better" in tw or "better" in fw: verdict = "met"
        else: verdict = "not worse on both (neither resolved)"
        h.append(f"<tr><td>{esc(cell_label(*key))}</td><td>{esc(tw)}</td><td>{esc(fw)}</td><td>{esc(verdict)}</td></tr>")
    h.append("</table>")
    return "\n".join(h)
manifest = json.load(open("/var/tmp/jhan/i4500b-20260930/manifest.json")) if os.path.exists("/var/tmp/jhan/i4500b-20260930/manifest.json") else {}
perf_note = ""
if os.path.exists(os.path.join(RESC, "perf", "perf.done")):
    perf_note = f"<p>Perf block (exec/i4500c-20260930, runtron tp2 with 2 users, 6 s of decode, 391 k samples per binary): {esc(open(os.path.join(RESC, 'perf', 'perf.done')).read().strip())}. Finding: the K store symbols of the model thread are equally small in both builds (about 0.03 % of all samples each), but the policy build spends 0.91 % of all samples in latch_ref::count_down, absent from the canonical profile (below 0.015 %). That is the release of the K/V latch at the end of Save K and Save V (model.hpp save_k_impl and save_v_impl; the attention workers wait on it with mwaitx in run_attention_job). The 0.91 % of all samples is about 47 us per 5 ms pass, the size of the Save K gap. Reading: the policy build's workers reach that wait earlier (their Ready sections are shorter: 141 vs 171 us per worker per pass in the traces), so more cores are parked on the latch line when the main thread releases it, and the release itself pays. It is a wake-up cost of the many-waiter latch, not a cost of the K store; it applies to any build whose workers arrive early. A remedy (a release that does not wake every core at once, or per-worker latch lines) is a separate change to the threading code.</p>"
    for arm in ("base", "fixS1"):
        rp = os.path.join(RESC, "perf", arm, "report-main.txt")
        if os.path.exists(rp): perf_note += f"<p>{arm}, main thread, top symbols (self time):</p>" + pre(rp, 40)
else:
    perf_note = "<p>The perf block of exec/i4500c-20260930 (perf record of both runtron binaries in decode, to attribute the Save K gap by symbol) had not finished when this page was generated.</p>"
G2 = groups.get(("qwen3-4b", 2, 2, 1024), {}); G4 = groups.get(("qwen3-4b", 4, 4, 1024), {}); GL = groups.get(("llama-8b", 2, 8, 4096), {})
def pv(g, a, b, m):
    p = paired(g, a, b, m); return "n/a" if not p else f"{p['pct']:+.1f} % (t {p['t']:+.1f}, n = {p['n']}, {'resolved' if p['resolved'] else 'n.r.'})"
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Issue 4500 policy results</title>
<style>:root{{color-scheme:light}}body{{background:#fff;color:#222;font-family:system-ui,sans-serif;max-width:1060px;margin:24px auto;padding:0 16px;line-height:1.45}}
table{{border-collapse:collapse;font-size:14px}}th,td{{border:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}}th{{background:#f4f4f4}}pre{{background:#f6f6f6;padding:8px;overflow-x:auto;font-size:12px}}h2{{margin-top:32px}}.short{{background:#eef6ff;padding:10px 14px;border-left:4px solid #2a78d6}}.note{{background:#fff8e6;padding:8px 12px;border-left:4px solid #e0a800}}</style></head><body>
<h1>Issue #4500, round 2: decode blocks stay row-major under FPGA attention (measured 2026-09-30)</h1>
<p class="short"><b>Short version.</b> The remaining qwen-3-4b decode loss of the VNNI K layout under FPGA attention came from work the card never benefits from: the forward-end conversion of every completed K block (serial on the main thread, every 16th step, for every layer and KV head) and a still slower per-row K save. Commit 452b2052c9 (branch jhan-amx-vnniK-i4500) stops that conversion for the KV slots the FPGA scores. Measured on delphi-3bda with the nightly's own client, the policy build (fixS1) is at TPS {pv(G2, 'fixS1', 'base', 'tps')} at tp2 with 2 users and {pv(G4, 'fixS1', 'base', 'tps')} at tp4 with 4 users against the canonical AMX build, with TTFT {pv(G2, 'fixS1', 'base', 'ttft')} and {pv(G4, 'fixS1', 'base', 'ttft')}; llama-3.1-8b keeps its gain ({pv(GL, 'fixS1', 'base', 'tps')} TPS) with TTFT {pv(GL, 'fixS1', 'base', 'ttft')}: a resolved 46 ms on 13.4 s, the same size the PR head showed on 09-29, so a property of the VNNI prefill store in the hand-written llama plugin, not of this commit. Generated tokens are identical to the 09-29 fix build in all four smoke cells.</p>
<p>Words used here: tron = the inference program under test; rinzler = the production server; runtron = tron's command-line tool; VNNI K = the K cache layout of PR #4424 (K stored as the AMX B operand); AMX = Intel's matrix instructions; canonical AMX = main 3faba6d0fd with the AMX kernels on and row-major K (the "base" arm); the fix = the 09-29 row-major 16-token tail block (f34b0fe2ec, deb 98a5accb8b); the policy = commit 452b2052c9 (deb 2fd11e32ca), the "fixS1" arm; FPGA attention = the Positron card scores the keys the CPU staged to it (GOF = a group of four tokens copied to the card by DMA), the CPU scores only the tail above the last complete GOF; kill switch = TRON_AMX_DISABLE=1 (no AMX tile bracket, no Q packing, no dense kernel); TPS = decode tokens per second per user, captured between generated tokens 896 and 1024 of 1536 over 10 rounds; TTFT = time to first token (ms); paired t = mean of the per-repetition differences over its standard error (resolved at |t| &gt;= 4.30 for n = 3, 3.18 for n = 4; "n.r." = not resolved); AMX-busy = cycles of the EXE.AMX_BUSY counter on the engine during 20 s.</p>

<h2>1. The requirement</h2>
<p>jhan (2026-09-30): the VNNI K layout must deliver better TPS and TTFT than canonical AMX on llama-8b tp2 and qwen3-4b tp2 and tp4; failing both, one better and the other not worse.</p>
{requirement_table()}
<p>"Not worse (within noise)" = the paired difference is not resolved at the repetitions run; "better" / "worse" = resolved. The cells are the nightly's loads: qwen-3-4b tp2 with 2 users per engine and tp4 with 4 users at prompt 1024 (FPGA attention), llama-3.1-8b tp2 with 8 users at prompt 4096 (CPU attention).</p>

<h2>2. What the code reading found (why the 09-29 fix left a loss)</h2>
<p>A 25-agent code reading with adversarial verification (session b0cfc925, 2026-09-30) established, with file:line evidence at 452b2052c9 and main 3faba6d0fd:</p>
<ul>
<li>Under FPGA attention, keys the card covers cost the CPU no K bytes: a page the hardware covers takes the software loop, which jumps over the hardware range. The CPU scores only the tail above the last DMA-complete GOF (measured 2.5 tokens per job at prompt 1024 with the PR 4596 counters). The 09-29 report's lead, "positions 64..126 are scored by the CPU every step", is refuted: the engagement point (127) gates query positions and the first shard's DMA prefix, never key positions.</li>
<li>The dense AMX page kernel never runs in steady-state FPGA decode at prompt 1024, and ran 0 times in the prefill of that prompt length. So the VNNI layout brings the FPGA-attention decode nothing; it can only cost.</li>
<li>What the fix build still did per step that canonical does not: (a) at the forward end, on the main thread, convert every 16-token block that decode completed, for every layer and KV head (36 x 8 blocks per user every 16th step; 8 KiB of plane traffic plus an 8 KiB stack round trip each); (b) a 64-line gather in the staging whenever a converted block is copied to the card again; (c) row bookkeeping in the K save.</li>
<li>Trap found: main 3faba6d0fd carries PR #4191 (workless-range dismissal), which the PR branch lacks. The rinzler packages of every arm contain main 3faba6d0fd, so the cells compare like with like; the runtron trace comparison uses main c7844ca2ce (the branch's merge base) as its base for the same reason.</li>
</ul>

<h2>3. What the policy commit does</h2>
<p>When the hardware attention scores an operation's K (cached_operation_uses_hw, decided once per model), save_k records no row bits for the rows a short run stores and queues no block for the forward-end conversion. Such a block stays row-major, and a page copy does not convert it either. Whole-block saves (prefill) still store the VNNI layout at once, so the prefill path and its TTFT gain are untouched. The FPGA staging reads a row of a row-major block in place instead of copying it; k_forget_row skips its two locked read-modify-writes on a plain decode append. convert_pending_k_blocks gets a trace span. Note [Row-major blocks under hardware attention] in kv_cache.hpp carries the design. Two adversarial review passes (60 and 18 agents) found no blocker; their wording and test findings are applied.</p>
<p class="note">Accepted limitation (documented in the Note): the policy is static per operation. A range the software scores although the operation is a hardware one (before the engagement point, a prompt shorter than 128 tokens, a shard without HBM, USE_HW_ATTN=N raising the engagement point) scores the blocks decode completed with the row-major dotter, where the 09-29 fix let the AMX kernel score a page of them. Tokens are identical either way, because every reader takes the layout from the block bit.</p>

<h2>4. Decode TPS, four repetitions, arms interleaved</h2>
{chart("tps", "decode TPS per user", "TPS", "higher is better")}
<h2>5. TTFT</h2>
{chart("ttft", "time to first token", "ms", "lower is better")}
<p>TTFT of the nightly client is the mean over the 10 rounds' first tokens; its run-to-run spread today (sd 16 to 32 ms per pair) is larger than on 09-29 (2 to 7 ms), so the tp2 TTFT pair is not resolved and the tp4 pair sits at the threshold.</p>

<h2>6. Cells</h2>
{cells_table()}
<h2>7. Paired differences, TPS</h2>
{pairs_table("tps")}
<h2>8. Paired differences, TTFT</h2>
{pairs_table("ttft")}
<p>The kill-switch arms (tp4 only): they say how much the per-section AMX tile-configuration bracket and Q packing cost when no dense page is scored. Both arms are inside the tp4 spread.</p>

<h2>9. Decode traces (runtron, 2 users at tp2 and 4 users at tp4, 38 decode passes each)</h2>
<p>Perfetto traces of three runtron binaries that share the merge base c7844ca2ce (base = main c7844ca2ce, fix = f34b0fe2ec, fixS1 = 452b2052c9); tracing itself costs about 9 % of a step, so compare the arms with each other, not with the cells. The fix's conversion burst is visible at decode passes 14 and 30 (every 16th step): the gap from the last Save V to the pass end rises from about 450 to 1130 us at tp2 and from about 1000 to 3800 us at tp4 in the fix trace, and stays flat in the fixS1 trace. The main thread's Save K span stays about twice the canonical build's in both VNNI builds (below).</p>
{trace_table()}
<p>Open: the Save K gap. A store rewrite (commit 0bb74c2ab0, dropped) assumed a two-pass conversion; review showed the production K buffer is bf16, so the old path was one memcpy already. Candidates left: the per-run cut loop, the per-row page-state reads, the 4 KiB stack array, and the panel placement of the rows. {perf_note}</p>

<h2>10. Token smoke (runtron, one user, temperature 0, pay-for-determinism)</h2>
<p>fixS1 vs fixS12 (the same binary twice) and fixS1 vs fix must both be identical: under FPGA attention the same K bytes reach the card and the CPU scores the same row-major tail; under CPU attention the policy is off.</p>
{pre(os.path.join(RES, "smoke", "smoke.txt"), 12)}
<h2>11. Unit tests (fake device)</h2>
<p>VNNI build (TRON_K_VNNI on) at 452b2052c9:</p>{pre(os.path.join(RES, "tests-fixS1.txt"))}
<p>Row-major build (TRON_K_VNNI off):</p>{pre(os.path.join(RES, "tests-fixS1rm.txt"))}
<h2>12. Binaries and data</h2>
<pre>{esc(json.dumps(manifest, indent=1))}</pre>
<p>Arms: base = /var/tmp/jhan/canon-ci-20260918/root (main 3faba6d0fd + AMX in the deb preset); fix = /var/tmp/jhan/i4500fix-20260928/root (deb 98a5accb8b, measured on 09-29); fixS1 = /var/tmp/jhan/i4500b-20260930/root (deb 2fd11e32ca = the fix deb line + 452b2052c9). Results: exec/results/i4500b-20260930/ (cells/, smoke/, traces/, tests-*); scripts exec/i4500b-20260930/ (README.md); logs exec/logs/i4500b-20260930*.log. The branch is local (not pushed); PR #4424 is untouched.</p>
<h2>13. Open items</h2>
<ul>
<li>The Save K gap (section 9): about 0.9 % of a tp2 step, serial on the main thread under the late launch; the perf block attributes it by symbol.</li>
<li>The static policy (section 3): a per-range or lazy conversion would recover the AMX kernel in the software-fallback states; not needed for the nightly cells.</li>
<li>Rebase the branch onto main past PR #4191 before the PR update; the deb packages already contain it.</li>
<li>Tests: no unit test instantiates store_k_block with a bf16 K buffer (production), and the "row re-saved into a converted block" arm is untested through store_k_block (review findings, not blockers).</li>
<li>llama-8b TTFT: +46 ms on 13.4 s (+0.34 %, resolved at n = 4; +47 ms with the 09-29 fix, +23 ms with the PR head on 09-29). Candidate: the whole-block VNNI store (16 rows transposed in registers) runs on the main thread alone in the hand-written llama plugin (no shared block save there), where the canonical store is a memcpy per row. Measure: Save K spans of a llama prefill trace, base vs fixS1.</li>
<li>Separate lever, not part of the PR: TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 (early card launch at 2 users) gave +7.7 % TPS on canonical and +11 % on the VNNI build at tp2 on 09-19; a product default change to discuss on its own.</li>
</ul>
</body></html>"""
os.makedirs(os.path.dirname(OUT), exist_ok=True)
assert all(ord(ch) < 128 for ch in page), "non-ASCII in page"
open(OUT, "w").write(page)
print("wrote", OUT, "cells:", len(cells), "pairs:", len(pairs))
