
const K = 1024, M = K * K, G = M * K;
const fresh = [[256*K,3.66],[512*K,3.73],[M,3.74],[1.5*M,3.76],[2*M,5.79],[3*M,14.95],[4*M,19.21],[6*M,24.24],[8*M,26.09],[12*M,27.99],[16*M,29.09],[24*M,29.74],[32*M,30.18],[40*M,30.40],[48*M,30.54],[56*M,30.67],[64*M,35.86],[80*M,53.84],[96*M,65.81],[128*M,80.49],[192*M,94.74],[256*M,109.31],[512*M,140.87],[G,148.23],[2*G,149.86]];
const rep = [[4*K,1.43],[8*K,1.43],[16*K,1.43],[32*K,1.43],[48*K,1.43],[64*K,1.43],[96*K,1.63],[128*K,1.84],[256*K,2.19],[512*K,1.88],[M,3.75],[1.5*M,3.77],[2*M,4.03],[3*M,5.10],[4*M,6.18],[8*M,6.78],[16*M,5.63],[32*M,5.42],[64*M,23.91],[96*M,47.49],[128*M,71.36],[192*M,86.62],[256*M,101.96],[512*M,138.76],[G,148.19],[2*G,150.25]];
const S1 = '#2a78d6', S2 = '#eb6834', S3 = '#1baf7a', INK = '#1b1f24', MUTED = '#5b6470', RULE = '#d9dde3';
const svgNS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent, text) { const e = document.createElementNS(svgNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text !== undefined) e.textContent = text; parent.appendChild(e); return e; }
function fmtSize(b) { if (b >= G) return (b / G) + ' GiB'; if (b >= M) return (b / M) + ' MiB'; return (b / K) + ' KiB'; }
function tip(e, t) { el('title', {}, e, t); }

// Latency chart: log x, linear y
(function () {
  const s = document.getElementById('lat'), W = 880, H = 400, L = 56, R = 20, T = 20, B = 48;
  const x0 = Math.log2(4*K), x1 = Math.log2(2*G), ymax = 160;
  const X = b => L + (Math.log2(b) - x0) / (x1 - x0) * (W - L - R);
  const Y = v => T + (1 - v / ymax) * (H - T - B);
  // bands
  const bands = [[4*K, 64*K, 'L1 64 KiB'], [64*K, 2*M, 'L2 2 MiB'], [2*M, 128*M, 'SLC (L3) 128 MiB'], [128*M, 2*G, 'DRAM']];
  bands.forEach((b, i) => { el('rect', {x: X(b[0]), y: T, width: X(b[1]) - X(b[0]), height: H - T - B, fill: i % 2 ? '#f5f7f9' : '#eef3fa'}, s); el('text', {x: X(b[0]) + 6, y: T + 14, 'font-size': 12, fill: MUTED}, s, b[2]); });
  for (let v = 0; v <= ymax; v += 40) { el('line', {x1: L, x2: W - R, y1: Y(v), y2: Y(v), stroke: RULE}, s); el('text', {x: L - 8, y: Y(v) + 4, 'text-anchor': 'end', 'font-size': 12, fill: MUTED}, s, v); }
  el('text', {x: 14, y: T + 10, 'font-size': 12, fill: MUTED, transform: 'rotate(-90 14 ' + (T + 10) + ')', 'text-anchor': 'end'}, s, 'ns per load');
  [4*K, 64*K, M, 16*M, 128*M, G, 2*G].forEach(b => { el('line', {x1: X(b), x2: X(b), y1: H - B, y2: H - B + 5, stroke: MUTED}, s); el('text', {x: X(b), y: H - B + 19, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, fmtSize(b)); });
  el('text', {x: (L + W - R) / 2, y: H - 8, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'footprint of the random cycle (log scale)');
  function series(d, c) { el('path', {d: d.map((p, i) => (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1)).join(' '), fill: 'none', stroke: c, 'stroke-width': 2, 'stroke-linejoin': 'round'}, s); d.forEach(p => { const g = el('g', {}, s); el('circle', {cx: X(p[0]), cy: Y(p[1]), r: 4, fill: c, stroke: '#fff', 'stroke-width': 1.5}, g); tip(g, fmtSize(p[0]) + ': ' + p[1] + ' ns (' + (p[1] * 2.8).toFixed(1) + ' cycles)'); }); }
  series(rep, S2); series(fresh, S1);
  const lab = (x, y, t, c, anchor) => el('text', {x, y, 'font-size': 12.5, fill: c || INK, 'font-weight': 600, 'text-anchor': anchor || 'start'}, s, t);
  lab(X(16*K), Y(1.43) - 10, 'L1: 1.43 ns (4 cycles)', INK, 'middle');
  lab(X(1.2*M), Y(3.75) - 12, 'L2: 3.75 ns (10.5 cycles)', INK, 'middle');
  lab(X(32*M), Y(30.4) - 12, 'SLC: 30 ns (85 cycles)', S1, 'middle');
  lab(X(32*M), Y(5.42) + 20, 'repeated chain: 5.4 ns, every load misses L2', S2, 'middle');
  lab(X(G), Y(148) - 12, 'DRAM: 148 ns (415 cycles)', INK, 'end');
  // gap annotation at 32 MiB
  el('line', {x1: X(32*M), x2: X(32*M), y1: Y(30.18) + 6, y2: Y(5.42) - 6, stroke: '#c8373a', 'stroke-width': 1.5, 'stroke-dasharray': '3 3'}, s);
  lab(X(32*M) + 8, (Y(30.18) + Y(5.42)) / 2 + 4, '5.6x gap', '#c8373a');
})();

// Dumbbell: per-core bandwidth, compiled vs asm
(function () {
  const rows = [['L1 read', 66.8, 132.7], ['L1 write', 44.0, 89.5], ['L1 copy', 88.0, 178.4], ['L2 read', 67.1, 85.2], ['L2 write', 44.8, 89.5], ['L2 copy', 88.8, 138.8], ['SLC read', 67.0, 67.5], ['SLC write', 44.8, 73.2], ['SLC copy', 50.0, 55.4], ['DRAM read', 28.2, 30.5], ['DRAM write', 44.8, 63.0], ['DRAM copy', 42.2, 42.5]];
  const s = document.getElementById('db'), W = 880, L = 110, R = 70, T = 24, rowH = 36, H = T + rows.length * rowH + 44, xmax = 200;
  s.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  const X = v => L + v / xmax * (W - L - R);
  for (let v = 0; v <= xmax; v += 50) { el('line', {x1: X(v), x2: X(v), y1: T - 6, y2: H - 40, stroke: RULE}, s); el('text', {x: X(v), y: H - 24, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, v); }
  el('text', {x: (L + W - R) / 2, y: H - 6, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'GB/s per core, one thread');
  rows.forEach((r, i) => {
    const y = T + i * rowH + rowH / 2;
    if (i % 3 === 0 && i) el('line', {x1: L - 100, x2: W - R, y1: y - rowH / 2, y2: y - rowH / 2, stroke: RULE}, s);
    el('text', {x: L - 10, y: y + 4, 'text-anchor': 'end', 'font-size': 13, fill: INK}, s, r[0]);
    el('line', {x1: X(r[1]), x2: X(r[2]), y1: y, y2: y, stroke: '#b9c4d1', 'stroke-width': 3}, s);
    const a = el('circle', {cx: X(r[1]), cy: y, r: 6, fill: S2, stroke: '#fff', 'stroke-width': 1.5}, s); tip(a, r[0] + ', compiled loop: ' + r[1] + ' GB/s');
    const b = el('circle', {cx: X(r[2]), cy: y, r: 6, fill: S1, stroke: '#fff', 'stroke-width': 1.5}, s); tip(b, r[0] + ', asm loop: ' + r[2] + ' GB/s');
    const gain = r[2] / r[1];
    if (gain > 1.08) { el('text', {x: X(r[1]) - 10, y: y + 4, 'text-anchor': 'end', 'font-size': 12, fill: S2}, s, r[1]); el('text', {x: X(r[2]) + 10, y: y + 4, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, r[2] + '  (x' + gain.toFixed(1) + ')'); }
    else { el('text', {x: X(Math.max(r[1], r[2])) + 10, y: y + 4, 'font-size': 12.5, fill: INK}, s, r[1] + ' / ' + r[2] + '  same'); }
  });
})();

// Aggregate bars (TB/s)
(function () {
  const rows = [['L1 read', 15.89], ['L1 write', 10.74], ['L1 copy', 21.38], ['L2 read', 10.22], ['L2 write', 10.73], ['L2 copy', 9.02], ['SLC read ≥', 0.62], ['DRAM read', 0.533], ['DRAM write', 0.447], ['DRAM copy', 0.415]];
  const s = document.getElementById('agg'), W = 880, L = 120, R = 90, T = 16, rowH = 30, H = T + rows.length * rowH + 44, xmax = 22;
  s.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  const X = v => L + v / xmax * (W - L - R);
  for (let v = 0; v <= xmax; v += 5) { el('line', {x1: X(v), x2: X(v), y1: T - 4, y2: H - 40, stroke: RULE}, s); el('text', {x: X(v), y: H - 24, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, v); }
  el('text', {x: (L + W - R) / 2, y: H - 6, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'TB/s, whole chip (120 cores used)');
  rows.forEach((r, i) => {
    const y = T + i * rowH + 4, h = rowH - 10;
    el('text', {x: L - 10, y: y + h / 2 + 4, 'text-anchor': 'end', 'font-size': 13, fill: INK}, s, r[0]);
    const b = el('rect', {x: X(0), y, width: Math.max(2, X(r[1]) - X(0)), height: h, rx: 3, fill: i < 6 ? S1 : (i < 7 ? S3 : S2)}, s); tip(b, r[0] + ': ' + (r[1] >= 1 ? r[1].toFixed(2) + ' TB/s' : (r[1] * 1000).toFixed(0) + ' GB/s'));
    el('text', {x: X(r[1]) + 8, y: y + h / 2 + 4, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, r[1] >= 1 ? r[1].toFixed(2) + ' TB/s' : (r[1] * 1000).toFixed(0) + ' GB/s');
  });
})();

// SLC scaling
(function () {
  const d = [[8, 455], [16, 705], [24, 809], [32, 899], [40, 1349]];
  const s = document.getElementById('slc'), W = 880, H = 300, L = 60, R = 30, T = 16, B = 44, xmax = 44, ymax = 1500;
  const X = v => L + v / xmax * (W - L - R), Y = v => T + (1 - v / ymax) * (H - T - B);
  for (let v = 0; v <= ymax; v += 500) { el('line', {x1: L, x2: W - R, y1: Y(v), y2: Y(v), stroke: RULE}, s); el('text', {x: L - 8, y: Y(v) + 4, 'text-anchor': 'end', 'font-size': 12, fill: MUTED}, s, v); }
  el('text', {x: 14, y: T + 10, 'font-size': 12, fill: MUTED, transform: 'rotate(-90 14 ' + (T + 10) + ')', 'text-anchor': 'end'}, s, 'GB/s aggregate');
  [8, 16, 24, 32, 40].forEach(v => el('text', {x: X(v), y: H - B + 19, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, v));
  el('text', {x: (L + W - R) / 2, y: H - 8, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'threads, one per core pair, 3 MiB each');
  el('path', {d: d.map((p, i) => (i ? 'L' : 'M') + X(p[0]) + ',' + Y(p[1])).join(' '), fill: 'none', stroke: S1, 'stroke-width': 2}, s);
  d.forEach(p => { const g = el('g', {}, s); el('circle', {cx: X(p[0]), cy: Y(p[1]), r: 5, fill: S1, stroke: '#fff', 'stroke-width': 1.5}, g); tip(g, p[0] + ' threads: ' + p[1] + ' GB/s'); el('text', {x: X(p[0]), y: Y(p[1]) - 12, 'text-anchor': 'middle', 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, p[1]); });
  el('text', {x: X(40) - 10, y: Y(1349) + 28, 'text-anchor': 'end', 'font-size': 12.5, fill: '#c8373a', 'font-weight': 600}, s, 'still rising: footprint rule stops the test here');
})();

// DRAM vs threads
(function () {
  const rd = [[16, 144], [32, 219], [48, 273], [64, 346], [80, 411], [96, 415], [112, 424], [120, 368]];
  const wr = [[16, 204], [32, 280], [48, 346], [64, 394], [80, 217], [96, 174], [112, 158], [120, 148]];
  const cp = [[16, 223], [32, 273], [48, 324], [64, 354], [80, 388], [96, 253], [112, 187], [120, 176]];
  const rp = [[32, 347], [48, 523], [60, 522]];
  const s = document.getElementById('dram'), W = 880, H = 380, L = 60, R = 30, T = 16, B = 44, xmax = 124, ymax = 600;
  const X = v => L + v / xmax * (W - L - R), Y = v => T + (1 - v / ymax) * (H - T - B);
  for (let v = 0; v <= ymax; v += 100) { el('line', {x1: L, x2: W - R, y1: Y(v), y2: Y(v), stroke: RULE}, s); el('text', {x: L - 8, y: Y(v) + 4, 'text-anchor': 'end', 'font-size': 12, fill: MUTED}, s, v); }
  el('text', {x: 14, y: T + 10, 'font-size': 12, fill: MUTED, transform: 'rotate(-90 14 ' + (T + 10) + ')', 'text-anchor': 'end'}, s, 'GB/s aggregate');
  [16, 32, 48, 64, 80, 96, 112, 120].forEach(v => el('text', {x: X(v), y: H - B + 19, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, v));
  el('text', {x: (L + W - R) / 2, y: H - 8, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'threads, 256 MiB each');
  function series(d, c, name, dash) { el('path', {d: d.map((p, i) => (i ? 'L' : 'M') + X(p[0]) + ',' + Y(p[1])).join(' '), fill: 'none', stroke: c, 'stroke-width': 2, 'stroke-dasharray': dash || 'none'}, s); d.forEach(p => { const g = el('g', {}, s); el('circle', {cx: X(p[0]), cy: Y(p[1]), r: 4.5, fill: c, stroke: '#fff', 'stroke-width': 1.5}, g); tip(g, name + ', ' + p[0] + ' threads: ' + p[1] + ' GB/s'); }); }
  series(rd, S1, 'read'); series(wr, S2, 'write'); series(cp, S3, 'copy'); series(rp, INK, 'read, one per pair', '5 4');
  const lab = (x, y, t, c, a) => el('text', {x, y, 'font-size': 12.5, fill: c, 'font-weight': 600, 'text-anchor': a || 'start'}, s, t);
  lab(X(48), Y(523) - 12, 'read, one per pair: 523', INK, 'middle');
  lab(X(112), Y(424) - 12, 'read: 424', S1, 'middle');
  lab(X(64), Y(394) + 20, 'write: 394', S2, 'middle');
  lab(X(80), Y(388) - 12, 'copy: 388', S3, 'middle');
  lab(X(120), Y(148) + 18, 'write: 148', S2, 'end');
  lab(X(120), Y(176) - 10, 'copy: 176', S3, 'end');
})();

// Pair bars
(function () {
  const d = [['CPUs 0,1 (a pair)', 78.3, true], ['CPUs 2,3 (a pair)', 77.9, true], ['CPUs 4,5 (a pair)', 78.5, true], ['CPUs 0,2', 126.6, false], ['CPUs 1,2', 132.0, false], ['CPUs 0,64', 134.1, false], ['CPUs 0,119', 134.0, false]];
  const s = document.getElementById('pair'), W = 880, L = 150, R = 70, T = 10, rowH = 30, H = T + d.length * rowH + 40, xmax = 150;
  s.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  const X = v => L + v / xmax * (W - L - R);
  for (let v = 0; v <= xmax; v += 50) { el('line', {x1: X(v), x2: X(v), y1: T, y2: H - 36, stroke: RULE}, s); el('text', {x: X(v), y: H - 20, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, v); }
  el('text', {x: (L + W - R) / 2, y: H - 4, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'GB/s, two threads reading 8 MiB each');
  d.forEach((r, i) => { const y = T + i * rowH + 4, h = rowH - 10; el('text', {x: L - 10, y: y + h / 2 + 4, 'text-anchor': 'end', 'font-size': 13, fill: INK}, s, r[0]); const b = el('rect', {x: X(0), y, width: X(r[1]) - X(0), height: h, rx: 3, fill: r[2] ? S2 : S1}, s); tip(b, r[0] + ': ' + r[1] + ' GB/s'); el('text', {x: X(r[1]) + 8, y: y + h / 2 + 4, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, r[1]); });
})();

// Latency table
(function () {
  const t = document.getElementById('lattab');
  const sizes = Array.from(new Set(rep.map(p => p[0]).concat(fresh.map(p => p[0])))).sort((a, b) => a - b);
  const fr = Object.fromEntries(fresh), rp = Object.fromEntries(rep);
  const half = Math.ceil(sizes.length / 2);
  for (let i = 0; i < half; i++) {
    const tr = document.createElement('tr');
    [i, i + half].forEach(j => { const b = sizes[j]; if (b === undefined) { tr.innerHTML += '<td></td><td></td><td></td>'; return; } tr.innerHTML += '<td>' + fmtSize(b) + '</td><td>' + (fr[b] !== undefined ? fr[b].toFixed(2) : '–') + '</td><td>' + (rp[b] !== undefined ? rp[b].toFixed(2) : '–') + '</td>'; });
    t.appendChild(tr);
  }
})();

// Load/store pipelines: 3 loads or 2 stores of 16 B per cycle
(function () {
  const s = document.getElementById('pipes'), PANEL = '#f5f7f9';
  function panel(x0, title, lanes, color, perCycle, peak, meas, idle) {
    el('text', {x: x0, y: 18, 'font-size': 13.5, 'font-weight': 600, fill: INK}, s, title);
    const lx = x0 + 96, cw = 64, rows = lanes.length + (idle ? idle.length : 0);
    for (let c = 0; c < 4; c++) el('text', {x: lx + c * cw + cw / 2 - 4, y: 38, 'text-anchor': 'middle', 'font-size': 11.5, fill: MUTED}, s, 'cycle ' + (c + 1));
    lanes.forEach((name, i) => {
      const y = 50 + i * 30;
      el('text', {x: lx - 8, y: y + 15, 'text-anchor': 'end', 'font-size': 12, fill: INK}, s, name);
      for (let c = 0; c < 4; c++) { el('rect', {x: lx + c * cw, y, width: cw - 8, height: 22, rx: 3, fill: color}, s); el('text', {x: lx + c * cw + (cw - 8) / 2, y: y + 15, 'text-anchor': 'middle', 'font-size': 11.5, fill: '#fff', 'font-weight': 600}, s, '16 B'); }
    });
    (idle || []).forEach((name, j) => {
      const y = 50 + (lanes.length + j) * 30;
      el('text', {x: lx - 8, y: y + 15, 'text-anchor': 'end', 'font-size': 12, fill: MUTED}, s, name);
      for (let c = 0; c < 4; c++) el('rect', {x: lx + c * cw, y, width: cw - 8, height: 22, rx: 3, fill: 'none', stroke: RULE, 'stroke-dasharray': '3 3'}, s);
      el('text', {x: lx + 4 * cw + 2, y: y + 15, 'font-size': 11.5, fill: MUTED}, s, 'idle');
    });
    const yb = 50 + rows * 30 + 14;
    el('text', {x: x0, y: yb, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, perCycle);
    el('text', {x: x0, y: yb + 18, 'font-size': 12.5, fill: INK}, s, peak);
    el('text', {x: x0, y: yb + 36, 'font-size': 12.5, fill: S1, 'font-weight': 600}, s, meas);
  }
  panel(8, 'Read loop (LDP q): 3 loads per cycle', ['Load/Store 0', 'Load 1', 'Load 2'], S1, '3 × 16 B = 48 B per cycle', '× 2.8 GHz = 134.4 GB/s peak', 'measured 132.7 GB/s (99 %)', ['Store 1']);
  panel(456, 'Write loop (STP q): 2 stores per cycle', ['Load/Store 0', 'Store 1'], S2, '2 × 16 B = 32 B per cycle', '× 2.8 GHz = 89.6 GB/s peak', 'measured 89.5 GB/s (100 %)', ['Load 1', 'Load 2']);
  el('text', {x: 8, y: 240, 'font-size': 12, fill: MUTED}, s, 'Load/Store 0 does a load or a store in a given cycle, so 3 loads and 2 stores cannot all happen in the same cycle.');
})();

// Cache ways: address split and set/way grid for the L1 data cache
(function () {
  const s = document.getElementById('ways');
  // address bar
  const ax = 8, ay = 24, segs = [['tag (bits 47 to 14)', 330, '#f5f7f9', INK], ['set index (bits 13 to 6)', 170, '#eef3fa', S1], ['offset (bits 5 to 0)', 110, '#fff4ee', S2]];
  el('text', {x: ax, y: 16, 'font-size': 12.5, fill: MUTED}, s, 'address of a load, 48 bits');
  let x = ax;
  segs.forEach(g => { el('rect', {x, y: ay, width: g[1], height: 30, fill: g[2], stroke: g[3]}, s); el('text', {x: x + g[1] / 2, y: ay + 19, 'text-anchor': 'middle', 'font-size': 12.5, fill: INK}, s, g[0]); x += g[1]; });
  // explanations at right
  [['256 sets = 2^8', 'so 8 index bits pick one set'], ['64 B line = 2^6', 'so 6 offset bits pick the byte inside the line'], ['tag', 'the rest of the address, stored with the line and compared on lookup']].forEach((t, i) => { el('text', {x: ax, y: ay + 50 + i * 15, 'font-size': 11.5, fill: INK, 'font-weight': 600}, s, t[0]); el('text', {x: ax + 100, y: ay + 50 + i * 15, 'font-size': 11.5, fill: MUTED}, s, t[1]); });
  // grid of sets x ways
  const gx = 120, gy = 136, cw = 110, ch = 20, waysN = 4, shown = [0, 1, 2, 36, 37, 38, 254, 255];
  for (let w = 0; w < waysN; w++) el('text', {x: gx + w * cw + cw / 2, y: gy - 6, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'way ' + w);
  shown.forEach((setNo, r) => {
    const y = gy + r * ch, hi = setNo === 37;
    el('text', {x: gx - 8, y: y + 14, 'text-anchor': 'end', 'font-size': 12, fill: hi ? S1 : INK, 'font-weight': hi ? 600 : 400}, s, 'set ' + setNo);
    for (let w = 0; w < waysN; w++) { el('rect', {x: gx + w * cw, y, width: cw - 2, height: ch - 2, fill: hi ? '#eef3fa' : '#fff', stroke: hi ? S1 : RULE, 'stroke-width': hi ? 1.5 : 1}, s); if (hi) el('text', {x: gx + w * cw + cw / 2, y: y + 13, 'text-anchor': 'middle', 'font-size': 11, fill: S1}, s, 'one 64 B line'); }
    if (r === 2 || r === 5) el('text', {x: gx - 8, y: y + ch + 12, 'text-anchor': 'end', 'font-size': 12, fill: MUTED}, s, '…');
  });
  // arrow from set index to set 37
  const sx = ax + 330 + 85, sy = ay + 30, ty = gy + 4 * ch + 8;
  el('path', {d: 'M' + sx + ',' + sy + ' L' + sx + ',' + (sy + 22) + ' L' + (gx + waysN * cw + 14) + ',' + (sy + 22) + ' L' + (gx + waysN * cw + 14) + ',' + ty + ' L' + (gx + waysN * cw + 4) + ',' + ty, fill: 'none', stroke: S1, 'stroke-width': 1.5, 'marker-end': 'url(#ar)'}, s);
  el('text', {x: gx + waysN * cw + 20, y: ty - 10, 'font-size': 12, fill: S1, 'font-weight': 600}, s, 'index = 37');
  el('text', {x: gx + waysN * cw + 20, y: ty + 8, 'font-size': 12, fill: S1}, s, 'the line can use any of these 4 slots');
  el('text', {x: gx + waysN * cw + 20, y: ty + 24, 'font-size': 12, fill: MUTED}, s, 'and no slot in any other set');
  el('text', {x: 8, y: gy + 8 * ch + 24, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, 'L1 data: 256 sets × 4 ways × 64 B = 64 KiB.');
  el('text', {x: 8, y: gy + 8 * ch + 42, 'font-size': 12, fill: MUTED}, s, 'Two addresses 16 KiB apart (256 × 64 B) share a set. A fifth such line evicts one of the four.');
})();

// Cache ways, worked example: set 37 after the loads, after the eviction, and during a read of B
(function () {
  const s = document.getElementById('waysex'), PW = 272, RH = 24, RED = '#c8373a';
  function panel(px, title, sub, slots, hiRow, hiColor) {
    el('text', {x: px, y: 16, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, title);
    el('text', {x: px, y: 31, 'font-size': 11.5, fill: MUTED}, s, sub);
    slots.forEach((t, i) => {
      const y = 42 + i * RH, hi = i === hiRow;
      el('rect', {x: px, y, width: PW - 10, height: RH - 3, rx: 3, fill: hi ? '#fff4ee' : '#eef3fa', stroke: hi ? hiColor : S1, 'stroke-width': hi ? 1.5 : 1}, s);
      el('text', {x: px + 6, y: y + 15, 'font-size': 11, fill: MUTED}, s, 'slot ' + i);
      el('text', {x: px + 46, y: y + 15, 'font-size': 11, fill: INK, 'font-family': 'IBM Plex Mono, monospace'}, s, t[0]);
      el('text', {x: px + PW - 16, y: y + 15, 'text-anchor': 'end', 'font-size': 11, fill: hi ? hiColor : INK, 'font-weight': hi ? 600 : 400}, s, t[1]);
    });
  }
  const T = ['tag 0x1fc48d158', 'tag 0x1fc48d159', 'tag 0x1fc48d15a', 'tag 0x1fc48d15b'];
  panel(8, 'set 37 after loads A, C, D, E', 'all 4 slots hold a line; tags tell them apart', [[T[0], 'line of A and B'], [T[1], 'line of C'], [T[2], 'line of D'], [T[3], 'line of E']], -1, S1);
  panel(304, 'set 37 after load F', 'no free slot, so one line is evicted (slot 0, est.)', [['tag 0x1fc48d15c', 'line of F'], [T[1], 'line of C'], [T[2], 'line of D'], [T[3], 'line of E']], 0, RED);
  panel(600, 'read B = 0x7f1234560950', 'compare tag 0x1fc48d158 with all 4 slots', [[T[0], 'equal: hit'], [T[1], 'not equal'], [T[2], 'not equal'], [T[3], 'not equal']], 0, S1);
  el('text', {x: 600, y: 42 + 4 * RH + 14, 'font-size': 11.5, fill: S1, 'font-weight': 600}, s, 'then offset 16 picks byte 16 of that line');
  el('text', {x: 8, y: 42 + 4 * RH + 34, 'font-size': 11.5, fill: MUTED}, s, 'Every slot above holds a line with set index 37. Only the stored tag says which 16 KiB-spaced line it is.');
  el('text', {x: 8, y: 42 + 4 * RH + 50, 'font-size': 11.5, fill: MUTED}, s, 'Loading A again after F is a miss if A was the evicted line: a conflict miss with only 320 B in use.');
})();

// Write-fall grid: writers per mesh, DRAM write GB/s as a heat map, read control in grey
(function () {
  const s = document.getElementById('wgrid'), WD = [[0, 16, 237.94], [0, 32, 346.63], [0, 48, 348.18], [0, 56, 361.3], [16, 0, 203.91], [16, 16, 346.49], [16, 32, 313.44], [16, 48, 213.64], [16, 56, 202.56], [32, 0, 280.18], [32, 16, 318.41], [32, 32, 172.81], [32, 48, 146.71], [32, 56, 148.68], [48, 0, 346.0], [48, 16, 230.18], [48, 32, 139.31], [48, 48, 142.91], [48, 56, 121.67], [64, 0, 394.15], [64, 16, 213.75], [64, 32, 157.31], [64, 48, 133.39], [64, 56, 139.94]], RD = [[0, 56, 318.11], [16, 16, 289.62], [32, 32, 327.91], [48, 48, 321.78], [64, 0, 346.05], [64, 56, 297.76]];
  const A = [0, 16, 32, 48, 64], Bv = [0, 16, 32, 48, 56], X0 = 170, Y0 = 50, CW = 120, CH = 48;
  const w = {}, r = {}; WD.forEach(([a, b, v]) => w[a + ',' + b] = v); RD.forEach(([a, b, v]) => r[a + ',' + b] = v);
  const vmin = 120, vmax = 400;
  const shade = v => { const k = Math.max(0, Math.min(1, (v - vmin) / (vmax - vmin))); const l = 96 - k * 58; return 'hsl(213 65% ' + l + '%)'; };
  el('text', {x: X0 + 2.5 * CW, y: 18, 'text-anchor': 'middle', 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, 'writer threads on mesh 1 (CPUs 64 and up)');
  Bv.forEach((b, j) => el('text', {x: X0 + j * CW + CW / 2, y: 40, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, b));
  el('text', {x: 14, y: Y0 + 2.5 * CH, 'font-size': 12.5, fill: INK, 'font-weight': 600, transform: 'rotate(-90 14 ' + (Y0 + 2.5 * CH) + ')', 'text-anchor': 'middle'}, s, 'writer threads on mesh 0 (CPUs 0 to 63)');
  A.forEach((a, i) => {
    el('text', {x: X0 - 10, y: Y0 + i * CH + CH / 2 + 4, 'text-anchor': 'end', 'font-size': 12, fill: MUTED}, s, a);
    Bv.forEach((b, j) => {
      const k = a + ',' + b, x = X0 + j * CW, y = Y0 + i * CH;
      if (!(k in w)) { el('rect', {x, y, width: CW - 3, height: CH - 3, fill: '#fff', stroke: RULE}, s); el('text', {x: x + CW / 2, y: y + CH / 2 + 4, 'text-anchor': 'middle', 'font-size': 12, fill: MUTED}, s, 'no threads'); return; }
      const v = w[k], dark = v > 290;
      el('rect', {x, y, width: CW - 3, height: CH - 3, fill: shade(v), stroke: '#fff'}, s);
      el('text', {x: x + 8, y: y + CH / 2 + 5, 'font-size': 14, fill: dark ? '#fff' : INK, 'font-weight': 600}, s, v.toFixed(0) + ' GB/s');
      if (k in r) el('text', {x: x + CW - 10, y: y + CH - 10, 'text-anchor': 'end', 'font-size': 10.5, fill: dark ? '#dfe8f5' : MUTED}, s, 'read ' + r[k].toFixed(0));
    });
  });
  el('text', {x: X0, y: Y0 + 5 * CH + 20, 'font-size': 12, fill: INK, 'font-weight': 600}, s, 'Same 64 threads: 394 GB/s on one mesh, 173 GB/s split 32 and 32.');
  el('text', {x: X0, y: Y0 + 5 * CH + 38, 'font-size': 11.5, fill: MUTED}, s, 'asmwrite, 256 MiB per thread, best of 3; reads in grey do not collapse.');
})();

// Per-core sweep: fresh 16 MiB latency and 1-thread asmread per CPU, two sweeps
(function () {
  const s = document.getElementById('percore'), D = [[0, 29.421, 29.344, 66.81, 67.09], [1, 29.507, 29.346, 68.38, 67.82], [2, 29.075, 29.044, 67.08, 66.97], [3, 29.116, 29.194, 67.07, 66.96], [4, 29.696, 29.765, 66.93, 67.19], [5, 29.52, 29.752, 69.99, 69.05], [6, 28.326, 28.293, 67.54, 67.35], [7, 28.352, 28.344, 67.35, 67.55], [8, 27.306, 27.29, 68.01, 68.14], [9, 27.098, 27.263, 67.99, 67.97], [10, 27.038, 27.114, 67.93, 68.07], [11, 27.088, 26.857, 68.15, 67.9], [12, 27.704, 27.645, 67.52, 67.95], [13, 27.706, 27.673, 71.29, 69.75], [14, 29.087, 28.981, 71.2, 70.93], [15, 29.099, 29.112, 67.22, 67.54], [16, 27.109, 27.128, 68.43, 68.21], [17, 26.988, 27.108, 71.53, 71.3], [18, 26.022, 26.004, 68.54, 69.67], [19, 26.033, 26.033, 68.96, 68.55], [20, 25.672, 25.755, 68.63, 68.9], [21, 25.858, 25.918, 68.97, 71.58], [22, 26.521, 26.482, 71.57, 71.1], [23, 26.471, 26.421, 68.4, 68.46], [24, 27.635, 27.803, 68.0, 68.22], [25, 27.866, 27.78, 71.55, 69.07], [26, 26.803, 26.849, 71.62, 68.73], [27, 26.664, 26.621, 68.68, 68.68], [28, 25.649, 25.508, 68.86, 68.83], [29, 25.658, 25.789, 71.65, 71.59], [30, 25.512, 25.518, 69.16, 69.01], [31, 25.501, 25.479, 68.99, 69.2], [32, 26.084, 26.046, 68.89, 68.94], [33, 26.095, 25.996, 68.73, 71.62], [34, 27.551, 27.463, 68.34, 68.54], [35, 27.346, 27.507, 68.62, 68.75], [36, 27.093, 26.967, 68.13, 68.34], [37, 26.99, 27.089, 68.18, 68.22], [38, 26.086, 26.094, 71.59, 71.56], [39, 26.06, 26.068, 68.59, 68.83], [40, 25.727, 25.911, 68.92, 68.66], [41, 25.67, 25.87, 71.6, 71.73], [42, 26.441, 26.459, 71.62, 71.6], [43, 26.382, 26.354, 68.8, 68.71], [44, 27.792, 27.894, 68.18, 68.13], [45, 27.816, 27.794, 68.28, 68.18], [46, 28.399, 28.352, 68.79, 67.47], [47, 28.268, 28.159, 67.3, 67.35], [48, 27.298, 27.353, 67.62, 67.73], [49, 27.109, 27.191, 71.45, 69.48], [50, 27.038, 26.995, 67.96, 67.91], [51, 26.975, 27.122, 67.89, 67.85], [52, 27.627, 27.716, 67.58, 67.64], [53, 27.557, 27.616, 68.06, 67.86], [54, 29.025, 28.983, 68.68, 67.55], [55, 28.881, 28.903, 67.05, 67.18], [56, 30.39, 30.529, 66.76, 66.45], [57, 30.314, 30.386, 66.48, 66.73], [58, 29.322, 29.416, 67.13, 67.36], [59, 29.356, 29.362, 67.08, 66.95], [60, 29.083, 29.184, 67.41, 67.02], [61, 29.038, 29.139, 71.05, 69.98], [62, 29.791, 29.722, 70.82, 70.95], [63, 29.718, 29.728, 67.09, 66.66], [64, 29.393, 29.384, 66.91, 66.73], [65, 29.322, 29.39, 66.81, 68.2], [66, 29.11, 29.034, 67.06, 67.11], [67, 29.074, 29.081, 67.0, 67.2], [68, 29.727, 29.743, 66.75, 66.88], [69, 29.796, 29.7, 68.13, 66.99], [70, 28.337, 28.348, 67.58, 70.14], [71, 28.199, 28.337, 67.53, 67.43], [72, 27.185, 27.279, 67.96, 67.82], [73, 27.21, 27.27, 68.38, 67.95], [74, 27.02, 27.028, 68.19, 68.96], [75, 26.975, 26.997, 68.23, 67.88], [76, 27.497, 27.628, 67.88, 67.75], [77, 27.699, 27.577, 67.98, 67.77], [78, 29.004, 29.06, 69.41, 67.05], [79, 28.874, 29.02, 67.42, 67.11], [80, 27.11, 27.095, 68.6, 68.57], [81, 27.119, 27.053, 71.49, 71.5], [82, 26.115, 26.094, 68.97, 68.7], [83, 26.082, 26.079, 68.84, 68.69], [84, 25.831, 25.859, 71.04, 68.75], [85, 25.866, 25.891, 68.73, 68.91], [86, 26.436, 26.417, 71.22, 71.53], [87, 26.423, 26.354, 68.56, 68.42], [88, 27.936, 27.791, 68.24, 68.06], [89, 27.769, 27.792, 70.62, 68.05], [90, 26.653, 26.739, 68.93, 68.58], [91, 26.804, 26.66, 68.69, 68.62], [92, 25.739, 25.68, 69.01, 68.64], [93, 25.653, 25.72, 71.44, 71.56], [94, 25.488, 25.393, 69.49, 68.93], [95, 25.469, 25.564, 69.07, 69.0], [96, 26.11, 26.031, 68.91, 68.71], [97, 25.963, 26.053, 69.17, 71.67], [98, 27.5, 27.502, 68.61, 68.41], [99, 27.479, 27.385, 68.55, 68.23], [100, 27.171, 27.172, 68.3, 68.52], [101, 27.086, 27.151, 71.45, 71.65], [102, 26.054, 25.943, 68.94, 68.46], [103, 26.007, 25.924, 68.58, 68.62], [104, 25.75, 25.826, 68.71, 68.68], [105, 25.85, 25.778, 68.89, 70.15], [106, 26.355, 26.432, 69.53, 68.39], [107, 26.453, 26.395, 68.42, 68.84], [108, 27.714, 27.888, 68.09, 68.2], [109, 27.723, 27.756, 67.95, 71.52], [110, 28.494, 28.326, 67.52, 67.74], [111, 28.345, 28.388, 67.29, 67.72], [112, 27.177, 27.275, 67.88, 67.85], [113, 27.25, 27.362, 71.31, 71.27], [114, 27.054, 27.103, 67.86, 68.26], [115, 26.945, 27.028, 67.94, 68.11], [116, 27.593, 27.602, 67.68, 67.61], [117, 27.587, 27.557, 69.49, 71.15], [118, 28.973, 28.91, 70.57, 67.51], [119, 28.948, 28.952, 67.21, 67.1]];
  const L = 56, R = 16, W = 880;
  const X = c => L + (c + 0.5) / 120 * (W - L - R);
  function panel(T, H, idx, ymin, ymax, unit, title) {
    const Y = v => T + (1 - (v - ymin) / (ymax - ymin)) * H;
    el('text', {x: L, y: T - 8, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, title);
    for (let v = ymin; v <= ymax + 1e-9; v += (ymax - ymin) / 5) { el('line', {x1: L, y1: Y(v), x2: W - R, y2: Y(v), stroke: RULE}, s); el('text', {x: L - 6, y: Y(v) + 4, 'text-anchor': 'end', 'font-size': 11, fill: MUTED}, s, v.toFixed(unit === 'ns' ? 1 : 0)); }
    el('text', {x: 10, y: T + H / 2, 'font-size': 11, fill: MUTED, transform: 'rotate(-90 10 ' + (T + H / 2) + ')', 'text-anchor': 'middle'}, s, unit);
    el('line', {x1: X(63.5), y1: T, x2: X(63.5), y2: T + H, stroke: RULE, 'stroke-dasharray': '4 3'}, s);
    let hi = D[0], lo = D[0];
    D.forEach(d => { if (Math.max(d[idx], d[idx + 1]) > Math.max(hi[idx], hi[idx + 1])) hi = d; if (Math.min(d[idx], d[idx + 1]) < Math.min(lo[idx], lo[idx + 1])) lo = d; });
    D.forEach(d => { const c = d[0], col = c < 64 ? S1 : S2; [idx, idx + 1].forEach(k => { const e = el('circle', {cx: X(c), cy: Y(d[k]), r: 3, fill: col, opacity: 0.8}, s); tip(e, 'CPU ' + c + ': ' + d[k].toFixed(2) + ' ' + unit); }); });
    [[hi, unit === 'ns' ? -8 : 15], [lo, unit === 'ns' ? 15 : -8]].forEach(([d, dy]) => { const v = (d[idx] + d[idx + 1]) / 2; el('text', {x: X(d[0]) + (d[0] > 100 ? -8 : 8), y: Y(v) + dy, 'text-anchor': d[0] > 100 ? 'end' : 'start', 'font-size': 11.5, fill: INK, 'font-weight': 600}, s, 'CPU ' + d[0] + ': ' + v.toFixed(1) + ' ' + unit); });
  }
  panel(30, 150, 1, 25, 31, 'ns', 'fresh 16 MiB chase, ns per load (SLC)');
  panel(240, 130, 3, 66, 72, 'GB/s', 'one-thread asmread at 8 MiB, GB/s (SLC)');
  for (let c = 0; c <= 100; c += 20) el('text', {x: X(c), y: 395, 'text-anchor': 'middle', 'font-size': 11, fill: MUTED}, s, 'CPU ' + c);
  el('text', {x: X(119), y: 395, 'text-anchor': 'end', 'font-size': 11, fill: MUTED}, s, 'CPU 119');
  el('text', {x: X(31), y: 412, 'text-anchor': 'middle', 'font-size': 11, fill: S1}, s, 'mesh 0, CPUs 0 to 63');
  el('text', {x: X(92), y: 412, 'text-anchor': 'middle', 'font-size': 11, fill: S2}, s, 'mesh 1, CPUs 64 to 119');
})();

// Core map: the crosspoint of each core pair on each mesh, from the latency gradient fit
(function () {
  const s = document.getElementById('coremap'), POS = [[0,0,1,2],[1,0,1,2],[2,0,1,3],[3,0,1,3],[4,0,1,4],[5,0,1,4],[6,0,2,1],[7,0,2,1],[8,0,2,2],[9,0,2,2],[10,0,2,3],[11,0,2,3],[12,0,2,4],[13,0,2,4],[14,0,2,5],[15,0,2,5],[16,0,3,1],[17,0,3,1],[18,0,3,2],[19,0,3,2],[20,0,3,3],[21,0,3,3],[22,0,3,4],[23,0,3,4],[24,0,3,5],[25,0,3,5],[26,0,4,1],[27,0,4,1],[28,0,4,2],[29,0,4,2],[30,0,4,3],[31,0,4,3],[32,0,4,4],[33,0,4,4],[34,0,4,5],[35,0,4,5],[36,0,5,1],[37,0,5,1],[38,0,5,2],[39,0,5,2],[40,0,5,3],[41,0,5,3],[42,0,5,4],[43,0,5,4],[44,0,5,5],[45,0,5,5],[46,0,6,1],[47,0,6,1],[48,0,6,2],[49,0,6,2],[50,0,6,3],[51,0,6,3],[52,0,6,4],[53,0,6,4],[54,0,6,5],[55,0,6,5],[56,0,7,1],[57,0,7,1],[58,0,7,2],[59,0,7,2],[60,0,7,3],[61,0,7,3],[62,0,7,4],[63,0,7,4],[64,1,1,2],[65,1,1,2],[66,1,1,3],[67,1,1,3],[68,1,1,4],[69,1,1,4],[70,1,2,1],[71,1,2,1],[72,1,2,2],[73,1,2,2],[74,1,2,3],[75,1,2,3],[76,1,2,4],[77,1,2,4],[78,1,2,5],[79,1,2,5],[80,1,3,1],[81,1,3,1],[82,1,3,2],[83,1,3,2],[84,1,3,3],[85,1,3,3],[86,1,3,4],[87,1,3,4],[88,1,3,5],[89,1,3,5],[90,1,4,1],[91,1,4,1],[92,1,4,2],[93,1,4,2],[94,1,4,3],[95,1,4,3],[96,1,4,4],[97,1,4,4],[98,1,4,5],[99,1,4,5],[100,1,5,1],[101,1,5,1],[102,1,5,2],[103,1,5,2],[104,1,5,3],[105,1,5,3],[106,1,5,4],[107,1,5,4],[108,1,5,5],[109,1,5,5],[110,1,6,1],[111,1,6,1],[112,1,6,2],[113,1,6,2],[114,1,6,3],[115,1,6,3],[116,1,6,4],[117,1,6,4],[118,1,6,5],[119,1,6,5]];
  const NOSLICE = ['1,5', '4,5', '7,5'], DX = 54, DY = 46, CW = 50, CH = 40;
  window.CORE_POS = POS; // reused by the core-port diagram
  [[0, 44, 'mesh 0 (arm_cmn_0): CPUs 0 to 63'], [1, 486, 'mesh 1 (arm_cmn_1): CPUs 64 to 119']].forEach(([m, X0, title]) => {
    const Y0 = 44;
    el('text', {x: X0, y: 16, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, title);
    for (let x = 1; x <= 7; x++) el('text', {x: X0 + (x - 1) * DX + CW / 2, y: 36, 'text-anchor': 'middle', 'font-size': 10.5, fill: MUTED}, s, 'X' + x);
    for (let y = 1; y <= 5; y++) el('text', {x: X0 - 6, y: Y0 + (5 - y) * DY + CH / 2 + 4, 'text-anchor': 'end', 'font-size': 10.5, fill: MUTED}, s, 'Y' + y);
    for (let y = 1; y <= 5; y++) for (let x = 1; x <= 7; x++) {
      const cs = POS.filter(p => p[1] === m && p[2] === x && p[3] === y).map(p => p[0]), X = X0 + (x - 1) * DX, Y = Y0 + (5 - y) * DY, nos = NOSLICE.includes(x + ',' + y);
      el('rect', Object.assign({x: X, y: Y, width: CW, height: CH, rx: 3, fill: cs.length ? '#eef3fa' : '#fff', stroke: nos ? MUTED : S1}, nos ? {'stroke-dasharray': '3 2'} : {}), s);
      if (cs.length) {
        el('text', {x: X + CW / 2, y: Y + (cs.length > 2 ? 16 : 24), 'text-anchor': 'middle', 'font-size': 11, fill: INK, 'font-weight': 600}, s, cs.length > 2 ? cs.slice(0, 2).join(',') : cs.join(','));
        if (cs.length > 2) el('text', {x: X + CW / 2, y: Y + 32, 'text-anchor': 'middle', 'font-size': 11, fill: INK, 'font-weight': 600}, s, cs.slice(2).join(','));
      } else el('text', {x: X + CW / 2, y: Y + 24, 'text-anchor': 'middle', 'font-size': 10, fill: MUTED}, s, nos ? 'no slice' : 'no cores');
    }
  });
  el('text', {x: 44, y: 286, 'font-size': 11.5, fill: MUTED}, s, 'Blue cells: a crosspoint with two slices and the listed cores on its core port. Numbering runs column by column, bottom to top.');
  el('text', {x: 44, y: 300, 'font-size': 11.5, fill: MUTED}, s, 'Column 7 of mesh 1 is where CPUs 120 to 127, not used here, would be.');
})();

// Distance map: CPU 0 latency to every slice of its own mesh and of the other mesh
(function () {
  const s = document.getElementById('dist'), G = [{"1,1":22.4,"1,2":20.8,"1,3":22.1,"1,4":24.3,"2,1":25.9,"2,2":23.3,"2,3":24.8,"2,4":27.0,"2,5":29.1,"3,1":28.1,"3,2":25.9,"3,3":29.9,"3,4":30.4,"3,5":32.2,"4,1":31.9,"4,2":31.1,"4,3":31.3,"4,4":33.4,"5,1":33.9,"5,2":32.7,"5,3":33.9,"5,4":36.1,"5,5":38.1,"6,1":37.4,"6,2":34.8,"6,3":38.1,"6,4":39.1,"6,5":41.3,"7,1":40.3,"7,2":39.5,"7,3":40.4,"7,4":43.2}, {"1,1":36.1,"1,2":38.1,"1,3":36.9,"1,4":34.0,"2,1":39.1,"2,2":41.1,"2,3":34.1,"2,4":36.7,"2,5":32.3,"3,1":41.8,"3,2":40.0,"3,3":38.0,"3,4":40.0,"3,5":35.0,"4,1":25.0,"4,2":33.2,"4,3":30.9,"4,4":29.1,"5,1":24.1,"5,2":28.8,"5,3":31.0,"5,4":22.2,"5,5":19.1,"6,1":27.2,"6,2":32.1,"6,3":26.1,"6,4":25.2,"6,5":23.1,"7,1":30.2,"7,2":22.2,"7,3":28.1,"7,4":28.1}];
  const DX = 54, DY = 46, CW = 50, CH = 40, vmin = 18, vmax = 44;
  const shade = v => { const k = Math.max(0, Math.min(1, (v - vmin) / (vmax - vmin))); return 'hsl(213 65% ' + (95 - k * 55) + '%)'; };
  [[0, 44, 'CPU 0 to the 64 slices of its own mesh (arm_cmn_0), ns'], [1, 486, 'CPU 0 to the other mesh\'s 64 slices, ns (via proxies)']].forEach(([m, X0, title]) => {
    const Y0 = 44;
    el('text', {x: X0, y: 16, 'font-size': 12.5, fill: INK, 'font-weight': 600}, s, title);
    for (let x = 1; x <= 7; x++) el('text', {x: X0 + (x - 1) * DX + CW / 2, y: 36, 'text-anchor': 'middle', 'font-size': 10.5, fill: MUTED}, s, 'X' + x);
    for (let y = 1; y <= 5; y++) el('text', {x: X0 - 6, y: Y0 + (5 - y) * DY + CH / 2 + 4, 'text-anchor': 'end', 'font-size': 10.5, fill: MUTED}, s, 'Y' + y);
    for (let y = 1; y <= 5; y++) for (let x = 1; x <= 7; x++) {
      const v = G[m][x + ',' + y], X = X0 + (x - 1) * DX, Y = Y0 + (5 - y) * DY, here = m === 0 && x === 1 && y === 2;
      if (v === undefined) { el('rect', {x: X, y: Y, width: CW, height: CH, rx: 3, fill: '#fff', stroke: MUTED, 'stroke-dasharray': '3 2'}, s); el('text', {x: X + CW / 2, y: Y + 24, 'text-anchor': 'middle', 'font-size': 10, fill: MUTED}, s, 'no slice'); continue; }
      el('rect', {x: X, y: Y, width: CW, height: CH, rx: 3, fill: shade(v), stroke: here ? '#c8373a' : '#fff', 'stroke-width': here ? 2.5 : 1}, s);
      el('text', {x: X + CW / 2, y: Y + 25, 'text-anchor': 'middle', 'font-size': 12.5, fill: v > 31 ? '#fff' : INK, 'font-weight': 600}, s, v.toFixed(1));
    }
  });
  el('text', {x: 44, y: 290, 'font-size': 11.5, fill: INK, 'font-weight': 600}, s, 'Own mesh: 19.0 ns at the home crosspoint (1,2), about 2.6 ns per hop, 42 ns at (7,4).');
  el('text', {x: 44, y: 308, 'font-size': 11.5, fill: MUTED}, s, 'Other mesh: the same range, lowest near column 5, which is where the proxies of those homes sit on this mesh.');
})();

// Mesh map data: the real 9 x 8 crosspoint grid of CRB mesh 0, parsed from crb/results/cmn-map.txt (mesh 1 is identical)
// Each entry: [x, y, XP number, port 0 type, port 0 node ids, port 1 type, port 1 node ids]
const MESH_D = [[0,0,0,"HN-T",[1],"CCG",[0,0]],[0,1,9,"SN-F_F",[],"",[]],[0,2,18,"SN-F_F",[],"",[]],[0,3,27,"SN-F_F",[],"",[]],[0,4,36,"SN-F_F",[],"",[]],[0,5,45,"SN-F_F",[],"",[]],[0,6,54,"SN-F_F",[],"",[]],[0,7,63,"HN-T",[14],"",[]],[1,0,1,"HN-I",[2],"????",[1]],[1,1,10,"HN-S",[0,1],"RN-F_F_E",[]],[1,2,19,"HN-S",[14,15],"RN-F_F_E",[]],[1,3,28,"HN-S",[28,29],"RN-F_F_E",[]],[1,4,37,"HN-S",[42,43],"RN-F_F_E",[]],[1,5,46,"HN-S",[],"RN-F_F_E",[]],[1,6,55,"HN-P",[10],"",[]],[1,7,64,"RN-I",[9],"CCG",[11,10]],[2,0,2,"HN-I",[3],"????",[2]],[2,1,11,"HN-S",[2,3],"RN-F_F_E",[]],[2,2,20,"HN-S",[16,17],"RN-F_F_E",[]],[2,3,29,"HN-S",[30,31],"RN-F_F_E",[]],[2,4,38,"HN-S",[44,45],"RN-F_F_E",[]],[2,5,47,"HN-S",[58,59],"RN-F_F_E",[]],[2,6,56,"RN-I",[2],"CCG",[8,3]],[2,7,65,"RN-D",[0],"HN-P",[15]],[3,0,3,"HN-I",[4],"????",[3]],[3,1,12,"HN-S",[4,5],"RN-F_F_E",[]],[3,2,21,"HN-S",[18,19],"RN-F_F_E",[]],[3,3,30,"HN-S",[32,33],"RN-F_F_E",[]],[3,4,39,"HN-S",[46,47],"RN-F_F_E",[]],[3,5,48,"HN-S",[60,61],"RN-F_F_E",[]],[3,6,57,"HN-P",[11],"",[]],[3,7,66,"RN-I",[11],"CCG",[12,12]],[4,0,4,"HN-I",[5],"",[]],[4,1,13,"HN-S",[6,7],"RN-F_F_E",[]],[4,2,22,"HN-S",[20,21],"RN-F_F_E",[]],[4,3,31,"HN-S",[34,35],"RN-F_F_E",[]],[4,4,40,"HN-S",[48,49],"RN-F_F_E",[]],[4,5,49,"HN-S",[],"RN-F_F_E",[]],[4,6,58,"RN-I",[4],"CCG",[9,5]],[4,7,67,"RN-D",[1],"HN-P",[16]],[5,0,5,"HN-I",[6],"????",[4]],[5,1,14,"HN-S",[8,9],"RN-F_F_E",[]],[5,2,23,"HN-S",[22,23],"RN-F_F_E",[]],[5,3,32,"HN-S",[36,37],"RN-F_F_E",[]],[5,4,41,"HN-S",[50,51],"RN-F_F_E",[]],[5,5,50,"HN-S",[64,65],"RN-F_F_E",[]],[5,6,59,"HN-P",[12],"",[]],[5,7,68,"RN-I",[13],"CCG",[13,14]],[6,0,6,"HN-I",[7],"????",[5]],[6,1,15,"HN-S",[10,11],"RN-F_F_E",[]],[6,2,24,"HN-S",[24,25],"RN-F_F_E",[]],[6,3,33,"HN-S",[38,39],"RN-F_F_E",[]],[6,4,42,"HN-S",[52,53],"RN-F_F_E",[]],[6,5,51,"HN-S",[66,67],"RN-F_F_E",[]],[6,6,60,"RN-I",[6],"CCG",[10,7]],[6,7,69,"RN-D",[2],"HN-P",[17]],[7,0,7,"HN-I",[8],"????",[6]],[7,1,16,"HN-S",[12,13],"RN-F_F_E",[]],[7,2,25,"HN-S",[26,27],"RN-F_F_E",[]],[7,3,34,"HN-S",[40,41],"RN-F_F_E",[]],[7,4,43,"HN-S",[54,55],"RN-F_F_E",[]],[7,5,52,"HN-S",[],"RN-F_F_E",[]],[7,6,61,"RN-I",[8],"HN-I",[13]],[7,7,70,"SBSX",[0],"HN-I",[18]],[8,0,8,"HN-T",[9],"CCG",[7,1]],[8,1,17,"SN-F_F",[],"",[]],[8,2,26,"SN-F_F",[],"",[]],[8,3,35,"SN-F_F",[],"",[]],[8,4,44,"SN-F_F",[],"",[]],[8,5,53,"SN-F_F",[],"",[]],[8,6,62,"SN-F_F",[],"",[]],[8,7,71,"RN-D",[3],"HN-D",[0]]];

// Core-port map: the mesh 0 grid, with the core port of each crosspoint (from the map file) and the CPUs the latency fit puts on it (mesh 0)
(function () {
  const s = document.getElementById('mesh2'), D = MESH_D, GREEN = '#1baf7a';
  const cpus = {};
  window.CORE_POS.filter(p => p[1] === 0).forEach(p => { (cpus[p[2] + ',' + p[3]] = cpus[p[2] + ',' + p[3]] || []).push(p[0]); });
  const X0 = 46, Y0 = 42, DX = 92, DY = 66, CW = 78, CH = 58;
  const cx = x => X0 + x * DX, cy = y => Y0 + (7 - y) * DY;
  const t = (x, y, str, a) => el('text', Object.assign({x, y, 'font-size': 11, fill: INK}, a || {}), s, str);
  for (let x = 0; x < 9; x++) t(cx(x) + CW / 2, 34, 'X ' + x, {'text-anchor': 'middle', fill: MUTED});
  for (let y = 0; y < 8; y++) t(X0 - 8, cy(y) + CH / 2 + 4, 'Y ' + y, {'text-anchor': 'end', fill: MUTED});
  for (let y = 0; y < 8; y++) for (let x = 0; x < 9; x++) {
    if (x < 8) el('line', {x1: cx(x) + CW, y1: cy(y) + CH / 2, x2: cx(x + 1), y2: cy(y) + CH / 2, stroke: '#b9c4d1', 'stroke-width': 2}, s);
    if (y < 7) el('line', {x1: cx(x) + CW / 2, y1: cy(y), x2: cx(x) + CW / 2, y2: cy(y + 1) + CH, stroke: '#b9c4d1', 'stroke-width': 2}, s);
  }
  D.forEach(([x, y, n, p0, ids0, p1]) => {
    const X = cx(x), Y = cy(y), port = p1 === 'RN-F_F_E', cs = cpus[x + ',' + y] || [];
    let l2, l3, l4, fill = '#f5f7f9', stroke = '#9aa3ad', dash = null;
    if (p0 === 'HN-S' && ids0.length) l2 = 'HN-S #' + ids0.join(' #');
    else if (p0 === 'HN-S') { l2 = 'HN-S, no node'; dash = '3 2'; }
    else if (p0 === 'SN-F_F') l2 = 'SN-F (memory)';
    else l2 = (p0 + (p1 ? ' / ' + p1 : '')).replace('????', '?');
    if (port) {
      stroke = S1; fill = cs.length ? '#eef3fa' : '#fff';
      l3 = 'core port'; l4 = cs.length ? 'CPUs ' + cs.join(', ') : 'no CPU found';
    } else { l3 = 'no core port'; l4 = ''; }
    el('rect', Object.assign({x: X, y: Y, width: CW, height: CH, rx: 4, fill, stroke, 'stroke-width': port ? 1.3 : 1}, dash ? {'stroke-dasharray': dash} : {}), s);
    const m = {'text-anchor': 'middle', 'font-size': 9};
    t(X + CW / 2, Y + 12, 'XP ' + n, Object.assign({}, m, {fill: MUTED}));
    t(X + CW / 2, Y + 25, l2, m);
    t(X + CW / 2, Y + 38, l3, Object.assign({}, m, port ? {fill: S1, 'font-weight': 600} : {fill: MUTED}));
    if (l4) t(X + CW / 2, Y + 51, l4, Object.assign({}, m, cs.length ? {'font-weight': 600} : {fill: MUTED}));
  });
  // legend
  const LY = 586;
  [['#eef3fa', S1, null, 'core port with 2 CPUs found on it: 32 crosspoints. CPU numbers are mesh 0, placed from measured latency.'],
   ['#fff', S1, null, 'core port with no CPU found on it: 3 crosspoints (XP 10, 46, 52)'],
   ['#f5f7f9', '#9aa3ad', null, 'no core port: 37 crosspoints (memory ports, CCG, I/O nodes)'],
   ['#fff', S1, '3 2', 'dashed border: port 0 has type HN-S and the driver lists no home node on it (XP 46, 49, 52)']].forEach((g, i) => {
    const y = LY + i * 17;
    el('rect', Object.assign({x: 8, y: y - 10, width: 14, height: 12, rx: 2, fill: g[0], stroke: g[1]}, g[2] ? {'stroke-dasharray': g[2]} : {}), s);
    t(28, y, g[3], {'font-size': 11.5});
  });
  // inset: what is attached to one crosspoint. Ports are on the crosspoint. Devices attach to ports.
  t(8, 676, 'Inside one crosspoint: XP 20 at (2,2). A port and the devices on it are separate things.', {'font-size': 12.5, 'font-weight': 600});
  el('rect', {x: 40, y: 700, width: 150, height: 140, rx: 6, fill: '#fff', stroke: INK, 'stroke-width': 1.3}, s);
  t(115, 760, 'XP 20', {'text-anchor': 'middle', 'font-size': 13, 'font-weight': 600});
  t(115, 777, 'crosspoint (router)', {'text-anchor': 'middle', fill: MUTED});
  t(115, 793, '4 mesh links, to', {'text-anchor': 'middle', fill: MUTED, 'font-size': 10});
  t(115, 806, 'XP 11, 19, 21, 29', {'text-anchor': 'middle', fill: MUTED, 'font-size': 10});
  const row = (yc, label, type, calDash, calText, devs, fill, stroke, notes) => {
    el('circle', {cx: 190, cy: yc, r: 5, fill: stroke}, s);
    el('line', {x1: 190, y1: yc, x2: 330, y2: yc, stroke, 'stroke-width': 2}, s);
    t(260, yc - 7, label, {'text-anchor': 'middle', 'font-size': 10.5, 'font-weight': 600, fill: stroke});
    t(260, yc + 14, type, {'text-anchor': 'middle', 'font-size': 10, fill: MUTED});
    el('rect', Object.assign({x: 330, y: yc - 17, width: 70, height: 34, rx: 4, fill: '#fff', stroke}, calDash ? {'stroke-dasharray': '4 3'} : {}), s);
    t(365, yc + 4, calText, {'text-anchor': 'middle', 'font-size': 10.5});
    devs.forEach((d, i) => {
      const y = yc - 31 + i * 34;
      el('line', {x1: 400, y1: yc, x2: 440, y2: y + 14, stroke, 'stroke-width': 1.5}, s);
      el('rect', {x: 440, y, width: 140, height: 28, rx: 4, fill, stroke}, s);
      t(510, y + 18, d, {'text-anchor': 'middle', 'font-weight': 600});
    });
    notes.forEach((n, i) => t(596, yc - 14 + i * 15, n, i === 2 ? {fill: MUTED} : {}));
  };
  row(735, 'port 0: HN-S port', 'type HN-S', false, 'CAL2', ['HN-S #16', 'HN-S #17'], '#eef3fa', S1,
    ['2 home nodes, inside the mesh (CMN).', 'Each holds one slice of the SLC.', 'The map prints both ids, #16 and #17.']);
  row(805, 'port 1: core port', 'type RN-F_F_E', true, 'CAL2 ?', ['CPU 8', 'CPU 9'], '#eaf7f1', GREEN,
    ['2 cores, outside the mesh (Arm: RN-F).', 'Each has its own L1 and L2.', 'The map prints no id here. CPUs: from latency.']);
  t(8, 856, 'Arm allows 1, 2 or 4 cores on one core port (no CAL, CAL2 for two devices, CAL4 for four devices).', {fill: MUTED});
  t(8, 871, 'CRB: 2 on each used port, from two timing tests (latency fit and pair test). Not read from hardware.', {fill: MUTED});
})();


;

// Data-path figures: one chip template, marked per measurement (who runs the loop, where the data is, the path).
(function () {
  const S1 = '#2a78d6', S2 = '#eb6834', INK = '#1b1f24', MUTED = '#5b6470';
  const ACTF = '#cfe0f8', PROVF = '#fde3d6', IDLEF = '#eef0f3', IDLEK = '#c3c9d1';
  const svgNS = 'http://www.w3.org/2000/svg';
  function el(tag, attrs, parent, text) { const e = document.createElementNS(svgNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text !== undefined) e.textContent = text; parent.appendChild(e); return e; }
  function marker(s, id, color) { const d = el('defs', {}, s); const m = el('marker', {id, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: 'auto'}, d); el('path', {d: 'M0,0 L10,5 L0,10 z', fill: color}, m); }
  function arrow(s, x1, y1, x2, y2, id, w) { el('line', {x1, y1, x2, y2, stroke: INK, 'stroke-width': w || 1.6, 'marker-end': 'url(#' + id + ')'}, s); }
  // chip(s, px, py, k, o): two chiplets. o.active = Set of CPUs running the loop; o.mesh = 'idle'|'prov'|'pass';
  // o.mem = 'idle'|'prov'|'maybe'; o.mode = 'read'|'write'; o.labels = true draws the template annotations.
  function chip(s, px, py, k, o) {
    const CW = 196 * k, CH = 134 * k, GAP = 24 * k, f = 9.5 * k;
    for (let c = 0; c < 2; c++) {
      const x = px + 8 * k + c * (CW + GAP), y = py;
      el('rect', {x, y, width: CW, height: CH, rx: 5 * k, fill: '#ffffff', stroke: IDLEK}, s);
      el('text', {x: x + 8 * k, y: y + 12 * k, 'font-size': f, fill: MUTED}, s, 'chiplet ' + c + ': CPUs ' + (64 * c) + ' to ' + (64 * c + 63));
      const gx = x + 10 * k, gy = y + 19 * k, hasActive = [...o.active].some(v => (v >> 6) === c);
      for (let p = 0; p < 32; p++) {
        const col = p % 8, row = p >> 3;
        for (let h = 0; h < 2; h++) {
          const cpu = c * 64 + p * 2 + h, on = o.active.has(cpu);
          const rx = gx + col * 22 * k + h * 10 * k, ry = gy + row * 14 * k;
          const r = el('rect', {x: rx, y: ry, width: 9 * k, height: 11 * k, fill: on ? ACTF : IDLEF, stroke: on ? S1 : IDLEK, 'stroke-width': on ? 1.2 : 0.7}, s);
          el('title', {}, r, 'CPU ' + cpu + (on ? ': runs the loop' : ': idle'));
        }
      }
      const bw = 176 * k, my = y + 84 * k, mmy = y + 110 * k, xc = gx + bw / 2;
      const meshFill = o.mesh === 'prov' && hasActive ? PROVF : IDLEF, meshK = o.mesh === 'prov' && hasActive ? S2 : IDLEK;
      el('rect', {x: gx, y: my, width: bw, height: 16 * k, fill: meshFill, stroke: meshK, 'stroke-dasharray': o.mesh === 'pass' && hasActive ? '3 2' : 'none'}, s);
      el('text', {x: xc, y: my + 11.5 * k, 'text-anchor': 'middle', 'font-size': f, fill: INK}, s, 'mesh: 64 slices of 1 MiB');
      const memOn = o.mem === 'prov' || (o.mem === 'maybe');
      el('rect', {x: gx, y: mmy, width: bw, height: 14 * k, fill: memOn ? PROVF : IDLEF, stroke: memOn ? S2 : IDLEK, 'stroke-dasharray': o.mem === 'maybe' ? '3 2' : 'none'}, s);
      el('text', {x: xc, y: mmy + 10.5 * k, 'text-anchor': 'middle', 'font-size': f, fill: INK}, s, '5 DDR5 channels' + (o.mem === 'maybe' ? ' (?)' : ''));
      if (hasActive && o.mesh !== 'idle') {
        const id = o.mode === 'read' ? 'pa-up' : 'pa-dn';
        if (o.mode === 'read') arrow(s, xc, my - 1, xc, gy + 56 * k, id, 1.6 * k); else arrow(s, xc, gy + 55 * k, xc, my - 1, id, 1.6 * k);
        if (o.mem !== 'idle') { if (o.mode === 'read') arrow(s, xc, mmy - 1, xc, my + 17 * k, id, 1.6 * k); else arrow(s, xc, my + 16 * k, xc, mmy - 1, id, 1.6 * k); }
      }
    }
    // chip-to-chip links
    const lx = px + 8 * k + CW, ly = py + 60 * k;
    el('line', {x1: lx, y1: ly, x2: lx + GAP, y2: ly, stroke: IDLEK, 'stroke-width': 3 * k}, s);
    el('line', {x1: lx, y1: ly + 10 * k, x2: lx + GAP, y2: ly + 10 * k, stroke: IDLEK, 'stroke-width': 3 * k}, s);
    if (o.labels) {
      el('text', {x: lx + GAP / 2, y: ly - 14 * k, 'text-anchor': 'middle', 'font-size': 7.5 * k, fill: MUTED}, s, 'chip-to-chip');
      el('text', {x: lx + GAP / 2, y: ly - 5 * k, 'text-anchor': 'middle', 'font-size': 7.5 * k, fill: MUTED}, s, 'links (CCG)');
    }
  }
  // strip(s, px, py, k, o): one core's path. o.level: index of the box that holds the data (1 L1, 2 L2, 4 SLC slice, 5 DDR); o.pass: indexes passed through.
  const BOX = ['core', 'L1 64 KiB', 'L2 2 MiB', 'pair port', 'SLC slice', 'DDR5'];
  function strip(s, px, py, k, o) {
    const w = [40, 54, 54, 58, 66, 44].map(v => v * k), aw = 20 * k, h = 22 * k, f = 9.5 * k;
    let x = px + 8 * k;
    const xs = [];
    for (let i = 0; i < 6; i++) {
      const held = i === o.level, pass = o.pass.includes(i), core = i === 0, far = i > o.level;
      el('rect', {x, y: py, width: w[i], height: h, rx: 3 * k, fill: held ? PROVF : core ? ACTF : IDLEF, stroke: held ? S2 : core ? S1 : IDLEK, 'stroke-dasharray': pass ? '3 2' : 'none', opacity: far ? 0.45 : 1}, s);
      el('text', {x: x + w[i] / 2, y: py + 14.5 * k, 'text-anchor': 'middle', 'font-size': f, fill: INK, opacity: far ? 0.6 : 1}, s, BOX[i]);
      xs.push(x); x += w[i] + aw;
    }
    for (let i = 0; i < 5; i++) {
      const a = xs[i] + w[i] + 2 * k, b = xs[i + 1] - 2 * k, ym = py + h / 2;
      if (i < o.level) { if (o.mode === 'read') arrow(s, b, ym, a, ym, 'pa-lt', 1.6 * k); else arrow(s, a, ym, b, ym, 'pa-rt', 1.6 * k); }
      else el('line', {x1: a, y1: ym, x2: b, y2: ym, stroke: IDLEK, 'stroke-width': 1.2 * k, opacity: 0.6}, s);
    }
    if (o.labels) {
      const notes = ['runs the loop', 'private, 4-way', 'private, 8-way', 'shared by 2 cores', 'by address hash', '10 in all'];
      for (let i = 0; i < 6; i++) el('text', {x: xs[i] + w[i] / 2, y: py + h + 13 * k, 'text-anchor': 'middle', 'font-size': 8.5 * k, fill: MUTED}, s, notes[i]);
    }
  }
  function panel(s, px, py, p) {
    el('text', {x: px + 8, y: py + 13, 'font-size': 13, 'font-weight': 600, fill: INK}, s, p.title);
    chip(s, px, py + 20, 1, p);
    strip(s, px, py + 166, 1, p);
    p.lines.forEach((t, i) => el('text', {x: px + 8, y: py + 206 + i * 13, 'font-size': 10.5, fill: MUTED}, s, t));
  }
  function figure(id, panels) {
    const s = document.getElementById(id); if (!s) return;
    ['pa-up', 'pa-dn', 'pa-lt', 'pa-rt'].forEach(m => marker(s, m, INK));
    panels.forEach((p, i) => { if (p) panel(s, (i % 2) * 440, Math.floor(i / 2) * 250, p); });
  }
  const one = new Set([0]), all = new Set([...Array(120).keys()]);
  const mesh40 = new Set([...Array(40).keys()].map(i => 2 * i));
  const dram30 = new Set([...Array(30).keys()].map(i => 4 * i));
  const dram16 = new Set([...Array(8).keys()].flatMap(i => [8 * i, 64 + 8 * i]));
  const L1 = {level: 1, pass: [], mesh: 'idle', mem: 'idle'}, L2 = {level: 2, pass: [1], mesh: 'idle', mem: 'idle'};
  const MESH = {level: 4, pass: [1, 2, 3], mesh: 'prov', mem: 'idle'}, DRAM = {level: 5, pass: [1, 2, 3, 4], mesh: 'pass', mem: 'prov'};
  const DRAM1 = Object.assign({}, DRAM, {mem: 'maybe'});
  // template
  (function () {
    const s = document.getElementById('tmpl'); if (!s) return;
    ['pa-up', 'pa-dn', 'pa-lt', 'pa-rt'].forEach(m => marker(s, m, INK));
    chip(s, 0, 6, 2, {active: new Set(), mesh: 'idle', mem: 'idle', mode: 'read', labels: true});
    el('text', {x: 36, y: 44, 'font-size': 10.5, fill: INK}, s, '32 pairs of cores, each pair = 2 cores on one port');
    strip(s, 0, 290, 2, {level: -1, pass: [], mode: 'read', labels: true});
  })();
  figure('path-r1', [
    Object.assign({title: 'L1: 133 GB/s (32 KiB buffer)', active: one, mode: 'read', lines: ['CPU 0 reads its own L1. Nothing leaves the core.', 'Limit: 3 loads of 16 B per cycle.']}, L1),
    Object.assign({title: 'L2: 85 GB/s (1 MiB buffer)', active: one, mode: 'read', lines: ['CPU 0 reads its own L2 through L1. Nothing leaves the core.', 'Limit: inside the core.']}, L2),
    Object.assign({title: 'SLC: 67 GB/s (8 MiB buffer)', active: one, mode: 'read', lines: ['Slices on chiplet 0 serve 81 % of lines, the own L2 19 %.', 'Lines homed on chiplet 1 come from a proxy slice on chiplet 0.']}, MESH),
    Object.assign({title: 'DRAM: 30 GB/s (1 GiB buffer)', active: one, mode: 'read', lines: ['Every line misses in the slice and comes from a DDR5 channel.', 'Which chiplet’s channels: not resolved by the counters.']}, DRAM1)]);
  figure('path-w1', [
    Object.assign({title: 'L1: 89.5 GB/s (32 KiB buffer)', active: one, mode: 'write', lines: ['CPU 0 writes whole lines into its own L1.', 'Limit: 2 stores of 16 B per cycle.']}, L1),
    Object.assign({title: 'L2: 89.5 GB/s (1 MiB buffer)', active: one, mode: 'write', lines: ['The buffer fits in L2; the same store limit applies.', 'No allocation in L1 or L2 on the way out (part 5 counters).']}, L2),
    Object.assign({title: '"SLC": 73 GB/s (8 MiB buffer) goes to DRAM', active: one, mode: 'write', lines: ['The home node does not keep the lines (0.013 fills per line).', 'About 1 memory request per line: this is a DRAM write path.']}, Object.assign({}, DRAM1, {mesh: 'pass'})),
    Object.assign({title: 'DRAM: 63 GB/s (1 GiB buffer)', active: one, mode: 'write', lines: ['Same path as the 8 MiB case, larger buffer.', 'Which chiplet’s channels: not resolved by the counters.']}, DRAM1)]);
  figure('path-rc', [
    Object.assign({title: 'L1: 15.9 TB/s, 120 threads', active: all, mode: 'read', lines: ['120 cores each read their own L1, 32 KiB each.', '120 × 132 GB/s: no shared part is involved.']}, L1),
    Object.assign({title: 'L2: 10.2 TB/s, 120 threads', active: all, mode: 'read', lines: ['120 cores each read their own L2, 1 MiB each.', '120 × 85 GB/s: no shared part is involved.']}, L2),
    Object.assign({title: 'SLC: ≥ 0.62 TB/s of 1.38, 40 threads', active: mesh40, mode: 'read', lines: ['CPUs 0, 2, … 78: 32 pairs on chiplet 0, 8 on chiplet 1, 3 MiB each.', 'Slices serve 45 % of lines (0.62 TB/s), each core’s L2 the rest.']}, MESH),
    Object.assign({title: 'DRAM: 533 GB/s, 30 threads', active: dram30, mode: 'read', lines: ['CPUs 0, 4, … 116: 15 per chiplet, 256 MiB each.', 'All 10 channels serve; 83 % of the 640 GB/s peak.']}, DRAM)]);
  figure('path-wc', [
    Object.assign({title: 'L1: 10.7 TB/s, 120 threads', active: all, mode: 'write', lines: ['120 cores each write their own L1.', '120 × 89.5 GB/s: no shared part is involved.']}, L1),
    Object.assign({title: 'L2: 10.7 TB/s, 120 threads', active: all, mode: 'write', lines: ['120 cores each write their own L2.', '120 × 89.5 GB/s: no shared part is involved.']}, L2),
    Object.assign({title: 'SLC: no number (writes are not kept)', active: new Set(), mode: 'write', lines: ['Streaming writes bypass slice allocation and go to DRAM.', 'A many-core write stream is the DRAM panel.']}, {level: -1, pass: [4], mesh: 'idle', mem: 'idle'}),
    Object.assign({title: 'DRAM: 447 GB/s, 16 threads', active: dram16, mode: 'write', lines: ['16 writers 8 cores apart, both chiplets, 256 MiB each (drawn 8 + 8).', 'All 10 channels absorb; 70 % of peak. 32 + 32 writers would collapse it.']}, DRAM)]);
})();
