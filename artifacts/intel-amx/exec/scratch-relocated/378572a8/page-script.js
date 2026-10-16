const sink={panels:'',arms:'',pairs:''};
const document={getElementById:id=>({insertAdjacentHTML:(w,h)=>{sink[id]+=h;},set innerHTML(v){sink[id]=v;}})};

const C = { main:'#009E73', pr3:'#E69F00', pr4:'#D55E00', probe:'#0072B2' };
const ARMS = [ ['main','baseoff','main'], ['pr3','headoff','PR 3'], ['pr4','newoff','PR 4'], ['probe','lazyoff','probe'] ];
// means and sample sd over 3 repetitions, from exec/results/pr4off-E-cpu/summary.md
const cells = [
 { name:'tp2, 8 users, prompt 1,024',
   tps:  { main:[72.83,0.01], pr3:[75.83,0.11], pr4:[73.36,0.30], probe:[74.81,0.24] },
   ttft: { main:[3.945,0.004], pr3:[3.862,0.002], pr4:[3.866,0.001], probe:[3.866,0.002] },
   takeTps:'PR 4 is 0.53 TPS (+0.7 %) above main, inside the 0.60 TPS band. PR 3 is 3.00 TPS (+4.1 %) above main, beyond it. The probe adds 1.45 TPS (+2.0 %) to PR 4, beyond the band.',
   takeTtft:'PR 3, PR 4 and the probe are 78 to 83 ms faster than main, inside the 0.15 s floor of the band.' },
 { name:'tp2, 8 users, prompt 8,192',
   tps:  { main:[14.57,0.02], pr3:[15.37,0.03], pr4:[14.96,0.02], probe:[15.10,0.03] },
   ttft: { main:[122.841,0.220], pr3:[117.274,0.067], pr4:[117.861,0.101], probe:[117.882,0.164] },
   takeTps:'PR 4 is 0.39 TPS (+2.7 %) above main, 0.01 TPS under the 0.40 TPS floor, so inside the band. PR 3 (+0.80 TPS, +5.5 %) and the probe (+0.53 TPS, +3.6 %) are beyond it.',
   takeTtft:'PR 4 is 4.98 s (4.1 %) faster than main, beyond the 0.44 s band. PR 3 is 5.57 s faster. PR 4 is 0.59 s slower than PR 3, beyond that pair’s 0.20 s band.' },
 { name:'tp4, 8 users, prompt 1,024',
   tps:  { main:[111.67,0.92], pr3:[111.63,0.40], pr4:[111.07,0.08], probe:[111.24,0.78] },
   ttft: { main:[2.471,0.003], pr3:[2.387,0.003], pr4:[2.403,0.007], probe:[2.398,0.003] },
   takeTps:'All four arms lie within 0.60 TPS of each other, inside the 1.84 TPS band (main’s repetitions vary by 0.92 TPS).',
   takeTtft:'PR 3, PR 4 and the probe are 68 to 84 ms faster than main, inside the 0.15 s floor of the band.' },
];
const band = (a, b, floor) => Math.max(2 * Math.max(a[1], b[1]), floor);
const fmt = (v, d) => v.toFixed(d);
function panel(c, key, unit, floor, dec) {
  const d = c[key]; const W = 560, L = 64, R = 118, rowH = 26, top = 16, H = top + rowH * 4 + 30;
  const vals = ARMS.map(a => d[a[0]][0]); const bw = band(d.main, d.pr4, floor);
  let lo = Math.min(...vals, d.main[0] - bw), hi = Math.max(...vals, d.main[0] + bw); const pad = (hi - lo) * 0.12 || 0.3; lo -= pad; hi += pad;
  const x = v => L + (v - lo) / (hi - lo) * (W - L - R);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${c.name}, ${unit}">`;
  s += `<rect x="${x(d.main[0] - bw)}" y="${top - 6}" width="${x(d.main[0] + bw) - x(d.main[0] - bw)}" height="${rowH * 4 + 6}" fill="#e6eaef"/>`;
  s += `<line x1="${x(d.main[0])}" y1="${top - 6}" x2="${x(d.main[0])}" y2="${top + rowH * 4}" stroke="${C.main}" stroke-width="1" opacity="0.6"/>`;
  ARMS.forEach(([k, arm, label], i) => {
    const y = top + rowH * i + rowH / 2; const v = d[k][0];
    if (k === 'pr4') s += `<line x1="${x(d.main[0])}" y1="${y}" x2="${x(v)}" y2="${y}" stroke="${C.pr4}" stroke-width="2"/>`;
    s += `<text x="${L - 8}" y="${y + 4}" text-anchor="end" font-size="12" fill="#5b6470">${label}</text>`;
    s += `<g><title>${arm}: ${fmt(v, dec)} ${unit}, sd ${fmt(d[k][1], dec)}, n = 3</title><circle cx="${x(v)}" cy="${y}" r="7" fill="#fff"/><circle cx="${x(v)}" cy="${y}" r="5" fill="${C[k]}"/></g>`;
    const left = k === 'pr4' && d.main[0] > v;  // keep the PR 4 label off its connector to main
    s += `<text x="${x(v) + (left ? -10 : 10)}" y="${y + 4}" text-anchor="${left ? 'end' : 'start'}" font-size="12" fill="#1b1f23" stroke="#fff" stroke-width="4" paint-order="stroke">${fmt(v, dec)}</text>`;
  });
  const delta = d.pr4[0] - d.main[0], pct = Number(T[c.name]['newoff vs baseoff'][key === 'tps' ? 0 : 1]), verdict = Math.abs(delta) > bw ? 'beyond' : 'inside';
  const ypr4 = top + rowH * 2 + rowH / 2;
  s += `<text x="${W - R + 4}" y="${ypr4 - 4}" font-size="11" fill="#1b1f23">PR 4 vs main</text><text x="${W - R + 4}" y="${ypr4 + 9}" font-size="11" fill="#1b1f23">${delta >= 0 ? '+' : '-'}${fmt(Math.abs(delta), dec)} (${pct >= 0 ? '+' : '-'}${Math.abs(pct).toFixed(1)} %)</text><text x="${W - R + 4}" y="${ypr4 + 22}" font-size="11" fill="#5b6470">${verdict} the band</text>`;
  const ay = top + rowH * 4 + 8; s += `<line x1="${L}" y1="${ay}" x2="${W - R}" y2="${ay}" stroke="#d0d7de"/>`;
  for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4; s += `<line x1="${x(v)}" y1="${ay}" x2="${x(v)}" y2="${ay + 4}" stroke="#d0d7de"/><text x="${x(v)}" y="${ay + 16}" text-anchor="middle" font-size="10" fill="#5b6470">${fmt(v, dec === 3 ? 2 : 1)}</text>`; }
  s += `</svg>`;
  return `<div class="panel"><h3>${unit === 'TPS' ? 'Decode TPS per user' : 'Prefill TTFT, s'} (band ${fmt(bw, dec === 3 ? 2 : 2)} ${unit === 'TPS' ? 'TPS' : 's'})</h3>${s}<p class="take">${key === 'tps' ? c.takeTps : c.takeTtft}</p></div>`;
}
// tables
let t = '<tr><th>Cell</th>' + ARMS.map(a => `<th class="num">${a[1]} TPS</th>`).join('') + ARMS.map(a => `<th class="num">${a[1]} TTFT s</th>`).join('') + '</tr>';
for (const c of cells) t += `<tr><td>${c.name}</td>` + ARMS.map(a => `<td class="num">${fmt(c.tps[a[0]][0], 2)} (${fmt(c.tps[a[0]][1], 2)})</td>`).join('') + ARMS.map(a => `<td class="num">${fmt(c.ttft[a[0]][0], 3)} (${fmt(c.ttft[a[0]][1], 3)})</td>`).join('') + '</tr>';
document.getElementById('arms').innerHTML = t;
// paired t values from summary.md (the page does not have the per-repetition values)
// from summary.md: [TPS delta %, TTFT delta %, paired t of TPS, paired t of TTFT]
const T = {
 'tp2, 8 users, prompt 1,024': { 'newoff vs baseoff':['+0.7','-2.0','+2.9','-37.4'], 'lazyoff vs baseoff':['+2.7','-2.0','+14.4','-26.1'], 'headoff vs baseoff':['+4.1','-2.1','+42.6','-28.1'], 'lazyoff vs newoff':['+2.0','+0.0','+5.2','+0.1'], 'newoff vs headoff':['-3.3','+0.1','-22.7','+4.3'] },
 'tp2, 8 users, prompt 8,192': { 'newoff vs baseoff':['+2.7','-4.1','+20.1','-38.1'], 'lazyoff vs baseoff':['+3.6','-4.0','+35.0','-67.5'], 'headoff vs baseoff':['+5.5','-4.5','+42.8','-38.1'], 'lazyoff vs newoff':['+0.9','+0.0','+4.4','+0.3'], 'newoff vs headoff':['-2.7','+0.5','-39.4','+18.1'] },
 'tp4, 8 users, prompt 1,024': { 'newoff vs baseoff':['-0.5','-2.7','-1.2','-12.0'], 'lazyoff vs baseoff':['-0.4','-2.9','-0.5','-96.4'], 'headoff vs baseoff':['-0.0','-3.4','-0.1','-24.2'], 'lazyoff vs newoff':['+0.2','-0.2','+0.4','-0.9'], 'newoff vs headoff':['-0.5','+0.6','-2.5','+5.5'] },
};
const host = document.getElementById('panels');
for (const c of cells) {
  host.insertAdjacentHTML('beforeend', `<p class="cellhead">${c.name}</p><div class="cellrow">${panel(c, 'tps', 'TPS', 0.40, 2)}${panel(c, 'ttft', 's', 0.15, 3)}</div>`);
}
const PAIRS = [['pr4','main'],['probe','main'],['pr3','main'],['probe','pr4'],['pr4','pr3']];
const nm = k => ARMS.find(a => a[0] === k)[1];
let q = '<tr><th>Cell</th><th>Pair</th><th class="num">TPS delta</th><th class="num">band</th><th>verdict</th><th class="num">paired t</th><th class="num">TTFT delta</th><th class="num">band</th><th>verdict</th><th class="num">paired t</th></tr>';
for (const c of cells) for (const [a, b] of PAIRS) {
  const pair = `${nm(a)} vs ${nm(b)}`;
  const dt = c.tps[a][0] - c.tps[b][0], bt = band(c.tps[a], c.tps[b], 0.40);
  const df = (c.ttft[a][0] - c.ttft[b][0]) * 1000, bf = band(c.ttft[a], c.ttft[b], 0.15) * 1000;
  const sg = (v, d) => (v >= 0 ? '+' : '-') + Math.abs(v).toFixed(d); const r = T[c.name][pair];
  q += `<tr><td>${c.name}</td><td>${pair}</td><td class="num">${sg(dt, 2)} TPS (${r[0]} %)</td><td class="num">${bt.toFixed(2)}</td><td>${Math.abs(dt) > bt ? 'beyond' : 'inside'}</td><td class="num">${r[2]}</td><td class="num">${sg(df, 0)} ms (${r[1]} %)</td><td class="num">${bf.toFixed(0)} ms</td><td>${Math.abs(df) > bf ? 'beyond' : 'inside'}</td><td class="num">${r[3]}</td></tr>`;
}
document.getElementById('pairs').innerHTML = q;
console.log('svgs', (sink.panels.match(/<svg/g)||[]).length, 'labels anchored end:', (sink.panels.match(/text-anchor="end" font-size="12" fill="#1b1f23"/g)||[]).length, 'pairs rows', sink.pairs.split('<tr>').length-2);
