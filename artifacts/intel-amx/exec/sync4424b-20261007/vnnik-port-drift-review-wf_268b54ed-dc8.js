export const meta = {
  name: 'vnnik-port-drift-review',
  description: 'Check the VNNI K typed port against the final PR 4557 conventions on main; adversarially verify each finding',
  phases: [{ title: 'Find', detail: 'six lenses over the synced tree' }, { title: 'Verify', detail: 'two refuters per finding' }],
}
const CTX = `
Context (read-only review; do NOT edit any file, do NOT run git commands that change state).
Tree under review: /home/jhan/workspace/ai-runs/tron-vnnik-sync (branch jhan-amx-vnniK-sync, tip 879ec1eb22). It is
PR #4424 (VNNI K: the K cache of 128-dimension heads stored in the AMX VNNI layout, branch jhan-amx-vnniK head 30c4ac82cb)
plus a merge of main at be0d5565b3 (which contains PR #4557 "typed KV-cache tensors", merged 2026-10-07) plus the typed K
port that PR #4746 had made against an OLD PR #4557 head (c12df586b6). PR #4557's final code differs from c12df586b6:
it was squashed (72083ab161) and then got 654e3ceac0 "Shared files keep their local constant spelling (Wade nit)",
982f82d2d9 "Packed V: assert the row preconditions, drop the unused width rule and element write" (Runar R3/R4/R5),
b74d9d6bc9 (cost row), e1e78f4078 (Note scope). The K port mirrors the V design: h/tron/tensor/k_vnni.hpp (owner
k_vnni_tensor, view k_vnni_view, detail::k_vnni_access, row views, store_row/load_row/store_block/copy_token),
h/tron/kernels/k_vnni.hpp (AVX-512 reader qk_group), kv_cache.hpp (kv_block::k conditional type, page::k_packed,
set_k_row/get_k_row/set_k_block, copy_storage_slot, fill_random, Note [K VNNI storage]), amx_attn_iface.hpp/amx_attn.cpp
(qk_vnni_128x4 takes the view), self_attention.hpp, model.hpp save_k, full.hpp, tests t_k_vnni_layout.cpp, t_llama_unit.cpp
(K typed-boundary probes near lines 400-470 and the save_k / 32-head cases near 3580-3950, 4100-4200), t_amx_numerics.cpp,
t_amx_dispatch_dtype.cpp.
Useful commands: \`git -C /home/jhan/workspace/ai-runs/tron-vnnik-sync diff origin/main HEAD -- <file>\` = what this PR
changes against main; \`git -C ... show origin/main:<path>\` = main's version; \`git -C ... show 654e3ceac0\`,
\`git -C ... show 982f82d2d9\` = the parent's last review rounds. The parent's review outcomes are summarized in
/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/wade-pr4557-review-response.md,
runar-pr4557-review-response.md, value-suffix-names-shared-files.md, pr4557-ben-review-response.md (same directory).
A finding must name file:line in the tree under review, quote the evidence (the parent's final code or review outcome),
and propose the concrete change. Report only what the parent's FINAL conventions or main's current code call for; do not
propose new features. Severity: must (would not pass the parent's reviewers / contradicts main) or should (parity, nit).
`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' }, claim: { type: 'string' },
  evidence: { type: 'string' }, fix: { type: 'string' }, severity: { type: 'string', enum: ['must', 'should'] } },
  required: ['id', 'file', 'line', 'claim', 'evidence', 'fix', 'severity'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LENSES = [
  { key: 'view-api', prompt: `Lens: owner/view API parity. Compare h/tron/tensor/k_vnni.hpp (k_vnni_view, k_vnni_tensor, detail::k_vnni_access, row views and helpers k_source_row/k_destination_row, store_row/load_row/store_block/copy_token) with main's h/tron/tensor/v_vnni.hpp FINAL shape: which members did the parent drop or add in 654e3ceac0 / 982f82d2d9 (writable at(), width requires clause, TRON_ASSERTs on row preconditions, pair_base assert, comment wording)? Does the K header carry a member with no consumer outside a test probe? (grep consumers across h/ src/ t/.) Also kv_cache_fwd.hpp forward declarations vs main's.` },
  { key: 'probes', prompt: `Lens: typed-boundary test probes. In t/t_llama_unit.cpp of the tree under review, find the K probes (k_packed_t, k_packed_mut_t, k_owner_t, amx_qk_vnni_accepts, matrix_at_writes, matrix_indexes_rows, owner_views_temporary, trivially_* , sizeof, alignof, page_k_packed_accepts_geometry). Compare with main's V probes in the same file (around lines 380-400 at origin/main) after Wade's W4 trimmed them (he dropped: trivial-type repeats of kv_cache.hpp static_asserts, sizeof checks, no-operator[], not-default-constructible; kept: kernel probes, pointer ctor, conversions, at(), temporary-owner, alignof). List every K probe that the parent's outcome says to drop or change, with line numbers.` },
  { key: 'notes', prompt: `Lens: Notes and comments vs main's final text. Read Note [K VNNI storage], Note [Shared block save], the kv_block::k comment, copy_storage_slot and fill_random comments in h/tron/models/kv_cache.hpp and model.hpp of the tree under review, and h/tron/tensor/k_vnni.hpp file comment. Compare with main's final Note [VNNI Packed V layout] / Note [KV block lifetime] / Note [DMA allocation creates objects] wording (git show origin/main:h/tron/models/kv_cache.hpp, origin/main:h/tron/tensor/v_vnni.hpp, origin/main:h/system/memory.hpp) and the parent's review outcomes (Runar R2 pair_base comment overclaim, R6 fill_random exception wording, Wade "comments that contradict code"). Report every K sentence that overclaims, contradicts the code in the tree, or names a thing main renamed/removed (e.g. TRON_CHUNK_SIZE 8-wide builds, the cross-avx512 preset, save_k_helper if absent, k_vnni_plane).` },
  { key: 'dead', prompt: `Lens: dead code after the merge of main. main fixed the chunk size at 16 (commit bbc702251e removed the 8-wide branches; TRON_CHUNK_SIZE is still #defined 16 in h/tron/simd/auto.hpp) and removed the AVX512 build option (8d64eeed81) and the cross-avx512 preset (PR 4726). In the tree under review find every guard, comment, include or CMake line of THIS PR (diff origin/main..HEAD) that still refers to a chunk size other than 16, to an AVX512 option, to the removed preset, or to a symbol main no longer has. Check: h/tron/models/kv_cache.hpp:30-42 (#error guard), t/t_k_vnni_layout.cpp lines 35/488/571 (#if TRON_CHUNK_SIZE == 16 ... #else ... #endif), README.ci.md, .github/workflows/cmake-single-platform.yml, CMakeLists.txt, src/tron/CMakeLists.txt. Also check includes this PR adds that nothing uses.` },
  { key: 'spelling', prompt: `Lens: constant spelling in shared files. The parent's reviewer Wade asked (memory value-suffix-names-shared-files.md): NAME_<value> constants are fine in AMX-owned files (amx_attn.cpp, amx_attn_iface.hpp, and by extension this PR's own k_vnni headers and t_k_vnni_layout.cpp), but code added to SHARED files (t_llama_unit.cpp, kv_cache.hpp, model.hpp, common.hpp, self_attention.hpp, full.hpp, gof.hpp) must match the file's existing spelling (literals, lower_snake constexpr, literal-plus-named-local for SIMD masks). Inventory every NAME_<value>-style constant this PR adds to shared files (git diff origin/main HEAD -- t/t_llama_unit.cpp h/tron/models/kv_cache.hpp h/tron/models/model.hpp h/tron/models/common.hpp h/tron/models/self_attention.hpp h/tron/scheduler/full.hpp h/tron/gof.hpp | grep '^+' ), count them per file, and say for each file what main's local spelling is (quote 2 examples from main's version). Report as ONE finding per file with the count and the two examples; severity should.` },
  { key: 'claims', prompt: `Lens: PR claims vs main. Read README.ci.md hunk and .github/workflows/cmake-single-platform.yml hunk of this PR (git diff origin/main HEAD -- README.ci.md .github/workflows/cmake-single-platform.yml CMakeLists.txt src/tron/CMakeLists.txt config/test-benchmarks.json). Verify every factual sentence against main: does the legacy CMake workflow still bundle gen/runtron for a benchmark job and fall back to a local make (grep the yml); does nix/cmake-tron-test-build.nix set TRON_AMX_DISPATCH/TRON_K_VNNI; does the weekly coverage preset set them (CMakePresets.json); does publish-deb.yml use that workflow; is the t_k_vnni_layout cost row present in config/test-benchmarks.json for every platform block main requires (compare with how main lists t_llama_unit rows: genoa96 / granite_rapids_6962p); does the CMake option text still say "128-dim" where the project writes "128-dimension". Report wrong or stale sentences with the main evidence.` },
]
const found = await pipeline(LENSES,
  l => agent(CTX + '\n' + l.prompt + '\nReturn every finding; an empty list is a valid answer.', { label: 'find:' + l.key, phase: 'Find', schema: FINDINGS }),
  (r, l) => (r ? r.findings : []).map(f => ({ ...f, lens: l.key })),
  fs => parallel(fs.map(f => () => parallel([0, 1].map(i => () =>
    agent(CTX + `\nA reviewer claims (lens ${f.lens}): ${f.file}:${f.line} — ${f.claim}\nEvidence given: ${f.evidence}\nProposed fix: ${f.fix}\nYour job: try to REFUTE it by reading the actual files and main's version. ${i === 0 ? 'Lens: is the claim factually true of the tree under review and of main (quote lines)?' : 'Lens: is the proposed fix what the parent PR 4557 final code / its reviewers actually settled on, or does it over-apply a V-specific decision to K?'} Default to refuted=true if uncertain.`,
      { label: `verify:${f.lens}:${f.id}`, phase: 'Verify', schema: VERDICT })))
    .then(vs => ({ ...f, votes: vs.filter(Boolean), survives: vs.filter(Boolean).filter(v => !v.refuted).length >= 2 })))))
const all = found.filter(Boolean).flat()
const confirmed = all.filter(f => f.survives)
const refuted = all.filter(f => !f.survives)
log(`${all.length} findings, ${confirmed.length} confirmed, ${refuted.length} refuted`)
return { confirmed, refuted: refuted.map(f => ({ file: f.file, line: f.line, claim: f.claim, reasons: f.votes.map(v => v.reason) })) }