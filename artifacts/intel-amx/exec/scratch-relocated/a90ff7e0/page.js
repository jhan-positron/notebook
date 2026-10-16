
const DATA = {"pr4424": {"harness": [{"cell": "llama-3.2-3b-instruct-fast-tp2@32u-p200", "attn": "fpga", "base_tps": 198.26, "target_tps": 195.56, "base_sd": 0.4, "target_sd": 0.44, "tps_delta_pct": -1.4, "tps_t": -16.56, "tps_resolved": true, "base_ttft_ms": 74.0, "target_ttft_ms": 58.0, "ttft_delta_ms": -15.0, "ttft_delta_pct": -20.8, "ttft_t": -1.47, "ttft_resolved": false, "name": "llama-3.2-3b tp2, 32 users, prompt 200"}, {"cell": "llama-3.1-8b-instruct-good-tp2@8u-p1024", "attn": "fpga", "base_tps": 143.03, "target_tps": 142.58, "base_sd": 0.55, "target_sd": 0.57, "tps_delta_pct": -0.3, "tps_t": -1.35, "tps_resolved": false, "base_ttft_ms": 586.0, "target_ttft_ms": 585.0, "ttft_delta_ms": -0.0, "ttft_delta_pct": -0.1, "ttft_t": -0.05, "ttft_resolved": false, "name": "llama-3.1-8b tp2, 8 users, prompt 1,024"}, {"cell": "llama-3.1-8b-instruct-good-tp2@32u-p4096", "attn": "fpga", "base_tps": 32.62, "target_tps": 34.2, "base_sd": 0.02, "target_sd": 0.03, "tps_delta_pct": 4.8, "tps_t": 39.4, "tps_resolved": true, "base_ttft_ms": 11821.0, "target_ttft_ms": 11833.0, "ttft_delta_ms": 12.0, "ttft_delta_pct": 0.1, "ttft_t": 0.66, "ttft_resolved": false, "name": "llama-3.1-8b tp2, 32 users, prompt 4,096"}, {"cell": "llama-3.3-70b-instruct-good-tp2@8u-p1024", "attn": "fpga", "base_tps": 17.01, "target_tps": 17.0, "base_sd": 0.01, "target_sd": 0.01, "tps_delta_pct": -0.0, "tps_t": -2.11, "tps_resolved": false, "base_ttft_ms": 9382.0, "target_ttft_ms": 9393.0, "ttft_delta_ms": 11.0, "ttft_delta_pct": 0.1, "ttft_t": 0.98, "ttft_resolved": false, "name": "llama-3.3-70b tp2, 8 users, prompt 1,024"}, {"cell": "llama-3.3-70b-instruct-good-tp2@4u-p1024", "attn": "fpga", "base_tps": 28.46, "target_tps": 28.68, "base_sd": 0.0, "target_sd": 0.04, "tps_delta_pct": 0.8, "tps_t": 13.14, "tps_resolved": false, "base_ttft_ms": 4086.0, "target_ttft_ms": 4457.0, "ttft_delta_ms": 371.0, "ttft_delta_pct": 9.1, "ttft_t": 1.05, "ttft_resolved": false, "name": "llama-3.3-70b tp2, 4 users, prompt 1,024"}, {"cell": "llama-3.3-70b-instruct-good-tp4@4u-p1024", "attn": "fpga", "base_tps": 31.71, "target_tps": 31.67, "base_sd": 0.0, "target_sd": 0.09, "tps_delta_pct": -0.1, "tps_t": -0.77, "tps_resolved": false, "base_ttft_ms": 4875.0, "target_ttft_ms": 4874.0, "ttft_delta_ms": -1.0, "ttft_delta_pct": -0.0, "ttft_t": -0.16, "ttft_resolved": false, "name": "llama-3.3-70b tp4, 4 users, prompt 1,024"}, {"cell": "mixtral-8x7b-instruct-v0.1-tp2@8u-p1024", "attn": "fpga", "base_tps": 80.68, "target_tps": 80.62, "base_sd": 0.31, "target_sd": 0.23, "tps_delta_pct": -0.1, "tps_t": -0.16, "tps_resolved": false, "base_ttft_ms": 1259.0, "target_ttft_ms": 1264.0, "ttft_delta_ms": 5.0, "ttft_delta_pct": 0.4, "ttft_t": 2.24, "ttft_resolved": false, "name": "mixtral-8x7b tp2, 8 users, prompt 1,024"}, {"cell": "qwen-2.5-32b-it-fast-tp2@8u-p1024", "attn": "fpga", "base_tps": 36.06, "target_tps": 36.02, "base_sd": 0.04, "target_sd": 0.01, "tps_delta_pct": -0.1, "tps_t": -2.6, "tps_resolved": false, "base_ttft_ms": 3946.0, "target_ttft_ms": 3939.0, "ttft_delta_ms": -7.0, "ttft_delta_pct": -0.2, "ttft_t": -1.11, "ttft_resolved": false, "name": "qwen-2.5-32b tp2, 8 users, prompt 1,024"}, {"cell": "ingested-qwen-3-4b-instruct-2507-tp2@8u-p1024", "attn": "fpga", "base_tps": 189.13, "target_tps": 187.38, "base_sd": 1.04, "target_sd": 0.68, "tps_delta_pct": -0.9, "tps_t": -2.19, "tps_resolved": false, "base_ttft_ms": 502.0, "target_ttft_ms": 494.0, "ttft_delta_ms": -8.0, "ttft_delta_pct": -1.6, "ttft_t": -1.01, "ttft_resolved": false, "name": "qwen3-4b tp2, 8 users, prompt 1,024"}, {"cell": "ingested-qwen-3-4b-instruct-2507-tp4@8u-p1024", "attn": "fpga", "base_tps": 181.01, "target_tps": 180.3, "base_sd": 0.44, "target_sd": 0.55, "tps_delta_pct": -0.4, "tps_t": -0.42, "tps_resolved": false, "base_ttft_ms": 557.0, "target_ttft_ms": 545.0, "ttft_delta_ms": -12.0, "ttft_delta_pct": -2.1, "ttft_t": -0.76, "ttft_resolved": false, "name": "qwen3-4b tp4, 8 users, prompt 1,024"}, {"cell": "gemma-2-9b-it-fast-tp2@8u-p1024", "attn": "fpga", "base_tps": 104.03, "target_tps": 104.84, "base_sd": 0.12, "target_sd": 1.06, "tps_delta_pct": 0.8, "tps_t": 0.97, "tps_resolved": false, "base_ttft_ms": 856.0, "target_ttft_ms": 852.0, "ttft_delta_ms": -5.0, "ttft_delta_pct": -0.5, "ttft_t": -1.73, "ttft_resolved": false, "name": "gemma-2-9b tp2, 8 users, prompt 1,024"}, {"cell": "ingested-gpt-oss-120b-tp4@8u-p1024", "attn": "fpga", "base_tps": 122.38, "target_tps": 121.83, "base_sd": 0.05, "target_sd": 1.34, "tps_delta_pct": -0.5, "tps_t": -1.28, "tps_resolved": false, "base_ttft_ms": 966.0, "target_ttft_ms": 944.0, "ttft_delta_ms": -22.0, "ttft_delta_pct": -2.3, "ttft_t": -1.93, "ttft_resolved": false, "name": "gpt-oss-120b tp4, 8 users, prompt 1,024"}, {"cell": "ingested-gemma-4-31b-it-tp2@8u-p1024", "attn": "fpga", "base_tps": 38.21, "target_tps": 38.23, "base_sd": 0.02, "target_sd": 0.04, "tps_delta_pct": 0.1, "tps_t": 0.7, "tps_resolved": false, "base_ttft_ms": 5456.0, "target_ttft_ms": 5448.0, "ttft_delta_ms": -8.0, "ttft_delta_pct": -0.1, "ttft_t": -1.57, "ttft_resolved": false, "name": "gemma-4-31b tp2, 8 users, prompt 1,024"}, {"cell": "ingested-meta-models--Muse-Glimmer-30B-tp4@8u-p1024", "attn": "fpga", "base_tps": 74.72, "target_tps": 76.53, "base_sd": 0.02, "target_sd": 0.15, "tps_delta_pct": 2.4, "tps_t": 24.35, "tps_resolved": true, "base_ttft_ms": 3720.0, "target_ttft_ms": 3602.0, "ttft_delta_ms": -118.0, "ttft_delta_pct": -3.2, "ttft_t": -25.9, "ttft_resolved": true, "name": "Muse-Glimmer-30B tp4, 8 users, prompt 1,024"}, {"cell": "ingested-qwen-3-4b-instruct-2507-tp2@8u-p8192", "attn": "sw", "base_tps": 59.84, "target_tps": 64.41, "base_sd": 0.2, "target_sd": 0.26, "tps_delta_pct": 7.6, "tps_t": 39.27, "tps_resolved": true, "base_ttft_ms": 12957.0, "target_ttft_ms": 12807.0, "ttft_delta_ms": -150.0, "ttft_delta_pct": -1.2, "ttft_t": -8.97, "ttft_resolved": true, "name": "qwen3-4b tp2, 8 users, prompt 8,192"}], "runtron_cpu": [{"cell": "q3-4b-tp2-8u-p1024", "attn": "cpu", "pair": "PR 4424 vs main", "base_tps": 79.1, "target_tps": 83.14, "base_sd": 0.29, "target_sd": 0.47, "tps_delta_pct": 5.1, "tps_delta": 4.04, "band_tps": 0.94, "tps_resolved": true, "base_ttft_ms": 3177, "target_ttft_ms": 3133, "ttft_delta_ms": -45.0, "ttft_delta_pct": -1.4, "band_ttft_ms": 150, "ttft_resolved": false, "n": 3, "base_commit": "be0d5565b3", "target_commit": "9d5c7a389b", "name": "qwen3-4b tp2, 8 users, prompt 1,024"}, {"cell": "q3-4b-tp2-8u-p8192", "attn": "cpu", "pair": "PR 4424 vs main", "base_tps": 17.1, "target_tps": 18.87, "base_sd": 0.03, "target_sd": 0.02, "tps_delta_pct": 10.3, "tps_delta": 1.77, "band_tps": 0.4, "tps_resolved": true, "base_ttft_ms": 52584, "target_ttft_ms": 52040, "ttft_delta_ms": -543.0, "ttft_delta_pct": -1.0, "band_ttft_ms": 192, "ttft_resolved": true, "n": 3, "base_commit": "be0d5565b3", "target_commit": "9d5c7a389b", "name": "qwen3-4b tp2, 8 users, prompt 8,192"}]}, "pr4901": {"harness": [{"cell": "llama-3.1-8b-instruct-good-tp2@8u-p1024", "attn": "fpga", "base_tps": 150.78, "target_tps": 150.15, "base_sd": 0.08, "target_sd": 0.33, "tps_delta_pct": -0.4, "tps_t": -1.05, "tps_resolved": false, "base_ttft_ms": 572.0, "target_ttft_ms": 586.0, "ttft_delta_ms": 14.0, "ttft_delta_pct": 2.5, "ttft_t": 2.08, "ttft_resolved": false, "name": "llama-3.1-8b tp2, 8 users, prompt 1,024"}, {"cell": "llama-3.1-8b-instruct-good-tp2@32u-p4096", "attn": "fpga", "base_tps": 32.73, "target_tps": 34.42, "base_sd": 0.0, "target_sd": 0.05, "tps_delta_pct": 5.2, "tps_t": 53.81, "tps_resolved": true, "base_ttft_ms": 11670.0, "target_ttft_ms": 11653.0, "ttft_delta_ms": -17.0, "ttft_delta_pct": -0.1, "ttft_t": -1.37, "ttft_resolved": false, "name": "llama-3.1-8b tp2, 32 users, prompt 4,096"}, {"cell": "ingested-gpt-oss-120b-tp4@8u-p1024", "attn": "fpga", "base_tps": 123.49, "target_tps": 123.11, "base_sd": 0.9, "target_sd": 0.07, "tps_delta_pct": -0.3, "tps_t": -0.59, "tps_resolved": false, "base_ttft_ms": 969.0, "target_ttft_ms": 972.0, "ttft_delta_ms": 4.0, "ttft_delta_pct": 0.4, "ttft_t": 0.58, "ttft_resolved": false, "name": "gpt-oss-120b tp4, 8 users, prompt 1,024"}], "runtron_cpu": [{"cell": "q3-4b-tp2-8u-p1024", "attn": "cpu", "pair": "PR 4901 vs main", "base_tps": 80.98, "target_tps": 84.75, "base_sd": 0.1, "target_sd": 0.12, "tps_delta_pct": 4.7, "tps_delta": 3.77, "band_tps": 0.4, "tps_resolved": true, "base_ttft_ms": 3181, "target_ttft_ms": 3125, "ttft_delta_ms": -56.0, "ttft_delta_pct": -1.8, "band_ttft_ms": 150, "ttft_resolved": false, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp2, 8 users, prompt 1,024"}, {"cell": "q3-4b-tp2-8u-p8192", "attn": "cpu", "pair": "PR 4901 vs main", "base_tps": 17.31, "target_tps": 18.95, "base_sd": 0.02, "target_sd": 0.03, "tps_delta_pct": 9.4, "tps_delta": 1.64, "band_tps": 0.4, "tps_resolved": true, "base_ttft_ms": 52549, "target_ttft_ms": 51852, "ttft_delta_ms": -697.0, "ttft_delta_pct": -1.3, "band_ttft_ms": 296, "ttft_resolved": true, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp2, 8 users, prompt 8,192"}, {"cell": "q3-4b-tp4-8u-p1024", "attn": "cpu", "pair": "PR 4901 vs main", "base_tps": 117.36, "target_tps": 120.22, "base_sd": 0.49, "target_sd": 0.39, "tps_delta_pct": 2.4, "tps_delta": 2.86, "band_tps": 0.98, "tps_resolved": true, "base_ttft_ms": 2215, "target_ttft_ms": 2142, "ttft_delta_ms": -73.0, "ttft_delta_pct": -3.3, "band_ttft_ms": 150, "ttft_resolved": false, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp4, 8 users, prompt 1,024"}], "runtron_fpga": [{"cell": "q3-4b-tp2-8u-p1024", "attn": "fpga", "pair": "PR 4901 vs main", "base_tps": 132.07, "target_tps": 132.84, "base_sd": 0.24, "target_sd": 0.48, "tps_delta_pct": 0.6, "tps_delta": 0.77, "band_tps": 0.96, "tps_resolved": false, "base_ttft_ms": 3192, "target_ttft_ms": 3171, "ttft_delta_ms": -21.0, "ttft_delta_pct": -0.6, "band_ttft_ms": 150, "ttft_resolved": false, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp2, 8 users, prompt 1,024"}, {"cell": "q3-4b-tp4-8u-p1024", "attn": "fpga", "pair": "PR 4901 vs main", "base_tps": 163.49, "target_tps": 163.07, "base_sd": 1.06, "target_sd": 0.83, "tps_delta_pct": -0.3, "tps_delta": -0.42, "band_tps": 2.12, "tps_resolved": false, "base_ttft_ms": 2232, "target_ttft_ms": 2192, "ttft_delta_ms": -40.0, "ttft_delta_pct": -1.8, "band_ttft_ms": 150, "ttft_resolved": false, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp4, 8 users, prompt 1,024"}], "runtron_off": [{"cell": "q3-4b-tp2-8u-p1024", "attn": "cpu", "pair": "PR 4901 vs main, AMX off on both", "base_tps": 72.83, "target_tps": 73.36, "base_sd": 0.01, "target_sd": 0.3, "tps_delta_pct": 0.7, "tps_delta": 0.53, "band_tps": 0.6, "tps_resolved": false, "base_ttft_ms": 3945, "target_ttft_ms": 3866, "ttft_delta_ms": -79.0, "ttft_delta_pct": -2.0, "band_ttft_ms": 150, "ttft_resolved": false, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp2, 8 users, prompt 1,024"}, {"cell": "q3-4b-tp2-8u-p8192", "attn": "cpu", "pair": "PR 4901 vs main, AMX off on both", "base_tps": 14.57, "target_tps": 14.96, "base_sd": 0.02, "target_sd": 0.02, "tps_delta_pct": 2.7, "tps_delta": 0.39, "band_tps": 0.4, "tps_resolved": false, "base_ttft_ms": 122841, "target_ttft_ms": 117861, "ttft_delta_ms": -4980.0, "ttft_delta_pct": -4.1, "band_ttft_ms": 440, "ttft_resolved": true, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp2, 8 users, prompt 8,192"}, {"cell": "q3-4b-tp4-8u-p1024", "attn": "cpu", "pair": "PR 4901 vs main, AMX off on both", "base_tps": 111.67, "target_tps": 111.07, "base_sd": 0.92, "target_sd": 0.08, "tps_delta_pct": -0.5, "tps_delta": -0.6, "band_tps": 1.84, "tps_resolved": false, "base_ttft_ms": 2471, "target_ttft_ms": 2403, "ttft_delta_ms": -68.0, "ttft_delta_pct": -2.7, "band_ttft_ms": 150, "ttft_resolved": false, "n": 3, "base_commit": "72308ec90c", "target_commit": "ea94e95a4e", "name": "qwen3-4b tp4, 8 users, prompt 1,024"}]}};
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
  const W = 960, labW = 250, gap = 34, colW = (W - labW - gap*2) / 2, rowH = 30, grpH = 26, top = 34;
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
            const t = el("text", {x: c.x0 + colW + 6, y: cy + 4 + oy, "text-anchor": "start", class:"val", "font-weight": res ? "600":"400"});
            t.textContent = labText + (s.tag ? "  " + s.tag : "");
            t.setAttribute("fill", color);
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
