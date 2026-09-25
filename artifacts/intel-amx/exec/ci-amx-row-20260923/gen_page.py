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
    "amx_insns_total": 98, "tilezero": 12,                           # verifier: objdump of rinzler from the publish-deb artifact; memory ci-enable-20260917
    "canon_src": "canon-ci-20260918 campaign (package 2026.09.18-0594dc54-jhan-ci-canon)",  # memory canon-ci-20260918-campaign.md:16
    "deb_amx_line": 4834,                                            # gh run view 35806901506 --log: "[317/375] Building CXX object ... kernels/amx_attn.cpp.o"
    "talos_0922": "4d0034b1-b637-11f1-87f0-bc2411bdb3f2", "talos_0922_genoa": "1e9c1199-b633-11f1-9378-bc2411bdb3f2",  # run log line 564; curl talos:5000/sessions/<id>
    "talos_0922_line": "28.25 (std dev 0.16) TTFT 18646ms, prefill 220 tok/s (4096 observed prompt tok, 1% cached)",  # talos_0922_3bda.json
    "talos_0922_cache_pct": 0.83, "talos_0922_prefill": 219.67,      # talos_0922_3bda_metrics.json entry: cache_hit_pct 0.8266, prefill_mean 219.6718
    "talos_0922_genoa_line": "29.00 (std dev 0.45) TTFT 13266ms, prefill 309 tok/s (4096 observed prompt tok, 1% cached)",  # talos_0922_genoa.json
    "ks_clean": 14.650, "ks_off": 14.745,                            # exec/results/qwen8u8k-pr1-half-20260909T1704.txt, 16 requests per arm
    "c918": {"qwen tp4": (149.94, 146.05), "gpt-oss tp4": (106.51, 102.33), "70b tp4": (29.92, 30.47)},  # ci-mimic base-pass1 vs canon-ci canon summary.txt (no kernels, kernels)
    "pr4534_gain": "+6.9 to +11.3 %",                                # PR #4534 body: gpt-oss-20b decode per user, counters on -> off, 1 and 4 users
    "syntax_log_end": "05:07:48 UTC",                               # ls -l /var/tmp/jhan/tron-issue4525-rebase-syntax.log on delphi-3bda
    "same_pkg_range": (0.07, 1.33),                                  # history_3bda.json, tp2 rows, nights 09-18..09-22 (one package)
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
        s.append(f'<text x="{W - 12}" y="{yb0 - 22}" text-anchor="end" font-size="12" fill="{C["ink2"]}">{l1}</text>')
        s.append(f'<text x="{W - 12}" y="{yb0 - 7}" text-anchor="end" font-size="12" fill="{C["ink2"]}">{l2}</text>')
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
    ("Nightly CI, delphi-3bda", "09-22 no AMX kernels, 09-23 kernels in", ci22["tps_mean"], ci23["tps_mean"], pct(ci_gain),
     "CI 09-22, package 2026.09.18-3faba6d0 (no AMX kernels), TPS", "CI 09-23, package 2026.09.23-5cf65b92 (AMX kernels in), TPS"),
    ("Our campaign, 2026-09-20, delphi-3bda", "same test, CI harness, mean of 3 passes each", base_mean, canon_mean, pct(our_gain),
     "our base arm (nightly package 3faba6d0), TPS", "our canon arm (3faba6d0 + AMX kernels), TPS"),
    ("Nightly CI, andoria-b1a3 (AMD)", "same two packages, CPU without an AMX unit", g22["tps_mean"], g23["tps_mean"], pct(g_gain),
     "CI 09-22 AMD, package 3faba6d0, TPS", "CI 09-23 AMD, package 5cf65b92 (kernels present, not used), TPS"),
]
svg1 = dumbbell("c1", "Decode speed of the 32-user llama-3.1-8b row, before and after the AMX kernels",
                f"Dumbbell chart. Intel nightly {f(ci22['tps_mean'])} to {f(ci23['tps_mean'])} TPS. Our campaign {f(base_mean)} to "
                f"{f(canon_mean)} TPS. AMD nightly {f(g22['tps_mean'])} to {f(g23['tps_mean'])} TPS. Shaded band {f(band_lo)} to "
                f"{f(band_hi)} TPS = the +11 to +21 % band registered before our campaign, applied to our measured no-kernel mean.",
                rows1, 27.0, 35.0, 1.0, "TPS = generated tokens per second per user (higher is faster)",
                band=(band_lo, band_hi, "+11 to +21 % band, registered before our campaign,",
                      f"applied to our measured no-kernel mean {f(base_mean, 3)} TPS = {f(band_lo)} to {f(band_hi)} TPS", 2))

# ---------- chart 2: prefill (TTFT-derived) ----------
rows2 = [
    ("Nightly CI, delphi-3bda", "09-22 value from Talos, not printed in Slack", ci22["prefill"], ci23["prefill"], pct(pref_gain_ci),
     "CI 09-22 prefill, tok/s (4096 / 18.646 s)", "CI 09-23 prefill, tok/s (Slack: 354)"),
    ("Our campaign, 2026-09-20, delphi-3bda", "same formula over our mean TTFT", base_pref, canon_pref, pct(pref_gain_ours),
     "our base arm prefill, tok/s", "our canon arm prefill, tok/s"),
    ("Nightly CI, andoria-b1a3 (AMD)", "09-22 value from Talos, not printed in Slack", g22["prefill"], g23["prefill"], pct(pref_gain_g),
     "CI 09-22 AMD prefill, tok/s", "CI 09-23 AMD prefill, tok/s (Slack: 307)"),
]
svg2 = dumbbell("c2", "Prefill rate of the 32-user llama-3.1-8b row (prompt 4096 tokens divided by mean TTFT)",
                f"Dumbbell chart. Intel nightly {f(ci22['prefill'],1)} to {f(ci23['prefill'],1)} tok/s. Our campaign {f(base_pref,1)} to "
                f"{f(canon_pref,1)} tok/s. AMD nightly {f(g22['prefill'],1)} to {f(g23['prefill'],1)} tok/s.",
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
      'as percent of that seven-night mean. The orange dot is the 09-23 value (package with AMX kernels). Rows outside their range are labelled.</desc>',
      f'<rect x="0" y="0" width="{W3}" height="{H3px}" fill="{C["surf"]}"/>']
yb = TOP3 + RH * len(H3) + 6
v = XMIN3
while v <= XMAX3:
    s3.append(f'<line x1="{X3(v):.1f}" y1="{TOP3 - 8}" x2="{X3(v):.1f}" y2="{yb}" stroke="{C["axis"] if v == 0 else C["grid"]}" stroke-width="{1.5 if v == 0 else 1}"/>')
    s3.append(f'<text x="{X3(v):.1f}" y="{yb + 17}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">{("+" if v > 0 else "") + str(v).replace("-", "&minus;")} %</text>')
    v += 4
s3.append(f'<text x="{(X03 + X13) / 2:.1f}" y="{yb + 40}" text-anchor="middle" font-size="12" fill="{C["ink2"]}">TPS relative to the row&#8217;s own 09-16 to 09-22 mean</text>')
s3.append(f'<text x="{X03 - 12}" y="{TOP3 - 22}" text-anchor="end" font-size="11.5" font-weight="600" fill="{C["ink2"]}">row (users in total, tp2 on 4 engines, tp4 on 2)</text>')
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
    ref = f"vs the {r['n_prior']}-night mean" if r["n_prior"] > 1 else "vs the one prior night, 09-22"
    s3.append(f'<circle cx="{X3(r["d"]):.1f}" cy="{y:.1f}" r="6" fill="{C["orange"]}" stroke="{C["surf"]}" stroke-width="2">'
              f'<title>{esc(r["label"])} 09-23: {f(r["last"])} TPS ({pct(r["d"])} {ref})</title></circle>')
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
t1 = ['<table class="num"><thead>', tr(["Run", "Package", "TPS mean", "sd, TPS", "p05, TPS", "slowest, TPS", "TTFT, ms", "prefill, tok/s", "samples"], True), "</thead><tbody>"]
t1.append(tr(["CI delphi-3bda 09-22", "2026.09.18-3faba6d0 (no kernels)", f(ci22["tps_mean"], 3), f(ci22["tps_sd"], 3), f(ci22["p05"]), f(ci22["tps_min"]),
              f"{ci22['ttft_mean_ms']:,.0f}", f"{ci22['prefill']:.1f} (Talos, not in Slack)", ci22["n"]]))
t1.append(tr(["<b>CI delphi-3bda 09-23</b>", "2026.09.23-5cf65b92 (kernels in)", f"<b>{f(ci23['tps_mean'], 3)}</b>", f(ci23["tps_sd"], 3), f(ci23["p05"]), f(ci23["tps_min"]),
              f"{ci23['ttft_mean_ms']:,.0f}", f"{ci23['prefill']:.1f}", ci23["n"]]))
t1.append(tr(["Ours 09-20, base arm", "2026.09.18-3faba6d0 (no kernels)", f(base_mean, 3), f"{min(b['tps_sd'] for b in BASE):.2f}&#8211;{max(b['tps_sd'] for b in BASE):.2f}",
              f(CELL["base_p05_mean"]), f(CELL["base_min_tps"]), f"{base_ttft:,.0f}", f"{base_pref:.1f}", "3 &#215; 320"]))
t1.append(tr(["Ours 09-20, canon arm", "3faba6d0 + AMX kernels", f(canon_mean, 3), f"{min(c['tps_sd'] for c in CANON):.2f}&#8211;{max(c['tps_sd'] for c in CANON):.2f}",
              f(CELL["canon_p05_mean"]), f(CELL["canon_min_tps"]), f"{canon_ttft:,.0f}", f"{canon_pref:.1f}", "3 &#215; 320"]))
t1.append(tr(["CI andoria-b1a3 09-22", "2026.09.18-3faba6d0", f(g22["tps_mean"], 3), f(g22["tps_sd"], 3), f(g22["p05"]), f(g22["tps_min"]),
              f"{g22['ttft_mean_ms']:,.0f}", f"{g22['prefill']:.1f} (Talos, not in Slack)", g22["n"]]))
t1.append(tr(["CI andoria-b1a3 09-23", "2026.09.23-5cf65b92", f(g23["tps_mean"], 3), f(g23["tps_sd"], 3), f(g23["p05"]), f(g23["tps_min"]),
              f"{g23['ttft_mean_ms']:,.0f}", f"{g23['prefill']:.1f}", g23["n"]]))
t1.append("</tbody></table>")
t1 = "\n".join(t1)

t2 = ['<table class="num"><thead>', tr(["Row (delphi-3bda)"] + [n[5:] if len(n) > 5 else n for n in NIGHTS] + ["09-23 vs range", "AMD, 09-22 to 09-23"], True), "</thead><tbody>"]
for r in H3:
    cells = [esc(r["label"])]
    for n in NIGHTS:
        v = HIST[n]["rows"].get(r["key"])
        cells.append(f(v[0]) if v else "&#8211;")
    cells[-1] = f"<b>{cells[-1]}</b>"
    if r["n_prior"] < 2:
        status = "1 prior night"
    elif r["outside"]:
        status = f"<b>{pct(r['beyond'])} {r['outside']}</b>"
    elif r["beyond"]:
        status = f"within 1 % ({pct(r['beyond'])} {'above' if r['beyond'] > 0 else 'below'})"
    else:
        status = "inside"
    cells.append(status)
    cells.append(pct(r["genoa"]) if r["genoa"] is not None else "&#8211;")
    t2.append(tr(cells))
pk = " | ".join(f"{n}: {HIST[n]['ver'][0]}" for n in NIGHTS)
t2.append("</tbody></table>")
t2 = "\n".join(t2)

q4 = by["ingested-qwen-3-4b-instruct-2507-tp4|u8"]; go = by["ingested-gpt-oss-120b-tp4|u8"]; l70 = by["llama-3.3-70b-instruct-good-tp4|u4"]
g4 = by["ingested-gemma-4-31b-it-tp2|u8"]; u8 = by["llama-3.1-8b-instruct-good-tp2|u8"]

# ---------- page ----------
ttft_drop_ci = (ci23["ttft_mean_ms"] / ci22["ttft_mean_ms"] - 1) * 100
near = [r for r in H3 if r["n_prior"] > 1 and abs(r["beyond"]) <= 0.3]
far = [r for r in H3 if r["outside"] and r["n_prior"] > 1]
spr = FACTS["same_pkg_range"]
c918 = {k: (v[1] / v[0] - 1) * 100 for k, v in FACTS["c918"].items()}
ks_diff = (FACTS["ks_off"] / FACTS["ks_clean"] - 1) * 100
slack23 = esc(FACTS["slack_0923"]).replace("~", "&#8776;")
first_pkg, last_prior_pkg = HIST[PRIOR[0]]["ver"][0], HIST[PRIOR[-1]]["ver"][0]

page = f"""<title>First Nightly With AMX Kernels</title>
<meta name="description" content="Checks the 2026-09-23 nightly AMX-benchmark row (32.5 TPS) against our measurements and finds the 2026-09-22 prefill rate.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600;700&display=swap">
<style>
:root {{ color-scheme: light; --ground:#f5f5f2; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --rule:#dcdbd3;
  --blue:{C["blue"]}; --orange:{C["orange"]}; --band:{C["band"]}; --code:#efeee9; }}
html, body {{ background: var(--ground); color: var(--ink); }}
body {{ font: 15.5px/1.6 "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; padding-inline: 16px; padding-block: 28px 64px; }}
.wrap {{ max-width: 1000px; margin: 0 auto; display: grid; gap: 18px; }}
.prose {{ max-width: 72ch; }}
h1 {{ font-size: 1.9rem; line-height: 1.2; margin: 0; text-wrap: balance; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.28rem; margin: 30px 0 0; padding-top: 16px; border-top: 1px solid var(--rule); text-wrap: balance; }}
h3 {{ font-size: 1.02rem; margin: 10px 0 0; }}
p, ul, ol {{ margin: 0; }}
ul, ol {{ padding-left: 1.25em; display: grid; gap: 6px; }}
.meta {{ color: var(--ink2); font-size: 0.9rem; }}
.short {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 14px 18px; display: grid; gap: 8px; max-width: 80ch; }}
.short b.lead {{ font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); }}
.verdict {{ font-size: 1.1rem; font-weight: 600; }}
code, .mono {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, monospace; font-size: 0.86em; }}
code {{ background: var(--code); padding: 1px 4px; border-radius: 3px; }}
.slack {{ font-family: "IBM Plex Mono", ui-monospace, Menlo, monospace; font-size: 0.82rem; background: var(--surface); border: 1px solid var(--rule);
  border-radius: 6px; padding: 10px 12px; overflow-x: auto; white-space: pre; }}
blockquote {{ margin: 0; padding: 10px 16px; border-left: 3px solid var(--orange); background: var(--surface); max-width: 80ch; }}
figure {{ margin: 0; display: grid; gap: 8px; }}
.chart {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; overflow-x: auto; }}
.chart svg {{ font-family: "IBM Plex Sans", system-ui, sans-serif; min-width: 640px; }}
figcaption {{ color: var(--ink2); font-size: 0.92rem; max-width: 82ch; }}
figcaption b {{ color: var(--ink); }}
.tw {{ overflow-x: auto; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.86rem; }}
th, td {{ padding: 6px 10px; border-bottom: 1px solid var(--rule); text-align: left; vertical-align: top; }}
th {{ font-weight: 600; color: var(--ink2); background: #f1f0eb; }}
table.num td {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
dl.words {{ display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; margin: 0; max-width: 92ch; }}
dl.words dt {{ font-weight: 600; }}
dl.words dd {{ margin: 0; color: var(--ink2); }}
@media (max-width: 640px) {{ dl.words {{ grid-template-columns: 1fr; }} dl.words dd {{ margin-bottom: 6px; }} }}
details {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 8px 12px; }}
summary {{ cursor: pointer; font-weight: 600; }}
summary:focus-visible, a:focus-visible {{ outline: 2px solid var(--blue); outline-offset: 2px; }}
a {{ color: #1f5fae; }}
.open {{ display: grid; gap: 14px; }}
.item {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 12px 16px; display: grid; gap: 8px; max-width: 88ch; }}
.item .tag {{ font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink2); font-weight: 600; }}
</style>

<div class="wrap">
<header style="display:grid;gap:6px">
<p class="meta">delphi-3bda nightly CI &#183; AMX benchmark row &#183; written 2026-09-23 from the 09-22 and 09-23 runs &#183; checked by an 8-agent verification pass</p>
<h1>First nightly with the AMX kernels: is 32.5 TPS what we expected?</h1>
</header>

<section class="short">
<b class="lead">Short version</b>
<p class="verdict">Yes: last night&#8217;s decode speed of 32.5 TPS (generated tokens per second per user) is what we expected once the AMX kernels (tron&#8217;s attention code for Intel&#8217;s matrix unit) reached the nightly package.</p>
<p>Our own test of the same setup, with only the AMX kernels changed, measured {f(canon_mean)} TPS, 0.9 % below the CI value.</p>
<p>The 09-22 prefill rate, which Slack did not print, was {ci22["prefill"]:.0f} tok/s (time to first token {ci22["ttft_mean_ms"]/1000:.1f} s) in the CI result store, Talos.</p>
</section>

<section style="display:grid;gap:10px">
<h2 style="border-top:0;margin-top:6px;padding-top:0">Words used here</h2>
<dl class="words">
<dt>CI</dt><dd>Continuous integration: here, the nightly build-and-test run on the two CI machines. It posts its report to Slack.</dd>
<dt>tron, rinzler</dt><dd>tron is the inference program under test. rinzler is the production server: the server binary inside the tron package.</dd>
<dt>token, prefill, decode</dt><dd>A token is a word piece, the unit the model reads and writes. Prefill is the phase that reads the whole prompt before the first output token. Decode then generates output tokens one at a time.</dd>
<dt>TPS</dt><dd>Decode speed: generated tokens per second for one user. The CI harness measures it between generated tokens 896 and 1024 of each request. One sample is the TPS of one finished request, read from its &#8220;Done&#8221; line in the run log. This row has 320 samples per night.</dd>
<dt>TTFT</dt><dd>Time to first token: the time from sending a request to receiving its first generated token, in milliseconds (ms). With several users per engine it includes the wait behind other users&#8217; prompts.</dd>
<dt>prefill rate (prefill&#8776;)</dt><dd>Prompt length divided by mean TTFT, in tokens per second (tok/s). The CI computes it on the client. It is not a server-side timing of prefill.</dd>
<dt>row, engine</dt><dd>A row is one test (model, card count, users, prompt length). It prints as one line in Slack. An engine is one rinzler instance with its own cards. A machine runs 4 engines at tp2 and 2 engines at tp4.</dd>
<dt>tp2, tp4</dt><dd>The model is split over 2 or 4 accelerator cards (tensor parallel).</dd>
<dt>@32u per machine</dt><dd>32 users in total. For this tp2 row that is 8 users per engine.</dd>
<dt>AMX</dt><dd>Advanced Matrix Extensions, a CPU instruction set: the matrix unit in Intel Xeon CPUs, such as the Xeon 6962P in delphi-3bda.</dd>
<dt>attention, AMX kernels</dt><dd>Attention is the model step that compares each new token with all earlier tokens. The AMX kernels are tron&#8217;s attention code that uses AMX. They are compiled in only when the build option <code>TRON_AMX_DISPATCH</code> is ON.</dd>
<dt>PR, .deb</dt><dd>PR is a pull request, one change merged into tron main (a merge). The .deb is the Debian install package the nightly installs. PR #4505 turned the AMX build option on for it.</dd>
<dt>no-kernel / kernels-in package</dt><dd>A tron package built without / with the AMX kernels.</dd>
<dt>kill switch</dt><dd>The environment variable <code>TRON_AMX_DISABLE</code>. It turns the AMX kernels off at run time in a kernels-in build.</dd>
<dt>canon, arm, pass</dt><dd>canon is our kernels-in build: tron main 3faba6d0 plus the AMX build option, built on 09-18 and measured on 09-20. An arm is one build in our comparison (the base arm is the no-kernel nightly package). A pass is one full run of the test (320 samples).</dd>
<dt>FPGA attention</dt><dd>Attention computed on the accelerator card&#8217;s programmable chip (FPGA) instead of the CPU. The variable <code>USE_HW_ATTN</code> selects FPGA or CPU attention.</dd>
<dt>delphi-3bda, andoria-b1a3</dt><dd>The two CI machines: Intel Xeon 6962P (has AMX) and AMD Genoa (no AMX unit).</dd>
<dt>p05, sd</dt><dd>p05 is the 5th percentile of the per-user TPS samples (95 % of samples are faster). sd is the population standard deviation of those samples.</dd>
<dt>systems_test, Talos, publish-deb, platformd</dt><dd>systems_test is the repository with the CI harness. Talos is the CI result store, and its bot posts the nightly report to Slack. publish-deb is the tron workflow that builds the nightly package at 01:35 UTC. platformd is the service that starts and stops the rinzler engines.</dd>
</dl>
</section>

<h2>1. Is 32.5 TPS what we expected?</h2>
<p class="prose">Chart 1 places the two nights of the CI row next to our 09-20 campaign of the same test (32 users, prompt 4096 tokens, 1536 generated tokens). The shaded band is the gain range we wrote down before our campaign, +11 to +21 % [CI-test/status/llama-3.1-8b-8u-4k-plan.md, section 7]. The chart applies it to the no-kernel mean that our campaign then measured.</p>
<figure>
<div class="chart">{svg1}</div>
<figcaption><b>The Intel rows moved by the expected amount.</b> On the AMD machine, the same package change moved this row {pct(g_gain)}. So changes that act on both platforms did not move it. AMD cannot show changes that act only on Intel (section 4). Blue dot = package without AMX kernels, orange dot = package with AMX kernels. Hover a dot for its source.</figcaption>
</figure>
<ul class="prose">
<li>The CI value is {f(ci23["tps_mean"], 3)} TPS, the mean of {ci23["n"]} samples. Slack rounds it to 32.5.</li>
<li>The CI gain from 09-22 to 09-23 is {pct(ci_gain)}. It mixes the AMX kernels with 31 other tron merges that entered the same package.</li>
<li>Our campaign changed only the AMX kernels and measured {pct(our_gain)}. Each of its three pass pairs gave {min(CELL["gain_pct_per_pass"]):+.1f} to {max(CELL["gain_pct_per_pass"]):+.1f} %.</li>
<li>The CI value is {ci23["tps_mean"] - canon_mean:.2f} TPS ({pct(ci_vs_canon)}) above our canon mean of {f(canon_mean, 3)} TPS. Our three canon passes ranged from {f(canon_lo)} to {f(canon_hi)} TPS. The CI value is above all three.</li>
<li>Our passes ran in one session. Across nights, the tp2 rows moved {spr[0]} to {spr[1]} % while the package stayed the same (09-18 to 09-22). So a 0.9 % gap is within normal night-to-night movement (section 5, item A).</li>
<li>TTFT is {ci23["ttft_mean_ms"]:,.0f} ms. That is {ttft_vs_canon:.1f} % longer than our canon value ({canon_ttft:,.0f} ms). My estimate on 09-22 was {FACTS["ttft_est"][0]} to {FACTS["ttft_est"][1]} s (est.). The CI value is {ci23["ttft_mean_ms"]/1000 - FACTS["ttft_est"][1]:.2f} s above the top of that range.</li>
<li>The row still has no threshold. &#8220;(placeholder threshold)&#8221; is only a display label. We proposed thresholds of mean {thr[0]} TPS, p05 {thr[1]} TPS and slowest sample {thr[2]} TPS [CI-test/status/llama-3.1-8b.html, section 9.4]. This night passes them by {ci23["tps_mean"] - thr[0]:.2f}, {ci23["p05"] - thr[1]:.2f} and {ci23["tps_min"] - thr[2]:.2f} TPS.</li>
</ul>
<div class="tw">{t1}</div>
<ul class="meta prose">
<li>CI rows use all 320 &#8220;Done&#8221; samples of the row in the GitHub run log [amx_row.py].</li>
<li>Our rows come from our campaign summary [exec/results/l8b-8u4k-20260920/summary.json].</li>
<li>For our rows, the sd cell shows the lowest and highest per-pass sd. p05 is the mean of the three per-pass values. Slowest is the lowest single sample over all passes.</li>
<li>Prefill = 4096 tokens / mean TTFT in every row.</li>
</ul>

<h2>2. The prefill rate of the 09-22 row</h2>
<p class="prose">The 09-22 row was measured like every other row. Only its Slack line was shorter. These are the two lines as posted (Slack emoji and bold or italic marks removed):</p>
<div class="slack">09-22: {esc(FACTS["slack_0922"])}
09-23: {slack23}</div>
<h3>The value</h3>
<ul class="prose">
<li>Talos holds it. For the 09-22 run, Talos session {FACTS["talos_0922"][:8]} stores a prefill rate of <b>{FACTS["talos_0922_prefill"]} tok/s</b> and a mean TTFT of 18,646 ms [talos:5000/sessions/{FACTS["talos_0922"]}].</li>
<li>Its summary line reads &#8220;{esc(FACTS["talos_0922_line"])}&#8221;. &#8220;1% cached&#8221; means that {FACTS["talos_0922_cache_pct"]} % of the prompt tokens were reused from earlier requests.</li>
<li>Our own computation from the 320 log samples gives the same value: 4096 tokens / {ci22["ttft_rounded_ms"]/1000:.3f} s = {ci22["prefill"]:.1f} tok/s.</li>
<li>In the Slack format of 09-23, the 09-22 line would have read: &#8220;... (AMX benchmark): 28.3 TPS (placeholder threshold), prefill&#8776;{ci22["prefill"]:.0f} tok/s, TTFT {ci22["ttft_rounded_ms"]}ms (@4.1k prompt)&#8221;.</li>
<li>The AMD row of 09-22 also lacked it. Talos holds {g22["prefill"]:.0f} tok/s with TTFT {g22["ttft_rounded_ms"]:,} ms [session {FACTS["talos_0922_genoa"][:8]}].</li>
</ul>
<h3>Why Slack did not print it</h3>
<ul class="prose">
<li>The 09-22 nightly ran systems_test commit {FACTS["st_head_0922"]}. In that version, a labelled benchmark row with no threshold got a short line with the TPS value only [testlib/results.py:486-491]. The AMX row is such a row: its label is &#8220;AMX benchmark&#8221;, and it has no threshold.</li>
<li>The gemma-4 row printed prefill and TTFT that same night. It has a placeholder threshold of 1.00 TPS [scripts/system_ci.py]. So it took the placeholder branch. That branch already printed prefill and TTFT.</li>
<li>PR #227 (&#8220;{esc(FACTS["pr227_title"])}&#8221;) changed the short line to the placeholder format with prefill and TTFT. It merged at {FACTS["pr227_merged"]}, after the 09-22 run. The 09-23 run used commit {FACTS["st_head_0923"]}, which includes it.</li>
<li>The prefill formula is the same in both commits [scripts/perf.py:396-397]. The harness sends the value to Talos with each result. Only the Slack line left it out.</li>
<li>The other systems_test changes between the two nights do not touch the measurement code. <code>scripts/perf.py</code>, <code>testlib/tps.py</code> and <code>testlib/perf_metrics.py</code> are unchanged [git diff {FACTS["st_head_0922"]} {FACTS["st_head_0923"]}].</li>
</ul>
<h3>Check of the method</h3>
<ul class="prose">
<li>Over the 09-23 log, the same computation gives TTFT {ci23["ttft_rounded_ms"]:,} ms and {ci23["prefill"]:.0f} tok/s. Slack printed the same numbers.</li>
<li>For the 09-23 AMD row it gives {g23["ttft_rounded_ms"]:,} ms and {g23["prefill"]:.0f} tok/s. Slack printed the same numbers.</li>
<li>For 09-23, the mean per-sample TTFT matches the Slack TTFT on all 13 rows of both machines.</li>
</ul>
<h3>The two-night prefill change</h3>
<ul class="prose">
<li>From 09-22 to 09-23 the CI prefill rate rose {pct(pref_gain_ci)} ({ci22["prefill"]:.1f} to {ci23["prefill"]:.1f} tok/s).</li>
<li>This is the same fact as a {abs(ttft_drop_ci):.1f} % drop in mean TTFT ({ci22["ttft_mean_ms"]/1000:.2f} s to {ci23["ttft_mean_ms"]/1000:.2f} s). It is a TTFT measurement.</li>
<li>TTFT includes the wait behind other users&#8217; prompts. So the rate is what one user sees. It is not the engine&#8217;s total prompt throughput.</li>
<li>The two nights also differ by 31 other tron merges. Our test of the same setup changed only the AMX kernels. It measured {pct(pref_gain_ours)} ({base_pref:.1f} to {canon_pref:.1f} tok/s).</li>
</ul>
<p class="prose">A sentence that stays inside the data:</p>
<blockquote>In the nightly CI AMX benchmark (llama-3.1-8b tp2, 32 users, prompt 4096), the TTFT-derived prefill rate rose 61 % from 09-22 to 09-23 ({ci22["prefill"]:.0f} to {ci23["prefill"]:.0f} tok/s, TTFT {ci22["ttft_mean_ms"]/1000:.1f} to {ci23["ttft_mean_ms"]/1000:.1f} s). The AMX kernels entered the package that night. Our A/B test of the same setup, with only the AMX kernels changed, measured +66 %.</blockquote>
<figure>
<div class="chart">{svg2}</div>
<figcaption><b>The prefill rate rose {pct(pref_gain_ci)} in CI and {pct(pref_gain_ours)} in our campaign.</b> The CI prefill gain is smaller than ours, while its decode gain is larger (section 5, item B).</figcaption>
</figure>

<h2>3. Did the nightly package really contain the AMX kernels?</h2>
<p class="prose">Yes. Each step below was checked on 2026-09-23. Only the last step, proof that AMX ran during the row, is missing.</p>
<div class="tw"><table>
<thead>{tr(["Step", "Evidence", "Source"], True)}</thead><tbody>
{tr(["The build switch merged", f"PR #4505 merged at {FACTS['pr4505_merged']} (merge commit {FACTS['pr4505_merge']}).", "<code>gh pr view 4505</code>"])}
{tr(["The package was built after it, with the kernels", f"publish-deb run {FACTS['deb_run']} started {FACTS['deb_start']} and succeeded on main {FACTS['deb_head']}. That commit contains {FACTS['pr4505_merge']}. The build log compiles <code>kernels/amx_attn.cpp</code>.", f"<code>gh run list</code>, <code>git merge-base --is-ancestor</code>, build log line {FACTS['deb_amx_line']}"])}
{tr(["Both CI machines installed it", f"delphi-3bda: &#8220;Setting up tron (2026.09.23-5cf65b92)&#8221; at {FACTS['install_time']}. andoria-b1a3: the same line at {FACTS['genoa_install_time']}. Both Slack reports name this version.", f"run logs, lines {FACTS['install_line']} and {FACTS['genoa_install_line']}"])}
{tr(["The installed server has the kernels", f"At {FACTS['check_time']}, dpkg (the Debian package tool) reported 2026.09.23-5cf65b92. <code>/opt/positron/bin/rinzler</code> ({FACTS['rinzler_bytes']} bytes) holds {FACTS['amx_insns']} AMX instructions of the kinds tdpbf16ps, tileloadd, tilestored, ldtilecfg and tilerelease. Its {FACTS['tilezero']} tilezero instructions are not in that count ({FACTS['amx_insns_total']} AMX instructions in total). It holds the kill-switch text once. Our canon build gives 86 by the same count. No-kernel packages give 0.", f"<code>objdump -d</code> and <code>strings</code> on delphi-3bda (read-only). A verifier repeated both on the rinzler from the build artifact. Canon: {FACTS['canon_src']}"])}
{tr(["No setting found that turns AMX off", "At 15:32 UTC, about 11 h after the row ran, <code>/opt/positron/user/config.env</code> was empty (0 bytes). <code>/etc/rinzler/instance-*.env</code> had no <code>TRON_AMX</code> line and no <code>USE_HW_ATTN</code> line. This is the state after the run, not during it. Indirect support: with the kill switch on, the row would read about 28 TPS, not 32.5.", "<code>grep</code> on delphi-3bda"])}
{tr(["Run-time proof", "Not available. The CI does not read the AMX busy-cycle counter (EXE.AMX_BUSY). The evidence that AMX ran is indirect: the gain matches ours, and the AMD machine did not move.", "Insufficient data: read the counter, or <code>/proc/&lt;pid&gt;/environ</code>, on one engine process during this row"])}
</tbody></table></div>

<h2>4. The rest of the nightly</h2>
<p class="prose">Chart 3 compares every delphi-3bda row of 09-23 with its range over the previous seven nights. All seven ran packages without AMX kernels ({esc(first_pkg)} to {esc(last_prior_pkg)}). Rows more than 1 % outside their range are bold and labelled.</p>
<figure>
<div class="chart">{svg3}</div>
<figcaption><b>{len(near)} of {len(H3)} rows stayed inside their range or within 0.3 % of it.</b> Three tp4 rows rose above it, and gemma-4 fell below it. The AMX row has only one earlier night.</figcaption>
</figure>
<ul class="prose">
<li>llama-3.1-8b tp2, 8 users: {f(u8["last"])} TPS, {pct(u8["beyond"])} above its highest earlier night. At this load (2 users per engine, prompt 1024) our campaign measured {pct(FACTS["u8_ref_gain"])} for AMX [exec/results/l8b-levers-20260919]. That gain was smaller than our pass-to-pass variation. So this small rise matches what we measured.</li>
<li>qwen-3-4b tp4: {f(q4["last"])} TPS against {f(q4["pmin"])} to {f(q4["pmax"])} before ({pct(q4["beyond"])} above the highest night). On AMD the same package change moved it {pct(q4["genoa"])}.</li>
<li>gpt-oss-120b tp4: {f(go["last"])} TPS against {f(go["pmin"])} to {f(go["pmax"])} ({pct(go["beyond"])} above). AMD: {pct(go["genoa"])}.</li>
<li>llama-3.3-70b tp4: {f(l70["last"])} TPS against {f(l70["pmin"])} to {f(l70["pmax"])} ({pct(l70["beyond"])} above). AMD: {pct(l70["genoa"])}.</li>
<li>gemma-4-31b tp2: {f(g4["last"])} TPS against {f(g4["pmin"])} to {f(g4["pmax"])} ({pct(g4["beyond"])} below). AMD: {pct(g4["genoa"])}.</li>
<li>qwen-3-4b and gpt-oss-120b run FPGA attention in the nightly. The llama and mixtral rows run CPU attention.</li>
<li>Our own light compile check ran on delphi-3bda during the nightly (2 CPUs, lowest priority). It started after 05:00 UTC (est.) and last wrote its log at {FACTS["syntax_log_end"]}. So it could overlap only the mixtral row (to 05:01 UTC) and the qwen-2.5-32b row (05:02 to 05:10 UTC). Both stayed inside their range. It did not overlap the AMX row (04:09 to 04:18 UTC).</li>
</ul>
<details><summary>All rows, all eight nights (TPS mean over the &#8220;Done&#8221; samples)</summary>
<div class="tw" style="margin-top:8px">{t2}</div>
<p class="meta" style="margin-top:6px">Packages: {esc(pk)}.</p>
</details>

<h2>5. What is not explained yet</h2>
<div class="open">
<div class="item"><span class="tag">Open item A</span>
<p><b>The CI kernels-in value is {pct(ci_vs_canon)} above ours.</b> On 09-22 the no-kernel values agreed to {pct(ci_vs_base_0922, 2)} with the same binary. So the harness setup, the prompt set and platformd 0.11 did not change the no-kernel value.</p>
<p>The two kernels-in builds differ in three ways:</p>
<ul>
<li>Code: CI ran main {FACTS["deb_head"]}, which is {FACTS["merges_after_canon"]} merges after 3faba6d0. One of them is #4505, the same build switch as our canon build. That leaves 31 other merges.</li>
<li>Builder: we built canon with <code>make deb</code> on delphi-3bda. CI built its package in the publish-deb job.</li>
<li>Day: our passes ran on 09-20, the CI row on 09-23.</li>
</ul>
<p>Hypotheses:</p>
<ol>
<li>Normal night-to-night movement. On one unchanged package the tp2 rows moved {spr[0]} to {spr[1]} %.</li>
<li>One of the 31 merges. The first candidate is #4534 (&#8220;Disable wait statistics by default&#8221;). It removed two shared counters from every timed wait, and its PR reports {FACTS["pr4534_gain"]} decode per user on gpt-oss-20b. Next come the shared KV cache (attention memory) and scheduler edits of #4455 and #4456, and #4205 (&#8220;cmake: compile model specializations per architecture&#8221;).</li>
<li>The builder.</li>
</ol>
<p>#4258 and #4516 are not on this row&#8217;s path. #4258 changes only the FPGA attention join, and llama-3.1-8b runs CPU attention. #4516 only refreshes CI unit-test timing data.</p>
<p>Measurement that decides it: interleaved passes on delphi-3bda with our harness, with these packages:</p>
<ul>
<li>the nightly package 2026.09.23-5cf65b92 and our canon package (these two alone decide hypothesis 1 against hypotheses 2 and 3),</li>
<li>our own <code>make deb</code> of {FACTS["deb_head"]} (separates the builder from the code),</li>
<li>the same build with <code>-DTRON_MWAIT_STATS=ON</code> (isolates #4534),</li>
<li>the nightly package with the kill switch (tests the AMX part).</li>
</ul>
</div>
<div class="item"><span class="tag">Open item B</span>
<p><b>CI TTFT is {ttft_vs_canon:.1f} % longer than ours, while CI TPS is {ci_vs_canon:.1f} % higher.</b> So in CI the first token comes later, and decode runs faster. On 09-22, CI TTFT was {abs(ttft_vs_base_0922):.1f} % shorter than our no-kernel value.</p>
<p>The cause is unknown. The passes in item A also record TTFT. They would show whether the newer code makes decode faster and prefill slower.</p>
</div>
<div class="item"><span class="tag">Open item C</span>
<p><b>Three tp4 rows rose on delphi-3bda only.</b> The cause is not determined.</p>
<p>Hypotheses:</p>
<ol>
<li>The AMX kernels. This is plausible only for llama-3.3-70b tp4, which runs CPU attention. qwen-3-4b and gpt-oss-120b run FPGA attention, where AMX covers only the CPU share. In our 09-18 CI-layout run, the same kernels on 3faba6d0 did not raise these rows: {pct(c918["qwen tp4"])}, {pct(c918["gpt-oss tp4"])} and {pct(c918["70b tp4"])} (single passes, inside each row&#8217;s normal spread) [exec/results/canon-ci-20260918, ci-mimic-20260918].</li>
<li>#4534 (wait counters removed). Its PR measured {FACTS["pr4534_gain"]} decode per user on gpt-oss-20b on four cards. On AMD the same package moved the three rows {pct(q4["genoa"])}, {pct(go["genoa"])} and {pct(l70["genoa"])}. A larger effect on Intel would need a platform-specific reason. That is untested.</li>
<li>Another merge: #4258 (FPGA attention join, used by the two FPGA-attention rows), the model code-generator merges #4449, #4450, #4451, #4475, #4476, #4479, #4159 and #4302, #4455 and #4456 (sliding-window KV, used by gpt-oss-120b), or #4531 (expert placement, gpt-oss-120b).</li>
</ol>
<p>Measurements that decide it:</p>
<ul>
<li>For hypothesis 1: run the three rows on the 09-23 package with and without the kill switch, and read EXE.AMX_BUSY per engine. In our last test on the canonical-kernel code, the kill switch ran at no-kernel speed: {FACTS["ks_off"]} vs {FACTS["ks_clean"]:.3f} tok/s per user ({pct(ks_diff)}), 16 requests each (2026-09-09, qwen-3-4b tp2, 8 users, prompt 8192) [exec/results/qwen8u8k-pr1-half-20260909T1704.txt]. So no separate no-kernel build is needed.</li>
<li>For hypotheses 2 and 3: rerun qwen-3-4b tp4 on the 09-22 and 09-23 packages with <code>USE_HW_ATTN=0</code> (CPU attention). If the rise disappears, the FPGA-path change (#4258) carries it. If it stays, test a <code>TRON_MWAIT_STATS=ON</code> build of {FACTS["deb_head"]} for #4534.</li>
</ul>
</div>
</div>

<h2>6. What to watch on the next nights</h2>
<ul class="prose">
<li>For this row, expect about 32.2 to 32.5 TPS, TTFT about 11.5 s and prefill about 354 tok/s (est.).</li>
<li>A fall toward 28.3 TPS means the kernels are missing or disabled. Then check the package version and that <code>strings rinzler | grep -c -x TRON_AMX_DISABLE</code> prints 1.</li>
<li>When this row gets its first threshold, calibrate it from 09-23 onward. The 09-22 night ran the no-kernel package.</li>
<li>Watch whether the three tp4 rises persist.</li>
</ul>

<h2>7. Sources</h2>
<ul class="prose">
<li>systems_test runs (GitHub Actions): delphi-3bda {FACTS["run_0922"]} (09-22) and {FACTS["run_0923"]} (09-23), andoria-b1a3 {FACTS["genoa_run_0922"]} and {FACTS["genoa_run_0923"]}, and six earlier delphi-3bda nights for chart 3. Logs saved in exec/ci-amx-row-20260923/.</li>
<li>Talos sessions (result store): delphi-3bda 09-22 {FACTS["talos_0922"]}, andoria-b1a3 09-22 {FACTS["talos_0922_genoa"]}. Saved JSON in the same folder.</li>
<li>Slack #ci-cd-notifications: the nightly reports of 2026-09-22 (06:20 PDT) and 2026-09-23 (06:05 PDT).</li>
<li>Scripts in exec/ci-amx-row-20260923/: amx_row.py (row statistics, p05 by linear interpolation as in systems_test), all_rows.py (every row), gen_page.py (this page).</li>
<li>Our campaign: exec/results/l8b-8u4k-20260920/summary.json, plan CI-test/status/llama-3.1-8b-8u-4k-plan.md, report CI-test/status/llama-3.1-8b.html.</li>
<li>Previous page: CI-test/status/first-CI-AMX-row-20260922.html (the 09-22 row against our no-kernel value).</li>
<li>systems_test code: <code>scripts/perf.py:396-397</code> (TTFT rounding and prefill), <code>testlib/results.py</code> (Slack line), commit 18c60c6 in PR #227.</li>
<li>Verification: workflow wf_0c541e28-684 (8 agents). 69 of 84 fact items were upheld as written. The 12 corrections and 2 refutations are applied here. One item (the engine environment during the row) stayed unverifiable, as section 3 says. The English review is applied as well [verify-wf_0c541e28-684.json].</li>
</ul>
</div>
"""
for bad in ("≈", "→", "—", "–", "·"):
    assert bad not in page, bad
page.encode("ascii")  # raises if any non-ASCII character slipped in
open(OUT, "w", encoding="ascii").write(page)
print("wrote", OUT, len(page), "bytes")
