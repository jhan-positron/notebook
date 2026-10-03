export const meta = {
  name: 'tron-review-pr4596',
  description: 'Multi-lens review of tron PR 4596 (attention path stats): find, dedup, adversarially verify, critic, second round, synthesize',
  phases: [
    { title: 'Map', detail: 'test-review table + change map' },
    { title: 'Find', detail: '12 lens finders' },
    { title: 'Dedup', detail: 'merge duplicate findings' },
    { title: 'Verify', detail: '3 refuters per finding (reachability, evidence, intent)' },
    { title: 'Critic', detail: 'what is missing' },
    { title: 'Find2', detail: 'targeted second round' },
    { title: 'Synthesize', detail: 'report data' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const SCRATCH = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/c1e2475d-c671-4e92-9fc3-579c9ced20ea/scratchpad'

const CTX = `
## Review context (facts established by the orchestrator; do not re-derive)

Target: positron-ai/tron pull request #4596 "Attention path stats: AVX / AMX / FPGA shares and timers behind TRON_ATTN_STATS".
- Worktree (READ ONLY, never modify, never checkout, never build): ${WT}
- HEAD = PR head = 04da001cb58ec415808f35fbd52beac7550615ef (branch jhan-attn-path-stats). Cite line numbers of THIS revision (use grep -n / sed -n on the worktree files).
- Base for the diff = merge-base with origin/main = 66c7bb8db1af2d68117d550c2bacb9f66277b279. Full diff saved at ${SCRATCH}/pr4596.diff (3064 lines). Regenerate any part with: git -C ${WT} diff 66c7bb8db1..HEAD -- <path>
- origin/main has moved 161 commits past the base and touches h/tron/models/model.hpp (+99 lines), h/tron/models/self_attention.hpp (11 lines) and t/heterogeneous_scheduler_compile.cpp (2 lines) since 66c7bb8db1. See: git -C ${WT} diff 66c7bb8db1..origin/main -- <path>
- Files changed by the PR: README.stats.md, h/tron/models/attn_stats.hpp (new, 953 lines), h/tron/models/model.hpp, h/tron/models/self_attention.hpp, t/CMakeLists.txt, t/assertion_signal.hpp (new), t/heterogeneous_scheduler_compile.cpp, t/t_amx_dispatch_dtype.cpp, t/t_attn_stats.cpp (new, 932 lines), t/t_compute_attention_unit.cpp, t/t_llama_unit.cpp.
- The live PR body and every review comment (Cursor bot, Wade's 5 comments W1-W5 at head 1430736b2a, jhan's 5 replies naming the fix commits) are saved at ${SCRATCH}/scout-context.txt (sections ----PRBODY, ----REVIEWS, ----COMMENTS). Read it.
- Round-4 commits on top of 1430736b2a: 6e23101744 (W1: T5 covers the software-only join, stretch timer in run_joins), 37bb2a4055 (unit tests for audit gaps), b6fd226982 (W2: forward_scope owns the per-forward record, constructed first in model::state::forward; full.hpp left the PR), ae8a6d38d9 (W3: listener_jobs / kv_only_jobs per class + README sentence), 15f355acb2 (W4: guards became TRON_ASSERT, note_token_path deleted), bff317e0d3 (W5: rows keyed by pool worker, T3/T4 per (class, layer) struct, n_attn_workers min/max recorded), 04da001cb5 (the three job counts of a forward move together).
- Repository conventions: read ${WT}/AGENTS.md and ${WT}/README.stats.md first. The C++ guide of the repo is the one the cpp-coding-guide skill describes; only the C++-guide lens loads that skill.

Terms (tron-code-review skill): tron = inference program; runtron = its CLI; rinzler = production server. Token job = one token's scheduled model work. Forward = one model execution over the scheduled token jobs. A listener receives a token job's output scores. In this PR: decode_like = every token job of the forward has a listener; prompt_or_mixed = at least one job lacks one. FPGA = programmable accelerator; FPGA-assisted attention can include software work (a software join of partials, a pending page served by AVX). Wall time includes waits. T1 = forward wall (TSC cycles), T2 = attention job busy time, T3 = attention job wall as the observer worker sees it, T4 = layer period, T5 = join_wait_cycles. A visit = one apply_page_tok call (query token, KV page of 64 tokens, KV head).

## Output discipline
Your final text is raw data for a program, not a message to a person. Every finding needs: a concrete trigger (inputs/state), the consequence, file:line at HEAD, quoted evidence lines, evidence strength, a discriminating check (what would distinguish correct behavior from the suspected defect), and a suggested fix. Separate current defects from design choices, future risks, test gaps and documentation mismatches. Verify a suspected condition is reachable before calling it a current defect. Do not claim absence of bugs outside the paths you actually read. Never fabricate line numbers: every file:line must come from a grep -n or sed -n you ran.
`

const FINDING_ITEM = {
  type: 'object',
  properties: {
    title: { type: 'string', description: 'short claim, <= 90 chars' },
    category: { type: 'string', enum: ['defect', 'design_choice', 'future_risk', 'test_gap', 'doc_mismatch', 'style'] },
    severity: { type: 'string', enum: ['must_fix', 'should_fix', 'nit', 'info'] },
    trigger: { type: 'string', description: 'concrete inputs / state that reach the condition' },
    consequence: { type: 'string' },
    location: { type: 'string', description: 'file:line at HEAD 04da001cb5, the primary anchor' },
    other_locations: { type: 'array', items: { type: 'string' } },
    evidence: { type: 'string', description: 'quoted code lines with their line numbers' },
    evidence_strength: { type: 'string', enum: ['confirmed_by_code', 'plausible', 'hypothesis'] },
    reachable_in_production: { type: 'string', enum: ['yes', 'no', 'unknown'] },
    discriminating_check: { type: 'string' },
    suggested_fix: { type: 'string' },
    conditions: { type: 'array', items: { type: 'string' }, description: 'conditions this finding concerns: sw_only, fpga_assisted, stats_on, stats_off, pure_batch, mixed_batch, empty, singleton, boundary_shape, eagle, amx_off_kill_switch, ci_lane_no_amx' },
  },
  required: ['title', 'category', 'severity', 'trigger', 'consequence', 'location', 'evidence', 'evidence_strength', 'reachable_in_production', 'discriminating_check', 'suggested_fix', 'conditions'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    findings: { type: 'array', items: FINDING_ITEM },
    conditions_checked: { type: 'array', items: { type: 'string' }, description: 'each: condition -> what you read (file:lines) and the conclusion' },
    conditions_not_checked: { type: 'array', items: { type: 'string' } },
    verified_correct: { type: 'array', items: { type: 'string' }, description: 'things you checked and found correct, with file:line, one per item (these go into the report as positive evidence)' },
  },
  required: ['lens', 'findings', 'conditions_checked', 'conditions_not_checked', 'verified_correct'],
}

const LENSES = [
  { key: 'forward-pass', prompt: `Lens: FORWARD-PASS BOOKKEEPING. Trace every entry point of a forward through completion at HEAD: model::state::forward (h/tron/models/model.hpp) with the forward_scope object from h/tron/models/attn_stats.hpp, run_forward, the callers in h/tron/scheduler/full.hpp and any other caller of state.forward (grep the whole repo: h/, src/, t/), the EAGLE child scheduler, proxy/mock, legacy_dispatch. Check normal exits, early returns, exceptions, interrupted or empty forwards. For each completed pass: exactly one forwards count when stats are on? T1 wall covers the documented start and end (perfetto "forward" slice; logits and listener delivery inside; latch-arena release)? Class decided once from n_listeners == token_jobs.size() and used consistently by token_jobs, listener_jobs, kv_only_jobs, fpga_queries, token_jobs_by_path_set, visits, timers? Can any path count jobs without counting the pass, or attribute timing/visits to the previous forward's class (workers still writing after the scope ends; current_class read by worker threads)? Check the intended treatment of interrupted passes before calling incomplete accounting a defect. Also check the 04da001cb5 commit ("three job counts move together").` },
  { key: 'visit-tallies', prompt: `Lens: VISIT TALLIES AND PATH BITS in the hottest loop. Read apply_page_range / apply_page_tok / page_tok_result and visit_tally in h/tron/models/self_attention.hpp and attn_stats.hpp at HEAD. For each counter (ready/pending x empty/avx/amx visits, k_tokens, avx_full_page_visits, served, relevant_k_tokens): does it count the intended work with clear units? Which code updates it? Can any execution path omit or double-count (mask ranges, several q_batches, the pending page, dense page served by AMX, AVX serving relevant K tokens, kill switch TRON_AMX_DISABLE, CI lane compiled without TRON_AMX_DISPATCH, the empty visit)? Is the per-visit hook really behind the hoisted bool with zero cost when off? Are the per-token-job path bits (token_path_span, path_bits keyed by pool worker after W5) written at the right index (tok_ix.i vs job index; several q_batches per job; helpers)? Check the closed-form identity in the PR body (avx_full_page(kill) == amx + avx_full_page(on)) against the code.` },
  { key: 'timers', prompt: `Lens: TIMERS T2..T5. Read run_attention_job, run_joins, stream_hw_joins, prepare_uniform_hw_attention and the timer hooks (note_attn_job, note_join_wait, layer_timers struct after W5) at HEAD in h/tron/models/self_attention.hpp and attn_stats.hpp. For each timer: rdtsc placement, units (TSC cycles, tsc_hz in summary), what starts/stops it, what happens across minibatches, the last layer of a forward (T4 has no period), which worker is the observer after W5 (pool worker index vs attention worker 0), whether the observer can change between forwards, whether the T5 stretch timer in run_joins can double count with stream_hw_joins in a layer that has both, whether a stretch that ends by exit (no progress then return) is recorded, and whether an rdtsc read happens with the switch off. Check the documented semantics (README.stats.md, the Note [Attention path stats]) against the code.` },
  { key: 'fpga-path', prompt: `Lens: FPGA-ASSISTED ATTENTION PATH. Read every FPGA-related hook at HEAD: note_fpga_pass, note_fpga_query, fpga_at, fpga_bits, the hw_plan / by_job queries in model.hpp (construct_hw_plan), prepare_uniform_hw_attention and stream_hw_joins in self_attention.hpp, and how the FPGA k_tokens / passes are counted per layer and per class. Check: layers with FPGA + software mix (pending page served by AVX in an FPGA layer), FPGA queries per token job vs per pass, the fpga bit in token_jobs_by_path_set, the wait accounting, EAGLE, and whether fpga_queries is written inside the forward_scope lifetime by construct_hw_plan for every path (including rejections / fallbacks to software). Are any FPGA call sites unreachable by unit tests (say so as test gaps, not defects)?` },
  { key: 'async-ownership', prompt: `Lens: ASYNCHRONOUS OWNERSHIP AND CONCURRENCY. Read model_stats lifetime at HEAD: how it is created (self_attention.hpp state ctor around line 496), shared_ptr/weak_ptr, FUSE leaf registration and callbacks (attn_stats.hpp register/leaf functions; the FUSE layer in h/tron/ or src/ that calls them; the "last-wins takeover" rule), the destructor that prints the stderr report, forward_scope construction/destruction order relative to worker threads that may still write rows (with_latch_arena, wait_for_coop_gof, plugin_state.run), the atomics' memory orders, and whether a FUSE reader can observe a torn or mid-fold value (acceptable if documented). Trace allocation, submission, completion, release and cancellation for every asynchronous piece: which owner keeps data alive until completion, which event permits reuse. Flag data races (two threads writing the same non-atomic field, e.g. layer_timers or fpga counters written by several workers), use-after-free of the stats object by a leaf callback after model destruction, and static/thread_local state.` },
  { key: 'worker-layer-index', prompt: `Lens: WORKER AND LAYER INDEXING after W5 (commit bff317e0d3). Read at HEAD how rows and path_bits are keyed by pool worker index, how the attention worker index maps to the pool worker index (num_workers() - n_attn_workers + W or similar; check the real formula in model.hpp / self_attention.hpp / the threading code), where n_attn_workers_min/max per class are recorded (assemble_attention_plan_impl or elsewhere), what active_workers means now, the size of rows (pool size) vs the indices used by every hook (main thread? helpers? worker 0 of the pool?), the per-worker FUSE leaves (<class>_worker_<W>), and the fold in end_forward / forward_scope dtor (does it loop over all pool workers per token job; cost on the main thread). Does every hook index keep the meaning readers expect across forwards when the main/helper split changes between forwards (recommend_n_main_helpers)? Are there off-by-one risks at the split boundary (worker == pool size - n_attn_workers)?` },
  { key: 'off-state-cost', prompt: `Lens: OFF-STATE COST AND HOT-LOOP CODE. With TRON_ATTN_STATS unset the PR must cost nothing measurable. Read every production line the PR adds to h/tron/models/self_attention.hpp and model.hpp at HEAD and classify: executed with the switch off (which ones, in which loop, per visit / per job / per layer / per forward), guarded by a hoisted bool, guarded by a branch on an atomic or on shared_ptr, rdtsc reads with the switch off, extra arguments passed through hot functions (register pressure), page_tok_result growth (16 B), template instantiation growth. Check env_enabled: read once (static), exact "1" rule, warning for other values. Is the stderr report printed only when on? Also check the PR-body objdump claims are consistent with the code (0 lock-prefixed, 0 rdtsc in apply_page_range; 9 rdtsc in run_attention_job) as far as the code allows. Flag any line that runs per visit with the switch off beyond one bool test.` },
  { key: 'tests', prompt: `Lens: TEST MEANINGFULNESS. For every new or changed test at HEAD (t/t_attn_stats.cpp all cases; t/t_llama_unit.cpp changed sections; t/heterogeneous_scheduler_compile.cpp changed/new sections including the software-join T5 section and the HW-join T5 check; t/t_amx_dispatch_dtype.cpp; t/t_compute_attention_unit.cpp; t/assertion_signal.hpp; t/CMakeLists.txt changes) ask: does it call the changed production boundary or only the hook? Does its fake retain the information that could be wrong (destination index, worker index, class)? What deliberate semantic break would make the assertion fail, and which breaks would NOT be caught? Are timing assertions flaky (thread start latency, rdtsc on a loaded host, 20 ms sleeps)? Are the fixtures sized so the W4 asserts hold (worker < pool, layer < n_layers, token_job < n)? Do the abort tests (assertion_signal fork+SIGABRT) work under the CI lanes (nix, sanitizers, -D_GLIBCXX_ASSERTIONS at t/CMakeLists.txt)? Which production paths of the PR have NO test (list them as test_gap findings with the smallest closing test). Read ${SCRATCH.replace(/'/g, '')}/../../../../../../home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/test-gap-register-20260929.md only as a prior list (it predates the round-4 commits); re-check each claim against HEAD.` },
  { key: 'docs-exports', prompt: `Lens: DOCUMENTATION AND EXPORTED VALUES. Compare at HEAD: README.stats.md (the attention section), the Note [Attention path stats] and other comments in attn_stats.hpp, the JSON keys actually rendered (render_summary, render_totals, render_forwards, render_layer, render_worker, print_report), the FUSE leaf names registered, and the live PR body (in ${SCRATCH}/scout-context.txt) including its sample leaves and stderr sample, its "Words used here", its test bullets and its verification list. List every key that the docs name but the code does not render or vice versa, every semantic sentence that the code contradicts (e.g. T3/T4 "on worker 0" after W5, T5 description, active_workers meaning, class rule wording, per-forward class caveat for serving), every stale sample (join_wait_cycles 0, wall_cycles_w0 keys, missing listener_jobs/kv_only_jobs/n_attn_workers keys), and whether a reader could mistake missing collection for no work (e.g. {} vs zeros when off; forwards leaf when off after the 1430736b2a fix). Doc mismatches are doc_mismatch category; a PR-body sentence that overstates a measurement is doc_mismatch with severity by impact.` },
  { key: 'main-drift', prompt: `Lens: MAIN DRIFT AND SEMANTIC CONFLICTS. origin/main moved 161 commits past the base 66c7bb8db1 and changed h/tron/models/model.hpp (+99 lines), h/tron/models/self_attention.hpp and t/heterogeneous_scheduler_compile.cpp. Run git -C ${WT} diff 66c7bb8db1..origin/main -- h/tron/models/model.hpp h/tron/models/self_attention.hpp t/heterogeneous_scheduler_compile.cpp h/tron/scheduler/full.hpp t/t_llama_unit.cpp t/t_amx_dispatch_dtype.cpp t/CMakeLists.txt README.stats.md and git -C ${WT} log --oneline 66c7bb8db1..origin/main -- <those paths>. Then check whether the PR's changes still hold on top of main: new callers of run_joins / stream_hw_joins / apply_page_range / state.forward added on main that the PR's new parameters or forward_scope would miss; textual conflicts (try git -C ${WT} merge-tree --write-tree origin/main HEAD or git merge-tree $(git merge-base origin/main HEAD) origin/main HEAD and read the conflict markers; do NOT check out anything); semantic conflicts (main changed the forward structure, the attention plan, the worker split, the perfetto args, the join loop). Also check t_amx_dispatch_dtype.cpp: the PR body says main's copy does not compile with -DTRON_AMX_DISPATCH=ON and #4557 carries the same fix; verify whether #4557 merged (git log origin/main --grep 4557 or the file's history) and whether the two fixes agree.` },
  { key: 'cpp-guide', prompt: `Lens: C++ GUIDE AND REPO CONVENTIONS. First load the skill: call the Skill tool with skill "cpp-coding-guide". Then review the PR's added C++ at HEAD (attn_stats.hpp in full; the model.hpp and self_attention.hpp hunks; the test files) against that guide and ${WT}/AGENTS.md: named values instead of literals (including 0/1 and true/false as the guide says), header hygiene and includes, naming, const correctness, noncopyable helpers, TRON_ASSERT use, atomics memory-order choices, integer types and narrowing, string formatting of JSON (escaping of model_id; is_safe_model_id), comment style (the repo's Note [..] convention), and test file conventions (Catch2 sections, named constants). Report only concrete guide violations with the guide rule named; style-only items get category style and severity nit unless the guide makes them blocking. Do not report items the repo's own code around the hunk also violates unless the guide is explicit.` },
  { key: 'conditions', prompt: `Lens: CONDITION MATRIX (boundary and mode coverage). Check the PR's behavior under each condition by reading the code at HEAD, and say for each which file:lines you read and the conclusion: (1) software-only attention (USE_HW_ATTN=0) vs FPGA-assisted; (2) stats on vs off; (3) pure prompt batch, pure decode batch, mixed batch (serving); (4) empty forward (0 token jobs) and singleton (1 token job, 1 layer, 1 attention worker, n_attn_workers == pool size, n_attn_workers == 0 if possible); (5) boundary model shapes: n_kv_heads, kv_mul (GQA), head_size, page_size 64, n_layers, models that never call these hooks (MoE, non-llama families, EAGLE draft) so that their leaves read zero or missing; (6) AMX kill switch TRON_AMX_DISABLE=1 and the CI lane compiled without TRON_AMX_DISPATCH; (7) several q_batches / minibatches per attention operation; (8) chunked prefill (one-token final chunk classified decode_like, as the PR body says). Every gap in a condition that the code handles wrongly is a finding; every condition handled right goes into verified_correct with its evidence.` },
]

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reasoning: { type: 'string', description: 'what you read (file:line) and why the finding holds or fails' },
    corrected_location: { type: 'string', description: 'file:line at HEAD if the finding cited the wrong place, else empty' },
    corrected_category: { type: 'string', enum: ['', 'defect', 'design_choice', 'future_risk', 'test_gap', 'doc_mismatch', 'style'] },
    corrected_severity: { type: 'string', enum: ['', 'must_fix', 'should_fix', 'nit', 'info'] },
    corrected_evidence_strength: { type: 'string', enum: ['', 'confirmed_by_code', 'plausible', 'hypothesis'] },
    note_for_report: { type: 'string', description: 'one or two sentences a reader needs (a caveat, a sharper trigger, a better discriminating check)' },
  },
  required: ['refuted', 'confidence', 'reasoning', 'corrected_location', 'corrected_category', 'corrected_severity', 'corrected_evidence_strength', 'note_for_report'],
}

const REFUTE_LENSES = [
  { key: 'reach', text: 'REACHABILITY lens: re-read the production code at HEAD and decide whether the trigger is reachable at all (which caller, which condition, which mode). A finding about an unreachable condition is refuted unless it is explicitly a future_risk or test_gap. Default to refuted=true if you cannot show the path.' },
  { key: 'evidence', text: 'EVIDENCE lens: verify the cited file:line and quoted code exist at HEAD 04da001cb5 exactly as claimed (run grep -n / sed -n yourself). Check the claimed consequence follows from that code (not from an older revision, not from Wade\'s comments about 1430736b2a). Wrong or stale evidence refutes. If the claim is right but the line is wrong, do not refute: fill corrected_location.' },
  { key: 'intent', text: 'INTENT lens: decide whether this is a current defect or an intended, documented design choice (README.stats.md, the Note in attn_stats.hpp, the PR body, jhan\'s replies to Wade in the scout context). A documented, deliberate choice reported as a defect is refuted as a defect (set corrected_category design_choice and refuted=false only if it still deserves a line in the report). Also calibrate severity: must_fix = wrong numbers or crash or race in production; should_fix = wrong under a reachable but uncommon condition, or a test that cannot fail; nit = style/docs.' },
]

const DEDUP_SCHEMA = {
  type: 'object',
  properties: {
    groups: { type: 'array', items: { type: 'object', properties: {
      keep_id: { type: 'string', description: 'id of the finding whose text is the most precise; it represents the group' },
      merged_ids: { type: 'array', items: { type: 'string' }, description: 'ids of true duplicates folded into keep_id (may be empty)' },
      title: { type: 'string', description: 'optional sharper title for the merged finding, else empty' },
    }, required: ['keep_id', 'merged_ids', 'title'] } },
    dropped_as_duplicate_of_seen: { type: 'array', items: { type: 'string' }, description: 'ids that duplicate an already-seen finding from an earlier round' },
  },
  required: ['groups', 'dropped_as_duplicate_of_seen'],
}

function keyOf(f) {
  const file = (f.location || '').split(':')[0].trim()
  const t = (f.title || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
  return file + '|' + t
}

// ---------- Map ----------
phase('Map')
const TEST_TABLE_SCHEMA = {
  type: 'object',
  properties: {
    tests: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, case_or_section: { type: 'string' }, lines: { type: 'string' },
      production_boundary_called: { type: 'string', description: 'the production function(s) it calls, or "hook only"' },
      fake_retains_information: { type: 'string' },
      semantic_break_that_fails_it: { type: 'string' },
      breaks_not_caught: { type: 'string' },
      verdict: { type: 'string', enum: ['meaningful', 'weak', 'cannot_fail', 'flaky_risk'] },
    }, required: ['file', 'case_or_section', 'lines', 'production_boundary_called', 'fake_retains_information', 'semantic_break_that_fails_it', 'breaks_not_caught', 'verdict'] } },
    build_lanes: { type: 'string', description: 'which test binaries include which files, under which compile options (from t/CMakeLists.txt), and which CI lane compiles AMX' },
  },
  required: ['tests', 'build_lanes'],
}
const CHANGE_MAP_SCHEMA = {
  type: 'object',
  properties: {
    hooks: { type: 'array', items: { type: 'object', properties: {
      hook: { type: 'string' }, defined_at: { type: 'string' }, call_sites: { type: 'array', items: { type: 'string' } },
      thread: { type: 'string', description: 'which thread calls it: main, attention worker (pool index), helper, FUSE reader' },
      index_meaning: { type: 'string' }, guarded_by: { type: 'string' },
    }, required: ['hook', 'defined_at', 'call_sites', 'thread', 'index_meaning', 'guarded_by'] } },
    leaves: { type: 'array', items: { type: 'object', properties: { leaf: { type: 'string' }, renderer: { type: 'string' }, keys: { type: 'string' }, off_state_value: { type: 'string' } }, required: ['leaf', 'renderer', 'keys', 'off_state_value'] } },
    forward_sequence: { type: 'string', description: 'ordered list of what happens in model::state::forward at HEAD with line numbers: scope ctor, plan, plugin run, joins, logits, listeners, arena release, scope dtor' },
    worker_index_map: { type: 'string', description: 'the exact formula mapping attention worker index to pool worker index at HEAD, with file:line, and where n_attn_workers is chosen' },
  },
  required: ['hooks', 'leaves', 'forward_sequence', 'worker_index_map'],
}
const mapWork = parallel([
  () => agent(`${CTX}\nTask: build the TEST REVIEW TABLE. Read every test file the PR touches at HEAD (t/t_attn_stats.cpp in full, and the PR hunks of t/t_llama_unit.cpp, t/heterogeneous_scheduler_compile.cpp, t/t_amx_dispatch_dtype.cpp, t/t_compute_attention_unit.cpp, t/assertion_signal.hpp, t/CMakeLists.txt; use the diff file to find the hunks). One row per Catch2 TEST_CASE or SECTION that the PR adds or changes. Be exact about lines.`, { label: 'map:tests', phase: 'Map', schema: TEST_TABLE_SCHEMA }),
  () => agent(`${CTX}\nTask: build the CHANGE MAP: every stats hook of h/tron/models/attn_stats.hpp with its production call sites (grep h/ and src/ for each method name), the thread that calls it, the meaning of its indices, the guard; every FUSE leaf with its renderer, keys and off-state value; the ordered sequence inside model::state::forward at HEAD; the attention-worker to pool-worker formula. Exact file:line for everything.`, { label: 'map:change', phase: 'Map', schema: CHANGE_MAP_SCHEMA }),
])

// ---------- Find round 1 ----------
phase('Find')
const round1 = (await parallel(LENSES.map(l => () =>
  agent(`${CTX}\n${l.prompt}\n\nWork method: read the diff hunks for your lens first, then the surrounding unchanged code (callers, callees, consumers). Quote line numbers from HEAD. Report also what you verified as correct (verified_correct) so the report can state coverage honestly. Aim for completeness over brevity: list every finding you can support, including nits, but mark evidence_strength honestly.`, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS_SCHEMA })
))).filter(Boolean)
log(`round 1: ${round1.length} lenses, ${round1.reduce((n, r) => n + r.findings.length, 0)} raw findings`)

const [testTable, changeMap] = (await mapWork)

// ---------- Dedup (barrier: needs the whole set) ----------
phase('Dedup')
async function dedup(raw, roundLabel, seenList) {
  const items = raw.map((f, i) => ({ id: `${roundLabel}-${i + 1}`, ...f }))
  if (items.length === 0) return []
  const brief = items.map(f => ({ id: f.id, lens: f.lens, title: f.title, category: f.category, severity: f.severity, location: f.location, other_locations: f.other_locations || [], trigger: (f.trigger || '').slice(0, 400), consequence: (f.consequence || '').slice(0, 300) }))
  const res = await agent(`${CTX}\nTask: PLAN THE MERGE OF DUPLICATE FINDINGS. Below are ${items.length} raw findings from independent lens reviewers, abbreviated (id, lens, title, category, severity, location, trigger, consequence). Group findings that describe the same defect at the same code (same root cause). Every id must appear in exactly one group as keep_id or in merged_ids${seenList.length ? ', or in dropped_as_duplicate_of_seen' : ''}. Keep distinct findings distinct even when they touch the same line; only merge true duplicates. Pick as keep_id the one with the most precise trigger and location. Output ONLY the plan (ids), not the findings' text. ${seenList.length ? 'Already-seen findings from an earlier round (drop duplicates of these): ' + JSON.stringify(seenList) : ''}\n\nRAW FINDINGS (abbreviated):\n${JSON.stringify(brief, null, 1)}`, { label: `dedup:${roundLabel}`, phase: 'Dedup', schema: DEDUP_SCHEMA })
  const byId = new Map(items.map(f => [f.id, f]))
  const merged = []
  const used = new Set()
  if (res && res.groups) {
    for (const g of res.groups) {
      const keep = byId.get(g.keep_id)
      if (!keep || used.has(g.keep_id)) continue
      used.add(g.keep_id)
      const dups = (g.merged_ids || []).map(id => byId.get(id)).filter(d => d && !used.has(d.id))
      dups.forEach(d => used.add(d.id))
      const locs = new Set([...(keep.other_locations || []), ...dups.flatMap(d => [d.location, ...(d.other_locations || [])])].filter(Boolean).filter(l => l !== keep.location))
      merged.push({ ...keep, title: g.title || keep.title, other_locations: [...locs], merged_from: [keep.id, ...dups.map(d => d.id)], lenses: [keep.lens, ...dups.map(d => d.lens)],
        extra_evidence: dups.map(d => `[${d.id} ${d.lens}] ${d.evidence}`).join('\n').slice(0, 3000) })
    }
    for (const id of res.dropped_as_duplicate_of_seen || []) used.add(id)
  }
  for (const f of items) if (!used.has(f.id)) merged.push({ ...f, merged_from: [f.id], lenses: [f.lens], extra_evidence: '' })
  log(`dedup ${roundLabel}: ${items.length} -> ${merged.length} (plan groups ${res && res.groups ? res.groups.length : 'none'}, dropped as seen ${res && res.dropped_as_duplicate_of_seen ? res.dropped_as_duplicate_of_seen.length : 0})`)
  return merged.map((f, i) => ({ ...f, id: `${roundLabel}-M${i + 1}` }))
}

// ---------- Verify ----------
async function verify(findings, roundLabel) {
  return pipeline(findings,
    f => parallel(REFUTE_LENSES.map(rl => () =>
      agent(`${CTX}\nTask: ADVERSARIALLY VERIFY one review finding. ${rl.text}\n\nFINDING (JSON):\n${JSON.stringify(f, null, 1)}\n\nRead the code yourself. Set refuted=true only when you can state what the finding gets wrong; set refuted=false when it holds (possibly with corrections). Fill note_for_report with the sharpest one-or-two-sentence caveat or confirmation a reader needs.`, { label: `verify:${rl.key}:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA })
    )).then(votes => {
      const v = votes.filter(Boolean)
      const refutations = v.filter(x => x.refuted).length
      return { ...f, votes: v.map((x, i) => ({ lens: REFUTE_LENSES[i] ? REFUTE_LENSES[i].key : 'unknown', ...x })), refutations, survives: v.length > 0 && refutations < 2 }
    })
  )
}

phase('Verify')
const merged1 = await dedup(round1.flatMap(r => r.findings.map(f => ({ lens: r.lens, ...f }))), 'R1', [])
const verified1 = (await verify(merged1, 'R1')).filter(Boolean)
const seen = new Set(merged1.map(keyOf))
log(`round 1 verified: ${verified1.filter(f => f.survives).length} survive, ${verified1.filter(f => !f.survives).length} refuted`)

// ---------- Critic ----------
phase('Critic')
const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    missing_areas: { type: 'array', items: { type: 'object', properties: { key: { type: 'string' }, prompt: { type: 'string', description: 'a complete finder prompt for this area: what to read (files, functions), what question to answer, what would count as a finding' } }, required: ['key', 'prompt'] }, maxItems: 8 },
    unverified_claims: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['missing_areas', 'unverified_claims', 'notes'],
}
const survivors1 = verified1.filter(f => f.survives)
const critic = await agent(`${CTX}\nTask: COMPLETENESS CRITIC. Round 1 of the review ran ${LENSES.length} lenses (${LENSES.map(l => l.key).join(', ')}). Below are the surviving findings, the refuted findings, the conditions each lens reported as checked / not checked, and the change map. Ask: which execution path, condition, caller, consumer, or claim of the PR body has NOT been read or verified? Which finding is still resting on a hypothesis? Produce up to 8 targeted finder prompts for a second round (each self-contained: files, functions, question, what counts as a finding). Prefer areas with no reader at all over re-reading covered ground.\n\nSURVIVING FINDINGS:\n${JSON.stringify(survivors1.map(f => ({ id: f.id, title: f.title, location: f.location, category: f.category, severity: f.severity })), null, 1)}\n\nREFUTED:\n${JSON.stringify(verified1.filter(f => !f.survives).map(f => ({ id: f.id, title: f.title, location: f.location, why: f.votes.filter(v => v.refuted).map(v => v.reasoning.slice(0, 300)) })), null, 1)}\n\nCONDITIONS BY LENS:\n${JSON.stringify(round1.map(r => ({ lens: r.lens, checked: r.conditions_checked, not_checked: r.conditions_not_checked })), null, 1)}\n\nCHANGE MAP:\n${JSON.stringify(changeMap, null, 1)}`, { label: 'critic', phase: 'Critic', schema: CRITIC_SCHEMA })
log(`critic: ${critic.missing_areas.length} areas for round 2; ${critic.unverified_claims.length} unverified claims`)

// ---------- Find round 2 ----------
phase('Find2')
let verified2 = []
if (critic.missing_areas.length) {
  const seenList = merged1.map(f => `${f.location} :: ${f.title}`)
  const round2 = (await parallel(critic.missing_areas.map(a => () =>
    agent(`${CTX}\nSecond-round targeted lens "${a.key}".\n${a.prompt}\n\nAlready reported (do NOT repeat these; only new findings count):\n${seenList.join('\n')}\n\nAlso re-examine these still-unverified claims if they fall in your area: ${JSON.stringify(critic.unverified_claims)}`, { label: `find2:${a.key}`, phase: 'Find2', schema: FINDINGS_SCHEMA })
  ))).filter(Boolean)
  const fresh = round2.flatMap(r => r.findings.map(f => ({ lens: r.lens, ...f }))).filter(f => !seen.has(keyOf(f)))
  log(`round 2: ${round2.length} lenses, ${fresh.length} fresh raw findings`)
  const merged2 = await dedup(fresh, 'R2', seenList)
  merged2.forEach(f => seen.add(keyOf(f)))
  verified2 = (await verify(merged2, 'R2')).filter(Boolean)
  log(`round 2 verified: ${verified2.filter(f => f.survives).length} survive, ${verified2.filter(f => !f.survives).length} refuted`)
  round1.push(...round2)
}

// ---------- Synthesize ----------
phase('Synthesize')
const all = [...verified1, ...verified2]
const REPORT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approve', 'approve_with_nits', 'request_changes', 'needs_measurement'] },
    short_version: { type: 'array', items: { type: 'string' }, maxItems: 3, description: 'three plain sentences a newcomer can follow' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, title: { type: 'string' }, category: { type: 'string' }, severity: { type: 'string' },
      trigger: { type: 'string' }, consequence: { type: 'string' }, location: { type: 'string' }, other_locations: { type: 'array', items: { type: 'string' } },
      evidence: { type: 'string' }, evidence_strength: { type: 'string' }, discriminating_check: { type: 'string' }, suggested_fix: { type: 'string' },
      verifier_notes: { type: 'string' }, conditions: { type: 'array', items: { type: 'string' } },
    }, required: ['id', 'title', 'category', 'severity', 'trigger', 'consequence', 'location', 'evidence', 'evidence_strength', 'discriminating_check', 'suggested_fix', 'verifier_notes', 'conditions'] } },
    rejected: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, title: { type: 'string' }, location: { type: 'string' }, why_rejected: { type: 'string' } }, required: ['id', 'title', 'location', 'why_rejected'] } },
    conditions: { type: 'array', items: { type: 'object', properties: { condition: { type: 'string' }, status: { type: 'string', enum: ['checked_by_reading', 'not_checked', 'test_run_needed'] }, evidence: { type: 'string' }, result: { type: 'string' } }, required: ['condition', 'status', 'evidence', 'result'] } },
    verified_correct: { type: 'array', items: { type: 'string' } },
    counter_audit: { type: 'array', items: { type: 'object', properties: { counter: { type: 'string' }, counts_intended_work: { type: 'string' }, updated_by: { type: 'string' }, owner_init_reset: { type: 'string' }, omit_or_double_count_risk: { type: 'string' }, verdict: { type: 'string' } }, required: ['counter', 'counts_intended_work', 'updated_by', 'owner_init_reset', 'omit_or_double_count_risk', 'verdict'] } },
    proposed_tests: { type: 'array', items: { type: 'string' } },
    open_questions_for_author: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'short_version', 'findings', 'rejected', 'conditions', 'verified_correct', 'counter_audit', 'proposed_tests', 'open_questions_for_author'],
}
const report = await agent(`${CTX}\nTask: SYNTHESIZE THE REVIEW REPORT DATA for PR 4596 at HEAD 04da001cb5. Inputs below: verified findings (each with three refuter votes; survives=true means at most one refuter refuted it), the per-lens condition coverage and verified_correct lists, the change map and the test table. Rules: (1) keep every surviving finding, apply the refuters' corrections (location, category, severity, evidence strength) when two of three agree or when the evidence refuter corrected the line; fold the refuters' note_for_report into verifier_notes; (2) list every non-surviving finding under rejected with the refuters' reason in one sentence; (3) order findings must_fix > should_fix > nit > info, defects before design choices before future risks before test gaps before doc mismatches before style; (4) build the condition table from the lens reports (a condition is checked_by_reading only if some lens names the file:lines it read); (5) build the counter_audit table: one row per exported counter or timer (visits by path and readiness, k_tokens, served, token_jobs, listener_jobs, kv_only_jobs, fpga_queries, token_jobs_by_path_set, forwards, T1..T5, fpga_k_tokens, fpga passes, n_attn_workers min/max, active_workers) with the skill's questions answered from the inputs; (6) propose tests that exercise the untested production paths through the model entry point; (7) verdict: request_changes only if a must_fix defect survives; approve_with_nits if only should_fix/nit items; (8) short_version: three sentences, plain English, define every term at first use, numbers with units. Do not invent anything not in the inputs; where the inputs disagree, say so in verifier_notes.\n\nVERIFIED FINDINGS:\n${JSON.stringify(all, null, 1)}\n\nLENS COVERAGE:\n${JSON.stringify(round1.map(r => ({ lens: r.lens, checked: r.conditions_checked, not_checked: r.conditions_not_checked, verified_correct: r.verified_correct })), null, 1)}\n\nCHANGE MAP:\n${JSON.stringify(changeMap, null, 1)}\n\nTEST TABLE:\n${JSON.stringify(testTable, null, 1)}`, { label: 'synthesize', phase: 'Synthesize', schema: REPORT_SCHEMA })

return { report, testTable, changeMap, critic, verified: all.map(f => ({ id: f.id, title: f.title, location: f.location, survives: f.survives, refutations: f.refutations, votes: f.votes })), lensCoverage: round1.map(r => ({ lens: r.lens, checked: r.conditions_checked, not_checked: r.conditions_not_checked, verified_correct: r.verified_correct })) }
