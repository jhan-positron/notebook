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
from statistics import median

HOME = os.path.expanduser("~")
RES = f"{HOME}/workspace/intel-AMX/exec/results/perf-model-20260903"
OUT_DEFAULT = f"{HOME}/workspace/intel-AMX/perf-model/index.html"
HIST = f"{HOME}/workspace/intel-AMX/exec/results/single-attn-20260901/summary.json"
THP_FILE = f"{HOME}/workspace/intel-AMX/exec/results/thp-20260901/thp.txt"  # 2026-09-01 Tron mirror-THP experiment (comparison only)

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
    W, H_ROW, PAD_L, PAD_R, PAD_T = 980, 44, 260, 210, 30
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


def routes_dot_svg(rows, meas, x_min, x_max, title, unit="%"):
    """One row per way of obtaining the AMX unit; x = the estimate. Filled dot = measured unit (route 1), hollow dot = predicted unit (route 2).
    Orange line = the measured boost, light orange band = +-3 points (the plan's 'on par' limit)."""
    W, H_ROW, PAD_L, PAD_R, PAD_T = 980, 34, 290, 80, 46
    H = PAD_T + H_ROW * len(rows) + 76
    px = lambda v: PAD_L + (v - x_min) / (x_max - x_min) * (W - PAD_L - PAD_R)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{esc(title)}" style="max-width:{W}px;display:block;font-family:IBM Plex Sans,system-ui,sans-serif">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')
    y_top, y_bot = PAD_T - 14, PAD_T + H_ROW * len(rows) + 4
    step = 5 if x_max - x_min > 20 else 2
    v = x_min
    while v <= x_max + 1e-9:
        x = px(v)
        s.append(f'<line x1="{x:.1f}" y1="{y_top}" x2="{x:.1f}" y2="{y_bot}" stroke="{C_GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x:.1f}" y="{y_bot + 16}" font-size="12" fill="{C_INK2}" text-anchor="middle">{v:+g}{unit}</text>')
        v += step
    s.append(f'<rect x="{px(meas - 3):.1f}" y="{y_top}" width="{px(meas + 3) - px(meas - 3):.1f}" height="{y_bot - y_top}" fill="{C_ORANGE}" opacity="0.12"/>')
    s.append(f'<line x1="{px(meas):.1f}" y1="{y_top}" x2="{px(meas):.1f}" y2="{y_bot}" stroke="{C_ORANGE}" stroke-width="2"/>')
    s.append(f'<text x="{px(meas):.1f}" y="{y_top - 6}" font-size="12" fill="{C_INK}" text-anchor="middle">measured {meas:+.1f}{unit}</text>')
    for i, (label, val, primary) in enumerate(rows):
        y = PAD_T + H_ROW * i + H_ROW / 2
        s.append(f'<text x="{PAD_L - 12}" y="{y + 4}" font-size="13" fill="{C_INK}" text-anchor="end">{esc(label)}</text>')
        if primary:
            s.append(f'<circle cx="{px(val):.1f}" cy="{y}" r="7" fill="{C_BLUE}" stroke="#fff" stroke-width="2"><title>{esc(label)}: {val:+.1f}{unit}</title></circle>')
        else:
            s.append(f'<circle cx="{px(val):.1f}" cy="{y}" r="6" fill="#ffffff" stroke="{C_BLUE}" stroke-width="2.5"><title>{esc(label)}: {val:+.1f}{unit}</title></circle>')
        # value label to the right of the dot, unless it would cross the measured line (within 6 px); then to the left.
        # Band edges are not tested: text over the 12%-opacity band stays legible.
        lx0, lw = px(val) + 13, 54
        if lx0 < px(meas) + 6 and lx0 + lw > px(meas) - 6:
            s.append(f'<text x="{px(val) - 13:.1f}" y="{y + 4}" font-size="12" fill="{C_INK}" text-anchor="end">{val:+.1f}{unit}</text>')
        else:
            s.append(f'<text x="{lx0:.1f}" y="{y + 4}" font-size="12" fill="{C_INK}">{val:+.1f}{unit}</text>')
    ly = H - 8
    s.append(f'<text x="{(PAD_L + W - PAD_R) / 2:.1f}" y="{y_bot + 36}" font-size="12" fill="{C_INK2}" text-anchor="middle">estimated AMX decode boost at prompt 8192 (percent faster per token than Tron in its AVX form)</text>')
    lx = 40
    s.append(f'<circle cx="{lx}" cy="{ly - 4}" r="7" fill="{C_BLUE}" stroke="#fff" stroke-width="2"/><text x="{lx + 12}" y="{ly}" font-size="12" fill="{C_INK2}">route 1: unit measured under load (primary)</text>')
    s.append(f'<circle cx="{lx + 320}" cy="{ly - 4}" r="6" fill="#fff" stroke="{C_BLUE}" stroke-width="2.5"/><text x="{lx + 332}" y="{ly}" font-size="12" fill="{C_INK2}">route 2: unit predicted with an assumed eta</text>')
    s.append(f'<rect x="{lx + 636}" y="{ly - 12}" width="26" height="16" fill="{C_ORANGE}" opacity="0.12"/><line x1="{lx + 640}" y1="{ly - 4}" x2="{lx + 658}" y2="{ly - 4}" stroke="{C_ORANGE}" stroke-width="2"/><text x="{lx + 668}" y="{ly}" font-size="12" fill="{C_INK2}">measured; band = ±3 points (on par)</text>')
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


def parse_thp_experiment(path):
    """exec/results/thp-20260901/thp.txt -> ms per token per (arm, prompt), dTLB counters per (arm, rep), cut-short windows.

    Part A blocks start "### model=... arm=A ctx=C ... rep=R" and end with a runtron line "... or X ms/tok".
    Part B blocks start "### arm=A group=G rep=R" and hold perf stat counter lines "N  name"; a block whose run
    ended before the 12 s window closed carries the line RUN-ENDED-DURING-WINDOW.
    """
    if not os.path.exists(path):
        return None
    ms, counters, truncated, cur = {}, {}, {}, None
    for line in open(path):
        m = re.match(r"### model=\S+ arm=(\w+) ctx=(\d+) .* rep=(\d+)", line)
        if m:
            cur = ("A", m.group(1), m.group(2), None)
            continue
        m = re.match(r"### arm=(\w+) group=(\w+) rep=(\d+)", line)
        if m:
            cur = ("B", m.group(1), int(m.group(3)), m.group(2))
            continue
        if line.startswith("### "):
            cur = None
            continue
        if cur and cur[0] == "A":
            m = re.search(r"or ([\d.]+) ms/tok", line)
            if m:
                ms.setdefault((cur[1], cur[2]), []).append(float(m.group(1)))
        elif cur and cur[0] == "B":
            if "RUN-ENDED-DURING-WINDOW" in line:
                truncated.setdefault((cur[1], cur[2]), set()).add(cur[3])
            m = re.match(r"\s*([\d,]+)\s+(cycles|ld_walk_4k|ld_walk_2m4m|ld_walk_active)\b", line)
            if m:
                counters.setdefault((cur[1], cur[2]), {})[m.group(2)] = int(m.group(1).replace(",", ""))
    return {"ms_per_tok_median": {k: median(v) for k, v in ms.items()}, "ms_per_tok_runs": ms, "counters": counters, "truncated": truncated}


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
        names = [("cycles", "cycles per unit (includes the barrier wait after each layer)"), ("instructions", "instructions per unit"), ("ipc", "instructions per cycle"),
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
    warnings_html = "".join(f"<li>{esc(w.replace('AMX numbers provisional', 'AMX numbers not final'))}</li>" for w in M.get("warnings", []))  # same plain word as the prose (jhan, 2026-09-03 comment)

    # ---- section 10, page sizes and THP (every number from the data files; the 2026-09-01 Tron run is a comparison, not an input)
    mm = re.search(r"^## thp\n(.*)$", m0_txt, re.M)
    thp_mode_line = mm.group(1).strip() if mm else "(not recorded)"
    mm2 = re.search(r"\[(\w+)\]", thp_mode_line)
    thp_mode = mm2.group(1) if mm2 else thp_mode_line
    gb = lambda key: (mr.get(key) or {}).get("per_core_GBs_median")
    r27t, r27n, r1t, r1n, t27t, t27n, t1t, t1n = (gb(k) for k in ("load-t27-thp", "load-t27-none", "load-t1-thp", "load-t1-none", "tile-t27-thp", "tile-t27-none", "tile-t1-thp", "tile-t1-none"))
    r1t_runs = (mr.get("load-t1-thp") or {}).get("per_core_mean") or []
    rel = lambda x, y, nd=1: pct((x / y - 1) * 100, nd) if x and y else "n/a"
    lat_idle = (lat.get("idle_ns_median") or {})
    lat_none, lat_thp = lat_idle.get("mb1024-none"), lat_idle.get("mb1024-thp")
    ubm = D.get("m3_unit_bench", {})
    w0u = lambda cfg: ((ubm.get(cfg) or {}).get("worker0") or {}).get("unit_ns")
    passes_of = lambda cfg: (ubm.get(cfg) or {}).get("passes")
    avx1g, avxthp, amx1g, amxthp = w0u("avx-p130-t27"), w0u("avx-p130-t27-thp"), w0u("amx-p130-t27"), w0u("amx-p130-t27-thp")
    avx_thp_pct, amx_thp_pct = pct(r8.get("avx_thp_pct")), pct(r8.get("amx_thp_pct"))
    avx_thp_abs, amx_thp_abs = f"{abs(r8.get('avx_thp_pct') or 0):.1f}%", f"{abs(r8.get('amx_thp_pct') or 0):.1f}%"
    walks_avx, walks_amx = f1((m6.get("avx") or {}).get("dtlb_ld_walk"), 1), f1((m6.get("amx") or {}).get("dtlb_ld_walk"), 1)
    calib_short = P((b8["unit_avx_us"] - r8["avx_bench_us"]) / b8["unit_avx_us"], 1)
    thp = parse_thp_experiment(THP_FILE)
    if thp:
        cnt, trunc = thp["counters"], thp["truncated"]
        reps = sorted({r for (_, r) in cnt})
        w4 = lambda arm: [cnt[(arm, r)]["ld_walk_4k"] for r in reps]
        w2 = lambda arm: [cnt[(arm, r)]["ld_walk_2m4m"] for r in reps]
        ok_reps = lambda arm: [r for r in reps if not ({"dtlb_mix", "core"} & trunc.get((arm, r), set()))]
        act = lambda arm: [cnt[(arm, r)]["ld_walk_active"] / cnt[(arm, r)]["cycles"] for r in ok_reps(arm)]
        dropped = [(arm, r) for arm in ("base", "thp") for r in reps if r not in ok_reps(arm)]
        mil = lambda xs: " and ".join(f"{x / 1e6:.1f} million" for x in xs)
        thou = lambda xs: " and ".join(f"{x / 1e3:.0f} thousand" for x in xs)
        shares = lambda xs: " and ".join(P(x, 2) for x in xs)
        d4k = pct((sum(w4("thp")) / sum(w4("base")) - 1) * 100, 0)
        d4k_abs = d4k.lstrip("+-")
        msm, msr = thp["ms_per_tok_median"], thp["ms_per_tok_runs"]
        b8192, t8192, b2048, t2048 = msm[("base", "8192")], msm[("thp", "8192")], msm[("base", "2048")], msm[("thp", "2048")]
        d8192, d2048 = (t8192 / b8192 - 1) * 100, (t2048 / b2048 - 1) * 100
        tron_change_max = f"{max(abs(d8192), abs(d2048)):.2f}%"
        spread = lambda arm, ctx: (max(msr[(arm, ctx)]) - min(msr[(arm, ctx)])) / median(msr[(arm, ctx)])
        sp8192, sp2048 = P(spread("base", "8192"), 2), P(spread("base", "2048"), 2)
        nrun = len(msr[("base", "8192")])
        bound = P(max(act("base")), 2)
        drop_txt = "".join(f" (the repeat-{r} window with the switch {'on' if arm == 'thp' else 'off'} is dropped: its run ended before the 12 s window closed, marked RUN-ENDED-DURING-WINDOW in thp.txt)" for arm, r in dropped)
        tron_row = (f"<tr><td>outside this report</td><td>Tron with the mirror on 2 MiB pages: <code>TRON_AMX_MIRROR_THP=1</code> allocates the mirror 2 MiB-aligned and marks it with madvise(MADV_HUGEPAGE); the same binary serves both settings, switch off and switch on; 2026-09-01. "
                    f"The AnonHugePages lines in thp.txt read 0 for both settings because the script queried the timeout wrapper's process, not runtron's. The take-up is shown by the counters: 2 MiB-page load walks rose from {thou(w2('base'))} to {thou(w2('thp'))} per window while 4 KiB-page walks fell {d4k_abs} (write-up, section 7.6).</td>"
                    f"<td>4 KiB-page load walks per 12 s window on the 28 app cores (two repeats): {mil(w4('base'))} → {mil(w4('thp'))} ({d4k}). Share of the 28 app cores' cycles with a page walk in progress: {shares(act('base'))} → {shares(act('thp'))}{drop_txt}; walk-active and cycle counts come from separate runs of the same repeat index, one run per counter group. "
                    f"runtron's reported time per generated token, medians of {nrun} runs: prompt 8192 {f1(b8192, 3)} → {f1(t8192, 3)} ms ({pct(d8192, 2)}), prompt 2048 {f1(b2048, 3)} → {f1(t2048, 3)} ms ({pct(d2048, 2)}); the write-up's fence-period medians for the same runs (7921 → 7919 µs and 4654 → 4667 µs) agree within 0.3%.</td>"
                    f"<td>files <code>exec/results/thp-20260901/thp.txt</code>; write-up PR3879/make-sense-amx-vs-avx.html, section 7.6 (that section quotes about 1.6% of app-core cycles for the walks, a figure its own counter table does not reproduce; thp.txt's counts give {shares(act('base'))})</td></tr>")
        tron_intro = f"In Tron, moving the mirror from 4 KiB to 2 MiB pages changed the time per generated token by {tron_change_max} at most on the medians of {nrun} runs (the 2026-09-01 experiment; details in the table below). That experiment is a measured AMX Tron run, so under the plan's rules it is a comparison and not an input."
        tron_bullet = (f" and {shares(act('base'))} of the 28 app cores' cycles in Tron (walk-active cycles divided by cycles, both from thp.txt). Removing {d4k_abs} of Tron's 4 KiB-page load walks changed its time per token by {tron_change_max} at most on the medians, less than the run-to-run spread ({sp2048} at prompt 2048, {sp8192} at prompt 8192). "
                       f"The walks occupied {bound} of the app cores' cycles on average, so removing them could gain at most about that share of the token time. At prompt 8192 the change was {pct(d8192, 2)} against a spread of {sp8192}, so most of the walk time is hidden behind other waiting (hypothesis: behind the memory wait the unit already has; a walk-active count on the benchmark against its unit time would test it). "
                       f"At prompt 2048 the spread ({sp2048}) is larger than the bound, so that cell cannot tell.")
    else:
        tron_row, tron_bullet = "", ""
        tron_intro = "The 2026-09-01 Tron experiment file (exec/results/thp-20260901/thp.txt) was not found."
    m7_alloc = ""
    m7log = f"{RES}/m7-cell-disable-c8192-r2.log"
    if os.path.exists(m7log):
        mm3 = re.search(r"(Allocating \d+ hugepages from \S+ on numa \d+)", open(m7log, errors="replace").read())
        m7_alloc = f'; the M7 log records "{esc(mm3.group(1))}"' if mm3 else ""
    chk = {}
    if os.path.exists(f"{RES}/check.txt"):
        for mm4 in re.finditer(r"check variant=(avx|amx) .*? v/s ([\d.e+-]+) (OK|FAIL)", open(f"{RES}/check.txt").read()):
            chk[mm4.group(1)] = (float(mm4.group(2)), mm4.group(3))
    chk_txt = (f"file check.txt: {chk['avx'][1]} on the AVX path and {chk['amx'][1]} on the AMX path, worst relative error of the normalized output {chk['avx'][0]:.1e} and {chk['amx'][0]:.1e} against a gate of 1e-3"
               if "avx" in chk and "amx" in chk else "check.txt missing")
    # ---- M6 explanation of the instructions-per-cycle gap (counts from unit_bench.cpp qk_mirror_128x4 + weights_times_v_128x4)
    m6a, m6x = (m6.get("avx") or {}), (m6.get("amx") or {})
    n_tdp, n_tld, n_tst, n_tz = 32, 40, 12, 12
    tdp_cyc = (insn.get("tdp_tp") or {}).get("core_cycles_per_insn")
    vdp_cyc = (insn.get("vdp_tp16") or {}).get("core_cycles_per_insn")
    tld_cyc = (insn.get("tld_l1") or {}).get("core_cycles_per_insn")
    amx_unit_us = r8["s_transfer_variants_us"]["none"]
    tmul_us = (n_tdp * tdp_cyc / r8["amx_serving_clock_ghz"] / 1000) if tdp_cyc else None
    ipc_txt = ""
    if m6a.get("instructions") and m6x.get("instructions") and tdp_cyc and vdp_cyc and tld_cyc:
        ipc_txt = (f"<p class=\"small\"><strong>Why the AMX path's instructions per cycle are low.</strong> The AMX path runs {f1(m6x['instructions'], 0)} instructions per unit against {f1(m6a['instructions'], 0)} on the AVX path ({m6a['instructions'] / m6x['instructions']:.1f} times fewer), in {f1(m6x['cycles'], 0)} cycles against {f1(m6a['cycles'], 0)} ({P(1 - m6x['cycles'] / m6a['cycles'], 0)} fewer). "
                   f"Instructions per cycle therefore falls from {f1(m6a.get('ipc'), 2)} to {f1(m6x.get('ipc'), 2)}: the instructions went away, most of the cycles did not. Two facts explain it. First, each AMX instruction does more work and takes longer: per unit the AMX kernel issues {n_tdp} TDPBF16PS tile multiplies, {n_tld} TILELOADD tile loads (1 KiB each), {n_tst} tile stores and {n_tz} tile clears (unit_bench.cpp, the copy of qk_mirror_128x4 and weights_times_v_128x4), and M5 measured TDPBF16PS at {f1(tdp_cyc, 1)} core cycles per instruction and TILELOADD at {f1(tld_cyc, 1)}, against {f1(vdp_cyc, 1)} for the AVX path's VDPBF16PS. "
                   f"Second, on both paths most of a unit's time is waiting for its 32 KiB of keys and values, not executing instructions: the data wait is {P(1 - r8['avx_compute_us'] / r8['avx_bench_us'], 0)} of the AVX unit and {P(1 - r8['amx_compute_us'] / amx_unit_us, 0)} of the AMX unit (section 5). The report therefore analyzes the unit as compute plus data wait (section 5), not as instructions per cycle; the yardstick is time per unit, {f1(amx_unit_us, 2)} against {f1(r8['avx_bench_us'], 2)} µs. "
                   f"The tile-multiply unit itself is busy for about {f1(tmul_us, 2)} µs of the {f1(amx_unit_us, 2)} µs unit ({P(tmul_us / amx_unit_us, 0)}; est., {n_tdp} multiplies × {f1(tdp_cyc, 1)} cycles at {f1(r8['amx_serving_clock_ghz'], 3)} GHz). Insufficient data for the measured occupancy and for the stall breakdown: M6 did not count EXE.AMX_BUSY (raw event 0xb7, umask 0x02, the counter used on Tron in the 2026-08-31 perf-stat rounds) and this perf has no top-down metrics; a rerun of M6 with that event would measure the occupancy directly.</p>\n")
    chk_amx = f"{chk['amx'][0]:.1e}" if "amx" in chk else "n/a"
    hs = ub8.get("amx_hot_split") or {}
    hot_split_txt = f"QK {f1(hs.get('qk_ns'), 0)}, softmax pieces {f1(hs.get('softmax_ns'), 0)}, PV {f1(hs.get('pv_ns'), 0)}, state update {f1(hs.get('state_ns'), 0)} ns" if hs else ""
    chk_avx = f"{chk['avx'][0]:.1e}" if "avx" in chk else "n/a"
    tps = lambda cfg: [t for t in ((ubm.get(cfg) or {}).get("timed_phase_s") or []) if t]
    tp_rng = lambda cfg: (f"{min(tps(cfg)):.1f} to {max(tps(cfg)):.1f}" if len(tps(cfg)) > 1 else (f"{tps(cfg)[0]:.1f}" if tps(cfg) else "n/a"))
    long_passes = (ubm.get("amx-hot-t27-long") or {}).get("passes")
    long_vs_hot = pct((ub8["amx_hot_long"] / ub8["amx_hot"] - 1) * 100) if ub8.get("amx_hot_long") and ub8.get("amx_hot") else "n/a"
    ctl_amx, arena_amx, ctl_avx, arena_avx = ub8.get("amx_t27_ctl"), ub8.get("amx_t27_arena"), ub8.get("avx_t27_ctl"), ub8.get("avx_t27_arena")
    ctl_pcts = [abs(c / a - 1) * 100 for c, a in ((ctl_amx, arena_amx), (ctl_avx, arena_avx)) if c and a]
    ctl_max_pct = f"{max(ctl_pcts):.1f}%" if ctl_pcts else "n/a"
    units_w0, ranges_w0 = b8.get("units_w0"), b8.get("ranges_w0")
    per_range = f1(units_w0 / ranges_w0, 0) if units_w0 and ranges_w0 else "n/a"
    p34_amx, p6_amx = w0u("amx-p34-t27"), w0u("amx-p6-t27")
    thp_html = f"""<h3 id="thp">Page sizes and THP: what was captured and what it shows</h3>
<p class="small">THP (transparent huge pages) is the kernel backing ordinary program memory with 2 MiB pages instead of 4 KiB pages; "Words used here" defines the terms. THP enters this report in three places as an input or a sensitivity: as the page size of the streaming-rate buffers (M1); as one sensitivity run of the unit benchmark (M3: 2 MiB pages instead of 1 GiB pages); and as the reason the K mirror is placed on 4 KiB pages in Tron, which in the benchmark's AMX unit costs {walks_amx} dTLB walks per unit (M6; Tron's own per-unit count was not measured). Two comparisons add to it: the latency chase on 4 KiB against 2 MiB pages (M2) and the 2026-09-01 Tron experiment. None of them changes the estimate. The 27-reader streaming rate differs by {rel(r27t, r27n)} between 4 KiB and 2 MiB pages (M1). In the benchmark, 2 MiB pages instead of 1 GiB pages make the AMX unit {amx_thp_abs} slower (M3). {tron_intro}</p>
<p class="small"><strong>Where each block of memory is placed.</strong> The machine's THP setting is "{esc(thp_mode)}" (M0): only a memory region the program marks with madvise(MADV_HUGEPAGE) gets 2 MiB pages. Tron's K and V pages (the 64-token KV pages) are on 1 GiB memory pages from the reserved pool (Tron's <code>--hugepage_file</code> option selects that pool{m7_alloc}). Tron's K mirror is ordinary memory from operator new (the C++ standard allocator) with 64-byte alignment (kv_cache.hpp, maybe_allocate_mirror_arena), not marked, so it is on 4 KiB pages. The benchmark reproduces both placements: keys and values by mmap with MAP_HUGETLB (the request for pages from the reserved pool) on 1 GiB pages, the mirror with madvise(MADV_NOHUGEPAGE) on 4 KiB pages. The kernel's per-process page-size report (/proc/self/smaps_rollup, read by unit_bench) confirms the placement in every M3 record; the M3 table's "pages obtained" column shows it as "1g/4k" (keys and values on 1 GiB pages, mirror on 4 KiB pages) and, for the two -thp rows, "thp/4k". Why the size matters: the TLB holds one entry per page. On this core the first-level load TLB has 96 entries for 4 KiB pages, 32 for 2 MiB pages and 8 for 1 GiB pages (stores have a separate 16-entry TLB). The second level has two arrays of 1024 entries each: one shared by 4 KiB and 2 MiB pages, one shared by 4 KiB and 1 GiB pages (CPUID leaf 0x18, the CPU instruction that reports its own TLB sizes; captured 2026-08-26). An AVX unit reads 32 KiB of keys and values, which lie inside one 1 GiB page. An AMX unit reads 16 KiB of K mirror plus 16 KiB of values; the mirror spans four 4 KiB pages in the benchmark, whose mirror region is 2 MiB-aligned, and four or five in Tron, whose arena is only 64-byte aligned (not measured).</p>
<div class="tablewrap"><table><tr><th>step</th><th>measurement</th><th>result</th><th>where in this report</th></tr>
<tr><td>M0</td><td>THP setting of delphi-3bda</td><td><code>{esc(thp_mode_line)}</code> (the bracketed word is the active setting)</td><td>M0 record above</td></tr>
<tr><td>M1</td><td>per-core streaming rate on 2 MiB pages against 4 KiB pages (the M1 table's page labels thp and none); the tile-load rows on 4 KiB pages stand for the production K mirror, which is on 4 KiB pages (plan, M1); memrate (the streaming-rate test program of M1, source memrate.c) has no 1 GiB option</td><td>27 readers: {f1(r27t, 2)} against {f1(r27n, 2)} GB/s ({rel(r27t, r27n)}); 1 reader: {f1(r1t, 2)} against {f1(r1n, 2)} GB/s ({rel(r1t, r1n)}; one 4 KiB run against the median of three 2 MiB runs that range from {f1(min(r1t_runs), 2) if r1t_runs else 'n/a'} to {f1(max(r1t_runs), 2) if r1t_runs else 'n/a'} GB/s, so this single-reader difference is not settled; for tile loads with 1 reader the 4 KiB run was faster, {f1(t1n, 2)} against {f1(t1t, 2)} GB/s); tile loads, 27 readers: {f1(t27t, 2)} against {f1(t27n, 2)} GB/s ({rel(t27t, t27n)})</td><td>M1 table above; R<sub>core</sub>(27) of sections 5, 8 and 9 is the 2 MiB value</td></tr>
<tr><td>M2</td><td>memory latency by pointer chase (each load's address comes from the previous load's value) over a 1024 MiB buffer, 4 KiB against 2 MiB pages</td><td>{f1(lat_none, 1)} against {f1(lat_thp, 1)} ns: 4 KiB pages add {f1(lat_none - lat_thp, 0) if lat_none and lat_thp else 'n/a'} ns per access. By construction nearly every 4 KiB access misses the TLB (262,144 pages against 1,120 entries), while the 512 pages of 2 MiB fit the second-level TLB (inferred from the sizes, not counted)</td><td>M2 above</td></tr>
<tr><td>M3</td><td>unit with keys and values on 2 MiB pages instead of 1 GiB pages (mirror on 4 KiB pages in both), 27 threads, prompt 8192, single-arena layout; the 2 MiB number is one run of {passes_of('avx-p130-t27-thp')} passes, the 1 GiB number the median of three repeats of {passes_of('avx-p130-t27')} passes</td><td>AVX {f1(avx1g, 0)} → {f1(avxthp, 0)} ns ({avx_thp_pct}); AMX {f1(amx1g, 0)} → {f1(amxthp, 0)} ns ({amx_thp_pct})</td><td>sections 1 and 4 (section 9 names the page-size round and refers back to section 4); M3 table above (rows ending in -thp)</td></tr>
<tr><td>M6</td><td>dTLB load walks completed per unit</td><td>AVX {walks_avx}; AMX {walks_amx} (the AMX path reads 16 KiB of mirror per unit on 4 KiB pages; the AVX path's streamed bytes, keys and values, are all on 1 GiB pages, and its small per-thread buffers stay in the TLB)</td><td>M6 table above</td></tr>
{tron_row}</table></div>
<p class="small"><strong>What it shows.</strong></p>
<ul class="small">
<li>Page size does not explain the calibration gap. 2 MiB pages instead of 1 GiB pages make the AVX unit {avx_thp_abs} slower (single-arena layout), while the benchmark's AVX unit is {calib_short} below Tron's (book layout, section 4).</li>
<li>The AMX unit changes little with page size ({amx_thp_abs} slower on 2 MiB pages than on 1 GiB pages). Together with the page-order run (pages placed at random: AVX {pct(r8.get('avx_shuffle_pct'))}, AMX {pct(r8.get('amx_shuffle_pct'))}) this forms the first of the two facts behind round 2's transfer rule "none" (the two facts: section 1; the rule: sections 4 and 9): layout settings that move the AVX unit move the AMX unit little.</li>
<li>The mirror's 4 KiB pages cost the AMX path {walks_amx} walks per unit in the benchmark{tron_bullet} Either way the model needs no separate THP term. The walk cost is inside the measured AMX unit, because the benchmark keeps the mirror on 4 KiB pages, the page size Tron uses ({walks_amx} walks per unit is the benchmark's count; Tron's per-unit count was not measured).</li>
<li>The one page-size gap: R<sub>core</sub>(27), the memory-time input, was measured on 2 MiB pages because memrate cannot use 1 GiB pages, while Tron's K and V are on 1 GiB pages. It enters only the decomposition (memory time and eta) of sections 5 and 8, the pre-AMX bracket rows and the "AMX unit modeled with the AVX path's eta" row of section 8, and the eta-above-1 trigger of the L3-residency round in section 9. The primary estimate of round 2 and the pre-registered band take the AMX unit as measured and do not depend on it. The 1 GiB rate itself is Insufficient data; memrate with MAP_HUGETLB 1 GiB buffers would measure it. For scale: the step from 4 KiB to 2 MiB pages changed the 27-reader rate by only {rel(r27t, r27n)} (M1).</li>
</ul>
"""


    # ---- section 5 addendum: where the AMX instruction-rate advantage goes (asked in two comment threads, 2026-09-03)
    hot_amx = D["m3_unit_bench"]["amx-hot-t27"]["worker0"]
    hot_avx = D["m3_unit_bench"]["avx-hot-t27"]["worker0"]
    m5 = D["m5_insn"]
    tdp_cyc = m5["tdp_tp"]["core_cycles_per_insn"]      # TDPBF16PS, throughput loop
    tld_cyc = m5["tld_l1"]["core_cycles_per_insn"]      # TILELOADD, 1 KiB tile in L1
    vdp_cyc = m5["vdp_tp8"]["core_cycles_per_insn"]     # VDPBF16PS, 8 chains
    dot_cyc = m5["dotter_l1"]["core_cycles_per_insn"]   # dotter per-token dot (4 VDPBF16PS + reduction)
    dot_ghz = m5["dotter_l1"]["core_mhz_median"] / 1000.0
    amx_macs_cyc = 16 * 16 * 32 / tdp_cyc               # multiply-adds per cycle, one tile multiply = 16x16 outputs x 32 terms
    avx_macs_cyc = 32 / vdp_cyc                         # one VDPBF16PS = 16 lanes x 2 pairs
    useful_rows = 4 / 16                                # decode: 4 query heads per KV head fill 4 of the 16 tile rows
    tile_floor_cyc = 32 * tdp_cyc + 40 * tld_cyc
    tile_floor_ns = tile_floor_cyc / r8["amx_hot_clock_ghz"]
    dot_floor_ns = 256 * dot_cyc / dot_ghz              # 4 heads x 64 tokens dot products per page
    amx_mm = hot_amx["qk_ns"] + hot_amx["pv_ns"]
    avx_mm = hot_avx["qk_ns"] + hot_avx["pv_ns"]
    amx_cw = hot_amx["softmax_ns"] + hot_amx["state_ns"]
    avx_cw = hot_avx["common_ns"]
    # Tron's own tile-unit busy counter (EXE.AMX_BUSY, perf-stat round 3 of 2026-09-01, arm fmirror, 28 app cores, 12 s windows): comparison only
    ps3_path = f"{HOME}/workspace/intel-AMX/exec/results/perfstat3-20260901/parsed.json"
    ps3 = json.load(open(ps3_path))
    busy = ps3["fmirror"]["exe_amx_busy"]
    busy_per_s = (sum(busy) / len(busy)) / 12.0
    units_per_s = 36 * 8 * 130 * 1e6 / hist["mirror-8192"]["period"]
    busy_cyc_unit = busy_per_s / units_per_s
    est_cyc_unit = 32 * tdp_cyc
    busy_us_unit = busy_cyc_unit / r8["amx_serving_clock_ghz"] / 1000.0
    tron_amx_unit_us = hist["mirror-8192"]["qk"] + hist["mirror-8192"]["common"] + hist["mirror-8192"]["pv"]
    eff_rows = [
        ("Multiply-adds per core cycle of one instruction stream (M5)", f"{avx_macs_cyc:.0f} (VDPBF16PS: 32 per {vdp_cyc:.1f} cycles)", f"{amx_macs_cyc:.0f} (TDPBF16PS: 8,192 per {tdp_cyc:.1f} cycles)", f"{amx_macs_cyc/avx_macs_cyc:.0f}x"),
        ("Useful multiply-adds per cycle: 4 of the 16 tile rows carry data", f"{avx_macs_cyc:.0f}", f"{amx_macs_cyc*useful_rows:.0f}", f"{amx_macs_cyc*useful_rows/avx_macs_cyc:.0f}x"),
        ("Matrix-multiply phases of the hot unit, QK + PV (ns, M3 hot-t27)", f"{avx_mm:,.0f} (dotter loop rate: {dot_floor_ns:,.0f} for QK, measured {hot_avx['qk_ns']:,.0f})", f"{amx_mm:,.0f} (tile instructions alone: {tile_floor_ns:,.0f}, from M5)", f"{avx_mm/amx_mm:.1f}x"),
        ("Whole hot unit (ns): softmax pieces + state update are {} and {} ns".format(f"{avx_cw:,.0f}", f"{amx_cw:,.0f}"), f"{hot_avx['unit_ns']:,.0f}", f"{hot_amx['unit_ns']:,.0f}", f"{hot_avx['unit_ns']/hot_amx['unit_ns']:.1f}x"),
        ("Core clock under the 27-thread load (GHz, M4)", f"{r8['avx_hot_clock_ghz']:.3f}", f"{r8['amx_serving_clock_ghz']:.3f}", pct(100 * (r8['amx_serving_clock_ghz'] / r8['avx_hot_clock_ghz'] - 1))),
        ("Unit under load, book layout (ns, M3): data wait {} and {} µs".format(f1(r8.get('avx_data_wait_us'), 2), f1(r8.get('amx_data_wait_us'), 2)), f"{avx_t27*1000:,.0f}", f"{amx_t27*1000:,.0f}", f"{avx_t27/amx_t27:.2f}x"),
    ]
    eff_tbl = "".join(f"<tr><td>{esc(a)}</td>{td(esc(b))}{td(esc(c))}{td(esc(d))}</tr>" for a, b, c, d in eff_rows)
    eff_html = f"""<h3 id="efficiency">Why the AMX path's compute looks inefficient: where the factor of {amx_macs_cyc/avx_macs_cyc:.0f} goes</h3>
<p>Asked in the comment threads on the M6 table and on this section. One tile multiply (TDPBF16PS) does {amx_macs_cyc/avx_macs_cyc:.0f} times the multiply-adds per cycle of one vector multiply (VDPBF16PS), both measured in M5, yet the AMX unit is only {hot_avx['unit_ns']/hot_amx['unit_ns']:.1f} times shorter with the page hot in L2 and {avx_t27/amx_t27:.2f} times shorter under load. No separate experiment was run for this question; the table below traces the factor through the campaign's existing measurements, one step per row, and each step is a measured fact, not a guess.</p>
<div class="tablewrap"><table><tr><th>Step (prompt 8192)</th><th class="num">AVX path</th><th class="num">AMX path</th><th class="num">AVX ÷ AMX</th></tr>{eff_tbl}</table></div>
<ul>
<li><strong>Padding.</strong> A tile multiply always processes 16 rows. In decode a KV head serves 4 query heads, so 4 of the 16 rows of the query and probability tiles carry data and 12 are zero (unit_bench.cpp, as in Tron; section 11). Three quarters of the tile unit's work is on zeros. This alone cuts the useful advantage from {amx_macs_cyc/avx_macs_cyc:.0f}x to {amx_macs_cyc*useful_rows/avx_macs_cyc:.0f}x.</li>
<li><strong>Long, few instructions, plus copies.</strong> Per unit the AMX path issues 32 tile multiplies at {tdp_cyc:.1f} cycles and 40 tile loads at {tld_cyc:.1f} cycles (M5), {tile_floor_cyc:,.0f} cycles = {tile_floor_ns:,.0f} ns at the AMX clock; the QK and PV phases measure {amx_mm:,.0f} ns hot, so about {100*tile_floor_ns/amx_mm:.0f}% of those phases is tile instructions and the rest is the score copy out of the 16-row tile, the P pack and the output copy (section 11, "What was timed"). The AVX path's QK phase runs at the dotter loop's measured rate: 256 dot products per page × {dot_cyc:.1f} cycles = {dot_floor_ns:,.0f} ns against {hot_avx['qk_ns']:,.0f} ns measured, so its hot compute is instruction-bound with nothing to remove.</li>
<li><strong>Common work grows.</strong> The softmax pieces and the state update are vector (AVX) code on both paths. On the AVX path they take {avx_cw:,.0f} ns hot; on the AMX path they take {amx_cw:,.0f} ns hot ({100*amx_cw/hot_amx['unit_ns']:.0f}% of the hot unit). The AMX version includes the copies between the 16-row tile buffers and the 4 rows of real data (section 11, "What was timed"); the split between those copies and the arithmetic was not timed separately. This is why the whole hot unit gains {hot_avx['unit_ns']/hot_amx['unit_ns']:.1f}x while its matrix-multiply phases gain {avx_mm/amx_mm:.1f}x.</li>
<li><strong>Clock.</strong> Under the 27-thread load the AMX runs hold {r8['amx_serving_clock_ghz']:.3f} GHz against {r8['avx_hot_clock_ghz']:.3f} GHz for the AVX runs (M4), {abs(100 * (r8['amx_serving_clock_ghz'] / r8['avx_hot_clock_ghz'] - 1)):.1f}% lower.</li>
<li><strong>Data wait.</strong> Under load the AMX unit waits {f1(r8.get('amx_data_wait_us'), 2)} µs of its {amx_t27:.2f} µs for bytes (the decomposition above). The tile unit itself is busy about {est_cyc_unit:,.0f} cycles per unit by M5 (32 × {tdp_cyc:.1f}), {est_cyc_unit / r8['amx_serving_clock_ghz'] / 1000:.2f} µs, {100 * est_cyc_unit / r8['amx_serving_clock_ghz'] / 1000 / amx_t27:.0f}% of the unit (est.). Tron's own counter agrees: in the perf-stat round of 2026-09-01 (arm fmirror, 28 app cores, two 12 s windows) EXE.AMX_BUSY counted {busy_per_s/1e9:.2f} billion busy cycles per second while Tron generated {1e6/hist['mirror-8192']['period']:.0f} tokens per second (the same day's arena-mirror run, single-attn-20260901/summary.json; 36 layers × 8 KV heads × 130 pages = 37,440 units per token), that is {busy_cyc_unit:,.0f} busy cycles per unit, about {busy_us_unit:.2f} µs of Tron's {tron_amx_unit_us:.2f} µs AMX unit ({100*busy_us_unit/tron_amx_unit_us:.0f}%). That is a measured AMX Tron number, so under the plan's rules it is a comparison, not an input.</li>
</ul>
<p class="small">The instructions-per-cycle figures of M6 (0.73 on the AVX path, 0.12 on the AMX path; section 10, "Why the AMX path's instructions per cycle are low") follow from the same facts: the AMX path's instructions are few and long, and most cycles on both paths are the data wait, so instructions per cycle does not measure work done here. Not measured in this campaign: the benchmark's own tile-unit occupancy (EXE.AMX_BUSY was not in the M6 event list) and a stall breakdown by phase (this perf build has no top-down metrics); the Tron counter above is the nearest measurement.</p>"""

    # ---- section 2 addendum: two routes to the estimate (asked by jhan, 2026-09-03 evening PDT)
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from model import chain as _chain
    cov8, ext8 = c["coverage"], r8["amx_extras_us"]
    comp_avx, comp_amx, mem = r8["avx_compute_us"], r8["amx_compute_us"], r8["memory_time_us_at_r_core_27"]
    def _b(u):
        return _chain(b8, u, cov8, ext8)["boost_pct"]
    assert abs(_b(r8["unit_amx_primary_us"]) - c["boost_pct"]) < 1e-6, "chain form drifted from model.py"
    assert abs(_b(r8["bracket_eta1_us"]) - r8["chain_bracket_eta1"]["boost_pct"]) < 1e-6
    eta_tron = (comp_avx + mem - b8["unit_avx_us"]) / min(comp_avx, mem)
    u_tron_eta = max(comp_amx, mem) + (1 - eta_tron) * min(comp_amx, mem)
    ld_amx = D["m3_unit_bench"]["amx-p130-t27-book24"]["worker0"]
    ld_avx = D["m3_unit_bench"]["avx-p130-t27-book24"]["worker0"]
    sa, sv = r8["amx_clock_scale"], r8["avx_clock_scale"]
    mm_amx_hot = (hot_amx["qk_ns"] + hot_amx["pv_ns"]) / 1000 * sa
    cw_amx_hot = (hot_amx["softmax_ns"] + hot_amx["state_ns"]) / 1000 * sa
    cw_amx_ld = (ld_amx["softmax_ns"] + ld_amx["state_ns"]) / 1000
    # the Notion page's recipe (section 0.2, step 4): "Predicted AMX unit = the larger of the kernel cost and the memory floor, plus the
    # common work from step 1"; step 1 is the AVX run, so the common work is Tron's AVX common work. Step 4 also expects the kernel to
    # reach about 90% of the streaming-reader rate, which lengthens the memory floor by 1/0.9.
    cw_avx_tron = b8["common_avx_us"]
    u_notion = max(mm_amx_hot, mem) + cw_avx_tron
    u_notion_90 = max(mm_amx_hot, mem / 0.9) + cw_avx_tron
    u_notion_ld = max(mm_amx_hot, mem) + cw_amx_ld
    mem16 = mem / 2
    def _eta(comp, m, t):
        return (comp + m - t) / min(comp, m)
    qk_avx_c, pv_avx_c = hot_avx["qk_ns"] / 1000 * sv, hot_avx["pv_ns"] / 1000 * sv
    qk_amx_c, pv_amx_c = hot_amx["qk_ns"] / 1000 * sa, hot_amx["pv_ns"] / 1000 * sa
    qk_avx_t, pv_avx_t = ld_avx["qk_ns"] / 1000, ld_avx["pv_ns"] / 1000
    qk_amx_t, pv_amx_t = ld_amx["qk_ns"] / 1000, ld_amx["pv_ns"] / 1000
    eta_qk_avx, eta_pv_avx = _eta(qk_avx_c, mem16, qk_avx_t), _eta(pv_avx_c, mem16, pv_avx_t)
    eta_qk_amx, eta_pv_amx = _eta(qk_amx_c, mem16, qk_amx_t), _eta(pv_amx_c, mem16, pv_amx_t)
    qk2 = max(qk_amx_c, mem16) + (1 - eta_qk_avx) * min(qk_amx_c, mem16)
    pv2 = max(pv_amx_c, mem16) + (1 - eta_pv_avx) * min(pv_amx_c, mem16)
    u_phase_hot, u_phase_ld = qk2 + pv2 + cw_amx_hot, qk2 + pv2 + cw_amx_ld
    # the Notion page's own memory floor (section 0.2, step 2): "15.7 to 15.9 GB/s per core ... Memory floor per unit = 32 KiB / that rate = 2.06 us"
    NOTION_FLOOR_US = 2.06
    u_notion_page = max(mm_amx_hot, NOTION_FLOOR_US) + cw_avx_tron
    routes = [
        # (table description, short label for the figure, eta text, unit, boost, where, primary)
        ("Route 1: the AMX unit measured under the 27-thread load (eta solved from it: %.2f)" % r8["amx_eta"], "route 1: measured unit (primary)", "measured", r8["unit_amx_primary_us"], c["boost_pct"], "sections 6 and 9; model.json chain_primary", True),
        ("Route 2, eta = 1 (roofline): max(compute, memory time)", "eta = 1, roofline", "1", r8["bracket_eta1_us"], r8["chain_bracket_eta1"]["boost_pct"], "section 8, reference row", False),
        ("Route 2, eta = 0 (serial): compute + memory time", "eta = 0, serial", "0", r8["bracket_eta0_us"], r8["chain_bracket_eta0"]["boost_pct"], "section 8, reference row", False),
        ("Route 2, eta solved from the benchmark's AVX unit (%.3f µs, section 4) with the AVX compute, then applied to the AMX compute" % r8["avx_bench_us"], "eta from the benchmark's AVX unit", "%.2f" % r8["avx_eta"], r8["unit_amx_modeled_with_avx_eta_us"], r8["chain_modeled_with_avx_eta"]["boost_pct"], "section 8, reference row", False),
        ("Route 2, eta solved from Tron's own AVX unit (%.3f µs, section 3, a pre-AMX input) with the AVX compute, then applied to the AMX compute" % b8["unit_avx_us"], "eta from Tron's AVX unit", "%.2f" % eta_tron, u_tron_eta, _b(u_tron_eta), "computed here (2026-09-03)", False),
        ("Route 2, the Notion page's recipe as written: max(matrix-multiply compute %.3f µs (QK + PV, page hot in L2), the page's own memory floor %.2f µs) + the AVX run's common work (%.3f µs, Tron M7)" % (mm_amx_hot, NOTION_FLOOR_US, cw_avx_tron), "Notion recipe, page's 2.06 µs floor", "1 (matrix multiplies only)", u_notion_page, _b(u_notion_page), "computed here (inputs: M3 run amx-hot-t27, the AMX unit with its page hot in L2 on 27 threads; the Notion page's floor; M7)", False),
        ("Route 2, the same recipe with this report's measured memory time (%.3f µs) in place of the page's floor" % mem, "Notion recipe, measured memory time", "1 (matrix multiplies only)", u_notion, _b(u_notion), "computed here (M3 run amx-hot-t27; M1 streaming rate; M7)", False),
        ("Route 2, the same recipe with the page's own expectation that the kernel reaches 90%% of the streaming rate (memory time ÷ 0.9 = %.3f µs)" % (mem / 0.9), "Notion recipe, 90% of the rate", "1 (matrix multiplies only)", u_notion_90, _b(u_notion_90), "computed here", False),
        ("Route 2, the same recipe with the AMX path's common work as measured under load (%.3f µs) in place of the AVX run's (%.3f µs)" % (cw_amx_ld, cw_avx_tron), "Notion recipe, AMX common work", "1 (matrix multiplies only)", u_notion_ld, _b(u_notion_ld), "computed here (inputs: M3 run amx-p130-t27-book24, the AMX unit under load with Tron's book layout; M1)", False),
        ("Route 2 per phase: QK and PV each against 16 KiB, with the AVX path's per-phase etas (QK %.2f, PV %.2f); common work hot in L2 (%.3f µs)" % (eta_qk_avx, eta_pv_avx, cw_amx_hot), "per phase, common work hot", "per phase", u_phase_hot, _b(u_phase_hot), "computed here; no valid per-phase eta for AMX (text)", False),
        ("Route 2 per phase, with the common work as measured under load (%.3f µs)" % cw_amx_ld, "per phase, common work loaded", "per phase", u_phase_ld, _b(u_phase_ld), "computed here", False),
    ]
    routes_tbl = "".join(f"<tr><td>{i + 1}</td><td>{esc(d)}</td>{td(esc(e))}{td(f1(u, 3))}{td(pct(bst))}{td(pct(bst - meas, 1).replace('%', ' pts'))}<td>{esc(w)}</td></tr>" for i, (d, _l, e, u, bst, w, p) in enumerate(routes))
    routes_vals = [bst for _d, _l, _e, _u, bst, _w, _p in routes] + [meas]
    routes_svg = routes_dot_svg([(l, bst, p) for _d, l, _e, _u, bst, _w, p in routes], meas, min(0, min(routes_vals) - 2), max(routes_vals) + 4, "The estimate under each way of obtaining the AMX unit")
    bracket_lo, bracket_hi = r8["chain_bracket_eta0"]["boost_pct"], r8["chain_bracket_eta1"]["boost_pct"]
    r2_vals = [bst for _d, _l, _e, _u, bst, _w, p in routes if not p]
    from decimal import Decimal, ROUND_HALF_UP
    def f3h(x):  # three decimals, round half up (1.1375 -> 1.138), so the text agrees with the ns tables of section 10
        return str(Decimal(repr(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
    rc27 = r8.get("r_core_27_GBs") or (32768 / mem / 1000.0)
    notion_inputs = "".join(f"<tr><td>{esc(a)}</td><td>{esc(bb)}</td><td>{esc(cc)}</td></tr>" for a, bb, cc in [
        ("kernel cost (QK + PV with the page hot in L2)", f"not given for this machine; this report supplies {mm_amx_hot:.3f} µs (M3 run amx-hot-t27)", f"{mm_amx_hot:.3f} µs, the same"),
        ("memory floor, or memory time", f"{NOTION_FLOOR_US:.2f} µs (32 KiB ÷ 15.9 GB/s, the page's per-core rate)", f"{mem:.3f} µs (32 KiB ÷ {rc27:.2f} GB/s, M1, 27 cores reading at once)"),
        ("overlap of the matrix multiplies with the wait", "eta = 1 assumed (perfect overlap)", f"eta = {r8['amx_eta']:.2f}, solved from the loaded unit"),
        ("common work added", f"{cw_avx_tron:.3f} µs (the AVX run, M7)", f"{cw_amx_ld:.3f} µs (the AMX path under load, M3 run amx-p130-t27-book24)"),
    ])
    routes_html = f"""<h3 id="routes">Two routes to the estimate, and why the report takes route 1</h3>
<p>There are two ways to obtain the AMX unit that the chain of section 6 needs. The chain is the arithmetic that turns one AMX unit time into worker 0's page work, then attention time, then token time, then the boost. <strong>Route 1 measures the unit:</strong> the unit benchmark (M3; a copy of Tron's AMX kernel run outside Tron, section 11) runs it under the 27-thread decode load over Tron's page layout, and its unit timer reads {r8['unit_amx_primary_us']:.3f} µs. <strong>Route 2 predicts the unit</strong> from its parts through the unit line of the model above (the unit formula: unit = max(compute, memory time) + (1 − eta) × min(compute, memory time)). Its inputs are the compute ({comp_amx:.3f} µs, the unit with its page already in L2), the memory time ({mem:.3f} µs: 32 KiB at the per-core streaming rate while 27 cores read at once) and the overlap efficiency eta. Route 1 is the primary of this report (round 2, section 9). The plan pre-registered the measured unit as the primary (action-plan.html, section 8, rule 5). That rule also adjusts the 27-thread benchmark unit by the plan's section 7 calibration rule (the transfer rule, "Words used here"). Round 2 of this report drops that adjustment; the departure is recorded in this report's sections 1 and 4. Route 2 appears as reference rows in section 8 and, in full, in the table below.</p>
<p><strong>Why route 2 is not the primary.</strong> The unit formula has one free number, eta. eta is not measured on its own; it is solved from the unit time measured under the 27-thread load (the "loaded unit" from here on): eta = (compute + memory time − loaded unit) ÷ min(compute, memory time) (model.py, the model script). Put a path's own eta back into the formula and it returns the loaded unit exactly. So with the AMX path's eta ({r8['amx_eta']:.2f}) route 2 is route 1 restated. Without the AMX run under load, eta has to be assumed. The assumption decides the answer. The two edges of the pre-AMX bracket of plan rule 5 run from {pct(bracket_lo)} (eta = 0: compute and memory time add) to {pct(bracket_hi)} (eta = 1: perfect overlap); its third member, the AVX path's eta, gives {pct(r8['chain_modeled_with_avx_eta']['boost_pct'])} (row 4). That range is {bracket_hi - bracket_lo:.1f} points wide; the acceptance rule allows 3 points ("on par", Words used here). eta is also not the same on the two code paths (AVX {r8['avx_eta']:.2f}, AMX {r8['amx_eta']:.2f}), so using the AVX value for the AMX path is an assumption, not a measurement. The two AVX-based values disagree with each other as well: eta solved from the benchmark's AVX unit is {r8['avx_eta']:.2f} ({pct(r8['chain_modeled_with_avx_eta']['boost_pct'])}, row 4); eta solved from Tron's own AVX unit, a pre-AMX input, is {eta_tron:.2f} ({pct(_b(u_tron_eta))}, row 5). Without route 1 no measurement says which row is right, so the uncertainty of route 2 is the spread of its rows, {pct(min(r2_vals))} to {pct(max(r2_vals))} in this table, not the distance of its best row. The plan states the consequence: "Since the composed terms add up to the 27-thread reading by construction, the model's contribution is the decomposition, and the prediction rests on running the production kernel code outside Tron under decode-like load" (action-plan.html, section 8, rule 5). In plain words: compute, memory time and eta are fitted to the measured unit, so they explain the unit but cannot predict it; the prediction is the measurement itself. The same rule requires the bracket (eta = 1, eta = 0 and the value the AVX path's eta would give) to be reported beside the primary in every case. It makes the bracket the fallback, labeled "bracketed, not measured under load", only if the 27-thread AMX run could not be made.</p>
<p><strong>The Notion page's recipe, a route-2 instance.</strong> This project started from a Notion page (Notion is the team's wiki tool): "Estimate: the AMX decode boost from pre-AMX data, in plain English", section 0.2, step 4. That page prescribes a route-2 recipe: "Predicted AMX unit = the larger of the kernel cost and the memory floor, plus the common work from step 1". In this report's words: the kernel cost is the QK and PV multiplies with the page hot in L2 ({mm_amx_hot:.3f} µs on the AMX path, M3 run amx-hot-t27); the memory floor is the memory time ("Memory lower bound" in Words used here); the recipe assumes eta = 1 for the multiplies and adds the common work in full. Its step 1 is the AVX run, so the common work it adds is the AVX path's. Its step 2 sets the memory floor from a per-core rate of 15.7 to 15.9 GB/s: 32 KiB ÷ 15.9 GB/s = {NOTION_FLOOR_US:.2f} µs per unit. This report measured {rc27:.2f} GB/s per core with 27 cores reading at once (M1), so its memory time is longer: 32 KiB ÷ {rc27:.2f} GB/s = {mem:.3f} µs. The inputs side by side:</p>
<div class="tablewrap"><table><tr><th>recipe term</th><th>the Notion page's value</th><th>this report's value</th></tr>{notion_inputs}</table></div>
<p class="small">Rows 2 to 4 are the differences; rows 3 and 4 are the two errors that cancel in the paragraph below.</p>
<p>The table of routes below applies the recipe four ways (rows 6 to 9). As written, with the page's own {NOTION_FLOOR_US:.2f} µs floor, it gives {pct(_b(u_notion_page))}, {abs(_b(u_notion_page) - meas):.1f} points above the measurement (row 6). With this report's measured memory time ({mem:.3f} µs) in place of that floor it gives {pct(_b(u_notion))}, {abs(_b(u_notion) - meas):.1f} points below the measurement (row 7). That closeness comes from two errors that cancel. First, the recipe assumes perfect overlap (eta = 1) for the matrix multiplies. Second, it uses the AVX run's common work, {cw_avx_tron:.3f} µs, where the AMX path's common work under load is {cw_amx_ld:.3f} µs, {cw_amx_ld / cw_avx_tron:.1f} times larger. The Notion page reports the same doubling from Tron's own timers (common work 0.16 µs per unit on the AVX path, 0.31 µs on the AMX path) and writes that this doubling "is what neither captured": neither its per-core-rate ceiling (+28.9%) nor its kernel-benchmark estimate (+33.4%) included it (section 0.2, step 5). Removing either error moves the recipe away from the measurement. For the first error, the page's own allowance that the kernel reaches only about 90% of the streaming rate (memory time ÷ 0.9 = {mem / 0.9:.3f} µs) gives {pct(_b(u_notion_90))} (row 8). For the second error, the AMX path's common work ({cw_amx_ld:.3f} µs) in place of the AVX run's ({cw_avx_tron:.3f} µs) gives {pct(_b(u_notion_ld))} (row 9).</p>
<p><strong>Why not per phase.</strong> A finer route 2 would predict QK, PV and the common work separately. Each of the two matrix-multiply phases, QK and PV, reads 16 KiB, so its memory time is {mem16:.3f} µs. On the AVX path both phases are longer than that under load (QK {f3h(qk_avx_t)} µs, PV {f3h(pv_avx_t)} µs), and solving the formula per phase gives etas of {eta_qk_avx:.2f} and {eta_pv_avx:.2f}. On the AMX path both phases are shorter than their own 16 KiB memory time (QK {f3h(qk_amx_t)} µs, PV {f3h(pv_amx_t)} µs). Solving the formula per phase then gives etas of {eta_qk_amx:.2f} and {eta_pv_amx:.2f}. An eta above 1 has no meaning: eta is a share, 0 to 1. The likely cause, not measured separately: the bytes of one phase keep arriving while the softmax pieces and the state update run ({cw_amx_ld:.2f} µs under load; they read no bytes from the page), so a phase can finish before its own 16 KiB could have arrived on its own. M6 supports this: most of a unit's 512 lines arrive by hardware prefetch (section 10). Per-phase cache-miss counters, or the same runs with the hardware prefetcher off, would confirm or reject it. Only the whole unit stays above its 32 KiB memory time ({r8['unit_amx_primary_us']:.3f} µs against {mem:.3f} µs). A per-phase memory model therefore has no valid eta for the AMX path. The two per-phase rows below apply it anyway, with the AVX path's per-phase etas, and are shown for completeness only.</p>
<p class="small">Every row uses the chain of section 6 unchanged (worker 0's {b8['units_w0']:,.0f} units, coverage {100*cov8:.2f}%, the per-range overhead and the AMX per-token extras; joins, barrier, untimed rest and other work as measured). Rows marked "computed here" are not in the plan and not in model.json (the model script's output file). They were added on 2026-09-03 to answer the question of which route the report takes. None of them changes the primary estimate or the pre-registered band.</p>
<div class="tablewrap"><table><tr><th class="num">row</th><th>How the AMX unit is obtained (prompt 8192)</th><th class="num">eta</th><th class="num">AMX unit (µs)</th><th class="num">estimate</th><th class="num">vs measured</th><th>where</th></tr>{routes_tbl}</table></div>
<figure>{routes_svg}<figcaption>Figure 2. The estimate under each way of obtaining the AMX unit, prompt 8192. Filled blue: route 1, the unit measured under load (the primary). Hollow blue: route 2, the unit predicted from compute, memory time and an assumed eta. Orange line: the measured {pct(meas)}; the light orange band is ±3 points, the plan's "on par" limit. The two bracket edges (eta = 0 and eta = 1) sit {abs(bracket_lo - meas):.1f} points below and {abs(bracket_hi - meas):.1f} points above the measurement. The choice of eta alone moves the estimate across that {bracket_hi - bracket_lo:.1f}-point range. That is why route 2 cannot be the primary.</figcaption></figure>"""
    avx_bench_txt = f1(r8["avx_bench_us"], 2)  # the benchmark's AVX unit, named in section 3 so the two Tron columns are not read as Tron vs benchmark
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
<a href="#rounds">9. Refinement rounds</a><a href="#record">10. Measurement record</a><a href="#amxunit">11. How the AMX unit was measured</a><a href="#sources">12. Sources</a></nav>
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
<dt>Pre-AMX input</dt><dd>An input that would exist before AMX was added to Tron: Tron's own AVX-path timers, page geometry, Intel documents and non-Tron processor measurements. The "pre-AMX bracket" rows of section 8 use only such inputs. The AMX unit itself is measured with a copy of Tron's AMX kernel run outside Tron (sections 2 and 11).</dd>
<dt>Pre-registered</dt><dd>Fixed in the plan (action-plan.html) before any measurement was taken: the rules, the search order and the acceptance thresholds.</dd>
<dt>Decode, token</dt><dd>The phase where the model produces one token per step; every step re-reads all stored keys and values. Times are per generated token.</dd>
<dt>Page, KV head, unit</dt><dd>A page is 64 tokens of stored keys (16 KiB) and values (16 KiB) for one layer and one KV head (a key/value head; each serves 4 query heads). A unit is one query token's 4 query heads against one page, including the softmax pieces and the running-state update.</dd>
<dt>QK, PV, common work</dt><dd>The two matrix multiplies of a unit (queries against keys; probabilities against values) and the rest (scaling, running maximum, exponentials and sum, state update).</dd>
<dt>AMX path unit</dt><dd>One unit run on Tron's AMX code path (or on the benchmark's copy of it), as opposed to the AVX path unit, which does the same work with the dotter on the canonical keys. The steps, in order: the QK multiply of the 4 query heads against the page's 64 keys, read from the K mirror as 1 KiB tiles (16 TDPBF16PS tile multiplies); the softmax pieces (scaling, running maximum, exponentials and their sum, which turn scores into probabilities); the P pack (the probabilities converted to bf16 and laid out as a tile); the PV multiply against the page's 64 values (16 more tile multiplies); and the state update (adding the result into the per-head running state). It reads 32 KiB per unit: 16 KiB of K mirror and 16 KiB of values. Its time in this report: {f1(ub8.get('amx_hot'), 0)} ns with the page already in the core's L2 cache (instructions only) and {f1(ub8.get('amx_t27_book24'), 0)} ns under the 27-thread decode load with Tron's book layout (measured outside Tron; section 11).</dd>
<dt>Page work, joins, barrier, untimed rest</dt><dd>The three timed phases of one attention operation on one worker: its loop over units; merging results across workers; waiting for the slowest worker. The untimed rest is attention time minus the three phases: handshakes and bookkeeping no phase timer covers; it is held unchanged in the estimate.</dd>
<dt>Other work</dt><dd>Everything in a token outside attention: the weight matrix multiplies (WQ, WK, WV, WO, WFF1, WFF3, WFF2; Tron runs them on the FPGA cards on both arms), the norms, the rope, the logits, and the preparation of and waits for the FPGA jobs. It is measured in Tron's AVX-form run as token time minus attention time (M7, section 3) and carried unchanged into the estimate (section 2, rule 2), because Tron's AMX build changes only the attention units: its AMX kernels are called from the attention code alone (self_attention.hpp), and the kill switch turns off only that call. The traced run of M8 (section 10) splits the main thread's share of it into FPGA waits, job preparation and launch, and the logits stage. The unit benchmark contains none of this work (section 11).</dd>
<dt>Worker, worker 0</dt><dd>One of the 27 CPU threads that run attention units at the same time, each on its own core of socket 0 (CPUs 24 to 35, 48 to 59, 151 to 154; one of the 28 hosts the main thread). Worker 0 is the one whose timers Tron exports; all per-token numbers are its medians. Tron's planner splits pages by measured worker speed, so worker 0's share differs from run to run.</dd>
<dt>Range, per-range overhead, AMX per-token extras</dt><dd>A range is one run of consecutive pages a worker handles in one attention operation; worker 0 has 36 per token, one per layer. The per-range overhead is page work minus units × unit cost: the page loop and the probe's own reads. The AMX per-token extras are the AMX-only costs paid once per range (tile configuration, the 1 KiB query copy, the tile release), measured by the benchmark's range timer.</dd>
<dt>Book, arena</dt><dd>Tron's KV allocator places a sequence's pages adjacent in books of 24 pages (a book holds 1600 tokens by default; 24 pages are used with 128-token prompt chunks); each book is its own arena, one contiguous block of memory. Found in the KV cache and scheduler source; reproduced by the benchmark's <code>--book-pages 24</code> option.</dd>
<dt>Probe, stamps</dt><dd>The timing code compiled into the Tron binary used here (git branch jhan-amx-fence, commit 8fd1e7798d), switched on with <code>TRON_ATTN_PHASE=1</code>; it records the per-token and per-phase counters (numbered "stamps") this report reads.</dd>
<dt>Coverage</dt><dd>The share of units that can use AMX: only full 64-token pages qualify (99.24% at prompt 8192, 97.14% at 2048, 84.78% at 256; from the fallback counters of 2026-09-01).</dd>
<dt>Data wait, compute, eta, memory time</dt><dd>Compute: the unit's time with all bytes already in the core's L2 cache. Memory time: 32 KiB divided by the per-core streaming rate under load. Data wait: the unit's time minus its compute. eta: the share of the shorter of compute and memory time that is hidden behind the longer one (1 = perfect overlap, the roofline case; 0 = the two add, the serial case).</dd>
<dt>Memory lower bound</dt><dd>The memory time: a unit cannot finish before its 32 KiB has arrived, however fast its instructions run.</dd>
<dt>R<sub>core</sub>(N)</dt><dd>The bytes per second one core streams from DRAM (main memory) when N cores on the socket read at once.</dd>
<dt>L1, L2, L3, DRAM, hot</dt><dd>The core's caches and main memory. L1 (48 KiB) and L2 (2 MiB) are private to each core; L3 (432 MiB) is shared by the socket. A "hot" unit reads a page that is already in the core's L2.</dd>
<dt>Cache line, demand miss, hardware prefetch</dt><dd>A cache line is 64 bytes (32 KiB = 512 lines). A demand miss is a load the program itself issued whose line was not in the cache. Hardware prefetch is the core fetching lines ahead of the program on its own guess; prefetched lines do not count as demand misses.</dd>
<dt>1 GiB pages, THP, hugetlb, TLB, dTLB walk</dt><dd>Memory page sizes. A memory page (a different thing from Tron's KV page of 64 tokens, defined under "Page, KV head, unit" above) is the block in which the kernel maps memory to a program. The ordinary size is 4 KiB. 1 GiB pages (hugetlb): a reserved pool of huge pages, 512 such pages (512 GiB) on this machine, that a program must request explicitly. THP (transparent huge pages): the kernel backing ordinary program memory with 2 MiB pages instead of 4 KiB pages, managed by the kernel rather than by the program. delphi-3bda's setting is "madvise", so only a region the program marks with madvise(MADV_HUGEPAGE) (the system call by which a program tags a memory region) gets them. The TLB (translation lookaside buffer) is the core's cache of address translations, one entry per page, so larger pages cover more memory per entry. A dTLB walk is the slow page-table lookup after a data-side TLB miss. Where Tron's and the benchmark's memory is placed, what THP data this campaign captured and what it shows: <a href="#thp">section 10, "Page sizes and THP"</a>.</dd>
<dt>rdtsc, turbostat, perf stat</dt><dd>rdtsc: the CPU's cycle-counter instruction, used as the clock by Tron's probe and by the benchmark. turbostat: the Linux tool that reports each core's clock; its Bzy_MHz column is the clock while the core is busy (M4). perf stat: the Linux tool that reads the CPU's hardware counters (M6).</dd>
<dt>Tron's AVX unit, benchmark AVX unit</dt><dd>The same quantity, the time of one unit on the AVX path, measured in two ways on the same machine (delphi-3bda, the test machine). Two measurements exist because the plan allows Tron to run here only in its AVX form: Tron's AMX path is never executed for this project, and the model's inputs are pre-AMX inputs (entry above), with the AMX unit as the one exception, measured outside Tron. So the AMX unit comes from the benchmark. The AVX unit is measured in both places so that the benchmark can be checked against Tron (section 4). Tron's AVX unit is measured inside Tron running in its AVX form (the kill switch), by the probe's timers on worker 0, while runtron generates 256 tokens after a prompt of 8192 tokens (one user, no network client). At prompt 8192 it is {f1(b8['unit_avx_us'], 3)} µs (M7, section 3); Tron exports worker 0 only. The benchmark AVX unit is measured by unit_bench, a stand-alone program (exec/perf-model-20260903/src/unit_bench.cpp) that runs a copy of Tron's per-unit code, both paths, over a copy of Tron's page layout on Tron's 27 attention cores, with rdtsc timers at the same points as the probe; section 11 lists what was copied from Tron, what was left out, how the runs were made and what was timed. At prompt 8192 with Tron's book layout the benchmark AVX unit is {f1(r8['avx_bench_us'], 3)} µs (M3; thread 0 of the benchmark, on CPU 24; the median over all 27 threads is {f1(((D.get('m3_unit_bench', {}).get('avx-p130-t27-book24') or {}).get('all_median') or {}).get('unit_ns', 0) / 1000, 2)} µs). The difference, {f1(r8['avx_residual_us'], 2)} µs ({abs(r8['calibration_error_pct']):.1f}% of Tron's unit), is the residual (next entry). Section 4 attributes {f1(r8['avx_residual_clock_part_us'], 2)} µs of it to Tron's lower clock ({f1(r8['avx_serving_clock_ghz'], 2)} GHz against the benchmark's {f1(r8['avx_hot_clock_ghz'], 3)} GHz) and leaves {f1(r8['avx_residual_unexplained_us'], 2)} µs ({r8['avx_residual_unexplained_pct_of_tron']:.1f}% of Tron's unit) unexplained.</dd>
<dt>Residual, calibration gate</dt><dd>The residual is Tron's AVX unit minus the benchmark's AVX unit under the same load and layout (as a share of Tron's). The gate is the plan's limit on it: within 5% at prompt 8192 with QK and PV each within 10%; within 10% at prompts 2048 and 256. When it fails, the verdict is "calibration failed", the AMX numbers are not final (they are reported, but the plan does not accept them until the gate passes), and the search of section 4 runs.</dd>
<dt>s, transfer rule</dt><dd>s = Tron's AVX unit ÷ the benchmark's AVX unit; the pre-registered rule of the plan (section 7) decides how the residual is carried to the AMX unit: none, multiplicative (× s) or additive (+ residual).</dd>
<dt>Band, points</dt><dd>The pre-registered band is the range of the estimate over the alternative rules of plan section 8, rule 6 (the three transfer variants, the AMX clock ±5%, the two barrier rules). Points are percentage points: +20% minus +17% is 3 points.</dd>
<dt>Verdict: on par, close</dt><dd>The plan's acceptance rule (section 1). On par: the primary estimate within 3 points of the measured +17.3% and the whole pre-registered band within 3 points. Close: the primary within 6 points. A failed calibration gate gives "calibration failed" instead.</dd>
<dt>Record labels</dt><dd>Tron's names for the weight multiplies: WQ, WK, WV (query, key, value), WO (attention output projection), WFF1, WFF3, WFF2 (the three feed-forward multiplies). Norms are the normalization layers; rope is the rotary position embedding; logits are the per-word scores produced once per token.</dd>
<dt>M0 to M8</dt><dd>The measurement steps of the plan, in the order the campaign ran them: M0 hardware check, M7 Tron in AVX form, M1 memory streaming rate, M2 memory latency, M5 instruction costs, M3 the unit benchmark (unit_bench, a stand-alone program outside Tron, which gives both the AVX unit and the AMX unit), M4 clocks (turbostat samples of the attention cores' busy clock during the benchmark runs of M3), M6 hardware counters (perf stat counts over the benchmark's threads during the 27-thread runs of M3), M8 a traced Tron run. Section 10 names the file of each step. Tron itself ran only in its AVX form: the campaign script starts runtron twice (M7 and M8), both with the kill switch <code>TRON_AMX_DISABLE=1</code>, so no AMX run of Tron was made. Tron's measured AMX numbers of 2026-09-01 appear only in the comparison table of section 4 ("Comparison only").</dd>
<dt>est., Insufficient data</dt><dd>est.: an estimated number, not a measured one. Insufficient data: a quantity the campaign could not measure, with the measurement that would settle it named.</dd>
</dl></section>

<section id="result"><h2>1. Result</h2>
<p class="verdict">Estimate at prompt 8192: {pct(c['boost_pct'])}. Measured: {pct(meas)}. Pre-registered band: {band_full[0]:+.1f}% to {band_full[1]:+.1f}%.</p>
<p>Verdict under the plan's rules: <strong>{esc(r8['verdict'])}</strong> (plan section 7: {esc('; '.join(r8['calibration_fail_reasons']))}). The gate compares the benchmark's AVX unit with Tron's under the same load and layout. Round 2 changed the transfer rule, not that comparison. So the gate still fails and the {pct(c['boost_pct'])} estimate is not final. If the gate is waived, the acceptance rule of plan section 1 gives "{esc(r8['verdict_if_gate_waived'])}", not "on par": the primary value is {r8['error_pp']:+.1f} points from the measurement (within 3), but the pre-registered band's low edge, {band_full[0]:+.1f}%, is {abs(band_full[0] - meas):.1f} points away (outside 3). Over the alternatives the search does not rule out (barrier rules, AMX clock ±5%) the band is {band_ph[0]:+.1f}% to {band_ph[1]:+.1f}%; that band is post hoc and not part of the acceptance rule.</p>
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
<p><strong>How many units.</strong> A unit is one query token's 4 query heads against one page (64 stored tokens) of one KV head; the 64 is the size of a page, not a count of units. Per layer, a decode step at prompt 8192 has 8 KV heads × 130 pages (8,192 prompt tokens plus about 128 generated ones at the middle of the run, in pages of 64) = {8*130:,} units; over 36 layers that is {36*8*130:,} units per token, shared by the 27 workers ({36*8*130/27:,.0f} each on average). The page-work timer this report reads is worker 0's, and Tron's planner gave worker 0 {b8["units_w0"]/b8["ranges_w0"]:.0f} pages per layer in the M7 run: {b8["ranges_w0"]:.0f} × {b8["units_w0"]/b8["ranges_w0"]:.0f} = {b8["units_w0"]:,.0f} units per token (section 3). Its page work reconciles by division: {b8["units_w0"]:,.0f} units × {b8["unit_avx_us"]:.3f} µs = {b8["units_w0"]*b8["unit_avx_us"]:,.1f} µs, and the remaining {b8["range_overhead_us"]:.1f} µs of the {b8["page_work_us"]:,.1f} µs page work is the per-range overhead ({b8["range_overhead_us"]/b8["ranges_w0"]:.1f} µs for each of the {b8["ranges_w0"]:.0f} ranges); section 6 shows the same arithmetic.</p>
<p>The AMX unit is measured by a copy of Tron's AMX kernel run outside Tron on 27 cores over Tron's page layout (the unit benchmark, M3; section 11 describes it step by step). The plan required the same benchmark to first reproduce Tron's own AVX unit within 5% under the same conditions. It came within {abs(r8['calibration_error_pct']):.1f}% ({r8['avx_bench_us']:.2f} µs against Tron's {r8['avx_tron_us']:.2f} µs at prompt 8192), {abs(r8['calibration_error_pct']) - 5:.1f} points outside that gate, so under the plan's rule the AMX reading is not final. Section 4 reports the search for the cause and what it established about the AMX unit; section 9 the round that uses the AMX reading as measured. The compute, memory and wait terms decompose that measurement (section 5).</p>
{routes_html}
</section>

<section id="baseline"><h2>3. Baseline: Tron in its AVX form, measured 2026-09-03 (M7)</h2>
<p>The kill-switch binary of 2026-09-01 was run again with the phase probe at prompts 256, 2048 and 8192 (two repeats each, 253 generated tokens of 256 requested). The tables compare today's worker-0 medians with the 2026-09-01 values. Both columns are Tron's own timers, from two Tron runs; the benchmark's AVX unit ({avx_bench_txt} µs) is not in these tables, it is compared with Tron's in section 4 and listed in the M3 table of section 10 (row avx-p130-t27-book24).</p>
<div class="tablewrap"><table><tr><th>Per token, prompt 8192 (µs)</th><th class="num">Tron, M7 (2026-09-03)</th><th class="num">Tron, 2026-09-01</th><th class="num">change</th></tr>{base_tbl}</table></div>
<div class="tablewrap"><table><tr><th>Per unit, prompt 8192 (µs)</th><th class="num">Tron, M7 (2026-09-03)</th><th class="num">Tron, 2026-09-01</th><th class="num">change</th></tr>{unit_tbl}</table></div>
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
<p class="small">How the AMX unit was measured, step by step: section 11.</p>
<figure>{legend_html([("instructions running (hot compute)", f"background:{C_BLUE}"), ("waiting for bytes (data wait), dashed", f"border:2px dashed {C_AQUA};background:{C_AQUA}26")])}{units_svg}<figcaption>Figure 3. One unit at prompt 8192 on each code path, from the benchmark under load (27 threads, book layout): the solid block is the hot run (instructions running), the dashed block is the rest, waiting for bytes. Memory time at R<sub>core</sub>(27) = {f1(r8.get('r_core_27_GBs'), 2)} GB/s is {f1(r8.get('memory_time_us_at_r_core_27'), 2)} µs per 32 KiB. eta: AVX {f1(r8.get('avx_eta'), 2)}, AMX {f1(r8.get('amx_eta'), 2)}.</figcaption></figure>
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
{eff_html}
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
<p>The same chain at prompts 2048 and 256 uses their own baseline rows and coverage (97.14% and 84.78%) and the single-arena benchmark runs (the book layout was run at prompt 8192 only). Their working sets (306 MiB and 54 MiB) fit in the 432 MiB L3 of the socket, so the DRAM memory time of {f1(r8['memory_time_us_at_r_core_27'], 2)} µs does not bind there: eta is above 1 on both paths, "memory rate not binding" in the plan's words (rule 5). eta only decomposes a unit, so those estimates are unaffected.</p>
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
<p class="small"><strong>What M3 is.</strong> M3 is the unit benchmark: unit_bench, a stand-alone program that runs outside Tron (section 11 describes what it copies from Tron, how it was run and what it times). The avx rows come from its hand copy of Tron's AVX dotter path. The amx rows come from its hand copy of Tron's AMX kernel (qk_mirror_128x4 with the score copy, the softmax pieces, the P pack, weights_times_v_128x4 with the output copy and the state update). Tron's AMX path was not run in this campaign: the campaign script starts runtron only for M7 and M8, both with the kill switch <code>TRON_AMX_DISABLE=1</code>. Before timing, both copies were checked against a scalar reference that models Tron's rounding ({chk_txt}). The QK, common, PV and state columns are rdtsc timers placed where Tron's probe puts its stamps: QK, common (softmax pieces and state update) and PV on the AVX path; QK, softmax, PV and state on the AMX path. Tron's own measured AMX unit (arena-mirror build, 2026-09-01) appears only in the comparison table of section 4 ("Comparison only"), never as an input.</p>
<p class="small">How to read the configuration code, path-workingset-threads[-variant]. Path: amx = the benchmark's copy of Tron's AMX kernel, avx = its copy of Tron's AVX dotter path (neither is a Tron run). Working set: hot = every unit reads the same one page, which stays in the core's L2 with the thread's buffers (compute only); pN = N pages per layer and KV head (p130 = prompt 8192 at the median decode pass, p34 = prompt 2048, p6 = prompt 256). Threads: t1 = one worker, t27 = 27 workers on Tron's attention cores. Variant: shuf = pages placed at random; thp = 2 MiB instead of 1 GiB pages for keys and values; book24 = Tron's book layout; ctl = its same-session control (single arena); long = a longer run for the clock sample. spread = (max − min) over the repeats as a share of the median. "pages obtained" is what the kernel gave: 1g/4k = keys and values on 1 GiB pages with the mirror on 4 KiB pages.</p>
<div class="tablewrap"><table><tr><th>configuration</th><th class="num">repeats</th><th class="num">unit</th><th class="num">QK</th><th class="num">common (softmax + state)</th><th class="num">PV</th><th class="num">spread</th><th>pages obtained</th></tr>{rec_tbl}</table></div>
<h3>M4 clocks (files m4-turbostat-&lt;configuration&gt;.txt; turbostat Bzy_MHz, busy app cores, samples inside the run window)</h3>
<p class="small"><strong>What M4 is.</strong> M4 is the clock measurement of the benchmark runs. While each sampled unit-benchmark run (M3) executes, turbostat (the Linux tool that reports each core's clock) samples the 27 attention cores once per second, recording the time of day, the core, its busy share (Busy%) and its clock while busy (Bzy_MHz). The table gives, per run, the median Bzy_MHz over the cores that were busy (Busy% above 50) among the samples inside the run's timed window (from one second after the benchmark's RUN-START mark to its RUN-END mark), and the number of such samples. The rows named amx-* are turbostat samples taken while the benchmark's copy of Tron's AMX kernel was running; no AMX run of Tron was made. The AMX clocks of section 5 come from these rows: {f1(r8['amx_hot_clock_ghz'], 3)} GHz for the hot run (amx-hot-t27-long) and {f1(r8['amx_serving_clock_ghz'], 3)} GHz for the 27-thread run under load (amx-p130-t27), which the model takes as the AMX serving clock. The one clock not measured in this campaign is the AVX serving clock, {f1(r8['avx_serving_clock_ghz'], 2)} GHz: {esc(K.get('avx_serving_clock_source', ''))}. That was an AVX run of Tron (kill switch), not an AMX run.</p>
<div class="tablewrap"><table><tr><th>run</th><th class="num">MHz</th><th class="num">samples</th></tr>{clk_tbl}</table></div>
<h3>M6 hardware counters (file m6-perf.txt; the first attempt with symbolic event names is m6-perf.failed-events.txt)</h3>
<p class="small"><strong>What M6 is.</strong> M6 is the hardware-counter measurement of the benchmark runs: perf stat (the Linux tool that reads the CPU's hardware counters) counted the events below over all threads of unit_bench during its 27-thread prompt-8192 runs, one run per code path. The two columns are the benchmark's two code paths: AVX path = its copy of Tron's dotter code, the code Tron runs with the kill switch; AMX path = its copy of Tron's AMX kernel. No Tron run was involved, so no AMX run of Tron was made. The counts are divided by the number of units executed, after subtracting a fill-only control run.</p>
<p class="small">perf stat over all threads of the 27-thread prompt-8192 single-arena runs (2000 timed passes plus 20 warm-up passes), with the fill-only control run (0 passes) subtracted; divisor 37,440 units per pass × 2020 passes. Events: MEM_LOAD_RETIRED.L1/L2/L3_MISS (raw 0xd1, umask 0x08/0x10/0x20) and DTLB_LOAD_MISSES.WALK_COMPLETED (0x12, umask 0x0e); the symbolic names are not known to this perf, and the top-down metric group is not available in it (Insufficient data for the memory-bound share the plan asked for). These are demand misses only: the 512 lines of a unit are mostly filled by hardware prefetch, so the counts do not measure the bytes read. Cycles per unit include the barrier wait after each layer.</p>
<div class="tablewrap"><table><tr><th>per unit</th><th class="num">AVX path</th><th class="num">AMX path</th></tr>{m6_tbl}</table></div>
{ipc_txt}<h3>M8 traced Tron run, AVX form (files m8-cell.log, m8-trace.txt, m8-avx-1u-8192.perfetto-trace.gz, m8-spans.json; script spans.py)</h3>
<p class="small">{esc(m8_txt)}</p>
{thp_html}</section>

<section id="amxunit"><h2>11. How the AMX unit was measured: Tron's AMX kernel run outside Tron</h2>
<p><strong>Short version.</strong> Tron's AMX path did not run in this campaign, so the AMX unit was measured by unit_bench, a stand-alone program that runs a copy of Tron's AMX attention kernel and of the per-unit code around it (copied by hand from the Tron source) on Tron's 27 attention cores, over a copy of Tron's memory layout, with timers where Tron's probe has them. Both numbers below are the time of one unit: one query token's 4 query heads against one 64-token page of one KV head, that is the QK multiply on 16 KiB of K mirror, the softmax pieces, the P pack, the PV multiply on 16 KiB of values and the state update, timed by rdtsc from the first instruction of the unit to the last (thread 0, median over the timed passes and the repeats, with 27 threads running). When the page is already in the core's L2 cache, so that only the instructions are timed, one AMX unit takes {f1(ub8.get('amx_hot'), 0)} ns (the hot run). Under the 27-thread decode load with Tron's book layout, where every unit's 32 KiB must first arrive from memory, the same unit takes {f1(ub8.get('amx_t27_book24'), 0)} ns; this is the value refinement round 2 (section 9) uses, and the difference between the two is the data wait of section 5. Tron's own AMX unit, measured on 2026-09-01 outside this project, is listed next to that value in the comparison table of section 4.</p>
<h3>What one unit is on the AMX path</h3>
<p><strong>A unit is one query token's 4 query heads against one 64-token page of one KV head</strong> ("Words used here", entries "Page, KV head, unit" and "AMX path unit"). On the AMX path the unit runs, in order: the QK multiply on the K mirror (Tron's second copy of the keys, stored in the pair-interleaved order the tile multiply needs), the softmax pieces (scaling the scores, the running maximum, the exponentials and their sum, which turn scores into probabilities), the P pack (converting the probabilities to bf16 and laying them out as a tile), the PV multiply (probabilities times values) and the state update (adding the result into the per-head running state). Per unit the kernel issues 32 TDPBF16PS tile multiplies (TDPBF16PS: the AMX instruction that multiplies two bf16 tiles and adds the products into a 32-bit tile; 16 in QK, 16 in PV), 40 TILELOADD tile loads (TILELOADD: the instruction that fills one tile from memory) of 1 KiB each (4 query tiles, 16 K-mirror tiles, 4 probability tiles, 16 value tiles), 12 tile stores and 12 tile clears. It reads 16 KiB of K mirror and 16 KiB of values. Only 4 of the 16 rows of the query and probability tiles carry data, because a decode step has 4 query heads per KV head; the other 12 rows are zero, as in Tron.</p>
<h3>What was copied from Tron, and from where</h3>
<ul>
<li>Source revision: branch jhan-amx-fence, commit 8fd1e7798d, the source the M7 probe binary was built from. All line numbers below refer to it.</li>
<li>The two tile kernels: qk_mirror_128x4, the QK multiply from the K mirror (src/tron/kernels/amx_attn.cpp, lines 241 to 268), and weights_times_v_128x4, the PV multiply (lines 183 to 230), which begins with the P pack to bf16 (round to nearest even, by the instruction the code calls cvtne2ps: it converts two vectors of 32-bit floats into one vector of bf16). In the kernel names, 128 is the head size (numbers per head) and 4 the query heads per KV head. Both were copied with the same tile numbers, strides (the byte distance between consecutive tile rows) and instruction order (unit_bench.cpp, lines 160 to 222).</li>
<li>The tile configuration and release around a range (amx_attn::begin_region, which issues LDTILECFG, the instruction that sets up the tile registers; end_region, which issues TILERELEASE, the instruction that frees them) and the query pack done once per range (pack_q_rows_128x4: the 4 query rows copied into a 16-row tile buffer; Tron packs once per token and KV head within a range, which at one decode token per range is once per range).</li>
<li>The per-unit code around the kernels: the score copy (moving the 4 real rows of scores out of the 16-row tile buffer), the per-head scaling, running maximum, exponential, sum and correction, and the state update, from apply_page_tok (Tron's function that handles one page for one query token) in h/tron/models/self_attention.hpp, lines 1595 to 1826.</li>
<li>Tron's exponential (h/tron/simd/fp32.hpp: a degree-7 polynomial evaluated in Estrin form, an ordering of the multiplies and adds that computes pairs of terms at the same time), with the same constants.</li>
<li>The AVX path's copy, used for the calibration of section 4: Tron's dotter (dotter&lt;bf16,128&gt;, h/tron/kernels/dotter.hpp, lines 176 to 226: 4 VDPBF16PS into 2 accumulators and a reduction per token) and the AVX per-unit code (the per-token range and sliding-window checks, the softmax pieces, the scaled-V product and the state update).</li>
</ul>
<h3>Check that the copy computes what Tron computes</h3>
<p>unit_bench --check runs each path over 3 pages. It compares the running maximum, the sum and the normalized output against a scalar reference whose dot products and sums accumulate in double precision (scores and exponentials rounded to 32-bit floats, as Tron's are). The reference applies the same bf16 rounding to the probabilities as the path under test: truncation on the AVX path, round to nearest even on the AMX path. The gates are limits on the relative error, set where a dropped or misplaced instruction would show: 1e-4 (one part in ten thousand) on the running maximum and the sum, 1e-3 (one part in a thousand) on the normalized output. A correct copy measures about 1e-7 (one part in ten million). Result: OK on both paths before the M3 runs (campaign.log; the same check re-run after M3 is the file check.txt, and the rebuilt binary of the book-layout runs was checked again in book-sens.log). Worst relative error of the normalized output: {chk_amx} on the AMX path, {chk_avx} on the AVX path.</p>
<h3>What is not Tron</h3>
<p>The benchmark leaves out the rest of Tron and replaces the objects around the kernel with fixed values. The unit contains attention math only: the feed-forward multiplies, the norms, the rope and the logits are not part of a unit and are not in the benchmark, and no FPGA card is used by it. In Tron those parts run the same code on both arms, because the AMX build changes only the attention units, so the estimate carries them unchanged as "other work" (section 2; glossary entry "Other work"). There are no FPGA matrix multiplies, none of Tron's other threads, and no joins across workers. The page, range-mask and scratchpad objects are fixed values (the range mask is Tron's list of token ranges that says which stored tokens each query may see; the scratchpad is a thread's working memory for one token). The benchmark has no dispatch: it runs the AMX unit on every page. This stands for Tron's dense path, the code path that handles all 64 tokens of a page in one tile multiply. Tron takes it when the whole page is active, covered by one visible range, inside the sliding window (a model setting that, when set, lets a query see only the most recent tokens), and its K mirror is present (self_attention.hpp, lines 1669 to 1682). Tron takes it for {P(c['coverage'], 2)} of units at prompt 8192: the coverage, defined in "Words used here" and carried into the arithmetic of section 6 as the factor {c['coverage']:.4f}. Of Tron's per-page bookkeeping the AMX path of the benchmark reproduces only the two position lookups (the query's and the page's first token). It does not evaluate Tron's dense-path gate and does not reproduce the page object's address arithmetic. Tron's dense AMX path has no per-token range or window checks; those belong to the AVX (dotter) loop, which the benchmark's AVX path reproduces. The split of pages among the 27 threads uses equal worker speeds where Tron's planner uses measured speeds, so only per-unit times are compared with Tron, never per-thread totals. A barrier joins the 27 threads after every layer, as Tron's attention operation ends with one; its wait is timed apart from the units.</p>
<h3>Memory layout</h3>
<p>The canonical arena (the primary copy of the keys and values, in the layout Tron's AVX path reads) holds one 32 KiB block per page: a 16 KiB block of keys, then a 16 KiB block of values. The block index is (layer × 8 + KV head) × pages per head + page, where 8 is the number of KV heads per layer; Tron's KV cache uses the same index, so consecutive pages of one head are consecutive blocks. The arena is placed on 1 GiB memory pages, as Tron's KV cache is. The K mirror arena holds one 16 KiB block of mirrored keys per page, with the same index, on 4 KiB memory pages, as in Tron. For the prompt-8192 working set (130 pages per layer and head) the canonical arena is 1170 MiB and the K mirror arena 585 MiB; the AMX path reads the mirror and the value half of the canonical arena, 1170 MiB per pass (37,440 units × 32 KiB), 2.7 times the 432 MiB L3 cache of the socket. Prompt 2048 (34 pages) gives 306 MiB and 153 MiB; prompt 256 (6 pages) gives 54 MiB and 27 MiB. The book-layout runs (--book-pages 24) group pages into books of 24 adjacent pages, each book its own arena, as Tron's allocator does (section 4).</p>
<p><strong>How the arenas are filled.</strong> The benchmark runs no model and loads no dump of Tron's cache. <strong>Tron's real keys and values were not used on either the AVX path or the AMX path.</strong> <u>Before the timed passes, the worker threads fill every page with pseudo-random bf16 numbers between -0.3 and 0.3, drawn from a fixed seed per page (a splitmix generator seeded with the page's block index), so every run sees the same contents.</u> Each page's values are written in Tron's pair-interleaved order (the values of two consecutive tokens side by side). Each page's K mirror is derived from that page's keys by the same rearrangement Tron's mirror uses (scatter_k_mirror: the keys of 16 tokens and 32 dimensions become one 1 KiB tile whose 16 rows are dimension pairs and whose columns are tokens). The 4 query rows per layer and KV head are pseudo-random in the same way (seed 777). Each thread fills the pages it will read, on its own core, so the memory is placed on NUMA node 0 at first touch; the fill takes about 0.1 to 0.2 s at prompt 8192 and is not timed. A unit's time does not depend on these numbers except through the exponentials, which the small range keeps in their normal regime (no underflow to zero or to very small denormal values; overflow is already prevented by subtracting the running maximum). The correctness check of this section compares each path's output on the same synthetic data against the scalar reference, not against Tron.</p>
<h3>How the runs were made</h3>
<p>The binary is built by the campaign script run-perf-model.sh with <code>g++ -O3 -std=c++17 -march=x86-64-v4 -mavx512bf16 -mamx-tile -mamx-bf16 -pthread src/unit_bench.cpp</code>; the same script runs the correctness check and every M3 run, and run-book-sens.sh runs the book-layout and control runs. Each run is one unit_bench process bound to NUMA node 0 (NUMA, non-uniform memory access: each CPU socket has its own memory; node 0 is the memory attached to socket 0, where the attention cores are) with one thread fixed to each of Tron's attention cores (CPUs 24 to 35, 48 to 59, 151 to 153); the single-thread runs use CPU 24 only. A pass is one decode step: every thread walks its ranges (its runs of consecutive pages, one per layer) for all 36 layers, with one barrier after each layer. The plain prompt-8192 27-thread runs (the M3 rows amx-p130-t27 and avx-p130-t27) use 2000 timed passes after 20 warm-up passes ({tp_rng('amx-p130-t27')} s of timed phase on the AMX path, {tp_rng('avx-p130-t27')} s on the AVX path); the shuffled-page, 2 MiB-page, book-layout and control runs at the same size use 300 timed passes after 20. In the hot runs every unit reads the same one page, so the page and the thread's buffers (about 70 KiB) stay in the core's L2 cache; the 27-thread hot runs use 60 timed passes after 5 warm-up passes, the single-thread hot runs 150 after 3. One longer 27-thread hot run per path ({f1(long_passes, 0)} passes on the AMX path, a count chosen from the third repeat's pass time to reach 12 s) was made so that turbostat could sample the clock (M4); its timed phase came out at {tp_rng('amx-hot-t27-long')} s on the AMX path. The other single-thread runs use 20 to 200 timed passes; the 27-thread runs at prompts 2048 and 256 use 600 after 40 and 2000 after 100. Every cell (one combination of path, working set, thread count and layout variant) was run 3 times; the 2 MiB-page run and the long hot run once. The book-layout runs and their same-session controls (single-arena runs made in the same session, so the book layout is compared against the same binary at the same time) were made later on the same day by run-book-sens.sh (300 timed passes after 20 warm-up passes, 3 repeats; file book-sens.log), with the binary rebuilt from a source revised to add the --book-pages option (the source and binary checksums differ from the morning's; campaign.log and book-sens.log). Two checks tie the rebuilt binary to the morning's: the correctness check gave the same result, and the control runs reproduce the morning's single-arena runs within {ctl_max_pct} (AMX {f1(ctl_amx, 0)} against {f1(arena_amx, 0)} ns; AVX {f1(ctl_avx, 0)} against {f1(arena_avx, 0)} ns). Two other measurement steps were taken on these benchmark runs and on no other program: M4, turbostat samples of the 27 attention cores' busy clock during the hot-t1, p130-t27 and hot-t27-long runs, and M6, perf stat hardware counters over all threads of one 2000-pass 27-thread prompt-8192 run per path with a fill-only control run subtracted; section 10 gives both tables. Section 10 also lists every configuration with its median over the repeats and their spread (M3 table).</p>
<h3>What was timed</h3>
<p>Inside every unit, rdtsc timers (rdtsc: the CPU's cycle-counter instruction, "Words used here") sit where Tron's probe puts its stamps: QK (the -infinity fill of the 4 score rows, the construction of the four AVX query objects that Tron builds before the dispatch, the two position lookups, the tile QK multiply and the score copy), the softmax pieces, PV (the P pack and the tile PV multiply) and the state update (the output copy and the running-state update). A range timer around each range captures the AMX-only costs paid once per range: the tile configuration, the query pack and the tile release. They come to {f1(ub8.get('amx_range_ns_per_unit'), 1)} ns per unit. The barrier wait after each layer is timed apart from the units. Per run, the benchmark records each thread's medians over the timed passes. The report uses thread 0 (CPU 24; the M3 table and section 6 call it "worker 0", by analogy with Tron's worker 0) and takes the median over its repeats. The median over all 27 threads is recorded as well.</p>
<h3>How the numbers enter the model</h3>
<p>Three AMX numbers enter the estimate at prompt 8192.</p>
<ul>
<li>The hot 27-thread unit, {f1(ub8.get('amx_hot'), 0)} ns ({hot_split_txt}; the 60-pass runs), scaled by the hot clock ÷ the serving clock (the clock of the loaded 27-thread run, the condition the unit is served under: {f1(r8['amx_hot_clock_ghz'], 3)} ÷ {f1(r8['amx_serving_clock_ghz'], 3)} GHz, M4, a ratio of {f1(r8['amx_clock_scale'], 3)}; the hot clock was sampled during the longer hot run, whose unit is {long_vs_hot} above the 60-pass runs, section 9), gives the compute of {f1(r8['amx_compute_us'], 3)} µs (section 5).</li>
<li>The loaded 27-thread unit with the book layout, {f1(ub8.get('amx_t27_book24'), 0)} ns, is the AMX unit that refinement round 2 takes as measured (sections 4 and 9).</li>
<li>The per-range extras, {f1(ub8.get('amx_range_ns_per_unit'), 1)} ns per unit × {f1(units_w0, 0)} units (worker 0's units per token in Tron's M7 run: {f1(ranges_w0, 0)} ranges of {per_range} units) = {f1(r8.get('amx_extras_us'), 1)} µs per token, enter the arithmetic of section 6 as the AMX per-token extras.</li>
</ul>
<p>The validation rows of section 8 take, in the same way, the single-arena 27-thread units at prompts 2048 and 256 (amx-p34-t27 {f1(p34_amx, 0)} ns and amx-p6-t27 {f1(p6_amx, 0)} ns; the book layout was run at prompt 8192 only). Layout changes move the AMX unit little (each figure is the change in unit time; positive means slower): pages placed at random {pct(r8.get('amx_shuffle_pct'))}, 2 MiB memory pages instead of 1 GiB pages {pct(r8.get('amx_thp_pct'))}, the book layout against a single arena {pct(r8.get('amx_book24_pct'))} (section 4). The same benchmark's AVX path was checked against Tron's own AVX unit first (section 4: {calib_short} below Tron's value). The AMX unit itself could only be compared with Tron's AMX unit measured on 2026-09-01, outside this project; section 4's comparison table ("Comparison only") shows that comparison per phase.</p>
</section>

<section id="sources"><h2>12. Sources</h2>
<ul>
<li>Plan and pre-registered rules: <a href="action-plan.html">perf-model/action-plan.html</a>.</li>
<li>Raw results and parsed medians: <code>exec/results/perf-model-20260903/</code> (campaign.log, book-sens.log, the m0 to m8 files, medians.json, model.json, m8-spans.json, narrative.json).</li>
<li>Tools, <code>exec/perf-model-20260903/</code>; the files that contain AMX instructions are marked (AMX). Tron's own AMX path is in Tron's source (src/tron/kernels/amx_attn.cpp and h/tron/models/self_attention.hpp), not in this folder.<ul><li><code>src/unit_bench.cpp</code> (AMX): the unit benchmark of M3; both code paths of one unit, the copy of Tron's AVX dotter path and the copy of Tron's AMX kernel, plus the correctness check (section 11).</li><li><code>src/memrate.c</code> (AMX): M1, the per-core streaming-read rate with N readers; its tile mode streams with AMX TILELOADD of 1 KiB tiles instead of 64-byte vector loads.</li><li><code>src/latency.c</code>: M2, the pointer-chase memory latency on one core (no AMX).</li><li><code>src/insn_loops.cpp</code> (AMX): M5, one-core instruction cost loops: VDPBF16PS and the dotter's reduction (AVX-512), TDPBF16PS and TILELOADD (AMX).</li><li><code>run-perf-model.sh</code>: the campaign driver; builds the tools, checks the CI lease and the huge-page pool, runs M0 to M8 in order and starts the turbostat and perf stat samplers.</li><li><code>run-book-sens.sh</code>: the later session that ran the book-layout and control cells of M3.</li><li><code>parse.py</code>: turns the raw output files into medians.json and names the raw file each number came from.</li><li><code>model.py</code>: the model's arithmetic; turns medians.json into model.json (the estimate and every intermediate number).</li><li><code>spans.py</code>: the per-token span medians of the traced Tron run (M8), from the perfetto trace.</li><li><code>gen_report.py</code>: builds this page from model.json, medians.json and narrative.json.</li></ul></li>
<li>2026-09-01 measurements (comparison columns): <code>exec/results/single-attn-20260901/summary.json</code>; Notion page "Estimate: the AMX decode boost from pre-AMX data, in plain English".</li>
<li>2026-09-01 THP experiment on Tron (comparison only; section 10, "Page sizes and THP"): <code>exec/results/thp-20260901/thp.txt</code> (script exec/fence-20260831/run-thp.sh; the <code>TRON_AMX_MIRROR_THP</code> switch is commit 735ca69c30 on branch jhan-amx-fence); write-up PR3879/make-sense-amx-vs-avx.html, section 7.6. TLB sizes: tmp/notion-hugepage-page/3bda-capture.txt (CPUID leaf 0x18, 2026-08-26).</li>
<li>Constants recorded in model.json: coverage ({esc(K.get('coverage_source', ''))}); the AVX serving clock {K.get('avx_serving_clock_ghz')} GHz ({esc(K.get('avx_serving_clock_source', ''))}); the measured boosts ({esc(K.get('measured_boost_source', ''))}).</li>
</ul>
<p>{N['closing_para']}</p>
</section>
</main></div></body></html>"""
    open(a.out, "w").write(html)
    print("wrote", a.out, len(html), "bytes")


if __name__ == "__main__":
    main()
