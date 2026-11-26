#!/usr/bin/env python3
"""gdn-impl-20261121: write GDN/gdn-amx-results.html, the result page of the GDN/AMX implementation.

Every number comes from report_data.load() (result files of the campaign, of the stand-alone benchmarks and of the
unit tests, and the prediction of 2026-11-21). The prose follows the plain-english-experiment rules; check it with
  python3 exec/gdn-20261120/review-loop/plain-english-tools/check_page.py GDN/gdn-amx-results.html
Usage: python3 gen_report.py [output file]
"""
import re
import statistics as st
import sys

sys.path.insert(0, "/home/jhan/workspace/intel-AMX/exec/gdn-20261120")
import pagelib as P  # noqa: E402
import report_data  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html"
D = report_data.load()
CMP, T1, VAR, T3, T4 = D["cmp"], D["task1"], D["variants"], D["task3"], D["task4"]
CMP1, CMPC = D["cmp1"], D["cmpc"]   # session 1 (earlier commits) and the control arms; None when not collected
CELLS = D["cells"]
C = P.C


# ---------------------------------------------------------------- small helpers
def cell_name(c):
    r = CMP["cells"][c]
    return f"{r['users']} user{'s' if r['users'] > 1 else ''}, prompt {r['prompt']:,}"


def f(v, d=1):
    return "n/a" if v is None else f"{v:,.{d}f}"


def rng(vals, d=1, unit=""):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n/a"
    a, b = min(vals), max(vals)
    return f"{a:,.{d}f}{unit}" if f"{a:.{d}f}" == f"{b:.{d}f}" else f"{a:,.{d}f} to {b:,.{d}f}{unit}"


def srng(vals, d=1):
    """A range of signed changes, with explicit signs: "-0.8 to +22.6". A value that rounds to zero prints as 0."""
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n/a"
    one = lambda v: (lambda t: t.replace("-", "").replace("+", "") if float(t) == 0 else t)(f"{v:+.{d}f}")
    a, b = one(min(vals)), one(max(vals))
    return a if a == b else f"{a} to {b}"


def ref(*ns):
    return " " + "".join(f'<span class="ref">[Ref{n}]</span>' for n in ns)


def ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def table(head, rows, num_cols=(), kind=""):
    num_cols = set(num_cols)
    k = lambda i: ' class="n"' if i in num_cols else ""
    h = "".join(f"<th{k(i)}>{c}</th>" for i, c in enumerate(head))
    b = "".join("<tr>" + "".join(f"<td{k(i)}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    c = f' class="{kind}"' if kind else ""
    return f'<div class="tablewrap"><table{c}><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def arm(c, a):
    return CMP["cells"][c]["arms"].get(a)


def term(c, a, key):
    t = CMP["cells"][c]["terms"].get(a)
    return None if t is None else t.get(key)


PARTS = [("p0", "Part 0", "GDN chain kernel, no AMX"), ("a", "Part A", "AMX block kernel for GDN, built on Part 0"),
         ("b", "Parts 0 and B", "GDN chain kernel, AMX attention"), ("ab", "Parts A and B", "all three changes")]


def direct(c, a):
    return CMP["cells"][c]["direct"].get(a)


def part_stats(a):
    ds = [direct(c, a) for c in CELLS if direct(c, a)]
    return {
        "measured": [d["measured_fall_pct"] for d in ds],
        "lo": [d["predicted_fall_pct"]["lo"] for d in ds],
        "mid": [d["predicted_fall_pct"]["mid"] for d in ds],
        "hi": [d["predicted_fall_pct"]["hi"] for d in ds],
        "inside": sum(d["verdict"] == "inside the range" for d in ds),
        "below": sum(d["verdict"] == "below the range" for d in ds),
        "above": sum(d["verdict"] == "above the range" for d in ds),
        "n": len(ds),
        "tps": [d["measured_tps_change_pct"] for d in ds],
    }


PS = {a: part_stats(a) for a, _, _ in PARTS}
N_CELLS = len(CELLS)
base_n = [CMP["cells"][c]["base"]["n"] for c in CELLS]
all_tps = [arm(c, a)["tps_change_pct"] for c in CELLS for a in ("p0", "a", "b", "ab", "a0") if arm(c, a)]


def verdict_words(s):
    if s["inside"] == s["n"]:
        return f"inside the predicted range in all {s['n']} cells"
    bits = [f"inside the predicted range in {s['inside']} of {s['n']} cells"]
    if s["below"]:
        bits.append(f"below it in {s['below']}")
    if s["above"]:
        bits.append(f"above it in {s['above']}")
    return ", ".join(bits)


# ---------------------------------------------------------------- figures
def fig_pred_vs_measured():
    """Per part and cell: the predicted range (bar), the working value (tick) and the measured fall (dot)."""
    width, left, right, row_h, group_gap = 960, 250, 150, 26, 34
    xmin, xmax = 0.0, 50.0
    rows = sum(1 for a, _, _ in PARTS for c in CELLS if direct(c, a))
    groups = sum(1 for a, _, _ in PARTS if any(direct(c, a) for c in CELLS))
    h = 44 + rows * row_h + groups * group_gap + 40
    plot_w = width - left - right
    X = lambda v: left + plot_w * (min(max(v, xmin), xmax) - xmin) / (xmax - xmin)
    out = [P.svg_open(width, h, "Predicted and measured fall of the time to first token, per change and cell")]
    lx = left
    out.append(P.line(lx, 14, lx + 26, 14, stroke=C["amx"], sw=8).replace("/>", ' stroke-opacity="0.30" stroke-linecap="round"/>'))
    out.append(P.text(lx + 34, 18.5, "predicted range (est.)", size=12, fill=C["ink2"]))
    lx += 34 + 150
    out.append(P.line(lx + 4, 6, lx + 4, 22, stroke=C["amx"], sw=3))
    out.append(P.text(lx + 14, 18.5, "predicted working value (est.)", size=12, fill=C["ink2"]))
    lx += 14 + 205
    out.append(f'<circle cx="{lx + 6}" cy="14" r="6" fill="{C["gdn"]}"/>' + P.text(lx + 17, 18.5, "measured", size=12, fill=C["ink2"]))
    top = 34
    t = xmin
    while t <= xmax + 1e-9:
        x = X(t)
        out.append(P.line(x, top, x, h - 36, stroke=C["grid"]))
        out.append(P.text(x, h - 20, f"{t:g} %", size=11, fill=C["muted"], anchor="middle"))
        t += 10
    out.append(P.text(left + plot_w, h - 5, "fall of the time to first token, percent of the base run", size=11, fill=C["muted"], anchor="end"))
    y = top + 4
    for a, name, what in PARTS:
        if not any(direct(c, a) for c in CELLS):
            continue
        y += group_gap - 12
        out.append(P.text(10, y, f"{name}: {what}", size=13, weight=600))
        y += 12
        for c in CELLS:
            d = direct(c, a)
            if not d:
                continue
            p = d["predicted_fall_pct"]
            yc = y + row_h / 2
            out.append(P.text(left - 12, yc + 4, cell_name(c), size=12, anchor="end", fill=C["ink2"]))
            out.append(P.line(X(p["lo"]), yc, X(p["hi"]), yc, stroke=C["amx"], sw=9).replace("/>", ' stroke-opacity="0.30" stroke-linecap="round"/>'))
            out.append(P.line(X(p["mid"]), yc - 8, X(p["mid"]), yc + 8, stroke=C["amx"], sw=3))
            m = d["measured_fall_pct"]
            out.append(f'<circle cx="{X(m):.1f}" cy="{yc:.1f}" r="6" fill="{C["gdn"]}" stroke="{C["surface"]}" stroke-width="1.5">'
                       f'<title>{P.esc(name)}, {P.esc(cell_name(c))}: measured {m:.1f} %, predicted {p["lo"]:.1f} to {p["hi"]:.1f} %</title></circle>')
            note = f"{m:.1f} % ({d['verdict'].replace(' the range', '')})"
            out.append(P.text(left + plot_w + 12, yc + 4, note, size=11.5, weight=600,
                              fill=C["ink"] if d["verdict"].startswith("inside") else C["crit"]))
            y += row_h
    out.append("</svg>")
    return "".join(out)


def fig_ttft_seconds():
    """Time to first token per cell and arm, relative to the base run (100 %)."""
    arms = [("p0", "Part 0", C["other"]), ("a", "Part A", C["gdn"]), ("b", "Parts 0 and B", C["attn"]), ("ab", "Parts A and B", C["amx"])]
    width, left, right, row_h = 960, 200, 120, 80
    xmin, xmax = 50.0, 100.0
    h = 46 + len(CELLS) * row_h + 42
    plot_w = width - left - right
    X = lambda v: left + plot_w * (min(max(v, xmin), xmax) - xmin) / (xmax - xmin)
    out = [P.svg_open(width, h, "Time to first token of every arm, relative to the base run")]
    lx = left
    out.append(f'<circle cx="{lx + 6}" cy="14" r="6" fill="{C["ink2"]}"/>' + P.text(lx + 17, 18.5, "base run", size=12, fill=C["ink2"]))
    lx += 17 + 70
    for a, name, col in arms:
        out.append(f'<circle cx="{lx + 6}" cy="14" r="6" fill="{col}"/>' + P.text(lx + 17, 18.5, name, size=12, fill=C["ink2"]))
        lx += 17 + 7.0 * len(name) + 22
    top = 34
    t = xmin
    while t <= xmax + 1e-9:
        x = X(t)
        out.append(P.line(x, top, x, h - 38, stroke=C["ink2"] if t == 100 else C["grid"], dash="3 3" if t == 100 else None))
        out.append(P.text(x, h - 22, f"{t:g} %", size=11, fill=C["muted"], anchor="middle"))
        t += 10
    out.append(P.text(left + plot_w, h - 6, "time to first token, percent of the base run", size=11, fill=C["muted"], anchor="end"))
    y = top + row_h / 2 + 2
    for c in CELLS:
        r = CMP["cells"][c]
        out.append(P.text(left - 12, y + 4, cell_name(c), size=12.5, anchor="end", weight=600))
        out.append(P.line(X(xmin), y, X(100), y, stroke=C["line"], sw=1))
        out.append(f'<circle cx="{X(100):.1f}" cy="{y:.1f}" r="7" fill="{C["ink2"]}"/>')
        out.append(P.text(X(100) + 12, y + 4, f"{r['base']['ttft_s']:.3f} s", size=11.5, fill=C["ink2"]))
        placed = []
        for a, name, col in arms:
            v = arm(c, a)
            if not v:
                continue
            pct = 100 - v["ttft_fall_pct_of_base"]
            x = X(pct)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{col}" stroke="{C["surface"]}" stroke-width="1.5">'
                       f'<title>{P.esc(cell_name(c))}, {P.esc(name)}: {v["ttft_s"]:.3f} s</title></circle>')
            # labels alternate above and below. A label that would touch an earlier label on its side moves
            # one level further from the row line.
            above = len(placed) % 2 == 0
            near = any(side == above and abs(px - x) < 66 for px, side in placed)
            level = 13 if near else 0
            out.append(P.text(x, y - 12 - level if above else y + 21 + level, f"{v['ttft_s']:.3f} s", size=11, anchor="middle", fill=col, weight=600))
            placed.append((x, above))
        y += row_h
    out.append("</svg>")
    return "".join(out)


def fig_decode():
    arms = [("p0", "Part 0", C["other"]), ("a", "Part A", C["gdn"]), ("b", "Parts 0 and B", C["attn"]), ("ab", "Parts A and B", C["amx"])]
    width, left, right, row_h = 960, 200, 60, 40
    seen = [arm(c, a)["tps_change_pct"] for c in CELLS for a, _, _ in arms if arm(c, a)]
    step = 5.0 if max(seen, default=0.0) > 8.0 else 2.0
    xmin, xmax = -6.0 if step == 2.0 else -10.0, max(8.0, step * (int(max(seen, default=0.0) / step) + 1))
    h = 46 + len(CELLS) * row_h + 42
    plot_w = width - left - right
    X = lambda v: left + plot_w * (min(max(v, xmin), xmax) - xmin) / (xmax - xmin)
    out = [P.svg_open(width, h, "Decode speed of every arm, change against the base run")]
    lx = left
    for a, name, col in arms:
        out.append(f'<circle cx="{lx + 6}" cy="14" r="6" fill="{col}"/>' + P.text(lx + 17, 18.5, name, size=12, fill=C["ink2"]))
        lx += 17 + 7.0 * len(name) + 22
    out.append(P.line(lx + 4, 14, lx + 30, 14, stroke=C["amx"], sw=8).replace("/>", ' stroke-opacity="0.30" stroke-linecap="round"/>'))
    out.append(P.text(lx + 38, 18.5, "predicted range with Part B (est.)", size=12, fill=C["ink2"]))
    top = 34
    t = xmin
    while t <= xmax + 1e-9:
        x = X(t)
        out.append(P.line(x, top, x, h - 38, stroke=C["ink2"] if t == 0 else C["grid"], dash="3 3" if t == 0 else None))
        out.append(P.text(x, h - 22, f"{t:+g} %" if t else "0 %", size=11, fill=C["muted"], anchor="middle"))
        t += step
    out.append(P.text(left + plot_w, h - 6, "decode tokens per second per user, change against the base run", size=11, fill=C["muted"], anchor="end"))
    y = top + row_h / 2 + 2
    for c in CELLS:
        out.append(P.text(left - 12, y + 4, cell_name(c), size=12.5, anchor="end", weight=600))
        d = direct(c, "ab") or direct(c, "b")
        if d:
            p = d["predicted_tps_change_pct"]
            out.append(P.line(X(p["lo"]), y, X(p["hi"]), y, stroke=C["amx"], sw=9).replace("/>", ' stroke-opacity="0.30" stroke-linecap="round"/>'))
        for i, (a, name, col) in enumerate(arms):
            v = arm(c, a)
            if not v:
                continue
            yy = y - 9 + 6 * i
            out.append(f'<circle cx="{X(v["tps_change_pct"]):.1f}" cy="{yy:.1f}" r="5" fill="{col}" stroke="{C["surface"]}" stroke-width="1.2">'
                       f'<title>{P.esc(cell_name(c))}, {P.esc(name)}: {v["tps"]:.1f} tok/s ({srng([v["tps_change_pct"]], 1)} %)</title></circle>')
        # direct label: the change with Part B, at the right of its two dots
        with_b = [arm(c, a)["tps_change_pct"] for a in ("b", "ab") if arm(c, a)]
        if with_b:
            lo_b, hi_b = min(with_b), max(with_b)
            label = srng(with_b, 1) + " %"
            if X(hi_b) + 12 + 6.6 * len(label) < width - 6:
                out.append(P.text(X(hi_b) + 12, y + 10, label, size=11, weight=600, fill=C["ink"]))
            else:
                out.append(P.text(X(lo_b) - 12, y + 10, label, size=11, weight=600, fill=C["ink"], anchor="end"))
        y += row_h
    out.append("</svg>")
    return "".join(out)


def step_parts(c, a):
    """Parts of one GDN step in us. Their sum is the busy time per head token (the value of the large table)."""
    t = CMP["cells"][c]["terms"].get(a)
    if not t or t.get("gdn_step_us") is None:
        return None
    v = {"pre": t["gdn_step_pre_us"] or 0.0, "rec": t["gdn_step_recurrence_us"] or 0.0, "post": t["gdn_step_post_us"] or 0.0,
         "io": (t["gdn_step_start_us"] or 0.0) + (t["gdn_step_write_us"] or 0.0)}
    v["io"] += max(0.0, t["gdn_step_us"] - sum(v.values()))   # bookkeeping per work item: busy time outside the timed parts
    return v


STEP_CELL = "q35-tp4-1u-p1024" if "q35-tp4-1u-p1024" in CELLS else CELLS[0]


def fig_step():
    parts = [("rec", "recurrence", C["gdn"]), ("pre", "before: convolution, normalization", C["attn"]),
             ("post", "after: norm, output gate", C["fpga"]), ("io", "start, write and bookkeeping", C["other"])]
    rows = []
    for a, label, sub in (("base", "Base run", "token kernel"), ("p0", "Part 0", "chain kernel"), ("a", "Part A", "AMX block kernel")):
        v = step_parts(STEP_CELL, a)
        if v:
            rows.append({"label": label, "sub": sub, "values": v})
    return P.stacked(rows, parts, "us", "Time of one GDN step by part, measured by the new counters", left=150, right=70,
                     xlabel="microseconds per GDN step (one token of one key head), mean of the 16 GDN threads")


def fig_pass():
    parts = [("gdn", "GDN wall", C["gdn"]), ("rest", "pass wall minus GDN wall", C["other"])]
    rows = []
    for c in (CELLS[0], CELLS[-1]):
        for a, label in (("base", "base run"), ("p0", "Part 0"), ("a", "Part A"), ("b", "Parts 0 and B"), ("ab", "Parts A and B")):
            pw, gw = term(c, a, "prefill_pass_ms"), term(c, a, "prefill_gdn_wall_ms")
            if pw is None or gw is None:
                continue
            rows.append({"label": label, "sub": cell_name(c), "values": {"gdn": gw, "rest": pw - gw}})
    return P.stacked(rows, parts, "ms", "Wall time of one prefill pass and its GDN part", left=200, right=80, normalize=False,
                     xlabel="milliseconds per prefill pass", bar_h=30, gap=22)


def fig_kernels():
    med1 = st.median(r["design_order_ns"] for r in T1["runs"]) / 1e3
    g1, g2 = "Short runs, median of 3", "Loops of 4 s, median of 3"
    rows = [
        {"label": "Token kernel (base build)", "value": T3["token_med_us"], "color": C["other"], "note": "the reference", "group": g1},
        {"label": "Loop order of the design", "value": med1, "color": C["other"], "note": f"{rng(T1['ratio'], 2)} times faster", "group": g1},
        {"label": "Chain kernel (Part 0, built)", "value": T3["chain_med_us"], "color": C["gdn"], "note": f"{rng(T3['chain_ratio'], 2)} times faster", "group": g1},
        {"label": "AMX block kernel (Part A)", "value": T3["block_med_us"], "color": C["amx"], "note": f"{rng(T3['block_ratio'], 2)} times faster", "group": g1},
    ]
    for k, label, col in (("token", "Token kernel (base build)", C["other"]), ("chain", "Chain kernel (Part 0, built)", C["gdn"]), ("block", "AMX block kernel (Part A)", C["amx"])):
        v = T3["clock"].get(k)
        if v:
            rows.append({"label": label, "value": st.median(x[1] for x in v) / 1e3, "color": col,
                         "note": f"core clock {rng([x[0] for x in v], 2)} GHz", "group": g2})
    return P.hbars(rows, "us", "Time of the GDN recurrence per value head and token, stand-alone on delphi-3b35", left=250, right=230,
                   xlabel="microseconds per value head per prompt token")


# ---------------------------------------------------------------- tables
def partb_alone():
    """Part B alone: the fall from the Part 0 run to the run with Parts 0 and B (the kill-switch pair of task 5)."""
    return [(c, CMP["cells"][c]["rules"].get("task5_partB")) for c in CELLS if CMP["cells"][c]["rules"].get("task5_partB")]


def glance_table():
    rows = {}
    for a, name, what in PARTS:
        s = PS[a]
        if not s["n"]:
            continue
        rows[a] = [f"<b>{name}</b>", what, f"{rng(s['mid'], 0)} %", f"{min(s['lo']):.0f} to {max(s['hi']):.0f} %",
                   f"<b>{rng(s['measured'], 1)} %</b>", f"{srng(s['tps'], 1)} %", verdict_words(s).capitalize()]
    pb = partb_alone()
    if pb:
        inside = sum(x["verdict"].startswith("inside") for _, x in pb)
        out = [f"{x['verdict'].replace(' the range', '')} it with {cell_name(c)}" for c, x in pb if not x["verdict"].startswith("inside")]
        rows["pb"] = ["<b>Part B alone</b>", "the fall from the Part 0 run to the run with Parts 0 and B", f"{rng([x['working'] for _, x in pb], 0)} %",
                      f"{min(x['range'][0] for _, x in pb):.0f} to {max(x['range'][1] for _, x in pb):.0f} %",
                      f"<b>{rng([x['measured_pct_of_base'] for _, x in pb], 1)} %</b>",
                      f"{srng([x['decode_change_vs_kill_switch_pct'] for _, x in pb], 1)} %",
                      f"Inside the predicted range in {inside} of {len(pb)} cells" + ("".join(". " + o.capitalize() for o in out) if out else "")]
    order = [k for k in ("p0", "a", "pb", "b", "ab") if k in rows]
    return table(["Change", "What runs", "Predicted fall of the time to first token, working values (est.)", "Predicted range (est.)",
                  "Measured fall", "Measured change of decode speed against the base run. Row Part B alone: against the Part 0 run",
                  "Measured fall against the predicted range"], [rows[k] for k in order], num_cols=(2, 3, 4, 5))


def ttft_table():
    head = ["Users", "Prompt (tokens)", "Base run (s)"]
    for _, name, _ in PARTS:
        head += [f"{name}: measured (s)", f"{name}: fall (%)", f"{name}: predicted fall, low / working / high (%, est.)"]
    rows = []
    for c in CELLS:
        r = CMP["cells"][c]
        row = [str(r["users"]), f"{r['prompt']:,}", f"{r['base']['ttft_s']:.3f}"]
        for a, _, _ in PARTS:
            d = direct(c, a)
            if not d:
                row += ["n/a"] * 3
                continue
            p = d["predicted_fall_pct"]
            mark = "" if d["verdict"].startswith("inside") else f" ({d['verdict'].replace(' the range', '')})"
            row += [f"{d['measured_ttft_s']:.3f}", f"{d['measured_fall_pct']:.1f}{mark}", f"{p['lo']:.1f} / {p['mid']:.1f} / {p['hi']:.1f}"]
        rows.append(row)
    return table(head, rows, num_cols=range(0, len(head)))


def decode_table():
    arms = [("base", "Base run"), ("p0", "Part 0"), ("a", "Part A"), ("b", "Parts 0 and B"), ("ab", "Parts A and B")]
    head = ["Users", "Prompt (tokens)"] + [f"{n} (tok/s per user)" for _, n in arms] + ["Part B against the kill switch (%)", "Predicted range with Part B (%, est.)"]
    rows = []
    for c in CELLS:
        r = CMP["cells"][c]
        row = [str(r["users"]), f"{r['prompt']:,}"]
        for a, _ in arms:
            v = arm(c, a)
            row.append("n/a" if not v else (f"{v['tps']:.1f}" if a == "base" else f"{v['tps']:.1f} ({srng([v['tps_change_pct']], 1)} %)"))
        rule = r["rules"].get("task5_partB")
        row.append("n/a" if not rule else srng([rule["decode_change_vs_kill_switch_pct"]], 1))
        d = direct(c, "ab") or direct(c, "b")
        row.append("n/a" if not d else f"{d['predicted_tps_change_pct']['lo']:+.1f} to {d['predicted_tps_change_pct']['hi']:+.1f}")
        rows.append(row)
    return table(head, rows, num_cols=range(0, len(head)))


def terms_table():
    arms = [("base", "Base run"), ("p0", "Part 0"), ("a", "Part A"), ("b", "Parts 0 and B"), ("ab", "Parts A and B")]
    head = ["Cell", "Arm", "Prefill pass wall (ms)", "GDN wall, sum of the 24 GDN layers (ms)", "Pass wall minus GDN wall (ms)",
            "Attention busy time, mean of the 40 threads (ms)", "Join wait, inside the busy time (ms)",
            "GDN step, mean of the 16 threads (us)", "GDN step, median thread (us)", "GDN tokens on the AMX path (%)", "Attention K tokens on the AMX path (%)"]
    rows = []
    for c in CELLS:
        for a, n in arms:
            t = CMP["cells"][c]["terms"].get(a)
            if not t:
                continue
            pw, gw = t["prefill_pass_ms"], t["prefill_gdn_wall_ms"]
            amxk, avxk = t["prefill_amx_k_tokens"] or 0.0, t["prefill_avx_k_tokens"] or 0.0
            rows.append([cell_name(c), n, f(pw, 2), f(gw, 2), f(None if pw is None or gw is None else pw - gw, 2), f(t["prefill_attn_busy_ms"], 2),
                         f(t["prefill_attn_join_wait_ms"], 2), f(t["gdn_step_us"], 2), f(t["gdn_step_median_worker_us"], 2),
                         f(None if t["gdn_share_amx"] is None else 100 * t["gdn_share_amx"], 0),
                         f(100 * amxk / (amxk + avxk) if amxk + avxk else None, 0)])
    return table(head, rows, num_cols=range(2, len(head)))


def rules_table():
    """The pass rules of the plan (design section 6), with the measured value and the outcome."""
    rows = []
    t1 = T1["ratio"]
    rows.append(["1", "Stand-alone timing of the loop order of the design",
                 "2 times faster or more: the estimate is right. From 1.46 to 2 times: the low case. Below 1.46 times: wrong.",
                 f"{rng(t1, 2)} times in 3 runs with windows of 128 tokens. {rng(T1['ratio_w32'], 2)} times with windows of 32 tokens. "
                 f"With 16 copies at once: {rng(T1['copies16_ratio'], 2)} times.",
                 "At the limit between the low case and wrong"])
    fr = VAR["fused_ratio"]
    rows.append(["1", "The loop that was built in its place (see section 1)", "Same rule",
                 f"{rng(fr, 2)} times in 2 runs.", "The estimate from the counts is right"])
    s = PS["p0"]
    step = [term(c, "p0", "gdn_step_median_worker_us") for c in CELLS]
    rows.append(["2", "Part 0 in tron", "Equal bytes. The fall of the time to first token lies inside the Part 0 range. The GDN step on a 2.70 GHz thread is not above 4.6 us.",
                 f"Equal bytes in the unit tests. Fall {rng(s['measured'], 1)} %. GDN step of the median thread {rng(step, 2)} us.",
                 f"{verdict_words(s).capitalize()}. The step is below 4.6 us in {sum(1 for x in step if x is not None and x <= 4.6)} of {len(step)} cells."])
    blk = T3["clock"].get("block")
    if blk:
        b_us = st.median(x[1] for x in blk) / 1e3
        d_us = st.median(r["design_order_ns"] for r in T1["runs"]) / 1e3
        rows.append(["3", "Stand-alone AMX block kernel", "2 times faster than the loop of task 1 at the measured clock.",
                     f"{b_us:.2f} us against {d_us:.2f} us: {d_us / b_us:.1f} times, at a clock reading of {rng([x[0] for x in blk], 2)} GHz.",
                     "Pass"])
    if T4["cache_ratio"]:
        rows.append(["4", "Stand-alone attention kernel for 256-wide heads", "1.5 times faster than the AVX-512 path or more, with the data in cache.",
                     f"{rng(T4['cache_ratio'], 2)} times with the data in cache. {rng(T4['memory_decode_ratio'], 2)} times for decode from main memory.", "Pass"])
    pb = partb_alone()
    if pb:
        inside = sum(x["verdict"].startswith("inside") for _, x in pb)
        dec = sum(bool(x["decode_rule_pass"]) for _, x in pb)
        miss = [f"{x['verdict'].replace(' the range', '').capitalize()} the range with {cell_name(c)}: {x['measured_pct_of_base']:.1f} % against "
                f"{x['range'][0]:.1f} to {x['range'][1]:.1f} % (est.)." for c, x in pb if not x["verdict"].startswith("inside")]
        rows.append(["5", "Part B in tron", "The fall between the two runs of the kill-switch pair, as a percent of the base run, lies inside the Part B range. Decode is at most 1.1 % below the kill-switch run. AMX K tokens are above 0.",
                     f"Fall {rng([x['measured_pct_of_base'] for _, x in pb], 1)} % of the base run. Decode {srng([x['decode_change_vs_kill_switch_pct'] for _, x in pb], 1)} % against the kill-switch run. "
                     f"AMX K tokens per prefill pass: {rng([x['amx_k_tokens_per_prefill_pass'] for _, x in pb], 0)}.",
                     f"Range: inside in {inside} of {len(pb)} cells. " + " ".join(miss) + f" Decode rule: pass in {dec} of {len(pb)} cells."])
    r6 = [CMP["cells"][c]["rules"].get("task6_partA") for c in CELLS]
    r6 = [x for x in r6 if x]
    if r6:
        inside = sum(x["verdict"].startswith("inside") for x in r6)
        lower = sum(bool(x["ttft_lower_with_part_a"]) for x in r6)
        rows.append(["6", "Part A in tron", "The run with Part A has a lower time to first token than the run with the GDN switch set, in all 6 cells. "
                     "The fall from the base run to Part 0 and the fall of the GDN-switch pair, added, lie inside the Part A range.",
                     f"Fall of the GDN-switch pair {rng([x['ab_fall_pct_of_run1'] for x in r6], 1)} % of its run with the switch set. "
                     f"Sum of the two falls {rng([x['measured_pct_of_base'] for x in r6], 1)} % of the base run.",
                     f"Lower in {lower} of {len(r6)} cells. Range: inside in {inside} of {len(r6)} cells."])
    return table(["Task", "What", "Pass rule of the plan", "Measured", "Outcome"], rows, kind="prose")


def step_table():
    v0, va, vb = step_parts(STEP_CELL, "p0"), step_parts(STEP_CELL, "a"), step_parts(STEP_CELL, "base")
    if not (v0 and va and vb):
        return ""
    tot = lambda v: sum(v.values())
    mt = lambda a: term(STEP_CELL, a, "gdn_step_median_worker_us")
    rows = [
        ["Recurrence, 2 value heads", f"{vb['rec']:.2f} (the whole step loop)", "1.9 to 2.3, plus 0.1 to 0.2 for cache lines from L2", f"{v0['rec']:.2f}",
         "0.8 to 1.1 at 2.40 GHz, 1.0 to 1.4 at 1.90 GHz", f"{va['rec']:.2f}"],
        ["Work before and after the recurrence", "inside the row above", "0.7 to 1.0, copies included", f"{v0['pre'] + v0['post']:.2f}",
         "0.8 at 2.70 GHz, 0.9 at 2.40 GHz, 1.1 at 1.90 GHz", f"{va['pre'] + va['post']:.2f}"],
        ["Start and write of the state, with bookkeeping", f"{vb['io']:.2f}", "inside the row above. Norm, output gate and copies together: 0 to 0.3, not measured",
         f"{v0['io']:.2f}", "inside the row above", f"{va['io']:.2f}"],
        ["<b>GDN step, mean of the 16 threads</b>", f"<b>{tot(vb):.2f}</b>", "no value: the design gives one thread", f"<b>{tot(v0):.2f}</b>", "no value", f"<b>{tot(va):.2f}</b>"],
        ["<b>GDN step, median thread</b>", f"<b>{mt('base'):.2f}</b>", "2.7 to 3.5 on a 2.70 GHz thread", f"<b>{mt('p0'):.2f}</b>",
         "1.7 to 2.0 at 2.40 GHz, 2.2 to 2.5 at 1.90 GHz", f"<b>{mt('a'):.2f}</b>"],
        ["Factor against the base run (mean of the 16 threads)", "1", "1.4 / 2.1 / 2.4 (low / working / high)", f"<b>{tot(vb) / tot(v0):.2f}</b>",
         "2.0 / 3.2 / 3.7 (low / working / high)", f"<b>{tot(vb) / tot(va):.2f}</b>"],
    ]
    return table(["Part of the GDN step (us)", "Base run, measured", "Part 0, design (est.)", "Part 0, measured", "Part A, design (est.)", "Part A, measured"],
                 rows, num_cols=(1, 3, 5))


def kernel_table():
    rows = [
        ["Token kernel (base build)", rng(T3["token_us"], 2), "1"] + _clock_cells("token"),
        ["Loop order of the design (two passes, [chunk][row] halves)", rng(T1["design_order_us"], 2), rng(T1["ratio"], 2), "not measured", "not measured"],
        ["Chain kernel as built (joined loops, row-contiguous halves)", rng(T3["chain_us"], 2), rng(T3["chain_ratio"], 2)] + _clock_cells("chain"),
        ["AMX block kernel", rng(T3["block_us"], 2), rng(T3["block_ratio"], 2)] + _clock_cells("block"),
    ]
    return table(["Kernel", "Short runs: us per value head per token (3 runs)", "Times faster than the token kernel, inside each run",
                  "Loop of 4 s: us per value head per token", "Core clock reading in that loop (GHz)"], rows, num_cols=(1, 2, 3, 4))


def _clock_cells(k):
    v = T3["clock"].get(k)
    if not v:
        return ["not measured", "not measured"]
    return [rng([x[1] / 1e3 for x in v], 2), rng([x[0] for x in v], 2)]


def burst_table():
    gaps = sorted({b["gap_us"] for b in T3["burst"]})
    rows = []
    for g in gaps:
        get = lambda k: next((b for b in T3["burst"] if b["gap_us"] == g and b["kernel"] == k), None)
        t, c, b = get("token"), get("chain"), get("block")
        if not (t and c and b):
            continue
        rows.append([f"{g:,}" if g else "0 (no gap)", f"{t['kernel_us']:.0f}", f"{c['kernel_us']:.0f}", f"{b['kernel_us']:.0f}", f"{b['ns'] / 1e3:.2f}",
                     "n/a" if not g else f"{b['clock_first_quarter']:.2f}", "n/a" if not g else f"{b['clock_rest']:.2f}"])
    return table(["Scalar work between two bursts (us)", "Token kernel (us per burst)", "Chain kernel (us per burst)", "AMX block kernel (us per burst)",
                  "AMX block kernel (us per value head and token)",
                  "Core clock in the first quarter of the scalar work after an AMX burst (GHz)", "Core clock in the rest of that work (GHz)"],
                 rows, num_cols=range(0, 7))


def decay_table():
    keys = sorted({(d["decay_lo"], d["decay_hi"]) for d in T3["decay"]}, reverse=True)
    rows = []
    for lo, hi in keys:
        get = lambda build, k: next((d["ns"] for d in T3["decay"] if d["decay_lo"] == lo and d["decay_hi"] == hi and d["kernel"] == k and d["build"].endswith(build)), None)
        rows.append([f"{lo:g} to {hi:g}", f(get("noflush", "block"), 0), f(get("bench", "block"), 0), f(get("bench", "chain"), 0), f(get("bench", "token"), 0)])
    return table(["Decay per token", "AMX block kernel without the two bits (ns)", "AMX block kernel as built (ns)", "Chain kernel (ns)", "Token kernel (ns)"],
                 rows, num_cols=range(1, 5))


def task4_table():
    names = {"prefill16": "prefill, 16 query tokens per page", "prefill128": "prefill, 128 query tokens per page",
             "prefill1024": "prefill, 1,024 query tokens per page", "decode": "decode, 1 query token per page"}
    rows = [[("Pages in cache" if r["regime"] == "cache" else "Pages from main memory"), names.get(r["use"], r["use"]), rng(r["avx_us"], 2), rng(r["amx_us"], 2),
             rng(r["ratio"], 2), rng(r["avx_clock"], 2), rng(r["amx_clock"], 2)] for r in T4["rows"]]
    return table(["Data", "Use", "AVX-512 path (us per page unit)", "AMX kernels (us per page unit)", "Times faster", "Core clock, AVX-512 (GHz)", "Core clock, AMX (GHz)"],
                 rows, num_cols=range(2, 7))


def unit_table():
    names = {"ctr": "Counters only (base build)", "pa": "Plus GDN chain and block kernels", "pab": "Plus attention kernels",
             "noamx": "Head, Debug build without AMX dispatch"}
    sw = {"none": "none", "kill-switch": "kill switch", "gdn-switch": "GDN switch"}
    rows = [[names.get(u["build"], u["build"]), f"<code>{u['commit']}</code>", f"<code>{u['test']}</code>", sw.get(u["switch"], u["switch"]), f"{u['assertions']:,}",
             str(u["cases"]), u["result"], str(u["skips"])] for u in D["unit"]]
    return table(["Build", "Commit", "Test program", "Switch", "Assertions", "Test cases", "Result", "Lines that report a case without AMX"], rows, num_cols=(4, 5, 7))


def direct1(c, a):
    return ((CMP1 or {}).get("cells", {}).get(c) or {}).get("direct", {}).get(a)


def sessions_table():
    head = ["Users", "Prompt (tokens)"]
    for _, name, _ in PARTS:
        head += [f"{name}: session 1 (%)", f"{name}: session 2 (%)"]
    rows = []
    for c in CELLS:
        r = CMP["cells"][c]
        row = [str(r["users"]), f"{r['prompt']:,}"]
        for a, _, _ in PARTS:
            d1, d2 = direct1(c, a), direct(c, a)
            row += ["n/a" if not d1 else f"{d1['measured_fall_pct']:.1f}", "n/a" if not d2 else f"{d2['measured_fall_pct']:.1f}"]
        rows.append(row)
    return table(head, rows, num_cols=range(0, len(head)))


def controls_table():
    rows = []
    for c, r in (CMPC or {"cells": {}})["cells"].items():
        o, n, b = r["arms"].get("orig"), r["arms"].get("nost"), r["arms"].get("base")
        if not (o and n and b):
            continue
        pc = lambda x, y: srng([100 * (x - y) / y], 1)
        rows.append([f"{r['users']} user{'s' if r['users'] > 1 else ''}, prompt {r['prompt']:,}", f"{o['ttft_s']:.3f}", f"{n['ttft_s']:.3f}", f"{b['ttft_s']:.3f}",
                     pc(b["ttft_s"], n["ttft_s"]), f"{o['tps']:.1f}", f"{n['tps']:.1f}", f"{b['tps']:.1f}", pc(b["tps"], n["tps"])])
    return table(["Cell", "TTFT, build of 2026-11-20 (s)", "TTFT, GDN counters off (s)", "TTFT, GDN counters on (s)", "TTFT, on against off (%)",
                  "Decode, build of 2026-11-20 (tok/s)", "Decode, GDN counters off (tok/s)", "Decode, GDN counters on (tok/s)", "Decode, on against off (%)"],
                 rows, num_cols=range(1, 9))


def numerics_table():
    rows = [[n["case"], n["chain_bits"].lower(), f"{n['differ_pct']:.3f}", str(n["max_incr"]), str(n["max_incr_large"]), f"{n['state_rel_l2']:.1e}",
             f"{n['block_err'] / n['token_err']:.2f}", f"{n['state_err_ratio']:.2f}"] for n in T3["numerics"]]
    return table(["Input family (128 tokens, stand-alone)", "Chain kernel against the token kernel", "bf16 output words of the block kernel that differ (%)",
                  "Largest difference of any output (bf16 steps)", "Largest difference of a large output (bf16 steps)",
                  "State difference of the block kernel (relative)",
                  "Output error against float64: block kernel / token kernel", "State error against float64: block kernel / token kernel"],
                 rows, num_cols=range(2, 8))


TOKEN_ARMS = {"orig": "Build of 2026-11-20 (no counters)", "base": "Base run", "base2": "Base run, second run", "p0": "Part 0 (kill switch)",
              "a0": "Part 0 (GDN switch, build without Part B)", "a": "Part A", "a2": "Part A, second run", "b": "Parts 0 and B",
              "b2": "Parts 0 and B, second run", "bonly": "Part B alone (commit before the GDN changes)", "ab": "Parts A and B",
              "ab2": "Parts A and B, second run"}
EXACT_ARMS = ("orig", "base2", "p0", "a0")


def tokens_table():
    rows = [[f"{t['prompt']:,}", TOKEN_ARMS.get(t["arm"], t["arm"]), "the base run", "yes" if t["arm"] in EXACT_ARMS else "no", f"{t['equal']} of {t['of']}",
             "none" if t["first_difference"] is None else f"generated token {t['first_difference']}"] for t in D["tokens"]["rows"]]
    for t in D["tokens"]["pairs"]:
        if t["kind"] == "a_ab":
            rows.append([f"{t['prompt']:,}", TOKEN_ARMS["ab"], "the run with Part A", "no", f"{t['equal']} of {t['of']}",
                         "none" if t["first_difference"] is None else f"generated token {t['first_difference']}"])
        if t["kind"] == "partb":
            rows.append([f"{t['prompt']:,}", TOKEN_ARMS["bonly"], "the run with Parts 0 and B", "no", f"{t['equal']} of {t['of']}",
                         "none" if t["first_difference"] is None else f"generated token {t['first_difference']}"])
    return table(["Prompt (tokens)", "Run", "Compared with", "Must be equal", "Equal tokens", "First difference"], rows, num_cols=(0, 4))


def load_table():
    """Load before the runs: our 56 CPUs and the other socket, for every block of runs and every stand-alone benchmark."""
    rows = []
    for name, col in (("Session 2 (the main data)", D["col"]), ("Session 1", D["col1"]), ("Control runs", D["colc"])):
        if not col:
            continue
        ours = [r["load"].get("our-app-cores") for r in col["runs"].values() if r.get("load")]
        s0 = [r["load"].get("socket0") for r in col["runs"].values() if r.get("load")]
        rows.append([name, f"{len(col['runs'])} runs", rng(ours, 1), rng(s0, 1)])
    fix_runs = [v for k, v in D["side"].items() if ("__q-a__" in k or "__f-a__" in k) and v.get("load_ours") is not None]
    if fix_runs:
        rows.append(["Runs around the fix of section 7", f"{len(fix_runs)} runs", rng([v["load_ours"] for v in fix_runs], 1), rng([v["load_socket0"] for v in fix_runs], 1)])
    for b in D["bench_loads"]:
        rows.append([b["name"], "1 snapshot before the benchmark", f"{b['our-app-cores']:.1f}", f"{b['socket0']:.1f}"])
    return table(["Runs", "Snapshots", "Our 56 CPUs busy before a run (%)", "Other socket busy before a run (%)"], rows, num_cols=(2, 3))


# ---------------------------------------------------------------- text blocks
s_ab, s_0, s_a, s_b = PS["ab"], PS["p0"], PS["a"], PS["b"]
tps_span = max(abs(min(all_tps)), abs(max(all_tps))) if all_tps else 0.0
REPS = min(base_n) if base_n else 0
big_cells = [c for c in CELLS if CMP["cells"][c]["users"] == 8 and CMP["cells"][c]["prompt"] >= 4096]
tps_big = [arm(c, a)["tps_change_pct"] for c in big_cells for a in ("b", "ab") if arm(c, a)]
tps_rest = [arm(c, a)["tps_change_pct"] for c in CELLS if c not in big_cells for a in ("b", "ab") if arm(c, a)]
short_items = [
    "Three changes that speed up the model Qwen3.5 4B are built in tron and measured on delphi-3b35.",
    (f"With all three changes the time to first token fell by {rng(s_ab['measured'], 0)} %, against working predictions of {min(s_ab['mid']):.0f} to {max(s_ab['mid']):.0f} % (est.)."
     if s_ab["n"] else "The runs with all three changes are not finished."),
    (f"With 8 users and prompts of 4,096 tokens or more, token generation after the prompt got {rng(tps_big, 0)} % faster."
     if tps_big else "The decode comparison is not finished."),
]
intro_items = [
    "Part 0 is a faster loop for the GatedDeltaNet (GDN) layers of the model Qwen3.5 4B. It uses no AMX.",
    "Part A is a kernel for the same layers that uses AMX, a set of Intel matrix instructions.",
    "Part B is an AMX kernel for the attention layers of the model.",
    "Part A is built on Part 0, and a build with Part A always has Part 0. So the run named Parts A and B has all three changes.",
    "tron also got counters for its GDN layers. Section 8 describes them.",
]

WORDS = [
    ("tron, runtron", "tron is the inference program under test. runtron is its command-line tool."),
    ("Qwen3.5 4B", "the model under study. Its tron name is ingested-qwen-3.5-4b."),
    ("GDN (GatedDeltaNet)", "a recurrent layer type. 24 of the 32 layers of Qwen3.5 4B are GDN layers. The other 8 are attention layers."),
    ("state", "the memory of a GDN layer. It is one matrix of 128 key rows by 128 value columns per value head, in FP32."),
    ("decay", "a factor between 0 and 1 that multiplies the state of a value head for each token."),
    ("key head, value head", "a GDN layer has 16 key heads and 32 value heads. Each key head serves 2 value heads."),
    ("recurrence", "the arithmetic that reads and rewrites the state for one token."),
    ("GDN step", "the work of one token for one key head. Its parts are the convolution, the normalization, the recurrence on 2 value heads, the norm and the output gate."),
    ("GDN operation, work item", "tron runs one GDN operation per GDN layer and pass. A work item is one chain of one key head inside it."),
    ("GDN threads, median thread", "16 CPU threads run the GDN work. 2 of them run on faster CPUs (4.00 GHz, from the design page). "
     "The median thread is a thread at 2.70 GHz."),
    ("chain", "the consecutive tokens of one sequence in one pass. A GDN layer must take them in order."),
    ("token kernel, chain kernel, block kernel", "three routines for the recurrence." + ul([
        "The token kernel is the code of the base build. It takes one token per call.",
        "The chain kernel is Part 0. It gives the same bits with another loop order.",
        "The block kernel is Part A. It takes 32 tokens at once with AMX."])),
    ("step(), advance()", "two entries of tron's GDN code. step() takes one token. advance() is new and takes a run of tokens."),
    ("window, block", "advance() cuts a chain into windows of at most 32 tokens. A full window of 32 tokens is a block."),
    ("working copy", "a copy of the state that tron makes for a chain of 2 or more tokens. The stored state stays as it was until the chain ends."),
    ("AMX", "Intel Advanced Matrix Extensions: tile registers, and instructions that multiply two tiles."),
    ("tile, tile product", "a tile is an AMX register of 16 rows by 64 bytes. A tile product is one TDPBF16PS instruction, which multiplies two tiles of bf16 values."),
    ("AVX-512", "512-bit vector instructions. The code without AMX uses them."),
    ("bf16, FP32, float64", "number formats with 8, 24 and 53 significant bits."),
    ("bf16 step", "the distance between two neighbouring bf16 values. It is 0.125 for values from 16 to 32. Earlier pages call it one notch."),
    ("scores", "the values that the model gives to every token id for the next token. The sampler of these runs takes the token id with the best score."),
    ("correction", "the value that the recurrence adds to the state for one token."),
    ("error band", "a stated limit on how far a result may differ from a reference result. tron's AMX tests check such limits."),
    ("numerics contract", "a written rule about results. It says which results must be equal bit for bit and how far the others may differ."),
    ("subnormal value", "a nonzero value below the smallest normal value of its format (2^-126 for FP32). A CPU computes with such values slowly."),
    ("FTZ, DAZ", "two control bits of the CPU. With FTZ a result that would be subnormal becomes zero. With DAZ a subnormal operand is read as zero."),
    ("core clock", "the frequency at which a CPU core runs. The CPU lowers it under AVX-512 or AMX work."),
    ("prefill, pass", "prefill is the processing of the prompt. A pass is one forward computation through all 32 layers. A prefill pass has 128 prompt tokens per user."),
    ("decode step", "a pass with one token per user."),
    ("listener", "a token has a listener when its scores are read. Every generated token has one."),
    ("trace", "a recording of timed events that runtron can write. It slows the run."),
    ("thread split", "how tron divides its CPU threads between the kinds of work. A runtron option keeps it fixed."),
    ("registry entry", "the record of a model in tron's list of models."),
    ("TTFT", "time to first token: from the request to the first generated token."),
    ("decode, tok/s", "decode is the generation of tokens after the prompt. Its speed is given in tokens per second per user."),
    ("wall", "wall-clock time: the elapsed time of a piece of work, waits included."),
    ("GDN wall", "per GDN layer and pass: the time from the first thread's start to the last thread's end. The tables give the sum over the 24 GDN layers of a pass."),
    ("busy time", "the time a thread spends inside its GDN or attention work, without the waits before it. "
     "The attention busy time of a pass is the mean over the 40 attention threads, summed over the 8 attention layers."),
    ("join wait", "the time an attention thread waits, inside its work, for the other threads or for data. It is part of the attention busy time."),
    ("attention job", "the attention work of one layer in one pass on one thread. The counters keep its wall time for one thread only, attention thread 0."),
    ("attention wall", "the wall time of the attention job on attention thread 0, with every wait inside the job. Section 5 gives the sum over the 8 attention layers."),
    ("other work", "the wall of a decode step minus its GDN wall and its attention wall. It holds the matrix multiplies on the FPGA cards, the data transfers and the remaining CPU work."),
    ("start of a chain", "the work that prepares the state of one key head before a chain. The counters time it."),
    ("NaN", "not a number: a float value that marks an invalid result."),
    ("query head, KV head", "an attention layer of this model has 16 query heads and 4 KV heads. Each KV head stores the keys and values for 4 query heads."),
    ("K token, page unit", "a K token is one stored key row that a query is scored against. A page unit is the attention work of one query token on one 64-token page of one KV head."),
    ("counters", "the new GDN statistics of tron. The environment variable TRON_GDN_STATS=1 turns them on."),
    ("head token", "the unit of the counters: one token of one key head of one GDN layer."),
    ("kill switch", "the environment variable TRON_AMX_DISABLE=1. It turns every AMX kernel off."),
    ("GDN switch", "the new environment variable TRON_AMX_GDN_DISABLE=1. It turns only the AMX block kernel of GDN off."),
    ("arm", "one build with one set of switches. The campaign has 6 arms. Section 2 lists them."),
    ("kill-switch pair, GDN-switch pair", "two pairs of runs that differ in one switch only." + ul([
        "The kill-switch pair is the build with all changes, with the kill switch set and with the GDN switch set. Its two runs differ in Part B.",
        "The GDN-switch pair is the build without Part B, with the GDN switch set and with no switch. Its two runs differ in Part A."])),
    ("cell", "one combination of user count and prompt length."),
    ("base build, base run", "the base build is tron with the new counters and with none of the three changes. A base run is a run of the base build in the same session."),
    ("Part 0, Part A, Part B", "the three changes of the design." + ul([
        "Part 0 is the GDN chain kernel, without AMX.",
        "Part A is the AMX block kernel for GDN. It is built on Part 0, so a run with Part A also has Part 0.",
        "Part B is the AMX attention kernel for 256-wide heads. It does not depend on the other two."])),
    ("working value, range", "the design gave each prediction a low, a working and a high value. The range runs from the low to the high value."),
    ("delphi-3b35, our half", "the test server. We use its second CPU socket and 4 of its 8 FPGA cards. Other users have the first socket and the other cards."),
    ("FPGA cards, engine, tp4", "tron runs its large matrix multiplies on FPGA cards. An engine is one copy of the model on a group of cards. tp4 is an engine on 4 cards."),
    ("us", "the microsecond, one millionth of a second."),
    ("est.", "an estimate. Every number without it is measured."),
    ("Insufficient data", "a value that we could not measure. The text names the measurement that would give it."),
]
words_html = "<details><summary>Words used here</summary><ul>" + "".join(f"<li>{k}: {v}</li>" for k, v in WORDS) + "</ul></details>"

sha = lambda t: f"<code>{(D['builds'].get(t) or 'n/a')[:10]}</code>"

s1_built = ul([
    f"The work is 3 commits on the branch jhan-gdn-amx, on top of commit 72e1191804 of the open pull request that adds the model{ref(1)}.",
    f"Commit {sha('ctr')} adds the GDN counters. It changes no kernel.",
    f"Commit {sha('pa')} adds Part 0 and Part A. They are the chain kernel, the executor entry advance() and the AMX block kernel.",
    f"Commit {sha('pab')} adds Part B: the AMX attention kernels for heads of 256 values.",
    f"The branch is pushed. It is the draft PR #5572 of the tron repository, on top of PR #3696{ref(1)}.",
])
code_rows = [
    ["Counters", "<code>h/tron/models/gdn_stats.hpp</code>, hooks in <code>gdn_execution.hpp</code> and <code>model.hpp</code>",
     ul(["TRON_GDN_STATS=1 turns them on.", "They count head tokens per path and time the parts of the GDN work.", "Section 8 describes them."])],
    ["Chain kernel (Part 0)", "<code>h/tron/kernels/gated_delta_net.hpp</code>",
     ul(["gdn_recurrence_chain advances a chain window by window.", "The state is held as two row-contiguous halves of 64 value columns.",
         "The write loop of a token also computes the read sum of the next token."])],
    ["Executor", "<code>h/tron/models/gdn_rolling_executor.hpp</code>, <code>gdn_execution.hpp</code>",
     ul(["advance() takes a run of tokens: prepare a window, run the recurrence, postprocess the window.",
         "Chains of 1 token keep step(), so decode runs the token kernel of the base build. step() gained one branch for working copies.",
         "The working copy of a chain now has the layout of the chain kernel."])],
    ["AMX block kernel (Part A)", "<code>src/tron/kernels/amx_gdn.cpp</code>, <code>h/tron/kernels/amx_gdn_iface.hpp</code>",
     ul(["It takes one block of 32 tokens of one key head.", "The FP32 state is split into 3 bf16 pieces per value.",
         "It refuses a block with a correction or an output that is not finite. It also refuses a correction of 2^100 or larger.",
         "A refused value head then takes the chain kernel."])],
    ["Attention kernels (Part B)", "<code>src/tron/kernels/amx_attn.cpp</code>, <code>amx_attn_iface.hpp</code>, <code>self_attention.hpp</code>",
     ul(["A second kernel shape: heads of 256 values with 4 query heads per KV head.",
         "The code of the three existing 128-wide kernels is unchanged. One comment line inside one of them was reworded."])],
    ["Switches", "environment variables, read once at start",
     ul(["TRON_AMX_DISABLE=1 turns every AMX kernel off (it existed).", "TRON_AMX_GDN_DISABLE=1 turns only the GDN block kernel off (new).", "TRON_GDN_STATS=1 turns the GDN counters on (new)."])],
]
fr_ = VAR["fused_ratio"]
blocked = VAR.get("two_pass_blocked_runs") or []
diff_items = [
    "The chain kernel has another loop than the design describes." + ul([
        f"In a stand-alone test the loop order of the design was {rng(T1['ratio'], 2)} times faster than the loop of the base build{ref(4)}.",
        f"Another loop joins the write pass of a token with the read pass of the next token. It was {rng(fr_, 2)} times faster, with equal bits{ref(5)}.",
    ]),
    "The halves of the state are stored row by row. "
    + (f"The layout of the design gave {blocked[0]:,.0f} ns per value head and token in one run and {blocked[1]:,.0f} ns in the next run{ref(5)}." if len(blocked) >= 2 else ""),
    "The chain kernel also works in windows of at most 32 tokens. The design ran each half of the state over the whole chain.",
    "The windows follow the token position in the sequence, as the design asked for the blocks. "
    "So the same tokens fall into the same blocks, except where a cut of the scheduler divides a window.",
    "The block kernel has a second refusal rule: a correction of 2^100 or larger. The design refused only results that are not finite.",
    "The block kernel sets the CPU bits FTZ and DAZ for its own work. Section 7 gives the measurement behind this.",
    "The design asked to clear the 512-bit registers before tile work. "
    + (f"Per value head and token the block kernel took {rng([x[1] for x in T3['zeroupper'].get('with', [])], 0)} ns with the clearing and {rng([x[1] for x in T3['zeroupper'].get('without', [])], 0)} ns without it. "
       f"So the kernel does not clear the registers{ref(7)}." if T3["zeroupper"].get("with") else f"A measurement showed no effect, so the kernel does not do it{ref(7)}."),
    "Part 0 and Part A are one commit. The design listed them as two tasks.",
    "The counters are kept per GDN operation, not per model layer. tron's GDN code does not know the layer number.",
]

arms_rows = [
    ["base", "Base run", "counters only", "none", "token kernel", "AVX-512"],
    ["p0", "Part 0", "all three changes", "TRON_AMX_DISABLE=1 (kill switch)", "chain kernel (Part 0)", "AVX-512"],
    ["b", "Parts 0 and B", "all three changes", "TRON_AMX_GDN_DISABLE=1 (GDN switch)", "chain kernel (Part 0)", "AMX (Part B)"],
    ["ab", "Parts A and B", "all three changes", "none", "AMX block kernel (Part A)", "AMX (Part B)"],
    ["a0", "Part 0, GDN switch", "counters, Part 0, Part A", "TRON_AMX_GDN_DISABLE=1 (GDN switch)", "chain kernel (Part 0)", "AVX-512"],
    ["a", "Part A", "counters, Part 0, Part A", "none", "AMX block kernel (Part A)", "AVX-512"],
    ["orig", "Build of 2026-11-20 (control)", "no change, no GDN counters", "none", "token kernel", "AVX-512"],
    ["nost", "GDN counters off (control)", "counters only", "TRON_GDN_STATS not set", "token kernel", "AVX-512"],
]
builds = D["builds"]
head_tips = {(builds.get(t) or "")[:10] for t in ("ctr", "pa", "pab")}
n_runs = sum(arm(c, a)["n"] for c in CELLS for a in ("base", "p0", "b", "ab", "a0", "a") if arm(c, a))
n_runs1 = sum(v["n"] for r in (CMP1 or {"cells": {}})["cells"].values() for v in r["arms"].values())
tips2 = sorted({t for c in CELLS for a in ("base", "p0", "b", "ab", "a0", "a") if arm(c, a) for t in arm(c, a).get("tips", [])})
tips1 = sorted({t for r in (CMP1 or {"cells": {}})["cells"].values() for v in r["arms"].values() for t in v.get("tips", [])})
head_is_measured = head_tips == set(tips2)
t0_, t1_ = D["session2_times"]


def _pst(ts):
    """UTC time stamp -> 'HH:MM' and the local (PST, UTC-8) date and time."""
    import datetime
    u = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    loc = u - datetime.timedelta(hours=8)
    return u, loc


if t0_ and t1_:
    (u0, l0), (u1, l1) = _pst(t0_), _pst(t1_)
    when2 = f"on {u0:%Y-%m-%d} from {u0:%H:%M} to {u1:%H:%M} UTC ({l0:%Y-%m-%d}, {l0:%H:%M} to {l1:%H:%M} PST)"
else:
    when2 = "n/a"
spread_ttft = max(v["ttft_spread_pct"] for c in CELLS for v in CMP["cells"][c]["arms"].values())
spread_tps = max(v["tps_spread_pct"] for c in CELLS for v in CMP["cells"][c]["arms"].values())
s2_items = [
    f"Every run uses runtron on our half of delphi-3b35, with one engine on four FPGA cards (tp4){ref(2)}.",
    "A cell is 1 or 8 users with a prompt of 1,024, 4,096 or 8,192 tokens. Every run then generates 256 tokens per user.",
    f"The campaign ran {n_runs} runs: 6 cells, 6 arms and {REPS} repetitions. The arm order changes with each repetition.",
    f"These runs are session 2. They ran {when2}, on the commits after the code review{ref(13)}.",
    f"Session 1 ran earlier, on the commits before the code review. It was stopped after {n_runs1} runs, and session 2 took its place.",
    "Every value on this page comes from session 2, unless the text names session 1.",
] + ([] if head_is_measured else [
    f"After session 2, only comments, tests, commit messages and two README files changed{ref(16)}. The 3 commits of the branch include these changes. The code that runs is the same.",
]) + [
    "Every value is the median of the repetitions of one cell and arm.",
    f"The 3 repetitions of one cell and arm differ by up to {spread_ttft:.1f} % in the time to first token. In decode speed they differ by up to {spread_tps:.1f} %.",
    "With 8 users, the time to first token of a run is that of the slowest user. The decode speed of a run is the mean of the 8 users.",
    "The base run is part of the same session. The values of 2026-11-20 are not used as a denominator.",
    "A load snapshot was taken before every run. A run does not start when our CPUs are more than 5 % busy.",
    "The 6 arms of the campaign have both sets of counters on (TRON_ATTN_STATS=1 and TRON_GDN_STATS=1).",
    "The two control arms have the attention counters only. One runs with TRON_GDN_STATS not set. The other is the build of 2026-11-20, which has no GDN counters.",
]
s2_kernels = [
    "A token of a GDN layer takes exactly one of the three recurrence kernels. So one token gets the gain of Part 0 or the gain of Part A, never both.",
    "A chain of 1 token takes the token kernel. Every decode token is such a chain.",
    "With Part A on, a full window of 32 prompt tokens takes the block kernel.",
    "A shorter window takes the chain kernel of Part 0. A block that the block kernel refuses takes it too.",
    "So a run with Part A always includes Part 0. The arm named Parts A and B is the run with all three changes.",
    "In the 6 cells every chain of a prefill pass is a whole number of blocks. The block kernel refused 0 blocks there (section 9). "
    "So with Part A on, 100 % of the prompt tokens took the block kernel.",
]
col_runs = D["col"]["runs"].values()
ours_all = [r["load"].get("our-app-cores") for r in col_runs if r.get("load")]
s0_all = [r["load"].get("socket0") for r in col_runs if r.get("load")]
s2_load = [
    f"In {len(ours_all)} of {len(ours_all)} runs of session 2 our 56 CPUs were {rng(ours_all, 1)} % busy before the run{ref(2)}.",
    f"The other socket was {rng(s0_all, 1)} % busy. Other users run their jobs there.",
    "The table gives the same two values for session 1, for the control runs and for 5 stand-alone benchmarks.",
    "Insufficient data for the load before three stand-alone tests: the loop variants, the register-clearing test and the decay test. They have no snapshot of their own.",
    "The nearest snapshot was taken 4 minutes before the loop variants and 2 minutes before the decay test. Our CPUs were 0.0 to 0.1 % busy in both.",
    "No snapshot was taken in the 30 minutes before the register-clearing test. Builds of ours ran on the same socket in that time.",
]

r5 = [CMP["cells"][c]["rules"].get("task5_partB") for c in CELLS]
r5 = [x for x in r5 if x]
r6 = [CMP["cells"][c]["rules"].get("task6_partA") for c in CELLS]
r6 = [x for x in r6 if x]

def s3_bullet(name, st_, arm_id):
    """One bullet of section 3: measured fall, working values, range, and where the result lies."""
    below_mid = sum(d["measured_fall_pct"] < d["predicted_fall_pct"]["mid"] for d in (direct(c, arm_id) for c in CELLS) if d)
    reps = [(c, v) for c in CELLS if direct(c, arm_id) for v in arm(c, arm_id)["ttft_fall_pct_per_rep"]]
    out_reps = sum(not (direct(c, arm_id)["predicted_fall_pct"]["lo"] <= v <= direct(c, arm_id)["predicted_fall_pct"]["hi"]) for c, v in reps)
    where = (f"below the working value in {below_mid} of {st_['n']} cells and " if below_mid else "") + verdict_words(st_)
    text = (f"{name} the time to first token fell by {rng(st_['measured'], 1)} %. "
            f"The working values were {rng(st_['mid'], 0)} % (est.), and the range was {min(st_['lo']):.0f} to {max(st_['hi']):.0f} % (est.). "
            f"The result is {where}.")
    extra = []
    if out_reps:
        edge = min(((direct(c, arm_id)["measured_fall_pct"] - direct(c, arm_id)["predicted_fall_pct"]["lo"], c) for c in CELLS if direct(c, arm_id)))
        d = direct(edge[1], arm_id)
        extra = [f"With {cell_name(edge[1])} the fall is {d['measured_fall_pct']:.1f} %, and the low end of the range is {d['predicted_fall_pct']['lo']:.1f} % (est.).",
                 f"{out_reps} of the {len(reps)} single repetitions of this arm is outside its range."]
    return text + (ul(extra) if extra else "")


pb_ = partb_alone()
s3_items = [
    s3_bullet("With Part 0 alone", s_0, "p0"),
    s3_bullet("With Part A", s_a, "a"),
    s3_bullet("With Parts 0 and B", s_b, "b"),
    s3_bullet("With Parts A and B", s_ab, "ab"),
]
if pb_:
    miss = [(c, x) for c, x in pb_ if not x["verdict"].startswith("inside")]
    s3_items.append(
        f"Part B alone is the fall from the Part 0 run to the run with Parts 0 and B. It is {rng([x['measured_pct_of_base'] for _, x in pb_], 1)} % of the base run. "
        f"The working values were {rng([x['working'] for _, x in pb_], 0)} % (est.)."
        + ul([f"With {cell_name(c)} it is {x['verdict'].replace(' the range', '')} the range: {x['measured_pct_of_base']:.1f} % against {x['range'][0]:.1f} to {x['range'][1]:.1f} % (est.)."
              for c, x in miss] + ["This is the only comparison of a time to first token that is not inside its range." if len(miss) == 1 else
                                   f"{len(miss)} comparisons of Part B alone are not inside their range."]) if miss else "")
s3_items += [
    f"The prediction for Parts 0 and B is not printed on the design page. It comes from the same prediction file{ref(3)}.",
    "The GDN changes help most at short prompts, and the attention change helps most at long prompts. The prediction said the same.",
]

sess_diff = [abs(direct1(c, a)["measured_fall_pct"] - direct(c, a)["measured_fall_pct"]) for c in CELLS for a, _, _ in PARTS if direct1(c, a) and direct(c, a)]
inside1 = sum(direct1(c, a)["verdict"].startswith("inside") for c in CELLS for a, _, _ in PARTS if direct1(c, a))
n1 = sum(1 for c in CELLS for a, _, _ in PARTS if direct1(c, a))
s3_sessions = [] if not sess_diff else [
    "Session 1 measured the same arms with the commits before the code review. Most of its cells have one repetition.",
    f"Its falls differ from session 2 by at most {max(sess_diff):.1f} percentage points.",
    f"In session 1 the fall is inside the predicted range in {inside1} of {n1} comparisons.",
]

# ---------------------------------------------------------------- section 4: decode
dec_b = [x["decode_change_vs_kill_switch_pct"] for x in r5]
dec_counts = {}
for arm_id in ("b", "ab"):
    dd = [direct(c, arm_id) for c in CELLS if direct(c, arm_id)]
    dec_counts[arm_id] = (sum(d["measured_tps_change_pct"] > d["predicted_tps_change_pct"]["hi"] for d in dd),
                          sum(d["measured_tps_change_pct"] < d["predicted_tps_change_pct"]["lo"] for d in dd), len(dd))
dec_dir = [direct(c, "b") for c in CELLS if direct(c, "b")]
clear_cells = [c for c in CELLS if all(direct(c, a) and direct(c, a)["measured_tps_change_pct"] - direct(c, a)["predicted_tps_change_pct"]["hi"] > spread_tps for a in ("b", "ab"))]
tj = lambda c, a, k: term(c, a, k) or 0.0
dec_fac = {u: [tj(c, "p0", "decode_attn_busy_ms") / tj(c, "b", "decode_attn_busy_ms") for c in CELLS
               if CMP["cells"][c]["users"] == u and tj(c, "b", "decode_attn_busy_ms")] for u in (1, 8)}
dec_fac_nojoin = {u: [(tj(c, "p0", "decode_attn_busy_ms") - tj(c, "p0", "decode_attn_join_wait_ms")) / (tj(c, "b", "decode_attn_busy_ms") - tj(c, "b", "decode_attn_join_wait_ms"))
                      for c in CELLS if CMP["cells"][c]["users"] == u and tj(c, "b", "decode_attn_busy_ms")] for u in (1, 8)}
big = max(CELLS, key=lambda c: (CMP["cells"][c]["users"], CMP["cells"][c]["prompt"]))
c8_ = [c for c in CELLS if CMP["cells"][c]["users"] == 8]
low = min(dec_dir, key=lambda d: d["measured_tps_change_pct"] - d["predicted_tps_change_pct"]["lo"]) if dec_dir else None
s4_items = [
    f"Part 0 and Part A do not touch decode. Their decode speed is within {max(abs(v) for v in s_0['tps'] + s_a['tps']):.1f} % of the base run.",
    (f"With Part B, decode changed by {srng(dec_b, 1)} % against the same build with the kill switch set."
     if dec_b else "The decode comparison of Part B is not finished."),
    ("The prediction for Part B was no change at the working value. Its range grows with the users and the prompt. "
     f"The widest range is {min(d['predicted_tps_change_pct']['lo'] for d in dec_dir):+.1f} to {max(d['predicted_tps_change_pct']['hi'] for d in dec_dir):+.1f} % (est.)."
     if dec_dir else ""),
    (f"Against the base run, the arm with Parts 0 and B is above its range in {dec_counts['b'][0]} of {dec_counts['b'][2]} cells. It is below its range in {dec_counts['b'][1]}. "
     f"The arm with Parts A and B is above in {dec_counts['ab'][0]} and below in {dec_counts['ab'][1]}." if dec_dir else ""),
    (f"Both arms run the same decode code. Repetitions of one arm differ by up to {spread_tps:.1f} %. "
     f"{len(clear_cells)} cells are above the range by more than that."
     + ul([f"{cell_name(c)}: {srng([direct(c, a)['measured_tps_change_pct'] for a in ('b', 'ab')], 1)} %" for c in clear_cells]) if clear_cells else ""),
] + [
    (f"With {cell_name(c)} the two arms are above the range by {rng([direct(c, a)['measured_tps_change_pct'] - direct(c, a)['predicted_tps_change_pct']['hi'] for a in ('b', 'ab')], 1)} percentage points. "
     + (f"All {sum(len(arm(c, a)['tps_change_pct_per_rep']) for a in ('b', 'ab'))} single repetitions are above it."
        if all(v > direct(c, a)["predicted_tps_change_pct"]["hi"] for a in ("b", "ab") for v in arm(c, a)["tps_change_pct_per_rep"]) else "This is inside the spread."))
    for c in CELLS if c not in clear_cells and all(direct(c, a) for a in ("b", "ab"))
    and any(direct(c, a)["measured_tps_change_pct"] > direct(c, a)["predicted_tps_change_pct"]["hi"] for a in ("b", "ab"))
] + [
    (f"The plan asked that decode with Part B is at most 1.1 % below the kill-switch run. That is true in {sum(bool(x['decode_rule_pass']) for x in r5)} of {len(r5)} cells. "
     f"The smallest margin to that limit is {min(x['decode_change_vs_kill_switch_pct'] for x in r5) + 1.1:.1f} percentage points."
     if r5 else ""),
]
s4_items = [x for x in s4_items if x] + ["Section 5 explains why decode gains little in the 4 cells with 1 user or with prompt 1,024."]
s4_why = [] if not (dec_fac[1] and dec_fac[8]) else [
    "The prediction assumed that the attention busy time of a decode step gets 0.9 to 1.17 times shorter (est.).",
    "The design took 1.18 and 1.22 times from measurements of the 128-wide kernels on delphi-3bda, another server. It multiplied them by an assumed clock ratio of 0.76 to 0.96 (est.).",
    f"The kill-switch pair gives the measured value. With 8 users the busy time got {rng(dec_fac[8], 2)} times shorter.",
    "With 1 user the change depends on the prompt."
    + ul([(f"prompt {CMP['cells'][c]['prompt']:,}: {tj(c, 'p0', 'decode_attn_busy_ms') / tj(c, 'b', 'decode_attn_busy_ms'):.2f} times shorter"
           if tj(c, 'p0', 'decode_attn_busy_ms') >= tj(c, 'b', 'decode_attn_busy_ms') else
           f"prompt {CMP['cells'][c]['prompt']:,}: {100 * (tj(c, 'b', 'decode_attn_busy_ms') / tj(c, 'p0', 'decode_attn_busy_ms') - 1):.0f} % longer, "
           f"from {tj(c, 'p0', 'decode_attn_busy_ms'):.3f} to {tj(c, 'b', 'decode_attn_busy_ms'):.3f} ms")
          for c in CELLS if CMP["cells"][c]["users"] == 1]),
    (f"Take {CMP['cells'][big]['users']} users and prompt {CMP['cells'][big]['prompt']:,}. "
     f"There the attention busy time of a decode step fell from {tj(big, 'p0', 'decode_attn_busy_ms'):.2f} to {tj(big, 'b', 'decode_attn_busy_ms'):.2f} ms. "
     f"The decode step fell from {tj(big, 'p0', 'decode_step_ms'):.2f} to {tj(big, 'b', 'decode_step_ms'):.2f} ms."),
    (f"The busy time includes the join wait. In that cell the join wait fell from {tj(big, 'p0', 'decode_attn_join_wait_ms'):.2f} to {tj(big, 'b', 'decode_attn_join_wait_ms'):.2f} ms. "
     f"That is {100 * (tj(big, 'p0', 'decode_attn_join_wait_ms') - tj(big, 'b', 'decode_attn_join_wait_ms')) / (tj(big, 'p0', 'decode_attn_busy_ms') - tj(big, 'b', 'decode_attn_busy_ms')):.0f} % of the fall of the busy time."),
    f"Without the join wait the busy time got {rng(dec_fac_nojoin[8], 2)} times shorter with 8 users. "
    f"The stand-alone test gave {rng(T4['memory_decode_ratio'], 2)} times for decode with pages from main memory{ref(9)}.",
    "So with 8 users the kernel work got shorter in all 3 cells. The join wait of a decode step got shorter only at the two longer prompts."
    + ul([f"prompt {CMP['cells'][c]['prompt']:,}: from {tj(c, 'p0', 'decode_attn_join_wait_ms'):.2f} to {tj(c, 'b', 'decode_attn_join_wait_ms'):.2f} ms" for c in c8_]),
    "The design divided the kernel work and the join wait by one factor.",
    "Insufficient data for why the join wait fell. A timer inside the join of a decode step would show what the threads wait for.",
    "The decode step is the wall of one forward pass. The time between two passes is not part of it.",
]

# ---------------------------------------------------------------- section 5 (why decode gains little) and the user comparison of section 3
import decode_why  # noqa: E402
DW = decode_why.build(globals(), fig_users=3, fig_flow=5, fig_lanes=6, fig_step=7, ref_code=21)

# ---------------------------------------------------------------- section 6: against the prediction
v0, va, vb = step_parts(STEP_CELL, "p0"), step_parts(STEP_CELL, "a"), step_parts(STEP_CELL, "base")
tot = lambda v: sum(v.values())
mt = lambda a: term(STEP_CELL, a, "gdn_step_median_worker_us")
pass_fall = lambda c, a, ref_="base": tj(c, ref_, "prefill_pass_ms") - tj(c, a, "prefill_pass_ms")
gdn_fall = lambda c, a, ref_="base": tj(c, ref_, "prefill_gdn_wall_ms") - tj(c, a, "prefill_gdn_wall_ms")
okc = lambda a: [c for c in CELLS if term(c, a, "prefill_pass_ms") and term(c, a, "prefill_gdn_wall_ms") and term(c, "base", "prefill_gdn_wall_ms")]
serial = [100 * pass_fall(c, "p0") / gdn_fall(c, "p0") for c in okc("p0") if gdn_fall(c, "p0")]
serial_a = [100 * pass_fall(c, "a") / gdn_fall(c, "a") for c in okc("a") if gdn_fall(c, "a")]
wall_fac = {a: [tj(c, "base", "prefill_gdn_wall_ms") / tj(c, a, "prefill_gdn_wall_ms") for c in okc(a)] for a in ("p0", "a")}
step_fac = {a: [tj(c, "base", "gdn_step_us") / tj(c, a, "gdn_step_us") for c in okc(a) if tj(c, a, "gdn_step_us")] for a in ("p0", "a")}
rest_ = lambda c, a: tj(c, a, "prefill_pass_ms") - tj(c, a, "prefill_gdn_wall_ms")
rest_change = {a: [100 * (rest_(c, a) - rest_(c, "base")) / rest_(c, "base") for c in okc(a)] for a in ("p0", "a")}
rest_ms_change = {a: [rest_(c, a) - rest_(c, "base") for c in okc(a)] for a in ("p0", "a")}
PREDC = D["pred"]["cells"]
ASSUME = D["pred"]["assumptions"]
TAX_MID = ASSUME["tax_rest_amx_gdn"]["mid"]


def pred_busy_factor(c, level):
    """Predicted factor of the whole attention busy time of a prefill pass under Part B (the formula of predict.py)."""
    pf = PREDC[c]["prefill"]
    new = pf["attn_ms"] - pf["attn_full_ms"] * (1 - 1 / ASSUME["s_attn_prefill"][level]) + pf["attn_other_ms"] * ASSUME["tax_attn_other"][level]
    return pf["attn_ms"] / new
amx_gdn_share = [100 * term(c, "a", "gdn_share_amx") for c in CELLS if term(c, "a", "gdn_share_amx") is not None]
fallbacks = [term(c, a, "gdn_amx_fallback_blocks") for c in CELLS for a in ("a", "ab") if term(c, a, "gdn_amx_fallback_blocks") is not None]

s5_gdn = []
if v0 and va and vb:
    s5_gdn = [
        f"The values of this part are means over the 16 GDN threads, in the cell with {cell_name(STEP_CELL)}. The design values are for one thread at 2.70 GHz.",
        f"The base run takes {tot(vb):.2f} us per GDN step. Part 0 takes {tot(v0):.2f} us, and Part A takes {tot(va):.2f} us.",
        f"So the measured factor is {tot(vb) / tot(v0):.2f} for Part 0 and {tot(vb) / tot(va):.2f} for Part A. The design assumed 2.1 and 3.2 at the working values (est.).",
        f"On the median thread the GDN step is {mt('base'):.2f} us (base run), {mt('p0'):.2f} us (Part 0) and {mt('a'):.2f} us (Part A). "
        "The design estimated 2.7 to 3.5 us for Part 0 and 1.7 to 2.5 us for Part A (est.).",
        f"The recurrence itself is close to the estimates. The chain kernel takes {v0['rec']:.2f} us for 2 value heads, and the block kernel takes {va['rec']:.2f} us.",
        f"The work around the recurrence is larger than estimated. With the start and the write of the state it takes {v0['pre'] + v0['post'] + v0['io']:.2f} us per step, against 0.7 to 1.0 us (est.).",
        "This work is the convolution, the normalization, the norm, the output gate and the copies of the state. No change of the design makes it faster.",
        f"With the block kernel the work before and after the recurrence is {100 * (va['pre'] + va['post']) / tot(va):.0f} % of the GDN step. "
        f"Everything except the recurrence is {100 * (tot(va) - va['rec']) / tot(va):.0f} %.",
    ]
s5_wall = []
if serial:
    s5_wall = [
        f"The GDN wall fell by a factor of {rng(wall_fac['p0'], 2)} with Part 0 and {rng(wall_fac['a'], 2)} with Part A. "
        f"The GDN step fell by {rng(step_fac['p0'], 2)} and {rng(step_fac['a'], 2)}.",
        f"With Part 0 the pass wall fell by {rng(serial, 0)} % of the fall of the GDN wall. With Part A it fell by {rng(serial_a, 0)} %.",
        "So a time saved in GDN shortens the pass by about the same time, as the design assumed.",
        "The design assumed a clock cost of Part A outside GDN and outside the attention busy time. The working value was 2.6 % of that part (est.).",
        f"That is {rng([PREDC[c]['prefill']['rest_ms'] * TAX_MID for c in CELLS if CMP['cells'][c]['users'] == 1], 1)} ms per pass with 1 user "
        f"and {rng([PREDC[c]['prefill']['rest_ms'] * TAX_MID for c in CELLS if CMP['cells'][c]['users'] == 8], 1)} ms with 8 users (est.).",
        f"The pass wall without the GDN wall changed by {srng(rest_ms_change['a'], 1)} ms with Part A and by {srng(rest_ms_change['p0'], 1)} ms with Part 0.",
        "Part 0 uses no AMX and shows the same small change. So these runs show no clock cost of Part A outside GDN.",
    ]
busy_ratio = [tj(c, "p0", "prefill_attn_busy_ms") / tj(c, "b", "prefill_attn_busy_ms") for c in CELLS if tj(c, "b", "prefill_attn_busy_ms")]
nj = lambda c, a: tj(c, a, "prefill_attn_busy_ms") - tj(c, a, "prefill_attn_join_wait_ms")
busy_ratio_nojoin = [nj(c, "p0") / nj(c, "b") for c in CELLS if tj(c, "b", "prefill_attn_busy_ms")]
shown = [100 * (tj(c, "p0", "prefill_pass_ms") - tj(c, "b", "prefill_pass_ms")) / (tj(c, "p0", "prefill_attn_busy_ms") - tj(c, "b", "prefill_attn_busy_ms"))
         for c in CELLS if tj(c, "b", "prefill_attn_busy_ms")]
shown_a = [100 * (tj(c, "a", "prefill_pass_ms") - tj(c, "ab", "prefill_pass_ms")) / (tj(c, "a", "prefill_attn_busy_ms") - tj(c, "ab", "prefill_attn_busy_ms"))
           for c in CELLS if tj(c, "ab", "prefill_attn_busy_ms")]
gdn_ab_vs_a = [100 * (tj(c, "ab", "prefill_gdn_wall_ms") - tj(c, "a", "prefill_gdn_wall_ms")) / tj(c, "a", "prefill_gdn_wall_ms") for c in CELLS if tj(c, "ab", "prefill_gdn_wall_ms")]
gdn_p0_vs_a0 = [100 * (tj(c, "p0", "prefill_gdn_wall_ms") - tj(c, "a0", "prefill_gdn_wall_ms")) / tj(c, "a0", "prefill_gdn_wall_ms") for c in CELLS if tj(c, "a0", "prefill_gdn_wall_ms")]
c8 = [c for c in CELLS if CMP["cells"][c]["users"] == 8]
join8 = {a: [tj(c, a, "prefill_attn_join_wait_ms") for c in c8] for a in ("p0", "b")}
s5_attn = []
if busy_ratio:
    s5_attn = [
        f"The kill-switch pair gives the effect of Part B in one build. The attention busy time of a prefill pass got {rng(busy_ratio, 2)} times shorter.",
        f"The pass wall fell by {rng(shown, 0)} % of the fall of the busy time.",
        f"The busy time includes the join wait. With 8 users the join wait rose from {rng(join8['p0'], 1)} ms to {rng(join8['b'], 1)} ms under Part B. The design kept it fixed.",
        f"Without the join wait the busy time got {rng(busy_ratio_nojoin, 2)} times shorter.",
        f"The stand-alone test of the kernel gave {rng(T4['cache_ratio'], 2)} times per page unit with the data in cache{ref(9)}.",
        "The prediction assumed 2.3 times for the scoring of full pages only (est.). It also assumed a slower clock for the other attention work.",
        f"For the whole busy time the working values give {rng([pred_busy_factor(c, 'mid') for c in CELLS], 2)} times (est.). "
        f"The measured value is above the working value in {sum(m_ > pred_busy_factor(c, 'mid') for c, m_ in zip(CELLS, busy_ratio))} of {len(busy_ratio)} cells."
        + ul([f"{cell_name(c)}: {m_:.2f} against a working value of {pred_busy_factor(c, 'mid'):.2f} and a low value of {pred_busy_factor(c, 'lo'):.2f} (est.)"
              for c, m_ in zip(CELLS, busy_ratio) if m_ < pred_busy_factor(c, "mid")]),
        "Hypothesis: the longer join wait is why Part B alone is below its range with 8 users and prompt 1,024. A time stamp per thread at the end of its scoring would show which threads end late.",
        f"The arms Part A and Parts A and B are two builds. Between them the pass wall fell by {rng(shown_a, 0)} % of the fall of the busy time.",
        f"There the GDN wall changed by {srng(gdn_ab_vs_a, 1)} % in the run with Part B. The chain kernel shows {srng(gdn_p0_vs_a0, 1)} % between the same two builds.",
        "Insufficient data for the cause of this change of the GDN wall. A build with Part B that keeps attention on AVX-512 while the block kernel runs would separate the two effects.",
    ]

t3d = T3["decay"]
slow = max((d["ns"] for d in t3d if d["build"].endswith("noflush") and d["kernel"] == "block"), default=None)
fast_same = next((d["ns"] for d in t3d if d["build"].endswith("bench") and d["kernel"] == "block" and slow and
                  any(e["ns"] == slow and e["decay_lo"] == d["decay_lo"] for e in t3d)), None)
SIDE = D["side"]
qa = [SIDE[k] for k in ("q35-tp4-1u-p1024__q-a__rep1", "q35-tp4-1u-p1024__q-a__rep2") if k in SIDE]
fa = [SIDE[k] for k in ("q35-tp4-1u-p1024__f-a__rep1", "q35-tp4-1u-p1024__f-a__rep2") if k in SIDE]
flat = lambda k: max(d["ns"] for d in t3d if d["kernel"] == k and d["build"].endswith("bench")) / min(d["ns"] for d in t3d if d["kernel"] == k and d["build"].endswith("bench"))
s6_items = [
    "The first runs of Part A in tron were slower than expected.",
    (f"Before the fix the time to first token with Part A was {rng([x['ttft'] for x in qa], 3)} s{ref(18)}. This is from 2 runs with 1 user and prompt 1,024."
     if qa else ""),
    (f"{qa[0]['ops_over_1_5']} of the {qa[0]['ops']} GDN layers had a GDN wall above 1.5 times the median layer. The largest was {rng([x['max_over_median'] for x in qa], 1)} times."
     if qa else ""),
    "The cause was subnormal numbers. A value head that forgets fast has small decay values. The block kernel multiplies the decays of up to 32 tokens.",
    "That product then drops below the smallest normal FP32 value. The CPU computes with such values through a slow path.",
    (f"In a stand-alone test with decays from 0.01 to 0.1 the block kernel took {slow:,.0f} ns per value head and token. With the bits FTZ and DAZ set it took {fast_same:,.0f} ns{ref(8)}."
     if slow and fast_same else "The stand-alone test of this case is in the result files."),
    "The kernel now sets both bits for its own work and restores the caller's setting on return. A unit test checks the restore.",
    (f"After the fix the time to first token was {rng([x['ttft'] for x in fa], 3)} s. The largest GDN wall of a layer was {rng([x['max_over_median'] for x in fa], 2)} times the median layer."
     if fa else ""),
    "A unit test covers decays whose products underflow. The kernel with the two bits stays inside its error band there.",
    f"In the stand-alone test the times of the token kernel and of the chain kernel change by less than {100 * (max(flat('token'), flat('chain')) - 1):.1f} % over the decay ranges.",
]
s6_items = [x for x in s6_items if x]

ut = D["unit"]
num = T3["numerics"]
st_ratio = [n["state_err_ratio"] for n in num]
sc_m = re.search(r"largest difference ([\d.]+) \(largest value ([\d.]+)\), (\d+) of (\d+) bf16 words differ", T4.get("selfcheck") or "")
s8_items = [
    "Part 0 changes no bit. New unit tests compare advance() with step() byte by byte, for outputs and for the stored state.",
    "They cover these cases." + ul(["at 128 value columns: chains of 1, 2, 3, 31, 32, 33, 127 and 128 tokens from 4 start positions",
                                    "at 16 and 80 value columns: chains of 2, 33 and 70 tokens from 2 start positions"]),
    "The existing tests of the prefill path now run the chain kernel too. They still require equal bytes.",
    "Part A changes few bits, as the design said. New tests bound the difference against the chain kernel and against a float64 computation.",
    f"In the stand-alone check {rng([n['differ_pct'] for n in num], 3)} % of the bf16 output words differ{ref(6)}. "
    f"An output above 1 % of the typical size differs by at most {max(n['max_incr_large'] for n in num)} bf16 step. A smaller output differs by up to {max(n['max_incr'] for n in num)} steps.",
    f"Against float64 the output error of the block kernel is {rng([n['block_err'] / n['token_err'] for n in num], 2)} times the error of the token kernel.",
    f"The state error of the block kernel is {rng(st_ratio, 2)} times that of the token kernel. It is larger in {sum(v > 1 for v in st_ratio)} of {len(st_ratio)} input families.",
    "A block is refused when a correction or an output is not finite. It is also refused when a correction is 2^100 or larger. Its state stays untouched.",
    "Tests cover these cases." + ul(["an infinity and a NaN in the start state", "a value of 3e38", "a value of 2^99, which the kernel must take",
                                     "an output that overflows"]),
    "advance() then gives the refused value head to the chain kernel. A test checks that the state of this head gets the bytes of step().",
    (f"In the campaign the block kernel refused {int(max(fallbacks))} blocks." if fallbacks else ""),
    "Part B has the error band of the existing 128-wide kernels. The existing band tests now run for both shapes.",
    (f"Part B changes many low bits. In the self-check of the stand-alone test, {int(sc_m.group(3)):,} of {int(sc_m.group(4)):,} bf16 words of the attention sums differ{ref(9)}. "
     f"The largest difference is {sc_m.group(1)} at a largest value of {sc_m.group(2)}." if sc_m else ""),
]
s8_items = [x for x in s8_items if x]
n_fail = sum(1 for u in ut if u["result"] != "passed")
sw_rows = [u for u in ut if u["switch"] != "none"]
s8_unit = [
    (f"All {len(ut)} runs of the test programs pass{ref(10)}." if not n_fail else f"{n_fail} of {len(ut)} runs of the test programs fail{ref(10)}."),
    "The CPU has AMX. Without a switch, t_amx_numerics reports no case without AMX. So its block-kernel cases and its attention cases ran.",
    "t_gated_delta_net does not print which kernel it took. Its cases have checks for both kernels, so its rows look the same with and without a switch.",
    "Four rows repeat two test programs with the kill switch and with the GDN switch set. The advance() cases of t_gated_delta_net then take the chain kernel.",
    "Under a switch t_amx_numerics reports the cases that it did not run. The last column counts them.",
] + ([
    "The last 3 rows are a Debug build of the head without AMX dispatch. It links and passes. Its two AMX test programs then have one placeholder case each.",
] if any(u["build"] == "noamx" for u in ut) else [])
tok = D["tokens"]["rows"]
tok_pairs = D["tokens"]["pairs"]
s8_tokens, s8_scores = [], []
if tok:
    exact_runs = [t for t in tok if t["arm"] in EXACT_ARMS]
    same = [t for t in exact_runs if t["first_difference"] is None]
    p0_runs = [t for t in exact_runs if t["arm"] in ("p0", "a0")]
    repeats = [t for t in tok_pairs if t["kind"] == "repeat"]
    rep_same = [t for t in repeats if t["first_difference"] is None]
    first = lambda arm, prompt: next((t for t in tok if t["arm"] == arm and t["prompt"] == prompt), None)
    where = lambda t: ("it gives the tokens of the base run" if t["first_difference"] is None else
                       f"the first different token is generated token {t['first_difference']}, and {t['equal']} of {t['of']} tokens are equal")
    s8_tokens = [
        f"One more check compares generated tokens{ref(11)}. Each arm ran the same prompt with a fixed thread split and a sampler that takes the best-scoring token.",
        f"The arms without an AMX kernel must give the tokens of the base run. {len(same)} of {len(exact_runs)} such runs did, over 256 generated tokens.",
        f"{len(p0_runs)} of these runs test Part 0: 2 arms at 2 prompts. So Part 0 changes no generated token in this check. The unit tests show the equal bytes.",
    ]
    if repeats:
        s8_tokens.append(f"A second run of an arm gave the tokens of its first run in {len(rep_same)} of {len(repeats)} cases. So the differences below are repeatable.")
    for prompt in sorted({t["prompt"] for t in tok}):
        a_, b_, ab_ = first("a", prompt), first("b", prompt), first("ab", prompt)
        if a_ and b_ and ab_:
            s8_tokens.append(f"At prompt {prompt:,}:" + ul([f"Part A: {where(a_)}.", f"Parts 0 and B: {where(b_)}.", f"Parts A and B: {where(ab_)}."]))
    aab = next((t for t in tok_pairs if t["kind"] == "a_ab" and t["prompt"] == 1024), None)
    tok_ab = SIDE.get("tok-q35-tp4-1u-p1024__ab__rep1")
    if aab and tok_ab:
        s8_tokens.append(f"At prompt 1,024 the run with Parts A and B gives the tokens of the run with Part A at {aab['equal']} of {aab['of']} positions. "
                         f"Both AMX kernels ran in it: {tok_ab['amx_head_tokens']:,} GDN head tokens and {tok_ab['amx_k_tokens'] / 1e6:.1f} million K tokens took the AMX path.")
    pb = [t for t in tok_pairs if t["kind"] == "partb" and t["prompt"] == 1024]
    if pb:
        s8_tokens.append("One more build has the Part B commit alone. It was built before the GDN changes and before the code review.")
        s8_tokens.append(f"At prompt 1,024 it gives the tokens of the arm with Parts 0 and B at {pb[0]['equal']} of {pb[0]['of']} positions."
                         + (" So that difference comes from the AMX attention kernels, not from the GDN changes." if pb[0]["first_difference"] is None else ""))
    s8_tokens.append("A different token is allowed for Part A and Part B. Both change low bits of the scores, and the sampler takes the best score.")

    # ---- what the scores show
    LG, SC = D["logit"], D["scores"]
    if SC.get("repeat"):
        r_ = SC["repeat"]
        s8_scores.append(f"A dump keeps the {r_[0]['k']} best scores of every generated step{ref(17)}. "
                         f"Two runs of the base arm give equal scores at {sum(x['differ'] == 0 for x in r_)} of {len(r_)} compared steps.")
    g0 = {k: next((x for x in SC.get(k, []) if x["g"] == 0), None) for k in ("b", "a")}
    if g0["b"] and g0["a"]:
        s8_scores.append("At generated token 0 the kept scores of the runs with an AMX kernel are close to the base run."
                         + ul([f"With Parts 0 and B, {g0['b']['common']} of the {g0['b']['k']} token ids are in both lists. {g0['b']['differ']} of these scores differ, by at most {g0['b']['largest']:g} bf16 step.",
                               f"With Part A, {g0['a']['common']} token ids are in both lists. {g0['a']['differ']} of these scores differ, by at most {g0['a']['largest']:g} bf16 step."]))
    gb = first("b", 1024)["first_difference"] if first("b", 1024) else None
    lb, la = LG.get((1024, "base", gb)), LG.get((1024, "b", gb))
    if lb and la:
        s8_scores.append(
            f"The run with Parts 0 and B first differs at generated token {gb}. There the two best scores of the base run are "
            + ("equal." if lb["steps"] == 0 else f"{lb['steps']:g} bf16 steps apart.")
            + ul([f"The base run scores {lb['v1']:g} for token id {lb['id1']} and {lb['v2']:g} for token id {lb['id2']}. The sampler takes the first one.",
                  f"The run with Parts 0 and B scores {la['v1']:g} for token id {la['id1']} and {la['v2']:g} for token id {la['id2']}.",
                  f"So one score moved by {la['steps']:g} bf16 step, and the other token id wins."]))
        s8_scores.append(f"An earlier campaign on another model found the same kind of tie{ref(15)}.")
        la1, lab1 = LG.get((1024, "a", gb)), LG.get((1024, "ab", gb))
        if la1:
            s8_scores.append(
                f"The run with Part A has the same tie at generated token {gb}. It scores {la1['v1']:g} for token id {la1['id1']} and {la1['v2']:g} for token id {la1['id2']}, and it takes token id {la1['id1']}."
                if la1["steps"] == 0 else
                f"The run with Part A scores {la1['v1']:g} for token id {la1['id1']} and {la1['v2']:g} for token id {la1['id2']} at generated token {gb}.")
        if lab1:
            s8_scores.append(
                f"The run with Parts A and B scores {lab1['v1']:g} for token id {lab1['id1']} and {lab1['v2']:g} for token id {lab1['id2']} there. "
                + ("So with both AMX kernels the same score does not move, and the token of the base run stays." if lab1["steps"] == 0 and lab1["id1"] == lb["id1"] else
                   f"So it takes token id {lab1['id1']}."))
        else:
            s8_scores.append(f"Insufficient data for the scores of the run with Parts A and B at generated token {gb}. A score dump of that run would give them.")
    ga = first("a", 1024)["first_difference"] if first("a", 1024) else None
    lb, la = LG.get((1024, "base", ga)), LG.get((1024, "a", ga))
    a_rows = [x for x in SC.get("a", []) if ga is not None and x["g"] < ga]
    if lb and la and a_rows:
        early = max(x["best_diff"] for x in a_rows if x["g"] < 80)
        late = max(x["best_diff"] for x in a_rows)
        base_scores = {lb["id1"]: lb["v1"], lb["id2"]: lb["v2"]}
        a_scores = {la["id1"]: la["v1"], la["id2"]: la["v2"]}
        s8_scores.append(
            f"The run with Part A gives the tokens of the base run for {len(a_rows)} steps. Its scores move away from the base run during these steps."
            + ul([f"In steps 0 to 79 its best score differs from the base run by at most {early:g} bf16 step.",
                  f"In the later steps it differs by up to {late:g} bf16 steps.",
                  f"At generated token {ga} the base run scores {lb['v1']:g} for token id {lb['id1']} and {lb['v2']:g} for token id {lb['id2']}. They are {lb['steps']:g} bf16 steps apart.",
                  f"The run with Part A scores {a_scores.get(lb['id1'], float('nan')):g} and {a_scores.get(lb['id2'], float('nan')):g} for them. So the other token id wins."]))
        drop = (lb["v1"] - a_scores.get(lb["id1"], lb["v1"])) / (lb["margin"] / lb["steps"]) if lb["steps"] else None
        s8_scores += [
            "The block kernel runs in prefill only. The counters show all GDN tokens of decode on the token path, in every arm.",
            "So after the prefill the base run and the run with Part A take the same kernels. They are the token kernel for GDN and the AVX-512 path for attention.",
            "The score difference becomes larger while both runs take these kernels.",
            f"This is not a tie. At generated token {ga} the score of token id {lb['id1']} is {drop:g} bf16 steps lower in the run with Part A. So token id {lb['id2']} wins."
            if drop else "This is not a tie.",
            "The dump has scores only. It does not show how much the GDN states and the stored keys and values differ after the prefill.",
        ]
        base_tokens = None
        try:
            base_tokens = open(f"{report_data.RES}/tokens/p1024__base.txt").read().split()
        except OSError:
            pass
        if base_tokens:
            s8_scores.append(f"Insufficient data for how such differences grow with other prompts. The output of this prompt repeats: the base run has {len(set(base_tokens))} different tokens in {len(base_tokens)}. "
                             "The same dump for more prompts would show it.")

_c = "q35-tp4-8u-p1024"
pb_pairs, pb_lo = [], None
if _c in D["col"]["cells"] and all(a in D["col"]["cells"][_c] for a in ("p0", "b", "base")):
    _v = D["col"]["cells"][_c]
    pb_pairs = [100 * (x - y) / _v["base"]["ttft_max_s"]["median"] for x in _v["p0"]["ttft_max_s"]["values"] for y in _v["b"]["ttft_max_s"]["values"]]
    pb_lo = CMP["cells"][_c]["rules"]["task5_partB"]["range"][0]
s9_items = [
    "The measurement covers one server, one model and the prompt texts built into runtron. Other prompts give other decay values and other attention patterns.",
    "The other socket of the server was 42 % busy with other users' jobs in every run. Its effect on our runs is not measured.",
    ("Two verdicts lie closer to their limit than the spread of the repetitions."
     + ul(["The first is the range of Parts 0 and B with 8 users and prompt 1,024. 1 of 3 repetitions is below its low end.",
           "The second is the decode rule with 1 user and prompt 1,024. Its margin is 0.1 percentage points."])),
    (f"The miss of the Part B rule with 8 users and prompt 1,024 is not such a case. All {len(pb_pairs)} pairs of repetitions give {rng(pb_pairs, 1)} %, below the low end of {pb_lo:.1f} % (est.)."
     if pb_pairs and max(pb_pairs) < pb_lo else ""),
    "The core clock inside tron was not read. The clock readings on this page come from stand-alone loops.",
    "The numeric checks used synthetic inputs. A capture of the GDN inputs of one real prompt would give the size of the differences on real data.",
    "The owners of the GDN code have not accepted the numerics contract of Part A. The design named this as a condition. The score comparison of section 9 is data for that decision.",
    "No person has reviewed the code yet. The reviews named on this page were made by AI agents.",
    "The model's registry entry says that its tokens are not yet valid. The token comparison on this page is a check of equal tokens, not of quality.",
    "Part B serves every model with 256-wide heads and 4 query heads per KV head. Only Qwen3.5 4B was run.",
    "Part B also changes two lines of the dispatch code that the 128-wide models run. Their unit tests passed. No 128-wide model was run in tron on this branch.",
    (f"With Part A the work before and after the recurrence is the largest part of the GDN step: {100 * (va['pre'] + va['post']) / tot(va):.0f} %. "
     "The convolution alone was 0.50 us per step in a stand-alone test of 2026-11-20." if va else ""),
    "16 of 56 threads run GDN, as before. Spreading the work over more threads is a scheduling change outside this design.",
]
s9_items = [x for x in s9_items if x] + DW["open_items"]

REFS = [
    "The tron branch <code>jhan-gdn-amx</code> is in the worktree <code>~/workspace/ai-runs/tron-gdn-amx</code>, and its draft PR is https://github.com/positron-ai/tron/pull/5572. "
    f"Its commits are {sha('ctr')} (counters), {sha('pa')} (Part 0 and Part A) and {sha('pab')} (Part B). They sit on top of <code>72e1191804</code>.",
    "The run recipe is <code>exec/gdn-impl-20261121/campaign.sh</code> with <code>exec/gdn-20261120/run-one.sh</code>. "
    "The builds come from <code>build.sh</code> and <code>build-all.sh</code>. The logs are in <code>exec/results/gdn-impl-20261121/rt/</code> and the load snapshots in <code>load/</code>.",
    "The numbers of this page come from <code>collect.py</code>, <code>compare.py</code>, <code>report_data.py</code> and <code>gen_report.py</code> in <code>exec/gdn-impl-20261121/</code>. "
    "The prediction is <code>exec/results/gdn-20261120/predictions.json</code>. Section 4 of <code>GDN/gdn-amx-design.html</code> explains it.",
    "Task 1 is <code>bench/bench_gdn_task1.c</code> with <code>bench/task1.sh</code> in <code>exec/gdn-impl-20261121/</code>. Its results are <code>bench/task1-*.txt</code> in <code>exec/results/gdn-impl-20261121/</code>.",
    "The loop variants are <code>bench/bench_slice_variants.c</code>. Their results are <code>bench/slice-variants-cpu140-run*.txt</code>.",
    "Task 3 is <code>bench/gdn_kernels.hpp</code> and <code>bench/amx_gdn_bench.cpp</code> with <code>bench/task3.sh</code> and <code>bench/task3_burst.sh</code>. "
    "Its results are <code>bench/task3-table-*.txt</code>, <code>task3-clock-cpu140.txt</code> and <code>task3-burst-cpu140.txt</code>.",
    "The test of register clearing before tile work is <code>bench/task3-zeroupper-cpu140.txt</code>.",
    "The test of subnormal decay products is <code>bench/task3-decay-cpu140.txt</code>. The test for stalls of other cores is <code>bench/stall_probe.c</code> with <code>bench/stall_test.sh</code>. Its result is <code>bench/stall-test.txt</code>.",
    "Task 4 is <code>bench/task4_attn256.cpp</code> with <code>bench/task4.sh</code>. Its results are <code>bench/task4-summary-cpu142.txt</code> and <code>bench/task4-table-*.txt</code>. "
    "The files of a first run, made while a build of ours ran, are in <code>bench/task4-first-run/</code>.",
    "The unit-test results are <code>exec/results/gdn-impl-20261121/unit-tests.txt</code>, written by <code>unit-tests.sh</code>. The new test sources are <code>t/t_amx_gdn_numerics.cpp</code> and <code>t/t_gdn_stats.cpp</code>. "
    "Changed test sources are <code>t/t_gated_delta_net.cpp</code>, <code>t/t_amx_numerics.cpp</code> and <code>t/t_amx_dispatch_dtype.cpp</code>.",
    "The token comparison is <code>exec/gdn-impl-20261121/token-check.sh</code>. Its results are in <code>exec/results/gdn-impl-20261121/tokens/</code>.",
    "The counters are documented in <code>README.stats.md</code> of the branch and in Note [GDN path stats] of <code>gdn_stats.hpp</code>.",
    f"Session 1 ran the commits {', '.join(f'<code>{t}</code>' for t in tips1) or 'n/a'}. "
    f"Session 2 ran the commits {', '.join(f'<code>{t}</code>' for t in tips2) or 'n/a'}. "
    "The steps of session 2 are in <code>exec/gdn-impl-20261121/final-chain.sh</code>, and the numbers of session 1 are in <code>comparison-session1.json</code>.",
    "The review findings and their checks are <code>review-result.json</code> and <code>review-verdicts.json</code> in <code>exec/gdn-impl-20261121/understand/</code>. "
    "The second review is <code>review2-result.json</code> in the same folder.",
    "The earlier campaign on token ties is <code>definitive-decode/token30-results.html</code> in this repository.",
    "The branch head differs from the commits of session 2 only in comments, tests, <code>README.stats.md</code> and <code>README.ci.md</code>. "
    "The branch <code>jhan-gdn-amx-measured</code> keeps the commits of session 2. The steps after session 2 are in <code>exec/gdn-impl-20261121/post-chain.sh</code>.",
    "The score dump is <code>exec/gdn-impl-20261121/logit-margin.sh</code> with <code>logit_summary.py</code>. "
    "Its results are <code>tokens/logits-summary-p1024-l*.txt</code> in <code>exec/results/gdn-impl-20261121/</code>.",
    "The tron runs around the fix of section 7 are the logs <code>rt/*__q-a__*</code> (before) and <code>rt/*__f-a__*</code> (after) in <code>exec/results/gdn-impl-20261121/</code>.",
    "The checks of the two draft pages are <code>verify-page-result.json</code> and <code>verify-page-v2-result.json</code> in <code>exec/gdn-impl-20261121/understand/</code>. "
    "The check before the draft PR is <code>pre-pr-check-result.json</code> in the same folder.",
    "Section 5 and the user comparison of section 3 are written by <code>exec/gdn-impl-20261121/decode_why.py</code>. "
    "The decode values come from the decode steps of <code>collected.json</code> (class <code>decode_like</code>). "
    "The prefill values, and all values of the user comparison, come from <code>comparison.json</code>.",
    "The start of a chain is <code>start_from_checkpoint</code> in <code>h/tron/models/gdn_rolling_executor.hpp</code>. A chain that begins a sequence takes <code>start_from_zero</code>. "
    "<code>run_gdn_operation</code> in <code>gdn_execution.hpp</code> times both.",
]
assert len(REFS) == 21
refs_html = '<ol class="refs">' + "".join(f'<li id="ref{i + 1}">[Ref{i + 1}] {r}</li>' for i, r in enumerate(REFS)) + "</ol>"

sample_name = next((k for k in sorted(D["col"]["runs"]) if k.startswith(f"{STEP_CELL}__ab__rep")), None)
g = ((D["col"]["runs"].get(sample_name) or {}).get("gdn") or {}).get("prompt_or_mixed", {}).get("totals")
sample_keys = ["items", "token_head_tokens", "chain_head_tokens", "amx_head_tokens", "amx_blocks", "amx_fallback_blocks", "pre_cycles",
               "amx_recurrence_cycles", "post_cycles", "busy_cycles", "wall_cycles"]
sample = "" if not g else "<pre><code>[gdn-stats] prompt_or_mixed/some_jobs_without_listener totals: {" + ", ".join(f'"{k}":{g[k]}' for k in sample_keys if k in g) + ", ...}</code></pre>"
g_hz = ((D["col"]["runs"].get(sample_name) or {}).get("gdn") or {}).get("summary", {}).get("tsc_hz")
sample_notes = [] if not (g and g_hz) else [
    f"A value with a name that ends in _cycles counts ticks of the CPU time stamp counter. The report gives the tick rate as tsc_hz: {g_hz / 1e9:.2f} GHz on this server.",
    f"Example: busy_cycles / amx_head_tokens / tsc_hz = {g['busy_cycles'] / g['amx_head_tokens'] / g_hz * 1e6:.2f} us per GDN step.",
]
s7_items = [
    "Until now only a trace could time GDN. The new counters time it in every run, with no trace.",
    "They follow the attention statistics of tron." + ul(["One environment variable turns them on.", "Each worker thread has its own counters.",
                                                          "tron prints a report at exit.", "Files show the values while the program runs."]),
    "Per GDN operation and thread they count the work items and the head tokens on each of the three paths.",
    "The paths are the token path (step()), the chain path (the chain kernel) and the AMX block path.",
    "They also count the blocks that the AMX kernel finished and the blocks that it refused.",
    "They time the parts of the work." + ul(["the start of a chain", "the work before the recurrence", "the recurrence, per path",
                                             "the work after the recurrence", "the write of the state"]),
    "Per operation they give the sum, the largest value and the count of the GDN walls.",
    "Two classes of pass are kept apart." + ul(["passes in which every token has a listener: these are decode steps", "all other passes: prefill passes and mixed passes"]),
    "With the switch off, a GDN call tests one flag and reads no clock.",
    f"The files are under <code>/model/&lt;model_id&gt;/gdn/</code> of tron's statistics folder{ref(12)}.",
]

ctl_cells = [r for r in (CMPC or {"cells": {}})["cells"].values() if all(r["arms"].get(a) for a in ("orig", "nost", "base"))]
ctl = [(r["arms"]["orig"], r["arms"]["nost"], r["arms"]["base"]) for r in ctl_cells]
s7_cost = []
if ctl:
    chg = [100 * (b["tps"] - n["tps"]) / n["tps"] for o, n, b in ctl]
    spreads = [x["tps_spread_pct"] for t3_ in ctl for x in t3_]
    worst = min(ctl_cells, key=lambda r: (r["arms"]["base"]["tps"] - r["arms"]["nost"]["tps"]) / r["arms"]["nost"]["tps"])
    wb, wn = worst["arms"]["base"], worst["arms"]["nost"]
    sep = wb["tps_range"][1] < wn["tps_range"][0]
    s2b = next((CMP["cells"][c]["arms"]["base"] for c in CELLS if CMP["cells"][c]["users"] == worst["users"] and CMP["cells"][c]["prompt"] == worst["prompt"]), None)
    s7_cost = [
        f"Control runs give the cost of the counters{ref(2)}. They ran on 3 cells with {min(x[2]['n'] for x in ctl)} repetitions.",
        f"With the GDN counters on, decode speed changed by {srng(chg, 1)} % against the same build with them off.",
        f"The time to first token changed by {srng([100 * (b['ttft_s'] - n['ttft_s']) / n['ttft_s'] for o, n, b in ctl], 1)} %.",
        f"With the counters off, decode speed is within {max(abs(100 * (n['tps'] - o['tps']) / o['tps']) for o, n, b in ctl):.1f} % of the build of 2026-11-20. That build has no GDN counters.",
        "The attention counters were on in all three arms.",
        f"Repetitions of one arm differ by {rng(spreads, 1)} % in decode speed. So these runs show no cost above that spread. They cannot show a cost below about 1 %.",
    ] + ([
        f"With {worst['users']} user{'s' if worst['users'] > 1 else ''} and prompt {worst['prompt']:,}, all 3 control runs with the counters on were slower than all 3 with them off."
        + ul([f"counters on: {wb['tps_range'][0]:.1f} to {wb['tps_range'][1]:.1f} tok/s", f"counters off: {wn['tps_range'][0]:.1f} to {wn['tps_range'][1]:.1f} tok/s"]
             + ([f"the 3 base runs of session 2 in this cell, also with the counters on: {s2b['tps_range'][0]:.1f} to {s2b['tps_range'][1]:.1f} tok/s"] if s2b else []))
        + "More repetitions of that cell would show whether this is a cost."] if sep else [])

RV = report_data.review()
s_review = [
    "Seven AI review agents read the change, each with another focus. Three more agents then checked every finding against the code.",
    f"They reported {RV['n']} findings. The check confirmed {RV['confirmed']} in full and {RV['partly']} in part, and rejected none{ref(14)}.",
    f"{RV['bug']} findings named the same build error. A build without AMX and without optimization failed to link. It is fixed.",
    f"{RV['false_claim']} findings named a comment or a document that did not match the code. {RV['test_gap']} findings named a missing test.",
    "Insufficient data for the count of fixed findings. No file records which findings are fixed. The list below names 9 that are open.",
    "Session 2 ran on the commits with these fixes.",
    "A second review then read the fixes. It found no defect in the code that runs.",
    "It found these points. They are fixed, and the unit tests ran again on the result."
    + ul(["comments that did not match the code, at 5 places", "2 test checks that could not fail", "1 test bound that was not a true bound", "1 gap in README.stats.md"]),
    "A last check before the draft PR compared the change with the rules of the repository. It led to stronger test expectations and corrected commit messages.",
    f"AI agents also recomputed the numbers of two drafts of this page from the raw logs{ref(19)}. Most table values agreed.",
    "They found wrong values in 4 tables of the first draft and in 2 tables of the second draft. These values are corrected.",
    "They also reported unclear sentences and missing facts. This version includes the corrections that the data support.",
    "These findings of the code reviews, among others, are not fixed." + ul([
        "The model-level unit test has no case that proves the 256-wide kernels ran.",
        "No unit test sets the GDN switch. The test programs ran once more with each switch set.",
        "No test runs the counters through the generated model code and a forward pass.",
        "On a CPU without AMX the 5 block-kernel test cases print a warning and pass with no check.",
        "The dispatch test runs 2 of its 5 cases for 256-wide heads, with one KV head.",
        "The clamp of the GDN wall counter has no test.",
        "The attention dispatch repeats one pattern in 3 branches. A shared type for the kernel set would remove the repeat.",
        "The 128-wide and the 256-wide kernels each have a copy of two helper routines.",
        "The query pack of the 256-wide kernel moves one value pair per step, and it runs before the page test.",
    ]),
]

blk_clock = [x[0] for x in T3["clock"].get("block", [])]
bget = lambda k, gap: next((b for b in T3["burst"] if b["kernel"] == k and b["gap_us"] == gap), None)
gaps_ = sorted({b["gap_us"] for b in T3["burst"] if b["gap_us"]})
stall_blk = [x for x in T3["stall"] if x["aggressors"] == "block"]
s9_gdn = [
    f"The stand-alone programs time only the recurrence, on one CPU{ref(6)}.",
    f"In loops of 4 s the system reported a lower core clock for the faster kernels. It reported {rng(blk_clock, 2)} GHz for the block kernel.",
    "The 4 s loops also time the copy of the inputs into the window and the layout change of the start state. The short runs leave both out.",
    "So the two timing columns of the table do not give the cost of the lower clock.",
]
s9_burst = [
    "tron runs the kernel in bursts with other work between them. The next table gives the kernels in such bursts.",
    "One burst is 128 tokens of one key head. That is 256 value-head tokens.",
] + ([
    f"An AMX burst took {bget('block', gaps_[0])['kernel_us']:.0f} us after {gaps_[0]:,} us of scalar work and {bget('block', gaps_[-1])['kernel_us']:.0f} us after {gaps_[-1]:,} us.",
    f"With {gaps_[0]:,} us of scalar work between two AMX bursts, that work ran at {bget('block', gaps_[0])['clock_first_quarter']:.2f} to {bget('block', gaps_[0])['clock_rest']:.2f} GHz. "
    f"With {gaps_[1]:,} us or more it ran at {min(min(bget('block', g_)['clock_first_quarter'], bget('block', g_)['clock_rest']) for g_ in gaps_[1:]):.2f} GHz or more.",
    "Insufficient data for the gap length inside tron. A trace of one GDN thread would give it.",
] if len(gaps_) >= 2 and bget("block", gaps_[0]) else []) + ([
    f"In a test of 4 s, AMX bursts on 16 CPUs did not stall {len(stall_blk)} other CPUs of ours. The longest gap there was {max(x['longest_us'] for x in stall_blk):.1f} us{ref(8)}.",
] if stall_blk else [])
lr = T4.get("loop_ratio") or {}
cache_loop = [v for k, v in lr.items() if k[0] == "cache"]
s9_attn = [
    f"The AMX kernels are {rng(T4['cache_ratio'], 2)} times faster than the AVX-512 path when the pages are in cache{ref(9)}.",
    f"For decode with pages from main memory they are {rng(T4['memory_decode_ratio'], 2)} times faster. Loading the page takes most of the time there.",
    "Each time is the lowest of 7 rounds in one run. The ranges cover 3 runs.",
    (f"The clock readings come from other loops of 4 s. There the ratio was {min(v[0] for v in cache_loop):.2f} to {max(v[1] for v in cache_loop):.2f} with the pages in cache."
     if cache_loop else ""),
    f"The system reported {rng([r['amx_clock'][0] for r in T4['rows']] + [r['amx_clock'][1] for r in T4['rows']], 2)} GHz for the AMX loops "
    f"and {rng([r['avx_clock'][0] for r in T4['rows']] + [r['avx_clock'][1] for r in T4['rows']], 2)} GHz for the AVX-512 loops.",
]
s9_attn = [x for x in s9_attn if x]

fig1 = P.figure(fig_pred_vs_measured(),
                "<b>Figure 1.</b> Predicted and measured fall of the time to first token. "
                + ul(["The pale bar is the predicted range (est.), and the tick is the working value (est.).", "The blue dot is the measured fall, as a percent of the base run of this session.",
                      "The text at the right gives the measured value and where it lies.",
                      "Every dot lies inside its bar and left of its tick. So every fall is inside the range and below the working value."]), "fig1")
fig2 = P.figure(fig_ttft_seconds(), "<b>Figure 2.</b> Time to first token of every arm, relative to the base run (100 %). "
                + ul(["Labels give seconds. Lower is better.", "The gap between the arms with and without Part B grows with the prompt length."]), "fig2")
fig3 = P.figure(fig_decode(), "<b>Figure 4.</b> Decode speed per user, change against the base run. "
                + ul(["Each dot is one arm.", "The pale bar is the range predicted for Part B (est.).", "Part 0 and Part A were predicted to change nothing.",
                      "The label gives the change of the two arms with Part B.",
                      "Only the two arms with Part B move. The change is large only with 8 users and prompts of 4,096 tokens or more."]), "fig4")
fig4 = P.figure(fig_step(), f"<b>Figure 8.</b> Time of one GDN step by part, from the new counters (cell with {cell_name(STEP_CELL)}). "
                + ul(["The values are means over the 16 GDN threads.", "The counters cannot split the step of the base run. Its blue bar is the whole step loop.",
                      "Only the blue part gets shorter with Part 0 and Part A."]), "fig8")
fig5 = P.figure(fig_pass(), "<b>Figure 9.</b> Wall time of one prefill pass and its GDN part, for the smallest and the largest cell. "
                + ul(["The blue part gets shorter with Part 0 and again with Part A.", "The grey part gets shorter only with Part B. It includes the attention work."]), "fig9")
fig6 = P.figure(fig_kernels(), "<b>Figure 10.</b> Time of the GDN recurrence per value head and token, stand-alone on one CPU of delphi-3b35. "
                + ul(["The upper group gives the median of 3 runs. Each run takes the lowest of 60 rounds.",
                      "The lower group gives the median of 3 loops of 4 s, with the core clock that the system reported.",
                      "The 4 s loops also time the copy of the inputs. So the two groups do not give the cost of the lower clock."]), "fig10")

# The page is written the way the design page is: title, style and content, with no html, head or body tags.
# The Artifact publish step wraps it. A browser opens the file as it is.
page = f"""<title>GDN AMX Results</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&amp;family=Space+Grotesk:wght@500;600&amp;family=JetBrains+Mono:wght@400&amp;display=swap">
<style>{P.CSS}{DW["css"]}</style>
<div class="sheet">
<div class="col">
<h1>GDN and AMX on Qwen3.5 4B: what was built and what it gave</h1>
<p class="meta">2026-11-21 (PST). Measured on our half of delphi-3b35, the test server. The code is tron, the inference program under test, on the branch jhan-gdn-amx.</p>
<p class="meta">This page follows the design page gdn-amx-design.html. It compares the measurement with the prediction of that page.</p>
<div class="short">
<h2>Short version</h2>
{ul(short_items)}
</div>
<p>The three changes, and one addition:</p>
{ul(intro_items)}
</div>
<h3>The changes in one table</h3>
{glance_table()}
{fig1}
<div class="col">
{words_html}
<ul class="toc">
<li><a href="#s1">1. What was built</a></li>
<li><a href="#s2">2. How it was measured</a></li>
<li><a href="#s3">3. Time to first token</a></li>
<li><a href="#s4">4. Decode speed</a></li>
<li><a href="#s5">5. Why decode gains little</a></li>
<li><a href="#s6">6. Measurement against the prediction</a></li>
<li><a href="#s7">7. A problem found during the work</a></li>
<li><a href="#s8">8. The new GDN counters</a></li>
<li><a href="#s9">9. Numerics and tests</a></li>
<li><a href="#s10">10. Stand-alone measurements</a></li>
<li><a href="#s11">11. Limits and open points</a></li>
<li><a href="#s12">12. Sources</a></li>
</ul>
</div>

<h2 id="s1">1. What was built</h2>
<div class="col">
{s1_built}
</div>
{table(["Piece", "Where", "What"], code_rows, kind="prose")}
<div class="col">
<h3>Differences from the design</h3>
{ul(diff_items)}
</div>

<h2 id="s2">2. How it was measured</h2>
<div class="col">
{ul(s2_items)}
</div>
{table(["Arm", "Name on this page", "Build", "Switch", "GDN prefill uses", "Attention uses"], arms_rows)}
<div class="col">
<h3>Which kernel takes a token</h3>
{ul(s2_kernels)}
</div>
<div class="col">
<h3>Load of the shared server before the runs</h3>
{ul(s2_load)}
</div>
{load_table()}

<h2 id="s3">3. Time to first token</h2>
<div class="col">
{ul(s3_items)}
</div>
{fig2}
{ttft_table()}
{DW["sec3"]}
<div class="col">
<h3>The earlier session</h3>
{ul(s3_sessions)}
</div>
{sessions_table() if s3_sessions else ""}

<h2 id="s4">4. Decode speed</h2>
<div class="col">
{ul(s4_items)}
</div>
{fig3}
{decode_table()}
<div class="col">
<h3>Where the decode gain comes from</h3>
{ul(s4_why)}
</div>

<h2 id="s5">5. Why decode gains little</h2>
{DW["sec5"]}
<h2 id="s6">6. Measurement against the prediction</h2>
<div class="col">
<h3>The pass rules of the plan</h3>
<p>The design page set a pass rule for each of its 6 tasks. The table gives the outcome of each rule{ref(3)}.</p>
</div>
{rules_table()}
<div class="col">
<h3>Where the GDN step time goes</h3>
{ul(s5_gdn)}
</div>
{fig4}
{step_table()}
<div class="col">
<h3>From the GDN step to the pass</h3>
{ul(s5_wall)}
</div>
{fig5}
<div class="col">
<h3>Attention with Part B</h3>
{ul(s5_attn)}
<h3>All measured parts of a prefill pass</h3>
</div>
{terms_table()}

<h2 id="s7">7. A problem found during the work</h2>
<div class="col">
{ul(s6_items)}
</div>
{decay_table()}

<h2 id="s8">8. The new GDN counters</h2>
<div class="col">
{ul(s7_items)}
<p>One line of the exit report of a run with Parts A and B, shortened:</p>
{sample}
{ul(sample_notes)}
<h3>What the counters cost</h3>
{ul(s7_cost) if s7_cost else "<p>Insufficient data. Control runs with the counters on and off would give the cost.</p>"}
</div>
{controls_table() if s7_cost else ""}

<h2 id="s9">9. Numerics and tests</h2>
<div class="col">
{ul(s8_items)}
</div>
{numerics_table()}
<div class="col">
<h3>Generated tokens</h3>
{ul(s8_tokens) if s8_tokens else ""}
<p>The table gives every comparison. Token positions count from 0.</p>
</div>
{tokens_table() if tok else ""}
<div class="col">
<h3>What the scores show</h3>
{ul(s8_scores) if s8_scores else "<p>Insufficient data. A dump of the scores of the differing steps would show them.</p>"}
</div>
<div class="col">
<h3>Unit tests on delphi-3b35</h3>
{ul(s8_unit)}
</div>
{unit_table()}
<div class="col">
<h3>Review of the code and of this page</h3>
{ul(s_review)}
</div>

<h2 id="s10">10. Stand-alone measurements</h2>
<div class="col">
<h3>The GDN recurrence kernels (tasks 1 and 3)</h3>
{ul(s9_gdn)}
</div>
{fig6}
{kernel_table()}
<div class="col">
{ul(s9_burst)}
</div>
{burst_table()}
<div class="col">
<h3>The attention kernel for 256-wide heads (task 4)</h3>
{ul(s9_attn)}
</div>
{task4_table()}

<h2 id="s11">11. Limits and open points</h2>
<div class="col">
{ul(s9_items)}
</div>

<h2 id="s12">12. Sources</h2>
<div class="col">
{refs_html}
</div>
</div>
{DW["script"]}
"""


def nowrap(html_text):
    token = re.compile(r"\b\d+(?:\.\d+)?e-\d+\b|\b2\^-?\d+|\bAVX-512\b")
    out = []
    for part in re.split(r"(<svg\b.*?</svg>|<script\b.*?</script>|<style\b.*?</style>|<pre\b.*?</pre>|<code\b.*?</code>|<title\b.*?</title>|<[^>]+>)", html_text, flags=re.S):
        out.append(part if part.startswith("<") else token.sub(lambda m: f'<span class="nw">{m.group(0)}</span>', part))
    return "".join(out)


page = nowrap(page)
page = page.encode("ascii", "xmlcharrefreplace").decode("ascii")
P.assert_ascii(page)
open(OUT, "w").write(page)
print("wrote", OUT, len(page), "bytes")
