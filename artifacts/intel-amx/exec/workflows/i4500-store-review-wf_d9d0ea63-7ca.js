export const meta = {
  name: 'i4500-store-review',
  description: 'Adversarial review of commit 0bb74c2ab0 (short-run K row written straight into its row-major block)',
  phases: [{ title: 'Find' }, { title: 'Refute' }],
}
const FIX = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-i4500'
const CTX = `CONTEXT: worktree ${FIX}, HEAD 0bb74c2ab0 (parent 452b2052c9). See the change with: git -C ${FIX} show 0bb74c2ab0. It changes store_k_block's short-run branch (model.hpp ~2953-2975): for each row and KV head, if page::k_row_if_row_major (kv_cache.hpp ~1996, returns row_ptr when the block bit is clear, else nullptr) gives a pointer, the row is written with view<bf16, true, false, seq<head_size>>{row}.set(kout) (the same view store the row-major layout's branch uses at ~2905-2913); otherwise the old set_k_row path (scatter into a converted block, converting to bf16 on the stack first when the K buffer is not bf16). Background: k_vnni::row_ptr (k_vnni.hpp ~261-271) = plane + ((t/4)*4 + c)*512 + (t%4)*128 elements; the plane (kv_block.k) is 64-byte aligned; the shared block save (Note [Shared block save]) may run store_k_block on helper threads for different units of one window; set_k_row does k_state_ix + one acquire load + memcpy. Rules: cite path:line; every finding = claim + evidence + concrete failure scenario + severity; return raw findings only; empty list if nothing.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'should-fix', 'nit'] }, claim: { type: 'string' }, evidence: { type: 'array', items: { type: 'string' } }, scenario: { type: 'string' }, fix: { type: 'string' } }, required: ['id', 'severity', 'claim', 'evidence', 'scenario'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { verdict: { type: 'string', enum: ['confirmed', 'refuted', 'downgraded'] }, reason: { type: 'string' }, evidence: { type: 'array', items: { type: 'string' } } }, required: ['verdict', 'reason', 'evidence'] }
const LENSES = [
  { key: 'correctness', p: 'LENS correctness: alignment of the row pointer for the aligned=true view store (is every row_ptr 64-byte aligned for every t and c? what does view<bf16, true, ...> assume: chunky store alignment?); the element type of kout for ingested plugins and llama.hpp (bf16 or fp32: does view::set handle both, and is the numeric result bit-identical to the old conv-then-memcpy path and to the row-major layout branch?); the race window: k_row_if_row_major reads the block bit then the store writes; can the block bit flip between the two (who sets it: note_k_block_saved after set_k_block on another thread of a shared window for a DIFFERENT block/unit; convert at forward end on main) so that the store lands in a block that is VNNI by the time it writes? Compare with the parent commit\'s set_k_row which had the same read-then-write; the geometry template parameter (geometry.kv vs the requires clause k_vnni::layout_on<geometry.head_size>); the row-major build (TRON_K_VNNI off): is this branch compiled at all (if constexpr) and does it still compile (k_row_if_row_major requires layout_on).' },
  { key: 'tests-perf', p: 'LENS tests and effect: which existing tests cover this branch (t_llama_unit save_k case: rows_are_bf16 true? any fp32 K buffer test? t_k_vnni_layout?); would a wrong pointer arithmetic be caught (the test checks every stored row against patterns via which accessor?); and is the claimed effect plausible: list what set_k_row + memcpy did per row vs the new view store per row (instruction-level), and whether the k_state_ix / acquire load per (row, head) remains (it does: in k_row_if_row_major). Is there a cheaper form (one block-bit read per run instead of per row and head, since all rows of a run are in one block c of one page: the bit cannot change during the run on this thread)? Give the concrete code shape if so.' },
]
phase('Find')
const found = await pipeline(LENSES,
  l => agent(`${CTX}\n\n${l.p}\n\nIds ${l.key}-1, ...`, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  async (r, l) => {
    if (!r || !r.findings.length) return { lens: l.key, results: [] }
    const results = await parallel(r.findings.map(f => async () => {
      const votes = await parallel([0, 1].map(i => () => agent(`${CTX}\n\nSkeptical verifier (${i === 0 ? 'check the cited lines literally' : 'look for guards/invariants that make the scenario impossible'}). Finding:\n${JSON.stringify(f, null, 1)}\nDefault to refuted when uncertain; path:line evidence.`, { label: `refute:${f.id}:${i}`, phase: 'Refute', schema: VERDICT })))
      const v = votes.filter(Boolean)
      return { finding: f, votes: v, confirmed: v.filter(x => x.verdict !== 'refuted').length >= 2 }
    }))
    return { lens: l.key, results: results.filter(Boolean) }
  })
return found.filter(Boolean)