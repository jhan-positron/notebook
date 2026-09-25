export const meta = {
  name: 'attn-stats-code-review',
  description: 'Adversarial review of commit 9b3832eb4b (attention path stats behind TRON_ATTN_STATS) in the tron worktree: 6 lenses, 2 refuters per finding, critic',
  phases: [
    { title: 'Find', detail: 'six review lenses over the diff' },
    { title: 'Refute', detail: 'two skeptics per finding' },
    { title: 'Critic', detail: 'coverage of the review itself' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const COMMON = 'You review a commit in tron (the inference program). Worktree: ' + WT + ' on branch jhan-attn-path-stats; the change is `git -C ' + WT + ' diff 66c7bb8db1..HEAD` (commit 9b3832eb4b: new header h/tron/models/attn_stats.hpp, hooks in h/tron/models/self_attention.hpp, h/tron/models/model.hpp, h/tron/scheduler/full.hpp, tests t/t_attn_stats.cpp, t/t_amx_dispatch_dtype.cpp, t/t_llama_unit.cpp, t/CMakeLists.txt, README.stats.md). READ-ONLY: do not edit, build, commit or run cmake/ninja; read with git/grep/sed/cat. The design context: the environment variable TRON_ATTN_STATS (exactly "1") turns per-model attention path statistics on; with it unset the per-visit hooks in apply_page_range must cost one predictable branch on a bool copied once per call and nothing else; rows are per (forward class, attention worker, layer) and written only by the owning worker; FUSE leaves are casual (no markers) and hold a weak_ptr; the exit report prints from the model_stats destructor. Report every finding with file:line in the worktree, the concrete failure scenario (inputs/state -> wrong output, crash, race, or cost), and the concrete fix. Do not report style preferences without a rule behind them. Return raw data only.'

const FIND_SCHEMA = { type: 'object', properties: {
  lens: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', properties: {
    title: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
    severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'] },
    scenario: { type: 'string' }, fix: { type: 'string' }, evidence: { type: 'string' },
  }, required: ['title', 'file', 'line', 'severity', 'scenario', 'fix', 'evidence'] } },
  checked_ok: { type: 'array', items: { type: 'string' }, description: 'things you verified and found correct' },
}, required: ['lens', 'findings', 'checked_ok'] }

const LENSES = [
  { key: 'threading', prompt: 'LENS threading and lifetime: data races between attention workers and the main thread (path_bits, fpga_bits, current_class, t4_* fields, rows), between workers and FUSE read callbacks (relaxed atomics vs plain members read by render_*), destructor order (model_stats destroyed while a FUSE read runs: weak_ptr lock vs the destructor printing), the EAGLE child state sharing cfg.id, states created in tests without stats::initialize, and whether begin_forward/end_forward bracket every path that runs attention workers (model.hpp run_forward; are there other callers of plugin_state.run or attention workers, e.g. speculative/EAGLE paths, that skip begin_forward so path_bits are stale or too short?). Check note_token_path bounds and the fold when n_token_jobs shrinks between forwards.' },
  { key: 'hotloop', prompt: 'LENS hot-loop cost and codegen: read apply_page_range and apply_page_tok in the diff. With stats->on false, what executes per visit and per call? Is stats_tally zeroing hoisted correctly (56+ bytes per call)? Does the page_tok_result struct change register allocation or add stores compared with the pair (apply_page_tok is always_inline)? Is the per-visit `if (stats_on)` block small enough not to hurt i-cache? Is the row add free of lock-prefixed instructions (add_relaxed = load/add/store)? Are there any per-visit atomic operations when ON? Any fetch_add on a per-visit path? Also check run_attention_job: rdtsc only when on? stream_hw_joins: the pointer test per wait-loop entry. Give the instruction-level estimate and name anything that is not O(1) per call.' },
  { key: 'correctness', prompt: 'LENS counting correctness: are the three return sites of apply_page_tok tagged with the right path (an AVX visit that scored zero tokens after the loop returns empty; the AMX return counts page_size K tokens; EAGLE begin=1 pages)? Is the pass index (ready/pending) the apply_page_range `pending` argument? Is the layer index binding.model_layer.i and is it < n_layers for every plugin (heterogeneous/ingested plugins with model_layer ids; the state template parameter n_layers = plugin::n_layers)? Is the worker index the scratchpad argument in every caller of apply_page_range (run_sections and the tests)? T4: verify the operation-change rule against llama.hpp run_attention_worker order and the ingested plugin order (ingest/src/TronCpp.hs), including a forward with one operation only (no period recorded: acceptable?) and the last layer (never recorded: documented?). T2/T3: worker 0 identity across forwards. T5: only the wait loop; run_joins passes the pointer only when join_hw. FPGA: note_fpga_pass per pass per layer (is prepare_uniform_hw_attention called once per (layer, minibatch) per forward, so the per-layer numbers are per forward, not duplicated?); fpga_queries per minibatch from by_job; forward class rule. end_forward path-set fold: are bits of workers beyond n_attn_workers stale? Is token_jobs.size() the right n at both begin and end?' },
  { key: 'fuse', prompt: 'LENS FUSE and reporting: register_fuse_files (paths, read_only, no markers, duplicate registration when a second state of the same id exists: which state do the leaves show, is that documented; EAGLE suffix), render_* JSON validity (quotes, commas, braces, escaping of model_id, empty-rows case when off, the {} returned after expiry), leaf sizes vs fuse_sysfs::MAX_STRING_LENGTH 2048 (compute the worst case of render_layer/render_totals with 20-digit numbers), print_report content and when it prints (destructor thread, spdlog vs fprintf convention in this codebase), README.stats.md accuracy against the code, the spdlog info line, and whether summary reads hardware::system::detail::cpu_frequency_hz legitimately (is detail a public namespace used elsewhere outside system.cpp?).' },
  { key: 'tests', prompt: 'LENS tests: do the new and changed tests encode the intent (a test that cannot fail when the logic changes is wrong)? t/t_attn_stats.cpp: every case, expected numbers, the FUSE environment (stats::initialize without start; mkdtemp; unmount in the destructor even on REQUIRE failure), the assumption that get_value runs the read callback (src/system/fuse_sysfs.cpp:933-955), Catch2 conventions of this repo (t/AGENTS.md, README.testing.md), the fake label and system_init. t/t_amx_dispatch_dtype.cpp: the new assertions against the fakes (packs/dense logic per SECTION), the two added apply_page_range arguments (work_estimate {} and visible), the replaced stats object. t/t_llama_unit.cpp: result.served check, nullptr args. t/CMakeLists.txt registration and config/test-benchmarks.json (missing entry: which CI step fails). What is NOT tested that should be (e.g. the T4 rule against a real llama forward, end_forward clearing, the EAGLE suffix, the off-state no-print rule)?' },
  { key: 'conventions', prompt: 'LENS repository conventions and the user C++ guide: (1) clang-format 19 (.clang-format, ColumnLimit 88) on the touched files; (2) lint-notes: Note [Attention path stats] defined with the ~~~ underline of the exact width, every "See Note [X]" / "Note [X] in file" reference resolves (bin/lint-notes rules); (3) no <cassert> (lefthook no-cassert); (4) named values: the user\'s guide forbids bare numeric and boolean literals in new code (named constants like N_PATHS_3 with the value in the name; true/false passed as arguments must be named constants or /*name=*/ comments) -- list every bare literal on added lines outside constexpr declarations and test constant definitions, by class (call args, loop starts, comparisons, indices); (5) braces on every for/if body on added lines (the user guide) vs the repo idiom; (6) comments in plain English: one claim per sentence, terms defined at first use, no idioms; (7) includes: is <type_traits> included for std::is_trivially_copyable_v, <utility> for std::pair, <cstdio> for fprintf; does attn_stats.hpp compile standalone (include-what-you-use); (8) the Co-Authored-By line and commit message format vs recent tron commits (git log -20 --format=%B).' },
]

phase('Find')
const found = await parallel(LENSES.map(l => () =>
  agent(COMMON + '\n\n' + l.prompt, { label: 'find:' + l.key, phase: 'Find', schema: FIND_SCHEMA })))
const all = found.filter(Boolean).flatMap(r => r.findings.map(f => ({ ...f, lens: r.lens })))
log(all.length + ' findings from ' + found.filter(Boolean).length + ' lenses')

phase('Refute')
const VERDICT = { type: 'object', properties: {
  refuted: { type: 'boolean' }, reason: { type: 'string' }, evidence: { type: 'string' },
  severity_override: { type: 'string', enum: ['blocker', 'major', 'minor', 'note', 'keep'] },
  fix_check: { type: 'string', description: 'is the proposed fix right? give the correct fix if not' },
}, required: ['refuted', 'reason', 'evidence', 'severity_override', 'fix_check'] }
const judged = await parallel(all.map((f, i) => () =>
  parallel([0, 1].map(k => () =>
    agent(COMMON + '\n\nYou are skeptic ' + (k + 1) + '. Try to REFUTE this review finding by reading the code yourself. Default refuted=true only with file:line evidence that the scenario cannot happen or that the code already handles it; otherwise refuted=false. Also judge the proposed fix.\n\nFINDING: ' + JSON.stringify(f, null, 1), { label: 'refute:' + i + ':' + k, phase: 'Refute', schema: VERDICT })))
    .then(vs => ({ finding: f, verdicts: vs.filter(Boolean) }))))
const confirmed = judged.filter(j => j.verdicts.filter(v => !v.refuted).length >= 1 && !(j.verdicts.length === 2 && j.verdicts.every(v => v.refuted)))
const rejected = judged.filter(j => !confirmed.includes(j))
log(confirmed.length + ' confirmed, ' + rejected.length + ' rejected')

phase('Critic')
const CRITIC = { type: 'object', properties: {
  missed_areas: { type: 'array', items: { type: 'string' } },
  must_fix: { type: 'array', items: { type: 'string' } },
  should_fix: { type: 'array', items: { type: 'string' } },
  ok_to_open_draft_pr: { type: 'boolean' },
}, required: ['missed_areas', 'must_fix', 'should_fix', 'ok_to_open_draft_pr'] }
const critic = await agent(COMMON + '\n\nYou are the review critic. Given the confirmed findings (with skeptic verdicts) and the rejected ones, list what the six lenses did not cover, rank the confirmed findings into must-fix before opening a draft PR and should-fix, and say whether a draft PR can be opened now.\n\nCONFIRMED:\n' + JSON.stringify(confirmed, null, 1) + '\n\nREJECTED:\n' + JSON.stringify(rejected.map(r => ({ title: r.finding.title, reasons: r.verdicts.map(v => v.reason) })), null, 1), { label: 'critic', phase: 'Critic', schema: CRITIC, effort: 'xhigh' })

return { confirmed, rejected: rejected.map(r => ({ title: r.finding.title, file: r.finding.file, line: r.finding.line, reasons: r.verdicts.map(v => v.reason) })), critic, checked_ok: found.filter(Boolean).map(r => ({ lens: r.lens, ok: r.checked_ok })) }