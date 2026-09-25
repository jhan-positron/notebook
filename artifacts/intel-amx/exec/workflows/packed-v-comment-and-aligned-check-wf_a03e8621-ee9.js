export const meta = {
  name: 'packed-v-comment-and-aligned-check',
  description: 'Fact-check and plain-English-check a rewritten Packed V comment and an explanation of the view aligned flag',
  phases: [
    { title: 'Check', detail: 'independent lenses: code facts, plain English, newcomer, ISA, code-alignment, word choice' },
    { title: 'Refute', detail: 'adversarial pass on the aligned-flag claims' },
  ],
}

const R = '/home/jhan/workspace/ai-runs/tron-issue4525'
const COMMON = `
Context: C++ repo worktree ${R} (branch jhan-kv-typed-tensors, PR #4557). READ-ONLY task: do not edit, stage, commit, or run builds.
The file under discussion is ${R}/h/tron/tensor/kv_cache_fwd.hpp (its working tree has an uncommitted user change that DELETED a "Words used here" glossary from the header comment; treat that deletion as a decision: never propose reinstating that glossary content, condensed or otherwise).
Definitions of the packed V types: ${R}/h/tron/tensor/v_vnni.hpp (Note [Packed V layout], v_vnni_row ~line 99, v_vnni_view ~165, v_vnni_tensor ~236).
The aligned/dma flags: ${R}/h/tron/tensor/view.hpp, ${R}/h/tron/tensor/views.hpp (dma comment at top), ${R}/h/tron/kernels/chunky.hpp (what aligned selects), ${R}/h/tron/simd/auto.hpp (tron_mm_* macro definitions, chunk_alignment), kv_block in ${R}/h/tron/models/kv_cache.hpp ~line 2477.
Tip: 'cd' in this shell prints a directory listing; use absolute paths or git -C.

CURRENT comment (kv_cache_fwd.hpp lines 27-29), which the user calls "hard reading verbose":
// Packed V: the owner (one aligned plane), the matrix view of Rows tokens x
// Cols dims that knows the address formula, and the logical row of one token.
// T is bf16 (writable) or const bf16 (read-only).
It sits right above:
template <size_t Rows, size_t Cols> struct v_vnni_tensor;
template <typename T, size_t Rows, size_t Cols> struct v_vnni_view;
template <typename T, size_t Cols> struct v_vnni_row;

CANDIDATE rewrites:
[A]
// Packed V types:
// - v_vnni_tensor contains the values: Rows tokens x Cols dims of bf16,
//   starting at an address that is a multiple of 64 bytes.
// - v_vnni_view refers to that array without owning it. It computes where
//   each token's values sit in the packed order.
// - v_vnni_row is one token's Cols values in dim order (view[token]).
// For the view and the row, T = bf16 allows writes, and T = const bf16 is
// read-only.
[B]
// Packed V types (T = bf16 allows writes, T = const bf16 is read-only):
// - v_vnni_tensor contains Rows x Cols bf16 values, 64-byte aligned.
// - v_vnni_view refers to them as Rows tokens x Cols dims.
// - v_vnni_row is one token's Cols values, returned by view[token].
[C]
// Packed V types. v_vnni_tensor contains the values: Rows tokens x Cols dims
// of bf16, starting at a 64-byte boundary. v_vnni_view refers to that array
// and computes where each token's values are. v_vnni_row is one token's Cols
// values, returned by view[token]. In the view and the row, T = bf16 allows
// writes and T = const bf16 is read-only.

DRAFT ANSWER to the user's question "What does 'align' mean? What are alternative words?" about
  // Values for the aligned and dma template flags of view and const_view
  // (view.hpp, and views.hpp for the dma flag).
  inline constexpr bool VIEW_ALIGNED_TRUE = true;
  inline constexpr bool VIEW_DMA_FALSE = false;
Claims:
C1. For view/const_view, aligned=true is a compile-time promise: the address of every chunk the view reads or writes with chunk()/set() (stride-1 last dim) is a multiple of that chunk's byte width, chunk_size x sizeof(T).
C2. The flag only picks the instruction: true -> aligned load/store (16-lane: _mm512_load_ps for fp32, _mm256_load_si256 for bf16/fp16), false -> unaligned loadu/storeu (chunky.hpp specializations; auto.hpp macros).
C3. Required address multiple: 16-lane build fp32 64 B, bf16/fp16 32 B; 8-lane build fp32 32 B, bf16 16 B. For element types without a chunky specialization, the flag has no effect (generic scalar loop).
C4. Nothing checks the promise (constructor accepts any pointer; TODO at view.hpp:13). If true is wrong, the aligned move instruction raises a general-protection fault (process gets SIGSEGV) whenever the compiler emits the aligned move; if the compiler folds the load into another VEX/EVEX instruction's memory operand, a misaligned address does not fault. So a wrong promise is a latent crash, not a checked error.
C5. The flag allocates and pads nothing; the memory owner provides the alignment. For native K: kv_block::k is alignas(kv_block_alignment = max(64, chunk_alignment)) and each K row is head_size x 2 bytes, a multiple of 32 bytes, so every bf16 chunk of every row starts at a multiple of 32 bytes at 16 lanes.
C6. view::last() reads past the end of the data and relies on the alignment so the over-read cannot cross a page boundary (view.hpp ~173-177).
C7. The word "aligned" in the current Packed V comment ("one aligned plane") means something related but different: v_vnni_tensor is alignas(64) (V_PLANE_ALIGNMENT_64), its first element starts at a multiple of 64 bytes.
C8. The name VIEW_ALIGNED_TRUE spells the view template parameter name ("aligned", main's name in view.hpp/views.hpp) plus its value, the same pattern as VIEW_DMA_FALSE.
Alternative words, proposed: in prose "starts on an N-byte boundary" / "its address is a multiple of N bytes"; for a rename of the constant: VIEW_CHUNK_ALIGNED_TRUE, VIEW_SIMD_ALIGNED_TRUE, VIEW_ALIGNED_LOADS_TRUE. Draft recommendation: keep VIEW_ALIGNED_TRUE (matches the template parameter name, and "aligned" is the standard C++/Intel term: alignas, alignof, "aligned load"), and gloss the meaning in the comment instead.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          target: { type: 'string', description: 'A, B, C, C1..C8, alternatives, or recommendation' },
          phrase: { type: 'string', description: 'exact phrase at issue' },
          problem: { type: 'string' },
          evidence: { type: 'string', description: 'file:line or external source (URL / manual section) that proves it' },
          fix: { type: 'string', description: 'corrected text' },
          severity: { type: 'string', enum: ['wrong', 'misleading', 'unclear', 'style'] },
        },
        required: ['target', 'phrase', 'problem', 'evidence', 'fix', 'severity'],
      },
    },
    ranking: { type: 'string', description: 'rank of A/B/C for this lens, best first, with one-line reason (or n/a)' },
    notes: { type: 'string' },
  },
  required: ['findings', 'ranking', 'notes'],
}

const LENSES = [
  { key: 'facts', prompt: `LENS: code facts for candidates A, B, C. Check every sentence of each candidate against v_vnni.hpp and kv_cache.hpp. Is each statement exactly true (contains vs owns, refers without owning, computes where values are, dim order, view[token] returns the row, T applies to view and row only, Rows = tokens, Cols = dims, 64-byte start address)? Flag over-generalizations and anything a reader could misread. Also flag facts a reader of this forward-declaration header NEEDS and every candidate omits (only if missing it would mislead). Cite file:line for each finding.` },
  { key: 'english', prompt: `LENS: the user's plain-english rules for CODE COMMENTS (global CLAUDE.md skill: Rules 2 and 6 in full, Rule 1 only for terms imported from outside the code; also rule 8 short sentences, no semicolons), plus the memory banned-word list (convoy, refund, "in disguise", swept). The user's complaint is "hard reading verbose": judge length too. Check A, B, C phrase by phrase: two claims in one sentence, idioms/phrasal verbs a non-native reader could misread, uncommon words, parentheses doing too much. Do not flag code identifiers. Rank A/B/C.` },
  { key: 'newcomer', prompt: `LENS: newcomer. You are a C++ engineer who has never seen this project. Read ONLY kv_cache_fwd.hpp (as it would look with each candidate in place) and answer, for each candidate: what is each of the three types, who owns memory, what does T change, what does "packed" mean and where would you look it up. List every word you had to guess at, and which candidate you understood fastest. Then open v_vnni.hpp and say whether your first-read understanding was right.` },
  { key: 'isa', prompt: `LENS: x86 ISA semantics of claims C2, C3, C4 (and any speed implication). Verify from primary sources (Intel SDM / Intel Intrinsics Guide entries for _mm512_load_ps, _mm256_load_si256, _mm_load_si128, _mm512_loadu_ps, VMOVAPS, VMOVDQA, VMOVDQA32/64, and the SDM rules on alignment checks for VEX/EVEX memory operands). Use WebSearch/WebFetch if available (load them with ToolSearch). Check: exact alignment each aligned intrinsic requires, which instruction it maps to, whether misalignment faults (#GP) and when a compiler-folded memory operand does not fault. Do NOT accept a claim without a source; if you cannot verify, say "Insufficient data" and name the source needed.` },
  { key: 'code-align', prompt: `LENS: code truth of claims C1, C3, C5, C6, C7, C8. Trace chunk()/set()/last() in view.hpp and the views.hpp rank>=2 path to chunky<T, aligned>. Check the tron_mm_* macros in simd/auto.hpp for both lane counts, including fp16 (defined only under TRON_AVX512_ENABLED?). Check that native K (kv_block::k and its view, and the native_k_view aliases) really satisfies the promise at both lane counts and for every head_size the static_asserts allow. Check whether any PR-added use of VIEW_ALIGNED_TRUE (git -C ${R} grep -n VIEW_ALIGNED_TRUE) points at memory that might NOT be aligned (e.g. a stack array in a test, a row pointer at an odd offset). Cite file:line.` },
  { key: 'words', prompt: `LENS: word choice for "aligned". Survey how this repo names alignment (git -C ${R} grep -n -i "aligned" -- h src | head -200; alignas uses; chunk_alignment; kv_block_alignment; V_PLANE_ALIGNMENT_64) and the standard vocabulary (C++ alignas/alignof, Intel "aligned load"). Evaluate the proposed alternative words and constant names (VIEW_CHUNK_ALIGNED_TRUE, VIEW_SIMD_ALIGNED_TRUE, VIEW_ALIGNED_LOADS_TRUE) and propose better ones if any. Is the recommendation (keep VIEW_ALIGNED_TRUE, gloss in comment) sound under the repo convention rule (match the codebase, surface conflicts)? Also propose a plain-English replacement for the two-line comment above VIEW_ALIGNED_TRUE / VIEW_DMA_FALSE that says what each flag value promises (keep it short, one claim per sentence, <= 80 columns per line).` },
]

phase('Check')
const results = await parallel(LENSES.map(l => () =>
  agent(`${COMMON}\n\n${l.prompt}\n\nReturn findings via the schema. Only report problems you can prove with evidence. Report an empty findings list if there is nothing.`,
    { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS })
    .then(r => ({ lens: l.key, ...r }))))

phase('Refute')
const REFUTE = {
  type: 'object',
  properties: {
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['holds', 'wrong', 'needs-rewording', 'unverifiable'] },
          reason: { type: 'string' },
          evidence: { type: 'string' },
          corrected: { type: 'string' },
        },
        required: ['id', 'verdict', 'reason', 'evidence', 'corrected'],
      },
    },
  },
  required: ['claims'],
}
const refuters = await parallel([
  { key: 'refute-code', lens: 'Read the code yourself and try to REFUTE each of C1-C8. Look for counterexamples: a view whose last stride is not 1, a rank-2 views path that ignores aligned, a type with an aligned specialization not listed, an 8-lane difference, a use site in the PR whose pointer is not aligned. Default to needs-rewording when a claim is true but stated too broadly.' },
  { key: 'refute-isa', lens: 'Try to REFUTE C2-C4 on ISA grounds with primary sources (Intel SDM, Intrinsics Guide; load WebSearch/WebFetch via ToolSearch). Pay attention to: _mm256_load_si256 alignment (32 B), EVEX VMOVAPS zmm alignment (64 B), whether EVEX/VEX folded memory operands check alignment, and whether C4 overstates the crash. Default to unverifiable if you cannot find a source.' },
].map(r => () => agent(`${COMMON}\n\n${r.lens}\n\nReturn one entry per claim C1..C8 (use verdict unverifiable with reason 'out of lens' for claims outside your lens).`,
  { label: r.key, phase: 'Refute', schema: REFUTE }).then(x => ({ lens: r.key, ...x }))))

return { checks: results.filter(Boolean), refutes: refuters.filter(Boolean) }
