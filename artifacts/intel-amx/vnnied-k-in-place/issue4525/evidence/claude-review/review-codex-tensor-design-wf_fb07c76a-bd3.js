export const meta = {
  name: 'review-codex-tensor-design',
  description: 'Review the codex design for issue 4525 (typed KV-cache tensors): find defects across 8 lenses, merge, adversarially verify each with 3 votes, then run a completeness critic',
  phases: [
    { title: 'Find', detail: '8 finders, one lens each' },
    { title: 'Merge', detail: 'dedup across finders' },
    { title: 'Verify', detail: '3 refuters per finding' },
    { title: 'Critic', detail: 'what is missing' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/8de7e5e8-3924-4198-a7db-7c54b084f87a/scratchpad'
const WT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K'
const COMMON = `
You are one reviewer in a panel reviewing a software DESIGN document (not code) written by the codex agent.
Context: Ben (a tron maintainer) reviewed PR #4424 (positron-ai/tron, branch jhan-amx-vnniK) and asked for typed tensor access to the KV cache instead of raw bf16 pointers. jhan asked codex to (1) confirm Ben's comment #1 is separate from #2/#3, (2) synthesize Ben's straw-man API and his reservation about a separate layout type, (3) if in doubt stop and ask, else (4) create a GitHub issue and write a design for a NEW parent PR that types the EXISTING packed V and native K caches on main, so PR #4424 can later be rebased on it with its VNNI K representation as a local change inside the new type. Codex created issue #4525 and wrote the design.

READ FIRST, in this order:
1. ${SP}/facts.md  (facts the lead already verified: paths, commits, Ben's comments verbatim, the live issue text, tron source facts with line numbers, CI facts, repo rules). Treat it as ground truth unless you find contrary evidence in the source; if you do, say so explicitly.
2. ${SP}/design-text.txt  (plain-text extraction of the design page). The HTML itself is /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/status/design-new-tensor-type.html if you need markup/links.
3. /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/input-2-ai/codex-add-tensor-type.md (jhan's request to codex).
4. Ben's comments verbatim are inside facts.md; the full JSON is /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/github-review.json.
5. tron source: read files at the pinned commits with  git -C ${WT} show f46e48bab498:<path>  (main snapshot the design reviewed) or  git -C ${WT} show 30c4ac82cbb6:<path>  (PR 4424 head) or  git -C ${WT} show 98bb8cb22f94:<path>  (current main tip). Use  git -C ${WT} diff <a> <b> -- <path>  for changes. NEVER checkout, reset, modify, build, or run anything in that worktree. Do not write files anywhere. Do not post to GitHub (gh read-only calls are fine).

RULES FOR FINDINGS:
- Every finding must cite evidence: a file path with line numbers at a named commit, or a verbatim quote from the design text, Ben's comment, jhan's prompt, or the issue. No evidence, no finding.
- Quote the design sentence(s) you are criticizing in design_quote (verbatim, short).
- Distinguish: (a) factual error in the design, (b) design decision you disagree with (say why, name the alternative), (c) ambiguity that would make an implementing agent guess, (d) omission. Put the kind at the start of claim, e.g. "Factual error: ...".
- Severity: blocker = the implementing agent would build the wrong thing or the parent PR could not merge; major = wrong or missing guidance that must change before implementation; minor = should change, low risk; note = worth knowing, no change required.
- Do NOT pad. If a lens yields few findings, return few. Do not repeat things the design already states correctly. Write claims in plain English (define code names at first use inside the claim), one claim per sentence.
- The design explicitly says it compiled nothing and ran nothing; do not report that as a finding unless a specific claim needs a compile to be trusted and the design presents it as settled.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string', description: 'short label, under 12 words' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'] },
          section: { type: 'string', description: 'design section number and name, or "issue #4525", or "process", or "page"' },
          claim: { type: 'string', description: 'kind + the defect, plain English, one claim per sentence' },
          evidence: { type: 'string', description: 'file:lines@commit and/or verbatim quotes that prove the claim' },
          design_quote: { type: 'string', description: 'verbatim sentence(s) from the design being criticized, or "omission"' },
          recommendation: { type: 'string', description: 'the concrete change to the design text' },
        },
        required: ['title', 'severity', 'section', 'claim', 'evidence', 'design_quote', 'recommendation'],
      },
    },
    verdict: { type: 'string', description: 'only for lenses that were asked a direct question: the answer in 1-4 sentences' },
  },
  required: ['findings'],
}

const LENSES = [
  {
    key: 'issue-capture',
    prompt: `LENS: does GitHub issue #4525 capture the request? Compare the LIVE issue title and body (in facts.md; re-fetch with  gh issue view 4525 --repo positron-ai/tron --json title,body  to be sure) against (a) jhan's four action-plan items and the output spec in codex-add-tensor-type.md, (b) Ben's comments #2 and #3 (what he actually asked for: vnni_tensor rank-2 type on the expr precedent, row-wise load/store, no bare bf16_t* with unknown layout, typed kernel boundaries, storage constructed not cast, zero-init invariant preserved), (c) the design's own scope. Check: is the ordering claim right ("before #4424" was changed by jhan to "independent from PR #4424" - does the body still make sense, does the design page still say "before"), is anything in scope that Ben did not ask for, is anything Ben asked for missing from the issue, does the issue say who is assigned and is that right, are links correct (review id 5270587330, comment 5765866077, discussion r4065141577), is the issue body self-contained for a reader who has not seen the PR thread. Also check the design's section 2 table: it labels the comments #1/#2/#3 with times; verify times and sources against the JSON. Answer the direct question in verdict: does the issue capture the request(s)? yes / partly / no, with the gaps.`,
  },
  {
    key: 'ben-fidelity',
    prompt: `LENS: fidelity to Ben's comments and to jhan's interpretation. jhan wrote: "He seemed saying layout and view can be combined. Claude designed the abstraction separation as: layout --> storage --> view, so I guess his point is, layout itself should be view of which it is how storage are presented to client. I tend to agree with his point, assuming my understanding is right." The design says "Your interpretation is mostly right" and folds the address calculation into each view type. Evaluate: (1) is jhan's reading of Ben's reservation correct, and does the design state precisely where it is and is not right; (2) does the design keep everything Ben's straw-man required (private pointer ctor, no data()/pointer conversion, mutable-to-const only, friend detail::vnni_access, storage as aligned array inside kv_block, typed kernel params, arena constructs the type rather than casting, zero-init invariant untouched, bulk ops keep optimized paths) and everything Ben's review #2 required (expr precedent, usual tensor operations, row-wise load/store); (3) where the design DEVIATES from Ben (e.g. const semantics: Ben said "as with std::span, a const view object does not make its elements const", the design instead makes indexing a const matrix return a read-only row, citing view.hpp; the design replaces at() with operator[][]; the design adds slices, iterators, generic expression assignment, set_pair, append_v_row that Ben never asked for) - is each deviation justified and clearly flagged as a deviation the reviewer (Ben) must accept? (4) does the design answer jhan's item 3 correctly (it says no clarification from Ben is needed - is that defensible, or are there questions Ben should be asked before implementation, e.g. whether he wants K typed in the parent even though native K already has a typed view, or whether he wants a single vnni_tensor template covering both K and V layouts as his straw-man implied)? Answer in verdict: is jhan's understanding right, and is codex's synthesis faithful?`,
  },
  {
    key: 'cpp-interface',
    prompt: `LENS: C++ interface soundness against tron's existing tensor machinery. Read at f46e48bab498: h/tron/kernels/expr.hpp (whole file), h/tron/tensor/view.hpp, h/tron/tensor/views.hpp, h/tron/tensor/slice.hpp, h/tron/tensor/tensor.hpp, h/tron/tensor/seq.hpp, h/tron/hardware/tensor.hpp lines 360-400, h/tron/hardware/dmatensor.hpp lines 280-310, h/tron/simd/chunky.hpp or wherever chunky<T,aligned>::set lives (grep in h/tron). Then check every declaration and requirement in design section 5 "Interface design" and the storage paragraphs of section 6: (a) can vnni_view<T,R,D> inherit expr<view_type, R, D> and be consumed by tensor<d0,d1>(expr const&) / operator= and by dtensor conversion as the design claims ("Existing tensor construction and dtensor conversion accept matrix expressions by reading their logical rows") - what does rhs[i] need to return and does the design's vnni_row satisfy std::construct_at(&data[i], rhs[i]) for tensor<d1> rows (look at tensor<N>'s constructors from expr<B,N>); (b) the concept 'expression' requires size_ - does the design's claim "Keep the concept's existing type restriction" cause the rank-2 view to be rejected by any generic function it needs (slice's const_views overload, print operators, set(expr))? (c) the row: it must provide chunk(i) returning fp32s and bf16_chunk(i) - is 'set(expr)' on a row that is not contiguous implementable with the existing chunky/set pattern, and does the design say how the odd/even merge happens per chunk; (d) "Delete overloads for rvalue owners ... Apply the same restriction to owner indexing" - is deleting operator[] && legal/useful, and does an rvalue restriction interact with the trivially-copyable requirement or with std::construct_at usage; (e) the owner must be trivially default constructible AND have "an explicitly defaulted default constructor" while also having "Owner expression constructor / assignment" - is that consistent (a user-provided converting ctor is fine, but check that = default keeps triviality when the class has an alignas array member of bf16 whose default ctor is trivial); (f) "Use placement construction ... A supported C++23 function for starting object lifetimes is another option" - std::start_lifetime_as: check the repo's compiler/library versions (nix files, CMakeLists CMAKE_CXX_STANDARD) and whether it is available; is placement-new on the arena for every block (n_slots*n_heads*n_pages objects) actually needed for a trivially-default-constructible type, or is the design over-specifying (implicit-lifetime types: an array of a trivially-copyable class type has implicit lifetime when created by an allocation function / memcpy... the arena comes from a DMA allocator returning uint8_t[]; discuss precisely and cite [intro.object]/[basic.life] rules for implicit-lifetime types); (g) the 'native_k_view' alias equals the existing k_view type - so a kernel taking const_native_k_view<64,128> accepts ANY const_view<bf16,true,false,seq<64,128>> including one over a row-major V plane in the AVX2 build or any other 64x128 bf16 matrix - does that undermine the "callers cannot confuse packed V with native K" goal for K (the goal holds for V only), and does the design admit it; (h) naming: 'vnni_tensor' for V-only pair interleave vs 'k_vnni_tensor' for K - Ben's straw-man used vnni_tensor<Layout> generically; does the design's naming collide with the child's existing namespace tron::k_vnni and constants; (i) anything in the design that cannot be expressed as written (e.g. 'const bf16' as T with expr base, 'slice<Rows,Cols> overloads that accept the new matrix view' returning 'a small internal slice expression that stores its own copy of the view' while 'Never pass a temporary packed view to the existing general expression slice' - is the existing slice(Owner&) overload going to grab owner.as_view() and then hit the const_views overload by reference to a temporary?). Report only what you can back with the source.`,
  },
  {
    key: 'behavior-preservation',
    prompt: `LENS: does the design preserve the behavior it promises, and does it introduce new behavior it does not flag? Read at f46e48bab498: h/tron/models/kv_cache.hpp lines 1598-1745, 1866-1985, 1985-2120, 2289-2400, and the Note [Zero-Initialized V Slots]; h/tron/models/model.hpp 2730-2850; h/tron/scheduler/full.hpp 2620-2680; h/tron/simd/bf16.hpp 60-115; t/t_llama_unit.cpp 2328-2470 and 1519-1600. Check: (1) The design requires "Ordinary row assignment must preserve the other row in the pair ... It cannot use the current behavior of page::set_v(even), which clears the odd row" and separately keeps append_v_row/set_pair for the cache append. Today set_v(even) is THE model write path and it zeroes the partner, which is what the Zero-Initialized V Slots invariant relies on. Trace: after the design, which operation does model save_v_impl call - the append operation (zeroes partner) or ordinary assignment (preserves partner)? If ordinary assignment, the invariant breaks for the padding row when a page is REUSED with stale odd data (clear_kv_complete_at does not clear V bytes). Does the design say this unambiguously? (2) Ordinary assignment of an even row on never-written storage reads indeterminate bytes (arena is allocated for overwrite, not zeroed) - the design says "that pair must already be initialized" - who guarantees it, and is reading indeterminate bf16 bits UB or merely garbage (bf16 is trivially constructible with indeterminate content; reading indeterminate values of unsigned-char-like types vs __bf16)? (3) Conversion table: "Packed V append from fp16 / float: The existing conversion to fp32 followed by keeping its upper 16 bits" - confirm against set_v impls (srli 16 = truncation) and against fp32s_to_bf16s (truncation with NaN-quieting) and state precisely what differs (NaN payload only? Inf? denormals?), and whether the design's table row "AVX2 row-major V append: Existing row-view .set() conversion ... Preserve its handling of NaN and infinity" is consistent with the CHUNK 8 path (what does chunky::set do for bf16 in AVX2; is there even an fp16 path in the 8-lane build?). (4) 'matrix.set(expr)' "Initialize complete pairs without reading old destination bytes ... Allow the source and destination to be the same matrix" - if source == destination and the op reads both source rows of a pair then stores the pair, fine; but "Other overlapping copies need not work" - is any caller doing overlapping copies today (copy_storage_slot within the same page? append with src==dst page and shifted ranges? check kv_cache.hpp append/copy_from callers and whether src_page == this is possible)? (5) scaled_v_expr takes const bf16s* data and count; the design types its V input - does the design preserve the 'count' semantics (valid tokens; reads count rounded up to even) and the requirement that the padding row is zero after the parent PR, given that the parent changes who zeroes? (6) GOF staging: v_head_fn calls get_v into scratch (CHUNK 16) - the design says "Unpack packed V into the existing temporary buffer supplied by the caller" - ok; but k_head_fn returns .data of the row view - the design says "Keep the parent PR's gof::page_info K callback interface" - consistent. (7) The design's claim "V already uses paired-token storage in the build with 16 fp32 values per vector instruction" - is TRON_CHUNK_SIZE 16 tied to AVX512=ON (CMake default ON) so the AVX2 8-lane build is a real supported configuration the parent must keep compiling? Does anything in CI build with AVX512=OFF (grep .github/workflows and nix/ at f46e48ba)? If nothing does, the design's "Build and test three supported configurations" includes an untested one - say so. (8) EAGLE storage and heterogeneous geometries: does the design's kv_block change (replace the v array with an owner object) keep kv_block_at_storage's static_asserts (sizeof == 2*page*head*2, alignof == storage_alignment) - what is storage_alignment and does alignas on the owner risk changing alignof(kv_block)? Report precisely.`,
  },
  {
    key: 'pr-split-process',
    prompt: `LENS: PR split, revision hygiene, CI evidence, and repository rules. Facts.md establishes that the design's "reviewed main snapshot" f46e48ba (2026-09-15) is NOT the current main; 98bb8cb2 (2026-09-19) is the live tip and the design mislabels it "stale local origin/main". Verify yourself: git -C ${WT} log --oneline f46e48bab498..98bb8cb22f94 -- h/tron/models/self_attention.hpp h/tron/models/model.hpp t/t_llama_unit.cpp h/tron/models/common.hpp t/CMakeLists.txt ; and git -C ${WT} diff --stat f46e48bab498 98bb8cb22f94 -- h/ src/ t/ . Then assess: (1) which of the design's step-7 files changed on main since the snapshot, and what that means for the implementing agent (it must start from 98bb8cb2 or newer; are there new callers of k()/v()/set_v/get_v/v_data/scaled_v in self_attention.hpp at 98bb8cb2 that the design's caller inventory misses - grep them at both commits and diff the counts); (2) the design's section 3 table row "Stale local origin/main 98bb8cb2 ... already out of date" - state the correct relationship; (3) PR 4424 also changes self_attention.hpp (+90) and main changed it by 432 lines since the merge-base - the design's "Then update PR #4424: Rebase the child's commits onto the completed parent" - is the conflict risk named? (4) The child's t_llama_unit.cpp changes (+439) vs main's (+364) since the merge-base: same file, likely conflicts; named? (5) CI: the design's S13 says the Nix test build leaves AMX off and asks for "A required CI job must build with AMX enabled" - check facts: is there any required job that can build with TRON_AMX_DISPATCH=ON today (README.ci.md at 98bb8cb2, .github/workflows/*.yml at 98bb8cb2, nix/*.nix); memory says PR #4505 (jhan-amx-deb-preset) adds the AMX preset line for the deb build - check  gh pr view 4505 --repo positron-ai/tron --json title,state,body  and whether it is relevant to the parent's CI evidence; is the design's demand realistic, and does it contradict AGENTS.md "do not create a dedicated CI job"? (6) Repo rules the design quotes (draft stack, Skip benchmarks, Run CI) - verify verbatim against AGENTS.md at 98bb8cb2 and note any misquote; (7) the design says "Exclude TRON_K_VNNI ... from the first pull request" and "Only the PR based on main may become ready for review. Keep #4424 draft until its parent merges" - is #4424 currently draft (yes per facts) and does the plan require re-targeting #4424's base to the parent branch (GitHub PR base) - the design does not mention changing the base branch of #4424 to the parent branch, which the AGENTS.md stack rule implies; (8) jhan's request said "we'd spin out a new PR ... And then we update PR #4424 to be atop the new PR" - does the design's section 3 diagram and step list deliver exactly that, and does it correctly separate what stays in the child (Ben's comment #1 worker index, TronCpp.hs generator) - does the design mention that the ingest code generator (ingest/src/TronCpp.hs) is where Ben's #1 lands? (9) The issue title/body edit by jhan ("independent from" instead of "before") vs the design's "Typed cache tensors before PR #4424" heading and repeated "parent/child" framing - is there a substantive difference (independent = could merge in any order?) that the design must reconcile, given the child must be rebased on it either way?`,
  },
  {
    key: 'simplicity-scope',
    prompt: `LENS: simplicity and scope (the project's coding rule: minimum code that solves the problem, nothing speculative, no abstractions for single-use code, push back when a simpler approach exists). Ben asked for: a vnni_tensor rank-2 type on the expr precedent with the usual tensor operations and in particular row-wise load/store; typed kernel boundaries; no bare pointers. The design adds: full matrix expression interface, row expressions with chunk/bf16_chunk, generic row .set(expr) preserving the partner, matrix .set(expr), owner expression constructor/assignment, slice<Rows,Cols> and slice<Cols> overloads with a new internal slice expression type, iteration over rows and elements, append_v_row overloads for bf16/fp16/float for both V layouts, set_pair with an even+zero variant, page::k_tensor/v_tensor accessors, removal of page::v_data, compile-time layout checks in tests, const-conversion rules, rvalue-owner deletions, placement construction of every block in every arena at allocation and restore. For each added element decide: is it needed to satisfy Ben and to let PR 4424 be rebased (the child needs: typed K/V plane params for qk_vnni_128x4 / weights_times_v_128x4 / qk_rowmajor_128x4, a typed row save/load for save_k/save_v, typed row extraction for GOF staging, typed copy for copy_storage_slot, and a typed plane for the AVX-512 qk_group reader), or is it speculative? Which callers TODAY (grep at f46e48bab498 and 98bb8cb22f94 for set_v, get_v, v_data, v_ptr, scaled_v, \\.v\\[, k_view, k_at, \\bk\\( in h/ src/ t/) would use slices of the packed matrix, iteration, or generic expression assignment into packed V? If none, say the design should defer those (YAGNI) and list what the minimal parent needs. Also: is 'native K' typing in the parent needed at all (native K already has view<bf16,true,false,seq<64,128>> - the design itself keeps it), or is the parent really "type packed V + type the kernel params"? Does the design over-specify implementation detail that constrains the implementer without a reason (e.g. "Each iterator must store the array's memory address and the coordinates directly", "Use a small internal slice expression", "Initially require a dimension slice to start at a whole SIMD chunk")? Conversely, is anything the child needs MISSING from the parent's scope (e.g. a typed plane accessor for a whole page that the AMX PV kernel gets today via v_data; a typed 'row view into scratch' for GOF; a typed const plane for the software scaled_v; a typed accessor by kv_storage_offset for append/copy paths that use kv_block_at_storage)? Produce a table-like list in recommendation: keep / defer / missing.`,
  },
  {
    key: 'handoff-actionability',
    prompt: `LENS: is the design actionable for the implementing agent without guessing? Read design sections 5-8 closely and look for: contradictions between sections; requirements stated as prohibitions without a positive alternative; ambiguous names (k_tensor/v_tensor vs existing k()/v(); 'append_v_row' vs existing 'append_v' and 'set_v' - which existing function maps to which new one, and which existing functions are deleted, renamed, or kept); missing signatures (the design shows kernel signatures with 'explanatory names' and says 'Preserve the order and names of the remaining parameters' - is that enough); the step list's completion checks - are they checkable (e.g. "Check the generated code to confirm that construction does not initialize either plane" - how, with what command; "Compare generated instructions for the combined even-row write and partner clear" - with what baseline and tool); the 'Definition of done' - is each item testable; the 'Where to build and run tests' section - does it cite the right machines and rules (facts.md: build on claude-box requires nix in ~/.nix-profile which memory says is gone; sw-dev-01 is named by the design - is sw-dev-01 mentioned anywhere in the tron repo AGENTS.md or run-tron-tests SKILL.md at 98bb8cb2? grep it; and delphi-3bda is the user's CI machine with lease rules - does the design's paragraph match the user's actual rule (check CI lease via lib-guard) or does it invent process?); does the design tell the implementer which commit to branch from (it says 'updated main' and pins f46e48ba as 'reviewed main snapshot' while the real tip is 98bb8cb2 - contradictory guidance?); does it specify the CMake/Nix configurations to build (three) with the exact flags; does it define what 'the child's existing rules for how long that buffer remains valid' are or point to them; are the S1-S13 source references sufficient to find each claimed fact (spot-check at least 8 of the 38 pinned links: open the cited line range at the cited commit and confirm the range contains what the design says it contains - report any citation whose range does not support the sentence that cites it). Also check whether the design's 'Words used here' table defines every code name it later uses (grep the design text for identifiers like scaled_v_expr, kv_block, book, page, gof, chunky, seq, TRON_CHUNK_SIZE, TRON_AMX_DISPATCH, TRON_K_VNNI, dotter, set_pair, append_v_row, k_tensor, v_tensor, vnni_access) and whether each is defined at or before first use.`,
  },
  {
    key: 'formulas-and-page',
    prompt: `LENS A (arithmetic): independently verify the two layout formulas and sizes in design section 4 against the source, not against codex's script: packed V offset (token/2)*(2*D) + 2*dim + token%2 versus kv_block::v declared as bf16s v[page_size/2][head_size/chunk_size*2] with bf16s = 16 bf16 under TRON_CHUNK_SIZE 16 (kv_cache.hpp@f46e48bab498 lines 2190-2205) and versus set_v's store pattern (2289-2320: element (i, token) at v_ptr + i*2 + token%2 within the pair block); blocked K formula versus k_vnni::index in h/tron/kernels/k_vnni.hpp@30c4ac82cbb6 (note the design writes R/16 where the child hardcodes TOKEN_BLOCKS_4 = 4; is the design's generalization to R correct for the child's pair_base which also uses TOKEN_BLOCKS_4; and is the design right that the blocked K formula is NOT a transpose of the V formula). Write and run your own small Python check in a heredoc (no files) enumerating storage order from the kv_block declaration semantics, and report whether codex's check_layouts.py (evidence dir) tests the same thing or a tautology (it enumerates physical order from the formula's own structure - does it independently derive order from the declaration?). Also check the table 'Computed size and mapping checks': plane sizes for 64x{64,128,256,512} in bytes and whether head_size 64 is even legal for the packed path (set_v requires head_size % 32 == 0; scaled_v requires head_size in {64,128,256,512}; kv_block requires head_size/chunk_size integral) - does the design's "column count must be positive and divisible by the number of values in one SIMD chunk" (16) match the stricter set_v requirement (32) and does it say which wins. LENS B (page quality against the user's plain-English rules in CLAUDE.md and the project's term list): sample sections 1, 2, 5 and 8 of the design text; report rule violations that matter for a reader (undefined code names at first use, two claims per sentence, numbers without units/meaning, idioms, citations replacing sentences) - at most 8 concrete examples with fixes, plus counts if you can compute them with a quick grep; check the page's terminology against the project CLAUDE.md term list and the PR 4424 vocabulary (the PR and code say "VNNI layout", "shared block save", "save" vs "store"; the design says "packed V", "blocked packed K", "block write", "K scatter and gather") and report where the design's vocabulary would confuse a reader of the PR or of the code (cite the code's Note [K VNNI storage] naming); check the page's 'Review findings' nav label vs the section it points to; report the 267 non-ASCII characters only if the page is meant to be published as an artifact (note the user's memory rule about pure-ASCII artifacts - state it as a note, not a defect of the design content); check that the two CSS 'diagrams' (arrows built from text) render meaning that the prose does not already carry, per the diagramming rule (depict the mechanism, not its name), and whether a real figure would help (e.g. the pair layout figure exists; is there a figure showing who zeroes the odd partner and when, which is the trickiest invariant?).`,
  },
]

phase('Find')
log('Find: 8 lenses in parallel')
const found = (await parallel(LENSES.map(l => () =>
  agent(COMMON + '\n' + l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS })
    .then(r => r ? { ...r, lens: l.key } : null)
))).filter(Boolean)

const verdicts = {}
for (const f of found) if (f.verdict) verdicts[f.lens] = f.verdict
const raw = found.flatMap(f => f.findings.map(x => ({ ...x, lens: f.lens })))
log(`Find: ${raw.length} raw findings from ${found.length} lenses`)

phase('Merge')
// Number the raw findings deterministically (finder order = LENSES order, then finder's own order).
raw.forEach((f, i) => { f.rid = 'R' + String(i + 1).padStart(2, '0') })
const compact = raw.map(f => `${f.rid} [${f.severity}] (${f.lens}) ${f.title} :: section=${f.section} :: ${String(f.claim).slice(0, 320)}`).join('\n')
const GROUPS = {
  type: 'object',
  properties: {
    groups: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'F01, F02, ...' },
          title: { type: 'string', description: 'merged title, under 12 words' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'] },
          members: { type: 'array', items: { type: 'string' }, description: 'raw ids R.. that describe the same defect; the FIRST member is the primary (clearest, best evidence)' },
        },
        required: ['id', 'title', 'severity', 'members'],
      },
    },
    dropped: { type: 'array', items: { type: 'string' }, description: '"Rnn: reason" for raw findings dropped as unsupported (no evidence) - normally empty' },
  },
  required: ['groups', 'dropped'],
}
const grouping = await agent(`You group review findings. Below is a compact list of ${raw.length} raw findings from 8 reviewers (id, severity, lens, title, design section, start of the claim). Produce groups so that findings describing the SAME defect (same design sentence or same mechanism) share one group, and distinct defects stay distinct even when they touch the same section.
Rules:
- Every raw id appears in exactly one group or in 'dropped'. Drop only if the finding is plainly unsupported; normally drop nothing.
- Put the clearest / best-evidenced member FIRST in 'members'.
- Group severity = the highest among members unless that is clearly wrong; then justify nothing, just pick.
- Order groups by severity (blocker, major, minor, note), then by design section order (issue, 2, 3, 4, 5, 6, 7, 8, page, process).
- Output ONLY the grouping (ids, titles, severities). Do not restate claims or evidence. Do not read any files.

RAW FINDINGS:
${compact}`, { label: 'merge-groups', phase: 'Merge', schema: GROUPS })
if (!grouping) throw new Error('grouping agent returned null')
const byRid = Object.fromEntries(raw.map(f => [f.rid, f]))
const seen = new Set()
const mergedFindings = []
for (const g of grouping.groups) {
  const members = g.members.filter(m => byRid[m] && !seen.has(m))
  if (!members.length) continue
  members.forEach(m => seen.add(m))
  const prim = byRid[members[0]]
  const others = members.slice(1).map(m => byRid[m])
  mergedFindings.push({
    id: g.id,
    title: g.title || prim.title,
    severity: g.severity || prim.severity,
    section: prim.section,
    claim: prim.claim,
    evidence: prim.evidence,
    design_quote: prim.design_quote,
    recommendation: prim.recommendation,
    lenses: [...new Set(members.map(m => byRid[m].lens))],
    members,
    also: others.map(o => ({ rid: o.rid, lens: o.lens, title: o.title, claim: o.claim, evidence: o.evidence, recommendation: o.recommendation })),
  })
}
// Any raw finding the grouper forgot becomes its own group.
let extra = 0
for (const f of raw) if (!seen.has(f.rid) && !grouping.dropped.some(d => d.startsWith(f.rid))) {
  extra++
  mergedFindings.push({ id: 'F' + String(mergedFindings.length + 1).padStart(2, '0'), title: f.title, severity: f.severity, section: f.section, claim: f.claim, evidence: f.evidence, design_quote: f.design_quote, recommendation: f.recommendation, lenses: [f.lens], members: [f.rid], also: [] })
}
const merged = { findings: mergedFindings, dropped: grouping.dropped }
log(`Merge: ${merged.findings.length} unique findings from ${raw.length} raw (${merged.dropped.length} dropped, ${extra} ungrouped kept)`)

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean', description: 'true if the finding is wrong, unsupported, or already handled by the design' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reason: { type: 'string', description: 'why, with the evidence you checked (file:lines@commit or quote)' },
    correction: { type: 'string', description: 'if the finding is partly right: the corrected claim; else empty' },
    severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'], description: 'your independent severity for the finding as corrected' },
  },
  required: ['refuted', 'confidence', 'reason', 'severity'],
}
const VERIFY_LENSES = [
  { key: 'source', text: 'SOURCE-TRUTH lens: re-derive the claim from primary sources only (tron source at the named commits via git show, Ben\'s comment text, jhan\'s prompt, the live issue). If the cited lines do not say what the finding says, or the finding misreads C++ semantics, refute. If you cannot verify, default to refuted=true with confidence low.' },
  { key: 'design-text', text: 'DESIGN-TEXT FAIRNESS lens: read the WHOLE design text and check whether the design already states, handles, or explicitly defers what the finding criticizes (findings often miss a sentence elsewhere in the page). Refute if the design already covers it adequately; if it covers it only partly, do not refute but write the correction. Also refute if the finding attacks a choice the design flags as deliberate AND the finding gives no evidence the choice is wrong.' },
  { key: 'intent', text: 'INTENT lens: judge against what Ben asked for (comments #2/#3 verbatim in facts.md) and what jhan asked codex for (codex-add-tensor-type.md). Refute if the finding would push the design away from Ben\'s or jhan\'s stated intent without saying so, or if it is a matter of taste with no consequence for the implementing agent or for Ben\'s acceptance. Set severity by consequence: would the implementer build the wrong thing (blocker), must the text change before implementation (major), should it change (minor), or is it just worth knowing (note).' },
]

phase('Verify')
log(`Verify: ${merged.findings.length} findings x 3 refuters`)
const verifyOne = (f) => parallel(VERIFY_LENSES.map(v => () =>
  agent(COMMON + `
You are an ADVERSARIAL VERIFIER. Your job is to try to REFUTE one finding from a fellow reviewer. ${v.text}

THE FINDING (JSON):
${JSON.stringify(f, null, 1)}

Return refuted=true only with a concrete reason and evidence. Return refuted=false only if you checked the evidence yourself and it holds.`,
    { label: `verify:${f.id}:${v.key}`, phase: 'Verify', schema: VERDICT })
    .then(r => r ? { ...r, lens: v.key } : null)
)).then(votes => {
  const vs = votes.filter(Boolean)
  const notRefuted = vs.filter(x => !x.refuted).length
  const survives = notRefuted >= 2
  return { ...f, votes: vs, survives }
})

const verified = (await pipeline(merged.findings, verifyOne)).filter(Boolean)
const confirmed = verified.filter(x => x.survives)
const rejected = verified.filter(x => !x.survives)
log(`Verify: ${confirmed.length} confirmed, ${rejected.length} rejected`)

phase('Critic')
const CRITIC = {
  type: 'object',
  properties: {
    missing: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'C01, C02, ...' },
          title: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'] },
          section: { type: 'string' },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          design_quote: { type: 'string' },
          recommendation: { type: 'string' },
          lenses: { type: 'array', items: { type: 'string' } },
        },
        required: ['id', 'title', 'severity', 'section', 'claim', 'evidence', 'design_quote', 'recommendation', 'lenses'],
      },
    },
    overall: { type: 'string', description: 'a 3-6 sentence independent overall assessment of the design: accept as is / accept with changes / redo, and why' },
    strengths: { type: 'array', items: { type: 'string' }, description: 'what the design gets right that a reviewer should say explicitly (cite section)' },
  },
  required: ['missing', 'overall', 'strengths'],
}
const critic = await agent(COMMON + `
You are the COMPLETENESS CRITIC. The panel has produced the confirmed findings below (and rejected others). Your job: what did the panel MISS? Think about: the child PR's actual needs (read h/tron/kernels/k_vnni.hpp, the kv_cache.hpp diff c7844ca2ceb7..30c4ac82cbb6, model.hpp diff, self_attention.hpp diff, full.hpp diff, gof.hpp diff at the child) versus what the parent design provides; the AVX2 8-lane build; EAGLE; heterogeneous geometries (head sizes other than 128; the design's V owner requires even rows and chunk-divisible columns - which geometries exist in t_llama_unit and in production plugins at 98bb8cb22f94, grep 'book<' and kv_geometry uses); thread-safety claims ("Changing the type does not make concurrent stores safe"); the interaction with PR #4424's shared block save (save_k helpers write K columns concurrently - does typing K rows in the parent constrain that); the FPGA hardware-attention path (GOF) and Bill's hwattn streaming join merged on main since the snapshot (git log f46e48bab498..98bb8cb22f94 -- h/tron/models/self_attention.hpp); the test policy in AGENTS.md vs the design's proposed tests; whether the design should have stopped at jhan's item 3 and asked Ben a question; anything about the GitHub issue. Only report items NOT already covered by the confirmed or rejected findings. Same evidence standard.
Also give strengths and an overall assessment.

CONFIRMED FINDINGS:
${JSON.stringify(confirmed.map(({ votes, survives, also, members, ...rest }) => rest), null, 1)}

REJECTED FINDINGS (titles + main refutation reasons):
${JSON.stringify(rejected.map(f => ({ id: f.id, title: f.title, reasons: f.votes.filter(v => v.refuted).map(v => v.reason) })), null, 1)}
`, { label: 'critic', phase: 'Critic', schema: CRITIC })
log(`Critic: ${critic.missing.length} new candidates`)

let criticVerified = []
if (critic.missing.length) {
  criticVerified = (await pipeline(critic.missing, verifyOne)).filter(Boolean)
}
const criticConfirmed = criticVerified.filter(x => x.survives)
const criticRejected = criticVerified.filter(x => !x.survives)
log(`Critic verify: ${criticConfirmed.length} confirmed, ${criticRejected.length} rejected`)

return {
  raw: raw.map(f => ({ rid: f.rid, lens: f.lens, severity: f.severity, title: f.title, section: f.section, claim: f.claim, evidence: f.evidence, design_quote: f.design_quote, recommendation: f.recommendation })),
  lens_verdicts: verdicts,
  raw_count: raw.length,
  merged_dropped: merged.dropped,
  confirmed: [...confirmed, ...criticConfirmed],
  rejected: [...rejected, ...criticRejected],
  critic_overall: critic.overall,
  critic_strengths: critic.strengths,
}