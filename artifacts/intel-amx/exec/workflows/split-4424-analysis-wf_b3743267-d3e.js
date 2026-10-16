export const meta = {
  name: 'split-4424-analysis',
  description: 'Classify every hunk of PR 4424 into concerns, verify the candidate PR seams adversarially, then run a planning panel',
  phases: [
    { title: 'Classify', detail: 'one agent per file group labels every hunk by concern with line counts' },
    { title: 'Seams', detail: 'verify each candidate cut for compile-level dependencies, 2 refuters each' },
    { title: 'Plan', detail: 'three planners + one judge' },
  ],
}

const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/8147fd4d-377d-40bd-ae3a-3103383074b7/scratchpad'
const W = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'

const CONCERNS = `
Concern codes (label every added/removed line of every hunk with exactly one):
- L = "K VNNI layout, storage, views, and the minimal per-row store": h/tron/tensor/k_vnni.hpp types (k_vnni_tensor, k_vnni_view, the index map, store_row/load_row, copy_token, k_source_row/k_destination_row, detail::k_vnni_access), kv_cache_fwd.hpp declarations, kv_cache.hpp integration (kv_block::k conditional owner, page::k_packed, set_k_row/get_k_row, page::k() constrained to row-major slots, copy_storage_slot via rows, Note [K VNNI storage]), k_vnni::layout_on, the CMake option TRON_K_VNNI and its tron_model_compile_config definition, model.hpp's per-row K store into the plane (set_k_row from the bf16 row), the tests of all of that.
- R = "AVX-512 software reader of the layout": h/tron/kernels/k_vnni.hpp (qk_group), the self_attention.hpp software-loop changes that build the live mask and call qk_group, the attn_stats.hpp comment, the reader tests (reader-vs-dotter envelope, fp16/float/bf16 query, wide groups).
- G = "FPGA/GOF staging": gof.hpp k_head_fn signature + comment, gof.cpp k_scratch, full.hpp k_head_fn lambda, the lambda signature updates in t_gof_dma.cpp, t_gof_staging_leaks.cpp, t_phase1_integration.cpp.
- A = "AMX dense kernel on the VNNI plane": amx_attn.cpp (pack_q_rows_128x4, qk_vnni_128x4, tile constants), amx_attn_iface.hpp declarations + Note text, self_attention.hpp packed_amx_query if-constexpr (pack_q_rows vs pack_q_group) and apply_dense_amx_page if-constexpr (qk_vnni vs qk_rowmajor) and their comments, t_amx_numerics.cpp bit-identity case, t_amx_dispatch_dtype.cpp fakes and cases for the new entry points.
- S = "shared block save": the 16-token block store (store_block, the 16x16 transpose) in h/tron/tensor/k_vnni.hpp, page::set_k_block, model.hpp save_k work units / window / worker_ix / n_workers / Note [Shared block save] / save_k_impl main-vs-helper branches, common.hpp k_store_window_t, ingest/src/TronCpp.hs and ingest/test/LoopyTronSpec.hs, the t_llama_unit save_k three-thread test, t_k_vnni_layout store_block tests.
- T = "row-major tail block + hardware-attention policy" = the content PR 4737 brought in (reference diff ${S}/ref/T-4737-merge.diff): k_rows_saved_ / k_vnni_blocks_ bitmaps, note_k_row_saved / note_k_block_saved, k_state_ix, pending_k_blocks / convert_pending_k_blocks, block_to_vnni / block_to_rows / store_row_major / load_row_major, row_major_row / k_row_if_row_major, k_forget_row, the dense gate k_layout_dense (BLOCKS_PER_PAGE_MASK_0XF, block_bit, offset_bit), dotter scoring of tail rows in the software loop, Note [Row-major tail block], Note [Row-major blocks under hardware attention], cached_operation_uses_hw policy, the tests of all of that.
- B = "build, CI, preset, cost rows, README": CMakePresets.json deb line, .github/workflows/cmake-single-platform.yml flag, README.ci.md, config/test-benchmarks.json rows, t/CMakeLists.txt add_catch_test registration.
When a hunk mixes concerns, split it into parts by line ranges and count each part. A comment-only edit of a line main already had goes to the concern the comment describes. Count with a script (grep/awk over the per-file diff), never by eye.`

const FILE_GROUPS = [
  { key: 'kv_cache', files: ['h/tron/models/kv_cache.hpp'] },
  { key: 'model+common+ingest', files: ['h/tron/models/model.hpp', 'h/tron/models/common.hpp', 'ingest/src/TronCpp.hs', 'ingest/test/LoopyTronSpec.hs'] },
  { key: 'tensor+fwd+reader', files: ['h/tron/tensor/k_vnni.hpp', 'h/tron/tensor/kv_cache_fwd.hpp', 'h/tron/kernels/k_vnni.hpp'] },
  { key: 'self_attention+amx', files: ['h/tron/models/self_attention.hpp', 'src/tron/kernels/amx_attn.cpp', 'h/tron/kernels/amx_attn_iface.hpp', 'h/tron/models/attn_stats.hpp'] },
  { key: 't_k_vnni_layout', files: ['t/t_k_vnni_layout.cpp'] },
  { key: 't_llama_unit', files: ['t/t_llama_unit.cpp'] },
  { key: 'amx-tests+gof', files: ['t/t_amx_numerics.cpp', 't/t_amx_dispatch_dtype.cpp', 't/t_gof_dma.cpp', 't/t_gof_staging_leaks.cpp', 't/t_phase1_integration.cpp', 'h/tron/gof.hpp', 'src/tron/gof.cpp', 'h/tron/scheduler/full.hpp'] },
  { key: 'build', files: ['CMakeLists.txt', 'src/tron/CMakeLists.txt', 't/CMakeLists.txt', 'CMakePresets.json', '.github/workflows/cmake-single-platform.yml', 'README.ci.md', 'config/test-benchmarks.json'] },
]

const PART = {
  type: 'object',
  properties: {
    concern: { type: 'string', enum: ['L', 'R', 'G', 'A', 'S', 'T', 'B'] },
    added: { type: 'integer' },
    removed: { type: 'integer' },
    what: { type: 'string' },
    symbols_defined: { type: 'array', items: { type: 'string' } },
    uses_from_other_concerns: { type: 'array', items: { type: 'object', properties: { symbol: { type: 'string' }, concern: { type: 'string' } }, required: ['symbol', 'concern'] } },
    split_note: { type: 'string', description: 'what must change for this part to live in a PR without the other concerns it references; empty if nothing' },
  },
  required: ['concern', 'added', 'removed', 'what'],
}
const CLASSIFY = {
  type: 'object',
  properties: {
    files: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' },
      hunks: { type: 'array', items: { type: 'object', properties: {
        index: { type: 'integer' }, header: { type: 'string' }, added: { type: 'integer' }, removed: { type: 'integer' },
        parts: { type: 'array', items: PART },
      }, required: ['index', 'header', 'added', 'removed', 'parts'] } },
      test_cases: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, concern: { type: 'string' }, added_lines: { type: 'integer' }, note: { type: 'string' } }, required: ['name', 'concern'] } },
    }, required: ['file', 'hunks'] } },
    notes: { type: 'string' },
  },
  required: ['files', 'notes'],
}

const classifyPrompt = (g) => `You classify the hunks of PR 4424 (positron-ai/tron, "VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save") for a plan that may split the PR into a stack of smaller PRs. Read-only task: do NOT modify any file or run any git command that writes.

Inputs:
- Per-file diffs (base be0d5565b3 = merge base with main, head 0a5334ccb6): ${S}/diff/<path with / replaced by _>.diff . Full diff: ${S}/diff/full.diff .
- The head tree for context: ${W} (checked out at 0a5334ccb6). The base tree for a file: \`git -C ${W} show be0d5565b3:<path>\`.
- Reference diffs of the historical seams: ${S}/ref/T-4737-merge.diff (everything PR 4737 added = concern T), ${S}/ref/S-4774-fold.diff (the save_k worker fold, part of S), ${S}/ref/S-orig-striping-0b54..804a.diff (the original shared block save commits, pre typed port, = concern S), ${S}/ref/L-orig-first-commit-0ec355b641.diff (the original layout commit: L+R+G+A before S and T existed), ${S}/ref/P-typed-port-66c2..154d.diff (the typed-owner port, concern L mostly).
${CONCERNS}

Your files: ${g.files.join(', ')}.
For EVERY hunk of every file: give its index (1-based in file order), the @@ header line, total added and removed lines (count '^+[^+]' and '^-[^-]' lines of that hunk with awk), and its parts by concern with counts that sum to the hunk totals. For each part name the symbols it defines and every symbol it uses that another concern defines (e.g. a line in an L hunk calling note_k_row_saved uses T; a self_attention hunk calling qk_vnni_128x4 uses A; model.hpp save_k calling set_k_block uses S). Write a split_note where separating the part would need new or different code (for example: "without A the dense AMX branch must be gated off for VNNI slots with if constexpr (!layout_on)"; "without S and T, save_k needs the per-row set_k_row loop of the first commit"). For test files list the TEST_CASE / SECTION names added or changed and the concern each one exercises (a case that exercises two concerns gets both, with a note on whether it can be cut by SECTION).
Be exact and exhaustive: every hunk, every line counted. Return the structured result; in notes, state anything that surprised you (e.g. a hunk you could not attribute, or code that two concerns share).`

phase('Classify')
const classified = (await parallel(FILE_GROUPS.map(g => () => agent(classifyPrompt(g), { label: `classify:${g.key}`, phase: 'Classify', schema: CLASSIFY })))).filter(Boolean)
log(`classified ${classified.length}/${FILE_GROUPS.length} groups`)

// Totals per concern (plain code).
const totals = {}
for (const r of classified) for (const f of r.files) for (const h of f.hunks) for (const p of h.parts) {
  totals[p.concern] = totals[p.concern] || { added: 0, removed: 0 }
  totals[p.concern].added += p.added; totals[p.concern].removed += p.removed
}
log('totals per concern: ' + JSON.stringify(totals))
const partitionJson = JSON.stringify(classified)

const VERDICT = {
  type: 'object',
  properties: {
    claim: { type: 'string' },
    holds: { type: 'boolean' },
    evidence: { type: 'array', items: { type: 'string' }, description: 'file:line facts, symbol lists, counts' },
    required_changes: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, change: { type: 'string' }, est_lines: { type: 'integer' } }, required: ['file', 'change'] } },
    risks: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['claim', 'holds', 'evidence', 'required_changes', 'risks', 'summary'],
}

const SEAM_CLAIMS = [
  { key: 'A-off', claim: 'PR-1 = concerns L+R+G+B (the VNNI K layout, its AVX-512 reader, the FPGA staging path, build/CI) compiles and its tests pass WITHOUT concern A (the AMX dense kernel on the VNNI plane) and without S and T, with TRON_K_VNNI ON and OFF and TRON_AMX_DISPATCH ON and OFF. List every symbol L/R/G hunks use that only A defines, say what temporary code PR-1 needs (e.g. gating the dense AMX page path off for VNNI slots so page::k() is never instantiated for them), whether the CMake FATAL_ERROR "TRON_K_VNNI requires TRON_AMX_DISPATCH" can be dropped (kernels/k_vnni.hpp uses _mm512_dpbf16_ps; src/tron/CMakeLists.txt:285 gives the tron target -mavx512bf16 PUBLIC), and whether the kill-switch and attn_stats semantics still hold.' },
  { key: 'S-off', claim: 'Concern S (the shared block save) can be removed from PR-1 and shipped as its own later PR: without S, model.hpp save_k stores each K row of a VNNI slot with the per-row path (set_k_row / store_row), the Haskell files (TronCpp.hs, LoopyTronSpec.hs) and common.hpp k_store_window_t are untouched by PR-1, and no L/R/G/A code references set_k_block, store_block, k_store_window or worker_ix. Describe the minimal PR-1 save_k (compare the head\'s save_k_impl with the first commit\'s save_k in ${S}/ref/L-orig-first-commit-0ec355b641.diff and the typed port) and estimate its size. Also say what S depends on (L only? T?).' },
  { key: 'T-off', claim: 'Concern T (row-major tail block + hardware-attention policy, the PR 4737 content) is cleanly removable: the head 0a5334ccb6 equals the tested commit ba69cb513e plus the 4737 merge 9d5c7a389b plus the preset commit, so a stack PR-1..3 without T is the tree of ba69cb513e (built and tested on 3bda 2026-10-08) and T becomes the last PR. Verify with git (git -C ${W} diff ba69cb513e 0a5334ccb6 --stat; is every non-preset change in 0a5334ccb6 vs ba69cb513e inside ${S}/ref/T-4737-merge.diff?). Then list what T depends on: A (the dense gate k_layout_dense), S (note_k_row_saved inside the shared-window store, note_k_block_saved), R (dotter scoring of tail rows in the software loop), G (k_row_if_row_major in full.hpp). Could T merge before S or before A, and what would change?' },
  { key: 'A-deps', claim: 'Concern A (amx_attn.cpp pack_q_rows_128x4 + qk_vnni_128x4, amx_attn_iface.hpp, the two if-constexpr dispatch sites in self_attention.hpp, t_amx_numerics bit-identity case, t_amx_dispatch_dtype fakes) depends only on L (k_vnni_view, page::k_packed, detail::k_vnni_access, the k_vnni constants) and on main\'s existing AMX dispatch, not on S or T, so it can be the second PR of the stack right after PR-1; and t_amx_dispatch_dtype in A does not need T\'s "record rows like save_k" change if T is not yet present. List every symbol A hunks use and which concern defines it.' },
  { key: 'tests', claim: 'The test additions partition by concern: every TEST_CASE/SECTION added in t/t_k_vnni_layout.cpp and t/t_llama_unit.cpp exercises exactly one of L, R, S, T (or can be cut at SECTION boundaries), so each stack PR can carry only its own tests and still compile without the later PRs\' symbols. List the cases that reference symbols of two concerns (e.g. a save_k case that calls convert_pending_k_blocks or checks k_vnni_blocks) and how to cut them; give the resulting test line counts per PR.' },
]

const seamPrompt = (c) => `Verify or refute this claim about splitting PR 4424 (positron-ai/tron, head 0a5334ccb6, base be0d5565b3) into a PR stack. Read-only: do NOT modify files or run writing git commands.
CLAIM: ${c.claim}
Inputs: hunk classification by concern (JSON, from the previous phase): ${partitionJson}
${CONCERNS}
Diffs: ${S}/diff/ (per file) and ${S}/diff/full.diff; reference diffs ${S}/ref/; head tree ${W}; base file = git -C ${W} show be0d5565b3:<path>; any commit = git -C ${W} show <sha>:<path>.
Method: grep the head tree and the diffs for the symbols; read the surrounding code; for compile questions reason about template instantiation (if constexpr discarded branches still need declared names; a constrained call in a non-dependent decltype is a hard error). Give evidence as file:line facts. Where the claim needs extra code to hold, list the required changes with an estimated line count. Decide holds=true only if the claim holds as stated or with small, clearly listed changes; otherwise holds=false and say why.`

const refutePrompt = (c, v) => `Adversarially refute this verdict about splitting PR 4424 (head 0a5334ccb6 in ${W}, read-only). Default to refuted=true if the verdict's evidence is missing, wrong or incomplete.
CLAIM: ${c.claim}
VERDICT: ${JSON.stringify(v)}
${CONCERNS}
Diffs: ${S}/diff/, references ${S}/ref/. Check each evidence line against the files (grep, read). Look especially for: symbols the verdict missed (grep the head for every function/type the claim names and every caller), compile breaks from discarded if-constexpr branches or decltype, a test that the verdict would leave referencing a later PR's symbol, a CMake or Haskell dependency, and a wrong line estimate (recount with a script). Return refuted (boolean), reasons (list of concrete file:line facts), and corrections (what the verdict should say instead).`
const REFUTE = { type: 'object', properties: { refuted: { type: 'boolean' }, reasons: { type: 'array', items: { type: 'string' } }, corrections: { type: 'array', items: { type: 'string' } } }, required: ['refuted', 'reasons', 'corrections'] }

const seams = await pipeline(SEAM_CLAIMS,
  c => agent(seamPrompt(c), { label: `seam:${c.key}`, phase: 'Seams', schema: VERDICT }),
  (v, c) => v ? parallel([0, 1].map(i => () => agent(refutePrompt(c, v) + `\n(refuter ${i + 1} of 2: refuter 1 focuses on compile-level symbol dependencies, refuter 2 on tests, CMake, Haskell and line counts)`, { label: `refute:${c.key}:${i + 1}`, phase: 'Seams', schema: REFUTE })))
    .then(rs => ({ key: c.key, claim: c.claim, verdict: v, refutations: rs.filter(Boolean) })) : null)
const seamResults = seams.filter(Boolean)
log('seams done: ' + seamResults.map(s => `${s.key}: holds=${s.verdict.holds}, refuted=${s.refutations.map(r => r.refuted).join('/')}`).join('; '))

phase('Plan')
const FACTS = `Facts you must use (verified today 2026-10-09, UTC):
- PR 4424: draft, base main, head 0a5334ccb6, 29 files +4054/-198, MERGEABLE; reviewer Ben (bgamari) asked on 2026-09-21 for a typed VNNI tensor (done: PR 4557 on main + the typed port) and for folding save_k_helper into save_k(worker_ix) (done: PR 4774 merged in). No reviewer has asked for a split; the author (jhan) judges the PR too big for manual review.
- History already contains the seams: 6b939d25d2 = layout + reader + staging + AMX kernel + shared save (save_k_helper form), 2694+/189- (3bda chain green 2026-10-08); 45e6bb266d/ba69cb513e = + save_k worker fold (91/91); 9d5c7a389b = + PR 4737 tail block & policy (1459+/113-); 0a5334ccb6 = + deb preset line (7/2). PR 4737 and PR 4774 were separate stacked PRs, each built and tested on 3bda, before being merged into 4424 on 2026-10-08.
- AGENTS.md: in a PR stack only the PR based on main may be ready for review; every descendant stays draft; after the parent merges, promote only the next PR.
- Build facts: the tron target has -mavx512bf16 PUBLIC (src/tron/CMakeLists.txt:285), so the AVX-512 reader needs no AMX flags; only amx_attn.cpp gets -mamx-*; CMake currently FATAL_ERRORs TRON_K_VNNI without TRON_AMX_DISPATCH (policy, not a code need). origin/main is 165 commits past the merge base (TronCpp.hs changed by 442 lines on main; t_llama_unit +122).
- Measured benefits by concern (qwen3-4b tp2 8 users unless said): layout + AVX reader alone (kill-switch arm "vnnioff" vs row-major AVX "off", 2026-09-14, old base): TPS +5.2/+3.7/+4.2 % at prompt 1024/2048/8192, TTFT -0.1/-1.4/-2.4 %; the AMX kernel on the plane (vnni vs canonical AMX base): TPS +6.1/+7.1/+10.4 % at tp2, TTFT +2.2/0.0/-1.8 % (the TTFT cost = per-token scatter store, +7.8 % at tp4 prompt 1024); shared block save: TTFT -128 ms tp2 / -254 ms tp4 at prompt 1024 vs the scatter store (2026-09-15), TPS unchanged; tail block + policy (PR 4737): qwen FPGA-attention decode loss -3.8/-11.8 % -> within noise (-0.9/-0.4 %, 2026-10-09 whole-machine), tokens identical to main under CPU attention. Final stack vs main (2026-10-09, 14 nightly configs): llama-8b 32u@4096 +4.8 % TPS, qwen sw-attention 8k +7.6 %, llama-3b 32u -1.4 % (kv_mul 3 open item), memory +-0.3 %.
- Author rules for PR bodies: present tense, no history; perf data = final head vs latest main only.`

const PLAN = {
  type: 'object',
  properties: {
    recommendation: { type: 'string', enum: ['keep one PR', 'split'] },
    prs: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, title: { type: 'string' }, concerns: { type: 'array', items: { type: 'string' } }, base: { type: 'string' }, est_lines: { type: 'integer' }, purpose_and_consumer: { type: 'string' }, standalone_benefit: { type: 'string' }, what_a_reviewer_checks: { type: 'string' }, temporary_code: { type: 'string' } }, required: ['id', 'title', 'concerns', 'base', 'est_lines', 'purpose_and_consumer'] } },
    merge_order_and_why: { type: 'string' },
    construction_method: { type: 'string' },
    verification_before_opening: { type: 'string' },
    costs_and_risks: { type: 'array', items: { type: 'string' } },
    why_not_the_alternatives: { type: 'string' },
  },
  required: ['recommendation', 'prs', 'merge_order_and_why', 'construction_method', 'verification_before_opening', 'costs_and_risks', 'why_not_the_alternatives'],
}
const ANGLES = [
  { key: 'minimal', angle: 'Minimal-change planner: prefer the fewest PRs and reuse of already-tested trees (the history seams), cut only where the construction is a git operation or a small subtraction.' },
  { key: 'concern', angle: 'Concern-first planner: one PR per concern (L+G, R, A, S, T, B folded where tiny), optimise for reviewer comprehension and the author\'s stated premise that the VNNI K layout is independent of AMX; accept construction work.' },
  { key: 'skeptic', angle: 'Skeptic: argue for keeping ONE PR (or the least split) unless the evidence shows the cuts are technically clean AND each piece has a consumer and a measurable standalone claim; weigh the re-measurement cost (author rule: final head vs latest main per PR), the main drift, reviewer time across N PRs, and the AGENTS.md draft-stack rule.' },
]
const planPrompt = (a) => `You are a planner for splitting PR 4424 of positron-ai/tron into a stack of smaller PRs, or keeping it whole. ${a.angle}
${FACTS}
Hunk classification totals per concern (added/removed lines): ${JSON.stringify(totals)}
Seam verdicts with refutations: ${JSON.stringify(seamResults)}
Per-file classification (for sizes and test cases): ${partitionJson}
Give a concrete plan: PR list with ids, titles, concerns, base branch, estimated size (sum the classified lines; count tests), the purpose and consumer of each PR (the repo norm: do not add code with no consumer), the standalone measurable benefit it can claim, what a reviewer checks in it, any temporary code it must carry (named, with where it is removed later). Give the merge order with the dependency reason for each edge, the construction method (git operations vs hunk subtraction vs rewrite, per PR), the verification needed before opening each PR (builds in both layouts, tests, which measurements), and the costs/risks. Explain why not the alternatives. Be concrete and honest; if the split is not technically sound, say so.`
const plans = (await parallel(ANGLES.map(a => () => agent(planPrompt(a), { label: `plan:${a.key}`, phase: 'Plan', schema: PLAN })))).filter(Boolean)

const JUDGE = {
  type: 'object',
  properties: {
    verdict: { type: 'string' },
    chosen_plan: PLAN,
    scores: { type: 'array', items: { type: 'object', properties: { plan: { type: 'string' }, score: { type: 'integer' }, why: { type: 'string' } }, required: ['plan', 'score', 'why'] } },
    open_questions_for_author: { type: 'array', items: { type: 'string' } },
    facts_to_verify_before_acting: { type: 'array', items: { type: 'string' } },
  },
  required: ['verdict', 'chosen_plan', 'scores', 'open_questions_for_author', 'facts_to_verify_before_acting'],
}
const judge = await agent(`You judge three plans for splitting (or not splitting) PR 4424 of positron-ai/tron. Score each 0-10 on technical soundness (every PR compiles and tests alone, no PR depends on a later one), reviewer value (each PR reviewable in one sitting, purpose clear, consumer present), construction cost, and honesty about standalone benefits. Then produce the chosen plan: start from the winner and graft the best elements of the others. Keep the author's premise in mind ("VNNI-K is independent of AMX, so the VNNI-K changes can be a separate PR") and state plainly whether the evidence supports it at the code level and at the benefit level. Read-only task.
${FACTS}
Totals per concern: ${JSON.stringify(totals)}
Seam verdicts: ${JSON.stringify(seamResults)}
Plans: ${JSON.stringify(plans.map((p, i) => ({ angle: ANGLES[i] ? ANGLES[i].key : i, plan: p })))}`, { label: 'judge', phase: 'Plan', schema: JUDGE })

return { totals, classified, seamResults, plans: plans.map((p, i) => ({ angle: ANGLES[i] ? ANGLES[i].key : i, plan: p })), judge }