#!/usr/bin/env python3
"""One page for all llama-3.1-8b CI-harness cells: CI-test/status/llama-3.1-8b.html.

Combines the Saturday campaign (2026-09-19, seven cells, exec/results/l8b-levers-20260919/) and the Sunday campaign
(2026-09-20, one cell, exec/results/l8b-8u4k-20260920/). Charts and tables come from the two campaign generators
(exec/l8b-levers-20260919/gen_report.py and exec/l8b-8u4k-20260920/gen_report.py), loaded here as modules, plus two
combined charts written here. Every measured number comes from the two summary.json files (analyze.py of each campaign)
and the pass records. The machine description and the tokenizer facts of section 6 come from the sources named there.
Output is pure ASCII (the artifact publisher mangles non-ASCII bytes). Reviewed 2026-09-20 (workflow wf_b75ceed4-177:
numbers, completeness against the two source pages, plain English); the findings are applied here.
usage: gen_combined.py [OUT_HTML]
"""
import html
import importlib.util
import json
import math
import os
import re
import sys
import time

OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/CI-test/status/llama-3.1-8b.html"
SAT_GEN = "/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/gen_report.py"
SUN_GEN = "/home/jhan/workspace/intel-AMX/exec/l8b-8u4k-20260920/gen_report.py"
CELL_SUN = "llama_3_1_8b_instruct_good_tp2_32u_p4096"
WINDOW_MID = (896 + 1024) // 2
USERS_PER_ENGINE = {4: 1, 8: 2, 16: 4, 32: 8}
C_BLUE, C_BLUE_LIGHT, C_ORANGE, C_AQUA = "#2a78d6", "#86b6ef", "#eb6834", "#1baf7a"
C_INK, C_INK2, C_MUTED, C_GRID, C_AXIS, C_SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def load_module(name, path):
    """Import a campaign generator with an empty argv so its RES/OUT defaults apply."""
    saved = sys.argv
    sys.argv = [saved[0]]
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.argv = saved
    return mod


sat = load_module("sat_gen", SAT_GEN)
sun = load_module("sun_gen", SUN_GEN)
esc, fmt, sfmt, wrap, svg_text_lines, parse_name, label, table = sat.esc, sat.fmt, sat.sfmt, sat.wrap, sat.svg_text_lines, sat.parse_name, sat.label, sat.table


def _wrap_sunday(text, width=105):
    """The Sunday chart subtitle says 'this run'; on this page that is the Sunday cell. Also no semicolons (plain English)."""
    text = (text.replace("3 passes; thin bar", "3 passes. Thin bar").replace("single-pass gain; hollow dot", "single-pass gain. Hollow dot")
            .replace("Saturday measurements; the large blue point at 4096 is this run; the shaded box is its pre-registered band.",
                     "Saturday (2026-09-19) measurements. The large blue point at 4096 is the Sunday (2026-09-20) cell. The shaded box is its pre-registered band."))
    return sat.wrap(text, width)


sun.wrap = _wrap_sunday


def kv_k(n, ovh):
    """K KV tokens per engine step; the server overhead is added only below prompt 4096 (prompts of 4096 are clipped to 4096)."""
    u, p = parse_name(n)
    return USERS_PER_ENGINE[u] * (p + (ovh if p < 4096 else 0) + WINDOW_MID) / 1000


def overhead_below_4096(summary):
    """Server-counted prompt tokens minus prompt_length, mean over the pass records of the cells below prompt 4096
    (the prompt-4096 cells are clipped to exactly 4096 and carry no overhead)."""
    vals = []
    for n, e in summary["configs"].items():
        _, p = parse_name(n)
        if p >= 4096:
            continue
        for pv in e.get("per_pass", {}).values():
            if pv.get("prompt_tokens_mean"):
                vals.append(pv["prompt_tokens_mean"] - p)
    return (sum(vals) / len(vals)) if vals else None


def hh_mm(line):
    m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):\d{2}Z", line)
    return m.group(2) if m else "?"


def upe_label(n):
    """'8 users per engine x prompt 1024' (one convention on the whole page)."""
    u, p = parse_name(n)
    k = USERS_PER_ENGINE[u]
    return f"{k} user{'s' if k > 1 else ''} per engine x prompt {p}"


def yes_no(b):
    return "yes" if b else "no"


# ---------------------------------------------------------------- combined charts
def chart_dumbbell_all(rows):
    """rows: [(name, entry, campaign)] sorted by KV tokens."""
    W, left, right, rowh, top = 960, 340, 210, 46, 100
    Hh = top + rowh * len(rows) + 50
    xmax = max(max(e["base_tps_mean"], e["canon_tps_mean"]) for _, e, _ in rows) * 1.06
    def X(v):
        return left + v / xmax * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="Decode TPS of every cell, nightly deb against canonical-AMX deb" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(svg_text_lines(20, 22, ["Decode TPS per cell: nightly deb (light dot) against canonical-AMX deb (dark dot), all eight cells"], 15, C_INK, "600", 18))
    out.append(svg_text_lines(20, 44, wrap("Mean of 3 passes per cell. Rows sorted by KV tokens per engine step (the attention work of one decode step). The label on each row is the gain of the AMX deb in percent. n.r. = not resolved by the pre-registered rule. Sat = 2026-09-19 campaign, Sun = 2026-09-20 campaign.", 135), 12, C_INK2, "400", 15))
    out.append(f'<circle cx="26" cy="{top - 16}" r="5" fill="{C_BLUE_LIGHT}"/><text x="36" y="{top - 12}" font-size="11" fill="{C_INK2}">nightly deb (no AMX code)</text>')
    out.append(f'<circle cx="216" cy="{top - 16}" r="5" fill="{C_BLUE}"/><text x="226" y="{top - 12}" font-size="11" fill="{C_INK2}">canonical-AMX deb</text>')
    v = 0
    while v <= xmax:
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{Hh - 40}" stroke="{C_GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{Hh - 24}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{v}</text>')
        v += 20
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 6}" font-size="11" fill="{C_MUTED}" text-anchor="middle">tokens per second per user (TPS), mean of the users of a cell</text>')
    for i, (n, e, camp) in enumerate(rows):
        y = top + rowh * i + rowh / 2
        b, c = e["base_tps_mean"], e["canon_tps_mean"]
        xb, xc = X(b), X(c)
        lab = f"{label(n)} ({camp})"
        out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="12" font-weight="{"600" if camp == "Sun" else "400"}" fill="{C_INK}" text-anchor="end">{esc(lab)}</text>')
        out.append(f'<text x="{left - 12}" y="{y + 17}" font-size="10" fill="{C_MUTED}" text-anchor="end">{e["kv_k"]:.1f}K KV tokens per step</text>')
        out.append(f'<line x1="{xb:.1f}" y1="{y:.1f}" x2="{xc:.1f}" y2="{y:.1f}" stroke="{C_BLUE_LIGHT}" stroke-width="3"/>')
        title = f"{lab}: nightly {b:.2f} TPS, canonical AMX {c:.2f} TPS, gain {e['gain_pct']:+.2f} %, paired t {fmt(e['paired_t'])}, {'resolved' if e['resolved'] else 'not resolved'}"
        out.append(f'<circle cx="{xb:.1f}" cy="{y:.1f}" r="7" fill="{C_BLUE_LIGHT}" stroke="{C_SURF}" stroke-width="2"><title>{esc(title)}</title></circle>')
        out.append(f'<circle cx="{xc:.1f}" cy="{y:.1f}" r="7" fill="{C_BLUE}" stroke="{C_SURF}" stroke-width="2"><title>{esc(title)}</title></circle>')
        gain = f"{e['gain_pct']:+.1f} %" + ("" if e["resolved"] else " n.r.")
        if abs(xc - xb) < 44:
            out.append(f'<text x="{max(xb, xc) + 12:.1f}" y="{y + 4}" font-size="12" fill="{C_INK}">{b:.1f} to {c:.1f}, {gain}</text>')
        else:
            lo, hi = (xb, xc) if xb < xc else (xc, xb)
            lo_v, hi_v = (b, c) if xb < xc else (c, b)
            out.append(f'<text x="{lo - 11:.1f}" y="{y + 4}" font-size="11" fill="{C_INK2}" text-anchor="end">{lo_v:.1f}</text>')
            out.append(f'<text x="{hi + 11:.1f}" y="{y + 4}" font-size="11" fill="{C_INK2}">{hi_v:.1f}</text>')
            out.append(f'<text x="{(lo + hi) / 2:.1f}" y="{y - 10}" font-size="12" font-weight="600" fill="{C_INK}" text-anchor="middle">{gain}</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_gain_vs_kv_all(rows):
    """Gain against KV tokens per engine step for all eight cells, three series: users lever (prompt 1024), context lever
    at 2 users per engine, context lever at 8 users per engine. The two prompt-1024 endpoints belong to two series each."""
    W, Hh, left, right, top, bottom = 960, 500, 70, 60, 118, 60
    xs = [e["kv_k"] for _, e, _ in rows]
    gains = [e["gain_pct"] for _, e, _ in rows] + [g for _, e, _ in rows for g in e["gain_pct_per_pass"]]
    xmax = max(xs) * 1.12
    ymin, ymax = min(0, min(gains)) - 1.5, max(gains) + 2.5
    def X(v):
        return left + v / xmax * (W - left - right)
    def Y(v):
        return top + (ymax - v) / (ymax - ymin) * (Hh - top - bottom)
    def series_of(n):
        u, p = parse_name(n)
        upe = USERS_PER_ENGINE[u]
        s = []
        if p == 1024:
            s.append("users")
        if upe == 2:
            s.append("ctx2")
        if upe == 8:
            s.append("ctx8")
        return s
    SERIES = [("users", C_BLUE, "users lever: prompt 1024, 2 to 8 users per engine"),
              ("ctx2", C_ORANGE, "context lever at 2 users per engine: prompt 1024 to 4096"),
              ("ctx8", C_AQUA, "context lever at 8 users per engine: prompt 1024 to 4096")]
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="AMX gain against KV tokens per engine step, all cells" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(f'<text x="20" y="22" font-size="15" font-weight="600" fill="{C_INK}">Gain of the AMX deb against the attention work of one decode step, all eight cells</text>')
    out.append(svg_text_lines(20, 42, wrap("Dot = mean gain over 3 passes. Thin bar = lowest and highest single-pass gain. Hollow dot = not resolved. x = users per engine x (prompt + server overhead below 4096 + 960 generated tokens). A line joins the cells of one lever. The prompt-1024 cells sit on two lines each.", 150), 12, C_INK2, "400", 15))
    gy = math.floor(ymin)
    while gy <= ymax:
        if gy % 2 == 0:
            out.append(f'<line x1="{left}" y1="{Y(gy):.1f}" x2="{W - right}" y2="{Y(gy):.1f}" stroke="{C_GRID if gy else C_AXIS}" stroke-width="1"/>')
            out.append(f'<text x="{left - 8}" y="{Y(gy) + 4:.1f}" font-size="11" fill="{C_MUTED}" text-anchor="end">{gy:+d}</text>')
        gy += 1
    gx = 0
    while gx <= xmax:
        out.append(f'<text x="{X(gx):.1f}" y="{Hh - bottom + 18}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{gx}K</text>')
        gx += 4
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 8}" font-size="11" fill="{C_MUTED}" text-anchor="middle">KV tokens per engine step (thousands), at the middle of the TPS window</text>')
    out.append(f'<text transform="translate(16,{(top + Hh - bottom) / 2:.1f}) rotate(-90)" font-size="11" fill="{C_MUTED}" text-anchor="middle">gain of the AMX deb, percent of the nightly TPS</text>')
    for key, col, _ in SERIES:
        pts = sorted([(e["kv_k"], e["gain_pct"]) for n, e, _ in rows if key in series_of(n)])
        if len(pts) > 1:
            path = " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(g):.1f}" for i, (x, g) in enumerate(pts))
            out.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="1.5" opacity="0.45"/>')
    placed = [(X(e["kv_k"]) - 9, Y(e["gain_pct"]) - 9, X(e["kv_k"]) + 9, Y(e["gain_pct"]) + 9) for _, e, _ in rows]   # the dots themselves
    for n, e, camp in sorted(rows, key=lambda t: t[1]["kv_k"]):
        x, g = X(e["kv_k"]), e["gain_pct"]
        s = series_of(n)
        col = dict((k, c) for k, c, _ in SERIES)[s[-1]]
        lo, hi = min(e["gain_pct_per_pass"]), max(e["gain_pct_per_pass"])
        out.append(f'<line x1="{x:.1f}" y1="{Y(lo):.1f}" x2="{x:.1f}" y2="{Y(hi):.1f}" stroke="{col}" stroke-width="2" opacity="0.6"/>')
        fill = col if e["resolved"] else C_SURF
        title = f"{label(n)} ({camp}): {g:+.2f} % (passes {', '.join(f'{v:+.1f}' for v in e['gain_pct_per_pass'])}), {e['kv_k']:.1f}K KV tokens per step"
        out.append(f'<circle cx="{x:.1f}" cy="{Y(g):.1f}" r="{7 if camp == "Sun" else 6}" fill="{fill}" stroke="{col}" stroke-width="2"><title>{esc(title)}</title></circle>')
        u, p = parse_name(n)
        txt = f"{USERS_PER_ENGINE[u]}u x {p}: {g:+.1f} %"
        tw = 6 * len(txt)
        right_side = [(x + 11, Y(g) - 10), (x + 11, Y(g) + 18), (x + 11, Y(g) + 32), (x + 11, Y(g) - 24)]
        left_side = [(x - 11 - tw, Y(g) - 10), (x - 11 - tw, Y(g) + 18), (x - 11 - tw, Y(g) + 32), (x - 11 - tw, Y(g) - 24)]
        cands = (left_side + right_side) if x + 11 + tw > W - right else (right_side + left_side)
        cands += [(x - tw / 2, Y(g) - 16), (x - tw / 2, Y(g) + 24)]
        for lx_, ly_ in cands:
            box = (lx_ - 2, ly_ - 10, lx_ + tw + 2, ly_ + 3)
            if not any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in placed):
                break
        placed.append(box)
        out.append(f'<text x="{lx_:.1f}" y="{ly_:.1f}" font-size="10" fill="{C_INK2}">{esc(txt)}</text>')
    ly = 84
    for _, col, name in SERIES:
        out.append(f'<circle cx="26" cy="{ly - 4}" r="5" fill="{col}"/><text x="36" y="{ly}" font-size="11" fill="{C_INK2}">{esc(name)}</text>')
        ly += 13
    out.append("</svg>")
    return "\n".join(out)


# ---------------------------------------------------------------- section 9: the proposal to the CI team
def section_proposal(e, e_2048, e_nightly):
    """Draft message to Rhys, the source changes, the binary to use. TPS numbers come from the Sunday summary entry e;
    the +0.2 % of today's row from e_nightly (Saturday, 2 users per engine x prompt 1024). Reviewed 2026-09-20
    (workflow wf_20e43d69-6a0: code facts against systems_test fc27f07 and tron, numbers, plain English)."""
    amx_mean, base_mean = e["canon_tps_mean"], e["base_tps_mean"]
    amx_p05, base_p05 = e["canon_p05_mean"], e["base_p05_mean"]
    amx_min, base_min = e["canon_min_tps"], e["base_min_tps"]
    thr_mean, thr_p05, thr_min = round(amx_mean * 0.95, 1), round(amx_p05 * 0.95, 1), round(amx_min * 0.95, 1)   # proposed: 5 % below the AMX values
    gain = e["gain_pct"]
    pp = e["per_pass"]
    canon_wall = [pp[f"canon-pass{k}"]["wall_s"] for k in (1, 2, 3) if pp.get(f"canon-pass{k}", {}).get("wall_s")]
    base_wall = [pp[f"base-pass{k}"]["wall_s"] for k in (1, 2, 3) if pp.get(f"base-pass{k}", {}).get("wall_s")]
    amx_min_cell = sum(canon_wall) / len(canon_wall) / 60 if canon_wall else 0
    base_min_cell = sum(base_wall) / len(base_wall) / 60 if base_wall else 0
    canon_means = [pp[f"canon-pass{k}"]["tps_mean"] for k in (1, 2, 3) if pp.get(f"canon-pass{k}")]
    spread_tps = max(canon_means) - min(canon_means) if canon_means else 0
    margin_tps = amx_mean - thr_mean
    m_mean, m_p05 = 100 * (thr_mean / base_mean - 1), 100 * (thr_p05 / base_p05 - 1)
    msg = "\n".join([
        "Hi Rhys,",
        "",
        "Proposal: add one perf config to the nightly on delphi-3bda and use it as the AMX metric test. AMX = Intel Advanced Matrix Extensions, CPU matrix instructions. \"The AMX kernel\" below means tron's CPU attention code from PR #3879, which uses those instructions. \"AMX metric test\" means a perf row whose thresholds come from runs with the AMX kernel. A package without the kernel, or a kernel regression, then fails that row.",
        "",
        "The shape: llama-3.1-8b-instruct-good-tp2 at 32 users (8 per engine behind Caddy), prompt length 4096, 1536 generated tokens, the same TPS window as today (generated tokens 896 to 1024), 10 rounds. It is today's llama-8b row with 4x the users and 4x the prompt.",
        "",
        f"Why: today's nightly rows do not detect the AMX kernel. At today's llama-8b row (8 users in total, 2 per engine, prompt 1024) the kernel changes decode speed by {sfmt(e_nightly['gain_pct'], 1)} % (paired t {e_nightly['paired_t']:.1f}, not distinguishable from zero, measured 2026-09-19). At the proposed shape it gains {gain:+.1f} % ({base_mean:.2f} to {amx_mean:.2f} TPS). I measured that on 2026-09-20 with the nightly's own client, engine layout and packages. The two packages ran alternately, three times each (3 pairs of runs). The paired t is {e['paired_t']:.0f} (the mean of the 3 per-pair TPS differences divided by their standard error, far above the 4.303 that settles the direction).",
        "",
        f"Cost: one config run of about {amx_min_cell:.0f} min per night with the kernel (about {base_min_cell:.0f} min on a package without AMX code). No extra provisioning when the new dict sits directly after the existing llama-8b entry (same model, inventory.py skips a re-provision). Placed elsewhere it costs one provisioning (58 s in the Saturday check cell).",
        "",
        "Measured values at this shape:",
        f"- With the kernel: {amx_mean:.2f} TPS mean, {amx_p05:.2f} p05, {amx_min:.2f} slowest sample.",
        f"- Without it: {base_mean:.2f} mean, {base_p05:.2f} p05, {base_min:.2f} slowest sample.",
        f"- Proposed initial thresholds, 5 % below the AMX values: in the YAML average_tps {thr_mean} and p05_tps {thr_p05}. In get_goal (the enforced check today) tps {thr_mean} and min_tps {thr_min} (raw slowest sample). That is {m_mean:+.0f} % above the no-AMX mean and {m_p05:+.0f} % above the no-AMX p05.",
        "- The ratchet can raise them later.",
        "",
        "What the change needs (details and code in section 9.2 of the page linked below):",
        "1. A new entry in scripts/perf.py configs.",
        "2. The prompt-source change in testlib/prompt.py: a 4096-token prompt needs the next conversations in the ShareGPT list (seed + 1, seed + 2, ...) joined to the seed's own conversation. Without that, prune_convo raises for most seeds. The patch is in the page.",
        "3. Thresholds for granite_rapids_72_rinzler at users 32: in the CURRENT THRESHOLD COMPATIBILITY BLOCK of scripts/system_ci.py (get_goal) and in thresholds/system_ci_perf.yaml.",
        "4. Your decision: the configs list is not gated by platform. The genoa nightly would therefore run the same config. Either gate it to granite or add genoa thresholds.",
        "",
        "The binary:",
        "- tron's .deb preset does not compile the AMX kernel yet.",
        "- The fix is commit 6f37cd2ed9 on branch jhan-amx-deb-preset (one added option line in CMakePresets.json, TRON_AMX_DISPATCH=ON in the deb preset). It is not in main, and no PR is open yet.",
        f"- Until it is merged the nightly deb has no AMX code, and the row would record the no-AMX values (about {base_mean:.1f} TPS).",
        "- For a test before the merge use the deb built with the change, on delphi-3bda at /var/tmp/jhan/canon-ci-20260918/target.deb (tron 2026.09.18-0594dc54-jhan-ci-canon = main 3faba6d0fd + that commit). Section 9.3 of the page has the install and check commands.",
        "",
        "Pages: CI-test/status/llama-3.1-8b.html (all eight cells), CI-test/status/llama-3.1-8b-8u-4k.html (the shape's campaign), PR3879/new-PRs/PR1/CI-AMX-test-shapes.html (the recommendation page).",
        "",
        "Thanks,",
        "jhan",
    ])
    perf_entry = """    {   # place it directly after the existing llama_3_1_8b_instruct_good_tp2 entry: same model, no re-provisioning
        "name": "llama_3_1_8b_instruct_good_tp2_32u_p4096",
        "model": "llama-3.1-8b-instruct-good-tp2",
        "nominal_users": 32,
        "shared_prompt_length": 0,
        "prompt_length": 4096,
        "generate_length": 1536,
        "start_capture": 896,
        "end_capture": 1024,
        "prompt_mode": "sharegpt",
    },"""
    goal_entry = f"""        # in get_goal(), platform_type granite_rapids_72_rinzler
        goal.tps[('llama-3.1-8b-instruct-good-tp2', 32)] = {thr_mean}       # AMX metric row, proposed: 5 % below the measured AMX mean {amx_mean:.2f}
        goal.min_tps[('llama-3.1-8b-instruct-good-tp2', 32)] = {thr_min}   # raw slowest sample, 5 % below the measured AMX value {amx_min:.2f}"""
    yaml_entry = f"""  - platform_type: granite_rapids_72_rinzler
    model: llama-3.1-8b-instruct-good-tp2
    users: 32
    average_tps:
      threshold: {thr_mean}
      update_policy: q30
    p05_tps:
      threshold: {thr_p05}
      update_policy: q30"""
    install = """# on delphi-3bda, outside the nightly window (the lease file /run/lock/systems-test-ci.lease must be absent or not busy)
sudo apt-get remove -y tron
sudo apt-get install -y --allow-downgrades /var/tmp/jhan/canon-ci-20260918/target.deb
dpkg-query -W -f='${Version}\\n' tron          # expect 2026.09.18-0594dc54-jhan-ci-canon
objdump -d --no-show-raw-insn /opt/positron/bin/rinzler | grep -c -E '\\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\\b'   # AMX tile instructions: 86 (the nightly deb gives 0)
# apt never restarts engines: restart them (POST platformd /api/inference/down, then POST /api/inference/up, then wait until
# platformd reports idle, as exec/l8b-8u4k-20260920/dut.sh serving-down and serving-up do), then run the config.
# The no-AMX arm on the same binary: TRON_AMX_DISABLE=1 in the engine environment (the kill switch).
# Proof that AMX ran: sudo perf stat -e cpu/event=0xb7,umask=0x02,name=amx_busy/ -p <rinzler pids> -- sleep 20 (billions of cycles under load; 0 without the kernel).
# Restore afterwards: sudo apt-get install -y --allow-downgrades tron=2026.09.18-3faba6d0 (or the current nightly version), then restart the engines again."""
    rows = [
        ["TPS mean", fmt(amx_mean), fmt(base_mean), f"{thr_mean}", f"{100 * (thr_mean / amx_mean - 1):+.1f} % / {100 * (thr_mean / base_mean - 1):+.1f} %"],
        ["p05 TPS", fmt(amx_p05), fmt(base_p05), f"{thr_p05}", f"{100 * (thr_p05 / amx_p05 - 1):+.1f} % / {100 * (thr_p05 / base_p05 - 1):+.1f} %"],
        ["slowest sample TPS", fmt(amx_min), fmt(base_min), f"{thr_min}", f"{100 * (thr_min / amx_min - 1):+.1f} % / {100 * (thr_min / base_min - 1):+.1f} %"],
    ]
    out = ['<h2 id="s9">9. Proposal to the CI team: add the shape as the AMX metric test</h2>']
    out.append("<p>jhan decided on 2026-09-20 to propose the 32-user (8 per engine) prompt-4096 shape to the CI team. This section holds the draft message, the source changes the shape needs, and the binary to test with while the tron package still lacks the AMX kernel. The TPS numbers below come from the Sunday cell of section 2. The " + esc(sfmt(e_nightly['gain_pct'], 1)) + " % figure comes from the Saturday cell at 2 users per engine, prompt 1024. The workflow, package and prompt numbers name their own sources where they appear.</p>")
    out.append("<h3>9.1 Draft message to Rhys (ready to paste)</h3>")
    out.append(f"<pre>{esc(msg)}</pre>")
    out.append("<h3>9.2 Source changes in systems_test</h3>")
    out.append("<p>The repository is positron-ai/systems_test. The nightly runs it from its own checkout on the self-hosted GitHub runner labelled system-ci (the runs-on line of the workflow file). The four changes below were read from the checkout at commit fc27f07 (2026-09-17, the merge of PR #216). Words used in this table: get_goal = the function in scripts/system_ci.py that returns today's enforced goals. CURRENT THRESHOLD COMPATIBILITY BLOCK = the code region that holds it (report label CURRENT THRESHOLDS). Comparison mode = the YAML thresholds are checked and reported, but their verdict does not change the CI exit status. Q30 ratchet = the rule that proposes raising a threshold towards the 30th percentile of the last 14 valid results, and never lowers it (docs/system_ci_ratchet.md). genoa = the same workflow on the genoa96_rinzler platform type, whose CPU has no AMX.</p>")
    out.append(table(["file", "change", "why"], [
        ["scripts/perf.py", "add one dict to the <code>configs</code> list (code below). The results are keyed by (model, nominal_users). The new row is therefore (llama-3.1-8b-instruct-good-tp2, 32).", "the list is the nightly's perf phase. Every entry runs on every platform (no platform gate exists in the file)."],
        ["testlib/prompt.py", "apply exec/l8b-levers-20260919/prompt.py.patch. PromptGenerator.generate copies the stored conversation list and joins the next conversations in the ShareGPT list (seed + 1, seed + 2, ...) until the token count reaches prompt_length, then prunes as before. A new helper _token_count counts tokens the way prune_convo does.", "most ShareGPT conversations are shorter than 4096 tokens (median 2045 tokens, measured 2026-09-19 with the llama-8b tokenizer over the 1000 stored conversations). prune_convo therefore raises for most seeds at prompt 4096. At prompt 1024 the loop never runs, and the existing rows are unchanged (verified: 1920 prompts, prompt-1024 output identical to the previous code)."],
        ["scripts/system_ci.py", "in get_goal(), add the (model, 32) keys to goal.tps and goal.min_tps of the granite_rapids_72_rinzler block (code below).", "the CURRENT THRESHOLD COMPATIBILITY BLOCK decides the CI verdict today (docs/system_ci_ratchet.md). A row without a goal has no verdict."],
        ["thresholds/system_ci_perf.yaml", "add one entry for platform_type granite_rapids_72_rinzler, model llama-3.1-8b-instruct-good-tp2, users 32 with average_tps and p05_tps thresholds (code below).", "the YAML thresholds run in comparison mode and supply the history of the Q30 ratchet."],
        ["(decision) platform gating", "either add a platform filter to the configs (for example a <code>platforms</code> key checked in test_performance) or add genoa96_rinzler entries for users 32 to both threshold places.", "the genoa nightly runs the same configs list (about 14 min more per night there, no AMX). Without a gate or genoa thresholds the row is absent from the enforced CURRENT report, appears in the YAML comparison report as a memo line, and marks the genoa YAML report incomplete every night (perf_warnings: performance threshold unavailable for genoa96_rinzler)."],
    ], cls=""))
    out.append("<p>Code for scripts/perf.py, the new entry. The existing 8-user entry stays.</p><pre>" + esc(perf_entry) + "</pre>")
    out.append("<p>Code for scripts/system_ci.py, get_goal, granite block. The proposed values are explained in 9.4.</p><pre>" + esc(goal_entry) + "</pre>")
    out.append("<p>Entry for thresholds/system_ci_perf.yaml (schema_version 2):</p><pre>" + esc(yaml_entry) + "</pre>")
    out.append("<p>Cost per night: one config run of " + esc(f"{amx_min_cell:.1f}") + " min with the AMX kernel (" + esc(f"{base_min_cell:.1f}") + " min without it), the wall time of the 10 rounds, mean of the three Sunday passes of each arm. Per AMX pass the wall time was " + esc(", ".join(f"{pp[f'canon-pass{k}'].get('wall_s', 0) / 60:.1f}" for k in (1, 2, 3))) + " min. The driver's total per pass, with provisioning, the AMX probe and its own waits, was 11.1 min (perf_minutes in the pass records). No extra provisioning when the new dict sits directly after the existing llama-8b entry (same model, inventory.py skips a re-provision and only runs a health check). The granite workflow starts at 03:30 UTC (its cron line) and has a job timeout of 660 min (11 h). The 2026-09-20 nightly (GitHub run 35487126137) started 03:39 UTC and ended 13:08 UTC, 9 h 29 min of the 11 h. The extra config run of 11 to 14 min fits.</p>")
    out.append("<h3>9.3 The binary to test with while CMakePresets.json is not merged</h3>")
    out.append("<ul>"
               "<li>The tron package the nightly installs is built with the deb preset of CMakePresets.json. That preset does not set TRON_AMX_DISPATCH=ON. The packaged rinzler therefore has no AMX code: objdump (the GNU disassembler) counts 0 AMX tile instructions in it (tdpbf16ps, tileloadd and the like, instructions only AMX code contains). This was checked on every nightly deb of these campaigns.</li>"
               "<li>The fix is commit 6f37cd2ed9 (CMakePresets: compile the AMX attention kernels into the .deb package, one added option line) on branch jhan-amx-deb-preset in positron-ai/tron. Checked 2026-09-20: not in main (main head 98bb8cb22f), no pull request opened yet.</li>"
               "<li>Until it is merged, a test of the new row on the nightly deb records the no-AMX values (about " + esc(f"{base_mean:.1f}") + " TPS). The AMX thresholds would fail. The test must use a deb built with the change.</li>"
               "<li>Such a deb exists on delphi-3bda: /var/tmp/jhan/canon-ci-20260918/target.deb = tron_2026.09.18-0594dc54-jhan-ci-canon_amd64.deb, built from main 3faba6d0fd plus commit 6f37cd2ed9. Its manifest (/var/tmp/jhan/canon-ci-20260918/manifest.json) records 86 AMX tile instructions, the kill-switch literal (the string TRON_AMX_DISABLE inside the binary) present, and PR #4424 not included. Both campaigns of this page used it as the AMX arm. Alternative: build from branch jhan-amx-deb-preset with <code>make deb</code>.</li>"
               "</ul>")
    out.append("<p>Install, check and restore commands (run on delphi-3bda):</p><pre>" + esc(install) + "</pre>")
    out.append("<h3>9.4 Threshold numbers</h3>")
    out.append(table(["metric", "with the AMX kernel (Sunday, 3 passes)", "without it (Sunday, 3 passes)", "proposed initial threshold", "margin against AMX / against no-AMX"], rows))
    out.append("<p>The proposed thresholds sit 5 % below the AMX values. The three AMX passes of the Sunday cell spread by " + esc(f"{spread_tps:.2f}") + " TPS (" + esc(f"{100 * spread_tps / amx_mean:.1f}") + " %, means " + esc(", ".join(f"{v:.2f}" for v in canon_means)) + "). The 5 % margin (" + esc(f"{margin_tps:.1f}") + " TPS) is about " + esc(f"{margin_tps / spread_tps:.0f}" if spread_tps else "n/a") + " times that spread. Day-to-day drift is not measured yet. The nightly's history will show it, and the ratchet raises the thresholds when the history supports it. Alternative for the first nights: the placeholder 1.00 TPS in get_goal only (tps and min_tps), as ingested-gemma-4-31b-it-tp2 uses today with no YAML entry. A placeholder row cannot fail. After 14 valid nightly results someone sets the real values by hand (docs/system_ci_ratchet.md: Q30 of the clipped history divided by 1.04) and adds the YAML entry. The 5 % margin proposed here is wider than that rule by about 1 point.</p>")
    return "\n".join(out)


# ---------------------------------------------------------------- section 10: prefill (time to first token)
T_LIMIT = {3: 4.303, 2: 12.706}


def _paired_t(d):
    n = len(d)
    if n < 2:
        return None
    m = sum(d) / n
    s = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    if s == 0:
        return math.inf if m != 0 else 0.0
    return m / (s / math.sqrt(n))


def prefill_stats(passes_by_campaign):
    """passes_by_campaign: {campaign: {tag: perf.json record}}. Per cell and pass-run: the harness prefill rate (results[].prefill_mean
    = configured prompt_length / rounded mean TTFT), the per-request rate as a ratio of sums (sum of server-counted prompt tokens /
    sum of TTFT), the uncached rate (sum of prompt tokens minus cached tokens / sum of TTFT), the cached share, TTFT mean and
    extremes. Per cell: means over the pass pairs, gains, paired t and the resolved flag for the harness and the uncached rate.
    Reviewed 2026-09-20 (workflow wf_f11e32ce-e1e); the findings are applied here."""
    cells = {}
    for camp, passes in passes_by_campaign.items():
        for tag, rec in passes.items():
            res_by_name = {d["name"]: d for d in rec.get("results", []) if d.get("tps_results")}
            for raw in rec.get("raw", []):
                n = raw.get("name")
                tt, pt, ct = raw.get("ttfts_ms") or [], raw.get("prompt_tokens") or [], raw.get("cached_tokens") or []
                if not n or not tt or len(tt) != len(pt) or len(ct) != len(pt):
                    continue
                d = res_by_name.get(n, {})
                ttft_mean = d.get("ttft_mean") or round(sum(tt) / len(tt))
                plen = raw.get("prompt_length") or 0
                harness = d.get("prefill_mean") or (plen / (ttft_mean / 1000) if ttft_mean else 0)
                secs = sum(tt) / 1000.0
                cells.setdefault(n, {"campaign": camp, "per_pass": {}})
                cells[n]["per_pass"][tag] = {"ttft_mean": ttft_mean, "ttft_min": min(tt), "ttft_max": max(tt), "prompt_length": plen,
                                             "prompt_tokens_mean": sum(pt) / len(pt), "cached_pct": (100.0 * sum(ct) / sum(pt)) if sum(pt) else 0.0,
                                             "harness": harness, "req_rate": sum(pt) / secs, "unc_rate": (sum(pt) - sum(ct)) / secs, "n": len(tt)}
    for n, c in cells.items():
        pp = c["per_pass"]
        ks = sorted({int(t.split("pass")[1]) for t in pp})
        pairs = [k for k in ks if f"base-pass{k}" in pp and f"canon-pass{k}" in pp]
        c["n_pairs"] = len(pairs)
        if not pairs:
            continue
        lim = T_LIMIT.get(len(pairs))
        for key in ("harness", "unc_rate"):
            b = [pp[f"base-pass{k}"][key] for k in pairs]
            cc = [pp[f"canon-pass{k}"][key] for k in pairs]
            gain = 100.0 * ((sum(cc) / len(cc)) / (sum(b) / len(b)) - 1.0)
            t = _paired_t([ci - bi for bi, ci in zip(b, cc)])
            c[f"{key}_gain_pct"] = gain
            c[f"{key}_gain_per_pass"] = [100.0 * (ci / bi - 1.0) for bi, ci in zip(b, cc)]
            c[f"{key}_t"] = t
            c[f"{key}_resolved"] = bool(t is not None and lim is not None and abs(t) >= lim and abs(gain) >= 1.0)
        c["gain_pct"], c["paired_t"], c["resolved"] = c["harness_gain_pct"], c["harness_t"], c["harness_resolved"]
        for key in ("ttft_mean", "cached_pct", "harness", "req_rate", "unc_rate", "prompt_tokens_mean"):
            c[f"base_{key}"] = sum(pp[f"base-pass{k}"][key] for k in pairs) / len(pairs)
            c[f"canon_{key}"] = sum(pp[f"canon-pass{k}"][key] for k in pairs) / len(pairs)
        for arm in ("base", "canon"):
            c[f"{arm}_ttft_min"] = min(pp[f"{arm}-pass{k}"]["ttft_min"] for k in pairs)
            c[f"{arm}_ttft_max"] = max(pp[f"{arm}-pass{k}"]["ttft_max"] for k in pairs)
        c["cached_diff_per_pass"] = [pp[f"canon-pass{k}"]["cached_pct"] - pp[f"base-pass{k}"]["cached_pct"] for k in pairs]
        c["ttft_gain_pct"] = 100.0 * (1.0 - c["canon_ttft_mean"] / c["base_ttft_mean"])
    return cells


def chart_dumbbell_prefill(rows):
    """rows: [(name, entry, campaign)] with base_harness / canon_harness / gain_pct / paired_t / resolved / kv_k, sorted by kv."""
    W, left, right, rowh, top = 960, 340, 210, 46, 100
    Hh = top + rowh * len(rows) + 50
    xmax = max(max(e["base_harness"], e["canon_harness"]) for _, e, _ in rows) * 1.06
    step = 200 if xmax > 1000 else 50
    def X(v):
        return left + v / xmax * (W - left - right)
    out = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" role="img" aria-label="Prefill rate of every cell, nightly deb against canonical-AMX deb" style="max-width:{W}px;font-family:system-ui,sans-serif">']
    out.append(svg_text_lines(20, 22, ["Prefill rate per cell: nightly deb (light dot) against canonical-AMX deb (dark dot), all eight cells"], 15, C_INK, "600", 18))
    out.append(svg_text_lines(20, 44, wrap("Prefill rate = prompt tokens per second of time to first token, the harness's own metric: prompt length divided by the mean time to first token of the cell, mean of 3 passes. The label on each row is the AMX gain in percent. n.r. = not resolved. Rows sorted by KV tokens per engine step. The rate of a cell with more users per engine includes waiting behind the other users' prompts (section 10).", 135), 12, C_INK2, "400", 15))
    out.append(f'<circle cx="26" cy="{top - 16}" r="5" fill="{C_BLUE_LIGHT}"/><text x="36" y="{top - 12}" font-size="11" fill="{C_INK2}">nightly deb (no AMX code)</text>')
    out.append(f'<circle cx="216" cy="{top - 16}" r="5" fill="{C_BLUE}"/><text x="226" y="{top - 12}" font-size="11" fill="{C_INK2}">canonical-AMX deb</text>')
    v = 0
    while v <= xmax:
        x = X(v)
        out.append(f'<line x1="{x:.1f}" y1="{top - 4}" x2="{x:.1f}" y2="{Hh - 40}" stroke="{C_GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{Hh - 24}" font-size="11" fill="{C_MUTED}" text-anchor="middle">{v}</text>')
        v += step
    out.append(f'<text x="{(left + W - right) / 2:.1f}" y="{Hh - 6}" font-size="11" fill="{C_MUTED}" text-anchor="middle">prefill rate, prompt tokens per second of TTFT (harness metric)</text>')
    for i, (n, e, camp) in enumerate(rows):
        y = top + rowh * i + rowh / 2
        b, c = e["base_harness"], e["canon_harness"]
        xb, xc = X(b), X(c)
        lab = f"{label(n)} ({camp})"
        out.append(f'<text x="{left - 12}" y="{y + 4}" font-size="12" font-weight="{"600" if camp == "Sun" else "400"}" fill="{C_INK}" text-anchor="end">{esc(lab)}</text>')
        out.append(f'<text x="{left - 12}" y="{y + 17}" font-size="10" fill="{C_MUTED}" text-anchor="end">TTFT {e["base_ttft_mean"]:.0f} / {e["canon_ttft_mean"]:.0f} ms</text>')
        out.append(f'<line x1="{xb:.1f}" y1="{y:.1f}" x2="{xc:.1f}" y2="{y:.1f}" stroke="{C_BLUE_LIGHT}" stroke-width="3"/>')
        title = f"{lab}: nightly {b:.0f} tok/s, canonical AMX {c:.0f} tok/s, gain {e['gain_pct']:+.1f} %, paired t {fmt(e['paired_t'], 1)}, {'resolved' if e['resolved'] else 'not resolved'}"
        out.append(f'<circle cx="{xb:.1f}" cy="{y:.1f}" r="7" fill="{C_BLUE_LIGHT}" stroke="{C_SURF}" stroke-width="2"><title>{esc(title)}</title></circle>')
        out.append(f'<circle cx="{xc:.1f}" cy="{y:.1f}" r="7" fill="{C_BLUE}" stroke="{C_SURF}" stroke-width="2"><title>{esc(title)}</title></circle>')
        gain = f"{e['gain_pct']:+.1f} %" + ("" if e["resolved"] else " n.r.")
        if abs(xc - xb) < 44:
            out.append(f'<text x="{max(xb, xc) + 12:.1f}" y="{y + 4}" font-size="12" fill="{C_INK}">{b:.0f} to {c:.0f}, {gain}</text>')
        else:
            lo, hi = (xb, xc) if xb < xc else (xc, xb)
            lo_v, hi_v = (b, c) if xb < xc else (c, b)
            out.append(f'<text x="{lo - 11:.1f}" y="{y + 4}" font-size="11" fill="{C_INK2}" text-anchor="end">{lo_v:.0f}</text>')
            out.append(f'<text x="{hi + 11:.1f}" y="{y + 4}" font-size="11" fill="{C_INK2}">{hi_v:.0f}</text>')
            out.append(f'<text x="{(lo + hi) / 2:.1f}" y="{y - 10}" font-size="12" font-weight="600" fill="{C_INK}" text-anchor="middle">{gain}</text>')
    out.append("</svg>")
    return "\n".join(out)


def section_prefill(pf, rows_kv):
    """pf = prefill_stats(); rows_kv = the decode rows [(name, entry, camp)] for the KV order and decode gains."""
    order = [(n, e["kv_k"], camp, e) for n, e, camp in rows_kv]
    prows = [(n, dict(pf[n], kv_k=kv), camp) for n, kv, camp, _ in order if n in pf and pf[n].get("n_pairs")]
    decode = {n: e for n, _, _, e in order}
    N2U1024 = "llama_3_1_8b_instruct_good_tp2_8u_p1024"
    sat_cached = {n: e for n, e, camp in prows if camp == "Sat"}
    sat_ctx = [e["base_cached_pct"] for n, e in sat_cached.items() if parse_name(n)[1] > 1024]
    sat_users = {n: e["base_cached_pct"] for n, e in sat_cached.items() if parse_name(n)[1] == 1024 and n != N2U1024}
    cached_diff_max = max((abs(v) for e in pf.values() if e.get("n_pairs") for v in [e["canon_cached_pct"] - e["base_cached_pct"]]), default=0)
    out = ['<h2 id="s10">10. Prefill: time to first token and the prefill rate</h2>']
    out.append("<p>Words used here. TTFT = time to first token: the time from sending a request to receiving its first generated token, in ms, measured by the harness per request. Prefill = the server's processing of the prompt before the first token. Prefill rate = the harness's own metric, the configured prompt length in tokens divided by the rounded mean TTFT of the cell, in tokens per second (the prefill_mean field that scripts/perf.py computes). Per-request rate = the sum of the server-counted prompt tokens of all requests of a pass-run divided by the sum of their TTFT, in tokens per second (a ratio of sums, so every request weighs by its own duration). Uncached rate = the same ratio with the prefix-cache hits subtracted from the token sum (only the tokens the server had to compute). Cached tokens = prompt tokens the prefix cache served, reported by the server per request. Pass record = the perf.json file the driver writes for each pass-run (section 11).</p>")
    out.append("<p>Derived, not measured: no prefill rate on this page or in the nightly is a direct measurement. The harness times TTFT on the client and divides the configured prompt length by the mean TTFT (scripts/perf.py, line 383). The nightly's Slack line prints that value with an approximation sign, for example prefill 1.5k tok/s for the llama-8b row at TTFT 664 ms (1024 tokens / 0.664 s = 1542 tokens per second), and its footnote reads: prefill is derived from prompt_length / TTFT, a client-side approximation of prefill throughput. No server-side prefill timing exists in the harness. The per-request and uncached rates below are the same kind of division, done with the server-counted tokens of every request.</p>")
    out.append("<p>The pass records hold the inputs: every request's TTFT, server-counted prompt tokens and cached tokens, and the harness's prefill rate per cell (the value the nightly posts as prefill in its Slack message). The table and chart below use them for all eight cells. Three facts limit what a rate means:</p><ul>"
               "<li>TTFT of one request includes waiting. The harness starts the users of a round 0.1 s apart (STAGGER_DELAY, the harness constant for that gap). With 8 users per engine a request's TTFT therefore includes the prefill of the other users' prompts. The engine handles those prompts first or at the same time. The per-request rate at 8 users per engine is therefore far below the rate at 2 users per engine for the same prompt length. It measures what one user experiences, not the engine's prefill throughput.</li>"
               + esc(f"Cached prefixes shorten the prefill. Every Saturday cell except 2 users per engine x prompt 1024 ({sat_cached[N2U1024]['base_cached_pct']:.1f} % cached) reused prompt text an earlier cell had sent. The longer prompts of a seed repeat the shorter prompt sent minutes earlier (2 users per engine at prompt 2048 to 4096: {min(sat_ctx):.0f} to {max(sat_ctx):.0f} % of the tokens cached). The cells with more users repeat the same prompts at the same length (4 and 8 users per engine at prompt 1024: {', '.join(f'{v:.1f}' for v in sat_users.values())} % cached, and about one third of their requests were served fully from the cache, with a cached token count equal to the prompt token count and a TTFT of 45 to 900 ms, median about 80 ms). The Sunday cell had no earlier cell with the same seeds ({pf[CELL_SUN]['base_cached_pct']:.1f} % cached). The uncached rate removes the cached tokens from the token sum.").join(["<li>", "</li>"])
               + esc(f"The cached share differs between the two arms. rinzler serves a prefix only when Caddy routes the request to the engine that holds it. The share therefore depends on the routing of each pass-run. The largest difference between the arms of one cell is {cached_diff_max:.1f} percentage points (mean of 3 passes). The table therefore gives the share per arm, and the uncached gain corrects the comparison.").join(["<li>", "</li>"]) + "</ul>")
    out.append('<div class="fig">' + chart_dumbbell_prefill(prows) + '<p class="cap">Figure 6. The harness\'s prefill rate per cell, nightly deb against canonical-AMX deb, mean of 3 passes. The small line under each label is the mean TTFT of the two arms.</p></div>')
    trows = []
    for n, e, camp in prows:
        trows.append([esc(label(n)), camp, f"{fmt(e['base_ttft_mean'], 0)} / {fmt(e['canon_ttft_mean'], 0)}", f"{fmt(e['base_ttft_min'], 0)} to {fmt(e['base_ttft_max'], 0)} / {fmt(e['canon_ttft_min'], 0)} to {fmt(e['canon_ttft_max'], 0)}",
                      f"{fmt(e['base_cached_pct'], 1)} / {fmt(e['canon_cached_pct'], 1)}", f"{fmt(e['base_harness'], 0)} / {fmt(e['canon_harness'], 0)}", f"<b>{sfmt(e['gain_pct'], 1)}</b>", fmt(e["paired_t"], 1), "yes" if e["resolved"] else "no",
                      f"{fmt(e['base_req_rate'], 0)} / {fmt(e['canon_req_rate'], 0)}", f"{fmt(e['base_unc_rate'], 0)} / {fmt(e['canon_unc_rate'], 0)}", f"{sfmt(e['unc_rate_gain_pct'], 1)} (t {fmt(e['unc_rate_t'], 1)}, {'yes' if e['unc_rate_resolved'] else 'no'})", sfmt(decode[n]["gain_pct"], 1)])
    out.append(table(["cell", "campaign", "TTFT ms mean nightly / AMX", "TTFT ms lowest to highest request nightly / AMX", "cached tokens % nightly / AMX", "harness prefill rate tok/s nightly / AMX", "harness gain %", "paired t", "resolved", "per-request rate tok/s nightly / AMX", "uncached rate tok/s nightly / AMX", "uncached gain % (t, resolved)", "decode gain % (section 2)"], trows))
    out.append('<p class="cap">Means over the 3 pass pairs of each cell. Lowest and highest request = over all requests of the 3 passes of that arm. The paired t and the resolved rule (|t| >= 4.303 and |gain| >= 1 %) are the same as for decode, applied to the harness rate and to the uncached rate.</p>')
    # reading
    best = sorted(prows, key=lambda t: -t[1]["gain_pct"])
    sun = pf.get(CELL_SUN)
    s2u4096 = pf.get("llama_3_1_8b_instruct_good_tp2_8u_p4096", {})
    s2u1024 = pf.get(N2U1024, {})
    s8u1024 = pf.get("llama_3_1_8b_instruct_good_tp2_32u_p1024", {})
    s8u2048 = pf.get("llama_3_1_8b_instruct_good_tp2_32u_p2048", {})

    def rs(e_):
        if e_["resolved"]:
            return "resolved"
        pp_ = ", ".join(f"{v:+.1f}" for v in e_["harness_gain_per_pass"])
        cd = ", ".join(f"{v:+.1f}" for v in e_["cached_diff_per_pass"])
        unc = f"on uncached tokens {sfmt(e_['unc_rate_gain_pct'], 1)} %, t {fmt(e_['unc_rate_t'], 1)}, {'resolved' if e_['unc_rate_resolved'] else 'not resolved'}"
        return f"not resolved on the harness rate: per-pass gains {pp_} %, cached share AMX minus nightly {cd} points, {unc}"
    out.append("<h3>Reading</h3><ul>")
    if sun:
        out.append(f"<li>At the proposed shape (8 users per engine x prompt 4096) the AMX deb raises the prefill rate by {sfmt(sun['gain_pct'], 1)} % ({fmt(sun['base_harness'], 0)} to {fmt(sun['canon_harness'], 0)} tokens per second of TTFT, {rs(sun)}). TTFT falls from {fmt(sun['base_ttft_mean'] / 1000, 1)} s to {fmt(sun['canon_ttft_mean'] / 1000, 1)} s ({sfmt(-sun['ttft_gain_pct'], 1)} %). The decode gain at the same cell is {sfmt(decode[CELL_SUN]['gain_pct'], 1)} %. The kernel therefore helps prefill more than decode at this shape.</li>")
    out.append(f"<li>Largest harness gains: {esc(label(best[0][0]))} {sfmt(best[0][1]['gain_pct'], 1)} % ({rs(best[0][1])}) and {esc(label(best[1][0]))} {sfmt(best[1][1]['gain_pct'], 1)} % ({rs(best[1][1])}). Smallest: {esc(label(best[-1][0]))} {sfmt(best[-1][1]['gain_pct'], 1)} % ({rs(best[-1][1])}).</li>")
    if s2u1024 and s2u4096:
        out.append(f"<li>Context lever at 2 users per engine: the harness gain grows with the prompt, {sfmt(s2u1024.get('gain_pct'), 1)} % at 1024 and {sfmt(s2u4096.get('gain_pct'), 1)} % at 4096 ({rs(s2u4096)}). Hypothesis: attention is a larger share of the prefill work at longer prompts. A profile of one prefill at 1024 and at 4096 tokens (attention time over total) would confirm it.</li>")
    if s8u1024 and s8u2048 and sun:
        out.append(f"<li>Users lever and both levers together: at 8 users per engine the harness gain is {sfmt(s8u1024.get('gain_pct'), 1)} % at prompt 1024 ({rs(s8u1024)}), {sfmt(s8u2048.get('gain_pct'), 1)} % at 2048 ({rs(s8u2048)}) and {sfmt(sun['gain_pct'], 1)} % at 4096 ({rs(sun)}).</li>")
    out.append("<li>Absolute rates are not comparable across user counts. At 8 users per engine a request waits behind up to 7 other prompts. Its TTFT and rate therefore describe the queue, not the engine. Within one cell the two arms saw the same queue. The gain is therefore a fair comparison.</li>")
    out.append("<li>TTFT also contains the wait behind other users' prompts, the network round trip and the first decode step. No rate on this page is the engine's prefill throughput. The uncached rate removes the cached tokens from the token sum and nothing else.</li>")
    out.append("</ul>")
    return "\n".join(out), prows


# ---------------------------------------------------------------- page
def build():
    sat_summary, sat_passes, sat_checks, sat_outcome, sat_hist, sat_pc = sat.load()
    sun_summary, sun_passes, sun_outcome, sun_hist, sun_pc, sun_compare, sun_base_id = sun.load()
    ovh = overhead_below_4096(sat_summary)
    rows = []
    for n, e in sat_summary["configs"].items():
        if e.get("n_pairs"):
            e = dict(e); e["kv_k"] = kv_k(n, ovh); rows.append((n, e, "Sat"))
    e_sun = dict(sun_summary["configs"][CELL_SUN]); e_sun["kv_k"] = kv_k(CELL_SUN, ovh); rows.append((CELL_SUN, e_sun, "Sun"))
    rows.sort(key=lambda t: t[1]["kv_k"])
    merged = {"configs": {n: e for n, e, _ in rows}}
    best = sorted(rows, key=lambda t: -t[1]["gain_pct"])[:2]
    v_sat, v_sun = sat_summary["verdicts"], sun_summary["verdicts"]
    cell = v_sun["cell"]
    goals = cell.get("candidate_goal_values_clean") or {}
    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    n_res = sum(1 for _, e, _ in rows if e["resolved"])

    def g(n):
        return merged["configs"][n]["gain_pct"]
    N = lambda u, p: f"llama_3_1_8b_instruct_good_tp2_{u}u_p{p}"
    E = lambda u, p: merged["configs"][N(u, p)]

    # the Saturday wait for the other session's runtron work, from the status lines
    wait_lines = [l for l in sat_hist if "waiting: another campaign (runtron)" in l]
    wait_start = hh_mm(wait_lines[0]) if wait_lines else "?"
    after = [l for l in sat_hist if "no runtron process on the DUT" in l and (not wait_lines or l > wait_lines[-1])]
    wait_end = hh_mm(after[0]) if after else "?"
    starts = [l for l in sat_hist if "campaign start (" in l]
    t_launch1 = hh_mm(starts[0]) if starts else "?"
    t_relaunch = hh_mm(starts[1]) if len(starts) > 1 else "?"
    t_lease = next((hh_mm(l) for l in sat_hist if "CI lease free" in l), "?")
    t_check = next((hh_mm(l) for l in sat_hist if "check-32u-p8192: starting perf phase" in l), "?")
    t_stop = next((hh_mm(l) for l in sat_hist if "SIGNAL received" in l), "?")
    n_lease_wait = sum(1 for l in sat_hist if "waiting: CI lease busy" in l)
    lease_wait_lines = [l for l in sat_hist if "waiting: CI lease busy" in l]
    lease_wait_span = f"{hh_mm(lease_wait_lines[0])} to {hh_mm(lease_wait_lines[-1])} UTC" if lease_wait_lines else "none"
    sun_last_pass_start = next((hh_mm(l) for l in reversed(sun_hist) if "starting perf phase" in l), "?")
    # Sunday data quality from the summary and the snapshots
    psi_vals = []
    for rec in sun_passes.values():
        for s_ in rec.get("snapshots", []):
            m = re.search(r"avg10=([0-9.]+)", s_.get("client_cpu_psi") or "")
            if m:
                psi_vals.append(float(m.group(1)))
    psi_last = []
    for rec in sun_passes.values():
        vals = [re.search(r"avg10=([0-9.]+)", s_.get("client_cpu_psi") or "") for s_ in rec.get("snapshots", [])]
        vals = [float(m.group(1)) for m in vals if m]
        if vals:
            psi_last.append(vals[-1])
    reqs_all = e_sun.get("engine_requests_all") or {}
    reqs_80 = all(r and all(v == 80 for v in r.values()) for r in reqs_all.values()) if reqs_all else False
    sun_pp = e_sun.get("per_pass", {})

    # ---- check cell rows (Saturday)
    check_rows = []
    for tag, rec in sat_checks.items():
        r0 = (rec.get("raw") or [{}])[0]
        tps, pt = r0.get("tpss") or [], r0.get("prompt_tokens") or []
        er = r0.get("engine_requests") or {}
        check_rows.append([esc(tag), str(r0.get("prompt_length", "?")), (f"{min(pt)} to {max(pt)}" if pt else "n/a"), str(len(tps)), fmt(sum(tps) / len(tps)) if tps else "n/a", fmt(min(tps)) if tps else "n/a",
                           fmt(sum(r0.get("ttfts_ms", [0])) / max(1, len(r0.get("ttfts_ms", [0]))), 0), fmt((r0.get("wall_seconds") or 0) / 60, 1),
                           "/".join(str(er.get(str(i), er.get(i, "?"))) for i in range(4)) if er else "n/a", f"{(r0.get('amx_busy_cycles') or 0) / 1e9:.1f}", esc(rec.get("stop") or "none")])

    # ---- tables
    cells_rows = []
    for n, e, camp in rows:
        u, p = parse_name(n)
        cells_rows.append([esc(label(n)), "2026-09-19" if camp == "Sat" else "2026-09-20", str(u), str(USERS_PER_ENGINE[u]), str(p), f"{e['kv_k']:.1f}K", str(e["n_pairs"]), fmt((e["wall_s_mean"] or 0) / 60, 1)])
    cells_table = table(["cell", "campaign", "users in total", "users per engine", "prompt length", "KV tokens per engine step", "pass pairs", "minutes per cell"], cells_rows)
    res_rows = []
    for n, e, camp in rows:
        res_rows.append([esc(label(n)), "Sat" if camp == "Sat" else "Sun", fmt(e["base_tps_mean"]), fmt(e["canon_tps_mean"]), f"<b>{sfmt(e['gain_pct'])}</b>", fmt(e["paired_t"], 2),
                         ("yes, " + e["direction"]) if e["resolved"] else "no", f"{fmt(e['base_ttft_ms_mean'], 0)} / {fmt(e['canon_ttft_ms_mean'], 0)}",
                         f"{fmt(e['base_min_tps'])} / {fmt(e['canon_min_tps'])}", f"{fmt(e['base_p05_mean'])} / {fmt(e['canon_p05_mean'])}"])
    results_table = table(["cell", "campaign", "nightly TPS", "AMX TPS", "gain %", "paired t", "resolved (|t| >= 4.303 and |gain| >= 1 %)", "TTFT ms nightly / AMX", "slowest sample TPS nightly / AMX", "p05 TPS nightly / AMX"], res_rows)

    e_8u2048, e_8u4096, e_8u1024, e_2u1024, e_2u4096 = E(32, 2048), E(32, 4096), E(32, 1024), E(8, 1024), E(8, 4096)
    pf = prefill_stats({"Sat": sat_passes, "Sun": sun_passes})
    pf_sun = pf.get(CELL_SUN, {})
    pf_gains = [c["gain_pct"] for c in pf.values() if c.get("n_pairs")]
    pf_unresolved = sum(1 for c in pf.values() if c.get("n_pairs") and not c.get("resolved"))
    short = [
        "Two campaigns on the test machine delphi-3bda compared the canonical-AMX deb against the nightly deb with the nightly's own benchmark client and engine layout, in seven test cells on 2026-09-19 and one on 2026-09-20.",
        f"The largest decode gains are {sfmt(e_8u2048['gain_pct'], 1)} % and {sfmt(e_8u4096['gain_pct'], 1)} %, both at 8 users per engine, with prompt 2048 and prompt 4096, against {sfmt(e_8u1024['gain_pct'], 1)} % at prompt 1024 at the same load and {sfmt(e_2u1024['gain_pct'], 1)} % at today's nightly shape (2 users per engine, prompt 1024), and no cell above prompt 4096 could be measured (the deployed tokenizer file cuts longer prompts, section 6).",
        f"The AMX attention kernel (the CPU code the canonical-AMX deb adds) also speeds prefill (the prompt processing before the first token): the benchmark client's prefill rate rises by {sfmt(pf_sun.get('gain_pct'), 1)} % at the proposed shape (8 users per engine, prompt 4096) and by {sfmt(min(pf_gains), 1)} to {sfmt(max(pf_gains), 1)} % over the eight cells ({pf_unresolved} of them not settled by the resolved rule, section 10).",
    ]
    words = [
        ("delphi-3bda, tron, rinzler, engine, tp2, FPGA", "delphi-3bda is the test machine (section 1 describes it). tron is the inference program under test. rinzler is its production server. One running rinzler is one engine. tp2 = two FPGA cards per engine. FPGA = field-programmable gate array, the accelerator card that runs the model's weight matrix multiplications. The nightly layout is 4 tp2 engines behind the Caddy proxy."),
        ("nightly, CI, deb, nightly deb, canonical-AMX deb, arm, pass", "The nightly is the automated run of systems_test (the CI test repository) that installs tron and benchmarks it every night on delphi-3bda (CI = continuous integration). A deb is a Debian package file, the installable form of one tron build. The nightly deb is the package the nightly installed, tron 2026.09.18-3faba6d0, built without the AMX kernel. The canonical-AMX deb is the same source plus one CMake preset line (TRON_AMX_DISPATCH=ON). Its rinzler therefore contains the AMX attention kernel of PR #3879 (PR = pull request) and nothing of PR #4424 (the later VNNI-K change: it stores the K cache, the key half of the attention cache, in the layout the VNNI vector instructions read. VNNI = Vector Neural Network Instructions, a CPU instruction set). An arm is one installed package. A pass is one run of the cells on one arm. A pass-run is one driver run of a pass (a pass repeated after a failure would have two pass-runs). base = the nightly-deb arm, canon = the canonical-AMX arm, as in the pass names base-pass1 and canon-pass1. Provisioning is the driver step that installs the package's model on the engines and restarts them."),
        ("AMX, AMX-busy cycles", "AMX = Intel Advanced Matrix Extensions, the CPU matrix instructions the kernel uses for attention. AMX-busy cycles come from the CPU counter EXE.AMX_BUSY, read with perf stat (the Linux counter-reading tool) for 20 s on the engine processes before each cell: about 0 cycles on the nightly deb, billions of cycles on the AMX deb."),
        ("CI harness, shape, cell, campaign", "The CI harness is the client code of the nightly, systems_test scripts/perf.py. A shape is one combination of user count and prompt length. A cell is one shape measured on one arm: 10 rounds of all users, 1536 generated tokens per request. config = the driver's word for a cell, used in the table headers. A check cell is a one-arm run of the largest shape before the first pass, used to confirm the shape works. A campaign is one day's run: Sat = 2026-09-19 (seven cells), Sun = 2026-09-20 (one cell)."),
        ("T0, T1", "The test names of the CI test-shape recommendation page (PR3879/new-PRs/PR1/CI-AMX-test-shapes.html). T0 = the Saturday campaign as run. T1 = the shape that page recommends for the nightly: 32 users in total (8 per engine) at prompt 1024. 'The recommended load' on this page means those 8 users per engine."),
        ("TPS, TTFT, slowest sample, p05", "TPS = decode tokens per second per user, measured between generated tokens 896 and 1024 of every request and averaged over all requests of a cell. TTFT = time to first token in ms. Slowest sample = the lowest single-request TPS. p05 = the 5th percentile of the request TPS values."),
        ("users per engine, KV tokens per engine step, the two levers", "Caddy spreads the harness's user count over the 4 engines. So 8 users in total = 2 users per engine, and 32 users = 8 users per engine. KV = the key/value cache, the stored attention state of every token in context. KV tokens per engine step = users per engine x context per user (prompt + tokens the server adds + generated tokens at the middle of the TPS window). It is the attention work of one decode step. The two ways to raise it are the two levers: more users per engine (users lever) or a longer prompt (context lever)."),
        ("gain, paired t, resolved", "gain = AMX-deb mean TPS over nightly-deb mean TPS minus 1, in percent, over the 3 passes. Paired t = mean of the 3 per-pass TPS differences divided by their standard error (pass k of one arm pairs with pass k of the other). Resolved = the direction of the difference is settled: |t| >= 4.303 (the 95 % two-sided limit of Student's t with 2 degrees of freedom) and |gain| >= 1 %."),
        ("pre-registered rule, band, 16K pair, 8K triple", "Decisions fixed in each plan before the run. A band is the gain range the plan expected before the run. Saturday: the 16K pair compares 2 users per engine x prompt 7168 with 8 users per engine x prompt 1024 (both about 16K KV tokens per step). The 8K triple compares 1 user per engine x prompt 7168, 2 users per engine x prompt 3000 and 4 users per engine x prompt 1024 (about 8K). Verdict thresholds for the pair and the triple are 3 percentage points of gain. Saturday also expected +0.2 to +1.2 % at 2 users per engine x prompt 1024 and +9.9 to +15.9 % at T1. Sunday: the band was +11 to +21 %. It was derived before the run from two inputs: the Saturday 8-users-per-engine series (+10.8 % at 1024, +14.0 % at 2048) and the kernel's per-unit speed ratio of about 1.26 (the AMX kernel does one attention unit about 1.26 times faster than the AVX kernel). That ratio sets the upper limit near +21 % when attention is most of the decode step (Sunday plan, section 7)."),
        ("prefix cache, seeds, prefill", "rinzler keeps the KV state of earlier prompts (the prefix cache). Every cell uses the same seeds (the random-number seeds that pick the ShareGPT conversations, ShareGPT = a public set of chat transcripts). A longer prompt of a seed therefore starts with the shorter prompt of the same seed, sent minutes earlier. The cache serves that prefix when Caddy routes the request to the same engine. This affects TTFT and prefill (the processing of the prompt before the first token), not the TPS window."),
        ("platformd, CI lease, Bill's marker, flock, serving-down and serving-up, runtron, FUSE", "platformd is the service on delphi-3bda that starts and stops the engines. The CI lease is the file the nightly writes while it holds the machine. Bill's marker is the file that reserves half of the machine for Bill. The flock is the host-wide file lock that lets one campaign run at a time. serving-down and serving-up are the campaign steps that stop and start all production engines through platformd. runtron is tron's command-line tool. FUSE = a user-space file system: rinzler exposes its counters as files, and prompts_total is its request counter."),
    ]
    css = """
    body{background:#f9f9f7;color:#0b0b0b;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.5;margin:0;padding-block:24px;padding-inline:16px}
    main{max-width:1040px;margin:0 auto}
    h1{font-size:26px;line-height:1.2;margin:0 0 6px;text-wrap:balance}
    h2{font-size:19px;margin:36px 0 10px;border-bottom:1px solid #e1e0d9;padding-bottom:4px}
    h3{font-size:16px;margin:22px 0 6px}
    p,li{max-width:78ch}
    .sub{color:#52514e;font-size:13px;margin:0 0 18px}
    .short{background:#fcfcfb;border:1px solid #e1e0d9;border-left:4px solid #2a78d6;padding:12px 16px;margin:16px 0}
    .short p{margin:6px 0}
    nav.toc{background:#fcfcfb;border:1px solid #e1e0d9;padding:10px 16px;margin:16px 0}
    nav.toc ol{margin:6px 0 0;padding-left:22px;columns:2;column-gap:32px}
    nav.toc li{margin:2px 0;break-inside:avoid}
    nav.toc a{color:#2a78d6;text-decoration:none}
    nav.toc a:hover{text-decoration:underline}
    .fig{background:#fcfcfb;border:1px solid #e1e0d9;padding:12px;margin:14px 0;overflow-x:auto}
    .cap{color:#52514e;font-size:13px;margin:6px 0 0}
    .tw{overflow-x:auto;margin:10px 0}
    table{border-collapse:collapse;font-size:13px;min-width:600px}
    th,td{border-bottom:1px solid #e1e0d9;padding:5px 8px;text-align:left;vertical-align:top}
    th{background:#f0efec;font-weight:600;color:#52514e}
    table.num td:not(:first-child){font-variant-numeric:tabular-nums;white-space:nowrap}
    dt{font-weight:600;margin-top:10px}
    dd{margin:2px 0 0 0;color:#0b0b0b}
    code{font-size:13px;background:#f0efec;padding:1px 4px}
    .verdict{background:#fcfcfb;border:1px solid #e1e0d9;padding:10px 14px;margin:10px 0}
    details{margin:8px 0}
    summary{cursor:pointer;color:#52514e;font-size:13px}
    pre{font-size:12px;overflow-x:auto;background:#fcfcfb;border:1px solid #e1e0d9;padding:8px}
    ul ul{margin-top:2px}
    @media (max-width:600px){nav.toc ol{columns:1}}
    """
    toc = [("s1", "1. What ran"), ("s2", "2. Results of all eight cells"), ("s3", "3. The two levers and the pre-registered verdicts"), ("s4", "4. Data quality"),
           ("s5", "5. Decisions taken during the runs and deviations from the plans"), ("s6", "6. The prompt truncation at 4096"), ("s7", "7. What this does and does not show"),
           ("s8", "8. Next steps (jhan decides)"), ("s9", "9. Proposal to the CI team: add the shape as the AMX metric test"), ("s10", "10. Prefill: time to first token and the prefill rate"), ("s11", "11. Files")]
    P = []
    P.append(f"<title>llama-8b AMX results</title>\n<style>{css}</style>\n<main>")
    P.append("<h1>AMX gain on llama-3.1-8b: every CI-harness cell of the 2026-09-19 and 2026-09-20 campaigns</h1>")
    P.append(f'<p class="sub">Whole delphi-3bda (the test machine), nightly layout, CI harness, nightly deb against canonical-AMX deb. Generated {now} by exec/l8b-8u4k-20260920/gen_combined.py from the two campaigns\' result files (section 11). Every measured number comes from those files. The machine description in section 1 and the tokenizer facts in section 6 name their own sources. This page replaces reading CI-test/status/Saturday-llama-3.1-8b.html and CI-test/status/llama-3.1-8b-8u-4k.html separately. Both stay as the per-campaign records.</p>')
    P.append('<div class="short"><p><b>Short version.</b></p>' + "".join(f"<p>{esc(s)}</p>" for s in short) + "</div>")
    P.append('<nav class="toc"><b>Contents</b><ol>' + "".join(f'<li><a href="#{a}">{esc(t)}</a></li>' for a, t in [("words", "Words used here")] + toc) + "</ol></nav>")
    P.append('<h2 id="words">Words used here</h2><dl>' + "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in words) + "</dl>")

    # ---- 1 what ran
    P.append('<h2 id="s1">1. What ran</h2>')
    P.append("<ul>"
             "<li>Machine: the whole of delphi-3bda, two 72-core Intel Xeon 6962P (Granite Rapids) sockets with 288 logical CPUs (measured 2026-08-16, memory note delphi-3bda-hardware) and 8 FPGA cards (4 tp2 engines x 2 cards). 4 tp2 engines started by platformd behind Caddy on port 80, exactly the nightly layout. The CI lease was free. Each campaign took Bill's marker. The whole machine was then reserved for the campaign.</li>"
             "<li>Client: the nightly's own perf code, run from the client host claude-agentsrv through the campaign driver (st_ci_perf.py). The driver records every request, the engine layout, the engine binary per pass and the AMX-busy probe. Talos (the CI results database) was replaced by a recording stub. Nothing reached the CI records.</li>"
             f"<li>Arms: nightly deb 2026.09.18-3faba6d0 against the canonical-AMX deb tron_2026.09.18-0594dc54-jhan-ci-canon, both campaigns. 3 passes per arm, interleaved (base, canon, base, canon, base, canon). Each cell therefore has 3 pass pairs. {n_res} of the 8 cells are resolved. Saturday passes: {esc(', '.join(sat_summary['passes_found']))}. Sunday passes: {esc(', '.join(sun_summary['passes_found']))}.</li>"
             "<li>Cells: llama-3.1-8b-instruct-good-tp2, 1536 generated tokens per request (the nightly's own generation length), TPS window 896 to 1024, 10 rounds. Only the user count and the prompt length differ between cells. Config files: configs-no7168.json (Saturday, 7 cells), configs-full.json (Sunday, 1 cell).</li>"
             "<li>Prompt source: ShareGPT conversations (a public set of chat transcripts). When a prompt needs more tokens than one conversation holds, the driver joins the following conversations (one code change in the driver's checkout, the nightly's checkout untouched). The prompt-1024 prompts are identical to those the previous (nightly) prompt code produces.</li>"
             "<li>Offline prompt checks before each launch: Saturday 1920 prompts (6 prompt lengths x seeds 0 to 319), Sunday 320 prompts at prompt length 4096 (seeds 0 to 319). Both had 0 exceptions and produced identical prompts across two runs. On Sunday the md5 (a file checksum) of testlib/prompt.py equalled the Saturday copy prompt.py.after. So both campaigns ran the same prompt code.</li>"
             f"<li>Tokens the server counted around a prompt below 4096, measured on Saturday: {fmt(ovh, 1)} tokens (server-counted prompt tokens minus the prompt length sent, mean over the 36 pass records of the six cells below 4096). The Saturday plan assumed 31 tokens. Prompts of 4096 are clipped to exactly 4096 (section 6).</li>"
             "</ul>")
    P.append("<h3>The eight cells</h3>" + cells_table)
    P.append('<p class="cap">Minutes per cell = wall time of the 10 rounds, mean over the passes and arms. KV tokens per engine step = users per engine x (prompt + server overhead below 4096 + 960 generated tokens). The Saturday page counted the overhead for the 2-users prompt-4096 cell too (10.2K there, 10.1K here).</p>')
    P.append("<h3>The Saturday check cell before the first pass (32 users x prompt 8192, canonical-AMX deb)</h3>")
    P.append(table(["cell", "prompt_length sent", "prompt tokens counted by the server", "requests", "TPS mean", "slowest sample", "TTFT ms", "minutes", "requests per engine 0/1/2/3", "AMX-busy cycles (billions)", "stop"], check_rows))
    P.append('<p class="cap">The harness sent 8192-token prompts. The server counted 4096 tokens for every request. On that finding the prompt-7168 and prompt-8192 cells were dropped (section 6).</p>')
    P.append("<h3>Identity of every pass-run, Saturday</h3>" + sat.identity_table(sat_summary, sat_passes))
    P.append("<h3>Identity of every pass-run, Sunday</h3>" + sun.identity_table(sun_summary, sun_passes))
    P.append('<p class="cap">The binary check compares every engine process with the installed rinzler (by sha256, a file checksum) after each provisioning. A pass stops if any engine still runs a deleted or foreign binary. AMX-busy cycles prove which kernel ran.</p>')

    # ---- 2 results
    P.append('<h2 id="s2">2. Results of all eight cells</h2>')
    P.append('<div class="fig">' + chart_dumbbell_all(rows) + '<p class="cap">Figure 1. Each row is one cell. The light dot is the nightly deb, the dark dot the canonical-AMX deb, both the mean TPS over 3 passes. The label is the AMX gain in percent. Hover a dot for the paired t.</p></div>')
    P.append(results_table)
    P.append('<p class="cap">Slowest sample = the lowest single request of all passes of that arm. p05 = mean of the per-pass 5th percentiles. TTFT = mean of the harness\'s per-pass integer means.</p>')
    P.append("<h3>Per pass, Saturday cells</h3>" + sat.per_pass_table(sat_summary, ovh))
    P.append("<h3>Per pass, Sunday cell</h3>")
    P.append('<div class="fig">' + sun.chart_per_pass(sun_summary) + '<p class="cap">Figure 2. TPS of each pass of the Sunday cell. The label is the gain of that pair. The paired t uses these three differences.</p></div>')
    P.append(sun.per_pass_table(sun_summary, sun_passes).replace("client load (max, 32 CPUs)", "client load (max)"))
    P.append('<p class="cap">Requests per engine come from rinzler\'s prompts_total counter read before and after the cell (32 users x 10 rounds / 4 engines = 80 expected). Anomalous samples are harness samples above 1000 TPS (a client-side stall indicator). Client CPU pressure is the avg10 value of /proc/pressure/cpu (the percent of the last 10 s in which some task waited for a CPU) on the client host at the last snapshot of the pass (the 2026-09-18 run with a saturated client showed 93 to 99 %).</p>')

    # ---- 3 levers and verdicts
    pair, triple = v_sat["pair_16k"], v_sat["triple_8k"]
    P.append('<h2 id="s3">3. The two levers and the pre-registered verdicts</h2>')
    P.append('<div class="fig">' + chart_gain_vs_kv_all(rows) + '<p class="cap">Figure 3. The AMX gain against the attention work of one decode step, all eight cells. Blue = users lever (prompt 1024). Orange = context lever at 2 users per engine. Aqua = context lever at 8 users per engine.</p></div>')
    fig4 = sun.chart_gain_vs_prompt(sun_summary).replace(" (this run)", " (Sunday)")
    P.append('<div class="fig">' + fig4 + '<p class="cap">Figure 4. The same gains against prompt length. Blue: 8 users per engine (Saturday at 1024 and 2048, Sunday at 4096). Orange: 2 users per engine (Saturday). The shaded box at 4096 is the band the Sunday plan expected.</p></div>')
    spread_sun = max(e_8u4096["gain_pct_per_pass"]) - min(e_8u4096["gain_pct_per_pass"])
    P.append("<h3>Reading</h3><ul>"
             f"<li>Best cells: {esc(label(best[0][0]))} at {sfmt(best[0][1]['gain_pct'], 1)} % and {esc(label(best[1][0]))} at {sfmt(best[1][1]['gain_pct'], 1)} %. Both are at 8 users per engine. The two agree within {abs(best[0][1]['gain_pct'] - best[1][1]['gain_pct']):.2f} percentage points (smaller than the {spread_sun:.1f}-point spread between the three Sunday passes).</li>"
             f"<li>Users lever at prompt 1024: {sfmt(g(N(8, 1024)), 1)} % at 2 users per engine, {sfmt(g(N(16, 1024)), 1)} % at 4, {sfmt(g(N(32, 1024)), 1)} % at 8.</li>"
             f"<li>Context lever at 2 users per engine: {sfmt(g(N(8, 1024)), 1)} % at 1024, {sfmt(g(N(8, 2048)), 1)} % at 2048, {sfmt(g(N(8, 3000)), 1)} % at 3000, {sfmt(g(N(8, 4096)), 1)} % at 4096.</li>"
             f"<li>Context lever at 8 users per engine: {sfmt(g(N(32, 1024)), 1)} % at 1024, {sfmt(g(N(32, 2048)), 1)} % at 2048, {sfmt(g(N(32, 4096)), 1)} % at 4096. The gain stops growing between 2048 and 4096 at this load.</li>"
             f"<li>At the same prompt 4096, 8 users per engine gain {sfmt(g(N(32, 4096)), 1)} % against {sfmt(g(N(8, 4096)), 1)} % at 2 users per engine.</li>"
             f"<li>TTFT at 8 users per engine x prompt 4096: {fmt(e_8u4096['base_ttft_ms_mean'], 0)} ms on the nightly deb, {fmt(e_8u4096['canon_ttft_ms_mean'], 0)} ms on the AMX deb (Saturday at prompt 2048: {fmt(e_8u2048['base_ttft_ms_mean'], 0)} / {fmt(e_8u2048['canon_ttft_ms_mean'], 0)} ms). TTFT includes the prefill of a 4096-token prompt for 8 users per engine and the client's own waits.</li>"
             "</ul>")
    def gain_or_dropped(x):
        return "not measured (cell dropped)" if x is None else f"{sfmt(x, 2)} %"
    P.append('<div class="verdict"><p><b>Saturday, 16K pair</b> (2 users per engine x prompt 7168 against 8 users per engine x prompt 1024): ' + esc(f"gains {gain_or_dropped(pair['gain_2u_p7168'])} and {gain_or_dropped(pair['gain_8u_p1024'])}.") + f"</p><p>Verdict: {esc(pair['verdict'].replace(': a cell', '. A cell'))}. The 7168 cell was dropped (section 6).</p></div>")
    P.append('<div class="verdict"><p><b>Saturday, 8K triple</b> (1 user per engine x prompt 7168, 2 users per engine x prompt 3000, 4 users per engine x prompt 1024): ' + esc(f"gains {gain_or_dropped(triple['gain_1u_p7168'])}, {gain_or_dropped(triple['gain_2u_p3000'])}, {gain_or_dropped(triple['gain_4u_p1024'])}.") + f"</p><p>Verdict: {esc(triple['verdict'].replace(': a cell', '. A cell'))}. The 1-user cell was dropped (section 6).</p></div>")
    P.append('<div class="verdict"><p><b>Saturday, expected bands</b>: ' + esc(f"2 users per engine x prompt 1024 expected +0.2 to +1.2 %, measured {sfmt(v_sat['expected_2u_p1024']['gain'], 2)} % (inside the band: {yes_no(v_sat['expected_2u_p1024']['inside'])}). 8 users per engine x prompt 1024 (T1) expected +9.9 to +15.9 %, measured {sfmt(v_sat['expected_8u_p1024_T1']['gain'], 2)} % (inside the band: {yes_no(v_sat['expected_8u_p1024_T1']['inside'])}).") + "</p></div>")
    P.append('<div class="verdict"><p><b>Sunday, 8 users per engine x prompt 4096</b>: ' + esc(f"expected {sfmt(cell['band_pct'][0], 0)} to {sfmt(cell['band_pct'][1], 0)} %, measured {sfmt(cell['gain_pct'], 2)} % (inside the band: {yes_no(cell['inside_band'])}), paired t {fmt(cell['paired_t'], 1)} (the limit for resolved is {fmt(cell['t_limit_95'], 3)}), resolved: {yes_no(cell['resolved'])}.") + "</p>"
             + "<p>Reading: " + esc(f"the gain is inside the band. The context lever keeps working at 8 users per engine. The cell is a candidate long-prompt CI shape at the recommended load (8 users per engine). The analyze.py verdict string is: ") + f"<code>{esc(cell['reading'])}</code>.</p>"
             + '<p>Candidate goal values for a CI threshold at this shape, from the nightly deb: ' + esc(f"mean TPS {fmt(goals.get('tps_mean'))}, slowest sample {fmt(goals.get('slowest_sample_tps'))} TPS, p05 {fmt(goals.get('p05_tps_mean'))} TPS (means over the 3 nightly-deb passes. Slowest sample = the lowest of all requests of those passes).") + " No threshold exists for this shape today.</p></div>")

    # ---- 4 data quality
    P.append('<h2 id="s4">4. Data quality</h2>')
    P.append("<h3>Saturday cells</h3>" + sat.quality_table(sat_summary, ovh))
    P.append('<p class="cap">Requests per engine: expected value = users x 10 rounds / 4 engines. Caddy health events are health-checker lines in Caddy\'s journal (its systemd log) during the cell. An engine that Caddy drops from its pool of engines sends its users to the other engines. Prefix-cache hits are inflated for the longer-prompt cells by the same-seed prompts of earlier cells. The TPS window is not affected.</p>')
    P.append("<h3>Sunday cell</h3><p>" + esc(f"The Sunday cell had no data-quality problem in any pass-run: requests per engine {'80/80/80/80' if reqs_80 else 'see the per-pass table'} in all {len(reqs_all)} pass-runs, {e_sun.get('anomalous_samples_total', 0)} anomalous samples, {len(e_sun.get('caddy_health_event_runs') or [])} pass-runs with Caddy health events, {len(e_sun.get('uneven_spread_runs') or [])} pass-runs with an uneven spread [summary.json]. Client CPU pressure (avg10) was at most {max(psi_vals) if psi_vals else 0:.2f} % over all {len(psi_vals)} client snapshots of the six pass-runs [perf.json snapshots]. The per-pass table in section 2 shows the last snapshot of each pass-run only, peaking at {max(psi_last) if psi_last else 0:.2f} %. The client host was nearly idle.") + "</p>")
    P.append('<div class="fig">' + sat.chart_durations(merged).replace("Wall time of one config (10 rounds)", "Wall time of one cell (10 rounds)") + '<p class="cap">Figure 5. Wall time of one cell (10 rounds), including prompt generation and the harness\'s own waits, mean over the passes, all eight cells. The AMX-busy probe and the layout snapshot are not included.</p></div>')

    # ---- 5 decisions
    sat_dev = [
        "Saturday: two arms only, no kill-switch arm (the AMX deb run with its kernel switched off through TRON_AMX_DISABLE). jhan's decision in the plan.",
        f"Saturday: the prompt-7168 and prompt-8192 cells were dropped before the first pass. The server truncates prompts above 4096 tokens (section 6). These cells could therefore not measure the prompt lengths the plan named. The first launch ({t_launch1} UTC) waited for the CI lease until {t_lease} UTC, ran the check cell from {t_check} UTC and was stopped at {t_stop} UTC. The stop reinstalled the nightly deb (status line 'restore ok: 2026.09.18-3faba6d0'). The campaign was relaunched at {t_relaunch} UTC with 7 cells and without a second check cell.",
        f"Saturday: the relaunched campaign waited about {wait_start} to {wait_end} UTC before taking the campaign flock. Another session was running runtron work on the machine's second half (the four socket-1 FPGA cards) for GitHub issue #4500 (the FPGA-attention TPS loss under PR #4424). That session had taken the production engines down. The first engine start of the campaign was therefore its own serving-up.",
        "Saturday: the driver timeout per pass was 5400 s (90 min) instead of the plan's about 3600 s. The plan's cell estimates left 16 min of margin, and no long-prompt cell had ever been timed.",
        "Saturday: the plan's 19:30 UTC was applied as the campaign-start deadline. Each pass had its own start deadline (23:45 UTC). Every pass had to finish before 01:00 UTC.",
        "Saturday: the check cell counted as a prompt-length failure in two cases only: a timeout after the benchmark had started, or a request-level error. A driver or provisioning fault was retried once. A second such fault would have stopped the campaign.",
        "Both: engines were restarted after every package switch (serving-down, then serving-up with a wait until platformd reports idle). The older provisioning path of the CI driver never restarts an engine that already serves the same model (verified on the machine).",
        "Both: a failed pass would have been repeated once after an engine restart. Saturday counted a cell as a systematic failure after two failures in one pass-run and did not repeat later passes for it. No pass failed in either campaign.",
        "Both: per-engine request counts were read from rinzler's FUSE stats (prompts_total). rinzler's journal (its systemd log) has no per-request line.",
        "Sunday: one cell, no check cell. The Saturday check cell and the Saturday 2-users-per-engine prompt-4096 cell had shown the shape works on both the server and the client side.",
        "Sunday: the offline prompt check ran for prompt 4096 only (seeds 0 to 319, two runs compared). The Saturday prompt-source change was still in place. The md5 of testlib/prompt.py equals exec/l8b-levers-20260919/prompt.py.after.",
        f"Sunday: driver timeout 2400 s per pass (40 min, about {2400 / (e_sun['wall_s_mean'] or 1):.1f} times the {fmt((e_sun['wall_s_mean'] or 0) / 60, 1)} min the cell takes). Campaign-start deadline 22:00 UTC, last pass start 00:20 UTC. Every pass had to finish before 01:00 UTC. The script's 50-min floor before that end made 00:10 UTC the effective last start. The last pass started at {sun_last_pass_start} UTC.",
        "Sunday: the Saturday stop rule ended a campaign after two driver runs with 0 completed configs. With one config that rule was changed to count only runs that never reached the benchmark. A cell failing twice therefore continues with the next pass, as the plan says.",
    ]
    P.append('<h2 id="s5">5. Decisions taken during the runs and deviations from the plans</h2><ul>' + "".join(f"<li>{esc(d)}</li>" for d in sat_dev) + "</ul>")
    P.append(f"<p>Campaign outcome lines (quoted from the driver). Saturday: <code>{esc(sat_outcome)}</code>. Sunday: <code>{esc(sun_outcome)}</code>.</p>")
    P.append(f"<details><summary>Saturday campaign status lines (click to open. {n_lease_wait} 'waiting: CI lease busy' lines from {esc(lease_wait_span)} are omitted)</summary><pre>" + esc("\n".join(l for l in sat_hist if "waiting: CI lease busy" not in l)) + "</pre></details>")
    P.append("<details><summary>Sunday campaign status lines (click to open)</summary><pre>" + esc("\n".join(sun_hist)) + "</pre></details>")

    # ---- 6 truncation
    P.append('<h2 id="s6">6. The prompt truncation at 4096</h2>')
    P.append("<p>Facts verified on delphi-3bda and on Hugging Face (the public model repository) on 2026-09-19 (the Saturday campaign session). They are recorded in the Saturday page and in the memory note l8b-levers-20260919-campaign, not in the result files.</p><ul>"
             "<li>For llama-3.1-8b on this deployment the server keeps at most the first 4096 prompt tokens of a chat request. The Saturday check cell showed it: the harness sent 8192-token prompts and the server counted 4096 tokens for every request.</li>"
             "<li>Cause:<ul>"
             "<li>The file tokenizer.json in the cached weights directory /opt/positron/weights_cache/cached/neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16/ contains a truncation block (a setting that cuts every input at max_length 4096 tokens, direction Right = the start is kept).</li>"
             "<li>The stock file on Hugging Face does not have it.</li>"
             "<li>tron's tokenizer wrapper never disables truncation. The tokenizer therefore drops everything after token 4096 before rinzler counts the prompt.</li>"
             "<li>rinzler's own limits (max_prompt_tokens, max_total_tokens) are 131072 tokens and are not the cause.</li></ul></li>"
             "<li>Scope: the same weights directory serves the llama-3.1-8b-instruct-good and -best deployments (two named configs of the same model). The 70b w4a16 weights (w4a16 = 4-bit weights, 16-bit activations), deployed as llama-3.1-70b-instruct-good, carry the same block with max_length 8192 tokens. The other 27 cached tokenizer files on the machine have none.</li>"
             "<li>Provenance (Hugging Face commit history):<ul>"
             "<li>The block is Neural Magic's own (Neural Magic published this quantized model, a copy with weights stored at reduced precision). It is in their upload of 2024-07-26. Their calibration code (the step that measures value ranges to set the reduced precision) calls the tokenizer with truncation=True and max_length=max_seq_len, and the saved tokenizer.json then carries that setting.</li>"
             "<li>They replaced tokenizer.json on 2024-09-30 (8b commit 1455f0f5f7, 70b commit 5ce1373819).</li>"
             "<li>Positron's weights store downloaded both models on 2024-09-10, 20 days before that fix, and never refreshed. The 8b file is byte-identical to upstream revision 8ecfb5aa0d (sha256 4a49a5d5...).</li>"
             "<li>The weights are not in any Positron GitHub repository. They live on the NFS (network file system) store /opt/positron/weights/huggingface. A cron script copies them to each machine's /opt/positron/weights_cache. tron's config/models.yaml only names the model id.</li></ul></li>"
             f"<li>Consequence for these campaigns: the prompt-4096 cells run at exactly 4096 server-side prompt tokens. The server adds its system line and chat template (the fixed text that wraps a chat message, {fmt(ovh, 1)} tokens as counted on Saturday), then keeps the first 4096 tokens. Decode speed is measured the same way whether or not the prompt was clipped. No cell above prompt 4096 exists. The 16K pair and the 1-user cell of the 8K triple could therefore not be measured.</li>"
             "<li>jhan's decision of 2026-09-19: nothing is done about the truncation itself. The finding stays documented here.</li>"
             "</ul>")

    # ---- 7, 8, 9
    P.append('<h2 id="s7">7. What this does and does not show</h2><ul>'
             "<li>It shows the AMX deb's effect in the exact nightly setting for llama-3.1-8b at eight shapes. It does not measure other models. It does not measure PR #4424 (VNNI K). That change is in neither package.</li>"
             "<li>Both arms ran the same client code, prompts, layout and machine, in alternating passes. A drift of the machine therefore affects both passes of a pair. The paired t uses only within-pair differences.</li>"
             "<li>The Saturday and Sunday cells were measured one day apart with the same packages and driver. No cell was re-run on the other day.</li>"
             "<li>TTFT and prefix-cache figures for prompts above 1024 are affected by prefixes the prefix cache already holds [Words used here: prefix cache]. Decode TPS is not.</li>"
             "</ul>")
    P.append('<h2 id="s8">8. Next steps (jhan decides)</h2><ul>'
             "<li>Whether to file the 32-user (8 per engine) prompt-1024 config (T1) in systems_test. Its reference values are the 8-users-per-engine prompt-1024 row of section 2.</li>"
             "<li>The 32-user (8 per engine) prompt-4096 shape is proposed to the CI team as the AMX metric test (jhan's decision of 2026-09-20). Section 9 carries the draft message, the source changes and the binary to test with.</li>"
             "<li>The CI test-shape recommendation page (PR3879/new-PRs/PR1/CI-AMX-test-shapes.html) already lists both campaigns in its source table, as entries H (Saturday) and I (Sunday).</li>"
             "<li>Whether to preserve this page in the notebook repository (github.com/jhan-positron/notebook, artifacts/intel-amx/pr3879).</li></ul>")
    P.append(section_proposal(e_sun, e_8u2048, e_2u1024))
    sec10, prows = section_prefill(pf, rows)
    P.append(sec10)
    P.append('<h2 id="s11">11. Files</h2><ul>'
             "<li>Saturday results: <code>exec/results/l8b-levers-20260919/</code> (per pass: perf.json, talos.json, driver.log, summary.txt. summary.json and summary.txt from analyze.py. check-32u-p8192/, check-mode/, prompt-check/run1.json and run2.json, preflight.txt, base-identity.txt, outcome.txt, status-history.log). Scripts: <code>exec/l8b-levers-20260919/</code> (campaign.sh, launch.sh, dut.sh, st_ci_perf.py, configs.py, prompt_check.py, analyze.py, gen_report.py, h_registry.py, review-findings.txt, review2-findings.txt). Plan: <code>CI-test/status/Saturday-plan.md</code>. Page: <code>CI-test/status/Saturday-llama-3.1-8b.html</code>.</li>"
             "<li>Sunday results: <code>exec/results/l8b-8u4k-20260920/</code> (same directory structure as the Saturday results, plus prompt-check/compare.log, run1.log and run2.log). Scripts: <code>exec/l8b-8u4k-20260920/</code> (campaign.sh, launch.sh, dut.sh, st_ci_perf.py, configs.py, prompt_check.py, analyze.py, gen_report.py, i_registry.py, gen_combined.py), copied from exec/l8b-levers-20260919/ with the changes of plan section 4. Plan: <code>CI-test/status/llama-3.1-8b-8u-4k-plan.md</code> (section 12 = execution notes). Page: <code>CI-test/status/llama-3.1-8b-8u-4k.html</code>.</li>"
             "<li>Recommendation page these campaigns checked: <code>PR3879/new-PRs/PR1/CI-AMX-test-shapes.html</code> (generator exec/canon-ci-20260918/gen_ci_shapes.py, sources H and I).</li>"
             "<li>This page: <code>exec/l8b-8u4k-20260920/gen_combined.py</code>, which loads the two campaign generators as modules for their charts and tables.</li>"
             "<li>Prompt-source change: <code>exec/l8b-levers-20260919/prompt.py.patch</code>, applied to the driver's checkout ~/workspace/ai-runs/systems_test and not committed. The nightly's checkout is untouched.</li>"
             "</ul></main>")
    page = "\n".join(P).encode("ascii", "xmlcharrefreplace").decode("ascii")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(page)
    print(f"wrote {OUT} ({len(page)} bytes, ascii)")


if __name__ == "__main__":
    build()
