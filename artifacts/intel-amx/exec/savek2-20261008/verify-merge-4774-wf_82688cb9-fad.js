export const meta = {
  name: 'verify-merge-4774',
  description: 'Adversarially verify the merge of PR 4774 (save_k worker fold) onto the jhan-amx-vnniK typed-K head',
  phases: [
    { title: 'Find', detail: 'six lenses read the merged tree and the three diffs' },
    { title: 'Verify', detail: 'three refuters per finding, majority rules' },
  ],
}
const CTX = `
CONTEXT (read-only task: never edit files, never run git commands that change state; no commit/checkout/reset/stash/clean).
Repository worktree: /home/jhan/workspace/ai-runs/tron-vnnik-savek2 (positron-ai/tron). HEAD = 45e6bb266d = a merge commit.
  First parent 6b939d25d2 = branch jhan-amx-vnniK head (PR 4424 "VNNI K", which merged main be0d5565b3 and ported K onto the typed KV tensors of PR 4557).
  Second parent f52d634c32 = the single commit of PR 4774 (fold of save_k_helper into save_k(worker_ix)), written on 30c4ac82cb = the merge base.
Useful commands (run inside the worktree):
  git diff 30c4ac82cb f52d634c32        # what PR 4774 changed (4 files)
  git diff 6b939d25d2 45e6bb266d        # what the merge changes against the branch head (the PR diff)
  git diff 30c4ac82cb 6b939d25d2 -- <file>   # what the branch head changed since the merge base (large)
  git show 45e6bb266d --format=%B -s    # the merge message, which states how the 6 conflict hunks were resolved
Conflict resolution policy used: the branch head renamed local constants to lowercase local spelling (k_join_timeout_s, kv_jobs, n_kv_heads, num_kv_tokens, n_workers); the merge keeps those names and takes PR 4774's code, messages and comments; the new test constant is main_worker_ix. TronCpp.hs comment keeps the head's "consecutive tokens inside one 16-token page block" wording and takes 4774's sentence about both call sites.
Key code: h/tron/models/model.hpp (Note [Shared block save] ~line 3078, k_store_shared ~3160, save_k_impl ~3311, save_k overloads ~3410), ingest/src/TronCpp.hs (helper-side AttentionStmt case ~2878, main-side submitAttentionOperation saveKv ~2950), ingest/test/LoopyTronSpec.hs (~3134 and ~3559), t/t_llama_unit.cpp (TEST_CASE "save_k stores every token's K row once" ~3666-3930).
Report only defects that would make the merge wrong, fail to compile, fail a test, or leave a comment/message that contradicts the code. Cite file:line of the merged tree for every finding. Do not report style preferences.
`
const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
      claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' },
      severity: { type: 'string', enum: ['compile', 'test', 'behavior', 'comment'] },
    }, required: ['id', 'file', 'line', 'claim', 'evidence', 'fix', 'severity'] } },
    checked: { type: 'string' },
  },
  required: ['findings', 'checked'],
}
const VERDICT = {
  type: 'object',
  properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } },
  required: ['refuted', 'reason'],
}
const LENSES = [
  { key: 'hunks', prompt: `Lens HUNKS: prove that every hunk of PR 4774's diff (30c4ac82cb..f52d634c32) is present in the merge diff (6b939d25d2..45e6bb266d) up to the renamed constants, and that the merge diff contains nothing else. Also prove the reverse: nothing of the branch head's own changes to these four files (30c4ac82cb..6b939d25d2) was lost or reverted by the merge (compare 6b939d25d2 vs 45e6bb266d line by line for each of the 4 files; every removed line must be one PR 4774 removed or rewrote). Report any lost line, any duplicated block, any leftover conflict marker, any value-suffix constant name (K_JOIN_TIMEOUT_S_120 etc.) left in the four files.` },
  { key: 'callers', prompt: `Lens CALLERS: list EVERY call site and mention of save_k, save_k_impl and save_k_helper in the merged tree outside gen/ (h/, src/, t/, ingest/, doc/, README*, CLAUDE.md, AGENTS.md; use grep -rn). For each C++ call, check the argument list against the new signatures save_k(q_batch, ks, worker_ix = 0, n_workers = 1) and save_k(q_batch, operation, ks, worker_ix = 0, n_workers = 1): a caller added on the branch head since 30c4ac82cb that passes n_workers as the FOURTH argument would now bind it to worker_ix silently. Check h/tron/plugins/llama.hpp, t/heterogeneous_scheduler_compile.cpp, t/t_llama_unit.cpp (all sections), and any other caller. Also check documentation mentions (README*, doc/) still describing save_k_helper.` },
  { key: 'typed-port', prompt: `Lens TYPED-PORT: the branch head (30c4ac82cb..6b939d25d2) ported the K cache onto typed KV tensors and merged 916 main commits. Check that save_k_impl at 45e6bb266d is coherent with that head: batch::k_store_window fields (opened, next_unit, finished, helper_windows, n_units, unit_start) exist in h/tron/models/common.hpp (or wherever batch lives) with the types used; store_k_block's signature matches its calls; k_store_cut_units exists and is called only by main; the helper early return happens before TRACE_EVENT/log_intermediate side effects that must stay main-only; mark_k_complete/credit_gof_save/count_down stay after the join on main only; the noexcept and template parameters are consistent; nothing in the typed port added a second place that must also take worker_ix.` },
  { key: 'test', prompt: `Lens TEST: examine the save_k TEST_CASE in t/t_llama_unit.cpp at 45e6bb266d. Check: the mark-check block uses token_pages, job_tokens, do_kv, slot, n_items as defined in this test at the merged head (types: page_t*, token_id, uint8_t...); page_t::offset_in_page(token_id) and is_kv_complete(slot, size_t)/mark_k_complete(slot, size_t) exist in h/tron/models/kv_cache.hpp with the claimed semantics (mark_k_complete returns true only when the count was 1 before; is_kv_complete false after one mark; a job without KV work has count 0) — read the implementation; the check lambda is called in both sections after save_k, so the second mark happens once per section (REQUIRE on the return value); the three-thread section's constants (n_workers, main_worker_ix) and the later REQUIREs (w.finished == n_workers - 1 etc.) are consistent; the test runs in both the VNNI and the row-major build (if constexpr guards). Also check ingest/test/LoopyTronSpec.hs expectations (count of "outer_state.template save_k<" == 2, the texts ",k,0,n_workers);" and ",k,worker_ix,n_workers);") against what the generator in ingest/src/TronCpp.hs emits (attentionRuntimeCall + LiteralExpr (IntLit 0) + ExprLit "n_workers": does the printed C++ have no spaces after commas? find the Cpp pretty printer's call rendering).` },
  { key: 'comments', prompt: `Lens COMMENTS: read every comment, Note and assertion message touched by the merge diff (6b939d25d2..45e6bb266d) and the whole Note [Shared block save] in h/tron/models/model.hpp plus the two TronCpp.hs comments (helper-side AttentionStmt case and submitAttentionOperation saveKv) and the LoopyTronSpec.hs comments near the save_k checks. Report any sentence that contradicts the merged code: e.g. function names that no longer exist (save_k_helper, runHelperStatement if that is not the real name), "worker index 0 (submitAttentionOperation)" if the main-side call is emitted elsewhere, the join watchdog constant name, the claim that helpers leave before the mark loop, the claim "the N-th window a helper enters is the N-th window main opens". Verify each by reading the code.` },
  { key: 'wade', prompt: `Lens WADE: review the PR diff (git diff 6b939d25d2 45e6bb266d) the way reviewer Wade does. Load the skill with the Skill tool (name "Wade-code-review") if available; otherwise read ~/.claude/skills/Wade-code-review/SKILL.md and apply its checks. Report only checks that FAIL on this diff with file:line evidence (dead symbols, debug switches, comments contradicting code, magic literals in AMX-owned files vs shared files [note: model.hpp and t_llama_unit.cpp are SHARED files, which keep their local constant spelling per the branch's convention], duplicated logic, silent fallbacks, index mismatches, tests that bypass the changed path, claims wider than the code).` },
]
phase('Find')
const results = await pipeline(
  LENSES,
  l => agent(CTX + '\n' + l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  (found, l) => {
    if (!found) { log(`lens ${l.key}: agent returned null`); return [] }
    log(`lens ${l.key}: ${found.findings.length} findings; checked: ${found.checked.slice(0, 200)}`)
    return parallel(found.findings.map(f => () =>
      parallel([1, 2, 3].map(i => () => agent(
        CTX + `\nYou are refuter ${i} of 3. A reviewer (lens ${l.key}) claims this defect in the merged tree:\n` +
        JSON.stringify(f, null, 2) +
        `\nTry hard to REFUTE it by reading the actual code at 45e6bb266d (not the claim). A finding is refuted when the code does not have the defect, when the cited lines say something else, when the claimed consequence cannot happen, or when it is only a style preference. Default to refuted=true if uncertain. Give the file:line evidence for your verdict.`,
        { label: `verify:${l.key}:${f.id}:${i}`, phase: 'Verify', schema: VERDICT })))
      .then(vs => {
        const votes = vs.filter(Boolean)
        const refutations = votes.filter(v => v.refuted).length
        return { lens: l.key, finding: f, confirmed: votes.length > 0 && refutations * 2 < votes.length, votes }
      })))
  },
)
const all = results.flat().filter(Boolean)
const confirmed = all.filter(r => r.confirmed)
const refuted = all.filter(r => !r.confirmed)
log(`${confirmed.length} confirmed, ${refuted.length} refuted`)
return { confirmed, refuted: refuted.map(r => ({ lens: r.lens, id: r.finding.id, claim: r.finding.claim, reasons: r.votes.map(v => v.reason) })) }