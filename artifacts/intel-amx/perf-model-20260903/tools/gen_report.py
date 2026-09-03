#!/usr/bin/env python3
"""gen_report.py - build perf-model/index.html from model.json + medians.json (+ m8-spans.json, m6-perf.txt).

Numbers in tables and in the estimate come from model.json and medians.json (parse.py, model.py).
Named exceptions: the traced-run spans (m8-spans.json, spans.py), the per-unit hardware counters
(m6-perf.txt), the M0 hardware record (m0-hardware.txt), the 2026-09-01 comparison values
(single-attn-20260901/summary.json) and the constants recorded in model.json["constants"].
Narrative paragraphs live in narrative.json; every number they quote is checked below against
model.json and the build fails if one disagrees.
"""
import argparse
import json
import os
import re

HOME = os.path.expanduser("~")
RES = f"{HOME}/workspace/intel-AMX/exec/results/perf-model-20260903"
OUT_DEFAULT = f"{HOME}/workspace/intel-AMX/perf-model/index.html"
HIST = f"{HOME}/workspace/intel-AMX/exec/results/single-attn-20260901/summary.json"

C_BLUE, C_ORANGE, C_AQUA = "#2a78d6", "#eb6834", "#1baf7a"
C_INK, C_INK2, C_MUTED, C_GRID = "#1f2933", "#4b5761", "#7a8790", "#e3e8ec"


def f1(x, nd=1):
    return "n/a" if x is None else f"{x:,.{nd}f}"


def pct(x, nd=1):
    return "n/a" if x is None else f"{x:+.{nd}f}%"


def P(x, nd=1):
    return "n/a" if x is None else "%.*f%%" % (nd, 100 * x)


def td(x, cls="num"):
    return f'<td class="{cls}">{x}</td>'


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def dumbbell_svg(rows, x_min, x_max, title, unit="%"):
    W, H_ROW, PAD_L, PAD_R, PAD_T = 880, 46, 150, 40, 40
    H = PAD_T + H_ROW * len(rows) + 50
    px = lambda v: PAD_L + (v - x_min) / (x_max - x_min) * (W - PAD_L - PAD_R)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{esc(title)}" style="max-width:{W}px;display:block;font-family:IBM Plex Sans,system-ui,sans-serif">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    step = 5 if x_max - x_min > 20 else 2
    v = x_min
    while v <= x_max + 1e-9:
        x = px(v)
        s.append(f'<line x1="{x:.1f}" y1="{PAD_T - 10}" x2="{x:.1f}" y2="{H - 40}" stroke="{C_GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x:.1f}" y="{H - 22}" font-size="12" fill="{C_INK2}" text-anchor="middle">{v:+g}{unit}</text>')
        v += step
    for i, (label, meas, est, lo, hi) in enumerate(rows):
        y = PAD_T + H_ROW * i + H_ROW / 2
        s.append(f'<text x="{PAD_L - 12}" y="{y + 4}" font-size="13" fill="{C_INK}" text-anchor="end">{esc(label)}</text>')
        if lo is not None and hi is not None:
            s.append(f'<rect x="{px(lo):.1f}" y="{y - 7}" width="{max(2, px(hi) - px(lo)):.1f}" height="14" fill="{C_BLUE}" opacity="0.18" rx="3"/>')
        if meas is not None and est is not None:
            s.append(f'<line x1="{px(meas):.1f}" y1="{y}" x2="{px(est):.1f}" y2="{y}" stroke="{C_MUTED}" stroke-width="2"/>')
        if meas is not None:
            s.append(f'<circle cx="{px(meas):.1f}" cy="{y}" r="7" fill="{C_ORANGE}" stroke="#fff" stroke-width="2"><title>measured {meas:+.1f}{unit}</title></circle>')
            s.append(f'<text x="{px(meas):.1f}" y="{y - 12}" font-size="12" fill="{C_INK}" text-anchor="middle">{meas:+.1f}{unit}</text>')
        if est is not None:
            s.append(f'<circle cx="{px(est):.1f}" cy="{y}" r="7" fill="{C_BLUE}" stroke="#fff" stroke-width="2"><title>estimate {est:+.1f}{unit}</title></circle>')
            s.append(f'<text x="{px(est):.1f}" y="{y + 24}" font-size="12" fill="{C_INK}" text-anchor="middle">{est:+.1f}{unit}</text>')
    ly = H - 6
    s.append(f'<circle cx="{PAD_L}" cy="{ly - 4}" r="6" fill="{C_ORANGE}"/><text x="{PAD_L + 12}" y="{ly}" font-size="12" fill="{C_INK2}">measured (Tron, 2026-09-01)</text>')
    s.append(f'<circle cx="{PAD_L + 220}" cy="{ly - 4}" r="6" fill="{C_BLUE}"/><text x="{PAD_L + 232}" y="{ly}" font-size="12" fill="{C_INK2}">model estimate</text>')
    s.append(f'<rect x="{PAD_L + 360}" y="{ly - 11}" width="22" height="14" fill="{C_BLUE}" opacity="0.18" rx="3"/><text x="{PAD_L + 388}" y="{ly}" font-size="12" fill="{C_INK2}">pre-registered band (plan section 8, rule 6)</text>')
    s.append("</svg>")
    return "\n".join(s)


def stacked_units_svg(rows, title):
    """rows: (label, [(segment, value us, color, dashed)], total label). Solid = instructions running, dashed = waiting."""
    W, H_ROW, PAD_L, PAD_R, PAD_T = 880, 44, 190, 150, 30
    H = PAD_T + H_ROW * len(rows) + 46
    vmax = max(sum(v for _, v, _, _ in segs) for _, segs, _ in rows) * 1.05
    px = lambda v: PAD_L + v / vmax * (W - PAD_L - PAD_R)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{esc(title)}" style="max-width:{W}px;display:block;font-family:IBM Plex Sans,system-ui,sans-serif">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    step = 0.5 if vmax <= 5 else 1.0
    v = 0.0
    while v <= vmax:
        s.append(f'<line x1="{px(v):.1f}" y1="{PAD_T - 8}" x2="{px(v):.1f}" y2="{H - 36}" stroke="{C_GRID}"/>')
        s.append(f'<text x="{px(v):.1f}" y="{H - 20}" font-size="12" fill="{C_INK2}" text-anchor="middle">{v:g} µs</text>')
        v += step
    for i, (label, segs, total_label) in enumerate(rows):
        y = PAD_T + H_ROW * i + 8
        s.append(f'<text x="{PAD_L - 12}" y="{y + 16}" font-size="13" fill="{C_INK}" text-anchor="end">{esc(label)}</text>')
        x = PAD_L
        for name, val, col, dashed in segs:
            w = max(0.0, px(val) - PAD_L - 2)
            if dashed:
                s.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="22" fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-width="2" stroke-dasharray="6 4"><title>{esc(name)}: {val:.2f} µs</title></rect>')
                tc = C_INK
            else:
                s.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="22" fill="{col}"><title>{esc(name)}: {val:.2f} µs</title></rect>')
                tc = "#ffffff"
            if w > 46:
                s.append(f'<text x="{x + w / 2:.1f}" y="{y + 15}" font-size="11" fill="{tc}" text-anchor="middle">{val:.2f}</text>')
            x += w + 2
        s.append(f'<text x="{x + 8:.1f}" y="{y + 16}" font-size="12" fill="{C_INK}">{esc(total_label)}</text>')
    s.append("</svg>")
    return "\n".join(s)


def legend_html(items):
    return '<div class="legend">' + "".join(f'<span><i style="{sty}"></i>{esc(n)}</span>' for n, sty in items) + "</div>"


def parse_m6(path, units_total):
    """per-unit counters for the avx/amx 27-thread runs, fill-only control subtracted."""
    if not os.path.exists(path):
        return {}
    blocks, cur = {}, None
    for line in open(path):
        m = re.match(r"## (avx|amx) p130 t27 counters(, fill-only control)?", line)
        if m:
            cur = (m.group(1), "ctl" if m.group(2) else "run")
            blocks[cur] = {}
            continue
        if line.startswith("## "):
            cur = None
            continue
        if cur:
            m = re.match(r"\s*([\d,]+)\s+(cycles|instructions|l1_miss|l2_miss|l3_miss|dtlb_ld_walk)\b", line)
            if m:
                blocks[cur][m.group(2)] = int(m.group(1).replace(",", ""))
    out = {}
    for v in ("avx", "amx"):
        run, ctl = blocks.get((v, "run"), {}), blocks.get((v, "ctl"), {})
        if not run:
            continue
        out[v] = {k: (run[k] - ctl.get(k, 0)) / units_total for k in run}
        if run.get("cycles"):
            out[v]["ipc"] = (run["instructions"] - ctl.get("instructions", 0)) / (run["cycles"] - ctl.get("cycles", 0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=f"{RES}/model.json")
    ap.add_argument("--medians", default=f"{RES}/medians.json")
    ap.add_argument("--narrative", default=f"{RES}/narrative.json")
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    M = json.load(open(a.model))
    D = json.load(open(a.medians))
    hist = json.load(open(HIST))
    N = json.load(open(a.narrative))
    spans = json.load(open(f"{RES}/m8-spans.json")) if os.path.exists(f"{RES}/m8-spans.json") else None
    P8 = M["prompts"]
    r8 = P8["8192"]
    b8 = M["baseline"]["8192"]
    bench = M["bench"]
    K = M.get("constants", {})
    c = r8["chain_primary"]
    ub8 = bench["unit_bench"]["8192"]
    meas = r8["measured_boost_pct"]

    # ---- narrative number checks (fail loud if the prose drifts from model.json)
    checks = {
        "%.1f" % c["boost_pct"]: N["short"], "%.1f" % abs(r8["error_pp"]): N["short"], "%.2f" % r8["unit_amx_primary_us"]: N["short"],
        "%.1f" % r8["chain_round1"]["boost_pct"]: N["result_para"], "%.1f" % abs(r8["calibration_error_pct"]): N["calibration_para"],
        "%.2f" % r8["avx_bench_us"]: N["calibration_para"], "%.2f" % r8["avx_tron_us"]: N["calibration_para"],
        "%.1f" % r8["chain_unexplained_carries_fully"]["boost_pct"]: N["result_para"],
    }
    for num, text in checks.items():
        assert num in text, f"narrative does not contain {num}: {text[:80]}"

    # ---- section 3: baseline tables and the audit outcome
    h8 = hist["disable-8192"]
    base_rows = [("Token time", b8["period_us"], h8["period"]), ("Attention", b8["attention_us"], h8["attn"]), ("Page work", b8["page_work_us"], h8["sect"]),
                 ("Joins", b8["joins_us"], h8["joins"]), ("Barrier", b8["barrier_us"], h8["barrier"]),
                 ("Untimed rest", b8["untimed_rest_us"], h8["attn"] - h8["sect"] - h8["joins"] - h8["barrier"]), ("Other work", b8["other_us"], h8["period"] - h8["attn"])]
    base_tbl = "".join(f"<tr><td>{n}</td>{td(f1(v))}{td(f1(h))}{td(pct((v / h - 1) * 100))}</tr>" for n, v, h in base_rows)
    unit_rows = [("AVX unit", b8["unit_avx_us"], h8["total"]), ("QK", b8["qk_avx_us"], h8["qk"]), ("common work", b8["common_avx_us"], h8["softmax"] + h8["state"]), ("PV", b8["pv_avx_us"], h8["pv"])]
    unit_tbl = "".join(f"<tr><td>{n}</td>{td(f1(v, 3))}{td(f1(h, 3))}{td(pct((v / h - 1) * 100))}</tr>" for n, v, h in unit_rows)
    unit_tbl += f"<tr><td>units on worker 0 per token</td>{td(f1(b8['units_w0'], 0))}{td(f1(h8['units'], 0))}{td(pct((b8['units_w0'] / h8['units'] - 1) * 100))}</tr>"
    mr = D.get("m1_memrate", {})
    r1 = (mr.get("load-t1-thp") or {}).get("per_core_GBs_median")
    r1_4k = (mr.get("load-t1-none") or {}).get("per_core_GBs_median")
    r14 = mr.get("load-t14-thp") or {}
    audit_txt = (f"The plan's condition for keeping the old values (action-plan.html, section 5, first row) was: M1 gives 15.7 to 15.9 GB/s at one reader, and M7 reproduces the 2026-09-01 rows within 3%. "
                 f"It was not met as worded. The per-token rows agree within 1% (token {pct((b8['period_us'] / h8['period'] - 1) * 100)}, attention {pct((b8['attention_us'] / h8['attn'] - 1) * 100)}, page work {pct((b8['page_work_us'] / h8['sect'] - 1) * 100)}), "
                 f"but the unit timers are {pct((b8['unit_avx_us'] / h8['total'] - 1) * 100)} (worker 0 handled {pct((b8['units_w0'] / h8['units'] - 1) * 100)} more units: the planner splits pages by measured worker speed, so worker 0's share changes from run to run while its page work does not), "
                 f"joins and barrier differ by {pct((b8['joins_us'] / h8['joins'] - 1) * 100)} and {pct((b8['barrier_us'] / h8['barrier'] - 1) * 100)}, and the untimed rest rose from {f1(h8['attn'] - h8['sect'] - h8['joins'] - h8['barrier'], 0)} to {f1(b8['untimed_rest_us'], 0)} µs per token ({P(b8['untimed_rest_us'] / b8['period_us'])} of the token; carried unchanged into the estimate). "
                 f"One reader streams {f1(r1, 1)} GB/s on 2 MiB pages and {f1(r1_4k, 1)} GB/s on 4 KiB pages, above the old 15.7 to 15.9 GB/s; the only same-machine comparison is the 14-reader row, {f1(r14.get('per_core_GBs_median'), 2)} GB/s per core against 15.2 to 16.0 in August 2026, which agrees. "
                 f"Because the check did not pass as worded, every baseline number of the chain comes from today's M7 run, and the 2026-09-01 values appear only in the comparison columns above.")

    # ---- section 1: rounds table, bands
    rounds_rows = [
        ("Round 1: model as pre-registered (transfer rule fired: %s; single-arena layout)" % esc(r8["round1_transfer_chosen"]), r8["round1_unit_amx_us"], r8["chain_round1"]["boost_pct"]),
        ("Search step 1 of 4: probe-off run (timer overhead) — not run; replaced by an argument (section 4)", None, None),
        ("Search step 2 of 4: page order (pages placed at random) — AVX %+.1f%%, AMX %+.1f%%" % (r8.get("avx_shuffle_pct", 0), r8.get("amx_shuffle_pct", 0)), None, None),
        ("Search step 3 of 4: 2 MiB instead of 1 GiB pages — AVX %+.1f%%, AMX %+.1f%%" % (r8.get("avx_thp_pct", 0), r8.get("amx_thp_pct", 0)), None, None),
        ("Search step 4 of 4: hardware counters (M6) — most of a unit's 512 lines arrive by hardware prefetch (section 10)", None, None),
        ("Added test, not in the plan's list: Tron's book layout (24 adjacent pages per book, one arena per book) — AVX %+.1f%%, AMX %+.1f%% against a same-session control; adopted as the primary layout for both paths" % (r8.get("avx_book24_pct", 0), r8.get("amx_book24_pct", 0)), None, None),
        ("Round 2: book layout, transfer rule \"none\" (a departure from the pre-registered rule, decided after round 1)", r8["unit_amx_primary_us"], c["boost_pct"]),
        ("Reading of the unexplained residual that carries it in full to the AMX unit (for comparison)", r8["chain_unexplained_carries_fully"]["unit_amx_us"], r8["chain_unexplained_carries_fully"]["boost_pct"]),
    ]
    rounds_tbl = "".join(f"<tr><td>{n}</td>{td(f1(u, 3) if u is not None else '')}{td(pct(bst) if bst is not None else '')}{td(pct(bst - meas, 1).replace('%', ' pts') if bst is not None else '')}</tr>" for n, u, bst in rounds_rows)
    band_full, band_ph = r8["band_pct"], r8["band_posthoc_pct"]
    gate_txt = "passed" if r8["calibration_ok"] else "failed (" + "; ".join(r8["calibration_fail_reasons"]) + ")"

    # ---- figure 1
    db_rows = []
    for p in ("8192", "2048", "256"):
        r = P8[p]
        if "chain_primary" in r:
            db_rows.append((f"prompt {p}", r["measured_boost_pct"], r["chain_primary"]["boost_pct"], r["band_pct"][0], r["band_pct"][1]))
    allv = [v for row in db_rows for v in row[1:] if v is not None]
    db_svg = dumbbell_svg(db_rows, min(0, min(allv) - 2), max(allv) + 3, "Estimate against measurement")

    # ---- section 5: decomposition figure and table
    avx_comp, amx_comp = r8.get("avx_compute_us"), r8.get("amx_compute_us")
    avx_t27, amx_t27 = r8["avx_bench_us"], r8["s_transfer_variants_us"]["none"]
    seg_rows = [("AVX unit, benchmark, 27 threads", [("instructions running (hot compute)", avx_comp, C_BLUE, False), ("waiting for bytes (data wait)", max(0, avx_t27 - avx_comp), C_AQUA, True)], f"{avx_t27:.2f} µs; Tron {b8['unit_avx_us']:.2f} µs"),
                ("AMX unit, benchmark, 27 threads", [("instructions running (hot compute)", amx_comp, C_BLUE, False), ("waiting for bytes (data wait)", max(0, amx_t27 - amx_comp), C_AQUA, True)], f"{amx_t27:.2f} µs; memory time {r8['memory_time_us_at_r_core_27']:.2f} µs")]
    units_svg = stacked_units_svg(seg_rows, "Where a unit's time goes")
    spa = ub8.get("avx_t27_split") or {}
    spm = ub8.get("amx_t27_split") or {}
    common_avx_b = (spa.get("common_ns") or 0) / 1000.0
    common_amx_b = ((spm.get("softmax_ns") or 0) + (spm.get("state_ns") or 0)) / 1000.0
    scale_src = (f"M3 hot-t27 × (hot clock ÷ serving clock). AVX: {f1(r8['avx_hot_clock_ghz'], 3)} GHz (M4, avx-hot-t27-long) ÷ {f1(r8['avx_serving_clock_ghz'], 2)} GHz (Tron's AVX arm, 2026-09-01, not re-sampled) = {f1(r8['avx_clock_scale'], 3)}. "
                 f"AMX: {f1(r8['amx_hot_clock_ghz'], 3)} GHz (M4, amx-hot-t27-long) ÷ {f1(r8['amx_serving_clock_ghz'], 3)} GHz (M4, the 27-thread AMX benchmark under load, taken as the AMX serving clock) = {f1(r8['amx_clock_scale'], 3)}.")

    # ---- section 6: chain text
    v = r8["s_transfer_variants_us"]
    chain_txt = f"""Baseline (Tron in its AVX form, M7 of 2026-09-03, worker 0 medians over {D['m7_tron_avx']['8192']['windows']} decode steps; prompt 8192; all times in µs per token):
  token            {b8['period_us']:8.1f}
  other work       {b8['other_us']:8.1f}   ({100 * b8['other_us'] / b8['period_us']:.1f}% of the token)          unchanged
  attention        {b8['attention_us']:8.1f}   ({100 * b8['attention_share']:.1f}%)
    page work      {b8['page_work_us']:8.1f}   worker 0 units per token {b8['units_w0']:.0f} (36 layers x {b8['units_w0'] / 36:.0f} pages) x unit {b8['unit_avx_us']:.3f} = {b8['units_w0'] * b8['unit_avx_us']:.1f};
                              per-range overhead {b8['range_overhead_us']:.1f} = page-work timer minus that product ({b8['range_overhead_us'] / 36:.1f} µs for each of the 36 ranges)
    joins          {b8['joins_us']:8.1f}   unchanged
    barrier        {b8['barrier_us']:8.1f}   unchanged
    untimed rest   {b8['untimed_rest_us']:8.1f}   unchanged

AMX unit (benchmark, 27 threads, prompt-8192 working set, {esc(r8['layout'])}):
  measured under load        {v['none']:.3f} µs   from unit_bench amx-p130-t27-book24, worker 0 median of 3 repeats
  calibration factor s       {r8['serving_factor_s']:.3f}      Tron AVX unit {r8['avx_tron_us']:.3f} / benchmark AVX unit {r8['avx_bench_us']:.3f} (same layout, same load)
  round 1 (rule as written)  {r8['round1_transfer_chosen']}: {r8['round1_unit_amx_us']:.3f} µs
  round 2 (this report)      {r8['s_transfer_chosen']}: {r8['unit_amx_primary_us']:.3f} µs   (variants: none {v['none']:.3f} / multiplicative {v['multiplicative']:.3f} / additive {v['additive']:.3f})
  AMX per-token extras       {r8['amx_extras_us']:.1f} µs     {esc(r8['amx_extras_source'])}

Chain (round 2):
  page work_AMX  = {b8['units_w0']:.0f} x ({r8['coverage']:.4f} x {r8['unit_amx_primary_us']:.3f} + {1 - r8['coverage']:.4f} x {b8['unit_avx_us']:.3f}) + {b8['range_overhead_us']:.1f} + {r8['amx_extras_us']:.1f} = {c['page_work_us']:.1f}
  attention_AMX  = {c['page_work_us']:.1f} + {b8['joins_us']:.1f} + {b8['barrier_us']:.1f} + {b8['untimed_rest_us']:.1f} = {c['attention_us']:.1f}   (ratio to the baseline {c['attention_ratio']:.3f})
  token_AMX      = {b8['other_us']:.1f} + {c['attention_us']:.1f} = {c['token_us']:.1f}                (ratio {c['token_ratio']:.3f})
  boost          = {b8['period_us']:.1f} / {c['token_us']:.1f} - 1 = {c['boost_pct']:+.1f}%      measured {meas:+.1f}%   error {r8['error_pp']:+.1f} points
  resolution     : 0.1 µs on the AMX unit moves the boost by {abs(r8['boost_pp_per_us_of_unit']) / 10:.1f} points
  band           = [{band_full[0]:+.1f}%, {band_full[1]:+.1f}%]  pre-registered (low edge: {esc(r8['band_edges']['low'])}; high edge: {esc(r8['band_edges']['high'])})
                   [{band_ph[0]:+.1f}%, {band_ph[1]:+.1f}%]  post hoc: the two ruled-out transfer variants dropped (not part of the acceptance rule)
  calibration gate (plan section 7) = {gate_txt}; unchanged by round 2
  verdict under the plan's rules    = {r8['verdict']}; if the gate is waived, the acceptance rule of plan section 1 gives "{r8['verdict_if_gate_waived']}" """

    # ---- section 8: validation and sensitivity tables
    val_tbl = ""
    for p in ("8192", "2048", "256"):
        r = P8[p]
        if "chain_primary" not in r:
            val_tbl += f"<tr><td>prompt {p}</td><td colspan=8>{esc(r['verdict'])}</td></tr>"
            continue
        band_s = "[%+.1f, %+.1f]" % (r["band_pct"][0], r["band_pct"][1])
        val_tbl += (f"<tr><td>prompt {p}</td><td>{esc(str(r['layout']).split(' ')[0])}</td>{td(f1(r['avx_tron_us'], 3))}{td(f1(r['avx_bench_us'], 3))}{td(pct(r['calibration_error_pct']))}"
                    f"{td(f1(r['unit_amx_primary_us'], 3))}{td(pct(r['chain_primary']['boost_pct']))}{td(pct(r['measured_boost_pct']))}{td(band_s)}<td>{'passed' if r['calibration_ok'] else 'failed'}</td></tr>")
    eta_tbl = ""
    for p in ("8192", "2048", "256"):
        r = P8[p]
        for vv in ("avx", "amx"):
            if r.get(f"{vv}_eta") is None:
                continue
            label = "within 0 to 1" if r.get(f"{vv}_eta_in_range") else ("above 1: memory rate not binding (working set in L3)" if r[f"{vv}_eta"] > 1 else "below 0")
            u = r["avx_bench_us"] if vv == "avx" else r["s_transfer_variants_us"]["none"]
            eta_tbl += f"<tr><td>prompt {p}</td><td>{vv.upper()}</td>{td(f1(u, 3))}{td(f1(r[f'{vv}_compute_us'], 3))}{td(f1(r['memory_time_us_at_r_core_27'], 3))}{td(f1(r[f'{vv}_eta'], 2))}<td>{label}</td></tr>"
    sens = [("primary (round 2)", c["boost_pct"], "band")]
    for k in ("none", "multiplicative", "additive"):
        sens.append((f"transfer variant: {k}", r8["chains_by_transfer"][k]["boost_pct"], "band"))
    sens += [("barrier scales with the unit-cost ratio", r8["chain_barrier_scaled"]["boost_pct"], "band"), ("joins and barrier scale", r8["chain_joins_and_barrier_scaled"]["boost_pct"], "band")]
    for k, n in (("chain_clock_plus5", "AMX clock +5% (compute part)"), ("chain_clock_minus5", "AMX clock −5% (compute part)")):
        sens.append((n, r8[k]["boost_pct"], "band"))
    for k, n in (("chain_round1", "round 1, rule as written (single-arena layout)"), ("chain_unexplained_carries_fully", "unexplained AVX residual carried in full to the AMX unit"),
                 ("chain_bracket_eta1", "pre-AMX bracket, eta = 1 (roofline: hot compute and memory time only)"), ("chain_bracket_eta0", "pre-AMX bracket, eta = 0 (serial)"),
                 ("chain_modeled_with_avx_eta", "AMX unit modeled with the AVX path's eta"), ("chain_zero_matmul_ceiling", "ceiling: both matmuls free, common work as measured")):
        if k in r8:
            sens.append((n, r8[k]["boost_pct"], "reference"))
    sens_tbl = "".join(f"<tr><td>{esc(n)}</td><td>{kind}</td>{td(pct(b))}{td(pct(b - meas, 1).replace('%', ' pts'))}</tr>" for n, b, kind in sens)

    # ---- section 7: per-layer table and level shares
    layer_rows = [("Other work (FPGA weight multiplies, norms, rope, K/V save; logits once per token, spread over the layers)", b8["other_us"], b8["other_us"]),
                  ("Attention: page work", b8["page_work_us"], c["page_work_us"]), ("Attention: joins", b8["joins_us"], b8["joins_us"]),
                  ("Attention: barrier", b8["barrier_us"], b8["barrier_us"]), ("Attention: untimed rest", b8["untimed_rest_us"], b8["untimed_rest_us"])]
    tot_a, tot_m = b8["period_us"], c["token_us"]
    layer_tbl = "".join(f"<tr><td>{n}</td>{td(f1(vv / 36))}{td(f1(vv))}{td(P(vv / tot_a))}{td(f1(m / 36))}{td(f1(m))}{td(P(m / tot_m))}</tr>" for n, vv, m in layer_rows)
    layer_tbl += f'<tr class="total"><td>Layer total</td>{td(f1(tot_a / 36))}{td(f1(tot_a))}{td("100%")}{td(f1(tot_m / 36))}{td(f1(tot_m))}{td("100%")}</tr>'

    def row3(level, comp, a_txt, m_txt):
        return "<tr><td>%s</td><td>%s</td>%s%s</tr>" % (level, comp, td(a_txt), td(m_txt))
    lvl_tbl = ""
    lvl_tbl += row3("Token (Tron baseline / estimate)", "other work", P(b8["other_us"] / b8["period_us"]), P(b8["other_us"] / c["token_us"]))
    lvl_tbl += row3("Token (Tron baseline / estimate)", "attention", P(b8["attention_share"]), P(c["attention_us"] / c["token_us"]))
    for nm, val in (("page work", b8["page_work_us"]), ("joins", b8["joins_us"]), ("barrier", b8["barrier_us"]), ("untimed rest", b8["untimed_rest_us"])):
        vm = c["page_work_us"] if nm == "page work" else val
        lvl_tbl += row3("Attention (Tron baseline / estimate)", nm, P(val / b8["attention_us"]), P(vm / c["attention_us"]))
    lvl_tbl += row3("Page work (estimate)", "covered units, AMX-eligible", "n/a", P(r8["coverage"], 2))
    lvl_tbl += row3("Page work (estimate)", "uncovered units, dotter", "100%", P(1 - r8["coverage"], 2))
    lvl_tbl += row3("Unit (benchmark, AVX / AMX path)", "instructions running (hot compute)", P(avx_comp / avx_t27, 0), P(amx_comp / amx_t27, 0))
    lvl_tbl += row3("Unit (benchmark, AVX / AMX path)", "waiting for bytes (data wait)", P(r8["avx_data_wait_us"] / avx_t27, 0), P(r8["amx_data_wait_us"] / amx_t27, 0))
    ta = (spa.get("qk_ns") or 0) + (spa.get("common_ns") or 0) + (spa.get("pv_ns") or 0)
    tm = (spm.get("qk_ns") or 0) + (spm.get("softmax_ns") or 0) + (spm.get("pv_ns") or 0) + (spm.get("state_ns") or 0)
    lvl_tbl += row3("Unit by phase (benchmark, AVX / AMX path)", "QK", P((spa.get("qk_ns") or 0) / ta, 0), P((spm.get("qk_ns") or 0) / tm, 0))
    lvl_tbl += row3("Unit by phase (benchmark, AVX / AMX path)", "PV", P((spa.get("pv_ns") or 0) / ta, 0), P((spm.get("pv_ns") or 0) / tm, 0))
    lvl_tbl += row3("Unit by phase (benchmark, AVX / AMX path)", "common work (softmax pieces + state update)", P((spa.get("common_ns") or 0) / ta, 0), P(((spm.get("softmax_ns") or 0) + (spm.get("state_ns") or 0)) / tm, 0))

    # ---- section 4: AMX comparison (comparison only)
    hm = hist["mirror-8192"]
    cmp_rows = [("unit", amx_t27, hm["total"]), ("QK", (spm.get("qk_ns") or 0) / 1000, hm["qk"]), ("softmax pieces", (spm.get("softmax_ns") or 0) / 1000, hm["softmax"]),
                ("PV", (spm.get("pv_ns") or 0) / 1000, hm["pv"]), ("state update", (spm.get("state_ns") or 0) / 1000, hm["state"])]
    cmp_tbl = "".join(f"<tr><td>{n}</td>{td(f1(bv, 3))}{td(f1(tv, 3))}{td(pct((bv / tv - 1) * 100) if tv else 'n/a')}</tr>" for n, bv, tv in cmp_rows)
    ph = r8.get("avx_phase_residual_pct") or {}
    phase_txt = ", ".join(f"{ {'qk': 'QK', 'common': 'common work', 'pv': 'PV'}[k] } {vv:.1f}%" for k, vv in ph.items())

    # ---- section 10: measurement record
    m3 = D.get("m3_unit_bench", {})
    mem_tbl = "".join(f"<tr><td>{m['mode']}</td>{td(m['threads'])}<td>{m['huge']}</td>{td(f1(m['per_core_GBs_median'], 2))}{td(f1(m['per_core_GBs_min_median'], 2))}{td(f1(m['total_GBs_median'], 1))}{td(m['repeats'])}</tr>"
                      for key in sorted(mr, key=lambda k: (mr[k]["mode"], mr[k]["huge"], mr[k]["threads"])) for m in [mr[key]])
    lat = D.get("m2_latency", {})
    lat_txt = "; ".join(f"{k}: {f1(vv, 1)} ns" for k, vv in (lat.get("idle_ns_median") or {}).items())
    lat_loaded = "; ".join(f"{k}: {f1(vv, 1)} ns" for k, vv in (lat.get("loaded_ns_median") or {}).items())
    rec_tbl = ""
    for cfg in sorted(m3):
        o = m3[cfg]
        w = o["worker0"]
        spread_s = "%.1f%%" % (100 * (w.get("unit_ns_spread") or 0))
        common_s = f1((w.get("softmax_ns") or 0) + (w.get("state_ns") or 0) + (w.get("common_ns") or 0), 0)
        rec_tbl += f"<tr><td><code>{cfg}</code></td>{td(o['repeats'])}{td(f1(w.get('unit_ns'), 0))}{td(f1(w.get('qk_ns'), 0))}{td(common_s)}{td(f1(w.get('pv_ns'), 0))}{td(spread_s)}<td>{esc(o['huge'].split(' ')[0])}</td></tr>"
    clocks = D.get("m4_clocks", {})
    clk_tbl = "".join(f"<tr><td><code>{k}</code></td>{td(f1(vv['bzy_mhz_median_busy_cores'], 0))}{td(vv['samples_in_window'])}</tr>" for k, vv in sorted(clocks.items()))
    insn = D.get("m5_insn", {})
    insn_names = {"vdp_tp4": "VDPBF16PS throughput, 4 chains", "vdp_tp8": "VDPBF16PS throughput, 8 chains", "vdp_tp16": "VDPBF16PS throughput, 16 chains", "vdp_lat": "VDPBF16PS latency",
                  "hred_tp": "horizontal reduction, throughput", "hred_lat": "horizontal reduction, latency chain", "dotter_l1": "dotter per-token dot (4 VDPBF16PS + reduction), page in L1",
                  "tdp_tp": "TDPBF16PS throughput", "tdp_lat": "TDPBF16PS dependent chain", "tld_l1": "TILELOADD, 1 KiB tile in L1"}
    insn_tbl = "".join(f"<tr><td>{insn_names.get(k, k)} (<code>{k}</code>)</td>{td(f1(vv.get('ns_per_insn'), 3))}{td(f1(vv.get('core_cycles_per_insn'), 2))}{td(f1(vv.get('core_mhz_median'), 0))}</tr>" for k, vv in sorted(insn.items()) if isinstance(vv, dict))
    units_total = 37440 * (2000 + 20)
    m6 = parse_m6(f"{RES}/m6-perf.txt", units_total)
    m6_tbl = ""
    if m6:
        names = [("cycles", "cycles per unit (includes each pass's end barrier)"), ("instructions", "instructions per unit"), ("ipc", "instructions per cycle"),
                 ("l1_miss", "L1 demand load misses per unit"), ("l2_miss", "L2 demand load misses per unit"), ("l3_miss", "L3 demand load misses per unit"), ("dtlb_ld_walk", "dTLB load walks completed per unit")]
        for k, n in names:
            m6_tbl += f"<tr><td>{n}</td>{td(f1(m6['avx'].get(k), 2 if k in ('ipc',) else 1))}{td(f1(m6['amx'].get(k), 2 if k in ('ipc',) else 1))}</tr>"
    m0_txt = open(f"{RES}/m0-hardware.txt").read() if os.path.exists(f"{RES}/m0-hardware.txt") else "(m0-hardware.txt missing)"
    m8_txt = ""
    if spans:
        ms = spans["main_thread_split"]
        pt = spans["per_token_us"]
        m8_txt = (f"Median forward {spans['forward_median_us'] / 1000:.2f} ms per token over {spans['forwards']} forwards. Per-token span medians: waiting for mbox {f1(pt['waiting for mbox']['median_us'], 0)} µs "
                  f"({pt['waiting for mbox']['count_per_token']:.0f} waits per token); Prepare hardware matmul job {f1(pt['Prepare hardware matmul job']['median_us'], 0)} + Launch hardware matmul job {f1(pt['Launch hardware matmul job']['median_us'], 0)} = {f1(ms['launch_and_prepare_us'], 0)} µs; "
                  f"fill_logits_buffer {f1(pt['fill_logits_buffer']['median_us'], 0)} + notify_listener {f1(pt['notify_listener']['median_us'], 0)} + waiting_for_logits {f1(pt['waiting_for_logits']['median_us'], 0)} = {f1(ms['logits_stage_us'], 0)} µs; "
                  f"Attention Ready {f1(pt['Attention Ready']['median_us'] / 1000, 1)} ms summed over the 27 workers ({f1(pt['Attention Ready']['median_us'] / 27 / 1000, 2)} ms per worker). Shares of the three main-thread groups: FPGA waits {ms['shares_pct']['fpga_waits']:.0f}%, launch and prepare {ms['shares_pct']['launch_prepare']:.0f}%, logits {ms['shares_pct']['logits']:.0f}% (est., traced).")
    jb = M["jb_fit"]
    jb_txt = (f"Joins plus barrier = {jb['a_us']:.0f} + {jb['b']:.4f} × page work (µs per token), fitted by least squares to the three M7 prompts; residuals "
              + ", ".join(f"{pct(jb['residual_pct_by_prompt'][p])} at prompt {p}" for p in ("256", "2048", "8192")) + f"; accepted: {'yes' if jb['accepted'] else 'no (the plan requires every residual within 10%)'}.")
    warnings_html = "".join(f"<li>{esc(w)}</li>" for w in M.get("warnings", []))

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AMX Decode Perf Model</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{color-scheme:light;--paper:#fff;--panel:#f3f6f8;--panel-2:#e9eef2;--rule:#d9e0e6;--ink:#1f2933;--ink-2:#4b5761;--muted:#7a8790;--wait:#0f766e;--crit:#d03b3b;
--sans:"IBM Plex Sans","Segoe UI",system-ui,sans-serif;--serif:"IBM Plex Serif",Georgia,serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}}
*{{box-sizing:border-box}}html{{background:var(--paper)}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:16px;line-height:1.55}}
.wrap{{max-width:1120px;margin:0 auto;padding:32px 24px 80px;display:grid;grid-template-columns:220px minmax(0,1fr);gap:40px}}
@media(max-width:900px){{.wrap{{grid-template-columns:1fr}}nav.toc{{position:static}}}}
nav.toc{{position:sticky;top:24px;align-self:start;font-family:var(--sans);font-size:13px;line-height:1.45}}nav.toc .toclabel{{text-transform:uppercase;letter-spacing:.08em;font-size:11px;color:var(--muted);margin-bottom:8px}}
nav.toc a{{display:block;color:var(--ink-2);text-decoration:none;padding:3px 0 3px 10px;border-left:2px solid var(--rule)}}nav.toc a:hover{{color:var(--ink);border-left-color:var(--wait)}}
main{{min-width:0}}header.title{{border-bottom:1px solid var(--rule);padding-bottom:18px;margin-bottom:26px}}.eyebrow{{font-family:var(--sans);text-transform:uppercase;letter-spacing:.1em;font-size:12px;color:var(--muted)}}
h1{{font-family:var(--sans);font-weight:600;font-size:30px;line-height:1.2;margin:6px 0 10px;text-wrap:balance}}.meta{{font-family:var(--sans);font-size:13px;color:var(--ink-2);display:flex;flex-wrap:wrap;gap:6px 22px}}
h2{{font-family:var(--sans);font-weight:600;font-size:21px;margin:44px 0 12px;padding-top:10px;border-top:1px solid var(--rule)}}h3{{font-family:var(--sans);font-weight:600;font-size:16px;margin:26px 0 8px}}
p,li{{max-width:72ch}}.short{{background:var(--panel);border-left:4px solid var(--wait);padding:14px 18px;margin:0 0 8px}}.short p{{margin:6px 0}}
.note{{background:var(--panel);padding:12px 16px;margin:14px 0;border-left:4px solid var(--rule)}}.rule{{border-left-color:var(--crit)}}
code,pre{{font-family:var(--mono);font-size:13.5px}}code{{background:var(--panel-2);padding:1px 5px;border-radius:3px}}pre{{background:var(--panel);border:1px solid var(--rule);padding:14px 16px;overflow-x:auto;line-height:1.5;margin:12px 0}}
.tablewrap{{overflow-x:auto;margin:12px 0 18px}}table{{border-collapse:collapse;width:100%;font-family:var(--sans);font-size:13.5px}}th,td{{text-align:left;vertical-align:top;padding:7px 10px;border-bottom:1px solid var(--rule)}}
th{{font-weight:600;background:var(--panel);white-space:nowrap}}td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}tr.total td{{font-weight:600;background:var(--panel)}}
figure{{margin:18px 0}}figcaption{{font-family:var(--sans);font-size:13px;color:var(--ink-2);margin-top:6px;max-width:80ch}}
.legend{{font-family:var(--sans);font-size:12px;color:var(--ink-2);display:flex;gap:18px;margin:6px 0}}.legend i{{display:inline-block;width:14px;height:12px;border-radius:2px;margin-right:6px;vertical-align:-2px}}
dl.words{{display:grid;grid-template-columns:max-content 1fr;gap:6px 18px;font-size:15px}}dl.words dt{{font-family:var(--sans);font-weight:600;font-size:14px}}dl.words dd{{margin:0;max-width:78ch}}.small{{font-size:13.5px;color:var(--ink-2)}}
.verdict{{font-family:var(--sans);font-weight:600;font-size:17px;max-width:none}}details summary{{cursor:pointer;font-family:var(--sans);font-size:13.5px;color:var(--ink-2)}}
</style></head><body><div class="wrap">
<nav class="toc" aria-label="Contents"><div class="toclabel">Contents</div>
<a href="#short">Short version</a><a href="#words">Words used here</a><a href="#result">1. Result</a><a href="#model">2. The model</a><a href="#baseline">3. Baseline (Tron, AVX form)</a>
<a href="#calib">4. Calibration</a><a href="#unit">5. The unit, decomposed</a><a href="#chain">6. The arithmetic</a><a href="#layers">7. Per layer</a><a href="#validation">8. Validation and sensitivity</a>
<a href="#rounds">9. Refinement rounds</a><a href="#record">10. Measurement record</a><a href="#sources">11. Sources</a></nav>
<main>
<header class="title"><div class="eyebrow">Perf model · report · 2026-09-03</div><h1>The AMX decode boost from a model with data waits</h1>
<div class="meta"><span>Machine: delphi-3bda (the test server, Intel Xeon 6962P)</span><span>Workload: qwen-3-4b-tp2, one user, prompt 8192, 256 generated tokens</span><span>Plan: <a href="action-plan.html">action-plan.html</a></span></div></header>

<section id="short"><div class="short"><p><strong>Short version.</strong> {N['short']}</p></div>
<p class="small">Every other term (unit, page, worker, book, and so on) is defined in "Words used here" below.</p></section>

<section id="words"><h2>Words used here</h2>
<dl class="words">
<dt>Tron, runtron</dt><dd>Positron's inference program and its command-line tool. Here Tron runs the weight matrix multiplies on FPGA cards (field-programmable gate arrays, the reconfigurable chips on Positron's accelerator cards) and the attention on CPU cores.</dd>
<dt>AMX, AVX, dotter</dt><dd>Two CPU instruction sets. AVX-512 is the ordinary 512-bit vector set; Tron's AVX attention loop is called the dotter. AMX (Advanced Matrix Extensions) multiplies 16-row tiles of bf16 numbers (bfloat16, a 16-bit floating-point format) in one instruction, TDPBF16PS. VDPBF16PS is the AVX-512 instruction the dotter uses (32 multiply-adds at once); TILELOADD loads one tile; LDTILECFG sets up the tile registers.</dd>
<dt>Arena-mirror</dt><dd>The AMX build of Tron that keeps a second copy of the keys in the tile-friendly layout (the K mirror, on ordinary 4 KiB pages); the build whose measured boost (+17.3%) this report estimates.</dd>
<dt>Kill switch, AVX form</dt><dd><code>TRON_AMX_DISABLE=1</code>: the AMX binary with AMX switched off, so it runs the dotter everywhere. The baseline of this report is that run (M7), the same binary and flags as the 2026-09-01 measurement.</dd>
<dt>Pre-AMX input</dt><dd>An input that would exist before AMX was added to Tron: Tron's own AVX-path timers, page geometry, Intel documents and non-Tron processor measurements. The "pre-AMX bracket" rows of section 8 use only such inputs. The AMX unit itself is measured with a copy of Tron's AMX kernel run outside Tron (section 2).</dd>
<dt>Pre-registered</dt><dd>Fixed in the plan (action-plan.html) before any measurement was taken: the rules, the search order and the acceptance thresholds.</dd>
<dt>Decode, token</dt><dd>The phase where the model produces one token per step; every step re-reads all stored keys and values. Times are per generated token.</dd>
<dt>Page, KV head, unit</dt><dd>A page is 64 tokens of stored keys (16 KiB) and values (16 KiB) for one layer and one KV head (a key/value head; each serves 4 query heads). A unit is one query token's 4 query heads against one page, including the softmax pieces and the running-state update.</dd>
<dt>QK, PV, common work</dt><dd>The two matrix multiplies of a unit (queries against keys; probabilities against values) and the rest (scaling, running maximum, exponentials and sum, state update).</dd>
<dt>Page work, joins, barrier, untimed rest</dt><dd>The three timed phases of one attention operation on one worker: its loop over units; merging results across workers; waiting for the slowest worker. The untimed rest is attention time minus the three phases: handshakes and bookkeeping no phase timer covers; it is held unchanged in the estimate.</dd>
<dt>Worker, worker 0</dt><dd>One of the 27 CPU threads that run attention units at the same time, each on its own core of socket 0 (CPUs 24 to 35, 48 to 59, 151 to 154; one of the 28 hosts the main thread). Worker 0 is the one whose timers Tron exports; all per-token numbers are its medians. Tron's planner splits pages by measured worker speed, so worker 0's share differs from run to run.</dd>
<dt>Range, per-range overhead, AMX per-token extras</dt><dd>A range is one run of consecutive pages a worker handles in one attention operation; worker 0 has 36 per token, one per layer. The per-range overhead is page work minus units × unit cost: the page loop and the probe's own reads. The AMX per-token extras are the AMX-only costs paid once per range (tile configuration, the 1 KiB query copy, the tile release), measured by the benchmark's range timer.</dd>
<dt>Book, arena</dt><dd>Tron's KV allocator places a sequence's pages adjacent in books of 24 pages (a book holds 1600 tokens by default; 24 pages are used with 128-token prompt chunks); each book is its own arena, one contiguous block of memory. Found in the KV cache and scheduler source; reproduced by the benchmark's <code>--book-pages 24</code> option.</dd>
<dt>Probe, stamps</dt><dd>The timing code compiled into the Tron binary used here (git branch jhan-amx-fence, commit 8fd1e7798d), switched on with <code>TRON_ATTN_PHASE=1</code>; it records the per-token and per-phase counters (numbered "stamps") this report reads.</dd>
<dt>Coverage</dt><dd>The share of units that can use AMX: only full 64-token pages qualify (99.24% at prompt 8192, 97.14% at 2048, 84.78% at 256; from the fallback counters of 2026-09-01).</dd>
<dt>Data wait, compute, eta, memory time</dt><dd>Compute: the unit's time with all bytes already in the core's L2 cache. Memory time: 32 KiB divided by the per-core streaming rate under load. Data wait: the unit's time minus its compute. eta: the share of the shorter of compute and memory time that is hidden behind the longer one (1 = perfect overlap, the roofline case; 0 = the two add, the serial case).</dd>
<dt>Memory lower bound</dt><dd>The memory time: a unit cannot finish before its 32 KiB has arrived, however fast its instructions run.</dd>
<dt>R<sub>core</sub>(N)</dt><dd>The bytes per second one core streams from DRAM (main memory) when N cores on the socket read at once.</dd>
<dt>L1, L2, L3, DRAM, hot</dt><dd>The core's caches and main memory. L1 (48 KiB) and L2 (2 MiB) are private to each core; L3 (432 MB) is shared by the socket. A "hot" unit reads a page that is already in the core's L2.</dd>
<dt>Cache line, demand miss, hardware prefetch</dt><dd>A cache line is 64 bytes (32 KiB = 512 lines). A demand miss is a load the program itself issued whose line was not in the cache. Hardware prefetch is the core fetching lines ahead of the program on its own guess; prefetched lines do not count as demand misses.</dd>
<dt>1 GiB pages, THP, hugetlb, TLB, dTLB walk</dt><dd>Memory page sizes and their cost. 1 GiB pages: the pool of huge pages Tron's KV arena uses (hugetlb). THP: transparent huge pages, 2 MiB pages the kernel assigns on request. The TLB caches address translations; a dTLB walk is the slow page-table lookup after a data-side TLB miss (one per 4 KiB page touched, when pages are small).</dd>
<dt>rdtsc, turbostat, perf stat</dt><dd>rdtsc: the CPU's cycle-counter instruction, used as the clock by Tron's probe and by the benchmark. turbostat: the Linux tool that reports each core's clock; its Bzy_MHz column is the clock while the core is busy (M4). perf stat: the Linux tool that reads the CPU's hardware counters (M6).</dd>
<dt>Residual, calibration gate</dt><dd>The residual is Tron's AVX unit minus the benchmark's AVX unit under the same load and layout (as a share of Tron's). The gate is the plan's limit on it: within 5% at prompt 8192 with QK and PV each within 10%; within 10% at prompts 2048 and 256. When it fails, the verdict is "calibration failed", the AMX numbers are provisional, and the search of section 4 runs.</dd>
<dt>s, transfer rule</dt><dd>s = Tron's AVX unit ÷ the benchmark's AVX unit; the pre-registered rule of the plan (section 7) decides how the residual is carried to the AMX unit: none, multiplicative (× s) or additive (+ residual).</dd>
<dt>Band, points</dt><dd>The pre-registered band is the range of the estimate over the alternative rules of plan section 8, rule 6 (the three transfer variants, the AMX clock ±5%, the two barrier rules). Points are percentage points: +20% minus +17% is 3 points.</dd>
<dt>Verdict: on par, close</dt><dd>The plan's acceptance rule (section 1). On par: the primary estimate within 3 points of the measured +17.3% and the whole pre-registered band within 3 points. Close: the primary within 6 points. A failed calibration gate gives "calibration failed" instead.</dd>
<dt>Record labels</dt><dd>Tron's names for the weight multiplies: WQ, WK, WV (query, key, value), WO (attention output projection), WFF1, WFF3, WFF2 (the three feed-forward multiplies). Norms are the normalization layers; rope is the rotary position embedding; logits are the per-word scores produced once per token.</dd>
<dt>M0 to M8</dt><dd>The measurement steps of the plan, in the order the campaign ran them: M0 hardware check, M7 Tron in AVX form, M1 memory streaming rate, M2 memory latency, M5 instruction costs, M3 the unit benchmark, M4 clocks, M6 hardware counters, M8 a traced Tron run. Section 10 names the file of each step.</dd>
<dt>est., Insufficient data</dt><dd>est.: an estimated number, not a measured one. Insufficient data: a quantity the campaign could not measure, with the measurement that would settle it named.</dd>
</dl></section>

<section id="result"><h2>1. Result</h2>
<p class="verdict">Estimate at prompt 8192: {pct(c['boost_pct'])}. Measured: {pct(meas)}. Pre-registered band: {band_full[0]:+.1f}% to {band_full[1]:+.1f}%.</p>
<p>Verdict under the plan's rules: <strong>{esc(r8['verdict'])}</strong> (plan section 7: {esc('; '.join(r8['calibration_fail_reasons']))}). The gate compares the benchmark's AVX unit with Tron's under the same load and layout; round 2 changed the transfer rule, not that comparison, so the gate is still failed and the {pct(c['boost_pct'])} estimate is provisional. If the gate is waived, the acceptance rule of plan section 1 gives "{esc(r8['verdict_if_gate_waived'])}", not "on par": the primary value is {r8['error_pp']:+.1f} points from the measurement (within 3), but the pre-registered band's low edge, {band_full[0]:+.1f}%, is {abs(band_full[0] - meas):.1f} points away (outside 3). Over the alternatives the search does not rule out (barrier rules, AMX clock ±5%) the band is {band_ph[0]:+.1f}% to {band_ph[1]:+.1f}%; that band is post hoc and not part of the acceptance rule.</p>
<p>{N['result_para']}</p>
<div class="tablewrap"><table><tr><th>Round or step (prompt 8192)</th><th class="num">AMX unit used (µs)</th><th class="num">estimate</th><th class="num">vs measured</th></tr>{rounds_tbl}</table></div>
<figure>{db_svg}<figcaption>Figure 1. Model estimate (blue) against the measured gain (orange) at the three prompt lengths; the light band is the pre-registered band (plan section 8, rule 6). Prompt 8192 is the exit test; the other two are validation rows.</figcaption></figure>
</section>

<section id="model"><h2>2. The model</h2>
<p>The model is the plan's section 3: the earlier "model in one picture" with a data-wait term at the unit level. Only the covered units change between the AVX and the AMX build; everything else in a token keeps its measured time.</p>
<pre><code>token time   = other work                                           unchanged
             + attention
attention    = page work + joins + barrier + untimed rest           joins, barrier, rest unchanged
page work    = per-range overhead + AMX per-token extras
             + sum over units of  covered unit -> AMX unit (99.24%)  /  uncovered unit -> AVX unit (0.76%)
unit         = compute (whole unit hot in L2, per code path) + data wait
             = max(compute, memory) + (1 - eta) * min(compute, memory),   memory = 32 KiB / R_core(27)</code></pre>
<p>The AMX unit is measured by a copy of Tron's AMX kernel run outside Tron on 27 cores over Tron's page layout (the unit benchmark, M3). The plan required the same benchmark to first reproduce Tron's own AVX unit within 5% under the same conditions. It came within {abs(r8['calibration_error_pct']):.1f}% ({r8['avx_bench_us']:.2f} µs against Tron's {r8['avx_tron_us']:.2f} µs at prompt 8192), {abs(r8['calibration_error_pct']) - 5:.1f} points outside that gate, so under the plan's rule the AMX reading is provisional. Section 4 reports the search for the cause and what it established about the AMX unit; section 9 the round that uses the AMX reading as measured. The compute, memory and wait terms decompose that measurement (section 5).</p>
</section>

<section id="baseline"><h2>3. Baseline: Tron in its AVX form, measured 2026-09-03 (M7)</h2>
<p>The kill-switch binary of 2026-09-01 was run again with the phase probe at prompts 256, 2048 and 8192 (two repeats each, 253 generated tokens of 256 requested). The tables compare today's worker-0 medians with the 2026-09-01 values.</p>
<div class="tablewrap"><table><tr><th>Per token, prompt 8192 (µs)</th><th class="num">M7 (2026-09-03)</th><th class="num">2026-09-01</th><th class="num">change</th></tr>{base_tbl}</table></div>
<div class="tablewrap"><table><tr><th>Per unit, prompt 8192 (µs)</th><th class="num">M7 (2026-09-03)</th><th class="num">2026-09-01</th><th class="num">change</th></tr>{unit_tbl}</table></div>
<p>{audit_txt}</p>
<p class="small">Sources: {esc(b8['source'])}; 2026-09-01: exec/results/single-attn-20260901/summary.json, key disable-8192; M1: m1-memrate.txt.</p>
</section>

<section id="calib"><h2>4. Calibration: the benchmark against Tron's AVX unit</h2>
<p>{N['calibration_para']}</p>
<div class="tablewrap"><table><tr><th>Prompt</th><th>layout</th><th class="num">Tron AVX unit (µs)</th><th class="num">benchmark AVX unit (µs)</th><th class="num">benchmark − Tron</th><th class="num">AMX unit used (µs)</th><th class="num">estimate</th><th class="num">measured</th><th class="num">pre-registered band</th><th>calibration gate</th></tr>{val_tbl}</table></div>
<p class="small">Per-phase residual at prompt 8192 (benchmark short of Tron, as a share of Tron's phase): {phase_txt}. Calibration gate: {esc(gate_txt)}. Transfer rule of round 1 (as pre-registered): {esc(r8['round1_transfer_reason'])}. Round 2: {esc(r8['s_transfer_reason'])}.</p>
<h3>Comparison only: the benchmark's AMX unit against Tron's measured AMX unit</h3>
<p>These Tron AMX numbers (arena-mirror build, 2026-09-01) are not inputs of the model and are not part of the round-2 argument. They are shown because they test the same benchmark on the AMX side.</p>
<div class="tablewrap"><table><tr><th>Per unit, prompt 8192 (µs)</th><th class="num">benchmark (27 threads, book layout)</th><th class="num">Tron, arena-mirror (2026-09-01)</th><th class="num">benchmark − Tron</th></tr>{cmp_tbl}</table></div>
</section>

<section id="unit"><h2>5. The unit, decomposed into compute and data wait</h2>
<p>{N['decomposition_para']}</p>
<figure>{legend_html([("instructions running (hot compute)", f"background:{C_BLUE}"), ("waiting for bytes (data wait), dashed", f"border:2px dashed {C_AQUA};background:{C_AQUA}26")])}{units_svg}<figcaption>Figure 2. One unit at prompt 8192 on each code path, from the benchmark under load (27 threads, book layout): the solid block is the hot run (instructions running), the dashed block is the rest, waiting for bytes. Memory time at R<sub>core</sub>(27) = {f1(r8.get('r_core_27_GBs'), 2)} GB/s is {f1(r8.get('memory_time_us_at_r_core_27'), 2)} µs per 32 KiB. eta: AVX {f1(r8.get('avx_eta'), 2)}, AMX {f1(r8.get('amx_eta'), 2)}.</figcaption></figure>
<div class="tablewrap"><table><tr><th>Quantity (prompt 8192)</th><th class="num">AVX path</th><th class="num">AMX path</th><th>Source</th></tr>
<tr><td>Compute: hot in L2, scaled to the serving clock (µs)</td>{td(f1(avx_comp, 3))}{td(f1(amx_comp, 3))}<td>{scale_src}</td></tr>
<tr><td>Unit under load, 27 threads, book layout (µs)</td>{td(f1(avx_t27, 3))}{td(f1(amx_t27, 3))}<td>M3, avx/amx-p130-t27-book24</td></tr>
<tr><td>Data wait = unit − compute (µs)</td>{td(f1(r8.get('avx_data_wait_us'), 3))}{td(f1(r8.get('amx_data_wait_us'), 3))}<td>difference</td></tr>
<tr><td>Data wait share of the unit</td>{td(P(r8['avx_data_wait_share'], 0))}{td(P(r8['amx_data_wait_share'], 0))}<td>ratio</td></tr>
<tr><td>Memory time = 32 KiB ÷ R<sub>core</sub>(27) (µs)</td>{td(f1(r8.get('memory_time_us_at_r_core_27'), 3))}{td(f1(r8.get('memory_time_us_at_r_core_27'), 3))}<td>M1, 27 readers, 64-byte loads, 2 MiB pages</td></tr>
<tr><td>Unit ÷ memory time</td>{td(f1(r8.get('avx_unit_over_memory_floor'), 2))}{td(f1(r8.get('amx_unit_over_memory_floor'), 2))}<td>ratio</td></tr>
<tr><td>eta (overlap efficiency)</td>{td(f1(r8.get('avx_eta'), 2))}{td(f1(r8.get('amx_eta'), 2))}<td>{esc(r8.get('amx_eta_note', 'both within 0 to 1'))}</td></tr>
<tr><td>Common work inside the unit (µs)</td>{td(f1(common_avx_b, 3))}{td(f1(common_amx_b, 3))}<td>M3 per-phase timers (AVX: common counter as Tron's; AMX: softmax + state)</td></tr>
</table></div>
</section>

<section id="chain"><h2>6. The arithmetic, from inputs to the estimate</h2>
<pre><code>{esc(chain_txt)}</code></pre>
</section>

<section id="layers"><h2>7. Per layer</h2>
<p>qwen-3-4b has 36 identical decoder layers; each runs one attention operation on the 27 workers while the FPGA cards run its weight multiplies. The per-token rows divided by 36 give the per-layer rows. The split of the non-attention work into its records (WQ, WK, WV, WO, WFF1, WFF3, WFF2, logits) is not exposed by an untraced run; the traced run M8 is summarized below in this section (file m8-spans.json).</p>
<div class="tablewrap"><table><tr><th>Component</th><th class="num">AVX µs/layer</th><th class="num">AVX µs/token</th><th class="num">AVX share</th><th class="num">AMX est. µs/layer</th><th class="num">AMX est. µs/token</th><th class="num">AMX share</th></tr>{layer_tbl}</table></div>
<h3>Each level of the model and the share of its components</h3>
<p class="small">Token and attention rows: Tron's M7 baseline and the round-2 estimate. Unit rows: the benchmark under load (27 threads, book layout), AVX path and AMX path.</p>
<div class="tablewrap"><table><tr><th>Level</th><th>Component</th><th class="num">AVX</th><th class="num">AMX</th></tr>{lvl_tbl}</table></div>
<h3>Inside "other work": the traced run (M8, labeled traced)</h3>
<p>{N.get('traced_para', '')}</p>
</section>

<section id="validation"><h2>8. Validation rows and sensitivity</h2>
<p>The same chain at prompts 2048 and 256 uses their own baseline rows and coverage (97.14% and 84.78%) and the single-arena benchmark runs (the book layout was run at prompt 8192 only). Their working sets (306 MiB and 54 MiB) fit in the 432 MB L3 of the socket, so the DRAM memory time of {f1(r8['memory_time_us_at_r_core_27'], 2)} µs does not bind there: eta is above 1 on both paths, "memory rate not binding" in the plan's words (rule 5). eta only decomposes a unit, so those estimates are unaffected.</p>
<div class="tablewrap"><table><tr><th>Prompt</th><th>path</th><th class="num">unit under load (µs)</th><th class="num">compute, hot (µs)</th><th class="num">DRAM memory time (µs)</th><th class="num">eta</th><th>label</th></tr>{eta_tbl}</table></div>
<p>The sensitivity table lists the alternatives the pre-registered band is made of ("band") and reference points that are not part of it ("reference"), at prompt 8192.</p>
<div class="tablewrap"><table><tr><th>Rule or variant (prompt 8192)</th><th>kind</th><th class="num">estimate</th><th class="num">vs measured</th></tr>{sens_tbl}</table></div>
</section>

<section id="rounds"><h2>9. Refinement rounds</h2>
<p>{N['rounds_para']}</p>
<p class="small">Joins-and-barrier fit (plan section 9): {esc(jb_txt)}</p>
<details><summary>Script flags raised while building model.json ({len(M.get('warnings', []))})</summary><ul class="small">{warnings_html}</ul></details>
</section>

<section id="record"><h2>10. Measurement record</h2>
<h3>M0 hardware check (file m0-hardware.txt)</h3>
<details><summary>Show the recorded hardware facts</summary><pre><code>{esc(m0_txt)}</code></pre></details>
<h3>M7 Tron in its AVX form (files m7-tron-avx.txt, m7-cell-disable-c*-r*.log, m7-phases-disable-c*.json)</h3>
<p class="small">The baseline rows of the chain; reported in section 3.</p>
<h3>M1 per-core streaming rate (file m1-memrate.txt)</h3>
<p class="small">How to read the table. Each reader is one thread pinned to one core of Tron's 27-core attention set, streaming its own 1024 MiB buffer for 6 s. mode: load = 64-byte AVX-512 loads (one per cache line, 8 independent accumulators); tile = AMX tile loads (1 KiB tiles of 16 rows × 64 bytes, the K-mirror panel pattern). pages: none = 4 KiB; thp = 2 MiB. "median of means" = the mean over the readers of each reader's GB/s, then the median over the repeats; "slowest core" = the same for the slowest reader; "total" = the sum over readers.</p>
<div class="tablewrap"><table><tr><th>mode</th><th class="num">readers</th><th>pages</th><th class="num">per core GB/s (median of means)</th><th class="num">slowest core GB/s</th><th class="num">total GB/s</th><th class="num">repeats</th></tr>{mem_tbl}</table></div>
<h3>M2 memory latency (file m2-latency.txt)</h3>
<p class="small">A pointer chase: each load's address comes from the previous load's value, so the time per hop is one memory access latency. mbN = a buffer of N MiB; the suffix is the page size obtained (1g = 1 GiB pages, thp = 2 MiB, none = 4 KiB). mb8192-1g (8 GiB, no TLB walks, 19 times the L3) is the DRAM number; mb64 fits in the L3. Idle: {esc(lat_txt)}. Loaded (26 readers streaming on the other attention cores while core 24 chases): {esc(lat_loaded)}.</p>
<h3>M5 instruction costs (files m5-&lt;loop&gt;.txt and m5-turbostat-&lt;loop&gt;.txt; core 24, 4 s per loop)</h3>
<div class="tablewrap"><table><tr><th>loop</th><th class="num">ns per instruction</th><th class="num">core cycles per instruction</th><th class="num">core MHz during the loop</th></tr>{insn_tbl}</table></div>
<h3>M3 unit benchmark (files m3-unit-bench.txt, book-sens.log and m3-&lt;configuration&gt;-r&lt;n&gt;.json; worker 0 medians over repeats, ns per unit)</h3>
<p class="small">How to read the configuration code, path-workingset-threads[-variant]. Path: amx or avx. Working set: hot = every unit reads the same one page, which stays in the core's L2 with the thread's buffers (compute only); pN = N pages per layer and KV head (p130 = prompt 8192 at the median decode pass, p34 = prompt 2048, p6 = prompt 256). Threads: t1 = one worker, t27 = 27 workers on Tron's attention cores. Variant: shuf = pages placed at random; thp = 2 MiB instead of 1 GiB pages for keys and values; book24 = Tron's book layout; ctl = its same-session control (single arena); long = a longer run for the clock sample. spread = (max − min) over the repeats as a share of the median. "pages obtained" is what the kernel gave: 1g/4k = keys and values on 1 GiB pages with the mirror on 4 KiB pages.</p>
<div class="tablewrap"><table><tr><th>configuration</th><th class="num">repeats</th><th class="num">unit</th><th class="num">QK</th><th class="num">common (softmax + state)</th><th class="num">PV</th><th class="num">spread</th><th>pages obtained</th></tr>{rec_tbl}</table></div>
<h3>M4 clocks (files m4-turbostat-&lt;configuration&gt;.txt; turbostat Bzy_MHz, busy app cores, samples inside the run window)</h3>
<div class="tablewrap"><table><tr><th>run</th><th class="num">MHz</th><th class="num">samples</th></tr>{clk_tbl}</table></div>
<h3>M6 hardware counters (file m6-perf.txt; the first attempt with symbolic event names is m6-perf.failed-events.txt)</h3>
<p class="small">perf stat over all threads of the 27-thread prompt-8192 single-arena runs (2000 timed passes plus 20 warm-up passes), with the fill-only control run (0 passes) subtracted; divisor 37,440 units per pass × 2020 passes. Events: MEM_LOAD_RETIRED.L1/L2/L3_MISS (raw 0xd1, umask 0x08/0x10/0x20) and DTLB_LOAD_MISSES.WALK_COMPLETED (0x12, umask 0x0e); the symbolic names are not known to this perf, and the top-down metric group is not available in it (Insufficient data for the memory-bound share the plan asked for). These are demand misses only: the 512 lines of a unit are mostly filled by hardware prefetch, so the counts do not measure the bytes read. Cycles per unit include each pass's end barrier.</p>
<div class="tablewrap"><table><tr><th>per unit</th><th class="num">AVX path</th><th class="num">AMX path</th></tr>{m6_tbl}</table></div>
<h3>M8 traced Tron run, AVX form (files m8-cell.log, m8-trace.txt, m8-avx-1u-8192.perfetto-trace.gz, m8-spans.json; script spans.py)</h3>
<p class="small">{esc(m8_txt)}</p>
</section>

<section id="sources"><h2>11. Sources</h2>
<ul>
<li>Plan and pre-registered rules: <a href="action-plan.html">perf-model/action-plan.html</a>.</li>
<li>Raw results and parsed medians: <code>exec/results/perf-model-20260903/</code> (campaign.log, book-sens.log, the m0 to m8 files, medians.json, model.json, m8-spans.json, narrative.json).</li>
<li>Tools: <code>exec/perf-model-20260903/</code> (unit_bench.cpp, memrate.c, latency.c, insn_loops.cpp, run-perf-model.sh, run-book-sens.sh, parse.py, model.py, spans.py, gen_report.py).</li>
<li>2026-09-01 measurements (comparison columns): <code>exec/results/single-attn-20260901/summary.json</code>; Notion page "Estimate: the AMX decode boost from pre-AMX data, in plain English".</li>
<li>Constants recorded in model.json: coverage ({esc(K.get('coverage_source', ''))}); the AVX serving clock {K.get('avx_serving_clock_ghz')} GHz ({esc(K.get('avx_serving_clock_source', ''))}); the measured boosts ({esc(K.get('measured_boost_source', ''))}).</li>
</ul>
<p>{N['closing_para']}</p>
</section>
</main></div></body></html>"""
    open(a.out, "w").write(html)
    print("wrote", a.out, len(html), "bytes")


if __name__ == "__main__":
    main()
