export const meta = {
  name: 'aof-amx-split-verify',
  description: 'Verify against tron source when the AMX path runs under FPGA attention (decode + prefill), refute every claim, synthesize cases',
  phases: [
    { title: 'Read', detail: '6 focused readers of the tron source, claims with file:line' },
    { title: 'Refute', detail: '2 refuters per claim (code-path lens, edge-case lens)' },
    { title: 'Synthesize', detail: 'cases table for the page' },
    { title: 'Critic', detail: 'completeness + contradiction check' },
  ],
}

const RO = '~/workspace/ai-runs/tron-counters-ro'
const ST = '~/workspace/ai-runs/tron-attn-stats'

const CTX = `
CONTEXT (read carefully; do not re-derive it).
Project: tron (Positron inference program). Two attention modes for the CPU-side work of one decode step:
 - CPU attention (USE_HW_ATTN=0): the CPU scores every cached key token. Per (query token, 64-token KV page, KV head) visit,
   apply_page_tok chooses the AMX dense-page kernel or the AVX dotter loop.
 - FPGA attention, also called AoF or HW attention (USE_HW_ATTN unset for qwen-3-4b): the card scores the HBM-resident prefix,
   the CPU scores the rest, and a join folds the two partials.
Source trees (read-only; never edit): ${RO} = tron main 0a51385e95 (the page's reference revision; cite this tree as file:line).
${ST} = branch jhan-attn-path-stats @ cbf1bb6c0c (main 66c7bb8db1 + the TRON_ATTN_STATS counters, PR #4596); use it only for counter names.
Known anchors in ${RO}: h/tron/models/self_attention.hpp:1601-1614 is_dense_amx_page (begin == 0 && end == page_size && query_visible && pg.at_offset(63) < range.tok_hi && sliding window), :1740-1860 apply_page_tok return sites (AMX / empty / AVX);
h/tron/models/model.hpp:2439-2670 construct_hw_plan (per query hw range = min(query_pos, last_token_pos); entries and queries below hw_attn_engagement_point() are skipped);
h/tron/scheduler/full.hpp:2740-2810 descent that computes dma_last_abs = base_tok_ix + complete_prefix_gofs * gof_tokens - 1 (first shard needs hwkv_min_gofs_for_offload complete GOFs; middle shards must be dma_complete; partial leaf shard pushed with its DMA progress);
h/tron/gof.hpp:34 gof_tokens = 4; src/tron/models/hw_attn_config.cpp (engagement point = hardware::MIN_TOK_IDX_FOR_HWATTN unless USE_HW_ATTN=N raises it); h/tron/shard.hpp (sw_fallback); src/tron/gof.cpp:73-79; src/rinzler.cpp:4271 (sw_fallback_total leaf).
The page under revision (counter.html, section 2) currently says: (a) under CPU attention at context N one decode query visits floor(N/64) full pages on AMX and N mod 64 tokens on AVX; (b) under FPGA attention the card scores the HBM-resident prefix up to the last complete GOF at plan time (est. 4-token lag), the CPU scores the remaining few tokens on AVX, no full CPU page exists, so AMX gets no work in steady-state decode; (c) positions below 127 are scored on the CPU only when the query itself is below 127; (d) Table 1 puts AMX = 0 in every FPGA-attention row (prefill "DMA keeps up" and decode "lag 4 tokens", both est.).
The user's impression to test: "at decode, when the latest KV page is partial, the attention operations are split between AVX and AMX; even with AoF enabled (USE_HW_ATTN=1) the AMX path is still used on some tokens' decode attention".
Measured evidence already in hand (do not re-measure; interpret): (1) 2026-09-24 TRON_ATTN_STATS exit reports, qwen-3-4b tp2, 8 users, prompt 1024, 256 tokens, CPU attention, AMX on: decode_like ready_amx_visits 10,278,144, pending_avx_visits 580,608, pending_amx_visits 6,912 (= 3 steps x 8 users x 36 layers x 8 KV heads: the steps where N mod 64 == 0), token_jobs_by_path_set {amx: 24, avx+amx: 2016}, fpga_queries 0; prompt_or_mixed: ready_amx 16,515,072, pending_avx 3,538,944, path sets {avx: 1024, avx+amx: 7168}. (2) 2026-09-17 perf EXE.AMX_BUSY on the rinzler engine pid, qwen-3-4b, ONE user, 3 decode-only requests after a warm-up with the same prompt (usage.cached_tokens = 910), about 131 generated tokens each: CPU attention + AMX 873,318,988 busy cycles; kill switch 0; FPGA attention (USE_HW_ATTN default) 501,350,140 busy cycles = 57 % of the CPU-attention count. Cause not established. (3) 2026-09-19 perf record of an FPGA-attention decode run (VNNI-K build): the dense AMX kernel symbol absent from the profile, apply_page_range present. (4) 2026-09-18/19 canonical-AMX deb whole-machine CI cells under FPGA attention: 10.5 G AMX-busy cycles in a 20 s probe with 4 short requests (prefill included), 0 on the no-AMX package.
Rules for your output: every claim is ONE sentence, cites file:line in ${RO} (or ${ST} for counter names), quotes the decisive code fragment in "evidence"; mark confidence; say "Insufficient data" when the code does not settle it and name what would. Do not speculate about hardware timing you cannot read from the code. Read the code with sed/grep (Bash) and Read; do not edit anything.`

const CLAIMS = {
  type: 'object',
  properties: {
    claims: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, text: { type: 'string' },
      cites: { type: 'array', items: { type: 'string' } },
      evidence: { type: 'string' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    }, required: ['id', 'text', 'cites', 'evidence', 'confidence'] } },
    insufficient: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['claims'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    correction: { type: 'string' },
    cites: { type: 'array', items: { type: 'string' } },
  },
  required: ['refuted', 'reason'],
}

const READERS = [
  { key: 'dense', q: `Question 1, the page-visit decision. In ${RO}/h/tron/models/self_attention.hpp read apply_page_tok (about :1700-1860), is_dense_amx_page (:1601-1614), apply_dense_amx_page (:1617-1700), and the callers that compute begin/end/query_visible/range (search for sw_required, query_visible, range_hint, apply_page_range, run_sections, pending). Establish with citations: (1) what begin and end are for a page whose token range is only partly required by the CPU (for example the page that contains the HW/SW boundary under FPGA attention), and why such a page cannot be dense; (2) what an "empty" visit is (the return site around :1820) and when a page fully owned by the card produces it; (3) whether uses_hw or the FPGA mode gates the AMX path anywhere, or whether AMX applies to any page the CPU is required to score (query_visible = sw_required); (4) the condition pg.at_offset(page_size-1) < range.tok_hi: for a decode query at position q, what tok_hi is, and therefore from which query position a given ready page becomes dense; (5) whether the pending page (written in this forward) can be dense when it is full (N mod 64 == 0) and what distinguishes the ready pass from the pending pass in run_sections. Also report: in the AVX dotter for a partial range, how many K tokens are scored (the range length, not the page).` },
  { key: 'plan', q: `Question 2, the HW plan per query. In ${RO}/h/tron/models/model.hpp read construct_hw_plan (:2439-2670), the hw_plan_entry / hw_query types, and in h/tron/models/self_attention.hpp prepare_uniform_hw_attention / prepare_hw_attention (:487-720) and the mask construction that splits HW and SW ranges (search for hw_plan, sw_required, items_mask, token_range, tok_lo, tok_hi). Establish with citations: (1) for one decode query at position p with an entry whose last_token_pos = L, exactly which key positions the card scores and which the CPU scores (inclusive/exclusive ends); (2) what happens to a query with position p < hw_attn_engagement_point(): does the CPU score all of 0..p; (3) for a query with p >= engagement point, are key positions 0..126 scored by the card (the page's sentence "positions below 127 are scored on the CPU only when the query itself is below 127" must be confirmed or corrected); (4) whether one query can have more than one SW range (for example a prefix-cache branch point) and how that affects density; (5) what hw_attn_engagement_point() returns by default and with USE_HW_ATTN=N (read src/tron/models/hw_attn_config.cpp and find the numeric value of hardware::MIN_TOK_IDX_FOR_HWATTN and POS_PER_PAGE in h/pos/).` },
  { key: 'dma', q: `Question 3, where the boundary L comes from. In ${RO}/h/tron/scheduler/full.hpp read the descent around :2650-2830 that builds hw_plan_entries (dma_last_abs, shard_stack, hwkv_min_gofs_for_offload, count_complete_prefix_gofs, dma_complete, shard_push_stopped), plus h/tron/shard.hpp and src/tron/shard.cpp (or wherever count_complete_prefix_gofs, dma_complete, base_tok_ix, sw_fallback live) and h/tron/gof.hpp. Establish with citations: (1) the value of hwkv_min_gofs_for_offload and what it implies for the first shard (how many resident tokens before the card engages); (2) the formula for the boundary when the leaf shard is partial (dma_last_abs) and its granularity (whole GOFs of gof_tokens = 4); (3) at what moment in the forward the boundary is captured relative to the K/V writes of the current step (is the newest token ever inside the HW range in the same step; what is the smallest possible lag in tokens between the query position and L in steady-state decode; state what the code guarantees and what depends on DMA timing); (4) what a shard with sw_fallback means for the plan (is the shard skipped so all its tokens become CPU work, for how long, where the "lose HW attention" / "HBM bypass space exhausted" warning is printed, and whether later requests sharing the tree node inherit it); (5) shards and prefix-cache tree nodes: is a shard owned by a tree node, and when a NEW request hits a cached prefix (tree nodes from an earlier request), does its plan reach the earlier request's shards (are they dma_complete already), or does the new request start with no HBM-resident prefix and DMA it again; read the code that allocates/attaches shards to nodes (search shard alloc, attach, tree node, hwkv) and answer or say Insufficient data with the exact function that decides.` },
  { key: 'gof', q: `Question 4, GOF population and DMA timing in decode. In ${RO} read src/tron/gof.cpp, h/tron/gof.hpp, h/tron/shard.hpp, the xfer_gof / populate / gof_rodeo / help_drain_gof / wait_coop_gof code (grep in h/tron/models/model.hpp and src/tron), and where DMA completion is polled (grep dma_complete, count_complete_prefix_gofs, poll). Establish with citations: (1) a GOF = gof_tokens consecutive tokens of one sequence whose K and V are complete; when a GOF becomes complete in decode (every 4th token per user); (2) the sequence populate (host staging gather) -> DMA (shard::xfer_gof) -> completion bookkeeping, and on which threads / at which point of the NEXT forward each runs; (3) therefore, at plan time of decode step with query position p, the tokens that can at best be resident (state the best-case lag in tokens as a formula of p mod 4 and the in-flight GOFs; if the code does not bound the in-flight count, say so and cite the polling point); (4) whether anything in the code forces the CPU range to be smaller than one 64-token page in steady state (answer is likely "no guarantee, only timing"; cite); (5) prefill: prompt tokens arrive 128 per user per forward (TRON_PER_USER_PROMPT_CHUNK_LIMIT, h/libtron.hpp about :196-204); when are chunk k's 32 GOFs populated and DMA'd relative to chunk k+1's plan; can chunk k's pages be dense CPU work (AMX) for chunk k+1's queries; cite the code that orders "populate the remainder on the forward thread before logits" and the DMA completion poll.` },
  { key: 'stats', q: `Question 5, what the new counters will show in an FPGA-attention run. In ${ST} (branch with TRON_ATTN_STATS) read h/tron/models/attn_stats.hpp (Note [Attention path stats]), README.stats.md, the hook sites in h/tron/models/self_attention.hpp (grep stats_on, visit_tally, ready_empty, pending_amx, fpga_queries, path_set, hw_wait, join_wait) and model.hpp (begin_forward/end_forward, decode_like / prompt_or_mixed classification, fpga queries from hw_plan.by_job). Establish with citations: (1) the exact names of every counter that distinguishes AMX / AVX / empty visits in the ready and pending passes, and the FPGA-side counters (fpga_queries, FPGA k tokens, T5 join wait); (2) how a token job's path set is classified, including the "fpga", "fpga+avx", "fpga+amx", "fpga+avx+amx" sets, so that an FPGA-attention run of qwen-3-4b (prompt 1024, 256 tokens, 8 users) prints values that directly answer "does AMX run under AoF in decode"; (3) how the forward is classified decode_like vs prompt_or_mixed (n_listeners == token_jobs.size()); (4) the exact stderr line format ("[attn-stats] ...") and the FUSE leaf paths, so a runbook can grep them; (5) any counter that would count the empty visits per decode step (to measure the DMA lag = avx_k_tokens per step in the ready pass) and whether a per-step DMA-lag histogram exists (probably not; say so).` },
  { key: 'prefill', q: `Question 6, prefill and the sub-127 region under FPGA attention, plus the sw_fallback path end to end. In ${RO} read h/libtron.hpp (:190-210 chunk limit), src/tron/context.cpp (:40-60 logits request), h/tron/scheduler/full.hpp (the descent :2650-2830 and the code that creates shards for new nodes, hwkv_min_gofs_for_offload), h/tron/models/model.hpp construct_hw_plan (:2439-2670, note [HW Attention and prompt queries]), src/rinzler.cpp around :4271 (sw_fallback_total), src/tron/gof.cpp:60-90. Establish with citations: (1) for a prompt of 1024 tokens fed 128 per forward, in forward k (k >= 2) which key pages of chunks 1..k-1 the card scores and which the CPU scores, in the two cases DMA complete / DMA not complete at plan time, and on which CPU path (dense page -> AMX, own-chunk triangle -> AVX); (2) the first forward (positions 0..127): all CPU, which path; (3) queries at positions 127..255 in forward 2: does the card score 0..127 or does the first shard need more resident tokens (hwkv_min_gofs_for_offload x 4) so that forward 2 is still all-CPU (then chunk 1's two pages are dense -> AMX); give the exact condition; (4) the sw_fallback path: what allocation fails, what the warning text is, whether the whole 1024-token shard stays CPU work for the life of the tree node, and what the CPU path for those 16 pages is (dense -> AMX if AMX is on); (5) a compact closed-form statement for one user: under FPGA attention with DMA keeping up, the CPU work per prefill forward k is the own-chunk causal triangle (AVX) plus nothing else; with a DMA lag of g GOFs, plus the lagging pages (dense -> AMX when a whole page lags).` },
]

const readOne = (r) => agent(`${CTX}\n\nYOUR TASK: ${r.q}\n\nReturn 6 to 15 claims (ids ${r.key}-1, ${r.key}-2, ...), each one sentence, each with file:line cites in ${RO} (or ${ST} for counter names) and a short quoted code fragment as evidence. List open points under "insufficient" with the measurement or code read that would settle each.`,
  { label: `read:${r.key}`, phase: 'Read', schema: CLAIMS, effort: 'high' })

const LENSES = [
  { name: 'code-path', hint: 'Follow the actual control flow and data values through the cited lines: check every arithmetic boundary (inclusive/exclusive ends, -1, page 64, GOF 4, engagement 127), every guard, every default. A claim is refuted if the cited code does not say what the claim says, or if the claim quietly generalizes from one call site to all.' },
  { name: 'edge-case', hint: 'Attack the claim with configurations and states it may not cover: multi-user batches, prefix-cache hits and branch points inside a page, sw_fallback shards, USE_HW_ATTN=N, the first 127 positions, N mod 64 == 0, the ready vs pending pass, ingested (generated) plugins vs handwritten llama.hpp, EAGLE, sliding-window layers. A claim is refuted if a realistic configuration in the code makes it false as stated; a claim that is true but needs a qualifier is NOT refuted: return refuted=false and put the qualifier in correction.' },
]

const refuteClaim = (c, readerKey) => parallel(LENSES.map(l => () =>
  agent(`${CTX}\n\nYou are an adversarial verifier with the ${l.name} lens. ${l.hint}\n\nCLAIM ${c.id}: "${c.text}"\nCITES: ${c.cites.join('; ')}\nREADER'S EVIDENCE: ${c.evidence}\n\nOpen the cited lines in ${RO} (or ${ST}) yourself and try to refute the claim. Default to refuted=true only if the cited code contradicts the claim or the claim cannot be supported by any code you can find in 10 minutes of reading; if the claim is right but imprecise, refuted=false with the precise wording in "correction". Give file:line cites for your reason.`,
    { label: `refute:${c.id}:${l.name}`, phase: 'Refute', schema: VERDICT, effort: 'high' })
)).then(vs => ({ claim: c, reader: readerKey, verdicts: vs.filter(Boolean).map((v, i) => ({ lens: LENSES[i].name, ...v })) }))

phase('Read')
const results = await pipeline(READERS,
  r => readOne(r),
  (res, r) => {
    if (!res || !res.claims) { log(`reader ${r.key} returned nothing`); return { reader: r.key, insufficient: [], judged: [] } }
    log(`reader ${r.key}: ${res.claims.length} claims, ${(res.insufficient || []).length} open points`)
    return parallel(res.claims.map(c => () => refuteClaim(c, r.key)))
      .then(judged => ({ reader: r.key, insufficient: res.insufficient || [], notes: res.notes || '', judged: judged.filter(Boolean) }))
  })

const all = results.filter(Boolean)
const kept = [], dropped = []
for (const r of all) for (const j of r.judged) {
  const refs = j.verdicts.filter(v => v.refuted)
  if (refs.length === 0) kept.push({ ...j.claim, reader: r.reader, corrections: j.verdicts.map(v => v.correction).filter(Boolean) })
  else dropped.push({ ...j.claim, reader: r.reader, refutations: refs.map(v => `${v.lens}: ${v.reason}${v.correction ? ' | correction: ' + v.correction : ''}`) })
}
const insufficient = all.flatMap(r => (r.insufficient || []).map(s => `${r.reader}: ${s}`))
log(`kept ${kept.length} claims, dropped ${dropped.length}, open points ${insufficient.length}`)

const CASES = {
  type: 'object',
  properties: {
    verdict_on_user_impression: { type: 'string' },
    steady_state_decode_aof: { type: 'string' },
    cases: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, phase: { type: 'string' }, when: { type: 'string' },
      cpu_scores: { type: 'string' }, amx_runs: { type: 'string' }, mechanism: { type: 'string' },
      cites: { type: 'array', items: { type: 'string' } },
      evidence_status: { type: 'string' }, measurement_that_settles: { type: 'string' },
    }, required: ['name', 'phase', 'when', 'cpu_scores', 'amx_runs', 'mechanism', 'cites', 'evidence_status'] } },
    table1_correction: { type: 'string' },
    interpretation_of_501M: { type: 'string' },
    fpga_run_expected_counters: { type: 'string' },
    contradictions_with_page: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict_on_user_impression', 'steady_state_decode_aof', 'cases', 'table1_correction', 'interpretation_of_501M', 'fpga_run_expected_counters', 'contradictions_with_page'],
}

phase('Synthesize')
const synth = await agent(`${CTX}\n\nYou are the synthesizer. Below are the claims that survived two adversarial refuters each (with optional corrections), the dropped claims with the refutation reasons, and the readers' open points. Build the answer for the page's new sub-sections.\n\nKEPT CLAIMS:\n${JSON.stringify(kept, null, 1)}\n\nDROPPED CLAIMS (do not use their content unless a correction restores it):\n${JSON.stringify(dropped, null, 1)}\n\nOPEN POINTS:\n${JSON.stringify(insufficient, null, 1)}\n\nProduce: (1) a one-paragraph verdict on the user's impression (is the AVX/AMX split of a partial page a CPU-attention fact, an FPGA-attention fact, or both); (2) the steady-state decode picture under FPGA attention in plain sentences; (3) an exhaustive list of cases in which the AMX path runs while FPGA attention is enabled (phase prefill/decode, condition, what the CPU scores, mechanism, cites, evidence status: verified-in-code / measured / predicted / Insufficient data, and the measurement that settles it); include the cases: query below the engagement point, DMA lag of a whole page, sw_fallback shard, prefill pages not yet resident, prefix-cache hit (open), HBM exhaustion, and any other you find in the kept claims; (4) whether Table 1's "AMX 0" in the FPGA rows must change (it is labelled est. with "DMA keeps up" / "lag 4 tokens"): say exactly what wording or footnote makes it right, or what number replaces 0 and why; (5) the most defensible interpretation of the 2026-09-17 measurement (501 M AMX-busy cycles under FPGA attention = 57 % of CPU attention, one user, warm 910-token cached prefix, about 131 generated tokens), listing the candidate mechanisms with their code cites and what the TRON_ATTN_STATS run would print for each; (6) the counter values an FPGA-attention run (qwen-3-4b, 8 users, prompt 1024, 256 tokens, TRON_ATTN_STATS=1) is expected to print for each case; (7) contradictions between the kept claims and the page's current section-2 text quoted in the context. Plain English: one claim per sentence, define terms at first use, numbers with units.`,
  { label: 'synthesize', phase: 'Synthesize', schema: CASES, effort: 'xhigh' })

phase('Critic')
const CRIT = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['must-fix', 'should-fix', 'note'] }, text: { type: 'string' }, cites: { type: 'array', items: { type: 'string' } } }, required: ['severity', 'text'] } } }, required: ['findings'] }
const critic = await agent(`${CTX}\n\nYou are the completeness critic. Here is the synthesized answer:\n${JSON.stringify(synth, null, 1)}\n\nAnd the kept claims it was built from:\n${JSON.stringify(kept.map(k => ({ id: k.id, text: k.text, cites: k.cites })), null, 1)}\n\nAsk: what case is missing in which AMX could run under FPGA attention; which statement in the synthesis is not backed by a kept claim or a named measurement; which cite does not say what the synthesis says (open the lines and check at least 8 of them, prefer the ones that carry the verdict); does the synthesis contradict the measured facts in the context (the 6,912 pending AMX visits, the 501 M cycles, the perf-record absence of the dense kernel); is the answer to the user's impression fair (the user may be right for CPU attention and for the non-steady cases). Return findings ordered must-fix first.`,
  { label: 'critic', phase: 'Critic', schema: CRIT, effort: 'xhigh' })

return { kept, dropped, insufficient, synth, critic, counts: { kept: kept.length, dropped: dropped.length } }