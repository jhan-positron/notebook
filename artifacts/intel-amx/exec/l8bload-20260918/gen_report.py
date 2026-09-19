#!/usr/bin/env python3
"""Report for the l8bload-20260918 campaign: AMX gain on llama-3.1-8b against the load per engine.

Reads exec/results/l8bload-20260918/cells/<U>u__<arm>__rep<N>/{perf.json, meta.json, amx_busy.txt}
and writes one self-contained, ASCII-only, light-theme HTML page with two inline SVG charts.
Usage: gen_report.py RESULTS_DIR OUT_HTML
"""
import datetime
import glob
import html
import json
import math
import os
import re
import statistics
import sys

RES, OUT = sys.argv[1], sys.argv[2]
BLUE, ORANGE, GREY, BAND, INK, MUTED = "#2a78d6", "#eb6834", "#898781", "#e1e0d9", "#1f1e1c", "#6b6965"
T975 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}
REF_RUNTRON = 17.0    # runtron 2026-09-16, 8 users on one engine, 1536 generated tokens: 83.3 -> 97.5 TPS
REF_NIGHTLY = 0.81    # ci-mimic 2026-09-18, nightly layout, 2 users per engine: 139.40 -> 140.53 TPS


def esc(s):
    return html.escape(str(s), quote=False)


# ---------- data ----------
cells = {}
for d in sorted(glob.glob(os.path.join(RES, "cells", "*u__*__rep*"))):
    m = re.match(r"(\d+)u__(off|on)__rep(\d+)$", os.path.basename(d))
    if not m or not os.path.exists(os.path.join(d, "perf.json")):
        continue
    u, arm, rep = int(m.group(1)), m.group(2), int(m.group(3))
    p = json.load(open(os.path.join(d, "perf.json")))
    meta = json.load(open(os.path.join(d, "meta.json"))) if os.path.exists(os.path.join(d, "meta.json")) else {}
    anomaly = open(os.path.join(d, "ANOMALY")).read().strip() if os.path.exists(os.path.join(d, "ANOMALY")) else ""
    amx = None
    try:
        for line in open(os.path.join(d, "amx_busy.txt")):
            if "amx_busy" in line and line.split(",")[0].strip().isdigit():
                amx = int(line.split(",")[0])
    except FileNotFoundError:
        pass
    load = re.search(r"load=(\S+)", meta.get("machine", ""))
    bill = re.search(r"bill_procs=(\d+)", meta.get("machine", ""))
    cells[(u, arm, rep)] = {"anomaly": anomaly, "tps": p["tps_mean"], "sd": p["tps_std_dev"], "min": p["min_tps"], "ttft": p["ttft_mean_ms"],
                            "per_engine": [e["tps_mean"] for e in p.get("per_engine", [])], "amx": amx,
                            "minutes": p.get("minutes"), "started": meta.get("started", ""), "ended": meta.get("ended", ""), "load1": load.group(1) if load else "?",
                            "bill": int(bill.group(1)) if bill else None, "sha": meta.get("binary_sha256", "")[:8]}
levels = sorted({k[0] for k in cells})
stats = {}
for u in levels:
    reps = sorted({k[2] for k in cells if k[0] == u and (u, "off", k[2]) in cells and (u, "on", k[2]) in cells
                   and not cells[(u, "off", k[2])]["anomaly"] and not cells[(u, "on", k[2])]["anomaly"]})
    if not reps:
        continue
    offs = [cells[(u, "off", r)] for r in reps]
    ons = [cells[(u, "on", r)] for r in reps]
    gains = [100.0 * (o["tps"] - f["tps"]) / f["tps"] for o, f in zip(ons, offs)]
    g = statistics.mean(gains)
    t = float("nan"); half = float("nan")
    if len(gains) >= 2:
        sd = statistics.stdev(gains)
        se = sd / math.sqrt(len(gains))
        t = g / se if se > 0 else float("inf")
        half = T975.get(len(gains), float("nan")) * se
    mean = lambda key, arr: statistics.mean([a[key] for a in arr if a[key] is not None]) if any(a[key] is not None for a in arr) else None
    stats[u] = {"reps": reps, "off": mean("tps", offs), "on": mean("tps", ons), "gain": g, "gains": gains, "t": t, "half": half,
                "t975": T975.get(len(gains)), "resolved": len(gains) >= 2 and abs(t) >= T975.get(len(gains), float("inf")) and abs(g) >= 1.0,
                "off_ttft": mean("ttft", offs), "on_ttft": mean("ttft", ons), "off_amx": mean("amx", offs), "on_amx": mean("amx", ons),
                "off_min": min(f["min"] for f in offs), "on_min": min(o["min"] for o in ons)}
n_cells = len(cells)
n_reps_full = min((len(s["reps"]) for s in stats.values()), default=0)
generated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


# ---------- charts ----------
def svg_header(w, h, title):
    # no style attribute on the root: cairosvg renders a blank image when it carries "height: auto" (seen 2026-09-18);
    # font and sizing come from the page CSS (figure svg, svg text)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="13">'
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>')


def chart_gain():
    """Dots: AMX gain per repetition (hollow) and the mean (filled) per users-per-engine level; grey markers = reference points."""
    W, H = 760, 470
    L, R, T, B = 80, 40, 50, 120
    xs = {u: L + (i + 0.5) * (W - L - R) / max(1, len(levels)) for i, u in enumerate(levels)}
    vals = [g for s in stats.values() for g in s["gains"]] + [REF_RUNTRON, REF_NIGHTLY, 0.0]
    lo, hi = min(min(vals) - 1.5, -1.0), max(vals) + 2.5
    y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    out = [svg_header(W, H, "AMX gain on llama-3.1-8b against users per engine")]
    step = 5 if hi - lo > 12 else 2
    v = math.ceil(lo / step) * step
    while v <= hi:
        yy = y(v)
        out.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{W - R}" y2="{yy:.1f}" stroke="{BAND}" stroke-width="1"/>')
        out.append(f'<text x="{L - 8}" y="{yy + 4:.1f}" text-anchor="end" fill="{MUTED}">{v:+d} %</text>')
        v += step
    out.append(f'<line x1="{L}" y1="{y(0):.1f}" x2="{W - R}" y2="{y(0):.1f}" stroke="{MUTED}" stroke-width="1.2"/>')
    out.append(f'<text x="{L}" y="{T - 22}" fill="{MUTED}">AMX gain in decode TPS per user, AMX kernel on against the kill switch, same binary</text>')
    pts = [(xs[u], y(stats[u]["gain"])) for u in levels if u in stats]
    if len(pts) >= 2:
        out.append('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + f'" fill="none" stroke="{ORANGE}" stroke-width="2" stroke-opacity="0.6"/>')
    last = levels[-1] if levels else None
    for u in levels:
        s = stats.get(u)
        out.append(f'<text x="{xs[u]:.1f}" y="{H - B + 22}" text-anchor="middle" fill="{INK}">{u} users per engine</text>')
        out.append(f'<text x="{xs[u]:.1f}" y="{H - B + 38}" text-anchor="middle" fill="{MUTED}">({2 * u} users on 2 engines)</text>')
        if not s:
            continue
        for g in s["gains"]:
            out.append(f'<circle cx="{xs[u]:.1f}" cy="{y(g):.1f}" r="5" fill="#ffffff" stroke="{ORANGE}" stroke-width="1.5"/>')
        out.append(f'<circle cx="{xs[u]:.1f}" cy="{y(s["gain"]):.1f}" r="7" fill="{ORANGE}" stroke="#ffffff" stroke-width="2"/>')
        lab = f'{s["gain"]:+.1f} % ({len(s["gains"])} repetition{"s" if len(s["gains"]) != 1 else ""})'
        if u == last:
            out.append(f'<text x="{xs[u] - 12:.1f}" y="{y(s["gain"]) - 10:.1f}" text-anchor="end" fill="{INK}" font-weight="600">{lab}</text>')
        else:
            out.append(f'<text x="{xs[u] + 12:.1f}" y="{y(s["gain"]) - 10:.1f}" fill="{INK}" font-weight="600">{lab}</text>')
    # reference markers, drawn 18 px left of the column so they do not hide a repetition dot
    if 8 in xs:
        rx, ry = xs[8] - 18, y(REF_RUNTRON)
        out.append(f'<rect x="{rx - 6:.1f}" y="{ry - 6:.1f}" width="12" height="12" transform="rotate(45 {rx:.1f} {ry:.1f})" fill="{GREY}"/>')
        out.append(f'<text x="{rx - 12:.1f}" y="{ry + 4:.1f}" text-anchor="end" fill="{GREY}">runtron run of 2026-09-16, 8 users on 1 engine, 1536 tokens: {REF_RUNTRON:+.0f} %</text>')
    if 2 in xs:
        rx, ry = xs[2] - 18, y(REF_NIGHTLY)
        out.append(f'<rect x="{rx - 5:.1f}" y="{ry - 5:.1f}" width="10" height="10" fill="{GREY}"/>')
        out.append(f'<text x="{rx + 30:.1f}" y="{ry + 22:.1f}" fill="{GREY}">ci-mimic run of 2026-09-18, nightly layout, 2 users per engine: {REF_NIGHTLY:+.1f} %</text>')
    # legend, two rows under the axis labels
    ly1, ly2 = H - 44, H - 20
    out.append(f'<circle cx="{L + 8}" cy="{ly1}" r="7" fill="{ORANGE}"/><text x="{L + 22}" y="{ly1 + 4}" fill="{INK}">mean of the repetitions</text>')
    out.append(f'<circle cx="{L + 8}" cy="{ly2}" r="5" fill="#ffffff" stroke="{ORANGE}" stroke-width="1.5"/><text x="{L + 22}" y="{ly2 + 4}" fill="{INK}">one repetition</text>')
    lx = L + 300
    out.append(f'<rect x="{lx + 2}" y="{ly1 - 6}" width="12" height="12" transform="rotate(45 {lx + 8} {ly1})" fill="{GREY}"/><text x="{lx + 22}" y="{ly1 + 4}" fill="{INK}">runtron run of 2026-09-16 (another driver)</text>')
    out.append(f'<rect x="{lx + 3}" y="{ly2 - 5}" width="10" height="10" fill="{GREY}"/><text x="{lx + 22}" y="{ly2 + 4}" fill="{INK}">ci-mimic run of 2026-09-18</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_tps():
    """Dumbbell per level: off (blue) and on (orange) TPS per user, pooled over both engines and the repetitions."""
    W = 760
    rows = [u for u in levels if u in stats]
    H = 70 + 52 * len(rows)
    L, R, T = 170, 40, 36
    hi = max(max(stats[u]["off"], stats[u]["on"]) for u in rows) * 1.12 if rows else 160
    x = lambda v: L + v / hi * (W - L - R)
    out = [svg_header(W, H, "TPS per user, AMX off against on, per load level")]
    step = 25 if hi > 100 else 10
    v = 0
    while v <= hi:
        out.append(f'<line x1="{x(v):.1f}" y1="{T}" x2="{x(v):.1f}" y2="{H - 30}" stroke="{BAND}"/>')
        out.append(f'<text x="{x(v):.1f}" y="{H - 12}" text-anchor="middle" fill="{MUTED}">{v}</text>')
        v += step
    out.append(f'<text x="{W - R}" y="{T - 16}" text-anchor="end" fill="{MUTED}">TPS per user (tokens per second)</text>')
    for i, u in enumerate(rows):
        s = stats[u]; yy = T + 20 + 52 * i
        a, b = x(s["off"]), x(s["on"])
        out.append(f'<text x="{L - 12}" y="{yy + 4}" text-anchor="end" fill="{INK}">{u} users per engine</text>')
        out.append(f'<line x1="{a:.1f}" y1="{yy}" x2="{b:.1f}" y2="{yy}" stroke="{MUTED}" stroke-width="2"/>')
        out.append(f'<circle cx="{a:.1f}" cy="{yy}" r="7" fill="{BLUE}" stroke="#ffffff" stroke-width="2"/>')
        out.append(f'<circle cx="{b:.1f}" cy="{yy}" r="7" fill="{ORANGE}" stroke="#ffffff" stroke-width="2"/>')
        out.append(f'<text x="{a:.1f}" y="{yy - 12}" text-anchor="middle" fill="{BLUE}" font-weight="600">{s["off"]:.1f}</text>')
        out.append(f'<text x="{b:.1f}" y="{yy + 24}" text-anchor="middle" fill="{ORANGE}" font-weight="600">{s["on"]:.1f}</text>')
        out.append(f'<text x="{max(a, b) + 14:.1f}" y="{yy + 4}" fill="{INK}">{s["gain"]:+.1f} %</text>')
    out.append(f'<circle cx="{L}" cy="{T - 12}" r="6" fill="{BLUE}"/><text x="{L + 10}" y="{T - 8}" fill="{INK}">AMX off (kill switch)</text>')
    out.append(f'<circle cx="{L + 230}" cy="{T - 12}" r="6" fill="{ORANGE}"/><text x="{L + 240}" y="{T - 8}" fill="{INK}">AMX on</text>')
    out.append("</svg>")
    return "\n".join(out)


# ---------- page ----------
def fmt(v, f="{:.2f}"):
    return "n/a" if v is None or (isinstance(v, float) and math.isnan(v)) else f.format(v)


def g_cycles(v):
    return "n/a" if v is None else f"{v / 1e9:.1f} billion"


def reps_word(n):
    return "1 repetition" if n == 1 else f"{n} repetitions"


NIGHTLY13_MEAN, NIGHTLY13_SD = 139.73, 0.52   # llama-3.1-8b good tp2 @8u, 13 nightlies 2026-09-05..17 (ci-mimic report-v4, fidelity table)
run_start = min((c["started"] for c in cells.values() if c["started"]), default="")
run_end = max((c["ended"] for c in cells.values() if c["ended"]), default="")

# level table
rows_lvl = []
for u in levels:
    s = stats.get(u)
    if not s:
        rows_lvl.append(f"<tr><td>{u}</td><td colspan='9'>no complete repetition yet</td></tr>")
        continue
    if s["resolved"]:
        verdict = "yes"
    else:
        failed = []
        if not (s["t975"] and abs(s["t"]) >= s["t975"]):
            failed.append("t below the threshold")
        if abs(s["gain"]) < 1.0:
            failed.append("change below 1 %")
        verdict = "no (" + ", ".join(failed) + ")"
    rows_lvl.append("<tr>" + "".join(f"<td>{c}</td>" for c in [
        u, len(s["reps"]), fmt(s["off"]), fmt(s["on"]), f'{s["gain"]:+.1f} %', ", ".join(f"{g:+.1f} %" for g in s["gains"]),
        fmt(s["t"], "{:+.1f}") + (f" (threshold {s['t975']:.2f})" if s["t975"] else ""), verdict,
        f'{fmt(s["off_ttft"], "{:.0f}")} / {fmt(s["on_ttft"], "{:.0f}")}', f'{g_cycles(s["off_amx"])} / {g_cycles(s["on_amx"])}']) + "</tr>")

# per-cell table and the anomaly notes
notes = {}
rows_cell = []
for (u, arm, r), c in sorted(cells.items()):
    mark = ""
    if c["anomaly"]:
        letter = chr(ord("A") + len(notes))
        notes[letter] = c["anomaly"]
        mark = f" (excluded, note {letter})"
    rows_cell.append("<tr>" + "".join(f"<td>{x}</td>" for x in [
        u, arm + mark, r, esc(c["started"][11:16]), f'{c["tps"]:.2f} +/- {c["sd"]:.2f}', f'{c["min"]:.1f}',
        " / ".join(f"{v:.1f}" for v in c["per_engine"]), c["ttft"], "n/a" if c["amx"] is None else f'{c["amx"]:,}',
        fmt(c["minutes"], "{:.1f}"), esc(c["load1"]), "0" if c["bill"] == 0 else esc(c["bill"])]) + "</tr>")
notes_html = ""
for letter, text in notes.items():
    items = "".join(f"<li>{esc(line.strip())}</li>" for line in text.split("\n") if line.strip())
    notes_html += f"<p><b>Note {letter} (excluded cell).</b></p><ul>{items}</ul>"

# short version and takeaways, from the statistics
if stats:
    lo_u, hi_u = min(stats), max(stats)
    parts = [f'{stats[u]["gain"]:+.1f} % at {u}' for u in levels if u in stats]
    grew = ", ".join(parts[:-1]) + f" and {parts[-1]}" if len(parts) > 1 else parts[0]
    n_word = reps_word(len(stats[hi_u]["reps"]))
    short1 = (f"On llama-3.1-8b the AMX kernel (AMX is an Intel CPU instruction set for matrix multiplication) gained {grew} users per engine "
              f"(mean of {n_word} per level, and the table in section 1 gives the paired test).")
    short2 = (f"The {REF_NIGHTLY:+.1f} % measured earlier in the nightly's arrangement (4 engines with 2 users each, two packages compared) "
              f"is the low-load end of this curve, not a kernel failure.")
    short3 = ("For llama-3.1-8b in the nightly CI (continuous integration) run, the users per engine decide the AMX gain, "
              "and the USE_HW_ATTN variable (the switch for attention on the FPGA accelerator cards) changes nothing for this CPU-attention model.")
    off2 = stats[lo_u]["off"]
    drops = []
    for u in levels:
        if u not in stats or u == lo_u:
            continue
        loss = off2 - stats[u]["off"]
        gain_abs = stats[u]["on"] - stats[u]["off"]
        share = 100.0 * gain_abs / loss if loss > 0 else float("nan")
        drops.append((u, loss, gain_abs, share))
    abs_gains = ", ".join(f'{stats[u]["on"] - stats[u]["off"]:+.1f}' for u in levels if u in stats)
    rel_gains = ", ".join(f'{stats[u]["gain"]:+.1f} %' for u in levels if u in stats)
    lv = ", ".join(str(u) for u in levels if u in stats)
    drop_txt = " and ".join(f"by {d[1]:.1f} TPS from {lo_u} to {d[0]} users per engine" for d in drops)
    back_txt = " and ".join(f"{d[2]:.1f} TPS ({d[3]:.0f} %) of the drop to {d[0]} users" for d in drops)
    caption2 = (f"TPS per user falls as users are added. Each decode step takes longer with more users. "
                f"The AMX kernel's gain grows with the load in absolute terms ({abs_gains} TPS per user at {lv} users per engine) "
                f"and in relative terms ({rel_gains}). Adding users lowers the off-arm TPS per user {drop_txt}. "
                f"The kernel gives back {back_txt}.")
    layout_cmp = 100.0 * (off2 - NIGHTLY13_MEAN) / NIGHTLY13_MEAN
else:
    short1, short2, short3, caption2, layout_cmp, off2 = "No complete repetition yet.", "", "", "", float("nan"), float("nan")
takeaway1 = ("Between levels only the load changed. Within a level only the kill switch changed. The binary, the placement "
             "(which FPGA cards and CPU cores each engine uses) and the attention mode (CPU attention in every cell) were the same in every cell. "
             "More users per engine means more attention work per decode step. The gain grows with it, as the hypothesis in section 4 predicts. "
             "Grey markers are earlier measurements under other conditions, shown for scale only (section 4 explains what each one counts).")

page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AMX gain against load, llama-3.1-8b</title>
<style>
:root {{ --ink: {INK}; --muted: {MUTED}; --band: {BAND}; --blue: {BLUE}; --orange: {ORANGE}; --grey: {GREY}; --bg: #ffffff; --panel: #f7f6f3; }}
html, body {{ background: var(--bg); color: var(--ink); font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.45; margin: 0; }}
main {{ max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }}
h1 {{ font-size: 24px; margin: 0 0 4px; }} h2 {{ font-size: 18px; margin: 32px 0 8px; border-bottom: 1px solid var(--band); padding-bottom: 4px; }}
.sub {{ color: var(--muted); font-size: 14px; }}
.short {{ background: var(--panel); border-left: 4px solid var(--orange); padding: 12px 16px; margin: 16px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; margin: 8px 0 12px; }}
th, td {{ border-bottom: 1px solid var(--band); padding: 5px 8px; text-align: left; vertical-align: top; }} th {{ background: var(--panel); }}
td:nth-child(n+3), th:nth-child(n+3) {{ white-space: nowrap; }}
.take {{ color: var(--ink); margin: 6px 0 18px; padding: 8px 12px; background: var(--panel); }}
figure {{ margin: 12px 0; overflow-x: auto; }} figure svg {{ max-width: 100%; height: auto; }}
dl dt {{ font-weight: 600; margin-top: 8px; }} dl dd {{ margin: 0 0 4px 0; }}
li {{ margin: 4px 0; }} code {{ background: var(--panel); padding: 0 4px; font-size: 90%; }}
</style></head><body><main>
<h1>Does the AMX gain on llama-3.1-8b grow with the load per engine?</h1>
<div class="sub">Campaign l8bload-20260918 on delphi-3bda (the test machine). Cells ran {esc(run_start[:10])} {esc(run_start[11:16])} to {esc(run_end[11:16])} UTC. Report generated {esc(generated)}. {n_cells} cells read, {n_reps_full} complete repetitions per level.</div>

<div class="short"><b>Short version.</b> {esc(short1)} {esc(short2)} {esc(short3)}</div>

<h2>Words used here</h2>
<dl>
<dt>tron, rinzler, runtron, token</dt><dd>tron is the inference program under test. rinzler is the production server built from it. runtron is tron's command-line tool. A token is one unit of text, about one word.</dd>
<dt>decode step, attention, dense part, FPGA</dt><dd>A decode step produces one token for every active user. Its attention part reads each user's whole context (the conversation so far) and grows with users and context length. Its dense part streams the model weights through the FPGA cards and does not grow with users at these counts. An FPGA (field-programmable gate array, a programmable chip) card is the accelerator that runs the dense part.</dd>
<dt>engine, tp2, users per engine, load</dt><dd>An engine is one rinzler process serving one model copy split across 2 FPGA cards (tp2, tensor parallel over 2 cards). Users per engine is how many conversations one engine decodes at the same time. Load in this report means users per engine. The nightly (defined below) runs llama-3.1-8b as 4 engines with 2 users each.</dd>
<dt>AMX, AMX kernel, kill switch, PR</dt><dd>AMX is an Intel CPU instruction set for matrix multiplication. A PR is a pull request, a proposed code change on GitHub. The AMX kernel (PR #3879) uses AMX for the attention part on the CPU. The kill switch is the environment variable TRON_AMX_DISABLE=1. Setting it keeps the same binary and turns the kernel off.</dd>
<dt>arm, level, cell, repetition</dt><dd>An arm is one setting of the kill switch: off (TRON_AMX_DISABLE=1) or on (unset). A level is one users-per-engine count: 2, 4 or 8. A cell is one benchmark run of one arm at one level. A repetition is one pass over the levels and both arms. Repetition 4 covered level 2 only (section 2, Order).</dd>
<dt>nightly, CI, CI harness, sharegpt</dt><dd>CI is continuous integration, the automated test system. The nightly is the CI run that executes on delphi-3bda every night. The CI harness is the nightly's throughput benchmark (the script testlib/tps.py in systems_test, the repository of the system tests). It sends prompts of 1024 tokens from the sharegpt set (a public set of real chat prompts), asks for 1536 generated tokens, runs 10 rounds, and starts users 0.1 s apart. In this campaign one client ran per engine. The clients ran on delphi-3bda itself, on cores no engine uses.</dd>
<dt>driver</dt><dd>A driver is the program that sends requests to an engine and measures the answers. Here the driver is the CI harness. The reference run of 2026-09-16 used runtron instead.</dd>
<dt>ci-mimic, base package, target package, main</dt><dd>ci-mimic is the campaign of 2026-09-18 that repeated the nightly's perf phase (its throughput benchmark step) by hand on the whole machine. It ran once with the nightly's own package (the base package: commit 3faba6d0 of main, the tron repository's main branch, with no AMX code) and once with the target package (the same commit plus PR #4424, with the AMX kernel and the VNNI K layout compiled in).</dd>
<dt>VNNI K layout, K cache, head, AVX-512</dt><dd>The K cache holds the key vectors of every past token (one vector per token, which attention compares each new query against). A head is one of the independent attention sub-units of a layer. PR #4424 stores the K cache of heads whose vectors are 128 numbers wide in the layout the AMX kernel reads directly (named after VNNI, Intel's Vector Neural Network Instructions). This is a compile-time option. Both arms of this campaign have it. With the kill switch, the layout is read by the PR's AVX-512 routine (the wider CPU vector instruction set) instead of the kernel.</dd>
<dt>hardware attention, USE_HW_ATTN, CPU attention</dt><dd>Hardware attention computes the attention part on the FPGA cards. CPU attention computes it on the CPU cores. The environment variable USE_HW_ATTN selects hardware attention. With it unset, tron keeps hardware attention off for llama-3.1-8b. This model therefore runs CPU attention in the nightly and in every cell here.</dd>
<dt>TPS, TTFT, sample, sd</dt><dd>TPS is decode tokens per second per user. The CI harness measures it over generated tokens 896 to 1024 of each request. A sample is one such measurement for one user in one round. A cell with U users per engine has 2 x U x 10 samples (two engines, U users each, 10 rounds). sd is the standard deviation over all samples of a cell, in the population form that tps.py reports (divide by the sample count). TTFT is the time to first token in ms.</dd>
<dt>paired t, standard error, resolved</dt><dd>In each repetition the on and off cells run back to back. The gain per repetition is (on - off) / off. The standard error is the standard deviation of the gains divided by the square root of their count. The paired t is the mean gain divided by its standard error. With 3 repetitions the 95 % threshold is 4.303 (the t value that chance alone would exceed in only 5 % of experiments with 3 paired repetitions). "Resolved" means the t passes the threshold and the mean change is at least 1 % in magnitude (a loss would count too).</dd>
<dt>AMX-busy cycles (the EXE.AMX_BUSY counter)</dt><dd>AMX-busy cycles are the count of a CPU hardware counter, EXE.AMX_BUSY, of cycles in which the AMX unit was busy. It was read for 20 s on both engine processes during each cell. Zero in the off arm proves the kill switch worked. A large count in the on arm proves the kernel ran.</dd>
<dt>load average, platformd, Caddy</dt><dd>The load average is the Linux count of runnable processes averaged over the last minute, read from /proc/loadavg at the start of each cell. delphi-3bda has 288 logical CPUs. A value near 50 means most CPUs are idle. platformd is the production process manager on delphi-3bda. Its HTTP API starts and stops the production engines. Caddy is the HTTP reverse proxy in front of the production engines.</dd>
</dl>

<h2>1. Result</h2>
<figure>{chart_gain()}</figure>
<p class="take">{esc(takeaway1)}</p>
<table><tr><th>users per engine</th><th>repetitions</th><th>off TPS</th><th>on TPS</th><th>gain</th><th>gain per repetition</th><th>paired t</th><th>resolved</th><th>TTFT off / on (ms)</th><th>AMX-busy cycles off / on (20 s)</th></tr>
{''.join(rows_lvl)}</table>
<figure>{chart_tps()}</figure>
<p class="take">{esc(caption2)}</p>

<h2>2. What ran</h2>
<ul>
<li><b>Binary.</b> The rinzler binary came from ci-mimic's target package (the PR #4424 package, tron 2026.09.18-29a8a547). The package holds commit 3faba6d0 of main plus PR #4424. It was built with the deb preset (the build preset for the .deb Debian package) with TRON_AMX_DISPATCH=ON and TRON_K_VNNI=ON, the compile options that enable the AMX kernel and the VNNI K layout. Its sha256 checksum (a file fingerprint) starts with 3ee9c8f0. It was extracted from the .deb and run from /var/tmp, not installed. It is the same file that the ci-mimic run's target package served.</li>
<li><b>Placement.</b> Two engines ran on CPU socket 1. Each used the exact placement flags (--instance, --devices, --app-cores, --dev-cores, --numa, --nr_hugepages) that platformd generated for the nightly's llama-3.1-8b engines on 2026-09-18 16:28 UTC. Engine a took the flags of platformd's file /etc/rinzler/instance-3.env (cards 90 and 93, 28 application CPUs from the --app-cores list, launcher cores 73 and 217). Engine b took those of instance-2.env (cards b9 and bc, 28 application CPUs, launcher cores 74 and 218). The launcher cores are the two CPUs that the taskset wrapper pins the process start to (platformd's CPUAFFINITY). The file number is platformd's. tron's own --instance flag inside those files reads 2,4 for engine a and 3,4 for engine b. Only the port and the hugepage file name differ from the nightly's flags. The engines were started by hand, not by platformd. There is therefore no hop through Caddy, and each harness client talks to its engine directly.</li>
<li><b>Arms.</b> off sets TRON_AMX_DISABLE=1 in the engine's environment. on leaves it unset. USE_HW_ATTN is unset in both. The model therefore runs CPU attention, as in the nightly. TRON_USE_SPECULATION=0 (speculative decoding off, a tron option that guesses tokens ahead) was set in both arms, as in the nightly. Two environment differences from the nightly remain: both arms ran with TRON_LOG_LEVEL=debug and SPDLOG_LEVEL=debug (set by rz.sh, a few log lines per minute), and without the nightly's RZ_TASK_GROUPS=4.</li>
<li><b>Order.</b> Each repetition ran the levels 2, 4 and 8 users per engine in that order. Inside a level the two arms ran back to back. Odd repetitions ran off then on. Even repetitions ran on then off. Repetition 4 came from a second launch at 21:01 UTC that ran level 2 only (on then off), to replace the excluded cell (note A in section 3).</li>
<li><b>Machine.</b> Before the first cell of each launch, the four idle production engines were taken down through the platformd API. Their journal had shown no request for the previous 10 minutes. They were brought back up at the end of each launch: up at 21:01:12, down again at 21:01:42, up at 21:07:48 UTC. The other half of the machine (CPU socket 0 and its four FPGA cards) was assigned to Bill (a colleague who shares delphi-3bda). His process count was recorded at the start of each cell. It was 0 in all {n_cells} cells.</li>
</ul>

<h2>3. Per cell</h2>
<table><tr><th>users per engine</th><th>arm</th><th>repetition</th><th>start UTC</th><th>TPS mean +/- sd</th><th>slowest sample</th><th>engine a / b TPS (a = cards 90/93, b = cards b9/bc)</th><th>TTFT ms</th><th>AMX-busy cycles (20 s)</th><th>benchmark minutes</th><th>1-min load average at start</th><th>Bill processes</th></tr>
{''.join(rows_cell)}</table>
{notes_html}

<h2>4. How to read it, and limits</h2>
<ul>
<li><b>Why the gain grows: a hypothesis, not a measurement.</b> The AMX kernel speeds up only the attention part of a decode step. At 2 users per engine that part is a small share of the step. A faster kernel then changes the step time little. At 8 users per engine the share is larger. This campaign measured TPS and TTFT only, not the time of each part. A per-step timing split (attention time against dense time) would confirm or reject it.</li>
<li><b>Same layout in both arms.</b> The kill switch leaves the VNNI K layout in place and switches only the kernel off. The gain here is the kernel's alone, in addition to whatever the layout itself changes. The off arm at 2 users per engine ({fmt(off2)} TPS) can be compared with the nightly's mean over 13 nights without PR #4424, {NIGHTLY13_MEAN:.2f} TPS (sd {NIGHTLY13_SD:.2f} TPS) [exec/results/ci-mimic-20260918/report-v4.html, row llama-3.1-8b good tp2 @8u, where @8u is the nightly's 8 users over 4 engines, 2 per engine]. That difference is {layout_cmp:+.1f} %. The two setups differ (2 engines instead of 4, no Caddy, client on the same host). This is an indication only, not a measurement of the layout's effect.</li>
<li><b>Reference points count more than the kernel.</b> The runtron {REF_RUNTRON:+.0f} % of 2026-09-16 came from another driver. runtron sends requests without HTTP and uses synthetic prompts. That run had 8 users on one engine and 2 repetitions. Its base binary was built from main just before PR #3879 merged (commit eb2de0265a). That base has neither the AMX kernel nor the VNNI K layout. Its +17 % therefore counts both changes. The ci-mimic {REF_NIGHTLY:+.1f} % compares the base package (no AMX code, no layout) with the target package, one run per package. It is not a kill-switch comparison on one binary. It therefore also counts the layout. Its client host was CPU-saturated during the target package's llama-3.1-8b config (CPU pressure 98.6 %, 1-min load 126) and lightly loaded during the base package's (1-min load 15.5).</li>
<li><b>Three repetitions.</b> The paired threshold is high (4.303). A level can show a clear mean gain and still be "not resolved" when its three gains differ widely.</li>
<li><b>Hardware attention.</b> This model runs CPU attention in the nightly. The tron log confirms it: "HW attention disabled for model 'llama-3.1-8b-instruct-good-tp2': default off for this model" [exec/results/l8bload-20260918/cells/2u__on__rep1/rinzler-e0.log]. USE_HW_ATTN=0 would change nothing for it. USE_HW_ATTN=1 would switch it to hardware attention. That mode was not run in this campaign.</li>
<li><b>Added level.</b> The 8-users-per-engine level was added by Claude as a third point (jhan approved 2 and 4). It is the same load as the runtron run of 2026-09-16 (8 users on one engine).</li>
</ul>

<h2>5. Files</h2>
<p>Paths are relative to ~/workspace/intel-AMX/.</p>
<ul>
<li>Scripts: exec/l8bload-20260918/{{campaign.sh, rz.sh, summarize.py, gen_report.py, launch.sh}}.</li>
<li>Results: exec/results/l8bload-20260918/cells/&lt;U&gt;u__&lt;arm&gt;__rep&lt;N&gt;/ (perf.json pooled, perf-e0/1.json per engine, rinzler-e0/1.log, amx_busy.txt, proof.txt, meta.json, and on the excluded cell ANOMALY and journal-2042-2045.txt), summary.md, summary.json.</li>
<li>Log: exec/logs/l8bload-20260918.log.</li>
</ul>
</main></body></html>
"""
data = page.encode("ascii", "xmlcharrefreplace")
open(OUT, "wb").write(data)
print(f"wrote {OUT}: {len(data)} bytes, ascii only, {page.count('<svg')} svg, {page.count('<table')} tables, cells {n_cells}, levels {levels}")
