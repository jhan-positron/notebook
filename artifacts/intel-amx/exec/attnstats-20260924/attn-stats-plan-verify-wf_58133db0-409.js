export const meta = {
  name: 'attn-stats-plan-verify',
  description: 'Verify the attention path stats implementation plan against tron main 66c7bb8db1: hook sites, threading, lifetime, cost; judge env var vs build option',
  phases: [
    { title: 'Read', detail: 'one reader per hook site or subsystem, read-only worktree' },
    { title: 'Refute', detail: 'each reader report attacked by a skeptic' },
    { title: 'Judge', detail: 'switch decision + scope' },
    { title: 'Critic', detail: 'what is missing' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const PLAN = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/22924373-d0c3-448c-ba41-f6004346c8e0/scratchpad/plan.md'
const COUNTER = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-new-counters/22924373-d0c3-448c-ba41-f6004346c8e0/scratchpad/counter.txt'

const COMMON = 'You are verifying an implementation plan for tron (the inference program). READ-ONLY: never edit, build, or git-modify anything under ' + WT + ' (a git worktree at origin/main 66c7bb8db1). Do not run cmake/ninja. Use grep/sed/cat to read code. Read the plan first: ' + PLAN + '. The earlier design page text (for context only) is ' + COUNTER + '.\nReport facts with file:line evidence from the worktree. When a plan statement is wrong, say exactly what the code does instead and propose the concrete fix (code shape, not prose). Mark every claim you could not verify as "unverified" and say what would verify it. Return raw data only (no human-facing prose beyond the fields).'

const READ_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' },
      status: { type: 'string', enum: ['holds', 'qualified', 'refuted', 'unverified'] },
      evidence: { type: 'string', description: 'file:line citations from the worktree' },
      correction: { type: 'string', description: 'what the plan must change, if anything' },
    }, required: ['claim', 'status', 'evidence'] } },
    line_map: { type: 'object', additionalProperties: { type: 'string' }, description: 'named hook site -> file:line at 66c7bb8db1' },
    risks: { type: 'array', items: { type: 'string' } },
    code_sketch: { type: 'string', description: 'concrete code for the hook as it should be written, if you have a strong opinion' },
  },
  required: ['topic', 'findings', 'line_map', 'risks'],
}

const READERS = [
  { key: 'H1-H2 apply_page_tok/apply_page_range', prompt: 'Verify plan hooks H1 and H2 in ' + WT + '/h/tron/models/self_attention.hpp: (a) the three return sites of apply_page_tok and that changing the return type from std::pair<int,const token_range*> to a 3-field struct is safe for every caller (grep the whole repo incl. t/ and ingest/); (b) the per-visit tally placement after the apply_page_tok call in apply_page_range, the scratchpad==attention-worker identity, the layer id available there (binding.model_layer), and the pending flag; (c) whether a visit can be AVX with relevant_k_tokens == page::page_size (a full page that failed the dense predicate) so avx_full_page_visits is meaningful; (d) what other code paths score K tokens in software outside apply_page_tok (e.g. heterogeneous geometries, EAGLE, sliding window skip) that the tallies would miss; (e) the existing TRON_PAGE_SHARE_COUNTERS hooks: do the new hooks conflict with them or can both coexist.' },
  { key: 'H3-H4 run_attention_job timers', prompt: 'Verify plan hooks H3 (run_attention_job timers T2/T3/T4, attn_jobs) and H4 (T5 hw join wait) in ' + WT + '/h/tron/models/self_attention.hpp and the callers in ' + WT + '/h/tron/plugins/llama.hpp and ' + WT + '/ingest/src/TronCpp.hs: (a) is run_attention_job the single entry every plugin uses (llama and ingested), and is worker_ix 0 always present per job; (b) where the returned attn_elapsed goes today (llama.hpp:758 and the ingested code) and whether recording it inside run_attention_job double counts anything; (c) T4 "layer period on worker 0 = entry-to-entry": are jobs of one worker strictly in layer order within a forward, per minibatch? If a forward has several minibatches, does worker 0 run layer L for minibatch A then minibatch B? Read llama.hpp run_attention_worker (:747-775) and the TronCpp.hs schedule to state the actual order, and propose how T4 should be defined so it is a per-layer wall clock. (d) where exactly T5 should be measured: stream_hw_joins wait loop (:1083-1097) vs around the stream_hw_joins call in run_joins (:1246); which thread and which worker index is known at each site. (e) rdtsc: hardware::system::rdtsc() cost and whether cycles_to_ns (h/system/system.hpp:267) is safe to call from any thread at report time.' },
  { key: 'H5-H6 FPGA counters', prompt: 'Verify plan hooks H5 (prepare_uniform_hw_attention fpga_k_tokens / query_passes, self_attention.hpp:532-621) and H6 (construct_hw_plan fpga_queries + fpga_bits, model.hpp:2486-2580) in ' + WT + ': (a) which thread runs prepare_uniform_hw_attention (trace model.hpp prepare_attention_job :2065-2075, hw_attention_phase, the llama.hpp and TronCpp.hs callers) and whether two calls for the same layer can run concurrently (so plain vs atomic counters); (b) whether every hw_query in construct_hw_plan becomes exactly one (pass, query) entry per layer in prepare_uniform_hw_attention, or passes are per device/shard group so query_passes > queries; (c) the inclusive-index semantics of relative_hw_tok_ix (tok_ix + 1 = K tokens scored?) with evidence from h/libpos.hpp or the hardware header; (d) whether construct_hw_plan runs once per forward per minibatch on the main thread (model.hpp:2285) and how many times per forward hw_query entries for the same job_ix can be pushed (several entries per job?), so fpga_queries counts distinct token jobs or plan entries; (e) hw_attn_engagement_point value and where it is defined.' },
  { key: 'H7-H8 forward class, fold, T1', prompt: 'Verify plan hooks H7 and H8 in ' + WT + ': (a) model.hpp forward()/run_forward (:1639-1755): the class proxy "listener_notifications.size() == token_jobs.size() means decode-like" -- inspect how token_jobs and listeners are built (full.hpp compute_forward_args, gather_token_job_ids :1760-1790, the comment Every token job must need KV, a listener, or both) and give counter-examples (prefill last chunk of 128 tokens requesting logits only for the last token: token_jobs 128, listeners 1 -> prompt; a decode step with speculative/EAGLE tokens; a 1-token final chunk). Propose the best available class rule and where n_listeners is stored. (b) The fold point after plugin_state.run (:1739): are all attention workers finished by then (Note [Plugin-owned worker launch]) so path_bits can be read and cleared on the main thread? (c) resize(max_tokens) at :1571 grows only; where would per-worker path_bits (in attn_accum) be resized to token_jobs.size() -- is there a per-forward hook in self_attention::state, or does model::state call something on self_attn_state per forward? (d) full.hpp:2090 state.forward(...) call: does it return only after listener delivery (run_listener_notifications enqueued at :1747-1750 and run_logits) so T1 = whole forward including logits; and does the fake scheduler (t/ tests) call the same state.forward? (e) the perfetto "forward" event at model.hpp:1655: its current arguments and whether adding n_listeners is possible (in_listener args available).' },
  { key: 'H9 state lifetime, FUSE, ctor order', prompt: 'Verify plan hook H9 in ' + WT + ': (a) model::state constructor (model.hpp:1280-1305) member init order: is self_attn_state (declared :1084) constructed before or after cfg (find the declaration order of cfg and self_attn_state in struct state), so can the self_attention::state ctor read enclosing_state.cfg.id? If not, propose where to create/register the stats object (e.g. at the end of the model::state ctor body). (b) How many model::state objects exist per loaded model in runtron (src/runtron.cpp) and rinzler (src/rinzler.cpp, completions_controller): one per model, or per context/draft? Where are they destroyed relative to stats::unmount (runtron.cpp:483-506, rinzler.cpp:4403-4806)? Does a FUSE read callback that captures a weak_ptr solve the dangling problem, and does a leaf path collision happen when two states share cfg.id (make_file on an existing path: src/system/fuse_sysfs.cpp:133-160 behavior)? (c) Can leaves be registered after stats::start() (h/system/fuse_stats.hpp Note [FUSE Stats Startup Ordering]) -- expert_stats registers at model load; is model load before or after start() in runtron and rinzler? (d) Which thread runs read callbacks and what value_type a std::string leaf returns; the max string length limit (fuse_sysfs.hpp:58 MAX_STRING_LENGTH) and whether a JSON leaf of by_layer x by_worker size (e.g. 80 layers x 64 workers x ~20 numbers) would exceed it -> propose leaf split. (e) cfg.id values in practice (config.hpp:20) and the expert_stats id safety check.' },
  { key: 'tests and build', prompt: 'Verify the test and build parts of the plan in ' + WT + ': (a) t/t_llama_unit.cpp: how the model/state is constructed for the apply_page_range cases (around :1496-1510 and :2170-2200, :2380-2480), whether the test can reach state.self_attn_state.stats to force on=true, and whether these cases run on a host without AMX (label fake?) -- read t/CMakeLists.txt for t_llama_unit and t_amx_dispatch_dtype registration (MODEL_REQUIREMENTS, LABELS). (b) t/t_tronstats_convention.cpp:161-180 StatsEnvironment: can a new test t_attn_stats reuse the pattern (needs /dev/fuse? does stats::initialize mount, or only start()? evidence from src/system/fuse_sysfs.cpp initialize vs start) and read a leaf value through get_file_handle()->get_value() without a mount. (c) add_catch_test signature and the cost-data rule (t/AGENTS.md, README.ci.md bin/slice bench): what CI job fails when config/test-benchmarks.json lacks the new test (grep .github/workflows and bin/ci for bench --check), and whether adding cases to an existing test avoids it. (d) clang-format config (.clang-format ColumnLimit) and the lint that checks Notes/comments (lint-notes?) that a new header must pass. (e) does any generated code (ingest TronCpp.hs) or the heterogeneous_scheduler_compile test call apply_page_tok/apply_page_range/run_attention_job with positional args that a signature change would break.' },
  { key: 'cost analysis', prompt: 'Cost analysis of the env-var (always compiled) design versus a CMake option, using ' + WT + ' code: (a) count the work per visit today in apply_page_range inner loop and apply_page_tok (self_attention.hpp:1497-1571, 1713-1853): what a visit costs in cycles for (i) a dense AMX page (apply_dense_amx_page, one page = 64 K tokens x 4 heads), (ii) an AVX full page, (iii) an AVX tail page with k relevant tokens, (iv) an empty visit (returns {0, hint} after the range test). Use the 2026-09-01 numbers in the design text (AMX 2.89 us, AVX 3.64 us per unit at prompt 8192) as measured anchors and estimate the empty-visit cost from the code (a few dozen cycles?). (b) The added off-state work: one bool test per visit (if (stats_on)), one 16-byte struct return instead of a pair (apply_page_tok is TRON(inline): is it force-inlined? check h/common/attributes.hpp TRON(inline)), the tally object on the stack for the call. Estimate the relative cost per visit type and the worst-case share for a decode step under CPU attention (visits per step: layers x kv_heads x pages). (c) Which visit type dominates in the p0perf-like A/A shape (llama-3.1-8b, 8 users, prompt 1024, CPU attention): compute visits per decode step and the share of empty visits. (d) State what "obvious perf impact" would look like in the A/A (band from earlier same-binary pairs: the design text mentions the 09-11 band); is a 0.1 % effect detectable? (e) Any hidden cost: code-size/i-cache growth in the hot loop, register pressure in the dotter loop from the live tally, the path_bits byte store per visit when ON (not off). Give a verdict: is an obvious impact plausible when OFF? when ON?' },
  { key: 'reviewer precedent and naming', prompt: 'Precedent and naming check (no code changes): read ' + WT + '/README.stats.md, ' + WT + '/h/tron/models/expert_stats.hpp, ' + WT + '/src/rinzler.cpp:4115-4300 (register_memory_pressure_fuse_stats, register_hbm_shard_pressure_fuse_stats), and grep the repo for getenv("TRON_ (all env vars read by tron: list them with file:line and their on/off rule, e.g. exactly "1" vs nonzero). Then: (a) is TRON_ATTN_STATS a good name against the existing set (any TRON_*_STATS or TRON_STATS_* precedent, any collision), and what rule ("1" only) matches the majority; (b) for casual leaves under /model/<id>/attention/, what marker files (.skip) are required so t_tronstats_convention keeps passing (README.stats.md Mark new grouping directories, src/system/fuse_tronstats.cpp) -- casual (non-exported) leaves: are they walked by the convention test? give evidence; (c) which existing leaves are JSON strings (precedent for a JSON leaf) and any size limits; (d) list the env vars already documented anywhere (README*.md, doc/) so the PR can add TRON_ATTN_STATS where the others are documented (issue #4338 asks for a central document; does one exist?).' },
]

phase('Read')
const reports = await parallel(READERS.map(r => () =>
  agent(COMMON + '\n\nTOPIC: ' + r.key + '\n\n' + r.prompt, { label: 'read:' + r.key.split(' ')[0], phase: 'Read', schema: READ_SCHEMA })))
const good = reports.filter(Boolean)
log(good.length + '/' + READERS.length + ' reader reports')

phase('Refute')
const REFUTE_SCHEMA = {
  type: 'object',
  properties: {
    topic: { type: 'string' },
    verdicts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, reader_status: { type: 'string' },
      refuted: { type: 'boolean' }, reason: { type: 'string' }, evidence: { type: 'string' },
    }, required: ['claim', 'refuted', 'reason'] } },
    missed: { type: 'array', items: { type: 'string' }, description: 'facts the reader should have found' },
  },
  required: ['topic', 'verdicts', 'missed'],
}
const refuted = await parallel(good.map((rep, i) => () =>
  agent(COMMON + '\n\nYou are a skeptic. A reader produced this report on topic "' + rep.topic + '":\n' + JSON.stringify(rep, null, 1) + '\n\nTry to REFUTE each finding by reading the code yourself (same worktree, read-only). Default to refuted=true only when you have file:line evidence that contradicts the reader; otherwise refuted=false. Also list facts relevant to the topic that the reader missed.', { label: 'refute:' + i, phase: 'Refute', schema: REFUTE_SCHEMA })))

phase('Judge')
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    decision: { type: 'string', enum: ['env_var', 'build_option', 'env_var_with_build_option_fallback'] },
    confidence: { type: 'number' },
    reasoning: { type: 'string' },
    acceptance_test: { type: 'string', description: 'the exact measurement and threshold that would flip the decision' },
    scope_changes: { type: 'array', items: { type: 'string' }, description: 'items to drop from or add to the v1 PR' },
    design_changes: { type: 'array', items: { type: 'string' } },
  },
  required: ['decision', 'confidence', 'reasoning', 'acceptance_test', 'scope_changes', 'design_changes'],
}
const bundle = JSON.stringify({ reports: good, refutations: refuted.filter(Boolean) }, null, 1)
const judgePrompts = [
  'LENS: performance engineering. Decide between (1) one environment variable TRON_ATTN_STATS, always compiled, for every counter and timer including the per-visit path tallies, and (2) a CMake option for the per-visit tallies plus the env var for the rest. The user prefers the env var (easier to turn on) unless the off-state cost is OBVIOUS. Weigh the cost analysis report and its refutation. Name the acceptance test precisely (shape, arms, reps, band) and what result flips the decision.',
  'LENS: code review by tron maintainers. Two approving reviewers of the earlier PR #4267 asked for exactly this: FUSE leaves with env-var opt-in (issue #4303). Another reviewer objected earlier to instrumentation "compiled by nobody". Decide env var vs build option from a review-acceptance standpoint: hot-loop hooks in apply_page_range, a return-type change of apply_page_tok, a shared_ptr in the attention state, JSON leaves. List the design changes that make the PR smallest and most reviewable (topical commits, what to defer to a follow-up: per-token path sets? T4? FPGA counters?).',
  'LENS: user of the numbers (the person running AMX-vs-AVX-vs-FPGA campaigns on the CI machine under platformd). Decide which switch serves the campaigns: can a build option even be used under the apt-installed deb that platformd runs? Which leaves and which exit-report lines are needed to answer "how much attention work ran on AVX / AMX / FPGA, per layer and per decode step", and which of the planned rows are unnecessary. Check the plan leaf layout against the MAX_STRING_LENGTH findings.',
]
const judges = await parallel(judgePrompts.map((p, i) => () =>
  agent(COMMON + '\n\nJUDGE ' + (i + 1) + '. ' + p + '\n\nEvidence bundle (reader reports + refutations):\n' + bundle, { label: 'judge:' + (i + 1), phase: 'Judge', schema: JUDGE_SCHEMA, effort: 'xhigh' })))

phase('Critic')
const CRITIC_SCHEMA = { type: 'object', properties: {
  missing: { type: 'array', items: { type: 'string' } },
  contradictions: { type: 'array', items: { type: 'string' } },
  must_fix_before_coding: { type: 'array', items: { type: 'string' } },
  ok_to_code: { type: 'boolean' },
}, required: ['missing', 'contradictions', 'must_fix_before_coding', 'ok_to_code'] }
const critic = await agent(COMMON + '\n\nYou are the completeness critic. Given the plan, the reader reports, refutations and judge verdicts below, list: what the plan still lacks to be implementable without guessing (unverified claims that matter, hook sites without a line number, threading questions left open), contradictions between judges, and the must-fix list before coding starts.\n\n' + bundle + '\n\nJUDGES:\n' + JSON.stringify(judges.filter(Boolean), null, 1), { label: 'critic', phase: 'Critic', schema: CRITIC_SCHEMA, effort: 'xhigh' })

return { reports: good, refutations: refuted.filter(Boolean), judges: judges.filter(Boolean), critic }