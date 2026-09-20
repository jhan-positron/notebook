#!/usr/bin/env python3
"""Chart page for the more-testing round-1 results:
PR3879/more-testing/round-1/results.html (light theme, inline SVG, no external
libraries). Reads the same raw results as gen_status.py through resultlib.
"""
import datetime
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resultlib import HOME, RES, MODELS, ARMS, SUBJECTS, SUBJECT_N, load_all, read  # noqa: E402
from mmlu_diff import compare  # noqa: E402

OUT = f"{HOME}/workspace/intel-AMX/PR3879/more-testing/round-1/results.html"
COL = {"off": "#6b6a66", "canon": "#2a78d6", "mirror": "#eb6834", "ci": "#9b9a95", "rep": "#6b6a66"}
LABEL = {"off": "off (AMX kill switch, baseline)", "canon": "canon (AMX, normal K layout)", "mirror": "mirror (AMX + K mirror arena)"}
W = 880


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def nice_ticks(lo, hi, n=5):
    import math
    span = (hi - lo) or 1
    raw = span / (n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    t = math.ceil(lo / step) * step
    out = []
    while t <= hi + 1e-9:
        out.append(round(t, 6)); t += step
    return out


def dotplot(title, rows, xlabel, unit_fmt, band=None, extra_marks=None, takeaway="", delta="pct"):
    """rows: list of (label, {arm: value}) ; extra_marks: {row_label: [(value, kind, tip)]} with kind ci|rep."""
    rowh, left, right, top = 54, 250, 200, 44
    n = len(rows)
    h = top + rowh * n + 60
    vals = [v for _, d in rows for v in d.values() if v is not None]
    for em in (extra_marks or {}).values():
        vals += [v for v, _, _ in em]
    if not vals:
        return f"<p>{esc(title)}: no data yet.</p>"
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.18 or 1
    lo, hi = lo - pad, hi + pad
    if lo < 0 < min(vals): lo = 0
    px = lambda v: left + (v - lo) / (hi - lo) * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{esc(title)}" font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">',
           f'<text x="0" y="20" font-size="15" font-weight="600" fill="#0b0b0b">{esc(title)}</text>']
    for v in nice_ticks(lo, hi):
        x = px(v)
        out.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + rowh * n}" stroke="#e6e5e1" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{top + rowh * n + 18}" font-size="11" fill="#52514e" text-anchor="middle">{unit_fmt(v)}</text>')
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{top + rowh * n + 40}" font-size="12" fill="#52514e" text-anchor="middle">{esc(xlabel)}</text>')
    for i, (label, d) in enumerate(rows):
        y = top + rowh * i + rowh / 2
        out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="12.5" fill="#0b0b0b" text-anchor="end">{esc(label)}</text>')
        off = d.get("off")
        if band and off is not None:
            b0, b1 = px(off - band), px(off + band)
            out.append(f'<rect x="{b0:.1f}" y="{y - 16}" width="{b1 - b0:.1f}" height="32" fill="#2a78d6" opacity="0.14"/>')
        # connector from off to each AMX arm
        for arm in ("canon", "mirror"):
            if off is not None and d.get(arm) is not None:
                out.append(f'<line x1="{px(off):.1f}" y1="{y}" x2="{px(d[arm]):.1f}" y2="{y}" stroke="{COL[arm]}" stroke-width="2" opacity="0.55"/>')
        for v, kind, tip in (extra_marks or {}).get(label, []):
            x = px(v)
            if kind == "ci":
                out.append(f'<circle cx="{x:.1f}" cy="{y}" r="6" fill="#fcfcfb" stroke="{COL["ci"]}" stroke-width="2"><title>{esc(tip)}</title></circle>')
            else:
                out.append(f'<rect x="{x - 5:.1f}" y="{y - 5}" width="10" height="10" fill="#fcfcfb" stroke="{COL["rep"]}" stroke-width="2"><title>{esc(tip)}</title></rect>')
        for arm in ARMS:
            v = d.get(arm)
            if v is None: continue
            x = px(v)
            out.append(f'<circle cx="{x:.1f}" cy="{y}" r="7" fill="#fcfcfb"/><circle cx="{x:.1f}" cy="{y}" r="5.5" fill="{COL[arm]}"><title>{esc(LABEL[arm])}: {unit_fmt(v)}</title></circle>')
        # direct labels: off value below, arms above (staggered)
        if off is not None:
            out.append(f'<text x="{px(off):.1f}" y="{y + 21}" font-size="11" fill="#52514e" text-anchor="middle">{unit_fmt(off)}</text>')
        ups = [(arm, d[arm]) for arm in ("canon", "mirror") if d.get(arm) is not None]
        seen = {unit_fmt(off)} if off is not None else set()
        placed = []
        for arm, v in sorted(ups, key=lambda t: t[1]):
            lab_ = unit_fmt(v)
            if lab_ in seen: continue          # same printed value as an already-labelled mark
            seen.add(lab_)
            dy = -12 if all(abs(px(v) - px(pv)) > 46 for pv in placed) else -24
            placed.append(v)
            out.append(f'<text x="{px(v):.1f}" y="{y + dy}" font-size="11" fill="#0b0b0b" text-anchor="middle">{lab_}</text>')
        # delta annotation at right
        if off:
            if delta == "points":
                parts = [f"{arm} {d[arm] - off:+.2f}" for arm in ("canon", "mirror") if d.get(arm) is not None]
                txt = ", ".join(parts) + " pt" if parts else ""
            else:
                parts = [f"{arm} {100 * (d[arm] - off) / off:+.1f}%" for arm in ("canon", "mirror") if d.get(arm) is not None]
                txt = ", ".join(parts)
            out.append(f'<text x="{W - right + 14}" y="{y + 4}" font-size="11.5" fill="#0b0b0b">{esc(txt)}</text>')
    out.append('</svg>')
    legend = ' &nbsp; '.join(f'<span class="lg"><i style="background:{COL[a]}"></i>{esc(LABEL[a])}</span>' for a in ARMS)
    if extra_marks and any(k == "ci" for em in extra_marks.values() for _, k, _ in em):
        legend += ' &nbsp; <span class="lg"><i class="hollow"></i>CI reference (main branch, 2026-09-04)</span>'
    if extra_marks and any(k == "rep" for em in extra_marks.values() for _, k, _ in em):
        legend += ' &nbsp; <span class="lg"><i class="sq"></i>off arm repeated (A/A control)</span>'
    if band:
        legend += f' &nbsp; <span class="lg"><i style="background:#2a78d6;opacity:.15"></i>&plusmn;{band} point parity band around off</span>'
    return f'<figure>{"".join(out)}<div class="legend">{legend}</div>' + (f'<figcaption>{takeaway}</figcaption>' if takeaway else '') + '</figure>'


def barchart(title, rows, takeaway=""):
    """rows: list of (label, pct_changed, r2w, w2r, color, tip)."""
    rowh, left, right, top = 34, 290, 30, 44
    n = len(rows); h = top + rowh * n + 50
    hi = max(60, max([r[1] for r in rows] + [1]) * 1.3)
    px = lambda v: left + v / hi * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{esc(title)}" font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">',
           f'<text x="0" y="20" font-size="15" font-weight="600" fill="#0b0b0b">{esc(title)}</text>']
    for v in nice_ticks(0, hi):
        x = px(v)
        out.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + rowh * n}" stroke="#e6e5e1" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{top + rowh * n + 18}" font-size="11" fill="#52514e" text-anchor="middle">{v:.0f}%</text>')
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{top + rowh * n + 38}" font-size="12" fill="#52514e" text-anchor="middle">final answers that differ from the off arm (percent of the 1196 questions)</text>')
    for i, (label, pct, r2w, w2r, color, tip) in enumerate(rows):
        y = top + rowh * i + 6
        out.append(f'<text x="{left - 12}" y="{y + 15}" font-size="12" fill="#0b0b0b" text-anchor="end">{esc(label)}</text>')
        out.append(f'<rect x="{left}" y="{y}" width="{px(pct) - left:.1f}" height="20" rx="3" fill="{color}"><title>{esc(tip)}</title></rect>')
        out.append(f'<text x="{px(pct) + 6:.1f}" y="{y + 15}" font-size="11" fill="#0b0b0b">{pct:.1f}%  ({r2w} lost, {w2r} gained, net {w2r - r2w:+d})</text>')
    out.append('</svg>')
    return f'<figure>{"".join(out)}' + (f'<figcaption>{takeaway}</figcaption>' if takeaway else '') + '</figure>'


def linechart(title, series, xlabel, ylabel, takeaway=""):
    """series: list of (name, color, [(x, y)])."""
    left, right, top, bottom = 70, 30, 44, 50
    h = 300
    xs = [x for _, _, pts in series for x, _ in pts]; ys = [y for _, _, pts in series for _, y in pts]
    if not xs:
        return f"<p>{esc(title)}: no data yet.</p>"
    xlo, xhi = 0, max(xs) or 1; ylo, yhi = min(0, min(ys)), max(ys) * 1.1 or 1
    px = lambda x: left + (x - xlo) / (xhi - xlo) * (W - left - right)
    py = lambda y: top + (yhi - y) / (yhi - ylo) * (h - top - bottom)
    out = [f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{esc(title)}" font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">',
           f'<text x="0" y="20" font-size="15" font-weight="600" fill="#0b0b0b">{esc(title)}</text>']
    for y in nice_ticks(ylo, yhi):
        out.append(f'<line x1="{left}" y1="{py(y):.1f}" x2="{W - right}" y2="{py(y):.1f}" stroke="#e6e5e1" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{py(y) + 4:.1f}" font-size="11" fill="#52514e" text-anchor="end">{y:.0f}</text>')
    for x in nice_ticks(xlo, xhi, 7):
        out.append(f'<text x="{px(x):.1f}" y="{h - bottom + 18}" font-size="11" fill="#52514e" text-anchor="middle">{x:.0f}</text>')
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{h - 8}" font-size="12" fill="#52514e" text-anchor="middle">{esc(xlabel)}</text>')
    out.append(f'<text transform="translate(14,{(top + h - bottom) / 2:.1f}) rotate(-90)" font-size="12" fill="#52514e" text-anchor="middle">{esc(ylabel)}</text>')
    for name, color, pts in series:
        d = " ".join(f"{'M' if i == 0 else 'L'}{px(x):.1f},{py(y):.1f}" for i, (x, y) in enumerate(pts))
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><title>{esc(name)}</title></path>')
    out.append('</svg>')
    legend = ' &nbsp; '.join(f'<span class="lg"><i style="background:{c}"></i>{esc(n)} (peak {max(y for _, y in pts):.1f}, end {pts[-1][1]:.1f})</span>' for n, c, pts in series)
    return f'<figure>{"".join(out)}<div class="legend">{legend}</div>' + (f'<figcaption>{takeaway}</figcaption>' if takeaway else '') + '</figure>'


cells, extra, soaks, ci = load_all()
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
short = {mid: lab for mid, lab, _ in MODELS}

# ---- data for figures
tps_rows, ttft_rows, mmlu_rows, mmlu_extra = [], [], [], {}
churn_rows = []
for mid, lab, elig in MODELS:
    tps_rows.append((lab, {a: (cells[(mid, a)]["perf"] or {}).get("tps_mean") for a in ARMS}))
    ttft_rows.append((lab, {a: (cells[(mid, a)]["perf"] or {}).get("ttft_mean_ms") for a in ARMS}))
    mm = {a: (cells[(mid, a)]["mmlu"] or {}).get("overall_pct") if (cells[(mid, a)]["mmlu"] or {}).get("complete") else None for a in ARMS}
    mmlu_rows.append((lab, mm))
    em = []
    cim = ((ci.get("mmlu", {}).get(mid) or {}).get("scores_pct") or {}).get("overall")
    if cim is not None: em.append((cim, "ci", f"CI reference (main branch): {cim:.2f}%"))
    for (emid, elabel), c in extra.items():
        if emid == mid and (c["mmlu"] or {}).get("complete"):
            em.append((c["mmlu"]["overall_pct"], "rep", f"{elabel}: {c['mmlu']['overall_pct']:.2f}%"))
    mmlu_extra[lab] = em
    off = cells[(mid, "off")]
    if (off["mmlu"] or {}).get("complete"):
        for a in ("canon", "mirror"):
            c = cells[(mid, a)]
            if (c["mmlu"] or {}).get("complete"):
                r = compare(f"{off['dir']}/eval_results", f"{c['dir']}/eval_results")
                churn_rows.append((f"{lab.split(' (')[0]}: {a} vs off" + (", no AMX code" if "not eligible" in elig else ""), 100 * r["pred_changed"] / r["n_common"], r["right_to_wrong"], r["wrong_to_right"], COL[a],
                                   f"{r['pred_changed']} of {r['n_common']} answers changed; {r['response_identical']} responses byte-identical"))
        for (emid, elabel), c in extra.items():
            if emid == mid and (c["mmlu"] or {}).get("complete"):
                r = compare(f"{off['dir']}/eval_results", f"{c['dir']}/eval_results")
                churn_rows.append((f"{lab.split(' (')[0]}: off again vs off (A/A)", 100 * r["pred_changed"] / r["n_common"], r["right_to_wrong"], r["wrong_to_right"], COL["off"],
                                   f"{r['pred_changed']} of {r['n_common']} answers changed; {r['response_identical']} responses byte-identical"))

# ---- page
P = []
w = P.append
w(f'''<title>AMX round-1 CI tests</title>
<style>
body{{background:#fcfcfb;color:#0b0b0b;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:14.5px;line-height:1.5;max-width:920px;margin:0 auto;padding:24px 20px 60px}}
h1{{font-size:24px;margin:0 0 6px}} h2{{font-size:18px;margin:34px 0 8px;border-bottom:1px solid #e6e5e1;padding-bottom:4px}} h3{{font-size:15.5px;margin:22px 0 6px}}
figure{{margin:14px 0 26px;padding:12px 12px 8px;border:1px solid #e6e5e1;border-radius:8px;background:#fff}}
figcaption{{font-size:13.5px;color:#0b0b0b;margin-top:6px;padding-top:6px;border-top:1px solid #f0efec}}
.legend{{font-size:12px;color:#52514e;margin-top:4px}} .lg i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}}
.lg i.hollow{{border:2px solid #9b9a95;width:8px;height:8px;background:#fff}} .lg i.sq{{border:2px solid #6b6a66;border-radius:0;width:7px;height:7px;background:#fff}}
table{{border-collapse:collapse;font-size:12.5px;margin:8px 0 14px;display:block;overflow-x:auto;max-width:100%}} th,td{{border:1px solid #e6e5e1;padding:4px 8px;text-align:right;white-space:nowrap}} th{{background:#f5f4f1;font-weight:600}} td:first-child,th:first-child{{text-align:left}}
.short{{background:#f5f4f1;border-radius:8px;padding:12px 16px;margin:12px 0 18px}} .muted{{color:#52514e}} code{{background:#f0efec;padding:1px 4px;border-radius:3px;font-size:12.5px}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:13.5px}} dt{{font-weight:600}} dd{{margin:0}}
</style>
<h1>AMX change (PR3879) under the nightly CI tests, round 1</h1>
<p class="muted">Generated {now} by <code>exec/more-testing-r1/gen_results_html.py</code>. Companion to <code>status.md</code> (the record) and <code>../test-plan.md</code> (the plan). Raw data: <code>exec/results/more-testing-r1/</code>.</p>''')

done = sum(1 for c in cells.values() if c["status"] == "done")
w('<div class="short"><b>Short version.</b> ')
w(f'The nightly CI\'s four test kinds (functional API tests, throughput benchmark, MMLU Pro accuracy, soak) were run against rinzler built from the PR3879 branch on four models in three arms (off, canon, mirror; defined below); {done} of 12 model-and-arm combinations (cells) and the 60-minute soak completed. ')
w('Every functional test passed identically in all arms; decode throughput (tokens generated per second after the prompt) rose by 14 to 19% on llama-3.1-8b and 4.5 to 5.5% on qwen-3-4b with AMX on, and did not change on mixtral; MMLU Pro scores moved by -0.4 to +1.5 points, while a repeat of the off arm with nothing changed moved by +1.7 points, so no accuracy change is detectable. ')
w('Two findings need follow-up: the mirror arm is 13% slower to first token than off on qwen and llama (24% and 17% slower than canon), and its K mirror arena grows host RAM by about half the KV cache size (about 40 GiB in the soak), which the CI soak monitor reports as an error (5 GiB threshold).</div>')

w('<h2>Words used here</h2><dl>')
for t, d in [("tron / rinzler / runtron", "tron is the inference engine under test; rinzler is its production HTTP server; runtron is tron's command-line tool used by the earlier decode-only rounds. The off and canon arms run the same binary (rinzler.canon, with and without the kill switch); the mirror arm runs a second build (rinzler.mirror) of the same source, PR3879 head 60d66d9c04."),
             ("K / KV cache / KV head / head size / FPGA", "for every served token the server stores the attention keys (K) and values (V); this store is the KV cache, kept in hugepages. A KV head is one stored key/value stream shared by several query heads; head size is the vector width of one attention head; the change's kernels exist only for head size 128 with 4 query heads per KV head (qwen, llama, mixtral), never for gpt-oss (64 and 8). FPGA = the accelerator cards this machine runs the models' matrix work on."),
             ("cell / prefill / decode / greedy decoding / chain-of-thought / sd", "cell = one model run in one arm. Prefill = processing the prompt (measured by TTFT); decode = generating tokens after it (measured by TPS). Greedy decoding = always taking the highest-scoring next token, so a tiny numeric difference early in an answer can change the rest of the text. Chain-of-thought = the reasoning text the model writes before its final letter. sd = standard deviation of the 80 per-user-per-round TPS samples inside one run."),
             ("AMX", "Intel Advanced Matrix Extensions, the CPU tile-matrix instructions the change uses for software attention; AVX is the older vector path."),
             ("off / canon / mirror", "off = the normal build of the branch (rinzler.canon) started with TRON_AMX_DISABLE=1, the kill switch, so attention runs on the AVX path; canon = the same binary with the switch unset, AMX kernels read the normal K layout; mirror = a second build that also keeps an AMX-friendly copy of K in ordinary RAM (the K mirror arena). The switch state is recorded by the launcher, not by the server."),
             ("USE_HW_ATTN=0", "forces attention onto the CPU for all models in all arms; otherwise the ingested models (qwen, gpt-oss) run attention on the FPGA and AMX never engages."),
             ("tp2 / tp4", "tensor parallelism, the number of FPGA cards one model instance spans (CI's choice per model was kept)."),
             ("TPS", "per-user generated tokens per second in the CI perf benchmark (8 users, 1024-token prompt, 1536 generated tokens, 10 rounds)."),
             ("TTFT", "time to first token in milliseconds in the same benchmark (mostly the prompt prefill with 8 requests arriving together)."),
             ("MMLU Pro", "multiple-choice knowledge test; CI setting = the first 10% of every subject, a fixed set of 1196 questions, chain-of-thought answers at temperature 0, 8 parallel requests. Score = percent correct."),
             ("answer churn / A/A control", "share of the questions answered by both runs whose extracted final letter differs (qwen and llama 1196, mixtral 1195, gpt-oss 1186); scores in the tables come from the CI runner, which credits a seeded random guess for a response with no extractable letter, so the net of the churn table can differ from the score difference by a few questions. A/A control = the same binary with the same switches run a second time, which measures the run-to-run spread of the serving path (8 requests batched in changing order)."),
             ("soak", "sustained mixed traffic from simulated users for a fixed time while a monitor records errors, host memory, power, and a coherency probe (is the answer to a fixed prompt still sensible)."),
             ("CI reference", "the nightly run of 2026-09-04 (GitHub Actions 33833914529, tron 2026.09.04-fe8dbdee, main branch). Its client ran on another host through the platformd proxy over 2 to 4 engines; ours ran on the DUT against one engine, so CI throughput and TTFT are not directly comparable and are kept to the tables.")]:
    w(f'<dt>{esc(t)}</dt><dd>{esc(d)}</dd>')
w('</dl>')

w('<h2>1. Decode throughput (CI perf benchmark)</h2>')
w(dotplot("Per-user decode throughput at 8 users, one engine", tps_rows, "tokens per second per user (higher is better)", lambda v: f"{v:.0f}",
          takeaway="Take-away: AMX raises decode throughput on the eligible models (qwen +4.5/+5.5%, llama +14/+19%). Mixtral (-0.2/+0.2%) and gpt-oss canon (+2.0%) are within the run-to-run spread: the qwen off arm run twice differed by 2.2% (77.8 vs 76.1 tok/s), so differences under about 2% are not resolved by one run per arm. gpt-oss mirror (+3.6%) is outside the plan's +/-3% band and is not resolved either way: no AMX or arena code runs for this model, but its within-run spread is three times qwen's and no gpt-oss arm was repeated. Gains are smaller than in the earlier runtron rounds, which measured decode alone, because this benchmark uses a prompt of about 1000 tokens and generates up to 1536 tokens."))
w('<h2>2. Time to first token (same benchmark)</h2>')
w(dotplot("Mean time to first token at 8 users, one engine", ttft_rows, "milliseconds (lower is better)", lambda v: f"{v:.0f}",
          takeaway="Take-away (deltas printed on the figure are against off): canon is faster to first token than off (-4 to -9%); mirror is 13% slower than off on qwen and llama (24% and 17% slower than canon) in every one of the 10 rounds, while TTFT reproduces to 0.2% between identical runs; mixtral and gpt-oss show no difference (gpt-oss allocates no mirror). Hypotheses, not tested here: (A) the K write into the mirror arena sits on the prefill critical path for qwen and llama but is hidden behind FPGA time on mixtral, which writes the same K bytes per token as llama; (B) a mirror-layout read cost in prefill attention. Round 2: single-user prefill time versus prompt length, canon vs mirror."))
w('<h2>3. MMLU Pro accuracy</h2>')
w(dotplot("MMLU Pro, percent correct on the fixed 1196-question set", mmlu_rows, "percent correct (right-hand deltas in points = percentage-point difference to the off arm)", lambda v: f"{v:.1f}", band=1.0, extra_marks=mmlu_extra, delta="points",
          takeaway="Take-away: the AMX arms move the score by -0.4 to +1.5 points; the square marker on the qwen row is the off arm run a second time with nothing changed (+1.7 points versus the first off run), so a move of that size is run-to-run spread of this serving path, not an AMX effect. Scores are the CI runner's totals; the gpt-oss arms answered 1194 and 1188 questions (empty completions excluded), the others 1195 to 1196. The hollow circles are the CI reference from the main branch (2 to 4 engines; FPGA attention for qwen and gpt-oss)."))
if churn_rows:
    w('<h2>4. Answer churn between arms</h2>')
    w(barchart("Share of final answers that differ from the off arm", churn_rows,
               takeaway="Lost = a question the off arm got right and the other run got wrong; gained = the reverse; counts use the letters actually extracted over the questions both runs answered. Take-away: even where no AMX kernel and no arena runs (gpt-oss, two builds compared) about 10% of final answers differ between two runs, because 8 concurrent requests are batched in changing order and the floating-point reduction order follows. The repeated off arm on qwen (same binary, same switches: the only true A/A control) churns 16.3% of answers, the same as the AMX arms (15.6%); the net score movement is the residue of many flips in both directions."))

sk, smeta, sstat = soaks["main"]
w('<h2>5. Soak (60 minutes, 25 users, mirror arm, two models on one tp2 engine)</h2>')
if sk and not sk.get("raw"):
    series = [("host used-memory growth (GiB)", COL["off"], sk["growth_series"])]
    if sk.get("arena_series"):
        series.append(("K mirror arena (server's GB value converted to GiB)", COL["mirror"], [(t, a / 1.073741824) for t, _, a in sk["arena_series"]]))
    for tag, (sk2, m2, st2) in soaks.items():
        if tag != "main" and sk2 and not sk2.get("raw") and sk2.get("growth_series"):
            series.append((f"host used-memory growth, {m2.get('arm', tag)} arm ({m2.get('minutes', '?')} min)", "#9b9a95", sk2["growth_series"]))
    w(linechart("Host memory growth during the soak, and the server's own mirror-arena footprint", series, "minutes since the soak started", "GiB",
                takeaway="Take-away: host used-memory growth (whole host, hugepages excluded) is 0.84 to 0.92 of the K mirror arena footprint at every mark (16.6 vs 19.7 GiB at 10 min, 31.1 vs 34.7 at 20 min, 39.7 vs 43.1 at 30 min, 33.2 vs 36.5 at the end), rises while the KV cache fills, then moves between 36 and 42 GiB as pages are freed and refilled. The arena is large enough to account for all of the growth; the 3 to 4 GiB of footprint not visible as used memory is unexplained (the monitor's per-process figure read 0 because it targets the production units). The off-arm soak with the same traffic grew -0.2 GiB. So the growth is a bounded property of the mirror arm (about half the KV cache size in ordinary RAM), not a leak, but CI's soak monitor flags any growth above 5 GiB as an error."))
    w('<table><tr><th>Model</th><th>Requests sent / completed / failed (a request still running at the cutoff is neither)</th><th>Avg TTFT [s]</th><th>Total generation [tok/s]</th><th>Per-user generation [tok/s]</th></tr>')
    for mname, v in sk["models"].items():
        w(f'<tr><td>{esc(mname)}</td><td>{v.get("sent")} / {v.get("succeeded")} / {v.get("failed")}</td><td>{fmt(v.get("avg_ttft_s"))}</td><td>{fmt(v.get("total_gen_tok_s"))}</td><td>{fmt(v.get("per_user_gen_tok_s"))}</td></tr>')
    w('</table>')
    w(f'<p>Coherency probes: {sk["coherency_checks"]}, failures {sk["coherency_failures"]}. The harness (soak.py) counted {sk.get("errors")} error(s): the memory-growth alert; 0 failed requests. Exit: {esc(sk.get("exit_reason") or "n/a")}.</p>')
    for tag, (sk2, m2, st2) in soaks.items():
        if tag != "main" and sk2 and not sk2.get("raw"):
            w(f'<p>Off-arm baseline soak (`{tag}`, {m2.get("minutes")} min, {m2.get("users")} users, same models): host memory growth {sk2.get("growth_gib"):.1f} GiB at the end, harness error count {sk2.get("errors")}, coherency probes {sk2["coherency_checks"]} with {sk2["coherency_failures"]} failures; requests ' + "; ".join(f'{k}: {v.get("sent")} sent / {v.get("succeeded")} completed / {v.get("failed")} failed' for k, v in sk2["models"].items()) + '.</p>')
else:
    w(f'<p>Soak status: {esc(sstat)}.</p>')

w('<h2>6. The record: per-model tables</h2>')
for mid, lab, elig in MODELS:
    w(f'<h3>{esc(lab)}: <code>{esc(mid)}</code> ({esc(elig)})</h3>')
    ciperf = (ci.get("perf", {}).get(mid) or [{}])[-1]; cimmlu = ci.get("mmlu", {}).get(mid, {})
    w('<table><tr><th>Arm</th><th>Status</th><th>Functional pass/skip/fail</th><th>TPS mean (sd)</th><th>TPS vs off</th><th>TTFT [ms]</th><th>MMLU Pro [%]</th><th>MMLU vs off [points]</th></tr>')
    w(f'<tr><td>CI reference (main, 2-4 engines)</td><td>2026-09-04</td><td>group totals only</td><td>{fmt(ciperf.get("tps"))}</td><td>n/a</td><td>{ciperf.get("ttft_ms", "n/a")}</td><td>{fmt((cimmlu.get("scores_pct") or {}).get("overall"))}</td><td>n/a</td></tr>')
    off = cells[(mid, "off")]
    rows = [(a, cells[(mid, a)]) for a in ARMS] + [(lbl, c) for (emid, lbl), c in extra.items() if emid == mid]
    for name, c in rows:
        f, p, m = c["functional"], c["perf"], c["mmlu"]
        fcol = f"{f['passed']}/{f['skipped']}/{f['failed']}" if f else "n/a"
        tps = f"{p['tps_mean']:.2f} ({p['tps_std_dev']:.2f})" if p else "n/a"
        dtps = (f"{100 * (p['tps_mean'] - off['perf']['tps_mean']) / off['perf']['tps_mean']:+.1f}%" if (p and off["perf"] and name != "off") else ("baseline" if name == "off" and p else "n/a"))
        mm = f"{m['overall_pct']:.2f}" if (m and m.get("complete")) else ("not planned" if c["meta"].get("run_mmlu") is False and c["status"] == "done" else "n/a")
        dm = (f"{m['overall_pct'] - off['mmlu']['overall_pct']:+.2f}" if (m and m.get("complete") and name != "off" and off["mmlu"] and off["mmlu"]["complete"]) else ("baseline" if name == "off" and m and m.get("complete") else "n/a"))
        w(f'<tr><td>{esc(name)}</td><td>{esc(c["status"])}</td><td>{esc(fcol)}</td><td>{tps}</td><td>{dtps}</td><td>{p["ttft_mean_ms"] if p else "n/a"}</td><td>{mm}</td><td>{dm}</td></tr>')
    w('</table>')
    subj_rows = []
    if cimmlu.get("scores_pct"): subj_rows.append(("CI reference", [cimmlu["scores_pct"].get(s) for s in SUBJECTS], (cimmlu.get("scores_pct") or {}).get("overall")))
    for name, c in rows:
        m = c["mmlu"]
        if m and m.get("per_subject"):
            subj_rows.append((name, [100.0 * m["per_subject"][s]["acc"] if s in m["per_subject"] else None for s in SUBJECTS], m["overall_pct"]))
    if subj_rows:
        w('<table><tr><th>MMLU Pro per subject [%]</th><th>overall</th>' + ''.join(f'<th>{esc(s)}<br><span class="muted">n={n}</span></th>' for s, n in zip(SUBJECTS, SUBJECT_N)) + '</tr>')
        for name, vals, over in subj_rows:
            w(f'<tr><td>{esc(name)}</td><td>{fmt(over)}</td>' + ''.join(f'<td>{fmt(v, 2)}</td>' for v in vals) + '</tr>')
        w('</table>')

w('<h2>7. Method and known differences from CI</h2><ul>')
for t in ["One rinzler process per cell on delphi-3bda (port 13100) with the same card, core and hugepage arguments platformd gives production engines (tp2: 2 cards, 128 hugepages; tp4: 4 cards, 256 hugepages); production serving was stopped per the standing policy while the machine was idle after the nightly.",
          "Test client = systems_test 470aca1 (the CI repository) in a local venv on the DUT; its CI reporting library was replaced by a no-op stub so nothing was written to the CI database. CI's client runs on another host through the platformd proxy over 2 to 4 engines, so CI throughput and TTFT are not directly comparable; the arm-to-arm comparison on one engine is the controlled one.",
          "MMLU Pro used the repository's detached runner (same prompts, sampling and 8-way parallelism as the nightly; request timeout raised from 60 s to 180 s because one engine serves all 8 questions). Functional = the CI pytest suite; the two proxy-authentication tests skip themselves when the Server header starts with drogon/ (rinzler's own HTTP server), in our cells and, by CI's pytest progress output, in both CI groups too. Perf = the CI benchmark code with each model's CI parameters. Soak = the CI soak script with 25 users for 60 minutes (CI: 100 users over 4 engines for 3 hours).",
          "Every arm runs USE_HW_ATTN=0 (CPU attention). In CI the ingested models (qwen, gpt-oss) run attention on the FPGA; llama and mixtral run CPU attention in CI too.",
          "Off arm = kill switch on the canonical binary; the August three-binary round showed the kill-switch arm within 0-3% of a clean AVX build. The switch state is set by the launcher (rz.sh) and recorded in each cell's meta.json; rinzler does not log it."]:
    w(f'<li>{esc(t)}</li>')
w('</ul>')
notes = read(f"{RES}/notes.md")
if notes:
    w('<h2>8. Notes from the analyst (dated, hand-written)</h2><ul>')
    for line in notes.splitlines():
        if line.startswith("- "): w(f'<li>{esc(line[2:])}</li>')
    w('</ul>')
open(OUT, "w").write("\n".join(P) + "\n")
print(f"wrote {OUT} ({os.path.getsize(OUT)} bytes)")
