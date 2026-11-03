export const meta = {
  name: 'glimmer-amx-review',
  description: 'Adversarial review of the kv_mul-16 AMX kernel change on branch jhan-amx-kvmul16',
  phases: [
    { title: 'Find', detail: 'five reviewers, one lens each' },
    { title: 'Verify', detail: 'three refuters per finding' },
  ],
}

const CTX = `
Review target: the two commits on branch jhan-amx-kvmul16 in the worktree /home/jhan/workspace/ai-runs/tron-glimmer-amx
(base origin/main 6198824246). Get the diff with \`git -C /home/jhan/workspace/ai-runs/tron-glimmer-amx diff origin/main..HEAD\`
and read the full changed files there. Use absolute paths; the shell cwd resets between calls. No build tools are available on
this machine (no nix); reason from the source. The repository is tron (the inference program); AMX = Intel tile-matrix
instructions; a tile = 16 rows x 64 bytes; TDPBF16PS = the bf16 tile multiply; kv_mul = query heads per KV head.
What the change does: the AMX software-attention kernels (h/tron/kernels/amx_attn_iface.hpp, src/tron/kernels/amx_attn.cpp,
call sites in h/tron/models/self_attention.hpp) served kv_mul 4 only; now they are function templates on group_heads,
explicitly instantiated for 4 and 16 (Muse Glimmer 30B: 32 query heads / 2 KV heads / head 128), with the gate shape_ok
widened to 4 or 16. The user's constraints: minimal diff, no renames, no refactor, kv_mul-4 behaviour and generated code
unchanged. Tests: t/t_amx_numerics.cpp (gate, pack layout, QK vs the AVX dotter, PV envelope; now both group sizes, plus a
sentinel check that rows group_heads..15 of s stay unwritten), t/t_amx_dispatch_dtype.cpp (CPU fakes of every kernel entry
point in its own TU, 4-head and new 16-head model cases), t/t_llama_unit.cpp (requires-probes now pass <GROUP_HEADS_4>).
Verified background you may rely on: after the two unpack stages of the 16x16 transpose, 128-bit lane l of u[row_group][k]
holds tile column 4*l+k for rows 4*row_group..+3; output row 4*lane+k uses stage-3 selector 0x88 for lane in {0,2} and 0xdd
for {1,3}, stage-4 selector 0x88 for lane in {0,1} and 0xdd for {2,3} (exhaustively simulated). libtron is a static archive;
the dispatch test's fakes keep amx_attn.o out of the link by defining every entry point.
Report only real defects or omissions with file:line and a concrete failure scenario; no style opinions without a rule.
`

const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
  claim: { type: 'string' }, failure_scenario: { type: 'string' }, fix: { type: 'string' } },
  required: ['id', 'file', 'line', 'severity', 'claim', 'failure_scenario', 'fix'] } } }, required: ['findings'] }

const LENSES = [
  ['correctness', `Lens: kernel and dispatch correctness. Check: the template declarations and definitions agree (requires-clauses identical token for token, noexcept, parameter types) so that the explicit instantiations and the test TU's primary-template fakes link and no ODR problem arises; the store helper's selector derivation and row offsets (s_block + lane*4*stride) produce rows 0..15 in the right order for group 16 and exactly today's four stores for group 4; the pack loop bound and index; the P scratch loop; every call site passes the right group (geometry.kv_mul() / operation_kv_mul); the s_pages buffer has group_heads rows at every caller; the thread_local P per instantiation claim; anything that reads past a 4-head Q group (q.data + kv_head*kv_mul*head_size with kv_mul 16 reads 16x128 bf16: is that inside qs_roped for Glimmer's 32 heads? check llama.hpp/plugin sizing of qs_roped = n_heads*head_size).`],
  ['tests', `Lens: do the tests verify intent? Check t_amx_numerics: both group sizes exercised for pack, QK, PV; the sentinel check is sound (could a real score equal -12345? the fixture bounds); the gate test covers 16 true and 8/2/64-head false; nothing silently skips (SECTION inside an early-return WARN: do both sections still run when AMX is available; does Catch2 re-enter the TEST_CASE per SECTION so the WARN path is evaluated per section and the counts in the summary are what the reader expects). t_amx_dispatch_dtype: the 16-head model (n_heads 16, n_kv_heads 1, dim 2048, hidden_dim 512, vocab 32) - look at h/tron/plugins/llama.hpp and h/tron/models/model.hpp static_asserts and any sizes derived from dim that could fail to compile or assert at runtime (e.g. ranged_mask capacity, scratch widths, minibatch, intermediate sizes, max_kernel_query_width); the fake pack copies group_heads*128 values from input: is the input buffer that large for the 16-head model (qs_roped sizing)? the fill formula values exact in bf16 (1 + h*0.0625 + (i%4)*0.25 up to 1+15*0.0625+0.75 = 2.6875: representable?); probe.group_heads reset between rounds (probe = {} each round) and asserted under packs only; t_llama_unit probes still meaningful. Also: is there any test that would catch a wrong selector pair (e.g. rows 4..7 swapped with 8..11)? The QK-vs-dotter check on 16 heads with distinct random q rows does: confirm the fixture gives distinct rows.`],
  ['wade', `Lens: reviewer Wade's checks (load the skill Wade-code-review if available and apply its code checks): dead symbols or includes, comments that contradict code (every "4", "rows 0..3", "columns 4..15" left in the three source files and the tests: grep them), magic literals in AMX-owned files (0x88/0xdd now named; what about 4 in "u[4][4]", "r < 4", "k < 4", "r * 16", "s + r * 16" - which are pre-existing and which new), names (pair_sel/quad_sel vs the comment's stage numbering: do the comment in the helper and the comment in qk_rowmajor use ONE consistent stage numbering?), silent fallbacks, hot-path cost (the helper is inline; is anything now a function call per page in the 4-head path?), instrumentation ownership, the explicit instantiation list vs group_heads_ok, and whether the header's top comment and Note [AMX attention dispatch] still read correctly for both sizes. Also the commit split: are comment-only hunks really only comments in commit 2 (git show 03eda02e2b)?`],
  ['cpp-guide', `Lens: the repository C++ guide (load the skill cpp-coding-guide and apply it) and the plain-English comment rules (one claim per sentence, terms defined, no idioms). Check literal naming in AMX-owned files (amx_attn_iface.hpp, amx_attn.cpp, t/t_amx_*.cpp): new bare literals 0.0625f, 0.25f, -12345.f (named? UNWRITTEN_ROW_SENTINEL is), 1/2/3 in "1 * ROWS_PER_LANE_4" etc.; template parameter naming; requires-clause style used elsewhere in the repo (grep "requires(" in h/ for precedent); static_assert messages; the two-line using-declaration comment in t_amx_numerics ("the / two group sizes served" split across two using lines - is that readable or a defect); clang-format conformance by eye (80-col limit? check .clang-format ColumnLimit) for every added line over the limit.`],
  ['perf-and-scope', `Lens: performance and scope. (1) For group 16 the QK epilogue does 4x the stores and shuffles; is the helper inlined and unrolled (inline + constexpr selectors + k loop of 4) so no per-row call overhead; any register pressure concern (u[4][4] = 16 zmm live + temporaries: 32 zmm available) that could spill? (2) The 4-head instantiation: enumerate every instruction-level difference you can infer from source vs origin/main (the implementation agent reports the pack and QK kernels identical and PV differing only in the TLS access model of the template's static local: general-dynamic vs local-dynamic). Is the TLS model change a real cost on the hot path (one __tls_get_addr call per PV call?) and is there a zero-cost way to keep the old model (e.g. keep ONE non-template thread_local P defined at namespace scope in the anonymous namespace shared by both instantiations, with the comment adjusted to "rows written by a larger group are harmless because output row i depends only on P row i")? Weigh that against the "P belongs to this instantiation" comment and recommend. (3) Scope creep: anything changed beyond the brief (files, behaviour for kv_mul 4, the kv_mul 8 refusal)? (4) The explicit instantiations: does the deb/CI build with TRON_AMX_DISPATCH=ON compile the 16 kernels on hosts without AMX (yes, -mamx flags per TU) and does anything at runtime touch them before available() is checked?`],
]

phase('Find')
const found = await pipeline(
  LENSES,
  ([key, lens]) => agent(`${CTX}\n${lens}`, { label: `find:${key}`, phase: 'Find', schema: FINDINGS }),
  async (res, [key]) => {
    if (!res) return null
    const verified = await parallel(res.findings.map(f => () =>
      parallel(['refute-by-code: re-open the cited lines and the callers; default refuted=true if the scenario cannot happen',
                'refute-by-rule: does a repository rule, guide or the brief actually require the fix? default refuted=true if it is taste',
                'confirm-by-reproduction-argument: construct the concrete input/state that triggers the failure; refuted=true if you cannot'].map((lens, i) => () =>
        agent(`${CTX}\nYou are a skeptical verifier (${lens}). Finding from lens ${key}: ${JSON.stringify(f)}. Verdict?`,
          { label: `verify:${f.id}:${i}`, phase: 'Verify', schema: { type: 'object', properties: { refuted: { type: 'boolean' }, evidence: { type: 'string' } }, required: ['refuted', 'evidence'] } })))
        .then(vs => { const ok = vs.filter(Boolean); return { ...f, lens: key, votes: ok.map(v => ({ refuted: v.refuted, evidence: v.evidence })), survives: ok.filter(v => !v.refuted).length >= 2 } })))
    return verified
  }
)
const all = found.filter(Boolean).flat()
const confirmed = all.filter(f => f.survives)
log(`${all.length} findings, ${confirmed.length} survive`)
return { confirmed, refuted: all.filter(f => !f.survives) }