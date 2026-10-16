export const meta = {
  name: 'pr2-prereview',
  description: 'Pre-review of PR-2 (jhan-vnnik-2-amx) diff: review skills, reviewer items, plain English; each finding adversarially verified',
  phases: [
    { title: 'Review', detail: 'six independent lenses over the diff jhan-vnnik-1-layout..HEAD' },
    { title: 'Verify', detail: 'three refuters per must-fix/should-fix finding' },
  ],
}
const W = '/home/jhan/workspace/ai-runs/tron-split-pr2'
const CTX = `
Context (read-only review; do NOT modify any file in the worktree, do not run git commands that change state, do not build or run tests; no AMX hardware and no nix here).
Worktree: ${W}, branch jhan-vnnik-2-amx, two commits on top of jhan-vnnik-1-layout (82d05e94be): e490a78a1e "amx: the QK kernel on the VNNI plane" and 9421eeb804 "tests: bit identity and the typed-boundary probe for the VNNI kernel".
Get the diff with: git -C ${W} diff jhan-vnnik-1-layout HEAD   (10 files, +285/-72). Commit messages: git -C ${W} log -2 --format=%B jhan-vnnik-1-layout..HEAD
What PR-2 is: the second of four stacked PRs that replace the big PR 4424 in positron-ai/tron. PR-1 (PR #4868, branch jhan-vnnik-1-layout) added the VNNI K layout (h/tron/tensor/k_vnni.hpp), its AVX-512 reader k_vnni::qk_group and the FPGA staging path, with a temporary gate that sent every page of a VNNI slot to the reader. PR-2 adds the AMX QK kernel qk_vnni_128x4 and the packer pack_q_rows_128x4 (src/tron/kernels/amx_attn.cpp, declared in h/tron/kernels/amx_attn_iface.hpp), dispatches to them in h/tron/models/self_attention.hpp by k_vnni::layout_on<head_size>, removes PR-1's temporary gate, restores comment wording, adds dispatch fakes in t/t_amx_dispatch_dtype.cpp, a bit-identity case in t/t_amx_numerics.cpp, six STATIC_REQUIREs in t/t_llama_unit.cpp and a README.ci.md sentence.
Constraints the handoff imposes (findings that ask to break these are out of scope): the diff must stay 10 files and two commits; no comment may narrate the split or the review (no "PR-1", "PR-2", "the next PR", "temporary", "until ... lands", "this change"); the CMake option TRON_K_VNNI stays off in every preset; nix/cmake-tron-test-build.nix is not touched; the identity case needs AMX hardware and returns early with a WARN without it (accepted limitation, issue #4865); the reader k_vnni::qk_group and the layout are PR-1's and not under review here except where PR-2's lines touch them.
Report format: findings only, each with file, line (in the new tree), severity (must-fix | should-fix | nit), the claim in one sentence, the evidence (what you read, with file:line), and a proposed exact fix (old text -> new text when it is a text change). No praise, no summary of what the diff does.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  file: { type: 'string' }, line: { type: 'integer' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
  claim: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'line', 'severity', 'claim', 'evidence', 'fix'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LENSES = [
  { key: 'wade', prompt: `Load the skill "Wade-code-review" with the Skill tool and apply its checks to this diff at its final head. ${CTX}` },
  { key: 'tron', prompt: `Load the skill "tron-code-review" with the Skill tool and apply it to this diff (execution-path coverage, forward-pass bookkeeping, meaningful tests). ${CTX}` },
  { key: 'positron', prompt: `Load the skill "positron-code-review" with the Skill tool and apply it to the COMMENTS of this diff: any comment that narrates the split, a review round, or a temporary state must be flagged with a lasting technical rationale as the fix. Also check the two commit messages for the same. ${CTX}` },
  { key: 'items', prompt: `Check these seven items the reviewers of PR-2 are expected to raise, by reading the code (src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp, h/tron/models/self_attention.hpp, h/tron/tensor/k_vnni.hpp, t/t_amx_numerics.cpp) and report only where the code or a comment is wrong, inconsistent or unproven:
1. the tile orientation (A = the padded Q rows, B = the K panels, C tiles 0..3 = the four token blocks): do the _tile_loadd strides, the panel offsets ((step*4+block)*PANEL_ELEMS_512) and the k_vnni.hpp index map agree? Derive the panel layout from k_vnni::index() yourself.
2. the padding contract of pack_q_rows_128x4: rows 4 to 15 are never written by the packer; the query-pack slots are zero-filled by resize() and only the 4 live rows are written, so the padding stays zero across calls and slot reuse; in the option-on build every eligible slot is a VNNI slot, so only this packer writes the slots. Check amx_qpack_slot, resize(), packed_amx_query in self_attention.hpp.
3. the 16-row tile store into the kernel's internal buffer s16 and the 4-row copy-out: sizes, strides, alignment, and that s needs only 4 rows.
4. the bit-identity claim: the test comment says both kernels add the same four 32-dimension partial dots in the same order inside TDPBF16PS; is that true given that qk_rowmajor_128x4 uses K as A and Q as B (read its loop in amx_attn.cpp) and qk_vnni_128x4 the reverse? Is the per-element fp32 accumulation order identical (same step order 0..3, same accumulator)?
5. the dispatch under the option: the packer and the kernel chosen by k_vnni::layout_on at both sites, the dense predicate is_dense_amx_page unchanged otherwise, the removed gate clause leaves the if constexpr condition well-formed, and the option-off build still instantiates the row-major path only.
6. the plane address taken once through detail::k_vnni_access::plane, and that the kernel is listed among the allowed readers in the k_vnni.hpp comments (friend / access rules: can amx_attn.cpp actually call detail::k_vnni_access::plane? check how k_vnni_access grants access and whether qk_group does the same).
7. the static_asserts that tie the plane constants to the kernel constants: do the named constants exist in k_vnni.hpp with those values (PAGE_TOKENS_64, HEAD_SIZE_128, STEP_DIMS_32, BLOCK_TOKENS_16, PANEL_ELEMS_512, TOKEN_BLOCKS_4, STEP_PAIRS_16)?
${CTX}` },
  { key: 'plain', prompt: `Load the skill "plain-english" with the Skill tool. Apply its Check mode to (a) every ADDED comment line of the diff (git diff jhan-vnnik-1-layout HEAD, lines starting with + that are comments) and (b) the two commit messages. Rules that apply to code comments: one claim per sentence, no idioms, define terms imported from outside the code at first use (a name visible in the surrounding code needs no definition). Report violations as findings with the exact phrase and the corrected text; do not report the absence of a Short version for comments or commit messages. ${CTX}` },
  { key: 'tests', prompt: `Review the three tests of the diff against tron's test policy (read ${W}/AGENTS.md "Test policy" and ${W}/t/AGENTS.md if present): (1) the t_amx_numerics identity case: does it fail when the kernel's panel addressing is wrong (reason about a mutation: the second panel load reading block 2 instead of block 1), can it pass trivially (e.g. both buffers zero, same uninitialized memory), is the scrambled store order meaningful, is CAPTURE/REQUIRE use right, does it leak AMX tile state (begin_region/end_region pairing)? (2) the t_amx_dispatch_dtype fakes: do the fakes of both packers write into the same probe such that the expectations "one pack, one QK, one PV" hold under either layout; is the removed clause in the dense predicate consistent with the production predicate? (3) the six STATIC_REQUIREs in t_llama_unit: is the requires-expression correct (template argument deduction with k_vnni_view<const bf16,...> from a mutable view; does "writable converts to read-only" actually hold for the kernel's signature)? Also check the commit split: commit (a) holds the dispatch fakes with the kernel so that t_amx_dispatch_dtype links at (a); verify by reading which amx_attn_h128g4 symbols self_attention.hpp instantiates and which the test defines. ${CTX}` },
]
const results = await pipeline(
  LENSES,
  l => agent(l.prompt, { label: `review:${l.key}`, phase: 'Review', schema: FINDINGS }),
  (r, l) => {
    if (!r) { log(`lens ${l.key} returned nothing`); return [] }
    log(`lens ${l.key}: ${r.findings.length} findings`)
    return r.findings.map(f => ({ ...f, lens: l.key }))
  },
  async (fs, l) => {
    const verified = []
    for (const f of fs) {
      if (f.severity === 'nit') { verified.push({ ...f, votes: 'unverified-nit' }); continue }
      const votes = await parallel(['correctness (is the claim true of the code as written? read the lines yourself)', 'scope (does the handoff context forbid or already answer this? is it about PR-1 lines PR-2 does not touch, or a design choice the handoff fixed?)', 'fix-quality (would the proposed fix compile, keep clang-format 88 columns, keep two commits and 10 files, and not introduce narration words?)'].map(lens => () =>
        agent(`Try to REFUTE this review finding through the ${lens} lens. Default to refuted=true if you are uncertain or cannot verify it from the files. Finding (from lens ${l.key}): file ${f.file} line ${f.line}, severity ${f.severity}. Claim: ${f.claim}. Evidence given: ${f.evidence}. Proposed fix: ${f.fix}. ${CTX}`, { label: `verify:${l.key}:${f.file.split('/').pop()}:${f.line}`, phase: 'Verify', schema: VERDICT })))
      const vs = votes.filter(Boolean)
      const kept = vs.filter(v => !v.refuted).length >= 2
      verified.push({ ...f, kept, votes: vs.map(v => (v.refuted ? 'R: ' : 'K: ') + v.reason) })
    }
    return verified
  },
)
const all = results.flat().filter(Boolean)
const kept = all.filter(f => f.kept || f.votes === 'unverified-nit')
const dropped = all.filter(f => !(f.kept || f.votes === 'unverified-nit'))
log(`total ${all.length}, kept ${kept.length} (incl. unverified nits), refuted ${dropped.length}`)
return { kept, dropped }