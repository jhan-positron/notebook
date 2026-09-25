#!/usr/bin/env python3
"""Page: is the first nightly "AMX benchmark" row WITH the AMX kernels (2026-09-23, 32.5 TPS) what we expected,
and what was the prefill rate of the 2026-09-22 row that Slack did not print?
Inputs (all in this folder unless noted):
  amx_row.json      amx_row.py over the four nightly logs (3bda + genoa, 09-22 + 09-23)
  history_3bda.json every 3bda perf row, nights 09-16..09-23 (all_rows.py rows() over the eight logs)
  all_rows.json     every perf row of both machines, 09-22 and 09-23
  ../results/l8b-8u4k-20260920/summary.json   our 09-20 campaign of the same test (base vs canon, 3 passes each)
Every other number is in FACTS with its source. Output: one light-theme, ASCII-only HTML page with inline SVG.
usage: gen_page.py [OUT_HTML]"""
import html, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/CI-test/status/CI-AMX-row-20260923.html"
AR = json.load(open(os.path.join(HERE, "amx_row.json")))
HIST = json.load(open(os.path.join(HERE, "history_3bda.json")))
ALL = json.load(open(os.path.join(HERE, "all_rows.json")))
SUM = json.load(open("/home/jhan/workspace/intel-AMX/exec/results/l8b-8u4k-20260920/summary.json"))
CELL = SUM["configs"]["llama_3_1_8b_instruct_good_tp2_32u_p4096"]
PP = CELL["per_pass"]
BASE = [PP[f"base-pass{i}"] for i in (1, 2, 3)]
CANON = [PP[f"canon-pass{i}"] for i in (1, 2, 3)]

FACTS = {  # source in the comment
    "slack_0923": "llama-3.1-8b-instruct-good-tp2 @32u per machine (AMX benchmark): 32.5 TPS (placeholder threshold), "
                  "prefill~354 tok/s, TTFT 11569ms (@4.1k prompt)",   # talos post 2026-09-23 06:05 PDT (#ci-cd-notifications)
    "slack_0922": "llama-3.1-8b-instruct-good-tp2 @32u per machine (AMX benchmark): 28.3 TPS",  # talos post 2026-09-22 06:20 PDT
    "run_0923": "35815209295", "run_0922": "35683952944",            # gh run list, systems_test, System CI (Rinzler 72-core Intel)
    "genoa_run_0923": "35813240282", "genoa_run_0922": "35682128668",
    "st_head_0922": "7327184", "st_head_0923": "5b2250b9",           # log line 84 / run headSha
    "pr4505_merged": "2026-09-22 21:08:26 UTC", "pr4505_merge": "9276183ad3",   # gh pr view 4505
    "deb_run": "35806901506", "deb_start": "2026-09-23 01:35:16 UTC", "deb_head": "5cf65b9241",  # gh run list publish-deb.yml
    "install_line": 455, "install_time": "03:40:06 UTC",           # nightly-35815209295.log "Setting up tron (2026.09.23-5cf65b92)"
    "genoa_install_line": 485, "genoa_install_time": "03:10:12 UTC",
    "check_time": "2026-09-23 15:32 UTC",                           # ssh delphi-3bda, read-only
    "rinzler_bytes": "234,414,048", "amx_insns": 86, "amx_strings": 1,   # objdump / strings -x TRON_AMX_DISABLE on /opt/positron/bin/rinzler
    "amx_insns_canon": 86,                                           # memory ci-enable-20260917 (same regex)
    "pr227_merged": "2026-09-22 17:48:38 UTC",                      # gh pr view 227 --repo positron-ai/systems_test
    "pr227_title": "Include prefill and TTFT in uncalibrated benchmark Slack reports",
    "merges_after_canon": 32, "commits_after_canon": 102,           # git log --first-parent / rev-list --count 3faba6d0fd..5cf65b9241
    "band": (11.0, 21.0),                                            # CI-test/status/llama-3.1-8b-8u-4k-plan.md section 7
    "ttft_est": (11.2, 11.5),                                        # memory first-ci-amx-row-20260922 ("TTFT est. 11.2-11.5 s")
    "proposed_thr": (30.6, 30.3, 30.0),                              # CI-test/status/llama-3.1-8b.html section 9.4 (mean / p05 / min)
    "u8_ref_gain": 0.21,                                             # l8b-levers-20260919 summary: 2 users/engine x prompt 1024, not resolved
}

ci22, ci23, g22, g23 = AR["3bda-0922"], AR["3bda-0923"], AR["genoa-0922"], AR["genoa-0923"]
base_mean = CELL["base_tps_mean"]; canon_mean = CELL["canon_tps_mean"]
base_ttft = CELL["base_ttft_ms_mean"]; canon_ttft = CELL["canon_ttft_ms_mean"]
base_pref = 4096 / (base_ttft / 1000); canon_pref = 4096 / (canon_ttft / 1000)
ci_gain = (ci23["tps_mean"] / ci22["tps_mean"] - 1) * 100
our_gain = CELL["gain_pct"]
g_gain = (g23["tps_mean"] / g22["tps_mean"] - 1) * 100
ci_vs_canon = (ci23["tps_mean"] / canon_mean - 1) * 100
ci_vs_base_0922 = (ci22["tps_mean"] / base_mean - 1) * 100
band_lo, band_hi = base_mean * (1 + FACTS["band"][0] / 100), base_mean * (1 + FACTS["band"][1] / 100)
canon_lo = min(c["tps_mean"] for c in CANON); canon_hi = max(c["tps_mean"] for c in CANON)
ttft_vs_canon = (ci23["ttft_mean_ms"] / canon_ttft - 1) * 100
ttft_vs_base_0922 = (ci22["ttft_mean_ms"] / base_ttft - 1) * 100
pref_gain_ci = (ci23["prefill"] / ci22["prefill"] - 1) * 100
pref_gain_ours = (canon_pref / base_pref - 1) * 100
pref_gain_g = (g23["prefill"] / g22["prefill"] - 1) * 100
thr = FACTS["proposed_thr"]

def esc(x): return html.escape(str(x), quote=True)
def f(x, nd=2): return f"{x:.{nd}f}"
def pct(x, nd=1): return f"{x:+.{nd}f}".replace("-", "&minus;") + " %"

# ---------- palette (dataviz reference instance, light) ----------
C = dict(blue="#2a78d6", orange="#eb6834", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9",
         axis="#c3c2b7", surf="#fcfcfb", band="#fbe9df", range="#a9c8ee")

def dumbbell(cid, title, desc, rows, xmin, xmax, step, unit_label, band=None, fmt=lambda v: f(v)):
    """rows: (label, sublabel, v_before, v_after, gain_text, note_before, note_after)."""
    W, X0, X1 = 1000, 400, 950
    top = 78 if band else 24
    ys = [top + 40 + i * 78 for i in range(len(rows))]
    H = ys[-1] + 92
    def X(v): return X0 + (v - xmin) / (xmax - xmin) * (X1 - X0)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="{cid}t {cid}d" style="max-width:{W}px;display:block">',
         f'<title id="{cid}t">{esc(title)}</title><desc id="{cid}d">{esc(desc)}</desc>',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="{C["surf"]}"/>']
    if band:
        lo, hi, l1, l2, nrows = band
        yb0, yb1 = ys[0] - 34, ys[nrows - 1] + 34
        s.append(f'<rect x="{X(lo):.1f}" y="{yb0}" width="{X(hi) - X(lo):.1f}" height="{yb1 - yb0}" fill="{C["band"]}"/>')
        s.append(f'<text x="{(X(lo) + X(hi)) / 2:.1f}" y="{yb0 - 22}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">{l1}</text>')
        s.append(f'<text x="{(X(lo) + X(hi)) / 2:.1f}" y="{yb0 - 7}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">{l2}</text>')
    yax = ys[-1] + 40
    v = xmin
    while v <= xmax + 1e-9:
        s.append(f'<line x1="{X(v):.1f}" y1="{top}" x2="{X(v):.1f}" y2="{yax}" stroke="{C["grid"]}" stroke-width="1"/>')
        s.append(f'<text x="{X(v):.1f}" y="{yax + 17}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">{fmt(v) if step < 1 else int(v)}</text>')
        v += step
    s.append(f'<line x1="{X0}" y1="{yax}" x2="{X1}" y2="{yax}" stroke="{C["axis"]}" stroke-width="1"/>')
    s.append(f'<text x="{(X0 + X1) / 2:.1f}" y="{yax + 40}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">{unit_label}</text>')
    for (lab, sub, vb, va, gtxt, nb, na), y in zip(rows, ys):
        s.append(f'<text x="{X0 - 16}" y="{y - 4}" text-anchor="end" font-size="14" font-weight="600" fill="{C["ink"]}">{lab}</text>')
        s.append(f'<text x="{X0 - 16}" y="{y + 14}" text-anchor="end" font-size="11.5" fill="{C["ink2"]}">{sub}</text>')
        xb, xa = X(vb), X(va)
        s.append(f'<line x1="{xb:.1f}" y1="{y}" x2="{xa:.1f}" y2="{y}" stroke="{C["axis"]}" stroke-width="2"/>')
        s.append(f'<circle cx="{xb:.1f}" cy="{y}" r="8" fill="{C["blue"]}" stroke="{C["surf"]}" stroke-width="2"><title>{esc(nb)}: {fmt(vb)}</title></circle>')
        s.append(f'<circle cx="{xa:.1f}" cy="{y}" r="8" fill="{C["orange"]}" stroke="{C["surf"]}" stroke-width="2"><title>{esc(na)}: {fmt(va)}</title></circle>')
        if abs(xa - xb) >= 90:
            s.append(f'<text x="{xb:.1f}" y="{y + 27}" text-anchor="middle" font-size="12.5" fill="{C["ink"]}">{fmt(vb)}</text>')
            s.append(f'<text x="{xa:.1f}" y="{y + 27}" text-anchor="middle" font-size="12.5" font-weight="600" fill="{C["ink"]}">{fmt(va)}</text>')
            s.append(f'<text x="{(xb + xa) / 2:.1f}" y="{y - 11}" text-anchor="middle" font-size="13" font-weight="700" fill="{C["ink"]}">{gtxt}</text>')
        else:  # dots nearly on top of each other: value labels outside, gain after the right one
            left_is_after = xa < xb
            xl, xr = min(xa, xb), max(xa, xb)
            vl, vr = (va, vb) if left_is_after else (vb, va)
            tl, tr = ("09-23", "09-22") if left_is_after else ("09-22", "09-23")
            s.append(f'<text x="{xl - 14:.1f}" y="{y + 5}" text-anchor="end" font-size="12.5" fill="{C["ink"]}">{fmt(vl)} ({tl})</text>')
            s.append(f'<text x="{xr + 14:.1f}" y="{y + 5}" font-size="12.5" fill="{C["ink"]}">{fmt(vr)} ({tr}) &#160; <tspan font-weight="700">{gtxt}</tspan></text>')
    s.append('</svg>')
    return "\n".join(s)

# ---------- chart 1: decode TPS ----------
rows1 = [
    ("Nightly CI, delphi-3bda", "09-22 no AMX kernels &#8594; 09-23 kernels in", ci22["tps_mean"], ci23["tps_mean"], pct(ci_gain),
     "CI 09-22, package 2026.09.18-3faba6d0 (no AMX kernels), TPS", "CI 09-23, package 2026.09.23-5cf65b92 (AMX kernels in), TPS"),
    ("Our campaign, 2026-09-20, delphi-3bda", "same test, CI harness, mean of 3 passes each", base_mean, canon_mean, pct(our_gain),
     "our base arm (nightly package 3faba6d0), TPS", "our canon arm (3faba6d0 + AMX kernels), TPS"),
    ("Nightly CI, andoria-b1a3 (AMD)", "same two packages; this CPU has no AMX unit", g22["tps_mean"], g23["tps_mean"], pct(g_gain),
     "CI 09-22 AMD, package 3faba6d0, TPS", "CI 09-23 AMD, package 5cf65b92 (kernels present, not used), TPS"),
]
svg1 = dumbbell("c1", "Decode speed of the 32-user llama-3.1-8b row, before and after the AMX kernels",
                f"Dumbbell chart. Intel nightly {f(ci22['tps_mean'])} to {f(ci23['tps_mean'])} TPS; our campaign {f(base_mean)} to "
                f"{f(canon_mean)} TPS; AMD nightly {f(g22['tps_mean'])} to {f(g23['tps_mean'])} TPS. Shaded band {f(band_lo)} to "
                f"{f(band_hi)} TPS is the expectation registered before our campaign.",
                rows1, 27.0, 35.0, 1.0, "TPS = generated tokens per second per user (higher is faster)",
                band=(band_lo, band_hi, "expected with the AMX kernels (registered before our campaign)",
                      f"+11 to +21 % over {f(base_mean)} = {f(band_lo)} to {f(band_hi)} TPS", 2))

# ---------- chart 2: prefill (TTFT-derived) ----------
rows2 = [
    ("Nightly CI, delphi-3bda", "09-22 value computed here; Slack did not print it", ci22["prefill"], ci23["prefill"], pct(pref_gain_ci),
     "CI 09-22 prefill, tok/s (4096 / 18.646 s)", "CI 09-23 prefill, tok/s (Slack: 354)"),
    ("Our campaign, 2026-09-20, delphi-3bda", "same formula over our mean TTFT", base_pref, canon_pref, pct(pref_gain_ours),
     "our base arm prefill, tok/s", "our canon arm prefill, tok/s"),
    ("Nightly CI, andoria-b1a3 (AMD)", "09-22 value computed here; Slack did not print it", g22["prefill"], g23["prefill"], pct(pref_gain_g),
     "CI 09-22 AMD prefill, tok/s", "CI 09-23 AMD prefill, tok/s (Slack: 307)"),
]
svg2 = dumbbell("c2", "Prefill rate of the 32-user llama-3.1-8b row (prompt 4096 tokens divided by mean TTFT)",
                f"Dumbbell chart. Intel nightly {f(ci22['prefill'],1)} to {f(ci23['prefill'],1)} tok/s; our campaign {f(base_pref,1)} to "
                f"{f(canon_pref,1)} tok/s; AMD nightly {f(g22['prefill'],1)} to {f(g23['prefill'],1)} tok/s.",
                rows2, 200, 380, 20, "prefill rate = 4096 tokens / mean TTFT, tok/s per user (higher is faster)", fmt=lambda v: f(v, 0))

# ---------- chart 3: every 3bda row vs its previous 7 nights ----------
TOL = 1.0  # a row counts as outside its range only when more than 1 % beyond it (the values carry two decimals)
NIGHTS = list(HIST.keys())            # 09-16 .. 09-23
PRIOR, LAST = NIGHTS[:-1], NIGHTS[-1]
SHORT = {
    "llama-3.2-3b-instruct-fast-tp2|u32": "llama-3.2-3b tp2, 32 users, prompt 200",
    "llama-3.1-8b-instruct-good-tp2|u8": "llama-3.1-8b tp2, 8 users, prompt 1024",
    "llama-3.1-8b-instruct-good-tp2|u32": "llama-3.1-8b tp2, 32 users, prompt 4096",
    "llama-3.3-70b-instruct-good-tp2|u8": "llama-3.3-70b tp2, 8 users",
    "llama-3.3-70b-instruct-good-tp2|u4": "llama-3.3-70b tp2, 4 users",
    "llama-3.3-70b-instruct-good-tp4|u4": "llama-3.3-70b tp4, 4 users",
    "mixtral-8x7b-instruct-v0.1-tp2|u8": "mixtral-8x7b tp2, 8 users",
    "qwen-2.5-32b-it-fast-tp2|u8": "qwen-2.5-32b tp2, 8 users",
    "ingested-qwen-3-4b-instruct-2507-tp2|u8": "qwen-3-4b tp2, 8 users",
    "ingested-qwen-3-4b-instruct-2507-tp4|u8": "qwen-3-4b tp4, 8 users",
    "gemma-2-9b-it-fast-tp2|u8": "gemma-2-9b tp2, 8 users",
    "ingested-gpt-oss-120b-tp4|u8": "gpt-oss-120b tp4, 8 users",
    "ingested-gemma-4-31b-it-tp2|u8": "gemma-4-31b tp2, 8 users",
}
ORDER = list(HIST[LAST]["rows"].keys())
H3 = []
for k in ORDER:
    prior = [HIST[n]["rows"][k][0] for n in PRIOR if k in HIST[n]["rows"]]
    last = HIST[LAST]["rows"][k][0]
    m = st.mean(prior)
    H3.append(dict(key=k, label=SHORT.get(k, k), n_prior=len(prior), pmin=min(prior), pmax=max(prior), pmean=m, last=last,
                   lo=(min(prior) / m - 1) * 100, hi=(max(prior) / m - 1) * 100, d=(last / m - 1) * 100,
                   outside=("above" if last > max(prior) * (1 + TOL / 100) else "below" if last < min(prior) * (1 - TOL / 100) else ""),
                   beyond=((last / max(prior) - 1) * 100 if last > max(prior) else (last / min(prior) - 1) * 100 if last < min(prior) else 0.0)))
def gchg(model_users):
    m, u = model_users.split("|u")
    a = [r for r in ALL["genoa-0922"] if r["model"] == m and r["users"] == int(u)]
    b = [r for r in ALL["genoa-0923"] if r["model"] == m and r["users"] == int(u)]
    return (b[0]["tps"] / a[0]["tps"] - 1) * 100 if a and b else None
for r in H3: r["genoa"] = gchg(r["key"])
by = {r["key"]: r for r in H3}

lo3 = min(min(r["lo"], r["d"]) for r in H3); hi3 = max(max(r["hi"], r["d"]) for r in H3)
XMIN3, XMAX3 = 4 * int((lo3 - 3.99) // 4), 4 * int(-(-(hi3 + 0.01) // 4))
W3, X03, X13, TOP3, RH = 1080, 318, 740, 46, 30
H3px = TOP3 + RH * len(H3) + 60
def X3(v): return X03 + (v - XMIN3) / (XMAX3 - XMIN3) * (X13 - X03)
s3 = [f'<svg viewBox="0 0 {W3} {H3px}" width="100%" role="img" aria-labelledby="c3t c3d" style="max-width:{W3}px;display:block">',
      '<title id="c3t">Every delphi-3bda perf row on 09-23 compared with its range over the previous seven nights</title>',
      '<desc id="c3d">For each row, a blue bar spans the lowest to highest nightly TPS of 09-16 to 09-22 (packages without AMX kernels), '
      'as percent of that seven-night mean; the orange dot is the 09-23 value (package with AMX kernels). Rows outside their range are labelled.</desc>',
      f'<rect x="0" y="0" width="{W3}" height="{H3px}" fill="{C["surf"]}"/>']
yb = TOP3 + RH * len(H3) + 6
v = XMIN3
while v <= XMAX3:
    s3.append(f'<line x1="{X3(v):.1f}" y1="{TOP3 - 8}" x2="{X3(v):.1f}" y2="{yb}" stroke="{C["axis"] if v == 0 else C["grid"]}" stroke-width="{1.5 if v == 0 else 1}"/>')
    s3.append(f'<text x="{X3(v):.1f}" y="{yb + 17}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">{("+" if v > 0 else "") + str(v).replace("-", "&minus;")} %</text>')
    v += 4
s3.append(f'<text x="{(X03 + X13) / 2:.1f}" y="{yb + 40}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">TPS relative to the row&#8217;s own 09-16 to 09-22 mean</text>')
s3.append(f'<text x="{X03 - 12}" y="{TOP3 - 22}" text-anchor="end" font-size="11.5" font-weight="600" fill="{C["ink2"]}">row (users in total, 4 engines)</text>')
s3.append(f'<rect x="{X03}" y="{TOP3 - 32}" width="22" height="8" rx="2" fill="{C["range"]}"/><text x="{X03 + 28}" y="{TOP3 - 24}" font-size="11.5" fill="{C["ink2"]}">range 09-16 to 09-22 (no AMX kernels)</text>')
s3.append(f'<circle cx="{X03 + 270}" cy="{TOP3 - 28}" r="5" fill="{C["orange"]}"/><text x="{X03 + 280}" y="{TOP3 - 24}" font-size="11.5" fill="{C["ink2"]}">09-23 (AMX kernels in)</text>')
for i, r in enumerate(H3):
    y = TOP3 + RH * i + RH / 2
    bold = ' font-weight="700"' if r["outside"] else ''
    s3.append(f'<text x="{X03 - 12}" y="{y + 4:.1f}" text-anchor="end" font-size="12.5"{bold} fill="{C["ink"]}">{esc(r["label"])}</text>')
    if r["n_prior"] > 1:
        s3.append(f'<rect x="{X3(r["lo"]):.1f}" y="{y - 5:.1f}" width="{max(2, X3(r["hi"]) - X3(r["lo"])):.1f}" height="10" rx="3" fill="{C["range"]}">'
                  f'<title>{esc(r["label"])}: {f(r["pmin"])} to {f(r["pmax"])} TPS over {r["n_prior"]} nights</title></rect>')
    else:
        s3.append(f'<rect x="{X3(0) - 2:.1f}" y="{y - 6:.1f}" width="4" height="12" fill="{C["blue"]}"><title>one prior night (09-22): {f(r["pmin"])} TPS</title></rect>')
    s3.append(f'<circle cx="{X3(r["d"]):.1f}" cy="{y:.1f}" r="6" fill="{C["orange"]}" stroke="{C["surf"]}" stroke-width="2">'
              f'<title>{esc(r["label"])} 09-23: {f(r["last"])} TPS ({pct(r["d"])} vs 7-night mean)</title></circle>')
    xr = max(X3(r["d"]), X3(r["hi"])) + 12
    tag = ""
    if r["outside"]:
        tag = f' &#183; {pct(r["beyond"])} {r["outside"]} range' if r["n_prior"] > 1 else " &#183; 1 prior night"
    s3.append(f'<text x="{xr:.1f}" y="{y + 4:.1f}" font-size="12"{bold} fill="{C["ink"]}">{f(r["last"])} TPS, {pct(r["d"])}{tag}</text>')
s3.append('</svg>')
svg3 = "\n".join(s3)

# ---------- tables ----------
def tr(cells, head=False):
    tag = "th" if head else "td"
    return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"
t1 = ['<table class="num"><thead>', tr(["Run", "Package", "TPS mean", "sd", "p05", "slowest", "TTFT, ms", "prefill, tok/s", "samples"], True), "</thead><tbody>"]
t1.append(tr(["CI delphi-3bda 09-22", "2026.09.18-3faba6d0 (no kernels)", f(ci22["tps_mean"], 3), f(ci22["tps_sd"], 3), f(ci22["p05"]), f(ci22["tps_min"]),
              f"{ci22['ttft_mean_ms']:,.0f}", f"{ci22['prefill']:.1f} (not in Slack)", ci22["n"]]))
t1.append(tr(["<b>CI delphi-3bda 09-23</b>", "2026.09.23-5cf65b92 (kernels in)", f"<b>{f(ci23['tps_mean'], 3)}</b>", f(ci23["tps_sd"], 3), f(ci23["p05"]), f(ci23["tps_min"]),
              f"{ci23['ttft_mean_ms']:,.0f}", f"{ci23['prefill']:.1f}", ci23["n"]]))
t1.append(tr(["Ours 09-20, base arm", "2026.09.18-3faba6d0 (no kernels)", f(base_mean, 3), f"{min(b['tps_sd'] for b in BASE):.2f}&#8211;{max(b['tps_sd'] for b in BASE):.2f}",
              f(CELL["base_p05_mean"]), f(CELL["base_min_tps"]), f"{base_ttft:,.0f}", f"{base_pref:.1f}", "3 &#215; 320"]))
t1.append(tr(["Ours 09-20, canon arm", "3faba6d0 + AMX kernels", f(canon_mean, 3), f"{min(c['tps_sd'] for c in CANON):.2f}&#8211;{max(c['tps_sd'] for c in CANON):.2f}",
              f(CELL["canon_p05_mean"]), f(CELL["canon_min_tps"]), f"{canon_ttft:,.0f}", f"{canon_pref:.1f}", "3 &#215; 320"]))
t1.append(tr(["CI andoria-b1a3 09-22", "2026.09.18-3faba6d0", f(g22["tps_mean"], 3), f(g22["tps_sd"], 3), f(g22["p05"]), f(g22["tps_min"]),
              f"{g22['ttft_mean_ms']:,.0f}", f"{g22['prefill']:.1f} (not in Slack)", g22["n"]]))
t1.append(tr(["CI andoria-b1a3 09-23", "2026.09.23-5cf65b92", f(g23["tps_mean"], 3), f(g23["tps_sd"], 3), f(g23["p05"]), f(g23["tps_min"]),
              f"{g23['ttft_mean_ms']:,.0f}", f"{g23['prefill']:.1f}", g23["n"]]))
t1.append("</tbody></table>")
t1 = "\n".join(t1)

t2 = ['<table class="num"><thead>', tr(["Row (delphi-3bda)"] + [n[5:] if len(n) > 5 else n for n in NIGHTS] + ["09-23 vs range", "AMD 09-22&#8594;09-23"], True), "</thead><tbody>"]
for r in H3:
    cells = [esc(r["label"])]
    for n in NIGHTS:
        v = HIST[n]["rows"].get(r["key"])
        cells.append(f(v[0]) if v else "&#8211;")
    cells[-1] = f"<b>{cells[-1]}</b>"
    cells.append((pct(r["beyond"]) + " " + r["outside"]) if r["outside"] and r["n_prior"] > 1 else ("inside" if not r["outside"] else "1 prior night"))
    cells.append(pct(r["genoa"]) if r["genoa"] is not None else "&#8211;")
    t2.append(tr(cells))
pk = " | ".join(f"{n}: {HIST[n]['ver'][0]}" for n in NIGHTS)
t2.append("</tbody></table>")
t2 = "\n".join(t2)

q4 = by["ingested-qwen-3-4b-instruct-2507-tp4|u8"]; go = by["ingested-gpt-oss-120b-tp4|u8"]; l70 = by["llama-3.3-70b-instruct-good-tp4|u4"]
g4 = by["ingested-gemma-4-31b-it-tp2|u8"]; u8 = by["llama-3.1-8b-instruct-good-tp2|u8"]

# ---------- page ----------
page = f"""<title>First Nightly With AMX Kernels</title>
<meta name="description" content="Checks the 2026-09-23 nightly AMX-benchmark row (32.5 TPS) against our measurements and computes the 2026-09-22 prefill rate.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600;700&display=swap">
<style>
:root {{ color-scheme: light; --ground:#f5f5f2; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --rule:#dcdbd3;
  --blue:{C["blue"]}; --orange:{C["orange"]}; --band:{C["band"]}; --code:#efeee9; }}
html, body {{ background: var(--ground); color: var(--ink); }}
body {{ font: 15.5px/1.6 "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; padding-inline: 16px; padding-block: 28px 64px; }}
.wrap {{ max-width: 1000px; margin: 0 auto; display: grid; gap: 18px; }}
.prose {{ max-width: 70ch; }}
h1 {{ font-size: 1.9rem; line-height: 1.2; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.28rem; margin: 30px 0 0; padding-top: 16px; border-top: 1px solid var(--rule); text-wrap: balance; }}
h3 {{ font-size: 1.02rem; margin: 10px 0 0; }}
p, ul, ol {{ margin: 0; }}
ul, ol {{ padding-left: 1.25em; display: grid; gap: 6px; }}
.meta {{ color: var(--ink2); font-size: 0.9rem; }}
.short {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 14px 18px; display: grid; gap: 8px; max-width: 78ch; }}
.short b.lead {{ font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); }}
.verdict {{ font-size: 1.1rem; font-weight: 600; }}
code, .mono {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, monospace; font-size: 0.86em; }}
code {{ background: var(--code); padding: 1px 4px; border-radius: 3px; }}
.slack {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, monospace; font-size: 0.82rem; background: var(--surface); border: 1px solid var(--rule);
  border-radius: 6px; padding: 10px 12px; overflow-x: auto; white-space: pre; }}
figure {{ margin: 0; display: grid; gap: 8px; }}
.chart {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; overflow-x: auto; }}
.chart svg {{ font-family: "IBM Plex Sans", system-ui, sans-serif; min-width: 640px; }}
figcaption {{ color: var(--ink2); font-size: 0.92rem; max-width: 80ch; }}
figcaption b {{ color: var(--ink); }}
.tw {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.86rem; }}
th, td {{ padding: 6px 10px; border-bottom: 1px solid var(--rule); text-align: left; vertical-align: top; }}
th {{ font-weight: 600; color: var(--ink2); background: #f1f0eb; }}
table.num td {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
dl.words {{ display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; margin: 0; max-width: 90ch; }}
dl.words dt {{ font-weight: 600; }}
dl.words dd {{ margin: 0; color: var(--ink2); }}
@media (max-width: 640px) {{ dl.words {{ grid-template-columns: 1fr; }} dl.words dd {{ margin-bottom: 6px; }} }}
details {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 8px 12px; }}
summary {{ cursor: pointer; font-weight: 600; }}
summary:focus-visible, a:focus-visible {{ outline: 2px solid var(--blue); outline-offset: 2px; }}
a {{ color: #1f5fae; }}
.open {{ display: grid; gap: 14px; }}
.item {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 12px 16px; display: grid; gap: 6px; max-width: 86ch; }}
.item .tag {{ font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); font-weight: 600; }}
</style>

<div class="wrap">
<header style="display:grid;gap:6px">
<p class="meta">delphi-3bda nightly CI &#183; AMX benchmark row &#183; written 2026-09-23 from the 09-22 and 09-23 run logs</p>
<h1>First nightly with the AMX kernels: is 32.5 TPS what we expected?</h1>
</header>

<section class="short">
<b class="lead">Short version</b>
<p class="verdict">Yes: last night&#8217;s 32.5 TPS is the value we expected once the AMX kernels reached the nightly package.</p>
<p>It is {pct(ci_gain)} above the night before ({f(ci22["tps_mean"])} TPS), and our own campaign measured {pct(our_gain)} for the same test.</p>
<p>The 09-22 prefill rate, which Slack did not print, was {ci22["prefill"]:.0f} tok/s (TTFT {ci22["ttft_mean_ms"]/1000:.1f} s).</p>
</section>

<section style="display:grid;gap:10px">
<h2 style="border-top:0;margin-top:6px;padding-top:0">Words used here</h2>
<dl class="words">
<dt>TPS</dt><dd>Decode speed: generated tokens per second for one user. The CI harness measures it between generated tokens 896 and 1024 of each request and reports the mean over all samples.</dd>
<dt>TTFT</dt><dd>Time to first token: the time from sending a request to receiving its first generated token, in milliseconds. With 8 users per engine it includes the wait behind other users&#8217; prompts.</dd>
<dt>prefill rate (prefill&#8776;)</dt><dd>Prompt length divided by mean TTFT, in tokens per second (tok/s). The CI computes it on the client. It is not a server-side prefill timing.</dd>
<dt>AMX</dt><dd>Advanced Matrix Extensions: the matrix unit in Intel Xeon CPUs, such as the Xeon 6962P in delphi-3bda.</dd>
<dt>AMX kernels</dt><dd>tron&#8217;s attention code that uses AMX. It is compiled in only when the build option <code>TRON_AMX_DISPATCH</code> is ON. PR #4505 turned it on for the nightly .deb package.</dd>
<dt>no-kernel / kernels-in package</dt><dd>A tron package built without / with the AMX kernels.</dd>
<dt>kill switch</dt><dd>The environment variable <code>TRON_AMX_DISABLE</code>. It turns the AMX kernels off at run time in a kernels-in build.</dd>
<dt>canon</dt><dd>Our 09-20 kernels-in build: tron main 3faba6d0 plus the AMX build option, with the canonical (default) AMX kernels.</dd>
<dt>tron, rinzler</dt><dd>tron is the inference program under test. rinzler is the server binary inside the tron package.</dd>
<dt>delphi-3bda, andoria-b1a3</dt><dd>The two CI machines: Intel Xeon 6962P (has AMX) and AMD Genoa (no AMX unit).</dd>
<dt>tp2, tp4</dt><dd>The model is split over 2 or 4 accelerator cards (tensor parallel).</dd>
<dt>@32u per machine</dt><dd>32 users in total, spread over 4 engines: 8 users per engine.</dd>
<dt>p05, sd</dt><dd>p05 is the 5th percentile of the per-user TPS samples (95 % of samples are faster). sd is the population standard deviation of those samples.</dd>
<dt>systems_test, talos, publish-deb</dt><dd>systems_test is the repository with the CI harness. talos is the bot that posts the nightly report to Slack. publish-deb is the tron workflow that builds the nightly package at 01:35 UTC.</dd>
</dl>
</section>

<h2>1. Is 32.5 TPS what we expected?</h2>
<p class="prose">Chart 1 places the two nights of the CI row next to our 09-20 campaign of the same test (32 users, prompt 4096 tokens, 1536 generated tokens). The shaded band is the range we wrote down before our campaign: +11 to +21 % over the no-kernel value [CI-test/status/llama-3.1-8b-8u-4k-plan.md, section 7].</p>
<figure>
<div class="chart">{svg1}</div>
<figcaption><b>Only the Intel rows moved.</b> The AMD machine ran the same two packages and did not change ({pct(g_gain)}). Blue dot = package without AMX kernels, orange dot = package with AMX kernels. Hover a dot for its source.</figcaption>
</figure>
<ul class="prose">
<li>The CI value is {f(ci23["tps_mean"], 3)} TPS, the mean of {ci23["n"]} samples. Slack rounds it to 32.5.</li>
<li>The CI gain is {pct(ci_gain)}. Our campaign measured {pct(our_gain)} (paired t {CELL["paired_t"]:.0f} over 3 pass pairs).</li>
<li>The CI value is {ci23["tps_mean"] - canon_mean:+.2f} TPS ({pct(ci_vs_canon)}) above our canon mean of {f(canon_mean, 3)} TPS. Our three canon passes spanned {f(canon_lo)} to {f(canon_hi)} TPS, so the CI value is above all three. On 09-22 the no-kernel values agreed to {pct(ci_vs_base_0922, 2)}. Section 5 lists what could cause the 0.9 % gap.</li>
<li>TTFT is {ci23["ttft_mean_ms"]:,.0f} ms, {pct(ttft_vs_canon)} slower than our canon ({canon_ttft:,.0f} ms). My estimate on 09-22 was {FACTS["ttft_est"][0]} to {FACTS["ttft_est"][1]} s, so the CI value is {ci23["ttft_mean_ms"]/1000 - FACTS["ttft_est"][1]:.2f} s above its upper edge.</li>
<li>The row still has no threshold. &#8220;(placeholder threshold)&#8221; is only a display label. With the thresholds we proposed (mean {thr[0]}, p05 {thr[1]}, slowest {thr[2]} TPS; CI-test/status/llama-3.1-8b.html section 9.4), this night passes by {ci23["tps_mean"] - thr[0]:.2f}, {ci23["p05"] - thr[1]:.2f} and {ci23["tps_min"] - thr[2]:.2f} TPS.</li>
</ul>
<div class="tw">{t1}</div>
<p class="meta prose">CI rows: all 320 &#8220;Done&#8221; samples of the row in the GitHub run log (amx_row.py). Our rows: exec/results/l8b-8u4k-20260920/summary.json; sd is the per-pass range, p05 the mean of the three pass values, slowest the lowest sample of all passes. Prefill = 4096 / mean TTFT in every row.</p>

<h2>2. The prefill rate of the 09-22 row</h2>
<p class="prose">The 09-22 row was measured like every other row. Only its Slack line was shorter. These are the two lines as posted:</p>
<div class="slack">09-22: {esc(FACTS["slack_0922"])}
09-23: {esc(FACTS["slack_0923"])}</div>
<h3>The value</h3>
<ul class="prose">
<li>Mean TTFT over the 320 samples was {ci22["ttft_mean_ms"]:,.2f} ms. The harness rounds it to {ci22["ttft_rounded_ms"]:,} ms.</li>
<li>Prefill = 4096 tokens / {ci22["ttft_rounded_ms"]/1000:.3f} s = <b>{ci22["prefill"]:.1f} tok/s</b>. The Slack line would have read &#8220;prefill&#8776;{ci22["prefill"]:.0f} tok/s, TTFT {ci22["ttft_rounded_ms"]}ms (@4.1k prompt)&#8221;.</li>
<li>The AMD row of 09-22 also lacked it: {g22["prefill"]:.1f} tok/s (TTFT {g22["ttft_rounded_ms"]:,} ms).</li>
</ul>
<h3>Why Slack did not print it</h3>
<ul class="prose">
<li>The 09-22 nightly ran systems_test commit {FACTS["st_head_0922"]}. In that version, a row with no threshold at all got a short line with the TPS value only [testlib/results.py, branch <code>if not has_threshold</code>].</li>
<li>The gemma-4 row printed timing that same night. It has a placeholder goal of 1.00 TPS in <code>scripts/system_ci.py</code>, so it took the placeholder branch, which already added timing. The AMX row had no goal entry.</li>
<li>PR #227, &#8220;{esc(FACTS["pr227_title"])}&#8221;, changed the short line to the placeholder format with timing. It merged at {FACTS["pr227_merged"]}, after the 09-22 run. The 09-23 run used commit {FACTS["st_head_0923"]}, which includes it.</li>
<li>The harness computed the value on 09-22 as well. The formula at <code>scripts/perf.py:396-397</code> is the same in both commits, and it stores prefill with each result. Only the Slack line left it out.</li>
</ul>
<h3>Check of the method</h3>
<p class="prose">The same computation over the 09-23 log gives TTFT {ci23["ttft_rounded_ms"]:,} ms and {ci23["prefill"]:.0f} tok/s. Those are the numbers Slack printed. For the AMD row it gives {g23["ttft_rounded_ms"]:,} ms and {g23["prefill"]:.0f} tok/s, also as printed. The per-sample TTFT means match the Slack TTFT of all 13 rows on both machines for 09-23.</p>
<figure>
<div class="chart">{svg2}</div>
<figcaption><b>The prefill rate rose {pct(pref_gain_ci)} in CI and {pct(pref_gain_ours)} in our campaign.</b> The rate includes the wait behind other users&#8217; prompts, so it describes what one user sees, not the engine&#8217;s total prompt throughput.</figcaption>
</figure>

<h2>3. Did the nightly package really contain the AMX kernels?</h2>
<p class="prose">Yes. Each step below was checked on 2026-09-23.</p>
<div class="tw"><table>
<thead>{tr(["Step", "Evidence", "Source"], True)}</thead><tbody>
{tr(["The build switch merged", f"PR #4505 merged at {FACTS['pr4505_merged']} (merge commit {FACTS['pr4505_merge']}).", "<code>gh pr view 4505</code>"])}
{tr(["The package was built after it", f"publish-deb run {FACTS['deb_run']} started {FACTS['deb_start']} and succeeded on main {FACTS['deb_head']}. That commit contains {FACTS['pr4505_merge']}.", "<code>gh run list</code>, <code>git merge-base --is-ancestor</code>"])}
{tr(["Both CI machines installed it", f"delphi-3bda: &#8220;Setting up tron (2026.09.23-5cf65b92)&#8221; at {FACTS['install_time']}. andoria-b1a3: same line at {FACTS['genoa_install_time']}. Both Slack reports name this version.", f"run logs, lines {FACTS['install_line']} and {FACTS['genoa_install_line']}"])}
{tr(["The installed server has the kernels", f"At {FACTS['check_time']}, dpkg reported 2026.09.23-5cf65b92. <code>/opt/positron/bin/rinzler</code> ({FACTS['rinzler_bytes']} bytes) holds {FACTS['amx_insns']} AMX tile instructions and the kill-switch text {FACTS['amx_strings']} time. Our canon build: {FACTS['amx_insns_canon']} and 1. No-kernel packages: 0 and 0.", "<code>objdump -d</code>, <code>strings</code> on delphi-3bda (read-only)"])}
{tr(["No setting found that turns AMX off", "<code>/opt/positron/user/config.env</code> is empty (0 bytes). <code>/etc/rinzler/instance-*.env</code> contain no <code>TRON_AMX</code> or <code>USE_HW_ATTN</code> line.", "<code>grep</code> on delphi-3bda"])}
{tr(["Run-time proof", "Not available. The CI does not read the AMX busy counter (EXE.AMX_BUSY). The evidence that AMX ran is indirect: the gain matches ours, and the AMD machine did not move.", "Insufficient data: read the counter on one engine process during this row"])}
</tbody></table></div>

<h2>4. The rest of the nightly</h2>
<p class="prose">Chart 3 compares every delphi-3bda perf row of 09-23 with its range over the previous seven nights. All seven ran packages without AMX kernels ({esc(pk.split(" | ")[0])} to {esc(pk.split(" | ")[-2])}).</p>
<figure>
<div class="chart">{svg3}</div>
<figcaption><b>Most rows stayed inside their normal range. Three tp4 rows rose above it.</b> The llama-3.1-8b row with 8 users rose {pct(u8["beyond"])} above its range. Our campaign measured {pct(FACTS["u8_ref_gain"])} for AMX at 2 users per engine and prompt 1024 (not resolved) [l8b-levers-20260919].</figcaption>
</figure>
<ul class="prose">
<li>qwen-3-4b tp4: {f(q4["last"])} TPS against {f(q4["pmin"])} to {f(q4["pmax"])} before ({pct(q4["beyond"])} above the highest night). AMD, same package change: {pct(q4["genoa"])}.</li>
<li>gpt-oss-120b tp4: {f(go["last"])} TPS against {f(go["pmin"])} to {f(go["pmax"])} ({pct(go["beyond"])} above). AMD: {pct(go["genoa"])}.</li>
<li>llama-3.3-70b tp4: {f(l70["last"])} TPS against {f(l70["pmin"])} to {f(l70["pmax"])} ({pct(l70["beyond"])} above). AMD: {pct(l70["genoa"])}.</li>
<li>gemma-4-31b tp2 fell {pct(g4["beyond"])} below its range ({f(g4["last"])} against {f(g4["pmin"])} to {f(g4["pmax"])}). AMD: {pct(g4["genoa"])}.</li>
<li>The other tp2 rows stayed inside their range, or within 0.3 % of it.</li>
</ul>
<details><summary>All rows, all eight nights (TPS mean over the &#8220;Done&#8221; samples)</summary>
<div class="tw" style="margin-top:8px">{t2}</div>
<p class="meta" style="margin-top:6px">Packages: {esc(pk)}.</p>
</details>

<h2>5. What is not explained yet</h2>
<div class="open">
<div class="item"><span class="tag">Open item A</span>
<p><b>The CI kernels-in value is {pct(ci_vs_canon)} above ours.</b> On 09-22 the no-kernel values agreed to {pct(ci_vs_base_0922, 2)} with the same binary. So the harness setup, the prompt set and platformd 0.11 did not change the no-kernel value.</p>
<p>The two kernels-in builds differ in their tron code. CI ran main {FACTS["deb_head"]}, which is {FACTS["merges_after_canon"]} merges ({FACTS["commits_after_canon"]} commits) after our canon base 3faba6d0.</p>
<p>Hypothesis: one of those merges speeds up this row on Intel with AMX. Candidates by title: #4455 and #4456 (sliding KV storage and reclamation), #4516 (slice cost data for the Xeon 6962P), #4258 (FPGA attention streaming join), and the placement changes. Measurement that decides it: interleaved passes of the nightly package 2026.09.23-5cf65b92 and our canon package on delphi-3bda with our harness.</p>
</div>
<div class="item"><span class="tag">Open item B</span>
<p><b>CI TTFT is {pct(ttft_vs_canon)} above ours, while CI TPS is {pct(ci_vs_canon)} above ours.</b> On 09-22, CI TTFT was {pct(ttft_vs_base_0922)} relative to our no-kernel value. The cause is unknown. The measurement in item A also reports TTFT and would show whether the newer code shifts time from prefill to decode.</p>
</div>
<div class="item"><span class="tag">Open item C</span>
<p><b>Three tp4 rows rose on delphi-3bda only.</b> The cause is not determined.</p>
<p>Hypotheses: (1) the AMX kernels also help these engines; (2) #4516 changed placement cost data for this CPU model only; (3) another merge in the same range. Measurement that decides (1): rerun the three rows on the 09-23 package with and without the kill switch and read EXE.AMX_BUSY per engine. The kill switch arm ran a few points slower than a no-kernel build in our 08-31 test [memory amx-vs-avx-sense]. A clean split therefore also needs a no-kernel build of 5cf65b92.</p>
</div>
</div>

<h2>6. Sources</h2>
<ul class="prose">
<li>systems_test runs (GitHub Actions): delphi-3bda {FACTS["run_0922"]} (09-22) and {FACTS["run_0923"]} (09-23); andoria-b1a3 {FACTS["genoa_run_0922"]} and {FACTS["genoa_run_0923"]}; seven earlier delphi-3bda nights for chart 3. Logs saved in exec/ci-amx-row-20260923/.</li>
<li>Slack #ci-cd-notifications: talos nightly reports of 2026-09-22 (06:20 PDT) and 2026-09-23 (06:05 PDT).</li>
<li>Scripts: amx_row.py (row statistics, p05 by linear interpolation as in systems_test), all_rows.py (every row), gen_page.py (this page), all in exec/ci-amx-row-20260923/.</li>
<li>Our campaign: exec/results/l8b-8u4k-20260920/summary.json; plan CI-test/status/llama-3.1-8b-8u-4k-plan.md; report CI-test/status/llama-3.1-8b.html.</li>
<li>Previous page: CI-test/status/first-CI-AMX-row-20260922.html (the 09-22 row against our no-kernel value).</li>
<li>systems_test code: <code>scripts/perf.py:396-397</code> (TTFT rounding and prefill), <code>testlib/results.py</code> (Slack line), commit 18c60c6 in PR #227.</li>
</ul>
</div>
"""
for bad in ("≈", "→", "—", "–", "·"):
    assert bad not in page, bad
page.encode("ascii")  # raises if any non-ASCII character slipped in
open(OUT, "w", encoding="ascii").write(page)
print("wrote", OUT, len(page), "bytes")
