export const meta = {
  name: 'pr4737-review-response',
  description: 'Verify the 6 review findings on PR 4737 against the code and draft fixes + replies',
  phases: [
    { title: 'Verify', detail: '3 lenses per finding' },
    { title: 'Sweep', detail: 'literal completeness + CI facts' },
  ],
}
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-i4500'
const SP = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4500/922a3361-aa01-4c82-918d-776e08c4d97d/scratchpad'
const GUIDE = `# C++ Coding Guide (verbatim, no exemptions beyond those written here)
## Named values
- Define fixed values as named constexpr variables, except for the conventional uses of literal 0 allowed below.
- Prefer literal 0 for zero initialization, resets, zero comparisons, and empty or disabled values when the surrounding code makes its meaning clear.
- Use a named constant when the value encodes a domain-specific rule or the name explains meaning that is not apparent at the use site.
- Name constexpr variables using uppercase letters and underscores between words.
- Append the variable's value to its name, separated by an underscore.
- For values containing punctuation or spaces, use an uppercase representation valid in a C++ identifier.
- When editing a value in source code, rename the variable and update its uses so the suffix matches the new value.
- Keep other literals, including 1, true, and false, in named declarations and refer to them by name. List any further exceptions explicitly.
Examples: constexpr int DAYS_PER_WEEK_7 = 7; constexpr int MAX_RETRIES_3 = 3; bool ROW_ALIGNED_TRUE = true;
## Braces
- Enclose control-flow bodies in braces (if, else, for, while, do). Braces may be omitted only when the entire statement, including its body and any else branches, appears on one physical line.`

const CONTEXT = `You are checking one review comment on tron PR #4737 (branch jhan-amx-vnniK-i4500, head 452b2052c9, base jhan-amx-vnniK at 30c4ac82cb = PR #4424).
The worktree with the PR head checked out is ${WT} (read only; do NOT edit, do NOT run git commands that change state).
The PR diff (base..head) is at ${SP}/pr4737.diff. The review comments are in ${SP}/comments.json (GitHub API JSON, 5 inline comments) and the review body text is below.
Lines quoted as path:line in a comment refer to the PR head file (the worktree).
Return raw data for the orchestrator (not a human-facing message).`

const REVIEW_BODY = `Review body (jhan-positron, 2026-10-01): "C++ guide observation: Added code still uses fixed literals where the guide requires named constants. Examples include alignas(64) in the two new block-conversion helpers and true, false, and sseq<1> in the new row view in self_attention.hpp. Reuse k_vnni::LINE_BYTES_64 for alignment and apply the guide within the added code."`

const FINDINGS = [
  { key: 'C1', text: `[P2] t/t_llama_unit.cpp:1952 (start 1943) "Run the new mixed-layout coverage in the default test build": the new setup is compiled out when TRON_K_VNNI is off. The default CI workflow .github/workflows/gcp-nix.yml builds through nix/tron-build.nix and nix/cmake-tron-test-build.nix; its CMake arguments omit TRON_AMX_DISPATCH and TRON_K_VNNI (both default OFF). The legacy cmake-single-platform.yml enables both but runs only via manual dispatch / workflow_call. The disabled options predate this diff; the concern is that the coverage added here does not run in the default test build, contrary to the repository's test policy (AGENTS.md "Test policy"). Reviewer asks: enable these checks in an existing required test suite; validate by showing a deliberate break in row-major-tail dispatch fails that suite.` },
  { key: 'C2', text: `[P3] h/tron/models/kv_cache.hpp:2448 (start 2443) "Pass the storage reference as one concept": copy_storage_slot adds a separate layout-state index (state_ix) to an existing five-parameter interface; k_storage_ref (physical storage offset + layout-state index) already names the relationship. Readers reconstruct it at each copy and conversion call; EAGLE storage makes it relevant (offset and state index can differ). Suggestion: pass k_storage_ref to copy_storage_slot and to k_block_to_vnni_at; keep source page and copy-range arguments explicit. Readability only; no incorrect mapping found.` },
  { key: 'C3', text: `[P3] h/tron/models/kv_cache.hpp:779 (start 776) "Describe the direct row pointer used by hardware staging": the changed callback in h/tron/scheduler/full.hpp returns k_row_if_row_major directly for a row-major block and calls get_k_row only for a converted block, so the phrase "a 256-byte copy from a row-major block" in Note [K VNNI storage] item 4 describes work the callback avoids. Suggested replacement text:
//   4. The FPGA (field-programmable gate array) staging path
//      (gof::populate -> shuffle_k_entry) needs one row per token.
//      For a row-major block, page_info::k_head_fn returns the row pointer
//      from page::k_row_if_row_major. For a converted block, it gathers
//      the row into caller-owned scratch with page::get_k_row.
//      v_head_fn copies the value row into caller-owned scratch.
//      The staging bytes and the HBM (High Bandwidth Memory,
//      the FPGA device memory) layout are unchanged.` },
  { key: 'C4', text: `[P3] h/tron/models/kv_cache.hpp:701 (start 699) "Name the caller's responsibility for publishing layout bits": the phrase "sets the 16 row bits and the block bit itself" attributes publication to page::set_k_block (per-head block writer), which only writes values; store_k_block (model.hpp) calls note_k_block_saved after storing every KV head, and that order matters (readers must not observe the converted-block bit before all heads have the layout). Suggested replacement:
//   - A full-block save (page::set_k_block) writes the VNNI layout directly.
//     After storing every KV head, the caller uses note_k_block_saved to
//     publish the 16 row bits and the block bit. Any thread of a shared
//     window may perform this save. Every row belongs to that one run.` },
  { key: 'C5', text: `[P3] h/tron/models/kv_cache.hpp:750 (start 749) "Distinguish preserved key values from identical generated tokens": "the tokens are the same either way" (end of Note [Row-major blocks under hardware attention]) can be read as a guarantee of identical generated output; selecting the layout preserves the stored keys but k_vnni::qk_group documents a different fp32 add order from the row-major dotter, so changing which reader runs can change scores. Suggested replacement:
// Every reader selects its access pattern from the block bit.
// Both layouts preserve the stored key values.
// The score accumulation order can differ between readers.
Known measurement (from the author's campaign notes, 2026-09-30): runtron smoke with 1 user at temperature 0, prompts 1024 and 1000, CPU attention and FPGA attention: the policy build (452b2052c9) produced tokens identical to the previous fix build (f34b0fe2ec) in all 4 cells (128/128), and under CPU attention the fix build differed from the PR 4424 head from token 52 (p1024) / token 6 (p1000), attributed to the dotter-vs-qk_group add order.` },
  { key: 'G', text: `Review-body C++ guide observation: added code uses fixed literals where the guide requires named constants: alignas(64) in k_vnni::block_to_vnni and block_to_rows (reuse k_vnni::LINE_BYTES_64), and true, false, sseq<1> in the new row view in self_attention.hpp (const_view<bf16, true, false, seq<operation_head_size>, sseq<1>> k{k_vnni::row_ptr(plane, i)}). The guide text:\n${GUIDE}` },
]

const LENSES = [
  { name: 'code', prompt: 'Lens: CODE CORRECTNESS. Read the actual code in the worktree (the lines the comment names and every caller/callee involved). Is the comment\'s factual claim right? Is the suggested change correct and complete (every caller, both TRON_K_VNNI on and off builds, EAGLE view)? Try to REFUTE the finding first; default to holds=false only with evidence.' },
  { name: 'scope', prompt: 'Lens: SCOPE AND CONVENTIONS. Is the requested change in scope for THIS PR (a stacked draft on PR #4424)? Does it conflict with the repository\'s conventions (AGENTS.md, README.ci.md, existing idioms on the same files, how main spells similar things), with the parent PR #4424, or with the project\'s test policy? Who should decide (author alone, or jhan/reviewers)? Check precedents in the worktree with grep.' },
  { name: 'wording', prompt: 'Lens: WORDING. If the fix is a comment or text change, produce the final replacement text that satisfies: plain English (define a term at first use, one claim per sentence, no idioms, short sentences), the tron convention of referring to Notes by name, and the C++ guide for any code. If the fix is code, produce the exact new code lines (compilable, clang-format style of the file). Also draft the GitHub reply (<= 120 words, plain English, states what was changed or why not, names the commit placeholder <sha>).' },
]

const VERDICT = {
  type: 'object',
  properties: {
    finding: { type: 'string' },
    lens: { type: 'string' },
    holds: { type: 'boolean', description: 'the comment\'s factual claim is right' },
    act: { type: 'string', enum: ['fix-in-this-pr', 'reply-only', 'defer-to-user'], description: 'what the orchestrator should do' },
    evidence: { type: 'array', items: { type: 'string' }, description: 'file:line facts read from the worktree' },
    fix: { type: 'string', description: 'exact replacement text / code, or empty' },
    reply: { type: 'string', description: 'draft GitHub reply' },
    risks: { type: 'array', items: { type: 'string' } },
  },
  required: ['finding', 'lens', 'holds', 'act', 'evidence', 'fix', 'reply', 'risks'],
}

const results = await pipeline(FINDINGS, f => parallel(LENSES.map(l => () =>
  agent(`${CONTEXT}\n\n${REVIEW_BODY}\n\nFINDING ${f.key}:\n${f.text}\n\n${l.prompt}\n\nUse the tools (Read, Grep, Bash for read-only git log/grep) on the worktree. Cite file:line for every evidence item.`,
    { label: `verify:${f.key}:${l.name}`, phase: 'Verify', schema: VERDICT })
)).then(vs => ({ key: f.key, verdicts: vs.filter(Boolean) })))

const SWEEP = {
  type: 'object',
  properties: {
    items: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, line: { type: 'integer' }, literal: { type: 'string' }, kind: { type: 'string' },
      status: { type: 'string', enum: ['allowed-zero', 'already-named', 'needs-name', 'other-exception'] },
      proposal: { type: 'string' } }, required: ['file', 'line', 'literal', 'kind', 'status', 'proposal'] } },
    summary: { type: 'string' },
  },
  required: ['items', 'summary'],
}
const sweep = agent(`${CONTEXT}\n\nTask: a MECHANICAL completeness pass of the C++ guide's named-value rule over the ADDED (+) lines of ${SP}/pr4737.diff, in the product headers only (h/tron/kernels/k_vnni.hpp, h/tron/models/kv_cache.hpp, h/tron/models/model.hpp, h/tron/models/self_attention.hpp, h/tron/scheduler/full.hpp) AND the test files (t/*.cpp) separately. List EVERY literal token on + lines: numeric (including 0, 1, 64, 0xf, 4 KiB numbers in code, template args like sseq<1>), bool (true/false), char, string (except assert/trace message strings and comment text), nullptr. For each: file, head line number (use the worktree file ${WT} to find the line), the literal, kind, and status: 'allowed-zero' (zero init / reset / zero comparison / empty value, per the guide), 'already-named' (a named constant is used), 'needs-name' (a name must be introduced; propose the constexpr name WITH the value suffix and where to put it), or 'other-exception' (explain). Do NOT invent exemptions: a bare true/false or 1 is needs-name unless an existing named constant can be reused. Check with grep how the same files on this branch spell similar things (e.g. existing view<bf16, true, false,...> on main, existing alignas(64)) and report that idiom as a note in the proposal, but still classify per the guide. The guide:\n${GUIDE}`,
  { label: 'sweep:literals', phase: 'Sweep', schema: SWEEP })

const CI = {
  type: 'object',
  properties: {
    facts: { type: 'array', items: { type: 'string' } },
    options: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, change: { type: 'string' }, pros: { type: 'string' }, cons: { type: 'string' }, who_decides: { type: 'string' } }, required: ['name', 'change', 'pros', 'cons', 'who_decides'] } },
    recommendation: { type: 'string' },
  },
  required: ['facts', 'options', 'recommendation'],
}
const ci = agent(`${CONTEXT}\n\nTask: establish the CI facts behind finding C1 and the realistic ways to get the TRON_K_VNNI tests executed by a required CI suite. Read in the worktree: .github/workflows/gcp-nix.yml (jobs tron-build, test-host, test-fpga, test; their runs-on labels and what they run), nix/cmake-tron-test-build.nix and nix/tron-build.nix (CMake arguments, whether a second configuration/matrix is possible), .github/workflows/cmake-single-platform.yml (lines ~325-340: the legacy configure line with -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON; its triggers), README.ci.md (which checks are required; the role of the legacy workflow; the deb preset), CMakeLists.txt + src/tron/CMakeLists.txt (what TRON_K_VNNI requires: TRON_AMX_DISPATCH; AVX512 flags; whether the AMX kernels compile on AMD runners and whether the VNNI tests need AMX hardware or only AVX-512 BF16), AGENTS.md (test policy and PR CI policy), and t/t_k_vnni_layout.cpp + t/t_llama_unit.cpp + t/t_amx_dispatch_dtype.cpp (what runs when TRON_K_VNNI is off: do these binaries still run with a row-major slot, i.e. is there partial coverage in default CI?). Also \`git log --oneline -5 -- nix/cmake-tron-test-build.nix .github/workflows/gcp-nix.yml\` for recent ownership. Facts: cite file:line. Options: at least (a) add -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON to the nix test build for everyone, (b) a second nix test configuration/matrix leg, (c) a separate CI PR against main after #4424 lands (precedent: PR #4505 added TRON_AMX_DISPATCH to the deb preset; PR #2999 'Enable Delphi AMX build in OCI CI' exists), (d) accept the legacy workflow as the executing suite via manual dispatch. For each, say what breaks or changes for other PRs (e.g. the default CI test binaries would then test the VNNI layout instead of row-major; runners without AMX run the AVX-512 fallback). Say who decides.`,
  { label: 'sweep:ci-facts', phase: 'Sweep', schema: CI })

const [sweepR, ciR] = await Promise.all([sweep, ci])
return { results, sweep: sweepR, ci: ciR }