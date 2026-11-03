export const meta = {
  name: 'pr4-prime-page-split-drift',
  description: 'Find why t_llama_unit "page splits match emulation" drifts by 0.022 at PR4 prime with TRON_K_VNNI on, where PR 4959 head passed',
  phases: [
    { title: 'Analyze', detail: 'five lenses over PR4 prime vs PR 4959 head' },
    { title: 'Verify', detail: 'three refuters per hypothesis' },
    { title: 'Synthesize', detail: 'ranked causes, fix, 3bda diagnostic plan' },
  ],
}

const FACTS = `
FACTS (verified, do not re-derive):
- Worktree W=/home/jhan/workspace/ai-runs/tron-ben-pr4 is branch jhan-vnnik-4-tail-block-5047 at f7c2ccf6b7 (PR4'). Read it with cat/sed/grep. Do NOT modify it, do NOT run git commands that change state, never cd (use git -C and absolute paths).
- PR 4959's head is 6b081187e1 (same repo): read old versions with: git -C $W show 6b081187e1:<path>. PR3' (merged into PR4') is 2c501a9390. PR 5047's head (Ben's structure) is ade89a9d9c.
- Failing run: delphi-3bda, build bp4v = f7c2ccf6b7 with -DTRON_K_VNNI=ON -DTRON_AMX_DISPATCH=ON, clang 19, preset native. Test host has NO AMX available at run time (attn-stats print amx_available=false), software attention, fake device.
  t_llama_unit, TEST_CASE "apply and join page ranges", SECTION "page splits match emulation" (t/t_llama_unit.cpp:3218-3226) calls check_page_range_reductions<8,false,true>(INT_MAX) then <8,false>(INT_MAX) (helper at t/t_llama_unit.cpp:2480-2900).
  Failure at t/testutil.hpp:86 REQUIRE(out_of_bounds.size()==0): "Array not within absolute tolerance 0.01 and relative tolerance 0.02. 1 of 256 elements out of bounds, max abs discrepancy 0.0219526, max rel 0.438241. observed[255]=0.269017 expected[255]=0.253496". That assert_allclose is the emulation comparison at t/t_llama_unit.cpp:~2778 (slice<2*head_size> of v_stars_saved[tok] vs emulation::compute_attention reference). Same failure under TRON_AMX_DISABLE=1. The option-OFF build (bp4) passes everything. PR2' (9a8045836a) and PR3' (2c501a9390) option-ON builds pass t_llama_unit.
- PR 4959's head ea94e95a4e (2026-10-12, option ON build) passed t_llama_unit (277,775 assertions, 66 cases) including this section. So the drift is new in PR4'.
- Test setup (PR4' version, t_llama_unit.cpp ~2548-2570): K planes filled by fill_random; then for page 0 all 64 rows and for later pages rows 0..40 are recorded with test::record_k_row_and_convert(*page, slot_0, tok) (t/kv_cache_helpers.hpp) "as save_k and the forward end would": page 0 = 4 converted VNNI blocks; later pages = blocks 0,1 converted, block 2 a row-major tail of 9 recorded rows, block 3 row-major unrecorded. The reference K is then copied out through get_k_row. At 6b081187e1 the same test block (under #ifdef TRON_K_VNNI) first RE-STORED every row through set_k_row from the raw plane bytes read as consecutive 128-value rows (via page::k_packed and an inverse index map), then recorded with note_k_row_saved + k_block_to_vnni. PR4' removed that re-store (page::k_packed no longer exists) with the comment "The VNNI build scores the K instance fill_random wrote, converted in place."
- PR4' code facts: dense gate inside page::try_score_k_amx (declines unless all four blocks are converted, and when AMX is unavailable); tail scoring inside page::score_k (converted blocks -> k_vnni::qk_group, row-major blocks/slots -> the dotter through one score_rows lambda and a private k_vnni_token_mask); page::set_k_block with 16 valid rows -> store_block (records row bits and block bit); fewer rows -> set_k_row per row; note_k_row_saved returns std::optional<page::k_pending_block>; k_block_to_vnni(k_pending_block); k_block_complete / k_block_converted name the two bit tests; row_major_row/store_row_major/load_row_major in namespace tron::detail (h/tron/tensor/k_vnni.hpp); k_head_fn always copies via get_k_row. Notes: [K VNNI storage] kv_cache.hpp:~688, [Row-major blocks under hardware attention] kv_cache.hpp:~822, [Row-major tail block] tensor/k_vnni.hpp:~425, [Shared VNNI K store] model.hpp:~3085. PR2' added k_vnni::panel_offset (one spelling of a panel address used by the AMX kernel and the qk_group reader).
- The emulation tolerance at line ~2778 is abs 0.01 + rel 0.02 in BOTH versions. A comment near line ~2811 says VNNI K scores differ from row-major scores in the last bits and move one element of the weighted V sum by up to ~0.022 (that comment is about the split-vs-unsplit v_star comparison with tolerance 5e-2 for VNNI).
`

const HYP_SCHEMA = {
  type: 'object',
  properties: {
    hypotheses: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          claim: { type: 'string', description: 'one sentence: what differs between PR 4959 head and PR4 prime and why it moves v_star by ~0.02' },
          mechanism: { type: 'string', description: 'step by step, with file:line citations from BOTH versions' },
          evidence: { type: 'array', items: { type: 'string' }, description: 'file:line quotes (short) that support it' },
          predicted_signature: { type: 'string', description: 'what the failure would look like if true (size, which elements, which tokens, option off/on, with/without AMX)' },
          consistent_with_observed: { type: 'boolean' },
          how_to_test_on_3bda: { type: 'string', description: 'exact instrumentation or single-case run that confirms or rejects it' },
          proposed_fix: { type: 'string' },
          confidence: { type: 'number' },
        },
        required: ['id', 'claim', 'mechanism', 'evidence', 'predicted_signature', 'consistent_with_observed', 'how_to_test_on_3bda', 'proposed_fix', 'confidence'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['hypotheses', 'notes'],
}

const LENSES = [
  { key: 'scoring-path', prompt: `Lens: which tokens of a mixed page go to which kernel. Compare PR 4959 head (git show 6b081187e1:h/tron/models/self_attention.hpp, the token loop / apply_page_tok / the dense page path, and its handling of VNNI slots with unconverted blocks) against PR4' (h/tron/models/kv_cache.hpp page::score_k, page::try_score_k_amx, k_vnni_token_mask, score_rows; h/tron/models/self_attention.hpp at HEAD). Look for: tokens scored by the wrong kernel, scored twice, or not at all at block boundaries (block 2 with 9 recorded rows of 16, block 3 unrecorded but holding live K tokens written by fill_random), the live mask vs the page offset bound, the score buffer layout and the scale factor, any change in the order/grouping of qk_group calls that changes fp32 accumulation. Also check how PR 4959's loop treated UNRECORDED rows of block 3 (row-major, never recorded) versus PR4'.` },
  { key: 'dense-gate', prompt: `Lens: the dense page (page 0, four converted blocks) and the AMX decline when AMX is unavailable at run time. Compare PR 4959 head (git show 6b081187e1:h/tron/models/self_attention.hpp apply_dense_amx_page / is_dense_amx_page and the fallback when amx is unavailable) with PR4' (page::try_score_k_amx in h/tron/models/kv_cache.hpp and apply_dense_amx_page at HEAD). Check: when try_score_k_amx returns false, does the caller then run score_k over the same tokens with the same mask, or does it skip / double-count / leave the score buffer partially written? Does the zero-filled score buffer or an early return change m_star/s_star for that page? Does PR4' route the dense page through qk_group where PR 4959 routed it through the dotter (or the reverse)? Quantify whether that alone explains a ~0.02 drift (the two readers differ in the last bits).` },
  { key: 'storage', prompt: `Lens: the K bytes each reader sees. Trace what fill_random writes into a VNNI slot's plane in t/t_llama_unit.cpp (find fill_random and how it stores K for geometry.kv with head_size 128: raw plane bytes, set_k_row, or a packed view) at PR4' and at 6b081187e1. Then trace test::record_k_row_and_convert (t/kv_cache_helpers.hpp) -> page::note_k_row_saved -> page::k_block_to_vnni -> k_vnni::block_to_vnni (h/tron/tensor/k_vnni.hpp), and the old path at 6b081187e1 (the test's re-store through set_k_row from the raw bytes, then note_k_row_saved + k_block_to_vnni). Decide whether the K instance as read by get_k_row (the reference) and as read by qk_group (converted blocks) and by the dotter (row-major blocks) is the SAME in PR4' as it was in 6b081187e1, token by token. Key question: was the old re-store an identity on the raw bytes, or did it change the K instance (e.g. set_k_row at 6b081187e1 wrote VNNI positions, or bf16 bit patterns from raw random bytes include NaN/inf/denormals that get normalised by a bf16 round trip)? Also check whether block 2 (9 recorded rows) could end up converted in one version and row-major in the other (set_k_block / note_k_row_saved / k_block_complete semantics; the 41-row count).` },
  { key: 'reader-numerics', prompt: `Lens: numerics of the readers. Compare k_vnni::qk_group and the panel addressing (k_vnni::panel_offset, added by PR2') at PR4' (h/tron/tensor/k_vnni.hpp, h/tron/kernels/k_vnni.hpp) with 6b081187e1 (git show). Check the order of the 32-dim steps and the pair accumulation, any changed fma/add order, scale application, and the dotter path (h/tron/kernels/dotter.hpp, unchanged?) and how score_rows in kv_cache.hpp calls it (row stride, dims, scale). Also compare the softmax/m_star/s_star accumulation per page and join_page_ranges at both versions. Could a changed accumulation order move a v_star element by 0.02? Say what size of score difference is needed for a 0.0155 move of a v_star element with 2048 K tokens and softmax weights of this test (q,k ~ N(0,1), head_size 128, scale 1/sqrt(128)).` },
  { key: 'test-change', prompt: `Lens: the test itself. Produce the full diff of check_page_range_reductions and of the "apply and join page ranges" case between 6b081187e1 and HEAD (git -C $W diff 6b081187e1 HEAD -- t/t_llama_unit.cpp t/kv_cache_helpers.hpp t/testutil.hpp) and read the whole helper at HEAD. Determine: (1) exactly which K values the reference (random_ks, copied through get_k_row at ~2572) holds versus the values the scorer reads, in both versions; (2) whether removing the re-store changed the K instance (bf16 round trip? positions?); (3) whether the tolerance at ~2778 (abs 0.01 rel 0.02) was adequate at 6b081187e1 only because the VNNI build scored those pages through a different reader than PR4' does; (4) whether <8,false,true> (uses_hw=true) vs <8,false> changes which pages are converted or which scorer runs (cached_operation_uses_hw policy from PR 4959: rows saved under hardware attention stay row-major); (5) the exact index 255 = head 1 dim 127 of token tok: which token is tok at the failure (first iteration of the loop? the loop order over tokens and algorithms ONE_PASS/TWO_PASS). Report which of these is a genuine PR4' code defect versus a test-setup change.` },
]

phase('Analyze')
const analyses = await parallel(LENSES.map(l => () => agent(
  `${FACTS}\n\nTASK (${l.key}): ${l.prompt}\n\nMethod: read the actual code at both versions (sed -n / grep / git -C show). Cite file:line for every claim. Produce 1 to 4 hypotheses, each a concrete mechanism, not a theme. Mark consistent_with_observed=false when the predicted signature contradicts the facts (e.g. a mechanism that would produce garbage scores for whole blocks cannot give a single 0.022 outlier among 256 values within tolerance). Do not run tests or builds.`,
  { label: `analyze:${l.key}`, phase: 'Analyze', schema: HYP_SCHEMA }
)))
const hyps = analyses.filter(Boolean).flatMap((a, i) => a.hypotheses.map(h => ({ ...h, id: `${LENSES[i].key}/${h.id}`, lens: LENSES[i].key })))
log(`${hyps.length} hypotheses from ${analyses.filter(Boolean).length} lenses`)

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reasoning: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
    corrected_claim: { type: 'string', description: 'if partly right, the corrected mechanism' },
  },
  required: ['refuted', 'reasoning', 'evidence'],
}

phase('Verify')
const verified = await parallel(hyps.map(h => () =>
  parallel([0, 1, 2].map(k => () => agent(
    `${FACTS}\n\nYou are refuter ${k + 1} of 3. Try to REFUTE this hypothesis by reading the code at both versions (W=/home/jhan/workspace/ai-runs/tron-ben-pr4 at HEAD; old = git -C $W show 6b081187e1:<path>). Default to refuted=true if you cannot find positive evidence in the code.\n\nHYPOTHESIS ${h.id} (lens ${h.lens}): ${h.claim}\nMechanism: ${h.mechanism}\nEvidence offered: ${h.evidence.join(' | ')}\nPredicted signature: ${h.predicted_signature}\n\nChecks: (a) is every cited line real and does it say what is claimed? (b) does the mechanism produce the OBSERVED signature (one of 256 values out of bounds by 0.022, max rel 0.44, same under the kill switch, option-OFF build passes, PR 4959 head option-ON passed)? (c) is there a simpler explanation the hypothesis ignores? Cite file:line.`,
    { label: `verify:${h.id}:${k}`, phase: 'Verify', schema: VERDICT }
  ))).then(votes => {
    const v = votes.filter(Boolean)
    const refutes = v.filter(x => x.refuted).length
    return { ...h, votes: v, survives: v.length > 0 && refutes * 2 < v.length }
  })
))
const survivors = verified.filter(Boolean).filter(h => h.survives)
log(`${survivors.length} of ${verified.length} hypotheses survive`)

phase('Synthesize')
const synth = await agent(
  `${FACTS}\n\nSurviving hypotheses after adversarial verification (with the refuters' reasoning):\n${JSON.stringify(survivors, null, 1)}\n\nRefuted hypotheses (for completeness, with the refuters' reasoning):\n${JSON.stringify(verified.filter(h => !h.survives).map(h => ({ id: h.id, claim: h.claim, votes: h.votes.map(v => v.reasoning.slice(0, 400)) })), null, 1)}\n\nWrite the synthesis as plain English (one claim per sentence, no semicolons, define terms at first use). Sections: (1) Short version (at most three sentences: the most likely cause and whether it is a PR4' code defect or a test-setup change). (2) Ranked causes with the evidence (file:line) and what would confirm each on 3bda. (3) The minimal fix for the top cause, as a concrete patch description (files, functions, the exact change), and whether the fix belongs in the cache code, the test, or the test helper. (4) A 3bda diagnostic plan: exact commands using the existing build at /var/tmp/jhan/tron-bp4v/gen (the test binary gen/t_llama_unit, Catch2 v3 filters such as -c "page splits match emulation" and the test name) and a minimal instrumentation patch (what to print: per-token scores of page 1 from qk_group and from the dotter, the block bits, and the reference rows) that distinguishes the top two causes in one run. (5) Open questions. Re-read the code yourself where the hypotheses disagree. Do not run tests or builds.`,
  { label: 'synthesize', phase: 'Synthesize' }
)
return { hypotheses: hyps.length, survivors: survivors.map(h => ({ id: h.id, claim: h.claim, confidence: h.confidence, fix: h.proposed_fix, test: h.how_to_test_on_3bda })), synthesis: synth }