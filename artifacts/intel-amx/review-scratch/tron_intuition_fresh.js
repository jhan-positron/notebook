'use strict';
const facts = JSON.parse(document.getElementById('evidence-data').textContent);
const models = JSON.parse(document.getElementById('model-data').textContent);
const byId = id => document.getElementById(id);
const fmt = (n, digits = 2) => n.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits});
const whole = n => fmt(n, 0);
const svgStart = (width, height, label) => `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${label}"><g font-family="system-ui,sans-serif" fill="#172e3b">`;
const svgEnd = '</g></svg>';
function numberInput(id) {
  const node = byId(id);
  return node.value.trim() !== '' && node.checkValidity() && Number.isFinite(node.valueAsNumber) ? node.valueAsNumber : null;
}

function updateWork() {
  const model = models.find(m => m.id === byId('model-select').value);
  const B = numberInput('query-count');
  const S = numberInput('visible-keys');
  if (B === null || S === null) {
    for (const id of ['work-pairs', 'work-ops', 'work-bytes']) byId(id).textContent = '—';
    byId('work-split').innerHTML = '';
    byId('work-status').textContent = 'Enter whole query and visible-key counts within the displayed limits.';
    return;
  }
  const full = B * model.kv * model.full * S;
  const window = B * model.kv * model.window * Math.min(S, 128);
  const pairs = full + window;
  const operations = 4 * pairs * (model.q / model.kv) * model.h;
  const bytes = 4 * pairs * model.h;
  byId('work-pairs').textContent = whole(pairs);
  byId('work-ops').textContent = fmt(operations / 1e9, 3);
  byId('work-bytes').textContent = fmt(bytes / 1048576, 2);
  const width = Math.max(270, byId('work-split').clientWidth);
  const plotWidth = width - 12;
  let svg = svgStart(width, 151, 'Logical attention work in full and window layers, with a common zero baseline.');
  const rows = [['Full layers', full, '#007c67'], ['Window layers', window, '#0072b2']];
  rows.forEach(([label, value, color], index) => {
    const y = 21 + index * 66;
    svg += `<text x="0" y="${y}" font-size="12">${label} · ${whole(value)} pairs (${fmt(value / pairs * 100, 2)}%)</text>`;
    svg += `<rect x="0" y="${y+9}" width="${plotWidth}" height="20" rx="3" fill="#edf2f4"/><rect x="0" y="${y+9}" width="${plotWidth*value/pairs}" height="20" fill="${color}"/>`;
  });
  svg += `<text x="0" y="147" font-size="11" fill="#526774">0%</text><text x="${plotWidth}" y="147" text-anchor="end" font-size="11" fill="#526774">100% of logical work</text>` + svgEnd;
  byId('work-split').innerHTML = svg;
  const group = model.q/model.kv;
  const eligibility = model.h === 128 && group === 4 ? 'Its shape matches this AMX kernel; runtime and page eligibility still apply.' : `Its ${group} × ${model.h} group fails this build’s AMX shape check.`;
  byId('work-status').textContent = `${model.name}: ${model.full} full layers and ${model.window} window layers. ${eligibility} These counts cover all attention before dividing work between CPU and FPGA.`;
  byId('work-lab').dataset.pairs = String(pairs);
  byId('work-lab').dataset.operations = String(operations);
  byId('work-lab').dataset.bytes = String(bytes);
}

function updatePages() {
  const offset = Number(byId('page-offset').value);
  byId('offset-value').textContent = `${offset} ${offset === 1 ? 'token' : 'tokens'}`;
  const width = Math.max(270, byId('page-chart').clientWidth);
  const left = 8;
  const usable = width - 16;
  const scale = usable / 192;
  let svg = svgStart(width, 184, `A 128-token window starts ${offset} tokens into a 64-token page. ${offset === 0 ? 128 : 64} keys occupy full-page candidates.`);
  let candidate = 0;
  let partial = 0;
  for (let index = 0; index < 3; index++) {
    const pageStart = index*64;
    const begin = Math.max(pageStart, offset);
    const end = Math.min(pageStart+64, offset+128);
    const count = Math.max(0, end-begin);
    const dense = count === 64;
    if (dense) candidate += count; else partial += count;
    const x = left+pageStart*scale;
    svg += `<text x="${x+32*scale}" y="22" text-anchor="middle" font-size="12">Page ${index+1}</text>`;
    svg += `<rect x="${x}" y="39" width="${64*scale}" height="39" fill="#fff" stroke="#81929b" stroke-dasharray="4 3"/>`;
    if (count) svg += `<rect x="${left+begin*scale}" y="39" width="${count*scale}" height="39" fill="${dense ? '#007c67' : '#b94c00'}"/>`;
    svg += `<text x="${x+32*scale}" y="104" text-anchor="middle" font-size="12" font-weight="650">${count} ${count === 1 ? 'key' : 'keys'}</text>`;
    svg += `<text x="${x+32*scale}" y="124" text-anchor="middle" font-size="11" fill="#526774">${dense ? 'full candidate' : count ? 'partial page' : 'outside window'}</text>`;
  }
  svg += `<path d="M${left+offset*scale} 143 v8 H${left+(offset+128)*scale} v-8" fill="none" stroke="#172e3b" stroke-width="1.5"/>`;
  svg += `<text x="${left+(offset+64)*scale}" y="178" text-anchor="middle" font-size="12">128-token visible window</text>` + svgEnd;
  byId('page-chart').innerHTML = svg;
  byId('page-chart').dataset.candidate = String(candidate);
  byId('page-summary').textContent = `${candidate} of 128 keys (${fmt(candidate/128*100,0)}%) are full-page candidates. The other ${partial} keys need partial-page handling. Current GPT-OSS AMX execution: 0 keys, because the head shape is unsupported.`;
}

function updateLanes() {
  const cpu = numberInput('lane-cpu');
  const fpga = numberInput('lane-fpga');
  const merge = numberInput('lane-merge');
  const speed = numberInput('lane-speed');
  if ([cpu,fpga,merge,speed].some(value => value === null)) {
    byId('lane-chart').innerHTML = '';
    byId('lane-status').textContent = 'Enter valid nonnegative durations and a CPU speedup of at least 1×. Producer work must be greater than 0 µs.';
    return;
  }
  const before = Math.max(cpu, fpga)+merge;
  const after = Math.max(cpu/speed, fpga)+merge;
  const width = 860;
  const left = 145;
  const plot = 665;
  const scale = plot/before;
  const x = time => left + time*scale;
  let svg = svgStart(width, 407, `Assumed attention schedule. Before: ${fmt(before,2)} microseconds. After: ${fmt(after,2)} microseconds. Saved: ${fmt(before-after,2)} microseconds. All durations share one scale.`);
  for (let tick = 0; tick <= 4; tick++) {
    const t = before*tick/4;
    svg += `<line x1="${x(t)}" x2="${x(t)}" y1="35" y2="371" stroke="#dce4e8"/><text x="${x(t)}" y="21" text-anchor="middle" font-size="12" fill="#526774">${fmt(t,1)} µs</text>`;
  }
  const block = (start, end, y, color, title, waiting = false) => {
    if (end <= start) return '';
    return `<rect x="${x(start)}" y="${y}" width="${(end-start)*scale}" height="23" ${waiting ? 'fill="#fff" stroke="#81929b" stroke-dasharray="4 3"' : `fill="${color}"`}><title>${title}: ${fmt(end-start,2)} µs est.</title></rect>`;
  };
  const drawScenario = (top, name, cpuTime, completion) => {
    const gate = Math.max(cpuTime, fpga);
    const critical = cpuTime >= fpga ? 'CPU' : 'FPGA';
    let row = `<text x="0" y="${top}" font-size="13" font-weight="750">${name} · ${fmt(completion,1)} µs est.</text>`;
    const cpuY=top+13, fpgaY=top+51, mergeY=top+89;
    row += `<text x="0" y="${cpuY+16}" font-size="12">CPU · ${fmt(cpuTime,1)} µs</text><text x="0" y="${fpgaY+16}" font-size="12">FPGA · ${fmt(fpga,1)} µs</text><text x="0" y="${mergeY+16}" font-size="12">Merge · ${fmt(merge,1)} µs</text>`;
    row += block(0,cpuTime,cpuY,critical==='CPU'?'#b32f3f':'#0072b2','CPU work');
    row += block(cpuTime,completion,cpuY,'','CPU waits or idles',true);
    row += block(0,fpga,fpgaY,critical==='FPGA'?'#b32f3f':'#007c67','FPGA work');
    row += block(fpga,completion,fpgaY,'','FPGA idle',true);
    row += block(0,gate,mergeY,'','Merge waits for inputs',true);
    row += block(gate,completion,mergeY,'#b32f3f','Serial merge');
    row += `<text x="${left}" y="${mergeY+42}" font-size="12" fill="#b32f3f">Critical path: ${critical} ${fmt(gate,1)} µs + merge ${fmt(merge,1)} µs = ${fmt(completion,1)} µs est.</text>`;
    return row;
  };
  svg += drawScenario(50, 'Before', cpu, before);
  svg += drawScenario(226, 'After', cpu/speed, after);
  svg += svgEnd;
  byId('lane-chart').innerHTML = svg;
  byId('lane-chart').dataset.before = String(before);
  byId('lane-chart').dataset.after = String(after);
  const saved = before-after;
  const hidden = cpu-cpu/speed-saved;
  byId('lane-status').textContent = `CPU service falls by ${fmt(cpu-cpu/speed,1)} µs est. Completion advances by ${fmt(saved,1)} µs est. (${fmt(saved/before*100,1)}%). ${saved === 0 ? 'The FPGA still determines when the merge can begin.' : `The other ${fmt(hidden,1)} µs of CPU savings overlap the remaining FPGA work.`}`;
}

let reductionRange = null;
function restoreGain() {
  byId('gain-budget').value = facts.nonjoinMs.toFixed(12);
  byId('gain-coverage').value = String(facts.denseFraction*100);
  byId('gain-reduction').value = '';
  byId('gain-exposure').value = '';
  byId('gain-overhead').value = '0';
  byId('gain-baseline').value = facts.forwardMs.toFixed(12);
  reductionRange = null;
}
function updateGain() {
  const C = numberInput('gain-budget');
  const coverage = numberInput('gain-coverage');
  const reduction = numberInput('gain-reduction');
  const exposure = numberInput('gain-exposure');
  const H = numberInput('gain-overhead');
  const T = numberInput('gain-baseline');
  const outputs = ['gain-saved','gain-percent','gain-throughput'];
  if ([C,coverage,reduction,exposure,H,T].some(value => value === null)) {
    byId(outputs[0]).textContent = 'Insufficient data';
    byId(outputs[1]).textContent = '—';
    byId(outputs[2]).textContent = '—';
    byId('gain-status').textContent = 'Supply the eligible service reduction and the share of savings exposed in elapsed time. Values outside their limits cannot produce an estimate. The initial coverage and zero added overhead are assumptions.';
    delete byId('gain-status').dataset.saved;
    return;
  }
  const reductions = reductionRange || [reduction];
  const savings = reductions.map(r => C*(coverage/100)*(r/100)*(exposure/100)-H/1000);
  if (savings.some(saved => T-saved <= 0)) {
    byId(outputs[0]).textContent = 'Invalid assumptions';
    byId(outputs[1]).textContent = '—';
    byId(outputs[2]).textContent = '—';
    byId('gain-status').textContent = 'The inputs remove the entire forward time or more. The service budget and overlap assumptions are inconsistent with this baseline.';
    delete byId('gain-status').dataset.saved;
    return;
  }
  const displayRange = (values, digits) => values.length === 1 ? fmt(values[0],digits) : `${fmt(values[0],digits)}–${fmt(values[1],digits)}`;
  byId('gain-saved').textContent = displayRange(savings,3);
  byId('gain-percent').textContent = displayRange(savings.map(saved => saved/T*100),2);
  byId('gain-throughput').textContent = displayRange(savings.map(saved => (T/(T-saved)-1)*100),2);
  const scenario = reductionRange ? 'The 12–16% reduction is a transferred assumption. ' : '';
  const slow = savings.every(saved => saved < 0) ? 'The added overhead makes the estimated forward slower. ' : '';
  byId('gain-status').textContent = `${scenario}${slow}Conditional est.: ${fmt(C,6)} ms service × ${fmt(coverage,5)}% eligible time × ${displayRange(reductions,1)}% reduction × ${fmt(exposure,1)}% exposure − ${fmt(H,2)} µs overhead. This is not a measurement of a new GPT-OSS kernel.`;
  byId('gain-status').dataset.saved = JSON.stringify(savings);
}

['model-select','query-count','visible-keys'].forEach(id => byId(id).addEventListener('input',updateWork));
byId('page-offset').addEventListener('input', updatePages);
['lane-cpu','lane-fpga','lane-merge','lane-speed'].forEach(id => byId(id).addEventListener('input',updateLanes));
byId('device-last').addEventListener('click', () => {byId('lane-cpu').value='30';byId('lane-fpga').value='90';byId('lane-merge').value='6';byId('lane-speed').value='2';updateLanes();});
byId('cpu-last').addEventListener('click', () => {byId('lane-cpu').value='90';byId('lane-fpga').value='30';byId('lane-merge').value='6';byId('lane-speed').value='2';updateLanes();});
['gain-budget','gain-coverage','gain-reduction','gain-exposure','gain-overhead','gain-baseline'].forEach(id => byId(id).addEventListener('input', () => {reductionRange=null;updateGain();}));
byId('gain-reset').addEventListener('click', () => {restoreGain();updateGain();});
byId('gain-twofold').addEventListener('click', () => {restoreGain();byId('gain-reduction').value='50';byId('gain-exposure').value='100';updateGain();});
byId('gain-proxy').addEventListener('click', () => {restoreGain();byId('gain-reduction').value='12';byId('gain-exposure').value='100';reductionRange=[12,16];updateGain();});
window.addEventListener('resize', () => {updateWork();updatePages();});
updateWork();
updatePages();
updateLanes();
updateGain();
