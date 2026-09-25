export const meta = {
  name: 'review-typed-kv-parent',
  description: 'Review the issue-4525 parent implementation diff: multi-lens finders, adversarial verification, completeness critic',
  phases: [
    { title: 'Find', detail: '8 lens reviewers over the diff and the design' },
    { title: 'Verify', detail: '3 refuters per finding' },
    { title: 'Critic', detail: 'completeness against the design tables' },
  ],
}

const W = '/home/jhan/workspace/ai-runs/tron-issue4525'
const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a726337-9373-4eb4-935f-269e8630de97/scratchpad'

const CONTEXT = `
You are reviewing an UNCOMPILED C++ change in a git worktree of the tron repository at ${W}
(branch jhan-kv-typed-tensors, base = origin/main 0a51385e95). READ-ONLY: do not edit any file,
do not run git commands that change state, do not build (this machine has no compiler for tron).

What the change is: the implementation of GitHub issue positron-ai/tron #4525, "Introduce typed
KV-cache tensors for packed V and native K", the parent of PR #4424. Only the parent scope:
typed packed-V owner/view/row (h/tron/tensor/v_vnni.hpp, new), an intrinsics-free declarations
header (h/tron/tensor/kv_cache_fwd.hpp, new), kv_cache.hpp integration (kv_block::v becomes the
owner, set_v/get_v take typed rows, v_packed accessor, append_v -> copy_token, scaled_v_expr takes
the packed view, arena block construction), model.hpp save_v_impl, AMX kernel signatures
(qk_rowmajor_128x4 takes const_native_k_view<64,128>, weights_times_v_128x4 takes
v_vnni_view<const bf16,64,128>), self_attention.hpp call sites, full.hpp GOF callback, and the tests
t_llama_unit / t_amx_numerics / t_amx_dispatch_dtype / heterogeneous_scheduler_compile.

Files to read:
- The unified diff of all modified files: ${S}/parent.diff (also visible via the worktree).
- The two NEW headers (not in the diff): ${W}/h/tron/tensor/v_vnni.hpp and ${W}/h/tron/tensor/kv_cache_fwd.hpp
- The design document (plain text, sections 1-10; sections 5, 6, 7, 8 are the contract): ${S}/design.txt
- Round-4 design-review findings that the implementation should not repeat: ${S}/r4-findings.md (skim for items relevant to your lens)
- The original files at the base commit: use \`git -C ${W} show origin/main:<path>\` (e.g. h/tron/models/kv_cache.hpp)
- Repository rules: ${W}/AGENTS.md and ${W}/t/AGENTS.md

Known facts (do not re-report these as findings):
- The production V buffer for tp*/host_bf16 executors is hardware::btensor = dmatensor<bf16,N> with dma = true; host uses tensor<N> (dma=false); host_fp16 uses dmatensor<fp16,N>. The design text saying the model source has dma=false is wrong; the implementation deduces the flag from the buffer type.
- At unmodified main, t/t_amx_dispatch_dtype.cpp does not compile with TRON_AMX_DISPATCH=ON because its apply_page_range call lacks the batch_queries argument; the diff fixes that call.
- The 8-lane (TRON_CHUNK_SIZE == 8, AVX2) build keeps row-major V; the packed classes must be complete there but the packed operations and v_vnni_row::chunk exist only at 16 lanes. t_llama_unit and t_heterogeneous_scheduler already do not compile at 8 lanes on main (unguarded set_v/get_v calls); that is out of scope.
- No CI or hardware run has happened yet; the code will next be compiled on delphi-3bda with clang-19 (C++23, -Wall -Wextra -Wpedantic, -Werror is NOT on) in configs: 16-lane AMX on/off, 8-lane AMX off, Debug.
- The user's C++ guide asks for named constexpr constants with the value in the name (e.g. PAGE_TOKENS_64); the repo already follows this in amx_attn_iface.hpp.

Report format: return findings ONLY for things you have verified by reading the actual code (quote the lines). For each finding give: title; file and line (of the worktree file, not the diff); severity (major = will not compile, wrong behavior, data race, violates the design contract or a repository rule; minor = should fix before review; note = optional); the claim; the evidence (quoted code or design text with location); a concrete recommendation (exact replacement text when small). Do not pad: zero findings is a valid answer. Do not report style preferences that clang-format will settle. Do not report the known facts above.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['major', 'minor', 'note'] },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          recommendation: { type: 'string' },
        },
        required: ['title', 'file', 'line', 'severity', 'claim', 'evidence', 'recommendation'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['findings', 'summary'],
}

const LENSES = [
  { key: 'compile', prompt: `LENS: will this compile with clang-19 in C++23? Check every template declaration and out-of-class definition (requires-clauses must match exactly), friend declarations and private access (v_vnni_row ctor from v_vnni_view, v_vnni_view ctor from v_vnni_tensor and detail::v_vnni_access), converting constructor constraints, const-correctness of every accessor (page::v_packed const, kv_block const& -> as_view() const&), template argument deduction at EVERY call site of set_v/get_v/append_v_row/load_row/copy_token (model.hpp save_v_impl, full.hpp lambda, kv_cache.hpp forwarding overloads, all test call sites), the explicit-vs-implicit conversions relied on (const_view from pointer is explicit; v_vnni_view<bf16> -> v_vnni_view<const bf16> implicit), the type identity between page::k<geometry>(slot,kv_head) on a const page and const_native_k_view<64,128> (row_major<seq<64,128>> vs std::integer_sequence<ptrdiff_t,128,1>), name lookup of load_row/copy_token/append_v_row from inside struct page, uses of tensor<d0,d1>(expr<B,d0,d1> const&) with the packed view, the intrinsics used (_mm256_load_epi32 needs AVX512VL; _mm512_cvtph_ps), the placement array new-expression, and unused-variable / unused-typedef warnings (-Wall). Also check the 8-lane build: everything under TRON_CHUNK_SIZE != 16 in kv_cache.hpp and v_vnni.hpp must still compile (classes complete, no reference to 16-lane-only members from unguarded code; scaled_v_expr 8-lane constructor).` },
  { key: 'behavior', prompt: `LENS: behavior preservation, bit for bit. Compare every moved SIMD body in v_vnni.hpp (append_v_row for bf16/fp16/float even and odd, load_row for float/bf16 even and odd, copy_token four parity branches, v_vnni_row::chunk) against the original page::set_v / get_v / append_v / scaled_v_expr::even_part+odd_part bodies at origin/main (git show origin/main:h/tron/models/kv_cache.hpp lines ~1860-1920 and ~2280-2475). Check the address arithmetic: pair_base, the i*2 offsets, the pair-row stride 2*Cols, the scaled_v_expr data pointer (const bf16s* built from the plane pointer; the loop uses data + i*(head_size/chunk_size) in bf16s units), the 8-lane scaled_v_expr view pointer, copy_storage_slot's 16-lane path via append_v -> copy_token (source/destination pages, storage offsets, const-ness), the model's set_v argument (&vs[ix][kv_head*head_size] same as before), full.hpp get_v destination. Check construct_kv_blocks: arena selection, uniform whole-arena array bound (bytes / sizeof block), heterogeneous per-slot offsets (n_pages * location.byte_offset), that it is called for both arenas on construction and only for the reclaimable arena on restore, that EAGLE's extra slot is covered in the uniform case, that nothing clears memory (default-initialization, not value-initialization), and that it does not run before the member sizes it reads are set. Check that fill_random/fill_storage_slot, copy_storage_slot 8-lane, K paths, completion counters and page_info K callback are untouched.` },
  { key: 'design', prompt: `LENS: conformance to the design document sections 5 (Interface design), 6 (Behavior the implementation must preserve) and 7 (Implementation steps, step table rows 1-6). Walk every table row and bullet of those sections and check the implementation does what it says, and does NOT add what it forbids (e.g. no dim/element/const_element/shape0/valid members without a caller, no public pointer route, no copy_plane, no requires-clauses on the class templates (static_assert in class body instead), no bf16_chunk override, v_ prefix, header homes, include boundaries: amx_attn_iface.hpp must stay intrinsics-free and include kv_cache_fwd.hpp, kernels-to-tensor include direction, comment/Note replacements listed in section 6 'Copies and hardware preparation' (kv_cache.hpp Notes, model.hpp two comment sites, self_attention.hpp k0 comment), Note [Zero-Initialized V Slots] wording, named layout Note in the new header with See Note cross references). Also check the decision record items Q1-Q4/D5 are implemented as 'proposed' (const at both ranks, operator[] rows, smaller scope, native K alias used at the QK kernel and the whole-plane call in self_attention.hpp). Report each deviation with the design sentence quoted.` },
  { key: 'tests', prompt: `LENS: tests. (a) Repository test policy in ${W}/AGENTS.md and ${W}/t/AGENTS.md: every new or changed assertion must protect a durable contract, no tautologies, no testing of implementation details without a consumer, regression tests only for real defects; judge the new TEST_CASE 'packed V rows keep their bits...' and the new STATIC_REQUIRE block in 'attention operations resolve to typed KV slots'. (b) Correctness of every expected constant in the new test: fp32 bit patterns -> bf16 truncation (0x3f80ffff->0x3f80, 0x7f800001->0x7f80, 0x7fc00000->0x7fc0, 0xbf818000->0xbf81), fp16 values 1.0/65504/-2^-14/0.5 -> fp32 -> bf16 truncation (0x3f80, 0x477f, 0xb880, 0x3f00), pattern() distinctness and finiteness, the specials, Catch2 SECTION semantics (the fill runs again for every section), CAPTURE usage, that std::bit_cast and <bit> are available, that fp16(float) exists and converts as assumed (read h/common/numerics/fp16.hpp). (c) Every STATIC_REQUIRE / STATIC_REQUIRE_FALSE in the typed-boundary block: evaluate each requires-expression and type trait against the actual class definitions and say whether it holds (private constructors and is_constructible, deleted rvalue as_view, const row element type, convertibility, the concept probes amx_qk_accepts/amx_pv_accepts against the declarations in amx_attn_iface.hpp). (d) The migrated callers in t_llama_unit.cpp, t_amx_numerics.cpp (PV fixture: heap owner, append_v_row fill, memcpy compare against the independent formula, kernel call), t_amx_dispatch_dtype.cpp (fake signatures, set_v wrap, apply_page_range fix with 'visible' as batch_queries: check the parameter order against self_attention.hpp:1374-1384 and what batch_queries means), heterogeneous_scheduler_compile.cpp. (e) Alignment: every buffer wrapped by v_source_row/v_destination_row/const_view must really be 64-byte aligned (alignas on the array or tensor's chunk_alignment); flag any that is not.` },
  { key: 'callers', prompt: `LENS: callers and API sweep across the WHOLE repository (h/, src/, t/, ingest/src/TronCpp.hs which generates C++, rust/, bin/). Search with grep for every removed or changed API and report any caller the diff did not migrate: page::v_data, kv_block::v_base, page::set_v with a raw pointer argument, page::get_v with a raw pointer argument, qk_rowmajor_128x4 and weights_times_v_128x4 callers/definitions/fakes (there must be exactly one real definition and one fake set), scaled_v_expr constructions, kv_block::v used as an array (e.g. '.v[' or 'v[i_page' or sizeof(v)) in any file, anything that reinterpret_casts a kv_block or its v member, and code generated by the Haskell generator that might call set_v/get_v directly (grep TronCpp.hs for set_v, get_v, save_v, v_data). Also check h/libtron.hpp and what it IWYU-exports: is kv_cache.hpp part of the public C++ API, and does AGENTS.md's 'preserve the public API' rule need an explicit note in the PR? Report exact file:line for anything missed.` },
  { key: 'prose', prompt: `LENS: comments, Notes and plain English. (a) lint-notes syntax: every 'Note [Name]' definition has the '~' underline line directly under it and a name of at least 5 characters; every 'See Note [Name]' / 'Note [Name]' reference in the changed files resolves to an existing definition with the EXACT same name (check Note [Packed V layout], Note [KV block lifetime], Note [Zero-Initialized V Slots], Note [AMX attention dispatch], Note [Tile stores write 16 rows], Note [QK orientation], Note [Shared KV cache mechanics]); grep the repository for each definition. (b) The user's plain-English rules (the CLAUDE.md skill): comments define terms at first use, one claim per sentence, no idioms; flag comments in the NEW header that a newcomer could not follow, and any comment that is now wrong (e.g. mentions cvtepu16_epi32 zeroing, 'v[i/2]', 'k0', 'v_data', pointer-based descriptions). (c) The header-top 'Words used here' paragraphs: are all code names they use accurate? (d) Check the design's exact replacement instructions for comments in section 6 'Copies and hardware preparation' were followed.` },
  { key: 'includes', prompt: `LENS: includes and build boundaries. For each changed/new file list the symbols it uses from other headers and check the include is present (IWYU discipline; the repo runs an optional iwyu-check): v_vnni.hpp (expr, fp32s, bf16s, bf16x16/bf16x32/fp16x16/fp32x16, chunk_size, seq/sseq, view/const_view, fp16, TRON_ASSERT_LT, TRON(...) attributes, std::same_as, std::add_const_t, std::is_const_v), kv_cache_fwd.hpp (std::integer_sequence, size_t, ptrdiff_t), kv_cache.hpp (v_vnni.hpp added; std::is_trivially_* needs <type_traits>; placement new needs <new>), amx_attn_iface.hpp (kv_cache_fwd.hpp only, must stay intrinsics-free: confirm no intrinsics header is reachable through kv_cache_fwd.hpp), amx_attn.cpp (v_vnni.hpp + view.hpp), the tests. Check include ordering matches the repository style (clang-format IncludeCategories in ${W}/.clang-format) and that no header includes something that creates a cycle (v_vnni.hpp <-> kv_cache.hpp, expr.hpp <-> view.hpp). Check the design's include-boundary rules: amx_attn_iface.hpp includes kv_cache_fwd.hpp and nothing with intrinsics; v_vnni.hpp may include kernels/expr.hpp (precedent tensor.hpp); self_attention.hpp gets the types via kv_cache.hpp.` },
  { key: 'adversarial', prompt: `LENS: adversarial. Try to BREAK the change. Think about: aliasing/lifetime of placement-new over the DMA arena while pages already hold raw pointers (kv_blocks_alias); restore_reclaimable_kv_storage after free (are stale views a new hazard?); book::append / copy_from with EAGLE storage offsets through append_v -> copy_token (const page* source, storage offset selection); the heterogeneous construct_kv_blocks lambda capturing 'reclaimable' and 'base' and the return in a templated lambda; whether construct_kv_blocks can run when retained_kv_bytes_ is not yet assigned; integer overflow in bytes / sizeof; whether kv_block is still standard-layout / trivially copyable so memcpy-based paths (copy_storage_slot K memcpy, fill_random) remain valid; whether v_vnni_row::chunk's runtime parity branch changes codegen of the weighted sum (it should not: scaled_v_expr does not use rows); whether the AMX kernel now reads through a view type whose 'data' member could be null (no null check before) and whether callers could pass a view of the wrong page; whether the 'aligned' template flag lies anywhere (a wrapped pointer that is not 64-byte aligned would fault in _mm512_load_si512); thread-safety claims in comments; -Wextra warnings (unused parameters in fakes, comparison of size_t with int in tests, narrowing in braces). Report only what you verified in the code.` },
]

phase('Find')
const found = (await parallel(LENSES.map(l => () =>
  agent(CONTEXT + '\n\n' + l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS })
))).filter(Boolean)
const all = found.flatMap((r, i) => r.findings.map(f => ({ ...f, lens: LENSES[i].key })))
log(`${all.length} raw findings from ${found.length} lenses`)

// Dedup: same file + line within 3 and similar title words
const key = f => `${f.file}:${Math.round(f.line / 4)}`
const seen = new Map()
for (const f of all) {
  const k = key(f)
  if (!seen.has(k)) seen.set(k, f)
  else { const g = seen.get(k); g.title += ' | ' + f.title; g.claim += '\n---\n' + f.claim; g.recommendation += '\n---\n' + f.recommendation; g.lens += ',' + f.lens }
}
const merged = [...seen.values()]
log(`${merged.length} after merge`)

phase('Verify')
const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    severity: { type: 'string', enum: ['major', 'minor', 'note', 'none'] },
    reason: { type: 'string' },
    corrected_recommendation: { type: 'string' },
  },
  required: ['refuted', 'severity', 'reason', 'corrected_recommendation'],
}
const verified = await parallel(merged.map(f => () =>
  parallel([0, 1, 2].map(i => () => agent(CONTEXT + `

You are refuter ${i + 1} of 3. A reviewer claims the following finding about the change. Your job is to REFUTE it by reading the actual code at ${W} (and origin/main via git show where relevant), the design text, and the C++ rules. Default to refuted=true if you cannot confirm the defect concretely (the code line does not say what the finding claims, the compiler would accept it, the design actually permits it, or the recommendation would make things worse). If the finding is real, say so, grade its severity honestly (major/minor/note) and correct its recommendation if needed.

FINDING:
title: ${f.title}
file:line: ${f.file}:${f.line}
severity claimed: ${f.severity}
claim: ${f.claim}
evidence: ${f.evidence}
recommendation: ${f.recommendation}
`, { label: `verify:${f.file.split('/').pop()}:${f.line}#${i}`, phase: 'Verify', schema: VERDICT })))
    .then(vs => ({ f, votes: vs.filter(Boolean) }))
))
const confirmed = verified.filter(Boolean).filter(v => v.votes.filter(x => !x.refuted).length >= 2)
  .map(v => ({ ...v.f, votes: v.votes }))
log(`${confirmed.length} confirmed of ${merged.length}`)

phase('Critic')
const critic = await agent(CONTEXT + `

You are the completeness critic. The finders reported and the refuters confirmed the findings listed below. Your job is different: read the design's section 7 step table (steps 1-6 and the 'AMX numerics fixture migration' bullets) and section 8 'Behavior checks for the implementing agent' table, and list what the implementation OMITTED or only partly did: a design row with no corresponding code or test change, a caller category not migrated, a comment site not updated, a check the design asks the implementer to encode that has no counterpart. Verify each omission by grepping the worktree (do not assume). Also list the 3-5 highest-risk spots a compile on delphi-3bda is most likely to reject, with the exact line.

CONFIRMED FINDINGS SO FAR:
${confirmed.map(f => `- [${f.severity}] ${f.file}:${f.line} ${f.title}`).join('\n')}
`, { label: 'critic', phase: 'Critic', schema: {
  type: 'object',
  properties: {
    omissions: { type: 'array', items: { type: 'object', properties: { design_item: { type: 'string' }, status: { type: 'string', enum: ['missing', 'partial', 'done'] }, evidence: { type: 'string' }, recommendation: { type: 'string' } }, required: ['design_item', 'status', 'evidence', 'recommendation'] } },
    compile_risks: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'integer' }, risk: { type: 'string' } }, required: ['file', 'line', 'risk'] } },
    overall: { type: 'string' },
  },
  required: ['omissions', 'compile_risks', 'overall'],
} })

return { confirmed, rejected: verified.filter(Boolean).filter(v => v.votes.filter(x => !x.refuted).length < 2).map(v => ({ title: v.f.title, file: v.f.file, line: v.f.line, reasons: v.votes.map(x => x.reason) })), critic, summaries: found.map((r, i) => ({ lens: LENSES[i].key, summary: r.summary })) }