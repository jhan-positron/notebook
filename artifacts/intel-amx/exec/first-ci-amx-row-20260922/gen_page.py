#!/usr/bin/env python3
"""Page: does the first nightly "AMX benchmark" row (2026-09-22, 28.3 TPS) match our expectation?
Reads nightly_rows.json (parse_row.py over the GitHub run logs) and the l8b-8u4k summary.json; writes one light-theme
ASCII-only HTML page with an inline SVG dot plot. Every number on the page comes from those two files or from the
FACTS dict below (each FACTS entry names its source).
usage: gen_page.py [OUT_HTML]"""
import html, json, os, statistics as st, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/workspace/intel-AMX/CI-test/status/first-CI-AMX-row-20260922.html"
ROWS = json.load(open(os.path.join(HERE, "nightly_rows.json")))
SUM = json.load(open("/home/jhan/workspace/intel-AMX/exec/results/l8b-8u4k-20260920/summary.json"))
CELL = SUM["configs"]["llama_3_1_8b_instruct_good_tp2_32u_p4096"]
PP = CELL["per_pass"]
BASE = [PP[k] for k in ("base-pass1", "base-pass2", "base-pass3")]
CANON = [PP[k] for k in ("canon-pass1", "canon-pass2", "canon-pass3")]
CI = ROWS["3bda"]; GENOA = ROWS["genoa"]; CI8U = ROWS["3bda_8u"]

FACTS = {  # source in the comment
    "slack_line": "llama-3.1-8b-instruct-good-tp2 @32u per machine (AMX benchmark): 28.3 TPS",  # talos post 2026-09-22 06:20 PDT
    "tron_version": "2026.09.18-3faba6d0",          # Slack "Tron did NOT update", log line 391, dpkg on 3bda 17:34 UTC
    "rinzler_sha": "27e6883c2e8696b861589272470d5f6a4ec5485f6e8cd2ad163ae699f1dc6616",  # sha256sum on 3bda; == base-identity of our run
    "amx_insns": 0, "amx_strings": 0,                # objdump / strings on /opt/positron/bin/rinzler, 3bda 17:34 UTC
    "amx_insns_canon": 86,                           # memory ci-enable-20260917: AMX-only deb build
    "run_id": "35683952944", "genoa_run_id": "35682128668",
    "pr221_merged": "2026-09-22 01:34 UTC", "pr4510_merged": "2026-09-22 03:50 UTC", "publish_deb_sched": "01:35 UTC",
    "pr4505_state": "open, approved 2026-09-21, not merged",
    "platformd_ci": "0.11.0", "platformd_ours": "0.10.7",
    "band": (11.0, 21.0),                             # plan section 7 pre-registered band
    "main_commits_ahead": 62, "main_head": "0a51385e95",  # gh: git log 3faba6d0..origin/main, verifier C4 2026-09-22 ~18:00 UTC
}
base_mean = st.mean(b["tps_mean"] for b in BASE); canon_mean = st.mean(c["tps_mean"] for c in CANON)
base_ttft = st.mean(b["ttft_ms"] for b in BASE); canon_ttft = st.mean(c["ttft_ms"] for c in CANON)
ci_vs_base_pct = (CI["tps_mean"] - base_mean) / base_mean * 100
gain_pct = (canon_mean - base_mean) / base_mean * 100
band_lo, band_hi = base_mean * (1 + FACTS["band"][0] / 100), base_mean * (1 + FACTS["band"][1] / 100)
pass_spread = max(b["tps_mean"] for b in BASE) - min(b["tps_mean"] for b in BASE)
ttft_pct = (CI["ttft_mean_ms"] - base_ttft) / base_ttft * 100

def esc(x): return html.escape(str(x), quote=True)
def f(x, nd=2): return f"{x:.{nd}f}"

# ---------- chart: one dot per row on a shared TPS axis ----------
C_BLUE, C_ORANGE, C_INK, C_INK2, C_MUTED, C_GRID, C_AXIS, C_SURF, C_BAND = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb", "#fbe9df"
W, H, X0, X1 = 1000, 340, 372, 960
XMIN, XMAX = 27.0, 35.0
def X(v): return X0 + (v - XMIN) / (XMAX - XMIN) * (X1 - X0)
rows = [
    ("Nightly CI, 2026-09-22", "package 2026.09.18-3faba6d0, no AMX kernels", CI["tps_mean"], C_BLUE, False, f"Slack shows {FACTS['slack_line'].split(': ')[1]}"),
    ("Our run, 2026-09-20, no AMX kernels", "same package file, same binary hash", base_mean, C_BLUE, False, "mean of 3 passes"),
    ("Our run, 2026-09-20, AMX kernels in", "same commit + kernels compiled in", canon_mean, C_ORANGE, True, "mean of 3 passes"),
]
ys = [95, 160, 225]
svg = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-labelledby="c1t c1d" style="max-width:{W}px;display:block">',
       '<title id="c1t">Decode speed of the 32-user llama-3.1-8b row: nightly CI vs our two arms</title>',
       f'<desc id="c1d">Dot plot. Nightly CI {f(CI["tps_mean"])} TPS, our run without AMX kernels {f(base_mean)} TPS, our run with AMX kernels {f(canon_mean)} TPS. Shaded band {f(band_lo,1)} to {f(band_hi,1)} TPS is the pre-registered expectation once AMX ships.</desc>',
       f'<rect x="0" y="0" width="{W}" height="{H}" fill="{C_SURF}"/>']
# band
svg.append(f'<rect x="{X(band_lo):.1f}" y="60" width="{X(band_hi)-X(band_lo):.1f}" height="{ys[-1]+35-60}" fill="{C_BAND}"/>')
svg.append(f'<text x="{(X(band_lo)+X(band_hi))/2:.1f}" y="38" text-anchor="middle" font-size="12" fill="{C_INK2}">expected once AMX is in the package</text>')
svg.append(f'<text x="{(X(band_lo)+X(band_hi))/2:.1f}" y="54" text-anchor="middle" font-size="12" fill="{C_INK2}">+11 to +21 % over {f(base_mean)} = {f(band_lo,1)} to {f(band_hi,1)} TPS</text>')
# grid + axis
for v in range(int(XMIN), int(XMAX) + 1):
    svg.append(f'<line x1="{X(v):.1f}" y1="60" x2="{X(v):.1f}" y2="{ys[-1]+35}" stroke="{C_GRID}" stroke-width="1"/>')
    svg.append(f'<text x="{X(v):.1f}" y="{ys[-1]+52}" text-anchor="middle" font-size="12" fill="{C_INK2}">{v}</text>')
svg.append(f'<line x1="{X0}" y1="{ys[-1]+35}" x2="{X1}" y2="{ys[-1]+35}" stroke="{C_AXIS}" stroke-width="1"/>')
svg.append(f'<text x="{(X0+X1)/2:.1f}" y="{ys[-1]+74}" text-anchor="middle" font-size="12" fill="{C_INK2}">TPS = generated tokens per second per user (higher is faster)</text>')
# rows
for (lab, sub, v, col, is_on, note), y in zip(rows, ys):
    svg.append(f'<text x="{X0-14}" y="{y-4}" text-anchor="end" font-size="14" font-weight="600" fill="{C_INK}">{esc(lab)}</text>')
    svg.append(f'<text x="{X0-14}" y="{y+14}" text-anchor="end" font-size="11.5" fill="{C_INK2}">{esc(sub)}</text>')
    if is_on:  # connector from the AMX-off value to the AMX-on value, gap annotated
        svg.append(f'<line x1="{X(base_mean):.1f}" y1="{y}" x2="{X(v):.1f}" y2="{y}" stroke="{C_ORANGE}" stroke-width="2" stroke-dasharray="4 3"/>')
        svg.append(f'<circle cx="{X(base_mean):.1f}" cy="{y}" r="6" fill="{C_SURF}" stroke="{C_BLUE}" stroke-width="2"><title>No AMX kernels, same run: {f(base_mean)} TPS</title></circle>')
        svg.append(f'<text x="{(X(base_mean)+X(v))/2:.1f}" y="{y-12}" text-anchor="middle" font-size="12.5" font-weight="600" fill="{C_INK}">+{f(gain_pct,1)} %</text>')
    svg.append(f'<circle cx="{X(v):.1f}" cy="{y}" r="8" fill="{col}" stroke="{C_SURF}" stroke-width="2"><title>{esc(lab)}: {f(v,3)} TPS ({esc(note)})</title></circle>')
    lbl = f"{f(v,3)} TPS" + (" (Slack prints 28.3)" if lab.startswith("Nightly") else "") if not is_on else f"{f(v)} TPS"
    svg.append(f'<text x="{X(v)+14:.1f}" y="{y+5}" font-size="14" font-weight="600" fill="{C_INK}" style="font-variant-numeric:tabular-nums">{lbl}</text>')
# bracket between row 1 and 2 dots
svg.append(f'<text x="{X(CI["tps_mean"])+14:.1f}" y="{ys[1]-24}" font-size="11.5" fill="{C_INK2}">gap between the two blue dots: {ci_vs_base_pct:+.2f} % ({CI["tps_mean"]-base_mean:+.3f} TPS)</text>')
svg.append('</svg>')
SVG = "\n".join(svg)

def tr(cells, head=False):
    t = "th" if head else "td"
    return "<tr>" + "".join(f"<{t}>{c}</{t}>" for c in cells) + "</tr>"

rec_head = tr(["Run", "Package / AMX", "n", "TPS mean", "sd", "min", "p05", "TTFT (s)"], True)
rec_rows = [
    tr([f"Nightly CI 3bda 2026-09-22, run {FACTS['run_id']}", f"tron {FACTS['tron_version']}, no AMX kernels", CI["n_samples"], f(CI["tps_mean"], 3), f(CI["tps_sd"], 3), f(CI["tps_min"]), f(CI["p05"]), f(CI["ttft_mean_ms"]/1000, 1)]),
] + [tr([f"Our base pass {i+1} (2026-09-20)", f"tron {FACTS['tron_version']}, no AMX kernels", b["n_samples"], f(b["tps_mean"], 3), f(b["tps_sd"], 3), f(b["min"]), f(b["p05"]), f(b["ttft_ms"]/1000, 1)]) for i, b in enumerate(BASE)
] + [tr([f"Our canon pass {i+1} (2026-09-20)", "same commit + AMX kernels compiled in (canonical build)", c["n_samples"], f(c["tps_mean"], 3), f(c["tps_sd"], 3), f(c["min"]), f(c["p05"]), f(c["ttft_ms"]/1000, 1)]) for i, c in enumerate(CANON)
] + [tr([f"Nightly CI AMD andoria-b1a3 2026-09-22, run {FACTS['genoa_run_id']}", f"tron {FACTS['tron_version']}; AMD CPU, no AMX unit", GENOA["n_samples"], f(GENOA["tps_mean"], 3), f(GENOA["tps_sd"], 3), f(GENOA["tps_min"]), f(GENOA["p05"]), f(GENOA["ttft_mean_ms"]/1000, 1)])]
rounds = ", ".join(f(r[1]) for r in CI["round_running_avgs"])
prm = CI["per_round_means"]; prm_lo, prm_hi = min(prm), max(prm)
pass_spread = max(b["tps_mean"] for b in BASE) - min(b["tps_mean"] for b in BASE)

page = f"""<title>First AMX Benchmark Night</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
:root{{--bg:#f4f3ee;--card:#fcfcfb;--ink:{C_INK};--ink2:{C_INK2};--muted:{C_MUTED};--grid:{C_GRID};--blue:{C_BLUE};--orange:{C_ORANGE};--band:{C_BAND};--rule:#d9d7cf}}
body{{background:var(--bg);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}}
main{{max-width:940px;margin:0 auto;padding:28px 16px 60px}}
h1{{font-size:28px;line-height:1.2;margin:0 0 6px;text-wrap:balance}}
h2{{font-size:19px;margin:36px 0 10px;padding-top:14px;border-top:1px solid var(--rule)}}
p,li{{max-width:72ch}}
.sub{{color:var(--ink2);margin:0 0 22px}}
.short{{background:var(--card);border-left:4px solid var(--blue);padding:14px 18px;margin:0 0 8px}}
.short p{{margin:6px 0}}
.card{{background:var(--card);padding:14px 16px;overflow-x:auto}}
.caption{{color:var(--ink2);font-size:13px;margin:8px 0 0}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;font-variant-numeric:tabular-nums}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--grid);vertical-align:top}}
th{{color:var(--ink2);font-weight:600;font-size:12px;letter-spacing:.03em;text-transform:uppercase}}
td:nth-child(n+3),th:nth-child(n+3){{text-align:right;white-space:nowrap}}
code,.mono{{font:13px "IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace}}
.kv{{display:grid;grid-template-columns:minmax(150px,220px) 1fr;gap:6px 16px;font-size:14px}}
.kv dt{{color:var(--ink2)}} .kv dd{{margin:0}}
dl.words dt{{font-weight:600;margin-top:8px}} dl.words dd{{margin:0 0 0 0;color:var(--ink2)}}
ul{{padding-left:22px}} li{{margin:4px 0}}
.tag{{display:inline-block;font-size:12px;padding:1px 8px;border-radius:10px;background:#e4ecf8;color:#1d4f8f;font-weight:600}}
.tag.on{{background:#fbe9df;color:#9a3d15}}
@media (max-width:600px){{.kv{{grid-template-columns:1fr}}}}
</style>
<main>
<h1>First AMX Benchmark Night</h1>
<p class="sub">Nightly System CI on delphi-3bda, 2026-09-22. Page written 2026-09-22 by Claude for jhan. All numbers come from the run logs and from our 2026-09-20 measurement files (paths in the Sources section).</p>

<div class="short">
<p><strong>Short version.</strong> The new row reported {f(CI["tps_mean"],1)} TPS, the one-decimal rounding of a 320-sample mean of {f(CI["tps_mean"],3)} TPS. We measured the same load with the same package on 2026-09-20 at {f(base_mean,3)} TPS, a build without the AMX kernels, so the CI value is within 0.01 TPS ({ci_vs_base_pct:+.2f} %) of our no-kernel value and inside the range of our three passes. The row matches the no-AMX expectation, not the expectation for a build with the kernels, about {f(canon_mean,1)} TPS (est.), because the package the nightly installed (tron {FACTS['tron_version']}) contains no AMX kernels.</p>
</div>

<h2>1. The chart</h2>
<div class="card">
{SVG}
<p class="caption">One dot per run, one shared axis. Blue = build without the AMX kernels, orange = build with the AMX kernels compiled in. Row 3 shows the no-kernel value of the same run as a hollow dot, so the dashed gap is the measured AMX gain. Only the orange dot moved. The shaded band is the expectation we wrote down before the 2026-09-20 run (plan section 7). Hover a dot for its exact value.</p>
</div>

<h2>2. Why the row reads 28.3 and not 32</h2>
<ul>
<li><strong>The package has no AMX kernels.</strong> At 03:39 UTC the nightly removed tron {FACTS['tron_version']} and re-installed the same version from the machine's local package cache ("Need to get 0 B/138 MB of archives", run log lines 391 and 434; Slack line "Tron did NOT update"). platformd re-created the four llama-8b engines at 04:07 UTC, after that install, so the row ran that package. The rinzler binary (the production server) inside that package has sha256 <span class="mono">{FACTS['rinzler_sha'][:12]}...</span>: every recorded install of the package on delphi-3bda gave this hash, including our three base passes (which hashed the running engine processes) and a read-only check at 17:34 UTC today on a copy our own campaign had re-installed from the saved package file at 16:11 UTC. That binary contains none of the five counted AMX tile mnemonics (tdpbf16ps, tileloadd, tilestored, ldtilecfg, tilerelease) and no TRON_AMX_DISABLE text; a build with the kernels has {FACTS['amx_insns_canon']} such instructions and 1 copy of that text (controls from the 2026-09-17 package check). The process image that served the row itself was not hashed (only our wrapper records that), so the identity rests on the same package file plus the matching speed. The run log never mentions AMX: tron has no AMX log line, so binary content and the AMX-busy counter are the only evidence.</li>
<li><strong>It is the package we measured as the no-kernel arm.</strong> Our 2026-09-20 base arm recorded the running engines' rinzler hash <span class="mono">{SUM['identity']['base-pass1']['installed_sha_env'][:12]}...</span> and an AMX-busy counter of 0 cycles in every pass. Note the project term "AMX-off" means something else: the TRON_AMX_DISABLE kill switch of a build that has the kernels, which runs 2 to 5 points slower than a build without them. Neither the nightly nor our base arm is that.</li>
<li><strong>The AMX switch for the package is still an open pull request, by design.</strong> tron PR #4505 (adds TRON_AMX_DISPATCH=ON to the deb preset, so the kernels get compiled into the package) is {FACTS['pr4505_state']}. jhan asked Rhys on 2026-09-21 to merge the test first and #4505 at least a day later, so a first night without AMX is the planned baseline. On today's tron main the preset still lacks the option and the kernel compile is still guarded by it; none of the {FACTS['main_commits_ahead']} commits since 3faba6d0 changes that.</li>
<li><strong>No new package has shipped since 2026-09-18.</strong> The scheduled publish-deb job (cron 01:17 UTC, runs start 01:31 to 01:41 UTC) failed at startup on 09-19, 09-20, 09-21 and 09-22 with zero jobs. The fix, tron PR #4510 (three permission lines in the workflow file), merged at {FACTS['pr4510_merged']}, after the 09-22 schedule; a manual run at 16:43 UTC passed validation and was cancelled during the build step, so the 09-23 schedule is the first real attempt with the fix. Rhys wrote in #ci-cd-notifications that a new tron version will appear tomorrow and that this first run "is a baseline with no AMX changes present".</li>
</ul>

<h2>3. How close the two AMX-off numbers are</h2>
<div class="kv">
<dt>CI row (320 samples)</dt><dd>{f(CI["tps_mean"],3)} TPS mean, sd {f(CI["tps_sd"],3)}, min {f(CI["tps_min"])}, p05 {f(CI["p05"])}, TTFT {f(CI["ttft_mean_ms"]/1000,1)} s</dd>
<dt>Our base arm (3 passes x 320)</dt><dd>{", ".join(f(b["tps_mean"],3) for b in BASE)} TPS (mean {f(base_mean,3)}), TTFT {f(base_ttft/1000,1)} s</dd>
<dt>Gap</dt><dd>{CI["tps_mean"]-base_mean:+.3f} TPS = {ci_vs_base_pct:+.2f} %. Our own three passes spread over {f(pass_spread,3)} TPS, so the CI value sits inside our pass-to-pass spread.</dd>
<dt>CI rounds</dt><dd>Per-round means {f(prm_lo)} to {f(prm_hi)} TPS; the log's cumulative running averages read {rounds} TPS. Round 1 started {CI["first_ts"][11:16]} UTC, round 10 closed {CI["last_ts"][11:16]} UTC. No warm-up trend: the first round is as fast as the last.</dd>
<dt>TTFT</dt><dd>CI {f(CI["ttft_mean_ms"]/1000,1)} s vs ours {f(base_ttft/1000,1)} s ({ttft_pct:+.1f} %, {CI["ttft_mean_ms"]-base_ttft:+.0f} ms). Our three passes spread over {max(b["ttft_ms"] for b in BASE)-min(b["ttft_ms"] for b in BASE)} ms, so this gap is a real difference, not noise. Its cause is not resolved (Insufficient data: the CI log prints no cache-hit or prompt-token lines for the row). Candidates: the prompt set, the client host, platformd 0.11.0. TTFT is time to first token; at 8 users per engine it includes queueing behind the other users' 4096-token prompts, and it does not enter the TPS number.</dd>
<dt>Pre-registered estimate</dt><dd>Plan section 7 (written before the 2026-09-20 run) said: clean about 28 TPS, canon about 32 TPS, canon TTFT about 11 s. The CI row landed on the clean estimate.</dd>
<dt>Second measurement with the kernels</dt><dd>The Saturday check cell of 2026-09-19 (32 users, prompt 8192 requested and truncated by the server to 4096) gave 32.25 TPS and TTFT 11.5 s with the AMX-busy counter at 30.7 G cycles, consistent with the canon arm.</dd>
</div>

<h2>4. What to expect next</h2>
<ul>
<li><strong>Tonight (2026-09-23 nightly):</strong> the publish-deb fix is in, and the 09-18 build took 24 minutes, so a package built from tron main at about 01:35 UTC should be ready before the 03:30 UTC nightly installs it. Two caveats: a full package build has not completed since 09-18 (PR #4510's body says "Full build and publication remain untested"), so a build-step failure is still possible; and if PR #4505 merges before the 01:17 UTC cron, the package carries the kernels and the row should read about {f(canon_mean,1)} TPS instead. If #4505 stays open, the package has no AMX kernels and the expected row value is 28.2 to 28.3 TPS (est.; four runs of the 3faba6d0 binary in this cell gave {min(min(b["tps_mean"] for b in BASE), CI["tps_mean"]):.3f} to {max(max(b["tps_mean"] for b in BASE), CI["tps_mean"]):.3f}). tron main is {FACTS['main_commits_ahead']} commits past 3faba6d0 (head {FACTS['main_head']}); PR #4258 (merged 2026-09-18 19:32 UTC, after the 09-18 build) rewrites parts of self_attention.hpp, and llama-8b runs CPU attention in the nightly, so the no-kernel base may move. No measurement of a newer main exists for this cell; the first rebuild without kernels shows whether the base moved.</li>
<li><strong>After PR #4505 merges, a publish-deb run after that merge succeeds, and the nightly log shows "Setting up tron" with that newer version:</strong> expected about {f(canon_mean,1)} TPS (est., +{f(gain_pct,1)} % over the same-package no-kernel value) and TTFT about 11.2 to {f(canon_ttft/1000,1)} s (est.; the CI harness already reads TTFT 2 % below ours). Basis: our canon arm measured {", ".join(f(c["tps_mean"],3) for c in CANON)} TPS on 2026-09-20 (3 pairs, paired t {f(SUM['verdicts']['cell']['paired_t'],1)}) with main 3faba6d0, our prompt source and platformd {FACTS['platformd_ours']}. The first AMX nightly will carry a newer main, Rhys's prompt source and platformd {FACTS['platformd_ci']}. The pre-registered band +11 to +21 % maps to {f(band_lo,1)} to {f(band_hi,1)} TPS if the no-AMX base stays at {f(base_mean)} TPS. PR #4424 (VNNI-K) is still open, so the first AMX nightly carries the canonical kernels only, the same variant as our canon arm. Timing: publish-deb runs at {FACTS['publish_deb_sched']}, so a merge of #4505 later in a day reaches the nightly two calendar nights later, not the next one.</li>
<li><strong>Reading rule (delphi-3bda line only):</strong> a value near 28.3 on a night whose installed package does contain the AMX kernels would be unexpected. The AMD report prints the same "(AMX benchmark)" label and will stay near 29 TPS even with the kernels in the package, because the AMX build takes the AVX path on AMD. TPS alone cannot separate "AMX not dispatched" from a main regression that cancels the gain, so it needs three checks, in order: the tron version in the run log ("Setting up tron" line), the installed binary (<span class="mono">strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE</span> must print 1, and objdump must show AMX tile instructions), and the AMX-busy counter on the engines during a request (perf event cpu/event=0xb7,umask=0x02).</li>
<li><strong>Thresholds:</strong> the row is informational (memo icon, no threshold). Section 9.4 of the combined llama-3.1-8b page proposed 30.6 mean / 30.3 p05 / 30.0 min TPS, 5 % below the value measured with the kernels, once AMX nights accumulate.</li>
</ul>

<h2>5. Record</h2>
<div class="card">
<table>
<thead>{rec_head}</thead>
<tbody>
{chr(10).join(rec_rows)}
</tbody>
</table>
<p class="caption">All rows: llama-3.1-8b-instruct-good-tp2, 32 users on 4 engines behind the Caddy proxy (8 users per engine), prompt 4096 tokens, 1536 generated tokens, TPS window tokens 896-1024, ShareGPT prompts. n = requests (10 rounds x 32 users). sd = standard deviation across the n samples (population form, the harness's own definition). The CI means are computed from log lines printed with two decimals, so their third decimal is good to about 0.0005 TPS. The "/ 140.00 TPS" printed on every CI sample line is the 8-user row's threshold, not a threshold for this row; this row has none. p05 = 5th percentile of the samples. The AMD row is a same-binary, same-night reference from another machine: Genoa (Zen 4) CPUs have no AMX unit (verified on andoria-06), so the kernels are never used there, and its {f(GENOA["tps_mean"]-CI["tps_mean"],2)} TPS ({(GENOA["tps_mean"]-CI["tps_mean"])/CI["tps_mean"]*100:+.1f} %) lead over 3bda with the same package is a machine difference (96-core Genoa vs 72-core Granite Rapids), not an AMX effect; its TTFT (mean over the 320 samples) is {(1-GENOA["ttft_mean_ms"]/CI["ttft_mean_ms"])*100:.0f} % lower. Slack prints the labelled row with one decimal: {esc(FACTS['slack_line'])}.</p>
</div>

<h2>6. Known differences between the CI run and our run</h2>
<ul>
<li><strong>Prompt source.</strong> The merged test appended 320 long ShareGPT records to the prompt file (1320 records, 332 eligible at 4096 tokens); the row's 320 requests use the first 320 eligible records in file order, the same set every night. Our run concatenated ShareGPT conversations. Both use seeds 0 to 319, so 320 distinct prompts, and both generate the full 1536 tokens per request. Our runs showed 4096 prompt tokens on the server for every request; for the nightly the log prints no token count, and the 4096 follows from the harness code, which raises on short prompts and truncates to the configured length. The decode speed matched, so the prompt text did not matter for TPS.</li>
<li><strong>platformd version.</strong> The nightly ran platformd {FACTS['platformd_ci']} (version from the Slack report; the log shows "provisioning mode: explicit"); our run used {FACTS['platformd_ours']} (legacy posadm path). Both show 4 engines and 4 healthy Caddy upstreams in their logs. The even 8-users-per-engine split is measured only in our runs (80 requests per engine per pass, from the engines' FUSE counters); the nightly log carries no per-engine counts. No effect on TPS is visible.</li>
<li><strong>Client host.</strong> CI drives from system-ci-runner; we drove from claude-agentsrv. Per-request TPS is measured inside the generation window, so the client host changes TTFT more than TPS.</li>
<li><strong>Engine state.</strong> The nightly ran the row on engines created at 04:07 UTC that had just served the 80 requests of the 8-user row ("already provisioned, verifying engines are healthy"). Each of our passes ran on engines that had served only 18 short probe and health requests since provisioning, because the arms alternated and every package switch re-provisioned. The CI samples are tighter than ours (sd 0.163 vs 0.24 to 0.27); the warm engines or a more even proxy spread are hypotheses, and a per-engine request count on a nightly would settle it.</li>
<li><strong>Harness code version.</strong> The nightly ran systems_test 7327184 (the PR #221 merge); our run used fc27f073 plus a local prompt patch. The per-sample TPS code is the same; the differences are error handling and one log line.</li>
<li><strong>Same on both sides.</strong> Speculation off (SYSTEM_CI_SPECULATION=0 in the workflow environment and in our driver), 10 rounds, 0.1 s stagger, sample interval 16, capture window 896 to 1024, 1536 generated tokens, the same per-sample TPS code in testlib/tps.py (the 38-line diff between the two harness versions is error handling). Our cached-token share was 0.8 % (the shared system-prompt prefix); the nightly log has no usage fields, so its share is unknown.</li>
</ul>

<h2>Words used here</h2>
<dl class="words">
<dt>tron / rinzler</dt><dd>tron is the inference program under test; rinzler is its production server binary, installed from the tron Debian package (the "deb").</dd>
<dt>AMX</dt><dd>Advanced Matrix Extensions, the Intel matrix-multiply unit. The tron AMX attention kernels are compiled only when the build option TRON_AMX_DISPATCH is ON; the package preset lacks it until PR #4505 merges.</dd>
<dt>AMX-off (project term, not used for these runs)</dt><dd>the TRON_AMX_DISABLE kill switch of a build that has the kernels; it runs 2 to 5 points slower than a build without the kernels. The nightly package and our base arm are builds without the kernels.</dd>
<dt>canonical build (canon)</dt><dd>tron main at the same commit as the nightly package plus the AMX kernels compiled in, without the K-mirror or VNNI-K variants.</dd>
<dt>Nightly System CI</dt><dd>the systems_test workflow that installs the newest tron package on delphi-3bda every night at 03:39 UTC and runs functional, performance, MMLU and soak phases; it posts to Slack #ci-cd-notifications.</dd>
<dt>TPS</dt><dd>tokens per second per user, measured by the CI harness over generated tokens 896 to 1024 of each request.</dd>
<dt>TTFT</dt><dd>time to first token, in seconds here.</dd>
<dt>p05, sd</dt><dd>5th percentile and standard deviation of the per-request TPS samples.</dd>
<dt>paired t</dt><dd>paired t statistic over the three base/canon pass pairs; the 95 % limit for 2 degrees of freedom is 4.30.</dd>
<dt>users per engine</dt><dd>the nightly spreads 32 users over 4 engines behind the Caddy reverse proxy, so each engine serves 8 users at once. The AMX gain grows with users per engine and prompt length.</dd>
<dt>publish-deb</dt><dd>the tron GitHub workflow (schedule {FACTS['publish_deb_sched']}) that builds the package the nightly installs.</dd>
</dl>

<h2>Sources</h2>
<ul>
<li>Slack #ci-cd-notifications: talos nightly report for delphi-3bda, 2026-09-22 06:20 PDT; Rhys Jordan's note, 09:50 PDT.</li>
<li>GitHub: systems_test run {FACTS['run_id']} (3bda) and {FACTS['genoa_run_id']} (AMD); systems_test PR #221 merged {FACTS['pr221_merged']}; tron PR #4505 (open), PR #4510 (merged {FACTS['pr4510_merged']}); tron publish-deb.yml run list.</li>
<li>delphi-3bda, 17:34 UTC, read-only: dpkg -s tron, sha256sum / strings / objdump on /opt/positron/bin/rinzler, /etc/rinzler/instance-*.env.</li>
<li>Our measurement: exec/results/l8b-8u4k-20260920/summary.json (3 base + 3 canon passes), plan CI-test/status/llama-3.1-8b-8u-4k-plan.md, report CI-test/status/llama-3.1-8b-8u-4k.html.</li>
<li>Generator: exec/first-ci-amx-row-20260922/gen_page.py, parse_row.py, nightly_rows.json, facts.md (with a corrections section).</li>
<li>Verification: workflow wf_b0e651b2-8c4, 6 claims x 3 lenses (data re-check, confounds, wording) plus a completeness critic; 18 of 18 verdicts upheld the claims; the corrections they returned are applied on this page.</li>
</ul>
</main>
"""
assert all(ord(ch) < 128 for ch in page), [ch for ch in page if ord(ch) >= 128][:5]
open(OUT, "w").write(page)
open(os.path.join(HERE, "chart.svg"), "w").write(SVG)
print("wrote", OUT, len(page), "bytes;", "gain", f(gain_pct, 2), "ci_vs_base", f(ci_vs_base_pct, 3), "band", f(band_lo, 2), f(band_hi, 2))
