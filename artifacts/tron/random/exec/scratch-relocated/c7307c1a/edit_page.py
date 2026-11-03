import sys
p = '/home/jhan/workspace/random/from-claude/TRON-multiuser-attention-claude.html'
t = open(p, encoding='utf-8').read()
SLIDES = 'https://drive.google.com/file/d/1Ko2_5VUn9z-SGfhBcCCZYZIDDJKpjAIo/view?usp=sharing'
R = []  # (old, new) exact replacements, each old must occur exactly once

# 1. subtitle: slide link + update note
R.append((
 '''slides 32 to 34. Written by Claude Code on 2026-10-19 from the TRON source at commit <code>e6c53ba7</code> (branch main, 2026-09-23) in <code>~/workspace/tron</code>. Every file reference is relative to that clone.</p>''',
 f'''slides 32 to 34. The slide deck is on Google Drive at <a href="{SLIDES}">drive.google.com/file/d/1Ko2_5VUn9z-SGfhBcCCZYZIDDJKpjAIo</a>. Written by Claude Code on 2026-10-19 from the TRON source at commit <code>e6c53ba7</code> (branch main, 2026-09-23) in <code>~/workspace/tron</code>. Every file reference is relative to that clone. Updated 2026-10-21: slide link added, and section 4 (what a minibatch is) added.</p>'''))

# 2. TOC
R.append((
 '''<a href="#s4">4 Minibatch level</a>
<a href="#s5">5 FPGA path: shards across cards</a>
<a href="#s6">6 What is not done</a>
<a href="#s7">7 Insufficient data</a>''',
 '''<a href="#s4">4 What a minibatch is</a>
<a href="#s5">5 Minibatch level</a>
<a href="#s6">6 FPGA path: shards across cards</a>
<a href="#s7">7 What is not done</a>
<a href="#s8">8 Insufficient data</a>'''))

# 3. section 1: slide link sentence
R.append((
 '''"Attention: each request reads its own KV cache, alone." [slide 33 of the talk]</p>''',
 f'''"Attention: each request reads its own KV cache, alone." [slide 33 of the talk]. The deck is on Google Drive [<a href="{SLIDES}">drive.google.com/file/d/1Ko2_5VUn9z-SGfhBcCCZYZIDDJKpjAIo</a>].</p>'''))

# 4. renumber headings (highest first)
R.append(('<h2 id="s7">7. Insufficient data</h2>', '<h2 id="s8">8. Insufficient data</h2>'))
R.append(('<h2 id="s6">6. What TRON does not do, and what that costs</h2>', '<h2 id="s7">7. What TRON does not do, and what that costs</h2>'))
R.append(('<h2 id="s5">5. The FPGA path: shards spread across cards</h2>', '<h2 id="s6">6. The FPGA path: shards spread across cards</h2>'))

NEW_S4 = r'''<h2 id="s4">4. What a minibatch is</h2>
<p>A minibatch is a subset of the queries of one pass that moves through the model's layers as one unit. In the code it is one <code>struct batch</code> object, and the list of them is named <code>q_batches</code> for historical reasons [h/tron/models/common.hpp:956-962 and 991]. The design note warns that the word is "not to be confused with numerous other ways in which 'batching' is used in ML" [h/tron/models/common.hpp:938-939].</p>
<ul>
<li><b>Not Ben's batch.</b> The slides use "batch" for the set of requests served together. In TRON that set is the whole pass. A minibatch is a cut of that pass.</li>
<li><b>Not a request.</b> One minibatch can hold several users' queries. One long prompt can be cut across two minibatches.</li>
<li><b>Why it exists.</b> The FPGA runs the matmuls and the CPU runs attention. With two minibatches the FPGA can run the matmuls of one while the CPU runs the attention of the other [h/tron/models/common.hpp:930-942]. With one minibatch each side waits for the other.</li>
</ul>

<h3>How a pass is cut into minibatches</h3>
<ol class="steps">
<li><b>Label.</b> During the tree walk the scheduler gives every token of the pass a group label. A token whose parent is also computed in this pass inherits the parent's label. Any other token starts a new label [h/tron/scheduler/full.hpp:2387-2389 and 2471-2473]. In a decode pass each user's new token sits under a cached parent, so each user gets its own label. In a prefill pass one prompt chunk shares one label. The label is a cheap stand-in for "these tokens share KV pages" [h/tron/models/model.hpp:198-203].</li>
<li><b>Grains.</b> <code>chunk_evenly</code> collects the tokens by label and cuts each group into grains of at most 8 tokens. A grain is never split again [h/tron/models/model.hpp:217-230; h/tron/models/common.hpp:310-315]. One fix follows: the even and odd token offsets of one KV page must stay in the same minibatch, because the V write packs the pair into one SIMD value [h/tron/models/model.hpp:232-237].</li>
<li><b>Target count.</b> The target is the query count divided by the plugin's cap, rounded up. The cap is 128 queries in the hand-written llama plugin [h/tron/models/model.hpp:240; h/tron/plugins/llama.hpp:184]. A target of 1 is raised to 2 when the pass has more than one label or more than 8 tokens, "to enable FPGA-vs-CPU latency hiding" [h/tron/models/model.hpp:245-249]. The runtime flag <code>--max-minibatches</code> can cap the count, and its default of -1 means no cap [h/tron/models/config.hpp:62; src/runtron.cpp:1034]. Generated (ingested) plugins set a cap of 1 minibatch of up to 1,024 queries [ingest/src/TronCpp.hs:262-263].</li>
<li><b>Greedy merge.</b> Grains are visited in order. A grain joins the current chunk when the chunk stays under the cap and the new size is at least as close to the target size as the old size. Otherwise the grain starts the next chunk [h/tron/models/model.hpp:250-265]. If one chunk comes out and it holds more than 8 tokens, it is split in half [h/tron/models/model.hpp:267-276].</li>
<li><b>Objects.</b> <code>batch_evenly</code> turns each chunk into one <code>struct batch</code> whose <code>items</code> are the chunk's token jobs. Each creation is a "Create minibatch" trace event [h/tron/models/model.hpp:344-367].</li>
</ol>

<div class="fig" id="figM">
<div class="scroll"><svg id="svgM" width="1000" height="360" viewBox="0 0 1000 360" role="img" aria-label="Two passes cut into minibatches: four decode users, and one 20-token prompt"></svg></div>
<p class="take"><b>Takeaway:</b> four decode users become two minibatches of two users. One 20-token prompt becomes two minibatches of 8 and 12 tokens. The cut follows labels and grains, not users.</p>
<p class="cav">Computed with a Python mirror of <code>chunk_evenly</code> (same rules, without the even/odd pair fix), not observed in a TRON run. The fix changes nothing here if the prompt starts at an even page offset. Mirror: <code>TRON-multiuser-attention-chunk-mirror.py</code> next to this page.</p>
</div>

<h3>Worked examples, computed</h3>
<p>The table lists what the mirror of <code>chunk_evenly</code> returns for a few passes. The cap is 128 queries and the count is unlimited unless the row says otherwise. These are computed values, not measurements.</p>
<div class="tablewrap">
<table class="src">
<tr><th>Pass</th><th>Queries</th><th>Labels</th><th>Grains</th><th>Target count</th><th>Target size</th><th>Minibatch sizes</th></tr>
<tr><td>4 decode users</td><td class="c">4</td><td class="c">4</td><td class="c">1, 1, 1, 1</td><td class="c">2</td><td class="c">2</td><td class="c">2, 2</td></tr>
<tr><td>6 decode users</td><td class="c">6</td><td class="c">6</td><td class="c">6 × 1</td><td class="c">2</td><td class="c">3</td><td class="c">3, 3</td></tr>
<tr><td>1 decode user (one label, 8 tokens or fewer, so no split)</td><td class="c">1</td><td class="c">1</td><td class="c">1</td><td class="c">1</td><td class="c">1</td><td class="c">1</td></tr>
<tr><td>200 decode users</td><td class="c">200</td><td class="c">200</td><td class="c">200 × 1</td><td class="c">2</td><td class="c">100</td><td class="c">100, 100</td></tr>
<tr><td>300 decode users</td><td class="c">300</td><td class="c">300</td><td class="c">300 × 1</td><td class="c">3</td><td class="c">100</td><td class="c">100, 100, 100</td></tr>
<tr><td>1 prompt of 20 tokens</td><td class="c">20</td><td class="c">1</td><td class="c">8, 8, 4</td><td class="c">2</td><td class="c">10</td><td class="c">8, 12</td></tr>
<tr><td>1 prompt of 300 tokens</td><td class="c">300</td><td class="c">1</td><td class="c">37 × 8, 4</td><td class="c">3</td><td class="c">100</td><td class="c">104, 104, 92</td></tr>
<tr><td>1 prompt of 20 tokens + 3 decode users</td><td class="c">23</td><td class="c">4</td><td class="c">8, 8, 4, 1, 1, 1</td><td class="c">2</td><td class="c">12</td><td class="c">16, 7</td></tr>
<tr><td>4 decode users, generated plugin (count 1, cap 1,024)</td><td class="c">4</td><td class="c">4</td><td class="c">1, 1, 1, 1</td><td class="c">1</td><td class="c">4</td><td class="c">4</td></tr>
<tr><td>1 prompt of 300 tokens, generated plugin</td><td class="c">300</td><td class="c">1</td><td class="c">37 × 8, 4</td><td class="c">1</td><td class="c">300</td><td class="c">300</td></tr>
</table>
</div>
<p>Two rows show that the merge is greedy, not optimal. The 300-token prompt ends as 104, 104 and 92, because a grain joins while the new size is at least as close to the target as the old size, and 104 ties with 96 at a distance of 4. The prompt plus three users ends as 16 and 7, because the second grain of 8 ties with the first at a distance of 4 from the target of 12 and joins it [h/tron/models/model.hpp:259-262].</p>

<h3>What one minibatch holds</h3>
<div class="fig" id="figN">
<div class="scroll"><svg id="svgN" width="1000" height="345" viewBox="0 0 1000 345" role="img" aria-label="Fields of struct batch, the object behind one minibatch"></svg></div>
<p class="take"><b>Takeaway:</b> a minibatch is more than a list of queries. It carries its own layer counter, its own attention plans and FPGA passes, and the latches that let the main thread and the attention workers hand work to each other.</p>
</div>

<h3>How minibatches move through the layers</h3>
<ul>
<li>Each minibatch carries its own layer counter. The field comment gives the picture: "batch A can compute e.g. attention in layer 2 while batch B computes feed-forwards in layer 1" [h/tron/models/common.hpp:1083-1086].</li>
<li>The main thread's loop is layer-outer and minibatch-inner. For each layer it visits every minibatch in turn and launches that minibatch's output projection and feed-forward on the FPGA. The code calls this "alternating feed forwards of one q_batch with attention of the next" [h/tron/plugins/llama.hpp:650-659 and 86-95].</li>
<li>The attention workers loop over attention operations, then over minibatches, then over the tokens of the minibatch [h/tron/plugins/llama.hpp:56-67].</li>
<li>A query in one minibatch can need a K or V that a token in another minibatch writes in this pass, for example when a prompt is cut into two chunks. Three fields per minibatch track that: which minibatches to notify, how many K/V producers to wait for, and how many have finished [h/tron/models/common.hpp:964-989 and 1143-1154].</li>
<li>Each minibatch gets its own page list per layer profile and its own attention plan, as section 3 describes [h/tron/models/model.hpp:2340-2393; h/tron/models/common.hpp:1100-1128].</li>
</ul>

<h2 id="s5">5. Minibatch level: two groups of users take turns on the CPU and the FPGA</h2>'''
R.append(('<h2 id="s4">4. Minibatch level: two groups of users take turns on the CPU and the FPGA</h2>', NEW_S4))

# 5. old minibatch-level section: replace the first two bullets (now covered by section 4)
R.append((
 '''<li><code>chunk_evenly</code> groups the pass's queries by an affinity label. A user's new token under a node whose tokens are all cached starts a new label, so each decoding user gets its own label [h/tron/scheduler/full.hpp:2387-2389 and 2471-2473].</li>
<li>The target number of minibatches is the query count divided by 128, rounded up [h/tron/models/model.hpp:242; h/tron/plugins/llama.hpp:184]. When that gives 1 and there is more than one label, the target is raised to 2 "to enable FPGA-vs-CPU latency hiding" [h/tron/models/model.hpp:245-249]. Generated (ingested) plugins pin the count to 1 [ingest/src/TronCpp.hs:262].</li>
<li>So a hand-written llama-plugin pass with four decoding users runs two minibatches of two users each.''',
 '''<li>Section 4 shows the cut. Each decoding user gets its own label, and a pass of 2 to 128 such users is cut into two minibatches of near-equal size [h/tron/models/model.hpp:240-265]. Generated (ingested) plugins pin the count to 1 [ingest/src/TronCpp.hs:262].</li>
<li>So a hand-written llama-plugin pass with four decoding users runs two minibatches of two users each.'''))

# 6. Insufficient data: add the minibatch-size item
R.append((
 '''<li><b>Shared-prefix savings on the CPU path.</b>''',
 '''<li><b>Minibatch sizes in a real pass.</b> The worked examples in section 4 are computed from a mirror of <code>chunk_evenly</code>, not observed. Resolving measurement: the "Create minibatch" trace events of one pass in a Perfetto trace, one per minibatch [h/tron/models/model.hpp:362], read together with each minibatch's item count.</li>
<li><b>Shared-prefix savings on the CPU path.</b>'''))

# 7. Words used here: minibatch entry
R.append((
 '''<dt>minibatch</dt><dd>A subset of this pass's queries that moves through the layers together. Not a request and not a training batch.</dd>''',
 '''<dt>minibatch</dt><dd>A subset of this pass's queries that moves through the layers together. Not a request and not a training batch. Section 4 explains how it is built.</dd>
<dt>label, grain, chunk</dt><dd>The three stages of the cut in section 4. A label marks tokens that share KV pages. A grain is a run of up to 8 tokens of one label that is never split. A chunk is a merged run of grains that becomes one minibatch.</dd>'''))

# 8. Sources table
R.append((
 '''<td class="c">Bootcamp 2026-10, 103, Ben Gamari (Drive file 1Ko2_5VUn9z-SGfhBcCCZYZIDDJKpjAIo)</td>''',
 f'''<td class="c"><a href="{SLIDES}">drive.google.com/file/d/1Ko2_5VUn9z-SGfhBcCCZYZIDDJKpjAIo</a> (Bootcamp 2026-10, 103, Ben Gamari)</td>'''))
R.append((
 '''<tr><td>Minibatch grouping, 128-query cap, split of a lone chunk in two.</td><td class="c">h/tron/models/model.hpp:209-249; h/tron/plugins/llama.hpp:184; h/tron/scheduler/full.hpp:2387-2389, 2471-2473; ingest/src/TronCpp.hs:262</td></tr>
<tr><td>Note Mini-batching: FPGA matmuls overlap CPU attention.</td><td class="c">h/tron/models/common.hpp:928-960</td></tr>''',
 '''<tr><td>chunk_evenly header comment: group kinds, minimize splits, labels as a stand-in for KV affinity.</td><td class="c">h/tron/models/model.hpp:190-203</td></tr>
<tr><td>chunk_evenly: labels to groups, grains of 8, even/odd pair fix, target count, greedy merge, lone-chunk split.</td><td class="c">h/tron/models/model.hpp:209-276; h/tron/plugins/llama.hpp:183-184; h/tron/scheduler/full.hpp:2387-2389, 2471-2473; ingest/src/TronCpp.hs:262-263</td></tr>
<tr><td>batch_evenly: one struct batch per chunk, "Create minibatch" trace event.</td><td class="c">h/tron/models/model.hpp:344-367</td></tr>
<tr><td>Minibatch count flag --max-minibatches, default -1 (no cap).</td><td class="c">h/tron/models/config.hpp:62, 102-109; src/runtron.cpp:1034</td></tr>
<tr><td>Note Mini-batching: definition, why (FPGA matmuls overlap CPU attention), grouping start, struct batch, the name q_batches.</td><td class="c">h/tron/models/common.hpp:928-962</td></tr>
<tr><td>struct batch fields: items, layer counter, attention plans, FPGA plan, latches, dependency counters, plugin_batch.</td><td class="c">h/tron/models/common.hpp:991-1163</td></tr>
<tr><td>Note Minibatch Dependency Tracking: cross-minibatch K/V dependencies.</td><td class="c">h/tron/models/common.hpp:964-989</td></tr>
<tr><td>llama plugin pseudo-code (attention workers: operation, minibatch, token) and the main loop (layer, minibatch).</td><td class="c">h/tron/plugins/llama.hpp:47-96, 650-659</td></tr>
<tr><td>Python mirror of chunk_evenly that computed the worked-example table.</td><td class="c">~/workspace/random/from-claude/TRON-multiuser-attention-chunk-mirror.py</td></tr>'''))

# 9. JS: figures M and N, inserted before figure D
FIGS = r'''/* ---------- Figure M: how chunk_evenly cuts a pass ---------- */
(function(){
const s=document.getElementById('svgM');defs(s);
const cols=[[20,'1. tokens of the pass'],[250,'2. groups by label'],[480,'3. grains (8 tokens or fewer)'],[720,'4. greedy merge into minibatches']];
cols.forEach(([x,t])=>txt(s,x,22,t,'ttl'));
txt(s,20,44,'lane 1: decode pass, 4 users, 1 new token each','lbl2');
const U=['A','B','C','D'];
U.forEach((u,i)=>{const y=54+i*30;box(s,20,y,90,24,C[u],STROKE[u],'q_'+u);box(s,250,y,130,24,C[u],STROKE[u],'label '+i+': q_'+u);box(s,480,y,130,24,C[u],STROKE[u],'grain: q_'+u+' (1)');});
arrow(s,114,111,246,111);arrow(s,384,111,476,111);arrow(s,614,111,716,111);
box(s,720,66,250,38,'#f0efec','#898781',null);txt(s,845,82,'MB0: q_A q_B','lbl','middle');txt(s,845,97,'2 queries','lbl2','middle');
box(s,720,118,250,38,'#f0efec','#898781',null);txt(s,845,134,'MB1: q_C q_D','lbl','middle');txt(s,845,149,'2 queries','lbl2','middle');
txt(s,20,188,'lane 1: target count = max(ceil(4 / 128), 2) = 2 and target size = 2, so q_A and q_B fill MB0, and q_C and q_D fill MB1.','lbl2');
el(s,'line',{x1:20,y1:200,x2:980,y2:200,stroke:'#e1e0d9'});
txt(s,20,218,'lane 2: prefill pass, one prompt P of 20 tokens','lbl2');
box(s,20,228,200,24,C.S,STROKE.S,'P: tokens 0..19 (20)');
box(s,250,228,130,24,C.S,STROKE.S,'label 0: P (20)');
[['0..7',8],['8..15',8],['16..19',4]].forEach(([r,n],i)=>box(s,480,228+i*30,130,24,C.S,STROKE.S,'P'+r+' ('+n+')'));
arrow(s,224,240,246,240);arrow(s,384,240,476,240);arrow(s,614,258,716,258);
box(s,720,228,250,24,'#f0efec','#898781','MB0: P0..7 (8)');
box(s,720,258,250,24,'#f0efec','#898781','MB1: P8..15 + P16..19 (12)');
txt(s,20,330,'lane 2: target count = 2 (one label, more than 8 tokens) and target size = 10. 8 + 8 = 16 is farther from 10 than 8 is, so the second grain starts MB1.','lbl2');
txt(s,20,346,'The grain of 4 then joins MB1: 12 is as close to 10 as 8 is, and a tie joins [model.hpp:259-262].','lbl2');
})();

/* ---------- Figure N: what one minibatch holds ---------- */
(function(){
const s=document.getElementById('svgN');defs(s);
box(s,20,150,200,44,'#f0efec','#898781',null);txt(s,120,168,'struct batch','ttl','middle');txt(s,120,184,'one minibatch [common.hpp:991]','lbl2','middle');
const rows=[
 ['items[], items_mask','the token jobs of this minibatch, and the same set as mask bits [common.hpp:1076-1081]'],
 ['_layer','the layer this minibatch is on, advanced one layer at a time [common.hpp:1083-1086]'],
 ['plans[profile]','one attention plan per layer profile: page runs per worker, work estimate, join masks [common.hpp:1100-1128]'],
 ['hw_plan, attn_launchers','the FPGA attention passes of this minibatch and their launchers [common.hpp:1088-1093]'],
 ['downstream_minibatches, kvs_needed, upstream_kvs_ready','cross-minibatch K/V dependency counters [common.hpp:1143-1154]'],
 ['attn_done_barrier, layer_done, free_scratchpads_barrier','latches between the main thread and the attention workers [common.hpp:1130-1135, 1156-1157]'],
 ['id, ix','Perfetto flow id, and the index into per-minibatch arrays [common.hpp:1137-1141]'],
 ['plugin_batch','model-specific state: the Q, K, V and FFN channels of the llama plugin [common.hpp:1159-1162]']];
rows.forEach(([n,d],i)=>{const y=12+i*41;el(s,'line',{x1:220,y1:172,x2:300,y2:y+17,stroke:'#c3c2b7'});box(s,300,y,680,34,'#fff','#c3c2b7',null);txt(s,308,y+14,n,'mono');txt(s,308,y+28,d,'lbl2');});
})();

/* ---------- Figure D: schematic lanes ---------- */'''
R.append(('/* ---------- Figure D: schematic lanes ---------- */', FIGS))

for old, new in R:
    n = t.count(old)
    if n != 1:
        print('FAIL: count', n, 'for:', old[:90].replace('\n', ' | '))
        sys.exit(1)
    t = t.replace(old, new)
open(p, 'w', encoding='utf-8').write(t)
print('ok, replacements:', len(R), 'bytes:', len(t.encode()))
