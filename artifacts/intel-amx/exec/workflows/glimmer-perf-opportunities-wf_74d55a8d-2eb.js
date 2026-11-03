export const meta = {
  name: 'glimmer-perf-opportunities',
  description: 'Find decode/prefill speed opportunities in the kv_mul-16 AMX attention path that the minimal-change rule left out, refute them, and rank the survivors',
  phases: [
    { title: 'Read', detail: 'five readers, each one lens' },
    { title: 'Refute', detail: 'two skeptics per candidate' },
    { title: 'Synthesize', detail: 'ranked list with code sketches and measurements' },
  ],
}
const WT = '/home/jhan/workspace/ai-runs/tron-glimmer-amx'
const CTX = `
Context (read before anything else). Branch jhan-amx-kvmul16 (worktree ${WT}, head 5061623a34, base main 6198824246)
made the AMX software-attention kernels serve kv_mul 16 (Muse Glimmer 30B: 32 query heads over 2 KV heads, head 128,
52 layers of which 39 are sliding-window layers (window 2048) always on CPU software attention and 13 full layers on
the FPGA by default). The change was done under a MINIMAL-CODE-CHANGE rule: the three kernels
(pack_q_group_128x4, qk_rowmajor_128x4, weights_times_v_128x4 in ${WT}/src/tron/kernels/amx_attn.cpp, interface
${WT}/h/tron/kernels/amx_attn_iface.hpp) became templates on group_heads (4 or 16); the QK transposing store got
store_transposed_rows<lane> for lanes 0..3; the call sites in ${WT}/h/tron/models/self_attention.hpp pass kv_mul.
Nothing else changed: page walk, dense-page predicate, Q packing per token, s_pages layout, the AVX fallback, the
worker/join scheme, the FPGA split, buffer sizes.
Measured (delphi-3bda, 8 users, 2026-10-16/17, results in
/home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/attn-stats-compare.md and the page
/home/jhan/workspace/intel-AMX/muse-glimmer/muse-glimmer-amx-results.html): decode TPS per user AMX off->on
tp2 p1024 fpga 38.42->41.89 (+9.0 %), tp2 p2048 fpga +15.2 %, tp4 p1024 fpga 60.44->63.08 (+4.4 %), tp4 p2048 fpga +10.2 %;
with all 52 layers on CPU +13.4/+21.2/+6.1/+13.7 %. Attention counters: AMX scores 72.1 % of decode K tokens (fpga
config, p1024), AVX tail 2.9 %, FPGA 24.9 %; per decode forward the attention busy time (all workers) dropped from
27.06 s to 15.99 s over 256 forwards (tp2 p1024 fpga), join wait share rose from 9.5 % to 25.3 %; T1 forward wall
25.86 -> 23.70 ms per forward (so attention is not the whole step). Prompt forwards: busy 51.1 -> 43.1 s over 8
forwards (tp2 p1024 fpga), join wait share 16 % -> 44 %.
The question from the user (jhan): "Your code change was under one requirement of minimum code changes, were there any
perf boost opportunities lost because of the requirement? Namespace naming or coding style improvement are still not
considered." Only changes that can make Glimmer decode or prefill measurably faster count. Candidates must be
concrete: which code, what change, why it is faster, how much (estimate with units, labelled est.), and the
measurement that would confirm it (runtron cell + counters). Plain English, define every term at first use.
`
const SCHEMA = { type: 'object', properties: { candidates: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, title: { type: 'string' }, where: { type: 'string' }, change: { type: 'string' },
  why_faster: { type: 'string' }, est_gain: { type: 'string' }, risk: { type: 'string' }, measurement: { type: 'string' },
  evidence: { type: 'string' } }, required: ['id','title','where','change','why_faster','est_gain','risk','measurement','evidence'] } } }, required: ['candidates'] }
const LENSES = [
  { key: 'qk', prompt: `Lens: the 16-head QK kernel and its transposing store. Read ${WT}/src/tron/kernels/amx_attn.cpp fully (store_transposed_rows, qk_rowmajor_128x4, the tile configuration in begin_region, the P scratch) and the Note [QK orientation] in the interface header. With 16 heads the C tile (16 tokens x 16 heads) is full, and the store transposes it into s[head][token] with 4 lanes of shuffles (40 vshuf per page, object compare r2-16 in /home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/local-obj-compare/). Questions: could the transpose be avoided (compute Q x K^T with Q as the A operand, or change the s layout that the softmax/PV consumers read), could the pack of Q be done once per group instead of per token, is the tile config (palette rows/cols) optimal for 16 heads, are there dead tile loads/stores for the 4-row case that the 16-row case no longer needs? Give candidates with evidence (line numbers).` },
  { key: 'pv', prompt: `Lens: the PV kernel (weights_times_v_128x4), the softmax between QK and PV, and the P scratch (thread_local P[16][64]) for 16 heads. Read ${WT}/src/tron/kernels/amx_attn.cpp and the PV call site in ${WT}/h/tron/models/self_attention.hpp (search weights_times_v_128x4, amx_o, s_pages). Questions: with 16 heads the P tile is full, is the bf16 conversion of P vectorised for 16 rows, does amx_o (16x128 floats) get accumulated per page with extra passes that could fuse, is the per-page softmax scaling done 16x on the same K page, is the V plane read once per group? Give candidates with evidence (line numbers).` },
  { key: 'dispatch', prompt: `Lens: the page walk and the dispatch decision around the AMX fast path in ${WT}/h/tron/models/self_attention.hpp (search amx, is_dense, dense page, pack_q_group_128x4, s_pages, range hint, sliding window, window). Glimmer's 39 sliding-window layers (window 2048) see pages at the window edge that are partially masked. Questions: which pages fall to the AVX loop (the counters say 2.9 % of K tokens, 381,472 AVX visits vs 2,766,816 AMX visits in a decode run), could the dense predicate accept more pages (e.g. the tail page with a range hint), is Q packed once per (token, kv head) or once per token across KV heads, are there per-page costs (tile config, buffer clears, bounds checks) that scale with the number of pages and could be hoisted per job? Read /home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/attn-stats-compare.md sections 2 and 4 for the visit counts. Give candidates with evidence (line numbers).` },
  { key: 'parallel', prompt: `Lens: worker parallelism and the join. Read /home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/attn-stats-compare.md section 7 (busy time, join wait share 25-32 % in decode with AMX on vs 9-13 % off; prompt forwards 44-62 %) and the attention worker scheme in ${WT}/h/tron/models/self_attention.hpp (Note [Attention join parallelism scheme], Note [Computing self-attention], Note [Ready versus pending attention work]) and the memory note /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/attn-worker-lane-facts.md. Glimmer has 2 KV heads: per layer and user there are only 2 attention jobs (one per KV head, each 16 query heads). With 8 users that is 16 jobs per layer for the attention workers. Questions: is the job granularity (one KV head x all 16 query heads) now too coarse so workers idle (the rising join wait share), could a job be split by query-head halves or by page ranges, what does the worker count look like (count workers in the stats), and what does the forward wall T1 vs attention busy say about the share attention still has? Give candidates with evidence; quantify with the counters.` },
  { key: 'prefill', prompt: `Lens: prefill (prompt forwards) on the AMX path. Read the prompt-chunk handling in ${WT}/h/tron/models/self_attention.hpp (search chunk, prompt, pending, 128) and /home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/attn-stats-compare.md sections 4 and 7 plus section 4a of /home/jhan/workspace/intel-AMX/muse-glimmer/muse-glimmer-amx-results.html (the 1600-token KV book and the moved shard at prompt 2048). Prompts are processed in 128-token chunks; each query token of a chunk is scored against the KV pages. Questions: in prefill does the AMX path pack Q per query token and re-walk all pages per token (quadratic page visits), could the kernel score 16 query tokens of one head at once (the tile rows are tokens then, not heads) for the sliding-window layers, is there a prefill-specific kernel orientation that the 4-head design never needed but 16 heads make natural? Give candidates with evidence (line numbers) and the prefill time measurement (the 'Parsing the prompt took' lines).` },
]
phase('Read')
const read = await parallel(LENSES.map(l => () => agent(CTX + '\n' + l.prompt + '\nReturn candidates only; no preamble. Each candidate id = "' + l.key + '-N".', { label: 'read:' + l.key, phase: 'Read', schema: SCHEMA })))
const cands = read.filter(Boolean).flatMap(r => r.candidates)
log(`${cands.length} candidates from ${read.filter(Boolean).length} readers`)
const VERDICT = { type: 'object', properties: { id: { type: 'string' }, refuted: { type: 'boolean' }, reason: { type: 'string' }, corrected_est_gain: { type: 'string' }, effort: { type: 'string' } }, required: ['id','refuted','reason','corrected_est_gain','effort'] }
const verified = await pipeline(cands,
  c => parallel([0, 1].map(i => () => agent(CTX + `\nYou are skeptic ${i + 1} of 2. Try to REFUTE this candidate by reading the code it cites (${WT}) and the measurements. Refute if: the code already does it; the gain is below 1 % of a decode step or of prefill time; it changes numerics beyond bf16 rounding order; it needs the FPGA path or the KV layout to change (that is PR 4424 territory, out of scope); or the evidence is wrong. Default refuted=true when uncertain. Also state the implementation effort (lines, files, tests) and a corrected gain estimate with units (est.).\nCandidate: ${JSON.stringify(c)}`, { label: `refute:${c.id}:${i + 1}`, phase: 'Refute', schema: VERDICT })))
    .then(vs => ({ c, votes: vs.filter(Boolean) })))
const survivors = verified.filter(Boolean).filter(v => v.votes.length && v.votes.every(x => !x.refuted))
const dead = verified.filter(Boolean).filter(v => !(v.votes.length && v.votes.every(x => !x.refuted)))
log(`${survivors.length} survive, ${dead.length} refuted`)
phase('Synthesize')
const synth = await agent(CTX + `\nSynthesize. Surviving candidates with their skeptic votes:\n${JSON.stringify(survivors, null, 1)}\n\nRefuted candidates (list them in one table with the refutation reason, so the user sees what was considered):\n${JSON.stringify(dead.map(d => ({ id: d.c.id, title: d.c.title, reasons: d.votes.map(v => v.reason) })), null, 1)}\n\nWrite a plain-English report (Short version of at most 3 sentences first, then Words used here, then one section per surviving candidate ranked by expected decode gain on the production configuration (FPGA full layers, tp4, 8 users): what to change (file:line), why faster, est. gain with units, numerics risk, the test to add, the runtron measurement; then the refuted table; then a recommendation of which 1-3 candidates to implement first on a branch stacked on jhan-amx-kvmul16, with the order). One claim per sentence. No idioms.`, { label: 'synthesize', phase: 'Synthesize' })
return { report: synth, survivors: survivors.length, refuted: dead.length }