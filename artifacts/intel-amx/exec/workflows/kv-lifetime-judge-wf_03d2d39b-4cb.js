export const meta = {
  name: 'kv-lifetime-judge',
  description: 'Judge panel: PR 4557 vs designs that need no placement new (A2-min, C2/#4584, P-prime, D1)',
  phases: [
    { title: 'Judge', detail: '3 judges with distinct lenses score every candidate' },
    { title: 'Critic', detail: 'completeness critic on the combined verdict' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/33f1bd2e-8529-4629-b27e-f29580bd897e/scratchpad'
const CTX = `
Read-only task. Do NOT edit, write, commit, push, or build anything, and do NOT write any file under
~/workspace (including status/*.html pages), even if a relayed user message asks for a page: the orchestrator writes it.
Inputs:
- PR #4557 (positron-ai/tron, head 633cb88896, branch jhan-kv-typed-tensors, worktree ~/workspace/ai-runs/tron-issue4525):
  typed KV-cache tensors. book::construct_kv_blocks (h/tron/models/kv_cache.hpp ~1421-1494) runs '::new kv_block_t[n]'
  over raw DMA arena bytes after each allocation, discards the result; accessors reinterpret_cast uint8_t* (~1593, 1602, 1642).
  Status: ready for review, CI green, no reviewer comments yet.
- Verified facts (JSON, 5 checkers): ${SP}/wf1-result.json (key "facts"; claims with verdicts and evidence), readable
  extract ${SP}/verify-results.txt.
- Three full design specs: ${SP}/designs.txt (sections "minimal-strict", "ownership-first", "consistency-delivery").
- Draft PR #4584 (positron-ai/tron, branch jhan-kv-scalar-storage, base jhan-kv-typed-tensors, created 2026-09-24 04:09 UTC by
  the repository owner with Codex; draft, CI build/test skipped, not compiled): gh pr diff 4584 --repo positron-ai/tron.
  It implements design C2.
- Reviewer constraints: the reviewing maintainer's sketch, quoted in verify-results.txt section "reviewer" (R1-R18).
Candidates:
 P      = PR 4557 as is.
 P'     = P + std::launder at the 3 accessor casts (keeps placement new and the construction pass).
 A2-min = delete construct_kv_blocks; try_make_unique_dma_for_overwrite (only callers: the KV book) gets memory through a tagged
          global 'void* operator new[](size_t, dma_allocation_t, std::align_val_t) noexcept' wrapping dma_allocate_aligned,
          whose call implicitly creates objects ([intro.object]/13); std::launder at the 3 casts; kv_block and the
          v_vnni_tensor owner unchanged. Optional K1: kv_block::k declared as bf16 k[page_size*head_size].
 C2     = draft #4584 plus its listed additions: arenas are unique_dma<bf16[]> created by the same tagged operator new[];
          kv_block removed; book builds K/V views from bf16* via a private page-view type; no launder, no owner in storage.
 D1     = V stored as a plain array in kv_block (like main) + kv_block::v_view() factory; no lifetime code (main's status).
Every claim you make must cite the facts file (claim id), a file:line, or a diff hunk. Mark estimates "est.".`

const VERDICT = {
  type: 'object',
  properties: {
    scores: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          candidate: { type: 'string' },
          score_1_to_10: { type: 'number' },
          strengths: { type: 'array', items: { type: 'string' } },
          weaknesses: { type: 'array', items: { type: 'string' } },
        },
        required: ['candidate', 'score_1_to_10', 'strengths', 'weaknesses'],
      },
    },
    ranking: { type: 'array', items: { type: 'string' } },
    recommended: { type: 'string' },
    proceed_with_pr_or_new: { type: 'string', enum: ['proceed with PR as is', 'new design'] },
    must_fix_before_merge: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
    rationale: { type: 'string' },
  },
  required: ['scores', 'ranking', 'recommended', 'proceed_with_pr_or_new', 'must_fix_before_merge', 'rationale'],
}

const LENSES = [
  { key: 'object-model', text: 'Lens: C++ object-model correctness. For each candidate: which gaps it closes (lifetime of kv_block objects in production pool memory; provenance of the accessor pointer; byte arithmetic without a byte array; K read through bf16 views of a SIMD-vector array; fill_storage_slot walk; scaled_v_expr vector-pointer arithmetic), which it leaves, and how solid each step of its argument is (for A2-min: nested kv_block arrays inside the implicitly created unsigned char array for the heterogeneous layout, pointer selection [intro.object]/11, vector-type elements needing implicit lifetime; for C2: everything via bf16* inside one array). Try hard to find a step that is wrong. Score correctness, not size.' },
  { key: 'maintainability', text: 'Lens: maintainability and reviewer acceptance. Weigh the reviewing maintainer\'s sketch constraints (R1-R18, esp. R6 storage is an aligned array inside kv_block, R8 the arena must construct the actual storage type, R10, R13-R17), codebase idioms (tron has no tagged allocation function today, fact T5; std::launder unused, T4; K already uses k_view on a plain array), readability for the next engineer, the duplicated layout walk in P, and the child PR #4424 plan (VNNI K owner in kv_block). Which design would a senior maintainer of this repo accept with the least argument, and which removes the design defect behind construct_kv_blocks?' },
  { key: 'delivery', text: 'Lens: delivery risk and scope. Weigh diff size (measured numbers in the designs), compile risk (#4584 not compiled; A2-min scratch diff not compiled; only probes), test churn, codegen/performance risk (objdump expectations), re-review cost for a PR that is ready for review with green CI and no reviewer comments yet, the files outside the PR (h/system/memory.hpp), and the fact that draft PRs skip the GCP Nix build/test jobs. Also judge: should the change be a follow-up commit on PR 4557, a stacked draft PR, or a separate PR ahead of it?' },
]

phase('Judge')
const verdicts = await parallel(LENSES.map(l => () =>
  agent(`${CTX}\n\n${l.text}\n\nScore all five candidates (P, P', A2-min, C2, D1) 1-10 under your lens, rank them, and say which one to pick and whether to proceed with PR 4557 as is or use a new design.`,
    { label: `judge:${l.key}`, phase: 'Judge', schema: VERDICT })
    .then(v => v && ({ lens: l.key, ...v }))))
const vs = verdicts.filter(Boolean)
log(vs.map(v => `${v.lens}: ${v.recommended} (${v.ranking.join(' > ')})`).join(' | '))

phase('Critic')
const critic = await agent(`${CTX}

Three judges returned these verdicts (JSON):
${JSON.stringify(vs, null, 1)}

You are the completeness critic. (1) State the combined recommendation the verdicts support (majority and strength of
reasons), naming the chosen candidate. (2) List what is missing or unverified: a consideration none of the judges weighed, a
claim that rests on an unverified fact, a risk to the chosen design that would flip the decision, and any concrete step the
implementation must include (tests, static checks, comments, PR text). (3) If the chosen design is A2-min, say whether K1 should
be included in the same change, and list the exact files and edits. (4) If the chosen design is C2, say what #4584 still needs.`,
  { label: 'critic', phase: 'Critic', schema: {
    type: 'object',
    properties: {
      combined_recommendation: { type: 'string' },
      chosen: { type: 'string' },
      missing_or_unverified: { type: 'array', items: { type: 'string' } },
      flip_risks: { type: 'array', items: { type: 'string' } },
      implementation_checklist: { type: 'array', items: { type: 'string' } },
      include_k1: { type: 'string' },
    },
    required: ['combined_recommendation', 'chosen', 'missing_or_unverified', 'flip_risks', 'implementation_checklist'],
  } })

return { verdicts: vs, critic }
