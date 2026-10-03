export const meta = {
  name: 'pr4596-review-facts-and-names',
  description: 'Verify 10 code facts behind the PR 4596 review answers (readers + refuters) and run a naming panel for 5 identifiers',
  phases: [
    { title: 'Verify', detail: 'one reader per claim, then 2 refuters per surviving claim' },
    { title: 'Names', detail: '3 independent naming proposals, then 2 judges' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const SHA = '04dab92a77'
const CTX = `Repository worktree: ${WT} (tron, branch jhan-attn-path-stats, PR #4596 head ${SHA}).
The working tree may be MID-EDIT by another process. Read the committed version only, with:
  git -C ${WT} show ${SHA}:<repo-relative path> | cat -n
Files: h/tron/models/attn_stats.hpp (the stats header), h/tron/models/self_attention.hpp (hooks),
h/tron/models/model.hpp (forward class, Note [Ready versus pending attention work] near line 1844),
h/tron/scheduler/full.hpp (the scheduler that builds token jobs and listeners), t/t_attn_stats.cpp.
Measured exit reports (read-only): /home/jhan/workspace/intel-AMX/exec/results/attnstats-2026092*/exit-reports.txt
Cite every fact as file:line of the committed version. Do not edit any file. Return raw findings, not prose for a human.`

const CLAIMS = [
  { id: 'C1', text: 'One attention job runs the software attention in two passes: run_attention_job calls run_sections(..., pending=false) over the ready pages, then waits on upstream_kvs_ready, then calls run_sections(..., pending=true) over the pending pages. So the comment "the two attention passes of one forward" for N_PASSES_2 / PASS_READY_0 / PASS_PENDING_1 in attn_stats.hpp is literally true at the job level. Also check: is the word "pass" ALSO used in attn_stats.hpp and self_attention.hpp for FPGA hardware passes (hw_workload.passes, note_fpga_pass, query_passes), i.e. is "pass" overloaded in this header?' },
  { id: 'C2', text: 'attn_stats::path::empty is returned by apply_page_tok only when its dotter loop found relevant_k_tokens == 0. List every condition that makes a K token not relevant (range not visible / not sw_required for the query, sliding window, EAGLE first-token exception, page.count()). The FPGA share of attention is never a per-visit path: the FPGA bit of a token job is set by model_stats::note_fpga_query from hw_plan.by_job (find the caller in model.hpp or self_attention.hpp), and FPGA K tokens are counted per hardware pass by note_fpga_pass. So path_bit(path) has no FPGA case by design.' },
  { id: 'C3', text: 'The per-token path set "none" (index 0 of token_jobs_by_path_set) can only occur for a token job that got no software visit on any attention worker AND no FPGA pass in the forward. In a correct run every token job attends at least to itself (its own K is either in the CPU pending page or on the FPGA card), so "none" should be 0. Check: (a) is there any legitimate token job kind in full.hpp / model.hpp that runs no attention at all (e.g. tokens without attention work, empty listeners, EAGLE draft, prefix-cache hits)? (b) grep the exit reports: is "none" ever nonzero in the measured runs?' },
  { id: 'C4', text: 'The forward class is decode_like iff n_listeners == token_jobs.size() (model.hpp near line 1746). A listener is an entry of in_listener_index: a token whose logits somebody consumes. Verify in h/tron/scheduler/full.hpp how listeners are created per token job: for a prompt chunk only its last token has a listener and only in the final chunk (or does every chunk end get one?), for a decode step every token job has one, for a speculative (EAGLE) verify step every draft token has one. Conclude which non-decode forwards are classified decode_like (a one-token final prompt chunk? a verify step? others?) and which forwards are prompt_or_mixed.' },
  { id: 'C5', text: 'All timers of the stats (T1..T5, fields wall_cycles, busy_cycles, period_cycles, join_wait_cycles) are differences of hardware::system::rdtsc() values, i.e. TSC (time stamp counter) ticks, not a real-time clock. tsc_hz in the summary leaf is hardware::system::get_cpu_freq(). Check in src/system/system.cpp (or h/system/system.hpp) how get_cpu_freq is calibrated and whether the TSC is treated as constant-rate (invariant). So "wall" in wall_cycles means elapsed real time including waits (as opposed to busy time), measured in TSC ticks.' },
  { id: 'C6', text: 'attn_stats::model_stats is constructed for EVERY self_attention state (self_attention.hpp near lines 470-499), with enabled = attn_stats::env_enabled(). So model_stats::on is false whenever TRON_ATTN_STATS is not exactly "1"; the object exists in the off state so the hooks can test one bool; no rows/fpga/path_bits vectors are allocated when off.' },
  { id: 'C7', text: 'In C++, "visit_tally const& tally" and "const visit_tally& tally" declare the same type. Count in h/tron/models/*.hpp (committed version) how many parameter/variable declarations use the east form "T const&" versus the west form "const T&"; report the numbers and which form self_attention.hpp itself uses more.' },
  { id: 'C8', text: 'In stream_hw_joins (self_attention.hpp ~1027-1148) the T5 wait loop (timed into *hw_wait_cycles) ends either when a hardware pass becomes ready OR when the software partials are done (sections_left == 0 with !software_ready). So the wait is not hardware-only, and run_joins names the same accumulator hw_wait_cycles while the row field is join_wait_cycles and the hook is note_hw_wait. List every identifier that names this T5 quantity and its file:line.' },
  { id: 'C9', text: 'The unit test t/t_attn_stats.cpp has "using namespace tron::attn_stats;" at file scope and defines constexpr size_t WORKER_0 = 0 inside an anonymous namespace. If attn_stats.hpp gains "inline constexpr size_t WORKER_0 = 0;" in namespace tron::attn_stats, an unqualified use of WORKER_0 in the test becomes ambiguous (compile error). Confirm from the C++ name lookup rules (using-directive + anonymous namespace at global scope) and list the unqualified WORKER_0 uses in the test with line numbers. Also check t/t_llama_unit.cpp and t/t_amx_dispatch_dtype.cpp for the same hazard (they have scoped using-directives of tron::attn_stats).' },
  { id: 'C10', text: 'model_stats::fpga_bits (attn_stats.hpp) holds one byte per token job, set to BIT_SET_1 by note_fpga_query and tested != BIT_CLEAR_0 in end_forward, where it is mapped to PATH_BIT_FPGA_4. Storing PATH_BIT_FPGA_4 directly in fpga_bits (note_fpga_query writes PATH_BIT_FPGA_4; end_forward starts with set = fpga_bits[job]) is behavior-preserving. Check every reader and writer of fpga_bits (header and tests) to confirm nothing else depends on the value being 1.' },
]

const VERDICT = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    holds: { type: 'boolean' },
    corrected_claim: { type: 'string', description: 'the claim as it should be stated, with file:line citations' },
    evidence: { type: 'array', items: { type: 'string' } },
    extra_facts: { type: 'array', items: { type: 'string' }, description: 'related facts the answer to the reviewer should mention' },
  },
  required: ['id', 'holds', 'corrected_claim', 'evidence', 'extra_facts'],
}
const REFUTE = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
  },
  required: ['id', 'refuted', 'reason', 'evidence'],
}

phase('Verify')
const verified = await pipeline(
  CLAIMS,
  c => agent(`${CTX}\n\nVerify this claim against the code. Read the cited regions AND the surrounding code. Correct anything wrong. Claim ${c.id}: ${c.text}`,
    { label: `read:${c.id}`, phase: 'Verify', schema: VERDICT }),
  async (v, c) => {
    if (!v) return null
    const votes = await parallel([1, 2].map(k => () =>
      agent(`${CTX}\n\nYou are refuter ${k}. Try hard to REFUTE the following statement by reading the code; cite file:line. Default to refuted=true only if you find concrete contrary evidence; a claim you could not check is NOT refuted, say so in reason. Statement ${c.id}: ${v.corrected_claim}\nEvidence given: ${v.evidence.join(' | ')}`,
        { label: `refute${k}:${c.id}`, phase: 'Verify', schema: REFUTE })))
    const refs = votes.filter(Boolean)
    return { ...v, refutations: refs, survives: refs.filter(r => r.refuted).length < 2 }
  },
)

phase('Names')
const NAMING_TASK = `${CTX}

The reviewer (the PR author) asked for alternative names for these identifiers in h/tron/models/attn_stats.hpp. Read the header and the hook sites first so every proposal fits the code and the vocabulary tron already uses (grep the repo for the words you propose). Rules from the project: plain English, exact (no hedging like "_like"), no idioms, C++ guide names constexpr values UPPER_CASE with the value as suffix (N_PATHS_3). Note the FUSE leaf names and the stderr report use the class names (decode_like_totals) and the path names (ready_empty_visits), so a class/path rename changes an external interface; say what changes.

Items:
1. enum class path { empty, avx, amx } -- "which path served one visit". Reviewer: "path is too general". Note the FPGA is NOT a visit path (it is counted per hardware pass and per token job). Propose 3 names for the enum, and say whether "empty" should stay (the Note defines "an empty visit") or change.
2. enum class forward_class { decode_like, prompt_or_mixed } and CLASS_NAMES. Classifier: decode_like iff every token job of the forward has a listener; this also catches a one-token final prompt chunk and a speculative verify step. Reviewer is "not 100% satisfied" with both value names and labels. Propose 3 pairs.
3. inline uint64_t get(std::atomic<uint64_t> const&) -- relaxed load. Siblings will be inc_relaxed(counter, value) and max_relaxed(counter, value). Propose 3 names.
4. The T5 accumulator: local hw_wait_cycles in run_joins, parameter uint64_t* hw_wait_cycles of stream_hw_joins, hook note_hw_wait; the row field is already join_wait_cycles; the wait loop ends when a hardware pass OR the peer workers' software partials become ready. Propose names for the local/parameter and the hook.
5. N_PASSES_2 / PASS_READY_0 / PASS_PENDING_1: index of the ready vs pending software pass of one job; "pass" is also the word for FPGA hardware passes in the same header (query_passes, note_fpga_pass). Reviewer's own alternative: N_PAGE_READY_TYPES_2 / PAGE_READY_0 / PAGE_PENDING_1. Propose 3 alternatives (may include the reviewer's), each avoiding the FPGA-pass collision.

For each candidate give: name(s), one-line rationale, and what else in the repo would have to change (grep counts).`

const PROPOSAL = {
  type: 'object',
  properties: {
    items: { type: 'array', items: { type: 'object', properties: {
      item: { type: 'integer' },
      candidates: { type: 'array', items: { type: 'object', properties: {
        names: { type: 'string' }, rationale: { type: 'string' }, blast_radius: { type: 'string' } },
        required: ['names', 'rationale', 'blast_radius'] } },
    }, required: ['item', 'candidates'] } },
  },
  required: ['items'],
}
const angles = [
  'name things by the exact rule the code applies (what the classifier or the return value literally means)',
  'name things by the vocabulary tron already uses in model.hpp, self_attention.hpp, full.hpp and README.stats.md (grep before proposing)',
  'name things for the reader of the FUSE leaves and the stderr report who has never seen the code',
]
const proposals = (await parallel(angles.map((a, i) => () =>
  agent(`${NAMING_TASK}\n\nYour angle: ${a}.`, { label: `propose:${i + 1}`, phase: 'Names', schema: PROPOSAL })))).filter(Boolean)

const JUDGE = {
  type: 'object',
  properties: {
    items: { type: 'array', items: { type: 'object', properties: {
      item: { type: 'integer' },
      ranked: { type: 'array', items: { type: 'object', properties: {
        names: { type: 'string' }, score: { type: 'number' }, why: { type: 'string' } },
        required: ['names', 'score', 'why'] } },
      keep_current_is_fine: { type: 'boolean' },
    }, required: ['item', 'ranked', 'keep_current_is_fine'] } },
  },
  required: ['items'],
}
const judges = (await parallel([1, 2].map(k => () =>
  agent(`${CTX}\n\nYou are judge ${k}. Below are naming proposals from 3 agents for 5 items (see the task text). Score each distinct candidate 0-10 on: exactness (says what the code does, no hedge), fit with tron vocabulary (verify by grep), plain English for a newcomer, brevity, consistency with sibling names, and cost of the rename (external leaf names count double). Rank the top 3 per item and say if keeping the current name is acceptable.\n\nTask text:\n${NAMING_TASK}\n\nProposals:\n${JSON.stringify(proposals, null, 1)}`,
    { label: `judge:${k}`, phase: 'Names', schema: JUDGE })))).filter(Boolean)

return { verified: verified.filter(Boolean), proposals, judges }