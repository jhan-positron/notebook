#!/usr/bin/env python3
"""Generate VNNIed-K-in-place/issue4500/root-cause-debug.html (pure ASCII, light theme, inline SVG).
Run: python3 exec/issue4500-20260918/gen_design.py [--with-results]
Reads (when present) exec/results/issue4500-20260918/{bench/bench.txt, summary.json, traces/analysis.json}.
"""
import json, os, re, statistics, sys, html as H

OUT = "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4500/root-cause-debug.html"
RES = "/home/jhan/workspace/intel-AMX/exec/results/issue4500-20260918"
INK, INK2, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"
GRAY = "#8a8987"


def esc(s):
    return H.escape(s, quote=True)


# ------------------------------------------------------------------ data: the budget
BUDGET = [  # config, base TPS, target TPS, rows per layer, users per engine, launch phase, source
    ("runtron tp2, 8 users, 1 engine", 125.41, 122.61, 64, 8, "early", "wedperf-attr block D, n=6, t -6.5"),
    ("runtron tp4, 8 users, 1 engine", 129.65, 117.12, 64, 8, "early", "wedperf-attr block D, n=6, t -2.9"),
    ("CI layout tp2, 2 users per engine", 186.13, 176.75, 16, 2, "late", "ci-mimic 2026-09-18, 80 samples, Welch t -7.2"),
    ("CI layout tp4, 4 users per engine", 149.94, 133.44, 32, 4, "early", "ci-mimic 2026-09-18, 80 samples, Welch t -17.4"),
]
LAYERS = 36
STORE_DELTA_NS = 350.0   # micro-benchmark: VNNI scatter minus row-major store, ns per row (measured 2026-09-18, see section 6)


def budget_rows():
    rows = []
    for name, b, t, rpl, users, phase, src in BUDGET:
        sb, st = 1000.0 / b, 1000.0 / t
        d = st - sb
        rows.append({"name": name, "base": b, "target": t, "step_b": sb, "step_t": st, "delta_ms": d, "pct": 100 * (t / b - 1),
                     "us_layer": d * 1000 / LAYERS, "ns_row": d * 1e6 / LAYERS / rpl, "rows": rpl, "users": users, "phase": phase, "src": src,
                     "store_pred_ms": rpl * LAYERS * STORE_DELTA_NS / 1e6})
    return rows


# ------------------------------------------------------------------ micro-benchmark results
def bench_table():
    p = os.path.join(RES, "bench", "bench.txt")
    if not os.path.exists(p):
        return None
    t = open(p).read()
    import collections
    res = collections.defaultdict(list)
    for b in re.split(r"\n== ", t)[1:]:
        hdr = b.split("\n", 1)[0]
        m = re.match(r"rows=(\d+) layout=(\S+) (\S+) rep=(\d)", hdr)
        if not m:
            continue
        rows, layout, w = int(m[1]), m[2], m[3]
        m2 = re.search(r"layout=(\w+) rows", b)
        lay = m2.group(1) if m2 else layout
        for k in ("store_ns_per_row", "tail_score_ns_per_row", "stage_ns_per_row"):
            mm = re.search(k + r"=([0-9.]+)", b)
            if mm:
                res[(rows, lay, w, k)].append(float(mm.group(1)))
    return {k: statistics.median(v) for k, v in res.items()}


# ------------------------------------------------------------------ figure 1: the budget vs the store prediction
def fig_budget(rows):
    W, H_ = 1040, 372
    left, right, top, rowh = 300, 900, 60, 58
    xmax = 1.0
    X = lambda v: left + v / xmax * (right - left)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H_}" width="{W}" height="{H_}" role="img" aria-label="Per-step decode loss to explain per configuration, with the store cost predicted from the micro-benchmark" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, Segoe UI, sans-serif">',
         f'<rect x="0" y="0" width="{W}" height="{H_}" fill="{SURF}"/>',
         f'<text x="20" y="24" font-size="13" fill="{INK2}">Figure 1. The loss per decode step (measured) and the K-store cost predicted from the micro-benchmark (rows per step x 350 ns).</text>']
    for v in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        x = X(v)
        s.append(f'<line x1="{x:.1f}" y1="{top - 6}" x2="{x:.1f}" y2="{top + rowh * len(rows)}" stroke="{GRID if v else AXIS}" stroke-width="1"/>')
        s.append(f'<text x="{x:.1f}" y="{top + rowh * len(rows) + 16}" font-size="12" text-anchor="middle" fill="{INK2}">{v:.1f} ms</text>')
    s.append(f'<text x="{(left + right) / 2:.0f}" y="{top + rowh * len(rows) + 36}" font-size="12.5" text-anchor="middle" fill="{INK2}">milliseconds added to one decode step (target minus base)</text>')
    for i, r in enumerate(rows):
        cy = top + i * rowh + 14
        s.append(f'<text x="{left - 12}" y="{cy + 4}" font-size="13" font-weight="600" text-anchor="end" fill="{INK}">{esc(r["name"])}</text>')
        s.append(f'<text x="{left - 12}" y="{cy + 20}" font-size="11.5" text-anchor="end" fill="{INK2}">{r["rows"]} rows per layer, {r["phase"]} launch</text>')
        s.append(f'<rect x="{X(0):.1f}" y="{cy - 8}" width="{X(r["delta_ms"]) - X(0):.1f}" height="16" rx="3" fill="{BLUE}"><title>measured loss {r["delta_ms"]:.3f} ms per step</title></rect>')
        s.append(f'<text x="{X(r["delta_ms"]) + 6:.1f}" y="{cy + 4}" font-size="12" fill="{INK}">{r["delta_ms"]:+.3f} ms ({r["pct"]:+.1f}% TPS)</text>')
        xp = X(r["store_pred_ms"])
        s.append(f'<line x1="{xp:.1f}" y1="{cy - 14}" x2="{xp:.1f}" y2="{cy + 22}" stroke="{ORANGE}" stroke-width="3"/><title>store prediction {r["store_pred_ms"]:.2f} ms</title>')
        s.append(f'<text x="{xp:.1f}" y="{cy + 34}" font-size="11" text-anchor="middle" fill="{ORANGE}">store est. {r["store_pred_ms"]:.2f} ms</text>')
    s.append(f'<rect x="20" y="{H_ - 22}" width="14" height="10" fill="{BLUE}"/><text x="40" y="{H_ - 13}" font-size="12" fill="{INK}">measured loss per step</text>')
    s.append(f'<line x1="250" y1="{H_ - 24}" x2="250" y2="{H_ - 10}" stroke="{ORANGE}" stroke-width="3"/><text x="260" y="{H_ - 13}" font-size="12" fill="{INK}">main-thread K store cost, est. from the micro-benchmark (+350 ns per row, measured 2026-09-18)</text>')
    s.append("</svg>")
    return "\n".join(s)


# ------------------------------------------------------------------ figure 2: one layer of one decode step, lanes
def fig_lanes():
    # schematic lanes, durations NOT to scale; two panels: early launch (B >= 4) and late launch (B < 4)
    W, H_ = 1240, 600
    s = [f'<svg class="chart" viewBox="0 0 {W} {H_}" width="{W}" height="{H_}" role="img" aria-label="One layer of one FPGA-attention decode step: what the main thread, the attention workers and the FPGA do, for the early and the late launch phase, with the three VNNI-only costs marked" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, Segoe UI, sans-serif">',
         f'<rect x="0" y="0" width="{W}" height="{H_}" fill="{SURF}"/>',
         f'<defs><marker id="ah2" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8 z" fill="{INK2}"/></marker></defs>',
         f'<text x="20" y="22" font-size="13" fill="{INK2}">Figure 2. One layer of one decode step with FPGA attention (order verified in the generated qwen plugin). Boxes are steps in order, widths are NOT time. Orange = changed by VNNI.</text>']

    def panel(y0, title, order):
        for j, part in enumerate(title.split("|")):
            s.append(f'<text x="20" y="{y0 + j * 17}" font-size="13.5" font-weight="{600 if j == 0 else 400}" fill="{INK if j == 0 else INK2}">{esc(part)}</text>')
        y0 += 17
        lanes = ["main thread", "attention workers", "FPGA card"]
        for i, ln in enumerate(lanes):
            y = y0 + 16 + i * 62
            s.append(f'<text x="20" y="{y + 26}" font-size="12.5" fill="{INK2}">{ln}</text>')
            s.append(f'<line x1="150" y1="{y + 44}" x2="{W - 20}" y2="{y + 44}" stroke="{GRID}" stroke-width="1"/>')
        x = 150
        for lane, label, w0, kind in order:
            w = int(w0 * 0.82)
            y = y0 + 16 + lane * 62
            fill = {"plain": "#f3f2ef", "vnni": "#fbe3d8", "wait": SURF, "fpga": "#e3edf9"}[kind]
            stroke = {"plain": AXIS, "vnni": ORANGE, "wait": AXIS, "fpga": BLUE}[kind]
            dash = ' stroke-dasharray="5 4"' if kind == "wait" else ""
            s.append(f'<rect x="{x}" y="{y + 6}" width="{w}" height="38" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="{2 if kind == "vnni" else 1}"{dash}/>')
            for j, part in enumerate(label.split("|")):
                s.append(f'<text x="{x + w / 2:.0f}" y="{y + 22 + j * 14}" font-size="10.5" text-anchor="middle" fill="{INK}">{esc(part)}</text>')
            x += w + 6
    early = [(0, "rmsnorm|+ rope", 70, "plain"), (0, "WV matmul|launch", 70, "plain"), (0, "prepare|(barrier)", 66, "plain"),
             (2, "attention on|the card", 150, "fpga"), (0, "launch HW|attention", 78, "plain"),
             (0, "Save K: scatter|64 lines per row", 132, "vnni"), (0, "Save V", 60, "plain"),
             (1, "drain GOFs: gather|64 lines per row", 138, "vnni"), (1, "wait K/V|of this layer", 88, "wait"),
             (1, "tail: qk_group|64 lines per block", 132, "vnni"), (1, "hw wait|(spin)", 66, "wait"), (1, "join", 50, "plain"),
             (0, "WO matmul|waits attention out", 120, "wait")]
    late = [(0, "rmsnorm|+ rope", 70, "plain"), (0, "WV matmul|launch", 70, "plain"), (0, "prepare|(barrier)", 66, "plain"),
            (0, "Save K: scatter|64 lines per row", 132, "vnni"), (0, "Save V", 60, "plain"),
            (0, "prepare +|launch HW", 90, "plain"), (2, "attention on|the card", 150, "fpga"),
            (1, "drain GOFs:|gather", 90, "vnni"), (1, "wait K/V", 60, "wait"),
            (1, "tail: qk_group", 100, "vnni"), (1, "hw wait|(spin)", 66, "wait"), (1, "join", 50, "plain"),
            (0, "WO matmul|waits attention out", 120, "wait")]
    panel(44, "A. Early launch (batch of 4 or more users per engine: runtron with 8 users, CI tp4).|The card is launched before Save K. The store overlaps the card's work.", early)
    panel(312, "B. Late launch (batch below 4 users per engine: CI tp2 with 2 users).|Save K and Save V run before the card is launched. The store is serial time.", late)
    s.append(f'<text x="20" y="{H_ - 34}" font-size="12" fill="{INK2}">Dashed = waiting. The drain of completed GOFs (populate + DMA submit) runs on the workers at the start of the NEXT layer, and on the main thread after the last layer (wait_coop_gof).</text>')
    s.append(f'<text x="20" y="{H_ - 16}" font-size="12" fill="{INK2}">Sources: generated plugin qwen_3_4b_instruct_2507.hpp:1790-1836 and 7743-7757 (on 3bda); model.hpp:91-137 (launch phase); self_attention.hpp:746-813; model.hpp:3166-3189.</text>')
    s.append("</svg>")
    return "\n".join(s)


# ------------------------------------------------------------------ figure 3: micro-benchmark dumbbells
def fig_bench(bt):
    if not bt:
        return "<p>Micro-benchmark results pending.</p>"
    W, H_ = 1040, 300
    left, right, top, rowh = 330, 900, 70, 62
    rows = [("K store, main thread", "store_ns_per_row", "with-worker"),
            ("tail scoring, 1 live token x 4 heads", "tail_score_ns_per_row", "with-worker"),
            ("staging read of a GOF row (populate)", "stage_ns_per_row", "with-worker")]
    xmax = 800.0
    X = lambda v: left + v / xmax * (right - left)
    s = [f'<svg class="chart" viewBox="0 0 {W} {H_}" width="{W}" height="{H_}" role="img" aria-label="Micro-benchmark: nanoseconds per row for the three K-path operations, VNNI layout against row-major, decode-like access pattern" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, Segoe UI, sans-serif">',
         f'<rect x="0" y="0" width="{W}" height="{H_}" fill="{SURF}"/>',
         f'<text x="20" y="22" font-size="13" fill="{INK2}">Figure 3. Micro-benchmark on delphi-3bda (2026-09-18): ns per (token, KV head) row, 2304 rows per step (8 users x 8 heads x 36 layers), main and worker on two cores.</text>',
         f'<circle cx="28" cy="44" r="6" fill="{GRAY}"/><text x="40" y="48" font-size="12.5" fill="{INK}">row-major K (base)</text>',
         f'<circle cx="228" cy="44" r="6" fill="{ORANGE}"/><text x="240" y="48" font-size="12.5" fill="{INK}">VNNI K (PR 4424)</text>']
    for v in range(0, 801, 200):
        x = X(v)
        s.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{top + rowh * len(rows)}" stroke="{GRID if v else AXIS}" stroke-width="1"/>')
        s.append(f'<text x="{x:.1f}" y="{top + rowh * len(rows) + 16}" font-size="12" text-anchor="middle" fill="{INK2}">{v} ns</text>')
    s.append(f'<text x="{(left + right) / 2:.0f}" y="{top + rowh * len(rows) + 36}" font-size="12.5" text-anchor="middle" fill="{INK2}">nanoseconds per row (median of 3 runs)</text>')
    for i, (lab, key, w) in enumerate(rows):
        cy = top + i * rowh + rowh / 2
        b = bt.get((2304, "rowmajor", w, key)); v = bt.get((2304, "vnni", w, key))
        if b is None or v is None:
            continue
        s.append(f'<text x="{left - 14}" y="{cy + 4}" font-size="13" font-weight="600" text-anchor="end" fill="{INK}">{esc(lab)}</text>')
        s.append(f'<line x1="{X(b):.1f}" y1="{cy:.1f}" x2="{X(v):.1f}" y2="{cy:.1f}" stroke="{ORANGE}" stroke-width="2"/>')
        s.append(f'<circle cx="{X(b):.1f}" cy="{cy:.1f}" r="7" fill="{GRAY}" stroke="{SURF}" stroke-width="2"/><circle cx="{X(v):.1f}" cy="{cy:.1f}" r="7" fill="{ORANGE}" stroke="{SURF}" stroke-width="2"/>')
        s.append(f'<text x="{X(b):.1f}" y="{cy - 12}" font-size="12" text-anchor="middle" fill="{INK2}">{b:.0f}</text>')
        s.append(f'<text x="{X(v):.1f}" y="{cy - 12}" font-size="12" text-anchor="middle" fill="{INK}">{v:.0f}</text>')
        s.append(f'<text x="{right + 14}" y="{cy + 4}" font-size="12.5" fill="{INK}">{v - b:+.0f} ns ({v / b:.1f}x)</text>')
    s.append("</svg>")
    return "\n".join(s)


# ------------------------------------------------------------------ the page
def page():
    rows = budget_rows()
    bt = bench_table()
    summ = json.load(open(os.path.join(RES, "summary.json"))) if os.path.exists(os.path.join(RES, "summary.json")) else None
    css = f"""
    body {{ margin: 0; background: #ffffff; color: {INK}; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 15px; line-height: 1.5; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 24px 16px 60px; }}
    h1 {{ font-size: 26px; margin: 0 0 6px; }} h2 {{ font-size: 20px; margin: 34px 0 10px; border-bottom: 1px solid {GRID}; padding-bottom: 4px; }} h3 {{ font-size: 16px; margin: 22px 0 6px; }}
    p {{ margin: 8px 0; }} .meta {{ color: {INK2}; font-size: 13px; }}
    .short {{ background: #f3f2ef; border-left: 4px solid {BLUE}; padding: 10px 14px; margin: 14px 0; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; margin: 10px 0; }} th, td {{ border: 1px solid {GRID}; padding: 5px 8px; text-align: left; vertical-align: top; }} th {{ background: #f3f2ef; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .chart {{ display: block; max-width: 100%; height: auto; margin: 12px 0; }} .cap {{ color: {INK2}; font-size: 13px; margin: 0 0 14px; }}
    code {{ background: #f3f2ef; padding: 1px 4px; border-radius: 3px; font-size: 13px; }} pre {{ background: #f3f2ef; padding: 10px 12px; overflow-x: auto; font-size: 12.5px; line-height: 1.4; }}
    .ok {{ background: #e6f4ec; }} .warn {{ background: #fbe3d8; }} .no {{ background: #f3f2ef; color: {INK2}; }} .mid {{ background: #fdf3d6; }}
    ul {{ margin: 6px 0 6px 22px; }} li {{ margin: 3px 0; }}
    """
    P = []
    P.append(f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Issue 4500 root cause plan</title><style>{css}</style></head><body><main>
<h1>Finding the cause of the FPGA-attention decode loss under the VNNI K layout</h1>
<p class="meta">Design and execution record for positron-ai/tron issue #4500. Written 2026-09-18 (Claude); code read at PR #4424 head 30c4ac82cb (worktree VNNIed-K-in-place/tron-VNNIed-K), merge base c7844ca2ce. Facts come from a 16-agent read-and-verify pass (8 readers, 8 adversarial verifiers); every fact carries a file:line citation. The codex design (codex/design/root-cause-tracing.html) was compared after this design was drafted; section 9 lists what was taken from it.</p>
<div class="short"><b>Short version.</b> The extra time is spent on the CPU, not on the FPGA card: the bytes the card reads are identical in both builds, and only three CPU operations on the K cache differ (the per-token K store on the main thread, the K-row gather when a group of four tokens is staged for the card, and the tail-scoring reader on the workers). A micro-benchmark run today on delphi-3bda measured the K store at +350 ns per row, which alone predicts 98 % of the runtron tp4 loss, about half of the CI tp4 loss and about 70 % of the CI tp2 loss (tp4 and tp2 = the model split over 4 or 2 FPGA cards; CI = the nightly test layout). The plan measures the three costs in the running program with runtron and Perfetto traces, separates the store from the other two with a run-time switch that needs no rebuild, and names in advance the result that confirms or rejects each cause.</div>
""")
    # ---------------- words
    P.append("""<h2>Words used here</h2>
<table><tr><th>term</th><th>meaning</th></tr>
<tr><td>tp2, tp4</td><td>tensor parallel over 2 or 4 FPGA cards: the model's weights are split across that many cards of one engine (tp2 uses cards 90 and 93 of our half, tp4 adds b9 and bc). The K cache is not split across the cards (section 1).</td></tr>
<tr><td>CI, CI layout, nightly</td><td>CI = the nightly continuous-integration run of systems_test on delphi-3bda. The CI layout is its serving shape: 8 users through the Caddy proxy over 4 tp2 engines (2 users per engine) or 2 tp4 engines (4 users per engine), prompt 1024, 1536 generated tokens, TPS captured between generated tokens 896 and 1024.</td></tr>
<tr><td>tron, runtron, rinzler</td><td>tron = the inference program under test. runtron = its command-line tool (one model, synthetic users). rinzler = the production server the nightly CI drives through the Caddy proxy.</td></tr>
<tr><td>FPGA attention, HW attention</td><td>attention scored on the FPGA cards. The environment variable USE_HW_ATTN unset turns it on for ingested models such as qwen-3-4b. The CPU still scores the newest tokens (the tail, section 2).</td></tr>
<tr><td>VNNI K layout, PR 4424, TRON_K_VNNI</td><td>VNNI = Vector Neural Network Instructions. PR 4424 stores the K cache of 128-dimension heads in the pair-interleaved operand layout of the AMX tile multiply instead of row by row. TRON_K_VNNI is its CMake option; there is no run-time switch.</td></tr>
<tr><td>AMX, kill switch</td><td>AMX = Intel Advanced Matrix Extensions, the tile unit of the CPU. The kill switch TRON_AMX_DISABLE=1 turns the AMX kernels off at run time; it does not change the K layout.</td></tr>
<tr><td>K, KV head, KV cache, bf16</td><td>K = the attention keys of the past tokens (V = their values). A KV head is one key/value head of an attention layer; qwen-3-4b has 8 per layer, each shared by 4 query heads. The KV cache is the store of every past token's keys and values. bf16 = 16-bit brain floating point, 2 bytes per value.</td></tr>
<tr><td>row, line, plane, page</td><td>row = one token's K values for one KV head (128 bf16 = 256 bytes). line = one 64-byte cache line. plane = the K storage of one (page, KV head) = 64 tokens x 128 dims = 16 KiB. page = 64 tokens of the KV cache.</td></tr>
<tr><td>scatter, gather, RFO</td><td>scatter_row writes one row into the VNNI plane with 4 AVX-512 scatter instructions: 4 bytes into each of 64 lines. gather_row reads one row back with 4 gather instructions from the same 64 lines. Row-major stores or reads a row as 4 whole lines. RFO = read-for-ownership: before a core writes part of a line it must fetch the whole line, so a partial write costs a line transfer.</td></tr>
<tr><td>GOF, populate, staging, DMA</td><td>GOF = group of four consecutive tokens, the unit copied to the card. gof::populate copies the 4 tokens' K and V rows into an 8 KiB + 8 KiB staging block. DMA = the copy of that block into the card memory (HBM). A GOF is populated when its 4th token's K and V are saved, and again only if its staging block was freed and a new DMA needs it (backfill of a new shard) [gof.cpp:193-195; gof.hpp:244-265]. In a plain decode run each GOF is populated once.</td></tr>
<tr><td>tail, qk_group, dotter</td><td>tail = the tokens after the last DMA-complete GOF (1 to about 8 per user), which the CPU scores every step. qk_group = the AVX-512 reader of the VNNI plane (64 masked line loads per 16-token block, whatever the number of live tokens). dotter = the row-major per-token reader (4 lines per live token).</td></tr>
<tr><td>main thread, attention workers, main helpers</td><td>main thread = the thread that runs the generated plugin's run() (rmsnorm, matmul launches, Save K, Save V). attention workers = the pool threads that score the tail and stage GOFs. main helpers = pool threads that share dense kernels with main; they do nothing for K in decode.</td></tr>
<tr><td>rmsnorm, rope, WV, WO, matmul</td><td>rmsnorm = the layer normalization before attention. rope = the rotary position encoding applied to Q and K. WV and WO = the value-projection and output-projection weight matrices of the attention layer (tron record labels). A matmul is one weight multiplication launched on the card.</td></tr>
<tr><td>ready section, pending section, join</td><td>An attention worker's ready section scores pages written in earlier steps (empty under FPGA attention in decode). Its pending section scores the pages written in this step (the tail). The join merges every worker's partial results and the card's result for one KV head.</td></tr>
<tr><td>Perfetto, trace, span, pass, category</td><td>Perfetto = the in-process tracing library compiled into tron; runtron --trace-gen FILE writes one trace per run. A span is one timed code region in the trace (start, end, thread). A pass is one forward run of the model over the batch: one prefill chunk or one decode step (the forward span carries n_token_jobs). A category is a group of spans that TRON_TRACE_CATEGORIES turns on together.</td></tr>
<tr><td>hugepage, generated tokens (-l)</td><td>hugepage = a 1 GiB memory page reserved for tron; the machine has 512, the tp4 placement needs 256. runtron -l N = N generated tokens per user (the runs below use 256 for TPS cells, 40 for traces, 4096 for the perf window).</td></tr>
<tr><td>early / late launch, B</td><td>B = tokens (users) in one batch of one engine. B &gt;= TRON_HWATTN_EARLY_LAUNCH_MIN_B (default 4) launches the card BEFORE Save K and Save V of the layer (early). Smaller B saves K and V first and launches after (late).</td></tr>
<tr><td>TPS, step, TTFT</td><td>TPS = generated tokens per second per user. step = 1000 / TPS in ms = the period of one batched decode step (all users of an engine share it). TTFT = time to first token.</td></tr>
<tr><td>arms: base, headoff, vnni, vnni2, vnnikill, head30</td><td>base = runtron.main0916 (c7844ca2ce, the PR's merge base, row-major K, AMX dispatch compiled). headoff = runtron.headoff0916 (ff680c8020 = PR code with TRON_K_VNNI=OFF, row-major K). vnni = runtron.pr4424 (ff680c8020, TRON_K_VNNI=ON). vnni2 = the vnni binary run a second time in the same repetition (an A/A control: two runs of the same program measure run-to-run noise; any vnni2 minus vnni difference is noise). vnnikill = vnni with TRON_AMX_DISABLE=1. head30 = tron-tilec/gen/runtron (30c4ac82cb, the PR head on GitHub), run once. All built on 3bda, RelWithDebInfo.</td></tr>
<tr><td>paired t, Welch t</td><td>paired t = mean of per-repetition differences divided by its standard error (repetitions interleave the arms). Welch t = two-sample t with unequal variances. Two-sided 95 % thresholds: 12.71 at n = 2, 4.30 at n = 3, 2.57 at n = 6, 2.26 at n = 10.</td></tr>
</table>""")
    # ---------------- section 1: the loss
    P.append("""<h2>1. The loss to explain</h2>
<p>All four measured configurations run qwen-3-4b (36 layers, 8 KV heads, head size 128, 4 query heads per KV head) with prompt 1024 and FPGA attention. The table converts each TPS pair into a per-step budget. The step period is 1000 / TPS. Every user of an engine reports the same ms per token to 0.001 ms, so the step is shared [wedperf-attr rt logs, 8 'average tok/s' lines per run].</p>
<table><tr><th>configuration</th><th class="num">base TPS</th><th class="num">target TPS</th><th class="num">step base ms</th><th class="num">step target ms</th><th class="num">loss ms/step</th><th class="num">loss %</th><th class="num">us per layer</th><th class="num">rows per layer</th><th class="num">ns per row</th><th>launch</th><th>source</th></tr>""")
    for r in rows:
        P.append(f'<tr><td>{esc(r["name"])}</td><td class="num">{r["base"]:.2f}</td><td class="num">{r["target"]:.2f}</td><td class="num">{r["step_b"]:.3f}</td><td class="num">{r["step_t"]:.3f}</td><td class="num">{r["delta_ms"]:+.3f}</td><td class="num">{r["pct"]:+.1f}</td><td class="num">{r["us_layer"]:.1f}</td><td class="num">{r["rows"]}</td><td class="num">{r["ns_row"]:.0f}</td><td>{r["phase"]}</td><td>{esc(r["src"])}</td></tr>')
    P.append("""</table>
<p class="cap">rows per layer = users per engine x 8 KV heads. ns per row = the loss per layer divided by the rows. The K cache is not split across the tp cards (a 1024-token shard with all 8 KV heads lives on one card) [full.hpp:2442-2488; gof.cpp:161-164], so tp does not change the rows [gof.hpp:36; shard.hpp:5].</p>
<ul>
<li><b>The loss is not proportional to rows.</b> Per row it spans 79 ns (runtron tp2) to 716 ns (CI tp4), a 9x spread. A cost that is purely per row cannot fit all four cells. Exposure matters: how much of the extra CPU time lands on the step's critical path.</li>
<li><b>The store cost fits the tp4 runtron cell and the CI tp2 cell.</b> CI tp2 runs 2 users per engine, below the early-launch threshold of 4 (section 2). Save K therefore runs before the card launch and is fully on the critical path. Its 495 ns per row is 1.4x the +350 ns per row the micro-benchmark gives for the scatter store (section 6), so the store explains 71 % of that cell. runtron tp4 loses 23 us per layer with 2304 rows per step, and 2304 rows x 350 ns = 0.81 ms per step (est.) is 98 % of its loss. CI tp4 loses the same 23 us per layer with only 1152 rows per step, so the store predicts 0.40 ms (est.) of its 0.825 ms, about half. The other half of the CI tp4 loss needs another cause (sections 3 and 5).</li>
<li><b>runtron tp2 with 8 users overlaps most of the store with the card's work.</b> It loses 5 us per layer. The micro-benchmark predicts 23 us per layer for the store at 8 users (est., 2304 rows x 355 ns / 36 layers). At tp2 the card's step is long enough that the early-launched attention runs at the same time as Save K and Save V, so most of the store cost is hidden there.</li>
<li><b>The tp4 runtron runs are bimodal.</b> The two row-major arms of the 2026-09-16 campaign (eb2de0265a = main before PR 3879, and c7844ca2ce = this page's base) sit at 7.40 ms per step in 9 of 12 repetitions and at 8.46 ms in 3. The VNNI arm (ff680c8020) sits at 8.54 ms in 6 of 6 [wedperf-attr rt logs, per-rep 'average tok/s']. The design records per-repetition steps, not only means.</li>
</ul>""")
    P.append(fig_budget(rows))
    P.append('<p class="cap">Figure 1. Blue bars: the measured loss per decode step. Orange ticks: the K-store cost predicted from the micro-benchmark (rows per step x 350 ns, est.). The tick reaches the bar in the runtron tp4 cell (98 %), covers half of the CI tp4 bar (49 %) and 70 % of the CI tp2 bar. The runtron tp2 bar is far below its tick, so most of the store is overlapped there.</p>')
    # ---------------- section 2: what runs
    P.append("""<h2>2. What a decode step does with FPGA attention (verified in the code)</h2>
<p>The FPGA reads K only through gof::populate. PR 4424 did not change the staging block format, the DMA or the HBM layout [git diff c7844ca2ce..30c4ac82cb: h/pos, lib, fpga-reg untouched; gof.cpp +2/-1]. So the card's work is identical in both builds and the loss is CPU time. Three operations differ, and only three, on the decode path:</p>
<table><tr><th>#</th><th>operation</th><th>who runs it, when</th><th>row-major (base, headoff)</th><th>VNNI (vnni)</th><th>how often</th><th>citations</th></tr>
<tr><td>1</td><td><b>K store</b> (Save K)</td><td>main thread, every layer, every step; never shared with helpers below 17 items</td><td>memcpy of 4 whole lines per row</td><td>scatter_row: 4 bytes into each of 64 lines (64 read-for-ownership transfers)</td><td>users x 8 heads rows per layer, every step</td><td>model.hpp:2806-2814, 3040, 2914-2927; kv_cache.hpp:1701-1711; k_vnni.hpp:135-146</td></tr>
<tr><td>2</td><td><b>staging gather</b> (populate)</td><td>an attention worker at the start of the next layer (help_drain_gof, 4 GOFs per worker), or the main thread after the last layer (wait_coop_gof)</td><td>returns a pointer into the page; the shuffle reads 4 lines</td><td>gather_row: 4 gathers over 64 lines into scratch, then the shuffle reads the scratch</td><td>once per GOF per layer: every 4th token per user (in runtron all users complete a GOF on the same step: 288 populates every 4th step)</td><td>full.hpp:2644-2661; gof.cpp:188-222; model.hpp:3146-3189; TronCpp.hs:1331-1348</td></tr>
<tr><td>3</td><td><b>tail scoring</b> (pending section)</td><td>attention workers, every layer, after Save K and Save V of the layer, before the hw wait</td><td>dotter: 4 lines per live token, 4 heads</td><td>qk_group: 64 masked line loads + 256 VDPBF16PS per 16-token block with any live token</td><td>users x 8 heads calls per layer, every step; 1 to 8 live tokens</td><td>self_attention.hpp:1604-1641, 776-789; k_vnni.hpp:246-308; dotter.hpp:176-226</td></tr>
</table>
<ul>
<li><b>Not on the decode path:</b>
<ul>
<li>the AMX dense-page kernel. is_dense_amx_page (the check that selects that kernel) needs a whole 64-token page in the software range. Under FPGA attention that holds only when the DMA lags by 64 or more tokens or when a shard cannot use the card [self_attention.hpp:1383-1394; ranged_mask.cpp:13-96]. The vnnikill arm is the direct check, and the m3 tail-length reading (H5) shows the lag. In prefill the dense AMX kernel does run under FPGA attention.</li>
<li>page copies. copy_storage_slot runs only from book::append during tree defragmentation (compaction of a conversation tree's KV pages) [kv_cache.hpp:2093-2120; full.hpp:1309-1347].</li>
<li>the shared block save. It needs more than 16 items [model.hpp:2806-2814].</li>
<li>the rest of the diff: a 4.7 KiB batch struct zeroed per step, a no-op helper call per layer, one assert per row on the VNNI path. Together below 20 us per step (est. from operation counts, not measured).</li>
</ul></li>
<li><b>Why the CPU-attention campaigns did not see it.</b> There the same store cost (+24 to +29 us per layer at 8 users [vnnik-trace-20260914 analysis.md]) was smaller than the time the AMX reader saved on the full pages, and the step still got shorter. Under FPGA attention the card scores the full pages. The AMX reader then saves no time, and the store, the gather and the tail reader add time with nothing to offset them.</li>
<li><b>Populate never gates the same step's card launch.</b> The launch waits only for the rotated Q; DMA completion is observed once per forward at the next forward's start [self_attention.hpp:634-672; full.hpp:1877; model.hpp:1512]. A slow populate lengthens the tail (more tokens scored on the CPU) in the following step instead.</li>
<li><b>Order inside a layer, early phase (B &gt;= 4)</b> [plugin qwen_3_4b_instruct_2507.hpp:1790-1836, 7743-7757; TronCpp.hs:2370-2411; model.hpp:91-137].
<ol>
<li>Main thread: (1) rmsnorm and rope; (2) launch the WV matmul; (3) prepare, ending in a barrier with the workers; (4) launch HW attention; (5) Save K; (6) Save V; (7) the WO matmul waits for the attention output.</li>
<li>Workers: (1) wait at the barrier; (2) drain up to 4 GOFs (populate + DMA submit); (3) ready sections (empty in decode); (4) wait for Save K and Save V; (5) pending section = tail scoring; (6) spin until the card's result arrives (hw wait); (7) join.</li>
<li>Late phase (B &lt; 4): Save K and Save V come before prepare and launch on the main thread. The workers' wait ends at Save V, so the tail scoring then runs in parallel with prepare, launch and the card.</li>
</ol></li>
</ul>""")
    P.append(fig_lanes())
    P.append('<p class="cap">Figure 2. In panel A the store (orange, main) overlaps the card; the tail scoring and the GOF drain (orange, workers) sit before the hw wait. In panel B the store precedes the launch, so every extra nanosecond of it delays the card. Widths are schematic; the traces of block m3 give the real widths.</p>')
    # ---------------- section 3: hypotheses
    P.append("""<h2>3. Candidate causes and what each predicts</h2>
<table><tr><th>id</th><th>cause</th><th>mechanism</th><th>scales with</th><th>size est. (from section 6, labelled est.)</th><th>prediction that would confirm it</th></tr>
<tr><td><b>H1</b></td><td>K store scatter on the main thread</td><td>64 partial-line writes per row instead of 4 whole lines; serial main-thread time; fully exposed when the launch is late, partly hidden when early</td><td>users per engine x 8 x 36, every step; exposure depends on B and on the card's step length</td><td>+350 ns per row: 0.81 ms per step at 8 users, 0.40 at 4, 0.20 at 2 (est.)</td><td>Save K span grows by about 20 us per layer at 8 users in the trace; the loss moves with the launch phase (block m2); perf: stores and RFO misses on the main thread only</td></tr>
<tr><td><b>H2</b></td><td>K-row gather in populate</td><td>64 lines per row, cross-core (the main thread wrote them); runs on workers before their sections or on main at forward end</td><td>users / 4 x 36 GOFs per step on average; bursty in runtron</td><td>+64 ns per row: +2.0 us per GOF per layer; 0.15 ms per step average at 8 users, 0.59 ms on the burst step (est.)</td><td>gof_populate sum per burst pass grows by about 0.5 ms; wait_coop_gof on main grows; a 4-step period in the per-step time series of runtron (absent in the CI layout)</td></tr>
<tr><td><b>H3</b></td><td>tail scoring with qk_group</td><td>64 lines per block for 1 to 8 live tokens instead of 4 lines per token; on the workers in the pending section, before the hw wait</td><td>users x 8 x 36 per step, spread over 20 to 47 workers</td><td>+580 ns per (user, head, layer): 1.3 ms of worker time per step at 8 users; 30 to 70 us per step on the critical path if spread (est.)</td><td>Attention Pending max per worker grows by about 2 us per layer; the loss does not move with the launch phase</td></tr>
<tr><td><b>H4</b></td><td>a discrete state at tp4</td><td>base sits in a fast (7.4 ms) or slow (8.5 ms) mode per run; the VNNI arm always in the slow one; candidate: round-robin card of the second shard, or a DMA-lag threshold</td><td>per run, not per row</td><td>1.05 to 1.14 ms per step when it flips (measured spread)</td><td>per-repetition steps of base/headoff show two clusters; traces of a fast and a slow base run differ in shard placement or hw wait</td></tr>
<tr><td><b>H5</b></td><td>second-order: a slower populate or DMA lengthens the tail</td><td>DMA completion is seen one step later; more tail tokens for H3 to score</td><td>couples H2 to H3</td><td>at most 4 more tokens per user per lagging step (est.)</td><td>the pending span's live-token count (or Attention Pending duration) grows on the step after a burst in the vnni arm only</td></tr>
<tr><td><b>H6</b></td><td>anything else in the PR (batch struct zeroing, helper no-op, asserts, AMX tile bracket)</td><td>common or tiny</td><td>-</td><td>below 20 us per step (est. by count); the AMX bracket exists in base too</td><td>headoff vs base shows no loss (same launch phase, same rows)</td></tr>
</table>""")
    # ---------------- section 4: measurements
    P.append("""<h2>4. Measurements, in the order they run</h2>
<p>Everything below runs with binaries that already exist on delphi-3bda; nothing needs a rebuild. Scripts: exec/issue4500-20260918/{campaign.sh, summarize.py, trace_analyze.py, bench/}. Results: exec/results/issue4500-20260918/.</p>
<table><tr><th>block</th><th>what</th><th>arms x cells</th><th>reads</th><th>separates</th><th>runs, time</th></tr>
<tr><td><b>m1</b></td><td>attribution without tracing: the same runtron cell as the issue (1 engine, 8 users, prompt 1024, 256 tokens, --dont-stop)</td><td>base, headoff, vnni, vnni2 (A/A), vnnikill; head30 once; tp2 and tp4; 3 interleaved repetitions (order reversed on even repetitions)</td><td>TPS per user, step ms, TTFT, per-rep values</td><td>layout (vnni vs headoff, same source) from the PR's other code (headoff vs base); AMX kernel (vnnikill vs vnni); noise (vnni2 vs vnni); GitHub head equivalence (head30 vs vnni)</td><td>32 runs, about 30 min</td></tr>
<tr><td><b>m2</b></td><td>launch-phase switch: TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 forces the early launch at 2 users, =100 forces the late launch at 8 users</td><td>headoff, vnni; users 2 and 8; tp2 and tp4; 3 repetitions</td><td>same</td><td>H1 (exposure of the store) from H2 and H3: D = (vnni minus headoff under the late launch) minus (the same under the early launch), per repetition. D clearly positive = the store is the exposed cost (H1); D negative = the tail reader (H3); D near zero = the gather (H2). Section 5 gives the threshold.</td><td>48 runs, about 45 min</td></tr>
<tr><td><b>m3</b></td><td>Perfetto in-process traces of all passes (40 generated tokens per user, enough for 10 GOF bursts): categories model, scheduler, hwattention (set A) and + hwattention-detail (set B)</td><td>base, headoff, vnni at tp2 and tp4 with 8 users; headoff and vnni at tp2 with 2 users (late launch)</td><td>per decode pass: Save K/V on main, wait_coop_gof, gof_rodeo / gof_populate count and duration per thread, Attention Pending/Ready per worker, hw wait, launch; burst passes tagged by gof_rodeo count</td><td>where the extra time sits (main vs workers), whether it is on the critical path (gap from Save V end to the WO launch, hw wait length), the 4-step burst pattern (H2), the tail length (H5)</td><td>14 runs, about 15 min; analysis on claude-agentsrv (trace_analyze.py)</td></tr>
<tr><td><b>m4</b></td><td>sampling and hardware counters with sudo perf on the runtron process during decode (4096 generated tokens per user, so decode lasts about 33 s): perf record -g for 6 s first (about 2 to 8 s into decode, steady state), then per-thread cycles and instructions (6 s), L1/L2/L3 load misses (raw event 0xd1, 3 s), LLC and local/remote DRAM misses (0x2e, 0xd3, 3 s), stores and RFO misses and AMX-busy (3 s)</td><td>headoff, vnni at tp2 and tp4, 8 users</td><td>which thread class absorbs the extra cycles and misses; symbol-level shares (store_k_block with the inlined scatter, the k_head_fn lambda with the gather, qk_group)</td><td>H1 (main thread stores/RFO) from H2/H3 (worker misses); confirms the micro-benchmark in place</td><td>4 runs, about 8 min</td></tr>
<tr><td><b>m1b</b></td><td>per-engine load like the CI layout: 2 and 4 users per engine</td><td>base, headoff, vnni; tp2 and tp4; 2 repetitions</td><td>same as m1</td><td>the users-per-engine dependence the CI cells show (late launch at 2 users)</td><td>24 runs, about 20 min</td></tr>
<tr><td><b>bench</b></td><td>micro-benchmark of the three operations in the decode access pattern (done, section 6)</td><td>VNNI vs row-major; 2304 / 1152 / 576 rows per step; with and without the worker thread</td><td>ns per row</td><td>sizes H1, H2, H3 before the traces</td><td>done 2026-09-18 21:50 UTC</td></tr>
<tr><td><b>m5</b> (conditional)</td><td>debug-branch probes if m1-m4 leave the split ambiguous: (a) a row-major shadow copy of K written at save time and read by k_head_fn (removes H2; also fix option 1 of the issue); (b) prefetch-for-write of the 64 lines before the scatter, or a streaming store variant (tests H1); (c) a one-line log of the shard's card per shard creation (tests H4)</td><td>on a debug branch only (jhan-dd-*), never on the PR branch</td><td>TPS + trace</td><td>the selective intervention codex asks for</td><td>build 10 min + 12 runs</td></tr>
<tr><td><b>m6</b> (after the cause is known)</td><td>CI-layout confirmation on our half with rinzler + the CI client (exec/l8bload-20260918/rz.sh + st_perf.py): 1 engine tp2 x 2 users, 1 engine tp4 x 4 users, generate 1536, TPS window 896-1024</td><td>installed nightly deb rinzler (no AMX code) vs the ci-mimic target deb rinzler (AMX + VNNI) vs target + kill switch vs target + TRON_HWATTN_EARLY_LAUNCH_MIN_B=1</td><td>CI-style TPS</td><td>ties the runtron finding to the harness that flips the CI threshold; tests the launch-phase lever as a mitigation at 2 users</td><td>16 runs x 3 min, next free window</td></tr>
</table>
<h3>Exact commands</h3>
<pre>""" + esc("""# one runtron cell (arm vnni, tp2, 8 users); the campaign wraps this in the guard and a watcher
cd /var/tmp/jhan/tron-pr4424 && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE -u USE_HW_ATTN TRON_LOG_LEVEL=info \\
  timeout -k 60 1200 gen/runtron.pr4424 stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \\
  --instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 \\
  --dev-cores 75,76 --numa 1 --nr_hugepages 128 --hugepage_file /dev/hugepages/amx-i4500 -o \\
  --prompt-length 1024 -l 256 -u 8 --dont-stop
# m2: prepend TRON_HWATTN_EARLY_LAUNCH_MIN_B=1 (early at 2 users) or =100 (late at 8 users)
# m3: add TRON_TRACE_CATEGORIES='-*,+model,+scheduler,+hwattention[,+hwattention-detail]' and
#     -l 40 --trace-gen FILE --trace-passes 1-   (passes are then classified by the forward span's n_token_jobs)
# m4: while decode runs (after 8 'Parsing the prompt took' lines):
sudo -n perf stat --per-thread -e cycles,instructions -p PID -- sleep 6
sudo -n perf stat --per-thread -e '{cpu/event=0xd1,umask=0x08,name=l1_miss/,cpu/event=0xd1,umask=0x10,name=l2_miss/,cpu/event=0xd1,umask=0x20,name=l3_miss/}' -p PID -- sleep 3
sudo -n perf stat -e mem_inst_retired.all_stores,mem_inst_retired.all_loads,ocr.demand_rfo.l3_miss,cpu/event=0xb7,umask=0x02,name=exe_amx_busy/ -p PID -- sleep 3
sudo -n perf record -g -F 1999 -p PID -o FILE -- sleep 6""") + "</pre>")
    # ---------------- section 5: prediction matrix + decision rules
    P.append("""<h2>5. Prediction matrix and decision rules</h2>
<p>Each cell says what the measurement shows if the cause in the column is the main one. A cause is accepted only when every row agrees.</p>
<table><tr><th>measurement</th><th>H1 store (main)</th><th>H2 gather (workers/main end)</th><th>H3 tail reader (workers)</th><th>H4 tp4 state</th></tr>
<tr><td>m1: headoff vs base (tests H6 for the PR code compiled with the layout off; the per-row assert and the k_store_shared check exist only on the VNNI path and fold into H1's Save K span)</td><td class="ok">no loss</td><td class="ok">no loss</td><td class="ok">no loss</td><td class="mid">base bimodal at tp4</td></tr>
<tr><td>m1: vnnikill vs vnni</td><td class="ok">no resolved change (layout kept)</td><td class="ok">no resolved change</td><td class="ok">no resolved change</td><td class="ok">no resolved change</td></tr>
<tr><td>m2: D = (vnni minus headoff) late minus early, equal users</td><td class="warn">D positive: the store is serial under the late launch</td><td class="no">D near zero (the drain is off the launch path in both phases)</td><td class="mid">D negative or zero: under the late launch the tail starts at Save V end, in parallel with prepare, launch and the card</td><td class="no">D near zero</td></tr>
<tr><td>m3: Save K span on main per layer</td><td class="warn">+15 to +25 us per layer at 8 users</td><td class="no">unchanged</td><td class="no">unchanged</td><td class="no">unchanged</td></tr>
<tr><td>m3: gof_populate / gof_rodeo per burst pass; wait_coop_gof on main</td><td class="no">unchanged</td><td class="warn">+0.3 to +0.6 ms per burst pass; coop wait grows; 4-step period</td><td class="no">unchanged</td><td class="no">unchanged</td></tr>
<tr><td>m3: Attention Pending max per worker per layer</td><td class="no">unchanged</td><td class="mid">grows on the step after a burst (H5)</td><td class="warn">+1 to +3 us per layer</td><td class="no">unchanged</td></tr>
<tr><td>m3: gap Save V end to WO launch; hw wait length</td><td class="warn">gap grows on main (early) or the launch is later (late)</td><td class="mid">hw wait shorter on burst steps (workers late)</td><td class="mid">hw wait shorter (workers busier)</td><td class="warn">hw wait itself longer in the slow mode</td></tr>
<tr><td>m4: per-thread cycles and misses</td><td class="warn">main thread: stores x 16, RFO misses up</td><td class="warn">workers: L2/L3 misses up on burst</td><td class="warn">workers: L2/L3 misses up every step</td><td class="no">no signature</td></tr>
<tr><td>m4: perf record symbols</td><td class="warn">store_k_block / scatter site</td><td class="warn">k_head_fn lambda / gather_row</td><td class="warn">qk_group</td><td class="no">none</td></tr>
<tr><td>bench (done)</td><td class="warn">+350 ns per row = 0.81 ms per step at 8 users</td><td class="mid">+60 ns per row = 0.14 ms per step average</td><td class="mid">+580 ns per call = 1.3 ms of worker time per step, spread</td><td class="no">not testable off line</td></tr>
</table>
<h3>Rules fixed before the data</h3>
<ul>
<li><b>Resolved effect:</b> |paired t| &gt;= 12.71 at n = 2, 4.30 at n = 3, 2.57 at n = 6, and |delta| &gt;= 1 % of TPS. summarize.py pairs every arm against base and headoff, and vnni2, vnnikill and head30 against vnni. The A/A pair (vnni2 vs vnni) must be unresolved, or the whole block is repeated. head30 runs once, so head30 vs vnni is one run against the same-repetition vnni run, judged by the 1 % rule alone.</li>
<li><b>m2 criterion:</b> D = (vnni minus headoff step under the late launch) minus (the same under the early launch), per repetition and per (tp, users) cell; summarize.py prints mean, sd and t of D. |t| &gt;= 4.30 at n = 3 resolves it. The vnnikill arm removes only the Q-group packing and the AMX tile bracket, which base and headoff also pay (est. below the 1 % resolution), so a resolved vnnikill gain counts as an AMX-kernel signal only if it exceeds that.</li>
<li><b>A cause is "the cause"</b> when the span or counter it predicts explains at least 70 % of the per-step budget of section 1 in both tp2 and tp4, and the m2 switch moves in the predicted direction. 30 to 70 % = partial cause; below 30 % = not a cause.</li>
<li><b>Exposure is judged from the trace, not from CPU time.</b> Worker spans that spin (hw wait, join polling) do not count as busy. The critical path of a layer is the longer of (main: Save K + Save V + launch) and (workers: drain + pending + hw wait + join), read from the same trace.</li>
<li><b>Estimators:</b> per-rep step = 1000 / mean TPS of that run; the paired difference is over reps. summarize.py also reports the mean of the users' own ms per token (runtron prints both). The two differ by up to 0.03 ms per step at tp4 in the 2026-09-16 data.</li>
<li><b>Trace overhead:</b> a traced run's TPS is compared with the untraced m1 cell of the same arm; category set B (hwattention-detail) adds about 30 spans per GOF on the workers, so B's populate durations are trusted only if set A and the untraced TPS agree within 3 %.</li>
</ul>""")
    # ---------------- section 6: bench results
    P.append("""<h2>6. Micro-benchmark (measured 2026-09-18 21:50 UTC on delphi-3bda)</h2>
<p>exec/issue4500-20260918/bench/bench_k_vnni.cpp is a stand-alone copy of scatter_row, gather_row, qk_group&lt;4,bf16&gt; and dotter&lt;bf16,128&gt;, built with clang++-19 -O3 -march=native on the host. Two threads on socket-1 cores 87 and 88 (idle; the production engines were spinning on cores 96-143) alternate like a decode step: the main thread stores one new row into every plane of the step, then the worker scores the newest token of every plane with one query group and, every 4th step, stages the 4 newest rows of every plane (populate). The working set of 2304 planes is 36 MiB, larger than the 2 MiB L2 and inside the 432 MiB L3.</p>""")
    P.append(fig_bench(bt))
    if bt:
        P.append("""<table><tr><th>operation</th><th class="num">rows per step</th><th class="num">row-major ns/row</th><th class="num">VNNI ns/row</th><th class="num">delta ns/row</th><th>per step at that load (est. = rows x delta)</th></tr>""")
        for lab, key in (("K store (main thread, with the worker reading)", "store_ns_per_row"), ("K store (main thread alone, no worker)", "store_ns_per_row@nw"), ("tail scoring, 1 live token, 4 heads", "tail_score_ns_per_row"), ("staging read per GOF row (populate)", "stage_ns_per_row")):
            k2 = key.replace("@nw", ""); w = "--no-worker" if key.endswith("@nw") else "with-worker"
            for rows_ in (2304, 1152, 576):
                b = bt.get((rows_, "rowmajor", w, k2)); v = bt.get((rows_, "vnni", w, k2))
                if b is None or v is None:
                    continue
                per = rows_ * (v - b) / 1e6
                note = f" average per step ({per * 4:.2f} ms on the burst step, every 4th step)" if k2 == "stage_ns_per_row" else (" of worker time, spread over the workers" if k2 == "tail_score_ns_per_row" else " serial on main")
                P.append(f'<tr><td>{esc(lab)}</td><td class="num">{rows_}</td><td class="num">{b:.0f}</td><td class="num">{v:.0f}</td><td class="num">{v - b:+.0f}</td><td>{per:.2f} ms{note}</td></tr>')
        P.append("""</table>
<ul>
<li><b>The store is the largest serial cost.</b> 375 to 390 ns per row against 34 to 64 ns, flat from 9 MiB to 36 MiB of planes, with or without the worker. This is the cost of 64 partial-line writes to L3-resident lines, not an L2-capacity effect. The live CPU-attention decode traces gave 444 ns per row at tp2 and 540 ns per row at tp4 [vnnik-trace-20260914 analysis.md]. The benchmark's 389 ns per row is 14 to 39 % lower. Hypothesis: the live step adds contention from the other threads and the card DMA, which the two-thread benchmark does not model; the m4 counters on the main thread test it.</li>
<li><b>The tail reader is the largest total cost but spread over the workers.</b> 630 to 690 ns per (user, head, layer) call against 70 to 85 ns: qk_group touches 64 lines that the main thread just wrote, the dotter 4. At 8 users that is 1.3 ms of worker time per step; with 20 or more workers scoring in parallel it is 30 to 70 us per step on the critical path (est.).</li>
<li><b>The gather is the smallest per row</b> (+64 ns) but bursty: 288 populates x 32 rows x 64 ns = 0.59 ms on every 4th step in runtron (est.), 0.15 ms per step on average, part of it on the main thread in wait_coop_gof for the last layer's 8 GOFs.</li>
<li>Sum of the three at 8 users, if fully exposed: 0.81 ms (store) + 0.15 ms (gather, average over the 4-step cycle) + 0.07 ms (tail reader, upper bound of its critical-path share) = about 1.0 ms per step (est.). The measured runtron tp4 loss is 0.80 to 0.83 ms per step. So the tp4 step exposes almost all of the sum. The runtron tp2 step loses 0.18 ms per step and overlaps the rest with the card's work.</li>
</ul>""")
    # ---------------- section 7: execution plan
    P.append("""<h2>7. Execution plan on delphi-3bda</h2>
<ul>
<li><b>Where:</b> our half (socket 1, cards 90/93/b9/bc; Bill's marker /bill-has-instance-0,2 is present, so the first half is his). The campaign takes the campaign guard (CI lease + host flock + no runtron of ours) before every run and a watcher stops our run within 10 s if the CI lease turns busy or a production unit comes up [exec/lib-guard.sh].</li>
<li><b>When:</b> the nightly CI holds the machine 03:38 to about 13:20 UTC; the campaign never starts a run inside the 01:40-03:45 UTC pre-CI hold and ends itself there. Launched 2026-09-18 21:50 UTC in waiting mode; relaunch with the same command after the nightly (done runs are skipped).</li>
<li><b>Machine sharing tonight (agreed 22:1x UTC):</b> another session runs the nightly CI perf phase once more on the WHOLE machine with a canonical-AMX deb (main 3faba6d0fd + the deb preset change, no PR 4424), about 22:40 to 00:30 UTC, holding the campaign flock. At its end it reinstalls the nightly deb, stops the idle production engines through platformd, removes their slice files and releases the flock. That is exactly this campaign's start condition (every rinzler@N unit inactive, 256 free hugepages, CI lease free), so this campaign starts by itself at about 00:30 UTC and runs until the 01:40 UTC pre-CI hold: enough for m1 and most of m2. jhan authorized this session (22:1x UTC, "Option B") to stop the idle engines itself (the recipe in launch.sh) if a unit is left up, and for the resume after the nightly (about 13:20 UTC Saturday: m3, m4, m1b). The ci-runner-stop timer restores production serving at 02:45 UTC for the nightly.</li>
<li><b>Order and duration:</b> m1 (30 min), m2 (45 min), m3 (15 min), m4 (10 min), m1b (20 min): about 2 h once the machine is free. Resume is idempotent (a run whose log has 'average tok/s' is skipped).</li>
<li><b>Outputs:</b> exec/results/issue4500-20260918/{rt-results.txt, rt/*.log, traces/, perf/, bench/, summary.md}; log exec/logs/issue4500-20260918.log; status .status; marker .done. Analysis: summarize.py (3bda or here), trace_analyze.py (here: the python TraceProcessor works on claude-agentsrv only), perf report on 3bda.</li>
<li><b>After the data:</b> section 8 of this page is filled with the tables and the wall-clock lanes of one burst and one quiet decode pass per arm; the issue gets a comment with the cause and the measured split; m5/m6 follow the decision rules.</li>
</ul>
<h3>Traps carried over from earlier campaigns</h3>
<ul>
<li>runtron's SYSTEM_CONFIG from the login shell re-places a run onto instance 1,2: every command uses env -u SYSTEM_CONFIG.</li>
<li>Never edit campaign.sh while it runs (bash re-reads the file at its byte offset).</li>
<li>NFS attribute cache: a file edited here is checked by md5 on 3bda before a launch (launch.sh).</li>
<li>runtron -u N with token files appends Moby Dick prompts; the cells use -u with --prompt-length only, as the issue's runs did.</li>
<li>Perfetto passes are classified by the forward span's n_token_jobs (1024 = prefill, &lt;= 8 = decode), never by index; traces cover all passes (--trace-passes 1-) so no span loses its end at a window edge.</li>
<li>perf: perf_event_paranoid is 4, so every perf command runs through sudo -n; raw event codes are needed (perf 6.8.12 names only 43 events on this CPU); at most 3 general-purpose events per brace group (the NMI watchdog holds one counter).</li>
<li>/proc/PID/task/TID/stat: tron thread names below CPU 100 carry a leading space inside the parentheses; strip the comm before splitting fields.</li>
</ul>""")
    # ---------------- section 8: results placeholder or results
    P.append('<h2>8. Results</h2>')
    if summ and summ.get("cells"):
        P.append("<p>Filled from exec/results/issue4500-20260918/summary.json.</p>")
        P.append('<table><tr><th>block</th><th>tp</th><th>users</th><th>tag</th><th>arm</th><th class="num">n</th><th class="num">TPS</th><th class="num">sd</th><th class="num">step ms</th><th class="num">TTFT s</th><th>version</th><th>HW attn</th></tr>')
        for c in summ["cells"]:
            P.append(f'<tr><td>{c["block"]}</td><td>{c["tp"]}</td><td>{c["users"]}</td><td>{c["tag"]}</td><td>{c["arm"]}</td><td class="num">{c["n"]}</td><td class="num">{"-" if c["tps_mean"] is None else f"{c[chr(116)+chr(112)+chr(115)+chr(95)+chr(109)+chr(101)+chr(97)+chr(110)]:.2f}"}</td><td class="num">{"-" if c["tps_sd"] is None else f"{c[chr(116)+chr(112)+chr(115)+chr(95)+chr(115)+chr(100)]:.2f}"}</td><td class="num">{"-" if c["step_ms"] is None else f"{c[chr(115)+chr(116)+chr(101)+chr(112)+chr(95)+chr(109)+chr(115)]:.3f}"}</td><td class="num">{"-" if c["ttft_s"] is None else f"{c[chr(116)+chr(116)+chr(102)+chr(116)+chr(95)+chr(115)]:.3f}"}</td><td>{esc(str(c["version"]))}</td><td>{esc(str(c["hw"]))}</td></tr>')
        P.append("</table>")
        P.append('<table><tr><th>block</th><th>tp</th><th>users</th><th>a</th><th>b</th><th class="num">n</th><th class="num">step a</th><th class="num">step b</th><th class="num">delta ms/step</th><th class="num">delta TPS %</th><th class="num">us/layer</th><th class="num">paired t</th></tr>')
        for p in summ["pairs"]:
            P.append(f'<tr><td>{p["block"]}</td><td>{p["tp"]}</td><td>{p["users"]}</td><td>{esc(p["a"])}</td><td>{esc(p["b"])}</td><td class="num">{p["n"]}</td><td class="num">{p["step_a"]:.3f}</td><td class="num">{p["step_b"]:.3f}</td><td class="num">{p["delta_ms"]:+.3f}</td><td class="num">{p["delta_tps_pct"]:+.2f}</td><td class="num">{p["delta_us_per_layer"]:+.1f}</td><td class="num">{"-" if p["t"] is None else f"{p[chr(116)]:+.2f}"}</td></tr>')
        P.append("</table>")
        if summ.get("m2_criterion"):
            P.append('<h3>m2: the launch-phase criterion</h3><p>D = (vnni minus headoff step under the forced late launch) minus (the same under the forced early launch), per repetition. Positive D = the extra time is on the main thread before the launch (the store, H1).</p>')
            P.append('<table><tr><th>tp</th><th>users</th><th class="num">n</th><th class="num">d early ms</th><th class="num">d late ms</th><th class="num">D ms</th><th class="num">sd</th><th class="num">t (4.30 at n = 3)</th><th class="num">store prediction ms (rows x 350 ns)</th></tr>')
            for c in summ["m2_criterion"]:
                pred = c["users"] * 8 * 36 * 350 / 1e6
                P.append(f'<tr><td>{c["tp"]}</td><td>{c["users"]}</td><td class="num">{c["n"]}</td><td class="num">{statistics.mean(c["d_early"]):+.3f}</td><td class="num">{statistics.mean(c["d_late"]):+.3f}</td><td class="num">{c["D_mean"]:+.3f}</td><td class="num">{c["D_sd"]:.3f}</td><td class="num">{"-" if c["t"] is None else f"{c[chr(116)]:+.2f}"}</td><td class="num">{pred:.2f}</td></tr>')
            P.append("</table>")
        rp = os.path.join(RES, "reading.html")
        if os.path.exists(rp):
            P.append(open(rp).read())
    else:
        P.append('<p><b>Pending.</b> The campaign is waiting for the machine (section 7). The micro-benchmark results of section 6 are the only new measurements so far. This section is regenerated by gen_design.py when summary.json and traces/analysis.json exist.</p>')
    # ---------------- section 9: codex comparison
    P.append("""<h2>9. Comparison with the codex design (codex/design/root-cause-tracing.html)</h2>
<p>Codex wrote its design in parallel from the same issue. Both designs agree on the frame: the loss is host-side, the primary comparison is the same source with the layout off and on, and a cause needs a trace signature plus a selective intervention. The lists below record what this design took from codex and where the two differ.</p>
<h3>Taken from codex</h3>
<ul>
<li>Manifest per run (binary hash, commit, env, placement, machine load) and an explicit A/A control arm (vnni2) with interleaved order; codex asks for randomized ABBA blocks, this design alternates the arm order per repetition.</li>
<li>The second-order mechanism (H5): a late upload lengthens the CPU tail of later forwards; the design measures the pending span after burst steps.</li>
<li>Correct the issue's "about 0.3 ms per step at tp4": with per-request rates the CI-layout tp4 loss is 0.82 ms per token and the CI-layout tp2 loss 0.28 ms (codex computed mean(1000 / TPS_i) from the 80 samples per arm; this design's 1000 / mean(TPS) gives 0.825 and 0.285). summarize.py reports both estimators for the new cells.</li>
<li>Token-position modulo 4 (GOF), 16 (block) and 64 (page) analysis of per-step times; trace validity checks (open spans, complete forwards) before durations are compared.</li>
<li>The row-major shadow copy as the strongest selective test of the gather (m5a), instead of a "skip the gather" probe that would feed the card wrong bytes.</li>
<li>rinzler tracing for the CI layout (m6 if needed): codex describes an external Perfetto session plus SIGUSR1 to the exact engine PIDs, with the session length set by the external config; rinzler has no trace flag. The in-process variant (TRACE_FILE + TRON_TRACE_CATEGORIES in the engine's environment) is this design's addition.</li>
</ul>
<h3>Where this design differs, and why</h3>
<ul>
<li><b>Measure first with existing spans and counters, instrument later.</b> Codex proposes a correlation-ID patch (forward, GOF, DMA descriptor identities) and dependency-graph attribution before the first capture. The existing spans (Save K, gof_rodeo, gof_populate, wait_coop_gof, Attention Pending, hw wait) already sit on the three changed operations and were verified in both binaries, so the first capture needs no code change. IDs are added only if the span-level attribution leaves more than 30 % of the budget unexplained.</li>
<li><b>The launch-phase switch (m2) is the cheapest discriminator</b> and is absent from codex: TRON_HWATTN_EARLY_LAUNCH_MIN_B is read at run time [model.hpp:107-128] and moves Save K from before to after the card launch. It separates the store (H1) from the worker-side costs (H2, H3) with no rebuild, and it is a mitigation candidate for the 2-users-per-engine CI cell.</li>
<li><b>The kill-switch arm</b> (codex: "secondary control") is kept in m1 because it settles whether the AMX kernel is involved at all in an FPGA run.</li>
<li><b>perf counters and perf record with sudo</b> (available on 3bda; codex relies on Perfetto only) give the thread class and the symbol without any patch.</li>
<li><b>Micro-benchmark before the traces.</b> Codex allows a gather micro-benchmark at any time, defers only the warm/cold-state and placement sweep to after the trace, and notes that a benchmark cannot establish the root cause by itself. Agreed on the last point; here it cost 5 minutes and already sizes the three costs, so the traces test predictions instead of exploring.</li>
<li><b>Kernel scheduling events</b> (codex) are skipped: they need the daemon backend with a writable tracefs (root) and the question they answer (runnable delay) is not among the hypotheses.</li>
<li><b>Dense AMX page path:</b> codex lists "CPU attention costs more" generically; this design shows the AMX dense kernel does not run in FPGA-attention decode while the software tail stays under one 64-token page (is_dense_amx_page needs a whole software-scored page), so the AMX gain that hid the store cost in CPU-attention runs is absent here.</li>
</ul>""")
    # ---------------- appendix
    P.append("""<h2>Appendix A. Facts this plan rests on</h2>
<table><tr><th>fact</th><th>citation</th></tr>
<tr><td>The FPGA staging path differs from main in exactly three places: the k_head_fn signature gains a scratch argument, populate passes a 2 KiB stack scratch, the scheduler's lambda gathers the row for VNNI slots.</td><td>gof.hpp:78; gof.cpp:203, 213; full.hpp:2644-2661; git diff --numstat c7844ca2ce..30c4ac82cb</td></tr>
<tr><td>gather_row = 4 x _mm512_i32gather_epi32 over 64 lines; scatter_row = 4 x _mm512_i32scatter_epi32 into 64 lines; a token's 128 values sit in 64 lines.</td><td>k_vnni.hpp:135-146, 219-228, 22-30</td></tr>
<tr><td>Decode never shares the K store: k_store_shared needs more than 16 items; store_k_block runs on the calling (main) thread; a run of one token uses set_k_row.</td><td>model.hpp:2806-2814, 3009-3040, 2914-2927; kv_cache.hpp:1701-1711</td></tr>
<tr><td>A GOF fires when its save counter reaches 8 (4 tokens x K and V); the enqueue happens inside Save V; workers drain 4 per operation before run_attention_job; main drains the rest in wait_for_coop_gof before logits.</td><td>gof.hpp:355-366, 47-49; model.hpp:3043-3054, 3110-3123, 3146-3189, 1707-1711; TronCpp.hs:1331-1348</td></tr>
<tr><td>The card launch waits only for the Q channel ("No explicit await on KV DMA here"); DMA completion is polled once per forward at its start.</td><td>self_attention.hpp:634-672; full.hpp:1877; model.hpp:1512; dma_tracker.cpp:83-129</td></tr>
<tr><td>For a decode query the CPU scores only the tail after the last DMA-complete GOF. The engagement point (127 by default; USE_HW_ATTN=N rounds N up to k*128-1) is applied to query positions and to the first shard's DMA-complete extent. At the default it excludes no key: the first shard is pushed only after 32 complete GOFs = 128 tokens, so once it is pushed keys 0-126 are read on the card.</td><td>ranged_mask.cpp:13-96; full.hpp:1936-1966 (query side), 2758-2817 (2771-2775 shard side); model.hpp:2496, 2503; config.hpp:98; shard.hpp:355-365</td></tr>
<tr><td>Early launch for B &gt;= 4 (default), late otherwise; the knob is the environment variable TRON_HWATTN_EARLY_LAUNCH_MIN_B.</td><td>model.hpp:91-137, 2022-2037, 2136-2187; TronCpp.hs:2353-2414</td></tr>
<tr><td>qk_group loads 64 lines per 16-token block with any live token; dotter&lt;bf16,128&gt; loads 4 lines per token.</td><td>k_vnni.hpp:265-306; dotter.hpp:176-226; self_attention.hpp:1604-1641</td></tr>
<tr><td>The kill switch keeps the layout and the qk_group reader; the dotter is compiled out for VNNI slots.</td><td>amx_attn.cpp:59-73; self_attention.hpp:1574-1603; kv_cache.hpp:684-693, 706-712</td></tr>
<tr><td>Prior CPU-attention decode traces: Save K 4.6 to 5.8 us per layer row-major, 28.4 to 34.5 us VNNI, at 8 users; the pass still got shorter because the AMX read gain outweighed it.</td><td>exec/results/vnnik-trace-20260914/analysis.md</td></tr>
<tr><td>Binaries on 3bda: tron-main0916 c7844ca2ce; tron-headoff0916 ff680c8020 TRON_K_VNNI=OFF; tron-pr4424 ff680c8020 ON; tron-tilec 30c4ac82cb ON; all TRON_AMX_DISPATCH=ON, RelWithDebInfo, frame pointers + DWARF-4.</td><td>CMakeCache.txt reads on 3bda 2026-09-18; CMakeLists.txt:598-599</td></tr>
<tr><td>perf works only through sudo -n (paranoid 4; sudo is passwordless); raw events 0xd1/0x2e/0xd3/0xb7 count correctly; IMC aliases are per sub-channel on kernel 6.8.0-138.</td><td>probes on 3bda 2026-09-18 (perf-tooling reader)</td></tr>
</table>
<p class="meta">Generated by exec/issue4500-20260918/gen_design.py. Pure ASCII, light theme.</p>
</main></body></html>""")
    return "\n".join(P)


if __name__ == "__main__":
    h = page()
    bad = [c for c in set(h) if ord(c) > 127]
    if bad:
        for c in bad:
            h = h.replace(c, "&#%d;" % ord(c))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(h)
    print(OUT, len(h), "bytes; non-ascii replaced:", len(bad))
