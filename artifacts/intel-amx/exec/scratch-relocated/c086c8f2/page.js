
'use strict';
const $ = id => document.getElementById(id);
const state = {end:11,size:4,window:6,page:4,query:11};
const physicalIds = [7,2,9,4,12];
let timer = null;
function lower(q) { return state.window ? Math.max(0,q-state.window+1) : 0; }
function getData() {
  const first = state.end-state.size+1;
  const lo = lower(state.query), unionLo = lower(first);
  const selectedPages = Array.from({length:Math.floor(state.query/state.page)-Math.floor(lo/state.page)+1},(_,i)=>i+Math.floor(lo/state.page));
  const unionPages = Array.from({length:Math.floor(state.end/state.page)-Math.floor(unionLo/state.page)+1},(_,i)=>i+Math.floor(unionLo/state.page));
  return {first,lo,unionLo,selectedPages,unionPages,visible:state.query-lo+1,unionCount:state.end-unionLo+1};
}
function range(a,b) { return a===b ? `position ${a}` : `positions ${a}–${b}`; }
function render() {
  state.end = Math.max(state.size-1,Math.min(19,state.end));
  const first = state.end-state.size+1;
  state.query = Math.max(first,Math.min(state.end,state.query));
  const d = getData();
  $('end').min=state.size-1; $('end').value=state.end;
  $('size').value=state.size; $('window').value=state.window; $('page-size').value=state.page;
  $('end-label').textContent=`Position ${state.end}`;
  $('end').setAttribute('aria-valuetext',`Last query position ${state.end}`);
  $('next').disabled=state.end+state.size>19;
  $('next').textContent=`Next minibatch (+${state.size} tokens) →`;
  $('live-summary').textContent=`${state.size} token ${state.size===1?'job':'jobs'} at ${range(first,state.end)}. Selected query: position ${state.query}. It may use ${range(d.lo,state.query)}.`;
  let html='<thead><tr><th scope="col">Query ↓ / K,V →</th>';
  for(let k=0;k<20;k++) html+=`<th scope="col">${k}</th>`;
  html+='</tr></thead><tbody>';
  for(let q=first;q<=state.end;q++) {
    html+=`<tr class="${q===state.query?'chosen':''}"><th scope="row"><button data-query="${q}" aria-pressed="${q===state.query}" aria-label="Select query at position ${q}">Q @ ${q}</button></th>`;
    for(let k=0;k<20;k++) {
      const allowed=k>=lower(q)&&k<=q;
      const label=allowed?'allowed':k>q?'future for this query':'outside window';
      html+=`<td class="${allowed?'allowed':k>q?'future':'masked'} ${k===q?'self':''} ${k%state.page===0?'page-start':''}" title="Query ${q}, K/V ${k}: ${label}" aria-label="Query ${q}, K/V ${k}: ${label}">${allowed?'●':k>q?'·':'×'}</td>`;
    }
    html+='</tr>';
  }
  html+='<tr class="union-row"><th scope="row">Group union</th>';
  for(let k=0;k<20;k++) html+=`<td class="${k>=d.unionLo&&k<=state.end?'in-union':''} ${k%state.page===0?'page-start':''}">${k>=d.unionLo&&k<=state.end?'■':'·'}</td>`;
  $('matrix').innerHTML=html+'</tr></tbody>';
  $('mask-note').textContent=`Purple inset marks each query’s own position. Orange vertical lines mark page boundaries. ${state.size>1?'A later position can already be computed in this group and still be masked for an earlier query.':'This group contains one query. Its range equals the group union.'}`;
  let pages='';
  for(let p=0;p<Math.ceil(20/state.page);p++) {
    const touched=d.unionPages.includes(p), selected=d.selectedPages.includes(p);
    pages+=`<div class="page-card ${touched?'union-page':''} ${selected?'query-page':''}" data-page="${p}"><div class="page-title"><span>Logical ${p}</span><span class="phys">physical #${physicalIds[p]}</span></div><div class="slots">`;
    for(let k=p*state.page;k<(p+1)*state.page;k++) {
      const visible=k>=d.lo&&k<=state.query;
      const union=k>=d.unionLo&&k<=state.end;
      const future=k>state.end;
      pages+=`<span class="slot ${visible?'visible':future?'future':union?'union-only':''}" title="K/V position ${k}: ${visible?'visible to selected query':future?'not yet processed':union?'needed by another query':'stored, not used by this group'}">${k}</span>`;
    }
    pages+=`</div><div class="page-foot">${touched?`<strong>${selected?'Selected query + group':'Other queries in group'}</strong>`:p*state.page>state.end?'Future allocation (placeholder)':'Retained in this mock'}<br>${p*state.page}–${(p+1)*state.page-1} · ${state.page} token slots</div></div>`;
  }
  $('pages').innerHTML=pages;
  const rows=[
    ['Current query jobs',`${state.size} tokens · ${range(first,state.end)}`],
    [`Visible to query ${state.query}`,`${d.visible} keys · ${range(d.lo,state.query)}`],
    ['Union across this minibatch',`${d.unionCount} keys · ${range(d.unionLo,state.end)}`],
    ['Pages with K/V eligible for query',`${d.selectedPages.length} pages · logical ${d.selectedPages.join(', ')}`],
    ['Pages with K/V eligible for group',`${d.unionPages.length} pages · logical ${d.unionPages.join(', ')}`],
    ['Capacity of group’s pages',`${d.unionPages.length*state.page} token slots · ${d.unionCount} needed by the group`]
  ];
  $('stats').innerHTML=rows.map(([a,b])=>`<tr><th scope="row">${a}</th><td>${b}</td></tr>`).join('');
  $('formula-detail').textContent=`For the selected query: ${state.window?`max(0, ${state.query} − ${state.window} + 1) = ${d.lo}`:'lower bound = 0'}. The upper bound is ${state.query}.`;
  $('lab-takeaway').innerHTML=`<strong>${d.visible} keys for query ${state.query}; ${d.unionCount} distinct keys for the group; ${d.unionPages.length} pages for storage.</strong> ${state.size>1?'The group union does not replace each query’s mask.':'The window moves with the query. Pages remain aligned to fixed token boundaries.'}`;
}
function stop() { if(timer)clearInterval(timer);timer=null;$('play').textContent='▶ Play minibatches';$('play').setAttribute('aria-pressed','false'); }
function advance() {
  if(state.end+state.size>19){stop();return;}
  state.end=state.end+state.size;state.query=state.end;render();
  if(state.end+state.size>19)stop();
}
function reset() {stop();Object.assign(state,{end:11,size:4,window:6,page:4,query:11});render();}
$('end').addEventListener('input',e=>{stop();state.end=+e.target.value;state.query=state.end;render();});
[['size','size'],['window','window'],['page-size','page']].forEach(([id,key])=>$(id).addEventListener('change',e=>{stop();state[key]=+e.target.value;render();}));
$('matrix').addEventListener('click',e=>{const b=e.target.closest('button[data-query]');if(b){stop();state.query=+b.dataset.query;render();$('matrix').querySelector(`[data-query="${state.query}"]`).focus({preventScroll:true});}});
$('next').addEventListener('click',()=>{stop();advance();});
$('reset').addEventListener('click',reset);
$('play').addEventListener('click',()=>{if(timer){stop();return;}if(state.end+state.size>19){state.end=state.size-1;state.query=state.end;render();}$('play').textContent='Ⅱ Pause minibatches';$('play').setAttribute('aria-pressed','true');timer=setInterval(advance,1600);});
document.querySelectorAll('[data-preset]').forEach(b=>b.addEventListener('click',()=>{reset();if(b.dataset.preset==='page')state.page=8;if(b.dataset.preset==='decode')state.size=1;render();$('lab').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}));
const phases=[
  {name:'Prepare jobs and masks',short:'Select work and sequence visibility.',title:'The scheduler prepares token jobs and their base visibility masks.',body:'This identifies the queries and their sequence context. Previously computed K/V can already exist in cache pages.'},
  {name:'Group jobs; plan pages',short:'Create minibatches and dependencies.',title:'The model groups token jobs and selects relevant pages.',body:'Each query keeps its own mask. The runtime distinguishes ready pages from pages waiting for new K/V.'},
  {name:'Form Q, K, and V',short:'Compute vectors at this layer.',title:'The layer forms Q, K, and V for the current tokens.',body:'Ready-page attention can start once Q is available. New K/V production may still be running. Each current token also contributes its own K/V.'},
  {name:'Write current K/V',short:'Populate the current cache slots.',title:'Current K/V is made available before dependent attention reads.',body:'Logical positions locate cache page slots. This diagram shows dependencies only. It leaves out most hardware operations.'},
  {name:'Finish attention',short:'Use pending pages; combine results.',title:'Pending-page attention waits for its required new K/V.',body:'It applies the per-query mask. Results from ready and pending pages are combined. Only allowed query–key pairs contribute.'},
  {name:'Continue the model',short:'Finish layers; choose next token.',title:'The remaining layer work and later layers complete.',body:'Repeat the layer computation through the model. At the generation boundary, output scores select the next token. Cached K/V can support later minibatches.'}
];
let phase=0, phaseTimer=null;
function renderPhases(){
  $('phases').innerHTML=phases.map((p,i)=>`<div class="phase ${i===phase?'active':''}" ${i===phase?'aria-current="step"':''}><span class="num">${i+1}</span><strong>${p.name}</strong><small>${p.short}</small></div>`).join('');
  $('step-caption').innerHTML=`<strong>${phases[phase].title}</strong>${phases[phase].body}`;
  $('phase-count').textContent=`Step ${phase+1} of ${phases.length}`;
  $('phase-next').disabled=phase===phases.length-1;
}
function stopPhases(){if(phaseTimer)clearInterval(phaseTimer);phaseTimer=null;$('phase-play').textContent='▶ Play steps';$('phase-play').setAttribute('aria-pressed','false');}
function advancePhase(){phase=Math.min(phases.length-1,phase+1);renderPhases();if(phase===phases.length-1)stopPhases();}
$('phase-play').addEventListener('click',()=>{if(phaseTimer){stopPhases();return;}if(phase===phases.length-1){phase=0;renderPhases();}$('phase-play').textContent='Ⅱ Pause steps';$('phase-play').setAttribute('aria-pressed','true');phaseTimer=setInterval(advancePhase,2300);});
$('phase-next').addEventListener('click',()=>{stopPhases();advancePhase();});
$('phase-reset').addEventListener('click',()=>{stopPhases();phase=0;renderPhases();});
document.addEventListener('visibilitychange',()=>{if(document.hidden){stop();stopPhases();}});
render();renderPhases();
