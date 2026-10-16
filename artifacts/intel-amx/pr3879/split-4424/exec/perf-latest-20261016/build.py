#!/usr/bin/env python3
"""Build the page perf-latest-4424-4901-vs-main-20261016.html from data.json."""
import json, sys
from pathlib import Path
H = Path(__file__).parent
data = json.loads((H / "data.json").read_text())
OUT = H.parent.parent / "perf-latest-4424-4901-vs-main-20261016.html"

def pretty(cell):
    m = {"llama-3.2-3b-instruct-fast": "llama-3.2-3b", "llama-3.1-8b-instruct-good": "llama-3.1-8b",
         "llama-3.3-70b-instruct-good": "llama-3.3-70b", "mixtral-8x7b-instruct-v0.1": "mixtral-8x7b",
         "qwen-2.5-32b-it-fast": "qwen-2.5-32b", "ingested-qwen-3-4b-instruct-2507": "qwen3-4b",
         "gemma-2-9b-it-fast": "gemma-2-9b", "ingested-gpt-oss-120b": "gpt-oss-120b",
         "ingested-gemma-4-31b-it": "gemma-4-31b", "ingested-meta-models--Muse-Glimmer-30B": "Muse-Glimmer-30B",
         "q3-4b": "qwen3-4b"}
    if "@" in cell:
        model_tp, rest = cell.split("@")
        model, tp = model_tp.rsplit("-tp", 1)
        users, prompt = rest.split("-p")
        users = users.rstrip("u")
    else:
        model, tp, users, prompt = cell.split("-tp")[0], cell.split("-tp")[1].split("-")[0], cell.split("-")[-2].rstrip("u"), cell.split("-p")[-1]
    return f"{m.get(model, model)} tp{tp}, {users} users, prompt {int(prompt):,}"

for pr in data.values():
    for rows in pr.values():
        for r in rows:
            r["name"] = pretty(r["cell"])

page = r"""<title>Latest PR vs main performance</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one column of reading width for prose, full-width panels for the charts and tables. Single light theme by the reader's standing rule. */
:root {
  color-scheme: light;
  --bg: #fbfbf9; --panel: #ffffff; --ink: #14140f; --ink-2: #55544c; --ink-3: #8a897f;
  --rule: #dcdbd3; --rule-2: #ecebe4;
  --s1: #2a78d6; --s2: #eb6834; --band: #e7e6df; --zero: #9b9a90;
  --good-bg: #e9f4ea; --flag-bg: #fdf1e8;
  --sans: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
}
body { background: var(--bg); color: var(--ink); font-family: var(--sans); line-height: 1.5;
  padding-block: 28px 56px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
main { max-width: 1040px; margin: 0 auto; display: grid; gap: 28px; }
h1 { font-size: 1.7rem; font-weight: 600; margin: 0; letter-spacing: -0.01em; text-wrap: balance; }
h2 { font-size: 1.25rem; font-weight: 600; margin: 0 0 6px; text-wrap: balance; }
h3 { font-size: 1rem; font-weight: 600; margin: 18px 0 6px; }
p { max-width: 70ch; margin: 0 0 10px; }
.eyebrow { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-3); margin-bottom: 4px; }
.short { border-left: 3px solid var(--s1); padding: 10px 16px; background: var(--panel); border-radius: 0 6px 6px 0; }
.short p { margin: 0 0 6px; }
.panel { background: var(--panel); border: 1px solid var(--rule); border-radius: 8px; padding: 18px 20px; min-width: 0; }
.chartwrap { overflow-x: auto; margin: 8px 0 4px; }
svg.dots { display: block; min-width: 760px; width: 100%; height: auto; font-family: var(--sans); }
svg.dots text { fill: var(--ink); font-size: 12.5px; }
svg.dots .lab { fill: var(--ink-2); }
svg.dots .grp { fill: var(--ink); font-weight: 600; font-size: 12px; }
svg.dots .axis { fill: var(--ink-3); font-size: 11px; }
svg.dots .val { font-family: var(--mono); font-size: 11.5px; }
svg.dots .sub { fill: var(--ink-3); font-size: 10.5px; font-family: var(--mono); }
svg.dots .hdr { fill: var(--ink-2); font-size: 11.5px; font-weight: 600; }
.legend { display: flex; flex-wrap: wrap; gap: 18px; font-size: 0.85rem; color: var(--ink-2); margin: 4px 0 2px; align-items: center; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; border: 2px solid var(--s1); box-sizing: border-box; }
.dot.f { background: var(--s1); } .dot.o { background: var(--s2); border-color: var(--s2); }
.bandkey { width: 22px; height: 11px; background: var(--band); display: inline-block; }
.take { font-size: 0.95rem; margin-top: 8px; padding: 8px 12px; background: var(--good-bg); border-radius: 6px; max-width: none; }
.flag { font-size: 0.95rem; padding: 8px 12px; background: var(--flag-bg); border-radius: 6px; max-width: none; }
.tip { position: fixed; pointer-events: none; background: var(--ink); color: #fff; font-size: 12px; padding: 6px 9px; border-radius: 4px; font-family: var(--mono); white-space: pre; display: none; z-index: 5; }
table { border-collapse: collapse; width: 100%; font-size: 0.84rem; font-variant-numeric: tabular-nums; }
.tablewrap { overflow-x: auto; }
th, td { text-align: right; padding: 5px 8px; border-bottom: 1px solid var(--rule-2); white-space: nowrap; }
th { color: var(--ink-2); font-weight: 600; border-bottom: 1px solid var(--rule); }
td:first-child, th:first-child { text-align: left; }
td.y { font-weight: 600; }
td.n { color: var(--ink-3); }
.num { font-family: var(--mono); }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 6px 14px; margin: 0; font-size: 0.9rem; }
dt { font-weight: 600; } dd { margin: 0; max-width: 80ch; }
ul { margin: 0 0 10px; padding-left: 20px; max-width: 80ch; } li { margin-bottom: 4px; }
details summary { cursor: pointer; font-weight: 600; margin: 6px 0; }
@media (max-width: 640px) { dl { grid-template-columns: 1fr; } }
</style>

<main>
<header>
  <div class="eyebrow">Positron tron, VNNI K stack, record of 2026-10-16</div>
  <h1>Latest decode and prefill results: PR 4424 and PR 4901 against main</h1>
</header>

<section class="short">
  <div class="eyebrow">Short version</div>
  <p>Both PRs speed up decode where the K cache is read many times per step, and leave the other models inside the noise. PR 4424 was measured on all 14 nightly models plus two software-attention cells on 2026-10-09 (one resolved loss: llama-3.2-3b at 32 users, -1.4 %). PR 4901 was measured on three nightly cells and eight qwen3-4b cells on 2026-10-12 to 2026-10-14, with the same direction and the same resolution as PR 4424 in every shared cell; the other 11 nightly models have no PR 4901 measurement.</p>
</section>

<section class="panel">
  <h2>Words used here</h2>
  <dl>
    <dt>tron, rinzler, runtron</dt><dd>tron is the inference program under test, rinzler its production server binary, runtron its command-line benchmark tool.</dd>
    <dt>PR 4424</dt><dd>The original VNNI K pull request (branch jhan-amx-vnniK, head 0a5334ccb6). Measured at 9d5c7a389b plus the deb-preset commit, which is the same content as the head.</dd>
    <dt>PR 4901</dt><dd>The fourth PR of the split stack (tail block, option on in the deb preset). Closed on 2026-10-15 and re-opened as PR 4959 on the same branch; the measurements below are at ea94e95a4e (2026-10-12), five commits before the current head 6b081187e1 (a benchmark-row refresh, one test, comment and naming edits, and a merge of the parent branch).</dd>
    <dt>main</dt><dd>The base of each comparison: the nightly package of main at be0d5565b3 (2026-10-08) for PR 4424, and a package of main at 72308ec90c (2026-10-12) for PR 4901. The two bases are different revisions, so the two PRs' absolute values are not comparable with each other, only their deltas against their own base.</dd>
    <dt>TPS</dt><dd>Decode speed, generated tokens per second per user. Higher is better.</dd>
    <dt>TTFT</dt><dd>Time to first token, the prefill time in milliseconds (the harness) or the slowest user's prefill time (runtron). Lower is better.</dd>
    <dt>AoF, FPGA attention</dt><dd>Attention on the FPGA cards, the production default (USE_HW_ATTN unset). The nightly harness runs this way.</dd>
    <dt>sw attention, CPU attention</dt><dd>Attention computed in software on the CPU (USE_HW_ATTN=0). This is the path the VNNI K layout and the AMX kernel change; the FPGA path only gathers K.</dd>
    <dt>AMX</dt><dd>Intel Advanced Matrix Extensions, the CPU tile instructions the new QK kernel uses. "AMX off" = the kill switch TRON_AMX_DISABLE=1 on both binaries.</dd>
    <dt>tp, users, prompt</dt><dd>tp = tensor-parallel degree (engines per model); users = concurrent requests; prompt = prompt length in tokens. Every run then generates a fixed number of tokens.</dd>
    <dt>resolved (harness)</dt><dd>The nightly harness's rule: a paired t statistic of at least 2.26 in magnitude over 20 round pairs (two passes per arm, 10 rounds each) and a change of at least 1 % (TTFT also at least 1 ms). Anything else is reported as noise.</dd>
    <dt>beyond the band (runtron)</dt><dd>The runtron rule from the PR bodies: 3 repetitions per arm in alternating order; the band is twice the larger of the two arms' sample standard deviations, never under 0.4 TPS or 0.15 s. A difference beyond the band counts as a change.</dd>
    <dt>deb</dt><dd>The Debian package of tron that the nightly installs; the harness campaigns compare two packages, the runtron campaigns compare two runtron binaries.</dd>
  </dl>
</section>

<section class="panel" id="pr4424">
  <div class="eyebrow">Campaign records pr4424ci-20261009 (harness, 2026-10-09) and m4737-E-cpu (runtron, 2026-10-09)</div>
  <h2>PR 4424 against main: 17 cells</h2>
  <p>Filled dots are resolved changes (harness rule) or changes beyond the band (runtron rule). Hollow dots are noise. The grey strip on the runtron rows is the band, converted to percent of the base value. The harness rows have no strip because their rule is a t statistic, not a band.</p>
  <div class="legend"><span><i class="dot f"></i> resolved / beyond the band</span><span><i class="dot"></i> noise</span><span><i class="bandkey"></i> runtron band</span><span>label = base to PR, then the change</span></div>
  <div class="chartwrap"><svg class="dots" id="c4424"></svg></div>
  <p class="take">Takeaway: three decode cells moved up (llama-3.1-8b 32 users +4.8 %, Muse-Glimmer-30B +2.4 %, qwen3-4b software attention +7.6 % at prompt 8,192 and +5.1 % / +10.3 % in the runtron cells). One moved down: llama-3.2-3b at 32 users, prompt 200, -1.4 % (t -16.6). gpt-oss-120b, both qwen3-4b FPGA cells, and the other nine models are noise. TTFT: two resolved improvements (Muse-Glimmer -118 ms, qwen3-4b sw -150 ms), no resolved loss.</p>
  <details><summary>Exact values, PR 4424 against main</summary><div class="tablewrap" id="t4424"></div></details>
</section>

<section class="panel" id="pr4901">
  <div class="eyebrow">Campaign records pr4ci-20261012 (harness, 2026-10-13), pr4-20261012 (runtron, 2026-10-12) and pr4off-20261014 (runtron, AMX off, 2026-10-14)</div>
  <h2>PR 4901 against main: 11 cells</h2>
  <p>Same marks as above. The AMX-off rows run the kill switch on both binaries, so they measure the layout and conversion code alone, without the AMX kernel.</p>
  <div class="legend"><span><i class="dot f"></i> resolved / beyond the band</span><span><i class="dot"></i> noise</span><span><i class="bandkey"></i> runtron band</span></div>
  <div class="chartwrap"><svg class="dots" id="c4901"></svg></div>
  <p class="take">Takeaway: decode gains in the same cells as PR 4424 (llama-3.1-8b 32 users +5.2 %, qwen3-4b software attention +4.7 % / +9.4 % / +2.4 %). gpt-oss-120b, llama-3.1-8b at 8 users and both qwen3-4b FPGA cells are noise, where PR 4424's FPGA cells were also noise. With AMX off on both binaries, decode is inside the band in all three cells and TTFT at prompt 8,192 is 4.98 s faster. TTFT with AMX on: one beyond-band improvement (qwen3-4b CPU, prompt 8,192, -697 ms), no loss.</p>
  <p class="flag">Not measured for PR 4901 against main: llama-3.2-3b, llama-3.3-70b (three cells), mixtral-8x7b, qwen-2.5-32b, gemma-2-9b, gemma-4-31b, Muse-Glimmer-30B, the harness's two qwen3-4b FPGA cells, and the harness's qwen3-4b software-attention cell at prompt 8,192 (SW8K=0, jhan's scope of 2026-10-12). Insufficient data for those models; the nearest evidence is PR 4424's run above, which carries the same kernels plus the parent PRs' code. Also not measured at the current head 6b081187e1 (PR 4959).</p>
  <details><summary>Exact values, PR 4901 against main</summary><div class="tablewrap" id="t4901"></div></details>
</section>

<section class="panel" id="shared">
  <div class="eyebrow">The cells both PRs have, harness rule</div>
  <h2>Same three nightly cells, both PRs</h2>
  <div class="legend"><span><i class="dot f"></i> PR 4424 (2026-10-09, base be0d5565b3)</span><span><i class="dot o"></i> PR 4901 (2026-10-13, base 72308ec90c)</span><span>filled = resolved, hollow = noise</span></div>
  <div class="chartwrap"><svg class="dots" id="cshared"></svg></div>
  <p class="take">Takeaway: same direction and same resolution in every shared cell. Only the llama-3.1-8b 32-user cell resolves, and PR 4901 keeps that gain (+5.2 % against +4.8 %). The base levels differ (llama-3.1-8b 8 users: 143.0 against 150.8 TPS) because the two bases are different main revisions, so the two campaigns are compared cell by cell, not subtracted.</p>
</section>

<section class="panel">
  <h2>How to read the two rules</h2>
  <ul>
    <li><b>Harness campaigns</b> (pr4424ci-20261009, pr4ci-20261012) install the two deb packages in turn on the whole of delphi-3bda (the Intel Xeon 6 test server) and run the nightly perf phase: four passes in the order base, target, target, base, 10 rounds per pass. TPS is the mean over the two passes of one arm; the parenthesised sd in the tables is the spread over those two passes.</li>
    <li><b>runtron campaigns</b> (m4737-E-cpu, pr4-E-cpu, pr4-E-fpga, pr4off-E-cpu) run runtron with qwen3-4b, 8 users, 256 generated tokens, 3 repetitions per arm in alternating order on the same server. The band is the PR body's rule (twice the larger sd, floored at 0.4 TPS and 0.15 s).</li>
    <li>Anomalous samples in pr4ci-20261012 (talos burst detections of 16 tokens in a few ms): llama 8 users 16 per pass in both arms; gpt-oss base 1 and 10 (base-pass2 within-pass sd 6.50 TPS), target 0 and 0 [exec/results/pr4ci-20261012/summary.md]. They widen the noise of those two cells and do not change the verdicts.</li>
    <li>Source files: exec/results/pr4424ci-20261009/summary.md, exec/results/m4737-E-cpu/summary.md, exec/results/pr4ci-20261012/summary.md, exec/results/pr4-E-cpu/summary.md, exec/results/pr4-E-fpga/summary.md, exec/results/pr4off-E-cpu/summary.md. Rebuild: exec/perf-latest-20261016/collect.py then build.py under split-4424.</li>
  </ul>
</section>
</main>
<div class="tip" id="tip"></div>

<script>
const DATA = __DATA__;
const S1 = "#2a78d6", S2 = "#eb6834";
const fmt = (x, d=1) => (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(d);
const tip = document.getElementById("tip");
function showTip(e, text){ tip.textContent = text; tip.style.display = "block"; moveTip(e); }
function moveTip(e){ tip.style.left = (e.clientX + 14) + "px"; tip.style.top = (e.clientY + 14) + "px"; }
function hideTip(){ tip.style.display = "none"; }

// groups: [{title, rows, kind: 'harness'|'runtron'}]; one row = one cell; two columns: TPS delta %, TTFT delta %
function dotChart(id, groups, opts){
  const svg = document.getElementById(id);
  const ns = "http://www.w3.org/2000/svg";
  const el = (n, a, parent) => { const x = document.createElementNS(ns, n); for (const k in a) x.setAttribute(k, a[k]); (parent||svg).appendChild(x); return x; };
  const W = 980, labW = 250, gap = 40, colW = (W - labW - gap*2) / 2, rowH = 30, grpH = 26, top = 34;
  const cols = [{key:"tps", title:"Decode TPS, change vs main (%)"}, {key:"ttft", title:"TTFT, change vs main (%)"}];
  const allRows = groups.flatMap(g => g.rows);
  const dom = {};
  for (const c of cols) {
    let m = 0; for (const r of allRows) for (const s of (r.series||[r])) m = Math.max(m, Math.abs(s[c.key+"_delta_pct"]), (s["band_"+c.key+"_pct"]||0));
    dom[c.key] = Math.ceil((m * 1.15) / 2) * 2 || 2;
  }
  let y = top;
  const nRows = allRows.length + groups.length;
  const H = top + groups.reduce((a,g)=>a + grpH + g.rows.length*rowH, 0) + 26;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  cols.forEach((c, i) => {
    const x0 = labW + i*(colW+gap);
    el("text", {x: x0 + colW/2, y: 16, "text-anchor":"middle", class:"hdr"}).textContent = c.title;
    const sc = v => x0 + (v + dom[c.key]) / (2*dom[c.key]) * colW;
    const step = dom[c.key] <= 4 ? 1 : dom[c.key] <= 12 ? 2 : 5;
    for (let v = -dom[c.key]; v <= dom[c.key] + 1e-9; v += step) {
      el("line", {x1: sc(v), x2: sc(v), y1: top - 6, y2: H - 20, stroke: v === 0 ? "#9b9a90" : "#ecebe4", "stroke-width": v === 0 ? 1.5 : 1});
      el("text", {x: sc(v), y: H - 6, "text-anchor":"middle", class:"axis"}).textContent = fmt(v, 0);
    }
    c.sc = sc; c.x0 = x0;
  });
  for (const g of groups) {
    y += grpH;
    el("text", {x: 0, y: y - 8, class:"grp"}).textContent = g.title;
    for (const r of g.rows) {
      const cy = y + rowH/2 - 2;
      el("text", {x: 0, y: cy + 4, class:"lab"}).textContent = r.name;
      el("line", {x1: 0, x2: W, y1: y + rowH - 2, y2: y + rowH - 2, stroke: "#f1f0ea"});
      for (const c of cols) {
        const series = r.series || [r];
        series.forEach((s, si) => {
          const k = c.key, v = s[k+"_delta_pct"], res = s[k+"_resolved"];
          if (s["band_"+k+"_pct"] != null) {
            const b = s["band_"+k+"_pct"];
            el("rect", {x: c.sc(-b), y: cy - 7, width: c.sc(b) - c.sc(-b), height: 14, fill: "#e7e6df"});
          }
          const color = s.color || S1;
          const cx = c.sc(v), oy = series.length > 1 ? (si === 0 ? -5 : 5) : 0;
          const dot = el("circle", {cx, cy: cy + oy, r: 5.5, fill: res ? color : "#ffffff", stroke: color, "stroke-width": 2});
          const base = s.base_tps, tgt = s.target_tps;
          let labText, sub;
          if (k === "tps") { labText = fmt(v) + " %"; sub = `${base.toFixed(1)} → ${tgt.toFixed(1)}`; }
          else { labText = fmt(s.ttft_delta_ms, 0) + " ms"; sub = `${Math.round(s.base_ttft_ms).toLocaleString()} → ${Math.round(s.target_ttft_ms).toLocaleString()}`; }
          if (series.length === 1) {
            const right = cx < c.x0 + colW*0.6;
            const tx = right ? cx + 10 : cx - 10;
            const t = el("text", {x: tx, y: cy + 4, "text-anchor": right ? "start" : "end", class:"val", "font-weight": res ? "600" : "400"});
            t.textContent = labText;
            const t2 = el("text", {x: right ? tx + (labText.length*7.2+6) : tx - (labText.length*7.2+6), y: cy + 4, "text-anchor": right ? "start" : "end", class:"sub"});
            t2.textContent = sub;
          } else {
            const right = cx < c.x0 + colW*0.6;
            const t = el("text", {x: right ? cx + 10 : cx - 10, y: cy + 4 + oy, "text-anchor": right ? "start" : "end", class:"val", "font-weight": res ? "600":"400"});
            t.textContent = labText + "  " + s.tag;
          }
          const hit = el("rect", {x: cx - 12, y: cy - 12 + oy, width: 24, height: 24, fill: "transparent"});
          const text = (s.pair ? s.pair + "\n" : "") + r.name + "\n" +
            (k === "tps" ? `TPS ${base.toFixed(2)} → ${tgt.toFixed(2)} (${fmt(v)} %)` : `TTFT ${s.base_ttft_ms} → ${s.target_ttft_ms} ms (${fmt(v)} %)`) + "\n" +
            (s.kind === "harness" ? `paired t ${fmt(k==="tps" ? s.tps_t : s.ttft_t, 2)} over 20 round pairs, ${res ? "RESOLVED" : "not resolved"}` :
             `band ±${k==="tps" ? s.band_tps + " TPS" : s.band_ttft_ms + " ms"}, n = ${s.n}, ${res ? "beyond the band" : "inside the band"}`);
          hit.addEventListener("mousemove", e => showTip(e, text)); hit.addEventListener("mouseleave", hideTip);
          dot.addEventListener("mousemove", e => showTip(e, text)); dot.addEventListener("mouseleave", hideTip);
        });
      }
      y += rowH;
    }
  }
}
function prep(rows, kind){ return rows.map(r => { r.kind = kind; if (r.band_tps != null) { r.band_tps_pct = r.band_tps / r.base_tps * 100; r.band_ttft_pct = r.band_ttft_ms / r.base_ttft_ms * 100; } return r; }); }

const P1 = DATA.pr4424, P2 = DATA.pr4901;
dotChart("c4424", [
  {title: "Nightly harness, FPGA attention (AoF), as shipped", rows: prep(P1.harness.filter(r => r.attn === "fpga"), "harness")},
  {title: "Nightly harness, software attention (USE_HW_ATTN=0)", rows: prep(P1.harness.filter(r => r.attn === "sw"), "harness")},
  {title: "runtron, qwen3-4b, CPU (software) attention", rows: prep(P1.runtron_cpu, "runtron")},
]);
dotChart("c4901", [
  {title: "Nightly harness (deb packages), FPGA attention (AoF)", rows: prep(P2.harness, "harness")},
  {title: "runtron, qwen3-4b, CPU (software) attention", rows: prep(P2.runtron_cpu, "runtron")},
  {title: "runtron, qwen3-4b, FPGA attention (AoF)", rows: prep(P2.runtron_fpga, "runtron")},
  {title: "runtron, qwen3-4b, CPU attention, AMX off on both binaries", rows: prep(P2.runtron_off, "runtron")},
]);
const sharedCells = P2.harness.map(r => r.cell);
dotChart("cshared", [{title: "Nightly harness, FPGA attention", rows: sharedCells.map(c => {
  const a = P1.harness.find(r => r.cell === c), b = P2.harness.find(r => r.cell === c);
  return {name: a.name, series: [Object.assign({}, a, {color: S1, tag: "PR 4424", kind: "harness", pair: "PR 4424 vs main"}), Object.assign({}, b, {color: S2, tag: "PR 4901", kind: "harness", pair: "PR 4901 vs main"})]};
})}]);

function table(id, groups){
  const h = ["cell", "attention", "rule", "base TPS", "PR TPS", "TPS change", "verdict", "base TTFT ms", "PR TTFT ms", "TTFT change", "verdict"];
  let s = "<table><thead><tr>" + h.map(x => `<th>${x}</th>`).join("") + "</tr></thead><tbody>";
  for (const g of groups) {
    s += `<tr><th colspan="11" style="text-align:left">${g.title}</th></tr>`;
    for (const r of g.rows) {
      const rule = r.kind === "harness" ? `t ${fmt(r.tps_t,2)} / t ${fmt(r.ttft_t,2)}` : `band ${r.band_tps} TPS / ${r.band_ttft_ms} ms`;
      const sdb = r.kind === "harness" ? ` (${r.base_sd.toFixed(2)})` : ` (${r.base_sd.toFixed(2)})`, sdt = ` (${r.target_sd.toFixed(2)})`;
      s += `<tr><td>${r.name}</td><td>${r.attn === "sw" || r.attn === "cpu" ? "software (CPU)" : "FPGA"}${r.pair && r.pair.includes("off") ? ", AMX off" : ""}</td><td class="num">${rule}</td>` +
        `<td class="num">${r.base_tps.toFixed(2)}${sdb}</td><td class="num">${r.target_tps.toFixed(2)}${sdt}</td><td class="num">${fmt(r.tps_delta_pct)} %</td><td class="${r.tps_resolved?"y":"n"}">${r.tps_resolved ? (r.kind==="harness"?"resolved":"beyond band") : "noise"}</td>` +
        `<td class="num">${Math.round(r.base_ttft_ms).toLocaleString()}</td><td class="num">${Math.round(r.target_ttft_ms).toLocaleString()}</td><td class="num">${fmt(r.ttft_delta_ms,0)} ms (${fmt(r.ttft_delta_pct)} %)</td><td class="${r.ttft_resolved?"y":"n"}">${r.ttft_resolved ? (r.kind==="harness"?"resolved":"beyond band") : "noise"}</td></tr>`;
    }
  }
  s += "</tbody></table><p style='font-size:0.8rem;color:var(--ink-3);margin-top:6px'>Parenthesised values after TPS: the harness rows give the sd over the two passes, the runtron rows the sample sd over 3 repetitions. The harness rows' TTFT is the mean over passes; the runtron rows' TTFT is the slowest user's prefill, mean over repetitions, and its change is the paired mean from the record.</p>";
  document.getElementById(id).innerHTML = s;
}
table("t4424", [
  {title: "Nightly harness, FPGA attention", rows: P1.harness.filter(r => r.attn === "fpga")},
  {title: "Nightly harness, software attention at prompt 8,192", rows: P1.harness.filter(r => r.attn === "sw")},
  {title: "runtron, qwen3-4b, CPU attention (record m4737-E-cpu)", rows: P1.runtron_cpu},
]);
table("t4901", [
  {title: "Nightly harness (deb packages), FPGA attention (record pr4ci-20261012)", rows: P2.harness},
  {title: "runtron, qwen3-4b, CPU attention (record pr4-E-cpu)", rows: P2.runtron_cpu},
  {title: "runtron, qwen3-4b, FPGA attention (record pr4-E-fpga)", rows: P2.runtron_fpga},
  {title: "runtron, qwen3-4b, CPU attention, AMX off on both (record pr4off-E-cpu)", rows: P2.runtron_off},
]);
</script>
"""
OUT.write_text(page.replace("__DATA__", json.dumps(data)))
print("wrote", OUT, OUT.stat().st_size, "bytes")
