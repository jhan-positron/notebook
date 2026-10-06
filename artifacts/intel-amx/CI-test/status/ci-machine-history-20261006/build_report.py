"""Build a light, standalone HTML report from the paired CI measurements."""

import base64
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
PAIRS = json.loads((ROOT / "paired-results.json").read_text())
SUMMARY = json.loads((ROOT / "summary.json").read_text())
REPORTS = json.loads((ROOT / "reports.json").read_text())
AMX = "llama-3.1-8b-instruct-good-tp2 @32u (AMX benchmark)"
LABELS = {
    AMX: "Llama 3.1 8B · TP2 · 32 users · AMX workload",
    "llama-3.2-3b-instruct-fast-tp2 @32u": "Llama 3.2 3B · TP2 · 32 users",
    "llama-3.1-8b-instruct-good-tp2 @8u": "Llama 3.1 8B · TP2 · 8 users",
    "llama-3.3-70b-instruct-good-tp2 @8u": "Llama 3.3 70B · TP2 · 8 users",
    "llama-3.3-70b-instruct-good-tp2 @4u": "Llama 3.3 70B · TP2 · 4 users",
    "llama-3.3-70b-instruct-good-tp4 @4u": "Llama 3.3 70B · TP4 · 4 users",
    "mixtral-8x7b-instruct-v0.1-tp2 @8u": "Mixtral 8×7B · TP2 · 8 users",
    "qwen-2.5-32b-it-fast-tp2 @8u": "Qwen 2.5 32B · TP2 · 8 users",
    "ingested-qwen-3-4b-instruct-2507-tp2 @8u": "Qwen 3 4B · TP2 · 8 users",
    "ingested-qwen-3-4b-instruct-2507-tp4 @8u": "Qwen 3 4B · TP4 · 8 users",
    "gemma-2-9b-it-fast-tp2 @8u": "Gemma 2 9B · TP2 · 8 users",
    "ingested-gpt-oss-120b-tp4 @8u": "GPT-OSS 120B · TP4 · 8 users",
    "ingested-gemma-4-31b-it-tp2 @8u": "Gemma 4 31B · TP2 · 8 users",
    "ingested-meta-models--Muse-Glimmer-30B-tp4 @8u": "Muse-Glimmer 30B · TP4 · 8 users",
}
BLUE, ORANGE, INK = "#0072B2", "#D55E00", "#243444"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#CDD5DC", "text.color": INK,
                     "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
                     "figure.facecolor": "white", "axes.facecolor": "white", "svg.fonttype": "none",
                     "svg.hashsalt": "ci-machine-history-20261006"})


def save(fig, name):
    fig.savefig(ROOT / f"{name}.png", dpi=160, bbox_inches="tight", facecolor="white")
    fig.savefig(ROOT / f"{name}.svg", bbox_inches="tight", facecolor="white", metadata={"Date": "2026-10-06"})
    svg = ROOT / f"{name}.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)


amx = [p for p in PAIRS if p["key"] == AMX]
post = [p for p in amx if p["date"] >= "2026-09-23"]
fig, ax = plt.subplots(figsize=(13, 4.7))
x = np.arange(len(amx))
ax.axvspan(-.4, .5, color="#F2F4F6", zorder=0)
ax.axvline(.5, color="#7A8792", ls="--", lw=1.1)
for machine, color, marker, delta in [("delphi", BLUE, "o", .17), ("andoria", ORANGE, "s", -.31)]:
    y = [p[f"{machine}_tps"] for p in amx]
    ax.plot(x, y, color=color, marker=marker, lw=2.1, ms=5.5, label=machine.title())
    for i, value in enumerate(y):
        shift = -.36 if machine == "delphi" and i == 0 else .2 if machine == "andoria" and i == 0 else delta
        ax.text(i, value + shift, f"{value:.2f}", color=color, ha="center", fontsize=8.5)
ax.text(.7, 33.72, "Sep 23: first nightly report with AMX", fontsize=10, weight="bold")
ax.text(5.9, 31.0, "Delphi leads on 14 / 14 nights\n+12.4% to +14.1% · median +13.5%", color=BLUE,
        fontsize=12, weight="bold", bbox={"facecolor": "#EDF6FC", "edgecolor": "none", "pad": 10})
ax.set(xlim=(-.45, 14.45), ylim=(27.2, 34.2), ylabel="Mean decode rate (tokens/s per user)",
       xticks=x, xticklabels=[p["date"][5:].replace("-", "/") for p in amx])
ax.tick_params(axis="x", labelsize=8.5)
ax.grid(axis="y", color="#E7EBEF", lw=.7)
ax.set_axisbelow(True)
ax.legend(loc="upper right", frameon=False, ncol=2)
fig.suptitle("Llama 3.1 8B: the lead changes on September 23", x=.065, ha="left", fontsize=16, weight="bold")
fig.text(.065, -.01, "2026 report dates · 32 users per machine · TP2 · 4,096-token prompt · 1,536-token generation\n"
         "The vertical axis starts at 27.2 tokens/s to show the change. Points are stored Talos measurements.", fontsize=9, color="#536171")
fig.subplots_adjust(left=.075, right=.985, top=.83, bottom=.18)
save(fig, "amx-history")

consistent = [AMX, "mixtral-8x7b-instruct-v0.1-tp2 @8u", "gemma-2-9b-it-fast-tp2 @8u", "ingested-gemma-4-31b-it-tp2 @8u"]
snapshot = {p["key"]: p for p in PAIRS if p["date"] == "2026-10-05"}
fig, ax = plt.subplots(figsize=(12.5, 3.8))
for i, key in enumerate(consistent):
    p = snapshot[key]
    a, d = p["andoria_tps"], p["delphi_tps"]
    ax.plot([a, d], [i, i], color="#B1BCC5", lw=3, zorder=1)
    ax.scatter([a], [i], marker="s", color=ORANGE, s=48, zorder=3)
    ax.scatter([d], [i], marker="o", color=BLUE, s=48, zorder=3)
    ax.text(a - 1, i + .25, f"{a:.2f}", ha="right", color=ORANGE, fontsize=10)
    ax.text(d + 1, i - .20, f"{d:.2f}", ha="left", color=BLUE, fontsize=10)
    ax.text(117, i, f"+{p['delphi_lead_pct']:.1f}%", va="center", color=BLUE, weight="bold")
ax.set(yticks=range(4), yticklabels=[LABELS[k].replace(" · AMX workload", "") for k in consistent],
       xlim=(0, 127), ylim=(3.6, -.6), xlabel="Mean decode rate (tokens/s per user)")
ax.set_xticks(range(0, 121, 20))
ax.grid(axis="x", color="#E7EBEF", lw=.7)
ax.set_axisbelow(True)
fig.suptitle("Four consistent Delphi leads — the October 5 results", x=.02, ha="left", fontsize=15, weight="bold")
fig.text(.38, .86, "■ Andoria", color=ORANGE, fontsize=11)
fig.text(.51, .86, "● Delphi", color=BLUE, fontsize=11)
fig.subplots_adjust(left=.34, right=.98, top=.78, bottom=.16)
save(fig, "consistent-leads")

temporary_keys = ["llama-3.3-70b-instruct-good-tp4 @4u", "ingested-gpt-oss-120b-tp4 @8u",
                  "llama-3.3-70b-instruct-good-tp2 @8u", "llama-3.3-70b-instruct-good-tp2 @4u"]
fig, axes = plt.subplots(2, 2, figsize=(13, 6.7))
for ax, key in zip(axes.flat, temporary_keys):
    rows = [p for p in PAIRS if p["key"] == key and p["date"] >= "2026-09-22"]
    for machine, color, marker in [("delphi", BLUE, "o"), ("andoria", ORANGE, "s")]:
        vals = [p[f"{machine}_tps"] if p["valid"] or p[f"{machine}_tps"] > 0 else np.nan for p in rows]
        ax.plot(range(len(rows)), vals, color=color, marker=marker, ms=3, lw=1.5)
        ax.annotate(f"{vals[-1]:.2f}", (len(rows) - 1, vals[-1]), xytext=(6, 0), textcoords="offset points", color=color, va="center", fontsize=9)
    for i, p in enumerate(rows):
        if p["valid"] and p["delphi_lead_pct"] > 0:
            ax.axvspan(i - .25, i + .25, color="#FBEAD9", zorder=-1)
    ax.set_title(LABELS[key], loc="left", fontsize=11, weight="bold")
    ax.set(xlim=(-.3, len(rows) + .5), ylabel="tokens/s per user", xticks=[0, 4, 7, 10, 14],
           xticklabels=[rows[i]["date"][5:].replace("-", "/") for i in [0, 4, 7, 10, 14]])
    ax.grid(axis="y", color="#E7EBEF")
fig.suptitle("Temporary Delphi wins coincide with Andoria throughput drops", x=.065, ha="left", fontsize=15, weight="bold")
fig.text(.065, .905, "Blue circles: Delphi · orange squares: Andoria · shaded dates: Delphi led · missing result is a gap", fontsize=10)
fig.text(.065, .005, "2026 report dates. Each panel uses its own labeled vertical scale. October 2 uses the original nightly, not the later rerun.", fontsize=9)
fig.subplots_adjust(left=.07, right=.97, top=.83, bottom=.10, wspace=.23, hspace=.37)
save(fig, "temporary-leads")


def link(url, text):
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(text)}</a>'


def image(name, alt):
    encoded = base64.b64encode((ROOT / f"{name}.svg").read_bytes()).decode()
    return f'<img src="data:image/svg+xml;base64,{encoded}" alt="{html.escape(alt)}">'


def source_pair(row):
    return link(row["delphi_value_source"], "Delphi") + " / " + link(row["andoria_value_source"], "Andoria")


def table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{v}</th>' for v in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{v}</td>' for v in r) + '</tr>' for r in rows) + '</tbody></table></div>'


summary_index = {s["key"]: s for s in SUMMARY}
other_rows = []
for key in consistent:
    p = snapshot[key]
    pre = next(row for row in PAIRS if row["date"] == "2026-09-22" and row["key"] == key)
    post_stats = summary_index[key]["post"]
    other_rows.append([LABELS[key], f"{pre['delphi_lead_pct']:+.1f}%", f"{p['delphi_tps']:.2f}", f"{p['andoria_tps']:.2f}",
                       f"{p['delphi_lead_pct']:+.1f}%", f"{post_stats['wins']}/{post_stats['n']}", source_pair(p)])
all_rows = []
for s in SUMMARY:
    p = snapshot[s["key"]]
    all_rows.append([LABELS[s["key"]], f"{s['post']['wins']}/{s['post']['n']}", f"{s['post']['median_lead_pct']:+.1f}%",
                     f"{p['delphi_tps']:.2f}" if p["valid"] else "Missing", f"{p['andoria_tps']:.2f}",
                     f"{p['delphi_lead_pct']:+.1f}%" if p["valid"] else "—", source_pair(p)])
daily = [[p["date"], f"{p['delphi_tps']:.2f}", f"{p['andoria_tps']:.2f}", f"{p['delphi_lead_pct']:+.2f}%",
          f"{p['delphi_ttft_ms']/1000:.3f}", f"{p['andoria_ttft_ms']/1000:.3f}", source_pair(p)] for p in amx]
temporary = []
for k in temporary_keys:
    s = summary_index[k]["post"]
    temporary.append([LABELS[k], f"{s['wins']}/{s['n']}", ", ".join(d[5:] for d in s["win_dates"]),
                      f"{snapshot[k]['delphi_lead_pct']:+.1f}%" if snapshot[k]["valid"] else "Missing Delphi result"])

pr = "https://github.com/positron-ai/tron/pull/4505"
baseline_note = "https://positronai.slack.com/archives/C06S8PNDBQA/p1790095827478439"
oct02 = "https://positronai.slack.com/archives/C06S8PNDBQA/p1790948618221139"
sep29 = "https://positronai.slack.com/archives/C06S8PNDBQA/p1790699156777329"
first = next(p for p in amx if p["date"] == "2026-09-23")
baseline = amx[0]
recent = amx[-1]
quoted = snapshot[AMX]
page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Delphi vs Andoria — nightly performance history</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#243444;font:16px/1.55 system-ui,sans-serif}main{max-width:1240px;margin:auto;padding:36px 28px 70px}h1{font-size:34px;line-height:1.2;margin:8px 0 16px}h2{font-size:23px;margin:32px 0 12px}p{max-width:1050px}a{color:#006ba6}section,.hero{background:white;border:1px solid #dce3e9;border-radius:12px;padding:24px;margin:20px 0}.eyebrow{font-size:13px;color:#59697a;letter-spacing:.07em;text-transform:uppercase}.short{font-size:18px}.callout{border-left:4px solid #0072b2;padding:10px 16px;background:#eff7fc}.note,figcaption{font-size:14px;color:#536171}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}th,td{padding:10px 12px;border-bottom:1px solid #e3e8ed;text-align:right;vertical-align:top}th{background:#f5f7fa;color:#425567}td:first-child,th:first-child{text-align:left}td a{white-space:nowrap}figure{margin:20px 0}img{max-width:100%;height:auto;display:block}li{margin:8px 0}select{font:inherit;max-width:100%;padding:8px;border:1px solid #aebbc5;border-radius:5px;background:white;color:#243444}summary{cursor:pointer;font-weight:650}code{font-size:13px;overflow-wrap:anywhere}.tag{display:inline-block;padding:4px 8px;margin:3px;background:#edf2f6;border-radius:4px;font-size:13px}.foot{border-top:1px solid #dce3e9;padding-top:16px}@media(max-width:650px){main{padding:20px 12px}section,.hero{padding:16px}h1{font-size:27px}th,td{padding:8px}.short{font-size:16px}}
</style><main><div class="eyebrow">Nightly CI history · report dates September 15–October 6, 2026</div>
<h1>Delphi overtook Andoria on the first AMX nightly</h1>
<div class="hero"><p class="short"><strong>Short version:</strong> Llama 3.1 8B at TP2 and 32 users is the only tested workload with a new, sustained Delphi lead after AMX was enabled. Its reversal first appears in the September 23 report and holds on all 14 paired nights through October 6. Mixtral 8×7B, Gemma 2 9B, and Gemma 4 31B already led on Delphi before the rollout.</p>
<p class="note">Delphi = delphi-3bda (Intel Granite Rapids); Andoria = andoria-b1a3 (AMD Genoa). CI means continuous integration, the automated nightly test suite. AMX means Intel Advanced Matrix Extensions, CPU instructions for matrix operations. The AMD machine runs the same workload without executing AMX instructions.</p>
<span class="tag">TPS: output tokens per second per user</span><span class="tag">TP2 / TP4: model split across 2 / 4 accelerator cards</span><span class="tag">TTFT: time to first token</span><span class="tag">Higher decode rate is better</span></div>
'''
page += '<section><h2>When the lead changed</h2>'
page += f'<ul><li><strong>September 22 report:</strong> the new 32-user benchmark was a baseline without AMX. Both machines still used <code>v2026.09.18-3faba6d0</code>. Delphi measured 28.25 tokens/s versus Andoria’s 29.00 tokens/s, a 2.6% deficit. {link(baseline_note,"Rollout explanation")} · {source_pair(baseline)}.</li>'
page += f'<li><strong>September 22 at 21:08 UTC / 14:08 PDT:</strong> the package change enabling AMX merged. {link(pr,"Package change #4505")}.</li>'
page += f'<li><strong>September 23 report:</strong> both machines used <code>v2026.09.23-5cf65b92</code>. Delphi reached 32.49 tokens/s versus 28.91 tokens/s, a 12.4% lead. Delphi’s day-to-day gain was 15.0%; Andoria changed by −0.3%. {source_pair(first)}.</li></ul>'
page += '<p class="callout">The merge happened on September 22. The first nightly report showing the reversal is dated September 23.</p>'
page += '<figure>' + image("amx-history", "Daily Llama 8B decode rate: Delphi rises from 28.25 to about 32.6 tokens/s on September 23; Andoria stays near 28.7 tokens/s.") + '<figcaption>Delphi’s rate rose at rollout and stayed above Andoria’s rate. Every point has a corresponding source in the daily table below.</figcaption></figure>'
page += f'<p>The quoted October 5 pair gives Delphi a <strong>13.9% decode lead</strong>. Its slowest user is also 14.1% faster: 31.96 versus 28.01 tokens/s. TTFT is 12.8% shorter: 11.577 versus 13.277 seconds. {source_pair(quoted)}.</p>'
page += f'<p>The October 6 pair confirms the lead: <strong>32.61 versus 28.70 tokens/s (+13.6%)</strong>. {source_pair(recent)}.</p>'
page += '<p class="callout"><strong>Historical conclusion:</strong> Among the tested configurations, Llama 3.1 8B at 32 users is the only one that was behind on September 22 and then ahead on every nightly through October 6. Mixtral and both Gemma leads predate the rollout. Llama 70B and GPT-OSS wins were temporary. Other models can improve without gaining a sustained lead over Andoria.</p>'
page += '<p class="note">All 31 retrieved summaries, including the October 2 rerun, record the same AMX workload: prompt=4096, generate=1536, shared_prefix=0, capture=896–1024, users=32, mode=sharegpt. Capture is the generated-token interval used to measure decode. The nightly pass percentages use different machine thresholds and are not the machine-to-machine speed comparison.</p></section>'
page += '<section><h2>Three other models consistently lead on Delphi</h2><p>These are decode-throughput wins. On October 5, all three had longer TTFT on Delphi, so the throughput result does not imply faster prompt processing.</p>'
page += '<figure>' + image("consistent-leads", "The October 5 snapshot shows Delphi ahead on Llama 8B 32 users, Mixtral 8x7B, Gemma 2 9B, and Gemma 4 31B.") + '<figcaption>The three non-Llama leads already existed in the September 22 baseline. All four workloads show Delphi wins on 14 of 14 nights after rollout.</figcaption></figure>'
page += table(["Workload", "Sep 22 lead", "Oct 5 Delphi<br>tokens/s", "Oct 5 Andoria<br>tokens/s", "Oct 5 lead", "Wins Sep 23–Oct 6", "Oct 5 sources"], other_rows)
page += '<p class="note">The baseline values are linked in the source browser below. The earlier September 15–21 records also show these three leads on every available paired date. Andoria has no performance results on September 17.</p></section>'
page += '<section><h2>Other Delphi wins were temporary</h2>'
page += table(["Workload", "Delphi wins / valid nights", "Winning report dates in 2026", "Oct 5 Delphi lead"], temporary)
page += f'<p>On September 29, Andoria’s GPT-OSS mean fell from 127.66 tokens/s after the first round to 73.71 tokens/s after the last round. Its Llama 70B TP2 runs also slowed substantially. {link(sep29,"September 29 run discussion")}.</p>'
page += f'<p>On October 2, the original Andoria nightly recorded 26.66 tokens/s for Llama 70B TP4 and 81.36 tokens/s for GPT-OSS. The incident discussion identifies a firmware update that caused slow cards. The later rerun returned to 34.06 and 128.20 tokens/s, respectively; both exceed Delphi’s original-nightly values of 31.74 and 121.90 tokens/s. {link(oct02,"October 2 incident")} · {link("https://positronai.slack.com/archives/C06S8PNDBQA/p1790967797473679","Andoria rerun")}.</p>'
page += '<figure>' + image("temporary-leads", "Four time-series panels show the temporary Delphi wins when Andoria throughput drops, followed by recovery.") + '<figcaption>These observations establish occasional wins during degraded runs. They do not establish a sustained Delphi advantage for these workloads.</figcaption></figure></section>'
page += '<section><h2>Every tested workload</h2><p>Same-date comparisons use the same model, TP setting, and user count. The median lead is the median of daily values of 100 × (Delphi / Andoria − 1). Positive values favor Delphi.</p>'
page += table(["Workload", "Delphi wins<br>Sep 23–Oct 6", "Median lead", "Oct 5 Delphi<br>tokens/s", "Oct 5 Andoria<br>tokens/s", "Oct 5 lead", "Oct 5 sources"], all_rows)
page += '<p class="note">Llama 70B TP2 at 4 users has 13 valid post-rollout pairs. The October 5 Delphi report shows 0.00, but its stored session has no corresponding benchmark summary; it is treated as missing. Muse-Glimmer has six paired nights. Other workloads have 14 paired nights. The 8-user Llama 8B workload remains faster on Andoria on all 14 nights.</p></section>'
page += '<section><h2>Exact Llama 8B AMX history</h2>'
page += table(["Report date", "Delphi tokens/s", "Andoria tokens/s", "Delphi lead", "Delphi TTFT, s", "Andoria TTFT, s", "Stored measurements"], daily)
page += '</section><section><h2>Browse the measurements</h2><p>Choose a workload to inspect every paired measurement and open its source. Values cover September 15–October 6 where available.</p><label for="model">Workload: </label><select id="model">'
page += ''.join(f'<option value="{html.escape(k)}" {"selected" if k == AMX else ""}>{html.escape(v)}</option>' for k, v in LABELS.items())
page += '</select><div id="measurement-table" class="table-wrap"></div></section>'
page += f'''<section><h2>Method and limits</h2><ul>
<li>Dates are the dates printed in the nightly reports. The September 22 evening deployment appears in the September 23 report.</li>
<li>The analysis uses the first nightly per machine per report date. The later Andoria runs on September 18 and October 2 are retained separately and do not add extra nightly votes. The AMX lead also holds against the October 2 rerun: 32.78 versus 28.69 tokens/s.</li>
<li>Andoria’s September 26–29 full workflows did not complete. Their performance measurements are available and are included. September 26–28 measurements were also checked against saved individual-request completion logs. Whole-workflow failure does not mean every benchmark lacked a measurement.</li>
<li>The 31 session summaries for September 22–October 6 were downloaded from Talos and cross-checked against the Slack reports. Earlier context uses the saved September 15–21 records. Full precision replaces the one-decimal Slack display where available.</li>
<li>Rates describe the mean per-user decode measurement, not aggregate machine throughput. Prefill, when shown in source records, is an <strong>est.</strong> in tokens/s calculated from configured prompt length divided by TTFT.</li>
<li>This report classifies the historical results: Llama 3.1 8B at 32 users is the only new sustained Delphi lead after the AMX rollout. The nightly sequence establishes the timing but does not isolate each change in the package. {link(pr,"Package change")}.</li>
</ul><p class="foot">Downloads: {link("paired-results.csv","All paired measurements (CSV)")} · {link("amx-history.png","Llama 8B history (PNG)")} · {link("paired-results.json","Paired data (JSON)")}. This HTML embeds its charts and works offline. Source links require access to the internal services.</p></section></main>'''
payload = json.dumps(PAIRS).replace("</", "<\\/")
page += '<script type="application/json" id="measurements">' + payload + '</script>'
page += '''<script>
const measurements=JSON.parse(document.getElementById('measurements').textContent);
const escapeText=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function render(){
 const rows=measurements.filter(x=>x.key===document.getElementById('model').value);
 let out='<table><thead><tr><th>Date</th><th>Delphi tokens/s</th><th>Andoria tokens/s</th><th>Delphi lead</th><th>Delphi TTFT, ms</th><th>Andoria TTFT, ms</th><th>Sources</th></tr></thead><tbody>';
 for(const r of rows){const values=[r.date,r.delphi_tps>0?r.delphi_tps.toFixed(2):'Missing',r.andoria_tps>0?r.andoria_tps.toFixed(2):'Missing',r.valid?(r.delphi_lead_pct>0?'+':'')+r.delphi_lead_pct.toFixed(2)+'%':'n/a',r.delphi_ttft_ms??'n/a',r.andoria_ttft_ms??'n/a'];out+='<tr>'+values.map(x=>'<td>'+escapeText(x)+'</td>').join('')+'<td><a href="'+escapeText(r.delphi_value_source)+'">Delphi</a> / <a href="'+escapeText(r.andoria_value_source)+'">Andoria</a></td></tr>';}
 document.getElementById('measurement-table').innerHTML=out+'</tbody></table>';
}
document.getElementById('model').addEventListener('change',render);render();
</script></html>'''
repo_path = "artifacts/intel-amx/CI-test/status/ci-machine-history-20261006/report.html"
rendered = f"https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/{repo_path}"
backup = f"https://raw.githack.com/jhan-positron/notebook/main/{repo_path}"
header = f"<!--\nRendered page (open in browser): {rendered}\nBackup renderer: {backup}\n-->\n"
(ROOT / "report.html").write_text((header + page).encode("ascii", "xmlcharrefreplace").decode("ascii"))
print("Built", ROOT / "report.html", "with", len(PAIRS), "paired records and three embedded charts.")
