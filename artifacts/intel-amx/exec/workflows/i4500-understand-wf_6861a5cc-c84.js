export const meta = {
  name: 'i4500-understand',
  description: 'Read the FPGA-attention decode/prefill paths of the VNNI-K fix branch vs canonical main; verify each fact adversarially; synthesize',
  phases: [
    { title: 'Read', detail: 'one reader per question, file:line facts' },
    { title: 'Verify', detail: 'two refuters per reader (code-reads-what-cited, missed-path)' },
    { title: 'Synthesize', detail: 'merged fact sheet with confirmed/refuted flags' },
  ],
}

const FIX = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-i4500'
const BASE = '/home/jhan/workspace/ai-runs/tron-canon-3faba'
const PRHEAD = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'

const CONTEXT = `
CONTEXT (read carefully; all paths are on this machine, claude-box):
- FIX worktree (branch jhan-amx-vnniK-i4500, head f34b0fe2ec, TRON_K_VNNI build assumed ON): ${FIX}
- BASE worktree (main 3faba6d0fd = the "canonical AMX" build, row-major K, AMX kernels on): ${BASE}
- PR HEAD worktree (PR #4424 head 30c4ac82cb, VNNI K without the fix): ${PRHEAD}
- Key files: h/tron/models/model.hpp (forward pass, save_k, launch phases, GOF staging), h/tron/models/self_attention.hpp (software attention loop apply_page_range, joins, HW passes), h/tron/models/kv_cache.hpp (page/book, Note [K VNNI storage]), h/tron/kernels/k_vnni.hpp, h/tron/kernels/amx_attn_iface.hpp, h/tron/gof.hpp, src/tron/models/hw_attn_config.cpp, h/tron/models/hw_attn_config.hpp.
- Situation: qwen3-4b with FPGA attention (USE_HW_ATTN default on for ingested models, engagement point 127) loses decode TPS under the VNNI K layout: PR head -3.8 % (tp2, 2 users/engine) and -11.8 % (tp4, 4 users/engine) vs BASE; the fix (row-major 16-token tail block, converted at forward end) recovers only ~1/3 (fix -2.3 % / -8.8 %). llama-8b with CPU attention (USE_HW_ATTN=0) gains +8.5 % with both. Under FPGA attention the AMX dense page kernel is believed never to run in decode. Micro-facts from earlier campaigns: 09-19 perfetto traces (PR head, no fix): tp2 2u Save K on main 210 vs 59 us/pass; workers' "Attention Pending" max 313 vs 201 us/pass; launch ~60 us; hw wait ~610 us. EXE.AMX_BUSY counts in FPGA cells are deterministic per binary+cell: 583 M cycles/20 s (early launch, and BASE) vs 1239 M (VNNI build, late launch) — nonzero although the dense kernel is believed absent.
- Earlier report claims to VERIFY OR REFUTE, do not assume: (a) "positions 64..126 are scored by the CPU on every decode step, in converted VNNI blocks" ("engagement-prefix page"); (b) "the AMX dense kernel never runs in FPGA decode"; (c) "gof::populate gathers K rows once per GOF (4 tokens) per user".
- Rules: cite every fact as path:line (relative to the worktree, say which worktree). Use grep/sed/awk via Bash to read. Read the actual code, not comments only; when a comment and code disagree, say so. Return raw data (no prose for a human).
`

const FACTS = {
  type: 'object',
  properties: {
    facts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, claim: { type: 'string' },
      evidence: { type: 'array', items: { type: 'string' } },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    }, required: ['id', 'claim', 'evidence', 'confidence'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['facts', 'open_questions', 'notes'],
}

const VERDICT = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      verdict: { type: 'string', enum: ['confirmed', 'refuted', 'corrected', 'unverifiable'] },
      reason: { type: 'string' },
      correction: { type: 'string' },
      evidence: { type: 'array', items: { type: 'string' } },
    }, required: ['id', 'verdict', 'reason', 'evidence'] } },
    missed: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdicts', 'missed'],
}

const READERS = [
  { key: 'cpu-key-range', q: `QUESTION 1: In DECODE under FPGA (HW) attention, for one user whose context is ~1100 tokens (prompt 1024 + generated), which KEY positions does the CPU software path score, and which does the card score? Trace: how the attention plan splits pages into HW passes vs SW sections/page ranges (self_attention.hpp: plan, run_sections, apply_page_range, hw_plan entries, query_mask, last_hw_token_pos, count_complete_gofs / count_complete_prefix_gofs, hardware::shard base_tok_ix, MIN_TOK_IDX_FOR_HWATTN, engagement point 127). Specifically decide claim (a): does the CPU score positions 64..126 on every step? Does it score page 0 (0..63)? Is any page the CPU scores DENSE (all 64 rows saved and visible) so that the AMX kernel gate could pass (claim (b))? Which threads (attention workers vs main) score the SW ranges, and which reader is used per page/block in FIX (dotter via row_ptr, k_vnni::qk_group, qk_vnni_128x4) vs BASE (row-major dotter, AMX transposing kernel)? Read the FIX worktree first, then diff vs BASE for the same functions.` },
  { key: 'main-thread-step', q: `QUESTION 2: List every piece of MAIN-THREAD work per decode step (per layer and per forward) that differs between FIX and BASE under FPGA attention: save_k row path (set_k_row, note_k_row_saved atomics, k_state_ix, pending block queue), convert_pending_k_blocks (when, how many bytes, which thread, memory ordering), wait_for_coop_gof, gof staging (populate/help_drain_gof: who runs it, how often, get_k_row memcpy vs gather), the late-launch sequence (what runs between Save K and the launch; is the K save serial with the card at batch < MIN_B), clear_kv_complete_at/k_forget_row on the scheduler thread. For each item give the FIX code, the BASE code, and an instruction-level estimate of extra work per token per layer (bytes touched, atomics). Also: does anything in FIX touch the K plane of ALREADY CONVERTED blocks on the main thread per step? Do NOT estimate timing beyond bytes/atomics counts.` },
  { key: 'amx-side-work', q: `QUESTION 3: What AMX-related work happens per apply_page_range call / per decode step on attention workers in the VNNI (FIX) build when NO page is dense (FPGA decode), vs BASE? Cover: the dense gate (what is checked, in which order, cost), Q packing (amx_attn_iface / qpack / attn_accum: when is Q packed — per call, per page, once per step per head?), tile configuration (ldtilecfg / tilerelease / _tile_loadconfig: per call? per thread? bracketed how?), scratch allocation, amx_available() probing, and what exactly TRON_AMX_DISABLE=1 (the kill switch) removes at run time. Determine where AMX instructions CAN execute under FPGA attention (decode and prefill: e.g. SW-scored query positions below the engagement point 127 during prefill, dense pages in the SW range) — this must explain a nonzero deterministic EXE.AMX_BUSY count. Also check whether any per-call AMX prep (tile config load, tile zero) happens even when the kernel is not invoked, both in FIX and BASE. Compare FIX vs BASE line by line for apply_page_range's per-page dispatch.` },
  { key: 'launch-phase', q: `QUESTION 4: The early/late HW attention launch (model.hpp Note [Early and late hardware attention launch], TRON_HWATTN_EARLY_LAUNCH_MIN_B default 4). Trace the exact sequence of main-thread actions per layer for batch B < MIN_B (late) and B >= MIN_B (early) in FIX: where Save K / Save V, prepare, launch, attention barrier, GOF staging drain sit relative to each other; what the workers do meanwhile; what the card's result wait looks like. Then: (i) why was the default 4 chosen (git log -S / blame in FIX or BASE for the note and the constant; any PR text in commit messages); (ii) what would break or change if the default became 1 or 2 (correctness hazards: does early launch require anything that a 2-user batch lacks? any test asserting the phase?); (iii) is the phase selectable per model or only globally via env; (iv) how rinzler sets env for engines (search src/rinzler and packaging/ config for TRON_HWATTN_EARLY_LAUNCH_MIN_B, USE_HW_ATTN, config.env, /opt/positron/user/config.env). Evidence with path:line.` },
  { key: 'prefill-ttft', q: `QUESTION 5: PREFILL (TTFT) path differences FIX vs BASE, both under FPGA attention (qwen3-4b) and CPU attention (llama-8b): the K store for full 16-token blocks (set_k_block, transposes in registers, shared block save with main helpers), the tail block of a prompt, gof::populate for prefill (how K rows are staged to the card: per row gather from VNNI blocks vs memcpy; how many rows per prompt; which threads), SW-scored prefill queries below the engagement point (which pages, which kernel), and anything at the end of prefill (conversions queued per forward: how many blocks, on which thread). Estimate bytes touched per prompt token per layer for each item in FIX vs BASE. Say explicitly which of these items are on the critical path of TTFT (main thread serial) vs on workers.` },
  { key: 'runtime-layout-policy', q: `QUESTION 6: FEASIBILITY of a RUNTIME layout policy in the FIX code: "for a model that runs with HW (FPGA) attention, never convert blocks to VNNI: keep every K block row-major, so the FPGA-attention decode path equals the row-major (BASE) path byte for byte, while CPU-attention models keep the VNNI layout". Read the FIX machinery: k_rows_saved_/k_vnni_blocks_ bits, set_k_block (full-block VNNI store), convert_pending_k_blocks, the dense AMX gate, readers get_k_row/set_k_row, qk_group vs row_ptr dotter, copy_storage_slot, k_forget_row. Enumerate every code site that would need a policy check, what the policy input would be (fwd_hw_attn_enabled(default) is per model: find where the model learns it, model.hpp ~line 1489 'HW attention enabled for model'), whether the book/page can carry a per-book flag (vs a global), and whether set_k_block has a row-major sibling path available in the VNNI build (or if the row-major full-block store exists only under #ifndef TRON_K_VNNI). Also assess the alternative of a per-model TEMPLATE/geometry choice (layout_on as a runtime bool vs compile-time constexpr): count the #ifdef TRON_K_VNNI and layout_on<...> uses in FIX (grep) and classify each. Return the list of sites with path:line and a difficulty rating each. Also note any test that pins 'VNNI build => blocks convert'.` },
  { key: 'kill-switch-tp4', q: `QUESTION 7: On 2026-09-19 (PR head, no fix) the kill switch TRON_AMX_DISABLE=1 recovered +6.8 % TPS at qwen tp4 (4 users/engine, early launch) but +0.3 % at tp2 (2 users, late launch); in runtron (8 users) +8.1 % at tp4, none at tp2. Enumerate EVERYTHING that changes at run time with TRON_AMX_DISABLE=1 in the PR HEAD and FIX builds (amx_attn_iface.hpp: the probe, dispatch, any thread-affinity, any scratch/arena allocation, any per-forward or per-page work, the dense gate, Q packing, tile config, the qk_group reader (still used with kill switch per Note [K VNNI storage]), the store paths (unchanged per the note), any logging/counters). Then list candidate mechanisms by which the kill switch could speed up FPGA decode at tp4 when no dense page is scored, each with the code path and the measurement that would confirm it (e.g. AMX frequency license after any tile instruction: does any tile instruction execute on workers per step? where?). Cite path:line.` },
  { key: 'worker-pending-section', q: `QUESTION 8: The attention WORKERS' per-step work under FPGA decode in FIX vs BASE: the "Attention Pending" section (self_attention.hpp: pending pages = pages this step's tokens are written into; ready pages), what pages/blocks a worker scores, with which reader (dotter/qk_group), the v_star/scaled_v accumulation, the join (run_joins, join_page_ranges, unpack_hw_pass), the hw wait spin, help_drain_gof(4) at the start of the next layer. For a 16-token block that is CONVERTED (VNNI) and fully visible, compare qk_group's instruction count and memory traffic per 16 tokens with the row-major dotter's for 16 tokens (read both kernels: k_vnni.hpp qk_group and the dotter in self_attention.hpp / kernels/dotter*.hpp), including the Q broadcast pattern, masking for partial live counts, and the horizontal reductions. Then: in FIX, which blocks does a worker read via qk_group per step under FPGA decode (only the pending page's converted blocks? the engagement-prefix page? none?). Cite path:line; give instruction/line counts, not timings.` },
]

phase('Read')
const results = await pipeline(
  READERS,
  r => agent(`${CONTEXT}\n\n${r.q}\n\nReturn facts with ids ${r.key}-1, ${r.key}-2, ... Each fact = one claim + path:line evidence. Include a fact for every sub-question, and separate 'the code says' from 'a comment says'.`, { label: `read:${r.key}`, phase: 'Read', schema: FACTS }),
  async (facts, r) => {
    if (!facts) return null
    const lenses = [
      'LENS A (citation check): for every fact, open the cited lines and decide whether the code at those lines really supports the claim. Refute anything where the citation does not show it. Also check the claim against the BASE worktree where the fact compares FIX and BASE.',
      'LENS B (missed path): for every fact, look for OTHER code paths, callers, template branches, #ifdef branches or runtime flags that would make the claim false or incomplete (e.g. another caller of the same function, a different geometry, minibatch grains of 8, EAGLE, shared window saves). Refute or correct where you find one; list what the reader missed.',
    ]
    const votes = await parallel(lenses.map((lens, i) => () => agent(
      `${CONTEXT}\n\nYou are an adversarial verifier. The reader's question was:\n${r.q}\n\nThe reader returned these facts (JSON):\n${JSON.stringify(facts, null, 1)}\n\n${lens}\n\nDefault to 'refuted' or 'corrected' when uncertain; 'confirmed' only when you saw the code yourself. Give path:line evidence for each verdict.`,
      { label: `verify:${r.key}:${i === 0 ? 'cite' : 'missed'}`, phase: 'Verify', schema: VERDICT })))
    return { key: r.key, question: r.q, facts, votes: votes.filter(Boolean) }
  },
)

phase('Synthesize')
const good = results.filter(Boolean)
log(`readers done: ${good.length}/${READERS.length}`)
const synthesis = await agent(`${CONTEXT}\n\nYou are the synthesizer. Below are 8 readers' fact lists with two verifiers' verdicts each. Produce a merged FACT SHEET as plain text (markdown) with these sections: 1) Confirmed facts (both verifiers confirmed, or one confirmed and the other 'unverifiable'), grouped by topic, each with its path:line evidence; 2) Corrected facts (give the corrected statement and the evidence); 3) Refuted claims (and why); 4) Contradictions between readers that you could not resolve (state both and what to check); 5) Open questions (merged, deduplicated). Keep every path:line. Do not add facts of your own without reading the code to confirm them; if you do read, cite. Where a fact matters for the three earlier-report claims (a) (b) (c) in CONTEXT, state the final status of each claim explicitly.\n\nDATA:\n${JSON.stringify(good, null, 1)}`,
  { label: 'synthesize', phase: 'Synthesize', effort: 'high' })
return { synthesis, raw: good }