export const meta = {
  name: 'wade-round5-verify',
  description: 'Verify Wade\'s four new PR 4596 comments against the code and design the smallest fixes',
  phases: [
    { title: 'Read', detail: 'sweep narration sites; verify W8 duplicate claim; design W9 helper' },
    { title: 'Refute', detail: 'adversarial checks of every proposed edit' },
    { title: 'Judge', detail: 'merge scrub wording; score W9 designs; critic' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const CTX = `
Context (do not re-derive): tron PR #4596 "attention path stats" (env var TRON_ATTN_STATS), branch jhan-attn-path-stats,
worktree ${WT} at head 0f784c44ff, diff base 66c7bb8db1 (git diff 66c7bb8db1..0f784c44ff shows the whole PR: README.stats.md,
h/tron/models/attn_stats.hpp, h/tron/models/model.hpp, h/tron/models/self_attention.hpp, t/CMakeLists.txt, t/assertion_signal.hpp,
t/heterogeneous_scheduler_compile.cpp, t/t_amx_dispatch_dtype.cpp, t/t_attn_stats.cpp, t/t_compute_attention_unit.cpp, t/t_llama_unit.cpp).
Use absolute paths; the shell prints a directory listing on cd in this environment. Read-only: do NOT edit, commit or build anything.
Reviewer Wade (GitHub Wado-posi) posted four new inline comments on 2026-09-30 at head 0f784c44ff:
W6 (h/tron/models/attn_stats.hpp:863): "probably don't want to reference 'PR review round blah comment blah' like this"
W7 (t/t_attn_stats.cpp:306): "same here... seems there are more. Scrub please."
W8 (t/t_attn_stats.cpp:640): "Nit: this case duplicates the next one ("rows keyed by pool worker", line 659), which already checks the same
    mapping (REQUIRE(row == WORKER_2) for split 1, REQUIRE(row == WORKER_1) for split 2) and also checks the outcome that matters: the counts
    land in the rows of the threads that ran the work, and the main-helper row stays zero. This one adds only the arithmetic of a one-line
    function, so it could be dropped."
W9 (h/tron/models/self_attention.hpp:855): "Nit: the pool-worker row key is computed two ways. Here it is the inline pool_worker_ix
    (tp.num_workers() - n_attn_workers + worker_ix, line 797), while run_joins (line 1343) and apply_page_range (line 1485) call
    stats->pool_worker(...). Suggest one helper for all three, so the rows can't drift if the convention changes."
Known facts: pool_worker_ix at self_attention.hpp:797 and the perfetto "app thread id" arg at :1498 are PRE-EXISTING main code (base :761/:1396);
model_stats::pool_worker (attn_stats.hpp:431-435) asserts n_attn_workers <= n_workers and attn_ix < n_attn_workers and returns
n_workers - n_attn_workers + attn_ix, where n_workers = attn.size() (self_attention.hpp:498), and attn is resized to app_pool().num_workers()
at :480 in production; test fixtures may resize attn (t_llama_unit :2614) and rebuild stats. The convention is documented in
Note [Attention workers are the last pool workers] (model.hpp:2253-2275), whose last bullet names model_stats::pool_worker.
The comment-cleanup rule (positron-code-review skill): remove references whose meaning depends on a review exchange (review rounds,
comment labels like W2, "as requested by a reviewer"); keep the technical reason (invariant, ownership rule, failure mode, why the tempting
alternative fails); if the surrounding comment already explains the reason, delete only the historical reference; do not expand a clear
explanation; do not replace narration with a restatement of the code. Commit messages are history and are NOT in scope.
Plain-English rules apply to any proposed comment text: one claim per sentence, no idioms, short sentences.
`

const SITES = {
  type: 'object',
  properties: {
    method: { type: 'string', description: 'how you searched (patterns, files read)' },
    sites: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, line: { type: 'integer' },
      original: { type: 'string', description: 'the exact comment lines (verbatim) that carry the reference, including neighbouring lines needed for the edit' },
      why_narration: { type: 'string' },
      technical_reason_present: { type: 'boolean', description: 'does the surrounding comment already state the technical reason' },
      proposed: { type: 'string', description: 'the exact replacement lines (verbatim, same indentation, <= 84 columns per line); empty string if the whole reference line should be deleted with no replacement' },
    }, required: ['file', 'line', 'original', 'why_narration', 'technical_reason_present', 'proposed'] } },
    not_narration: { type: 'array', items: { type: 'string' }, description: 'candidate hits you judged acceptable to keep, with the reason' },
  },
  required: ['method', 'sites', 'not_narration'],
}

const VERDICT = { type: 'object', properties: {
  holds: { type: 'boolean' }, confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  evidence: { type: 'string' }, corrections: { type: 'string' },
}, required: ['holds', 'confidence', 'evidence', 'corrections'] }

const W8 = { type: 'object', properties: {
  duplicate_claim_holds: { type: 'boolean' },
  what_the_640_case_checks: { type: 'string' },
  what_the_659_case_checks: { type: 'string' },
  what_the_negative_case_checks: { type: 'string', description: 'the pool_worker asserts at t_attn_stats.cpp:431-436' },
  lost_if_dropped: { type: 'string', description: 'any check that no other case keeps (e.g. the off-state call, the identity mapping at full split)' },
  is_lost_coverage_load_bearing: { type: 'boolean' },
  recommendation: { type: 'string' },
  exact_lines_to_delete: { type: 'string', description: 'first and last line numbers of the TEST_CASE block, and any constant that becomes unused' },
}, required: ['duplicate_claim_holds', 'what_the_640_case_checks', 'what_the_659_case_checks', 'what_the_negative_case_checks', 'lost_if_dropped', 'is_lost_coverage_load_bearing', 'recommendation', 'exact_lines_to_delete'] }

const W9 = { type: 'object', properties: {
  formula_sites: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, code: { type: 'string' }, pre_existing_on_main: { type: 'boolean' }, uses_pool_size_from: { type: 'string' } }, required: ['file', 'line', 'code', 'pre_existing_on_main', 'uses_pool_size_from'] } },
  attn_size_equals_num_workers_in_production: { type: 'string', description: 'evidence' },
  fixtures_where_they_differ: { type: 'string' },
  design: { type: 'object', properties: {
    name: { type: 'string' }, summary: { type: 'string' },
    diff: { type: 'string', description: 'unified diff hunks (verbatim code, clang-format style, <= 90 cols) for every file touched' },
    touches_pre_existing_main_lines: { type: 'boolean' },
    off_state_cost: { type: 'string' },
    test_changes: { type: 'string' },
    doc_changes: { type: 'string', description: 'Note/README/comment lines that name the formula or model_stats::pool_worker' },
    risks: { type: 'string' },
  }, required: ['name', 'summary', 'diff', 'touches_pre_existing_main_lines', 'off_state_cost', 'test_changes', 'doc_changes', 'risks'] },
}, required: ['formula_sites', 'attn_size_equals_num_workers_in_production', 'fixtures_where_they_differ', 'design'] }

const SCORE = { type: 'object', properties: {
  scores: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, score: { type: 'integer' }, reasons: { type: 'string' } }, required: ['name', 'score', 'reasons'] } },
  winner: { type: 'string' }, grafts: { type: 'string', description: 'ideas from the runners-up worth keeping' },
  final_diff: { type: 'string', description: 'the diff you would ship (verbatim hunks)' },
}, required: ['scores', 'winner', 'grafts', 'final_diff'] }

// ---------------- Phase 1: readers
const sweepPrompts = [
  `${CTX}\nTASK (sweep A, by grep): find EVERY comment or string in the PR's ADDED lines (git -C ${WT} diff 66c7bb8db1..0f784c44ff) whose meaning depends on a review exchange. Grep the diff's '+' lines case-insensitively for: review, round, comment W, W[1-9], R1-M, reviewer, Wade, cursor (bot), codex, "before the fix", "after the fix", "the fix", "old keying", "old code", "had two writers", "were indexed", "defect", "repro", "reproduce", "prevents", "previous", "used to", "no longer", "asked", "requested", "suggested". For each hit open the file at head and read the whole comment block. Decide per the cleanup rule. Report every site with verbatim original and proposed lines. Also report acceptable hits under not_narration.`,
  `${CTX}\nTASK (sweep B, by reading): do NOT rely on grep. Read every comment block and every TEST_CASE name/description that the PR ADDS, file by file, in: h/tron/models/attn_stats.hpp (the whole file is new), t/t_attn_stats.cpp (whole file new), and the added hunks of self_attention.hpp, model.hpp, README.stats.md, t_llama_unit.cpp, t_amx_dispatch_dtype.cpp, heterogeneous_scheduler_compile.cpp, t_compute_attention_unit.cpp, assertion_signal.hpp (use git -C ${WT} diff 66c7bb8db1..0f784c44ff -- <file> to find the hunks). Flag every sentence whose meaning needs the PR review history (rounds, comment labels, "before/after the fix", "the old keying", "defect 1", "reviewer asked") and propose the replacement per the cleanup rule. Report acceptable history-like references (issue links, design notes) under not_narration.`,
  `${CTX}\nTASK (sweep C, tests only, adversarial to the other sweeps): the test files carry most narration. Read t/t_attn_stats.cpp and the PR hunks of t/t_llama_unit.cpp, t/heterogeneous_scheduler_compile.cpp, t/t_amx_dispatch_dtype.cpp in full. For every TEST_CASE / SECTION name and comment, ask: would a reader who has never seen PR 4596 understand it? Flag names or comments that describe a past bug as "the fix", "before the fix", "the old ...", "defect N", "half record forward_scope prevents", or cite a review round or comment label. Distinguish: (a) must scrub (review-process reference), (b) should reword (history phrasing like "before the fix" that a future reader cannot anchor; reword as a present-tense statement of the failure mode, e.g. "keyed by the attention index instead, both forwards would land in row 0"), (c) keep (a failure mode stated in present tense). Report (a) and (b) as sites with proposed text, (c) under not_narration.`,
]

const w8Prompt = `${CTX}\nTASK: verify W8. Read t/t_attn_stats.cpp lines 400-460 (negative case) and 636-730 (the two pool_worker cases) in ${WT}. Answer the schema exactly: does the "rows keyed by pool worker" case (starting ~:659) already check the same mapping; what does the :640 case check that nothing else does (the off-state call off->pool_worker, the identity mapping at full split N_WORKERS_3, the WORKER_1 result for SPLIT_2); is any of that load-bearing in production (check whether any production caller invokes pool_worker with the switch off: self_attention.hpp :1343 and :1485 are behind stats_enabled). Give the exact line range to delete and whether any constant (N_WORKERS_3, WORKER_2, STATS_OFF_FALSE, SPLIT_1/SPLIT_2 are local) becomes unused (grep counts).`

const w9Designers = [
  { name: 'minimal', angle: 'Surgical: the smallest change that makes all three stats row keys come from one helper. Candidate: run_attention_job passes stats_ref.pool_worker(worker_ix, n_attn_workers) to note_attn_job instead of pool_worker_ix; the speedometer line (pre-existing main code) stays. Say whether the member asserts run in the off state (they must not: the call is inside if (stats_enabled)). Consider whether pool_worker_ix should be computed inside the stats_enabled branch only, and whether the member should be called once and stored in a local (stats_worker) like apply_page_range does.' },
  { name: 'one-formula', angle: 'Root cause: the formula exists at four places (self_attention.hpp :797 speedometer, :1498 perfetto arg, attn_stats.hpp :434, and the Note text in model.hpp :1741/:2258). Design ONE free constexpr function (e.g. attn_stats::attention_pool_worker(n_pool_workers, n_attn_workers, attn_ix) or a better name/place; the header order is attn_stats.hpp < self_attention.hpp < model.hpp, so the function must live in attn_stats.hpp or a header both include, e.g. check whether h/tron/models/common.hpp or h/tron/threading.hpp is included by attn_stats.hpp and self_attention.hpp) used by :797, :1498 and model_stats::pool_worker (which keeps its asserts and passes n_workers). State the cost: two pre-existing main lines change. Provide the diff and the Note/README wording updates.' },
  { name: 'convention-owner', angle: 'Ownership: the convention belongs to Note [Attention workers are the last pool workers] (model.hpp) and the plugin that launches workers (find the launch site: grep -rn "n_attn_workers" h/tron/models/*.hpp src/ | grep -i "run_on\\|spawn\\|worker_ix\\|schedule" ; check h/tron/models/llama*.hpp or wherever attention workers are dispatched). Design the helper next to the owner if header order allows (a static on thread_pool? a free function in h/tron/threading.hpp near app_pool()?), used by every formula site including model_stats::pool_worker. Compare with putting it in attn_stats.hpp. Give the diff for your preferred placement and say honestly whether the extra reach (threading.hpp is included everywhere -> full rebuild) is worth it for a nit.' },
]

phase('Read')
const sweeps = parallel(sweepPrompts.map((p, i) => () => agent(p, { label: `sweep:${'ABC'[i]}`, phase: 'Read', schema: SITES })))
const w8 = agent(w8Prompt, { label: 'read:W8', phase: 'Read', schema: W8 })
const w9 = parallel(w9Designers.map(d => () => agent(`${CTX}\nTASK: design a fix for W9 from this angle: ${d.angle}\nRead self_attention.hpp :780-870, :1320-1350, :1470-1500, attn_stats.hpp :320-345 and :425-445, model.hpp :1735-1750 and :2050-2075 and :2253-2290, t/t_attn_stats.cpp :425-440 and :636-730, t/t_llama_unit.cpp :2220-2245 and :2600-2625 in ${WT}. Name your design "${d.name}". Fill every schema field; the diff must be verbatim code a person can apply.`, { label: `design:${d.name}`, phase: 'Read', schema: W9 })))

const [sweepRes, w8Res, w9Res] = await Promise.all([sweeps, w8, w9])
const sweepList = sweepRes.filter(Boolean)
const designs = w9Res.filter(Boolean)
log(`sweeps: ${sweepList.map(s => s.sites.length).join('/')} sites; designs: ${designs.length}`)

// dedup sites by file+line (nearby lines merge within 3)
const merged = []
for (const s of sweepList) for (const site of s.sites) {
  const hit = merged.find(m => m.file === site.file && Math.abs(m.line - site.line) <= 3)
  if (hit) hit.proposals.push(site); else merged.push({ file: site.file, line: site.line, proposals: [site] })
}
merged.sort((a, b) => a.file.localeCompare(b.file) || a.line - b.line)
log(`merged narration sites: ${merged.length}`)

// ---------------- Phase 2: refute + judge per site (pipeline)
const WORDING = { type: 'object', properties: {
  file: { type: 'string' }, line: { type: 'integer' },
  is_narration: { type: 'boolean', description: 'after re-reading the file, is this really a review-process reference or history phrasing a future reader cannot anchor' },
  original: { type: 'string', description: 'verbatim lines to replace, exactly as in the file at head (copy them with sed -n)' },
  replacement: { type: 'string', description: 'verbatim replacement lines, same indentation, <= 84 columns, plain English; empty if the lines are deleted' },
  technical_reason_kept: { type: 'string', description: 'the invariant / ownership rule / failure mode the new text still states, or "already stated in the surrounding comment"' },
  notes: { type: 'string' },
}, required: ['file', 'line', 'is_narration', 'original', 'replacement', 'technical_reason_kept', 'notes'] }

const wordings = await pipeline(merged,
  m => agent(`${CTX}\nTASK (refute-then-merge, one site): site ${m.file}:${m.line}. ${m.proposals.length} sweep(s) flagged it with these proposals:\n${JSON.stringify(m.proposals, null, 1)}\nRe-read the file at head around the site (sed -n) plus the whole comment block. First try to REFUTE: is it really narration, or a present-tense failure-mode statement that should stay? Then produce ONE final wording that (1) removes every review-process reference and history anchor ("before the fix", "the old keying", "defect 1", round/comment labels), (2) keeps the technical reason in present tense (the invariant, why the tempting alternative fails), (3) does not restate the code, (4) is the smallest edit. The original field must be a verbatim copy of the current lines so it can be applied by exact string replacement; the replacement must keep the comment style (// or /* */), indentation and the 84-column limit (clang-format ColumnLimit: check ${WT}/.clang-format).`, { label: `word:${m.file.split('/').pop()}:${m.line}`, phase: 'Refute', schema: WORDING }),
  (w, m) => parallel([0, 1].map(k => () => agent(`${CTX}\nTASK (verify a proposed comment edit, lens ${k === 0 ? 'meaning: does the replacement still explain the design/failure mode to a reader who never saw the PR; does it drop any technical reason the original had; is it plain English (one claim per sentence, no idioms)' : 'mechanics: does the "original" text match the file verbatim (run grep -nF on each line in ${WT}); does the replacement keep indentation, comment markers, <= 84 columns; does it leave any other review reference in the same comment block or the same TEST_CASE'}):\n${JSON.stringify(w, null, 1)}\nDefault to holds=false if uncertain; put concrete corrections (verbatim) in corrections.`, { label: `verify${k}:${m.file.split('/').pop()}:${m.line}`, phase: 'Refute', schema: VERDICT }))).then(vs => ({ ...w, verdicts: vs.filter(Boolean) })),
)

// W8 refuters
const w8Verdicts = await parallel([0, 1].map(k => () => agent(`${CTX}\nTASK: try to REFUTE this W8 analysis (lens ${k === 0 ? 'coverage: name any assertion in the :640 case that no other case or production path keeps, and say whether it matters' : 'mechanics: confirm the exact line range of the TEST_CASE block to delete at head with sed -n, and grep whether N_WORKERS_3 / WORKER_2 / STATS_OFF_FALSE stay used elsewhere'}):\n${JSON.stringify(w8Res, null, 1)}\nDefault holds=false if uncertain.`, { label: `refute:W8:${k}`, phase: 'Refute', schema: VERDICT })))

// W9 refuters per design
const w9Refuted = await parallel(designs.map(d => () => parallel([
  () => agent(`${CTX}\nTASK: try to REFUTE the correctness of this W9 design (does the diff compile in principle: header order, names, constness, noexcept; does any call run model_stats asserts in the OFF state; does any fixture with attn.size() != app_pool().num_workers() break; does apply_page_range's hoisted stats_worker still equal run_attention_job's row):\n${JSON.stringify(d, null, 1)}\nDefault holds=false if uncertain; give verbatim corrections.`, { label: `refute:W9:${d.design.name}:correct`, phase: 'Refute', schema: VERDICT }),
  () => agent(`${CTX}\nTASK: try to REFUTE the scope/proportion of this W9 design against Wade's nit ("one helper for all three, so the rows can't drift") and the coding rules (surgical: touch only what you must; simplicity first; match conventions). Is it over- or under-engineered? Does it leave two formulas that can drift? Does it touch pre-existing main lines without need?\n${JSON.stringify(d, null, 1)}\nDefault holds=false if uncertain.`, { label: `refute:W9:${d.design.name}:scope`, phase: 'Refute', schema: VERDICT }),
]).then(vs => ({ ...d, verdicts: vs.filter(Boolean) }))))

// ---------------- Phase 3: judges
phase('Judge')
const w9Judges = await parallel([0, 1, 2].map(k => () => agent(`${CTX}\nTASK (judge ${k}: ${['correctness and drift-proofness', 'proportion for a nit + reviewer satisfaction (would Wade accept it as "one helper for all three")', 'maintainer view: which one is easiest to read a year from now, and keeps the Note in model.hpp truthful'][k]}): score each W9 design 1-10 with reasons, pick a winner, graft the best runner-up ideas, and output the final diff you would ship (verbatim hunks, clang-format style). Designs with their refuter verdicts:\n${JSON.stringify(w9Refuted, null, 1)}`, { label: `judge:W9:${k}`, phase: 'Judge', schema: SCORE })))

const critic = await agent(`${CTX}\nTASK (completeness critic): here is everything found so far. Sites to scrub with final wordings and verdicts:\n${JSON.stringify(wordings.filter(Boolean).map(w => ({ file: w.file, line: w.line, is_narration: w.is_narration, original: w.original, replacement: w.replacement, verdicts: w.verdicts.map(v => ({ holds: v.holds, corrections: v.corrections })) })), null, 1)}\nW8: ${JSON.stringify(w8Res)} refuters ${JSON.stringify(w8Verdicts)}\nW9 judges: ${JSON.stringify(w9Judges.filter(Boolean).map(j => ({ winner: j.winner, scores: j.scores })))}\nQuestions: (1) Run your own independent grep over the ADDED lines of git -C ${WT} diff 66c7bb8db1..0f784c44ff for any review reference the sites list misses (also README.stats.md, TEST_CASE names, SECTION names, string literals, spdlog messages). (2) Does any proposed replacement contradict the code at head? (3) Is there a fifth thing Wade would flag in the same spirit that is cheap to fix now (e.g. a comment that names "cursor[bot]" or "the bot", or a test name that says "half record forward_scope prevents")? (4) Do the four fixes interact (e.g. deleting the :640 case shifts line numbers that another edit cites; the W9 diff touches a comment block the scrub edits)? Return plain text: a numbered list of gaps with file:line and the exact fix, then a one-line verdict "ready to implement" or "not ready: <why>".`, { label: 'critic', phase: 'Judge' })

return { sites: wordings.filter(Boolean), w8: { analysis: w8Res, verdicts: w8Verdicts.filter(Boolean) }, w9: { designs: w9Refuted, judges: w9Judges.filter(Boolean) }, not_narration: sweepList.flatMap(s => s.not_narration), critic }