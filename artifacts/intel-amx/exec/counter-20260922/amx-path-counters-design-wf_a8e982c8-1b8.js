export const meta = {
  name: 'amx-path-counters-design',
  description: 'Verify AVX/AMX/FPGA attention path facts in tron and design path counters + timers',
  phases: [
    { title: 'Read', detail: '8 code readers, one question each, file:line citations' },
    { title: 'Refute', detail: '2 adversarial refuters per reader (code lens, scope lens)' },
    { title: 'Design', detail: '3 independent counter designs' },
    { title: 'Judge', detail: '2 judges score the designs, 1 critic lists gaps' },
  ],
}

const R = args.repo
const REV = args.rev

const COMMON = `
You are reading the tron inference engine source, checked out READ-ONLY at ${R} (git revision ${REV}, main as of ${args.date}).
Never modify files there. Use grep/sed/cat via Bash and Read. Cite every claim as file:line relative to the repo root
(for example h/tron/models/self_attention.hpp:1406). Quote the exact code line for every load-bearing claim.
If you cannot find evidence for something, say "not found" instead of guessing. Distinguish the three attention paths:
  AVX  = the software dotter loop in apply_page_tok (self_attention.hpp), the fallback for every (query, page) pair;
  AMX  = apply_dense_amx_page, taken only when TRON_AMX_DISPATCH is compiled, amx_attn_h128g4::available() is true
         (TRON_AMX_DISABLE != "1"), the shape is eligible (head 128, kv_mul 4, bf16 Q) and the page is dense
         (is_dense_amx_page: begin==0, end==page_size 64, query sees the whole page through one range, inside the window);
  FPGA = hardware attention ("HW attention", USE_HW_ATTN, hw_plan, GOF residency in HBM shards), the results are joined
         by the CPU (join_hw). Users also call the FPGA path "AoF" (attention on FPGA).
Key entry points you may need: h/tron/models/self_attention.hpp (apply_page_range ~1374, apply_page_tok ~1709,
is_dense_amx_page ~1601, compute_operation_uses_hw ~487, run_attention_job ~750-800, join ~1129-1230),
h/tron/models/model.hpp (forward ~1622, hw plan seeds ~2480-2700, hw attention enable ~1440-1530, Save K ~2753),
h/tron/models/ranged_mask.hpp (sw_mask / hw_mask / sw_required / visible), h/tron/models/hw_attn_config.hpp,
src/tron/models/hw_attn_config.cpp, h/tron/kernels/amx_attn_iface.hpp, h/tron/kernels/page_share_counters.hpp,
h/libtron.hpp (~194 prompt chunk limit), h/tron/plugins/ (llama.hpp handwritten plugin; ingested plugins are generated),
h/pos/hwattention.hpp (MIN_TOK_IDX_FOR_HWATTN, shard_tokens), README.perfetto.md, README.stats.md, h/tron/models/expert_stats.hpp.
Vocabulary: a KV page holds 64 tokens; an HBM shard holds 1024 tokens (verify); "pending" attention work = pages whose K/V
are written in this same forward pass; "ready" = pages written in earlier passes. A "decode step" = one forward() that
produces one new token per user. "Prefill" = the forward passes over the prompt tokens.
Return ONLY the structured output. Be exhaustive: more verified claims with citations beat fewer.`

const CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          claim: { type: 'string', description: 'one factual sentence' },
          citations: { type: 'array', items: { type: 'string' }, description: 'file:line entries' },
          quoted_code: { type: 'string', description: 'the exact source line(s) that prove it' },
          confidence: { type: 'string', enum: ['verified', 'likely', 'unsure'] },
          caveats: { type: 'string' },
        },
        required: ['id', 'claim', 'citations', 'confidence'],
      },
    },
    direct_answer: { type: 'string', description: 'plain-English answer to the question asked, 3-10 sentences' },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['claims', 'direct_answer'],
}

const READERS = [
  { key: 'R1-prefill', q: `QUESTION R1 (prefill path split). The user believes: "prefill is only the first token, and it has to be on AMX
no matter whether attention-on-FPGA is enabled or not, so a prefill counter may be useless". Test that belief against the code.
Establish: (a) how a prompt is fed: tokens per user per forward (h/libtron.hpp ~194-210 TRON_PER_USER_PROMPT_CHUNK_LIMIT, and the
per-forward capacity across users), so how many forward() calls a prompt of 1024 or 8192 tokens takes; (b) with CPU attention
(USE_HW_ATTN=0): for a prefill forward, which (query token, KV page) pairs satisfy is_dense_amx_page (full 64-token pages written in
EARLIER forwards, i.e. ready pages of previous chunks) and which go to the AVX dotter (the query's own chunk = pending pages, the
partial last page, pages a query only partly sees because of causality); (c) with FPGA attention: which pairs the hw plan sends to the
FPGA (hw_plan_entries, engagement point hw_attn_engagement_point() = MIN_TOK_IDX_FOR_HWATTN value?, HBM-resident complete GOFs,
"Note [GOF residency is a prefix", Note [HW Attention and prompt queries]) and which stay on the CPU (positions below the engagement
point, the own-chunk causal triangle, K/V whose DMA to HBM has not completed = "DMA-lagging"); (d) whether, when FPGA attention is on,
CPU-side dense visible pages can still take AMX (does apply_page_tok's dispatch consult uses_hw? run_visible_in_software vs
sw_required). (e) How much attention work prefill is relative to one decode step (number of (query,page) visits for prompt N with
page 64, order N^2/128, versus N/64 for one decode query) so the reader can judge whether prefill is "one token" of work.
Give the rule set as claims. Also state which unit ("tokens", "(query,page) visits", "K tokens scored" = dot products) makes the prefill
share meaningful.` },
  { key: 'R2-decode', q: `QUESTION R2 (decode path split). The user asks: "out of 256 generated tokens, how many are generated by the AVX path,
the AMX path, or the FPGA path? Can this be calculated?" Establish for ONE decode step of ONE user at context length N (prompt + tokens
so far), one layer, one kv_head: (a) how many KV pages the query visits; which are dense (is_dense_amx_page -> AMX) and which are partial
(the page currently being filled -> AVX dotter). Confirm whether the partial page is the "pending" page (Note [Ready versus pending
attention work], run_sections pending=true, plan_state.pending_kv_plan) and whether a full page can ever be pending. (b) with FPGA
attention on: which K tokens the FPGA scores (hw_query.last_hw_token_pos, reachable_shard_count, shard size hardware::shard_tokens, GOF
completion = HBM residency), what stays on the CPU (positions < hw_attn_engagement_point(); the tail between the last complete shard and
N; DMA-lagging K/V), and whether the FPGA/CPU boundary for a given N is deterministic or depends on asynchronous DMA completion timing
(count_complete_gofs race comment near model.hpp:2503; dma_tracker; "sw_fallback"). (c) Whether within the CPU part, under FPGA
attention, dense pages still take AMX (sw_required vs visible; is_dense_amx_page takes query_visible computed from sw_required when
!run_visible_in_software). (d) Therefore: is "a token is generated by path X" a well-defined statement, or is every decode token a mix
(FPGA for resident shards, AMX for full CPU pages, AVX for the partial page and the young positions)? (e) Give the closed-form counts a
person could compute for N (pages, dense pages, FPGA shards) and list what CANNOT be computed offline (DMA lag, residency, prefix-cache
state), which is the argument for measuring. Also check the sliding-window case (window layers never use hw; the window truncates the
page set) and Eagle.` },
  { key: 'R3-layers', q: `QUESTION R3 (per-layer uniformity). The user asks: "when a token is generated through a path (AVX/AMX/FPGA) at one
layer, it took the same path at all layers, correct?" Establish: (a) FPGA attention per layer: what do cfg.max_layers and
hw_attn_kv_slot_extent mean (model.hpp ~1440-1530, "HW attention enabled for model ... max_layers=... kv_slot_extent=..."): are there
models where only the first K layers have HBM-resident K/V and later layers run attention on the CPU? Which models (check config/,
ingest/, hw_attn_config, plugin force_hw_attn) and what decides max_layers (HBM capacity?). (b) compute_operation_uses_hw
(self_attention.hpp ~487): a layer/operation with a sliding window, a non-representable scale, an Eagle model, or a heterogeneous
geometry never uses the FPGA -> in models mixing full and window layers (gpt-oss? check h/tron/plugins and ingest for
sliding_window_size) the path differs by layer. (c) AMX per layer: eligibility (head_size 128, kv_mul 4, bf16 activation) is per
attention geometry; can geometry differ across layers of one model (heterogeneous_kv_cache.hpp, declares_geometry)? Is the KV page
structure (which tokens are in which page, page.count()) the same for every layer, so the dense predicate gives the same answer in every
layer for the same (query, page)? Is the pending/ready split the same for every layer? (d) List per model: llama-3.1-8b (handwritten
h/tron/plugins/llama.hpp), qwen-3-4b (ingested), gpt-oss-120b, mixtral-8x7b, llama-3.3-70b: head size, kv_mul, window layers, hw
default, AMX eligible yes/no, hw max_layers if found. Answer the user's question with "yes for ..., no for ..." and cite.` },
  { key: 'R4-existing', q: `QUESTION R4 (existing instrumentation). Inventory what tron ALREADY measures or traces that bears on: which path a
(query,page) pair took; attention run time per layer; per-layer run time; per-decode-step (per forward) run time. Cover: (a) PR0
page_share_counters (h/tron/kernels/page_share_counters.hpp, hooks in self_attention.hpp, t/t_page_share_counters.cpp, CMake option
TRON_PAGE_SHARE_COUNTERS in CMakeLists.txt / CMakePresets.json / README.ci.md): what is counted (visits, relevant query tokens,
pending visits, histogram), what is NOT (no AMX-vs-AVX tag, no FPGA work, no time), when it prints (exit_reporter). (b) Perfetto
TRACE_EVENT spans: list the spans in self_attention.hpp, model.hpp, the llama plugin and the scheduler that bound: one forward
("scheduler","forward" model.hpp:1622), one layer (find any per-layer span, e.g. in h/tron/plugins/llama.hpp or the generated ingested
plugin runtime), attention work per worker ("Attention Ready"/"Attention Pending" with args relevant q tokens / dot products / pages),
hw attention prep/launch/join ("hwattention" category), Save K / Save V. State which categories perfetto/runtron.cfg enables and what
the trace can already answer offline (per-layer attention time per worker, per-forward time) and what it cannot (path tag per page).
(c) FUSE stats (README.stats.md, h/system/fuse_stats.hpp, h/tron/models/expert_stats.hpp, any tokens/s or latency leaves in
src/rinzler* or src/tron): what live counters/timers exist, the make_file/set_read_callback pattern, the manifest/.skip rule for
exported leaves, and issue-#4303-style env-var opt-in. (d) runtron's own timing prints (grep src/ for "Parsing the prompt took",
tokens/s, per-token timing, --stats options) and any per-token latency stats in rinzler (TTFT, inter-token). (e) any existing
"sw_fallback" / "free_total" / "free_max" HBM counters (grep -rn sw_fallback) as a precedent for counting FPGA-vs-software fallbacks.
Return each item as a claim with citations, and a direct answer: what the user can get today with zero code, and what needs new code.` },
  { key: 'R5-gates', q: `QUESTION R5 (AMX gate chain and shapes). Establish the complete chain that decides whether a (query,page) pair can take
the AMX path, with citations: (1) compile time: CMake option TRON_AMX_DISPATCH (CMakeLists.txt, CMakePresets.json: which presets set it,
including the deb preset if any; README.ci.md), (2) process start: amx_attn_h128g4::available() (h/tron/kernels/amx_attn_iface.hpp,
src/tron/kernels/amx*.cpp): CPUID bits, arch_prctl permission request, TRON_AMX_DISABLE exact value "1", (3) shape:
eligible(head_size, kv_mul) and query_scalar_ok<activation_scalar> — the exact constants, (4) per pair: packed Q non-null and
is_dense_amx_page. Then: (5) confirm that uses_hw (FPGA attention) does NOT gate AMX: the dispatch sits inside the software page loop
that runs in both modes (self_attention.hpp ~1406 run_visible_in_software, ~1746 query_visible from sw_required). (6) For each production
model in config/ or README.models.md (llama-3.1-8b, llama-3.3-70b, qwen-3-4b, qwen3-30b?, gpt-oss-120b, mixtral-8x7b, deepseek?): head
size, n_heads/n_kv_heads -> kv_mul, activation type -> AMX eligible yes/no. (7) Where a "path taken" tag could be observed at zero
ambiguity: apply_page_tok's early return {page_size, range_hint} for AMX vs the dotter loop return, and what the cheapest possible
counter site would be (per apply_page_range call, plain integers flushed to atomics, like page_visit_counts). Also report how PR0's
counters are gated (compile-time define) and how issue #4303 proposed to gate them at runtime, if the repo has any trace of that.` },
  { key: 'R6-units', q: `QUESTION R6 (a common unit of attention work across AVX, AMX, FPGA). The user wants "how much, out of the total, ran on
each path". Establish which quantities exist in code that could be summed per path: (a) apply_page_tok returns relevant_k_tokens (the AMX
branch returns page::page_size = 64); what exactly does the dotter count as relevant (visible K tokens inside the window, begin..end)?
(b) work_estimate_t fields (k_dot_products, scaled_vs, kv_heads) in estimate_attention_work (model.hpp ~1787-1865): how they are computed
and whether they already split sw vs hw (any_sw_required vs any_visible) — could the estimate alone give the FPGA/CPU split per forward
without touching the hot loop? (c) FPGA side: per hw_query the covered K tokens = last_hw_token_pos + 1 (or reachable shards x 1024) —
where the plan records queries and shards per pass (model.hpp ~2480-2700, hw_plan, pass_seed, hw_plan_entry) and where a per-layer
counter could sum "K tokens scored by the FPGA" and "queries served by the FPGA". (d) Which unit is comparable: a (query, page) visit is
64 K tokens for AMX but 1..64 for AVX; a K-token score (one q.k dot product per query head, kv_mul heads per kv_head) is the same amount of
math on every path, so "K tokens scored x kv_mul" is the natural unit. Say what each path's count would be for one decode query at
context N with FPGA covering the first S complete shards. (e) Also determine how a forward can be classified as prefill vs decode from
inside model.hpp/self_attention.hpp (is there a flag: token_jobs_do_kv, n_tokens vs n_token_jobs, generation vs prompt, "is_prompt"?),
so counters can be split into prefill-share and decode-share buckets. Cite everything.` },
  { key: 'R7-timing', q: `QUESTION R7 (where to hook timers). The user wants: attention run time, each layer's run time, each decode step's run
time. Establish: (a) the code boundary of one decode step: scheduler forward() (model.hpp:1622) — is one forward() = one step for all
users in the batch? where does runtron loop over steps (src/runtron*.cpp or h/libtron.hpp generate loop), and what timing runtron already
prints per step or at the end. (b) the per-layer boundary: in the handwritten llama plugin (h/tron/plugins/llama.hpp) find the layer loop
and any TRACE_EVENT per layer; for ingested (generated) plugins find where the generated code runs one layer (h/tron/plugins/*.hpp,
ingest/ templates, "TronCpp.hs" Note [Generated attention operation phases]) and whether a common per-layer hook point exists in model.hpp
(e.g. next_layer, prepare_attention_job, layer.i in TRACE_EVENT args). (c) the attention boundary per layer: run_attention_job start
(self_attention.hpp ~750-800), the ready pass, the pending pass, the join, attn_done_barrier / vo latch; note that attention runs on
n_attn_workers threads concurrently with main-stream matmuls (the FPGA matmuls), so "attention run time" must be defined as either
per-worker busy time (sum) or wall time from first start to last join (critical path) — say which spans already exist. (d) which clock
tron uses in hot paths (rdtsc / __builtin_ia32_rdtsc / std::chrono::steady_clock / tron::now?) — grep for existing timers (h/system/,
h/tron/scheduler, "elapsed", "clock_gettime") and their cost expectations. (e) whether the FPGA attention time (launch -> results
consumed) is bounded by existing spans ("hwattention" launch_hw_attn, attention: join wait). Return claims with citations and a direct
answer proposing the exact hook lines for the three timers, and the number of attention workers per config if found
(n_attn_workers source).` },
  { key: 'R8-fpga-cpu', q: `QUESTION R8 (what the CPU does when the FPGA does attention, and FPGA fallbacks). Establish: (a) with FPGA
attention on, the CPU attention workers still run apply_page_range over sw_required pairs; enumerate every source of sw_required work in
a hardware layer: positions below hw_attn_engagement_point() (find the value of hardware::MIN_TOK_IDX_FOR_HWATTN in h/pos/hwattention.hpp),
the own-forward pending pages, K/V not yet HBM-resident (GOF not complete), per-query causal tails beyond the last complete shard, and
anything else the mask builder marks SW_REQUIRED (find where ranged_mask ranges get sw_required_mask vs hw_available_mask: grep
"SW_REQUIRED", "sw_required_mask", "hw_available", "add_range", in model.hpp / scheduler). (b) HBM K/V space exhaustion: when a shard
placement fails, does the query fall back to software for that range (grep sw_fallback, "largest free block", placement failure
warnings) — is that fallback counted anywhere (free_total/free_max/sw_fallback_total leaves)? (c) The join: how the CPU merges the FPGA
partial (m*, s*, v*) with the CPU partial (join_hw, Note [Streaming hardware attention join], Note [Host scale for hardware attention
joins]) so a counter that tags "K tokens scored by FPGA" per query can be read from the same place. (d) Whether FPGA attention is per
device/tp: with tp2 or tp4, do the FPGAs split the K/V by device (by_device groups) and is the CPU attention unsharded? (e) Whether decode
under FPGA attention uses FPGA for every layer or only layers <= max_layers (cross-check with R3, cite independently). Provide claims
with citations and a direct answer on: "for a decode token under attention-on-FPGA, which fraction of the K tokens is scored by the CPU and
why it is not zero".` },
]

const REFUTE_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim_id: { type: 'string' },
          verdict: { type: 'string', enum: ['holds', 'refuted', 'needs_qualifier', 'could_not_check'] },
          evidence: { type: 'string', description: 'file:line + quoted code that decides it' },
          corrected_claim: { type: 'string', description: 'the claim rewritten so it is true, if not holds' },
        },
        required: ['claim_id', 'verdict', 'evidence'],
      },
    },
    missed_facts: { type: 'array', items: { type: 'string' }, description: 'important facts the reader missed, with file:line' },
  },
  required: ['verdicts'],
}

const LENSES = [
  { name: 'code', text: `LENS = CODE CORRECTNESS. For every claim, open the cited lines and try to find a line that contradicts it, an off-by-one
(e.g. engagement point 127 vs position >= 127 vs > 127; page_size 64 vs count()), a different default (env var parsing), or a branch the
reader ignored (if constexpr, #ifdef, Eagle, sliding window, heterogeneous geometry). Default to "needs_qualifier" if the claim is true only
under a condition the claim does not state.` },
  { name: 'scope', text: `LENS = SCOPE AND GENERALITY. For every claim, ask: does it hold for BOTH plugin kinds (handwritten llama.hpp and generated
ingested plugins, e.g. qwen), for both attention modes (USE_HW_ATTN on/off), for multi-user batches and minibatches, for tp2/tp4 device
splits, for prefix-cache hits (shared pages, page.count() with stale entries from other branches), and at revision ${REV} rather than an
older tree? Check that cited line numbers actually contain the quoted code at this revision. Mark "needs_qualifier" with the missing
condition, or "refuted" with the contradicting code.` },
]

phase('Read')
log(`Reading ${READERS.length} questions against ${R} @ ${REV}`)

const readResults = await pipeline(
  READERS,
  r => agent(`${COMMON}\n\n${r.q}`, { label: `read:${r.key}`, phase: 'Read', schema: CLAIMS_SCHEMA }),
  (read, r) => {
    if (!read) return null
    return parallel(LENSES.map(l => () =>
      agent(`${COMMON}\n\n${l.text}\n\nHere are the claims a previous reader produced for the question "${r.key}". Try hard to REFUTE
each one against the source. Verdict "holds" only after you opened the cited code yourself. List important facts the reader missed.\n\n` +
        `READER DIRECT ANSWER:\n${read.direct_answer}\n\nCLAIMS (JSON):\n${JSON.stringify(read.claims, null, 1)}`,
        { label: `refute:${r.key}:${l.name}`, phase: 'Refute', schema: REFUTE_SCHEMA })
    )).then(votes => ({ key: r.key, read, votes: votes.filter(Boolean) }))
  },
)

const verified = readResults.filter(Boolean)
log(`Read+refute done for ${verified.length}/${READERS.length} questions`)

// Merge: a claim survives if no lens refuted it; qualifiers are attached.
const facts = []
for (const item of verified) {
  for (const c of item.read.claims) {
    const vs = item.votes.flatMap(v => v.verdicts.filter(x => x.claim_id === c.id))
    const refuted = vs.some(v => v.verdict === 'refuted')
    const quals = vs.filter(v => v.verdict === 'needs_qualifier')
    facts.push({
      q: item.key, id: c.id, claim: c.claim, citations: c.citations, quoted_code: c.quoted_code || '',
      confidence: c.confidence, caveats: c.caveats || '',
      status: refuted ? 'REFUTED' : quals.length ? 'QUALIFIED' : 'HOLDS',
      verdicts: vs.map(v => ({ verdict: v.verdict, evidence: v.evidence, corrected_claim: v.corrected_claim || '' })),
    })
  }
}
const missed = verified.flatMap(i => i.votes.flatMap(v => (v.missed_facts || []).map(m => ({ q: i.key, fact: m }))))
const answers = verified.map(i => ({ q: i.key, answer: i.read.direct_answer, open: i.read.open_questions || [] }))
log(`${facts.length} claims: ${facts.filter(f => f.status === 'HOLDS').length} hold, ${facts.filter(f => f.status === 'QUALIFIED').length} qualified, ${facts.filter(f => f.status === 'REFUTED').length} refuted; ${missed.length} missed facts`)

// ---------------- Design (barrier justified: designers need ALL verified facts) ----------------
phase('Design')
const FACT_PACK = `VERIFIED FACT PACK (from 8 readers + 16 refuters; status HOLDS / QUALIFIED (see corrected_claim) / REFUTED (do not use)):\n` +
  JSON.stringify(facts.filter(f => f.status !== 'REFUTED').map(f => ({ id: `${f.q}/${f.id}`, claim: f.claim, cites: f.citations, status: f.status,
    corrections: f.verdicts.filter(v => v.corrected_claim).map(v => v.corrected_claim) })), null, 0) +
  `\n\nREADER DIRECT ANSWERS:\n` + answers.map(a => `[${a.q}] ${a.answer}`).join('\n\n') +
  `\n\nMISSED FACTS FLAGGED BY REFUTERS:\n` + missed.map(m => `[${m.q}] ${m.fact}`).join('\n')

const USER_ASK = `THE USER'S REQUEST (jhan, 2026-09-22): "add counters on top of PR3879 (the canonical AMX attention PR, merged to main
2026-09-15) to measure how much, out of the total, runs on the AVX / AMX / AoF (attention-on-FPGA) path:
 - prefill tokens: only the first token, and it has to be on AMX no matter what AoF is enabled or not, right? So this counter may be useless?
 - decode tokens: out of 256 generated tokens, how many are generated by the AVX path, AMX path or AoF path. Can this be calculated?
   Even so it is good to measure. When a token is generated through a path at one layer, it took the same path at all layers, correct?
 - also measure attention run time, each layer run time and each token decode run time."
Context: PR0 (#4267, merged) added page_share_counters gated by CMake option TRON_PAGE_SHARE_COUNTERS with an exit report; issue #4303
asks to publish counters as FUSE stats with env-var opt-in so they can be read live. The kill switch TRON_AMX_DISABLE=1 turns AMX off at
run time. EXE.AMX_BUSY (perf raw event 0xb7/0x02 on the engine pid) already proves AMX ran from outside the process.`

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    design_name: { type: 'string' },
    thesis: { type: 'string' },
    unit_of_work: { type: 'string', description: 'the unit summed per path and why it is comparable across AVX/AMX/FPGA' },
    counters: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' }, unit: { type: 'string' }, path_tag: { type: 'string' },
          hook_site: { type: 'string', description: 'file:line and the surrounding function' },
          bucket: { type: 'string', description: 'per layer / per forward / per prefill-vs-decode / per user' },
          cost_when_on: { type: 'string' }, cost_when_off: { type: 'string' },
          what_it_answers: { type: 'string' },
        },
        required: ['name', 'unit', 'hook_site', 'what_it_answers'],
      },
    },
    timers: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' }, start_site: { type: 'string' }, end_site: { type: 'string' },
          clock: { type: 'string' }, definition: { type: 'string', description: 'wall vs busy, which thread' },
          bucket: { type: 'string' }, what_it_answers: { type: 'string' },
        },
        required: ['name', 'start_site', 'end_site', 'definition'],
      },
    },
    reporting: { type: 'string', description: 'exit report / FUSE leaves / perfetto args / all three; format of the report' },
    gating: { type: 'string', description: 'compile-time define and/or env var; default state; relation to TRON_PAGE_SHARE_COUNTERS' },
    answers_to_user: {
      type: 'object',
      properties: {
        prefill_counter_useless: { type: 'string' },
        decode_tokens_by_path_calculable: { type: 'string' },
        same_path_all_layers: { type: 'string' },
        timing: { type: 'string' },
      },
      required: ['prefill_counter_useless', 'decode_tokens_by_path_calculable', 'same_path_all_layers', 'timing'],
    },
    worked_example: { type: 'string', description: 'numbers for one decode query at context 1024+t and for prompt 1024 prefill, both modes' },
    risks: { type: 'array', items: { type: 'string' } },
    files_touched_est: { type: 'array', items: { type: 'string' } },
  },
  required: ['design_name', 'thesis', 'unit_of_work', 'counters', 'timers', 'reporting', 'gating', 'answers_to_user', 'worked_example', 'risks'],
}

const DESIGN_ANGLES = [
  { key: 'minimal', text: `ANGLE = MINIMAL PATCH. Reuse the PR0 page_share_counters shape (plain integers per apply_page_range call, flushed to
process-wide atomics, exit report) and add the smallest set of counters that answers the user's three questions; a path tag at the
apply_page_tok return site, an FPGA K-token count at the hw plan, and cheap per-forward / per-layer / per-attention-job timers with
rdtsc or steady_clock stored in fixed arrays indexed by layer. Prefer 1-3 files. State exactly which existing counter each new one extends.` },
  { key: 'live', text: `ANGLE = LIVE, PRODUCTION-READABLE. Follow issue #4303: env-var opt-in at run time, publish through the FUSE stats tree
(h/system/fuse_stats.hpp make_file + set_read_callback, expert_stats.hpp precedent, casual leaves without manifest), monotonic counters
that can be differenced over intervals from outside (pho / cat), one JSON summary leaf plus per-path leaves, per-layer histograms of
attention time. Handle the rinzler unmount-before-exit rule. Say what the .deb rinzler pays when the env var is unset.` },
  { key: 'trace', text: `ANGLE = DERIVE FROM TRACES FIRST. Ask what perfetto already gives (forward span, Attention Ready/Pending spans with
dot-product and page args, hwattention spans) and design the smallest code delta that makes the trace self-sufficient: add "amx pages",
"avx pages", "amx k tokens", "avx k tokens" args to the Attention Ready/Pending TRACE_EVENT, a per-layer span, and hw plan args (queries,
shards, k tokens) to launch_hw_attn; then an offline trace-processor SQL/python script computes shares and the three timings per layer and
per step. Explain what the trace overhead is and why this needs no exit report, and what it cannot do (production, live).` },
]

const designs = (await parallel(DESIGN_ANGLES.map(a => () =>
  agent(`${COMMON}\n\n${USER_ASK}\n\n${a.text}\n\nUse ONLY facts from the fact pack below or facts you verify yourself in the source (cite
file:line for every hook site you propose; open the file and confirm the line exists at this revision). Give a worked example with
numbers. Answer the user's three questions plainly (they hold two wrong premises if the fact pack says so: say which, and why).\n\n${FACT_PACK}`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA, effort: 'xhigh' })
))).filter(Boolean)
log(`${designs.length}/3 designs produced`)

// ---------------- Judge + critic (barrier: judges compare all designs) ----------------
phase('Judge')
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          design_name: { type: 'string' },
          correctness: { type: 'number' }, answers_user: { type: 'number' }, cost_and_intrusion: { type: 'number' },
          usefulness: { type: 'number' }, total: { type: 'number' },
          hook_site_errors: { type: 'array', items: { type: 'string' }, description: 'proposed hook lines that do not match the source' },
          rationale: { type: 'string' },
        },
        required: ['design_name', 'total', 'rationale'],
      },
    },
    winner: { type: 'string' },
    graft_from_others: { type: 'array', items: { type: 'string' }, description: 'specific ideas from runners-up to keep' },
    recommended_final: { type: 'string', description: 'the synthesized recommendation in 10-20 sentences' },
  },
  required: ['scores', 'winner', 'recommended_final'],
}
const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    gaps: { type: 'array', items: { type: 'string' } },
    wrong_premises_in_user_ask: { type: 'array', items: { type: 'string' }, description: 'each with the fact ids that show it' },
    unverified_claims_used_by_designs: { type: 'array', items: { type: 'string' } },
    measurements_needed_before_deciding: { type: 'array', items: { type: 'string' } },
    glossary_terms: { type: 'array', items: { type: 'string' }, description: 'terms the final page must define at first use' },
  },
  required: ['gaps', 'wrong_premises_in_user_ask'],
}
const DESIGN_PACK = designs.map(d => `=== DESIGN ${d.design_name} ===\n${JSON.stringify(d, null, 0)}`).join('\n\n')

const [judgeA, judgeB, critic] = await parallel([
  () => agent(`${COMMON}\n\n${USER_ASK}\n\nYou are JUDGE A (engineering reviewer of the tron team, cares about hot-loop cost, correctness of
hook sites, and that counters stay off in the .deb by default). Score each design 0-10 on correctness, answers_user, cost_and_intrusion,
usefulness; total = sum. Open every proposed hook site in the source and list the ones that do not exist or sit in the wrong function.
Pick a winner and list ideas to graft from the others.\n\n${FACT_PACK}\n\n${DESIGN_PACK}`,
    { label: 'judge:A-engineering', phase: 'Judge', schema: JUDGE_SCHEMA, effort: 'xhigh' }),
  () => agent(`${COMMON}\n\n${USER_ASK}\n\nYou are JUDGE B (the user's perspective: a performance engineer who will run campaigns on the CI
machine and needs numbers that answer "how much ran on AVX / AMX / FPGA" and "how long did attention / a layer / a decode step take",
per prompt length and per model, with the least ceremony). Score each design 0-10 on correctness, answers_user, cost_and_intrusion,
usefulness; total = sum. Check that each design's worked example is arithmetically consistent with the fact pack (page 64, shard size,
engagement point). Pick a winner and list ideas to graft.\n\n${FACT_PACK}\n\n${DESIGN_PACK}`,
    { label: 'judge:B-user', phase: 'Judge', schema: JUDGE_SCHEMA, effort: 'xhigh' }),
  () => agent(`${COMMON}\n\n${USER_ASK}\n\nYou are the COMPLETENESS CRITIC. Given the fact pack and the three designs: what is missing? Which of
the user's premises are wrong and which fact ids prove it? Which claims do the designs rely on that the fact pack does not verify (open the
source to check them)? What must be measured before choosing (e.g. cost of the off-state branch, rdtsc cost per call)? Which terms must the
final HTML page define at first use (project rule: tron, runtron, rinzler, AMX, AVX, AoF, bf16, KV page, shard, GOF, HBM, kv_mul/GQA,
forced run, pending/ready, engagement point, TRON_AMX_DISABLE, USE_HW_ATTN, FUSE stats, perfetto ...)?\n\n${FACT_PACK}\n\n${DESIGN_PACK}`,
    { label: 'critic:completeness', phase: 'Judge', schema: CRITIC_SCHEMA, effort: 'xhigh' }),
])

return { rev: REV, facts, missed, answers, designs, judges: [judgeA, judgeB].filter(Boolean), critic }
