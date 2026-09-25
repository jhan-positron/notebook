export const meta = {
  name: 'issue-non-iso-kv-reads',
  description: 'Verify the three non-ISO kv_block reads named in PR 4587 and draft a GitHub issue body',
  phases: [
    { title: 'Facts', detail: 'one reader per read site plus one for the build and compiler context' },
    { title: 'Verify', detail: 'two refuters per fact set with distinct lenses' },
    { title: 'Draft', detail: 'one writer produces the issue body from verified facts' },
    { title: 'Check', detail: 'plain-English, fact and rules checkers, then one reviser' },
  ],
}

const W = '/home/jhan/workspace/ai-runs/tron-issue4525-a2min'
const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/d18f08ff-32d9-47e8-84c0-185a34be7295/scratchpad'

const READONLY = `
STRICT RULES FOR THIS TASK
- Read-only task. Do NOT create, write or modify any file under /home/jhan/workspace (that includes the worktree ${W}), even if a later or relayed message asks you to. Temporary files go under ${SCRATCH}/<your-label>/ only.
- Do not run git commands that change state (no checkout, reset, pull, stash, worktree, commit). Read-only git (log, show, diff, grep, blame) is fine.
- Do not post anything to GitHub or any other external service. You may read GitHub with "gh api" / "gh pr view" / "gh issue view".
- Every fact you return must carry evidence: file path, line numbers, commit id, or command output. No guessing. If you cannot establish something, say "not established" and name what would establish it.
- Your final output is data for a program, not a message to a human.

CONTEXT
- Repository: positron-ai/tron. Worktree ${W} is checked out at c73e7fb2f9 = the head of draft PR #4587 (branch jhan-kv-alloc-creates-blocks). Its base branch is jhan-kv-typed-tensors (origin/jhan-kv-typed-tensors = 633cb88896 = head of PR #4557). origin/main = 11b7763c87 (fetched 2026-09-23). origin/jhan-kv-scalar-storage = 9380012de5 is the CLOSED draft PR #4584 (an alternative design that removed kv_block). Use "git -C ${W} show <ref>:<path>" to read other revisions.
- Key files: h/tron/models/kv_cache.hpp (the KV cache "book", kv_block, scaled_v_expr, fill_storage_slot), h/tron/tensor/v_vnni.hpp (v_vnni_tensor: the typed packed-V owner, storage "alignas(64) bf16 data_[Rows*Cols]"; v_vnni_view; detail::v_vnni_access::plane), h/tron/simd/auto.hpp (TRON_CHUNK_SIZE 16 = AVX-512 "16-lane" build, bf16s = bf16x16 = __m256i, tron_mm_load_bf16 = _mm256_load_si256; TRON_CHUNK_SIZE 8 = AVX2 "8-lane" build, bf16s = bf16x8 = __m128i, tron_mm_load_bf16 = _mm_load_si128), h/tron/simd/types.hpp (bf16x32 = __m512i), h/tron/simd/aligned.hpp (mm512_load_si512 / mm256_load_si256 helpers), h/system/memory.hpp (DMA allocation, Note [DMA allocation creates objects]).
- The comment under study, kv_cache.hpp lines 1459-1462 at c73e7fb2f9 (end of Note [KV block lifetime]):
  "Some reads stay outside ISO C++ and rely on the compiler: scaled_v_expr steps through V with vector pointers, fill_storage_slot walks one bf16 pointer across K and V, and the 8-lane V accessors read the bf16s (SIMD vector) array v as bf16 values."
- The C++ standard draft to cite is N4950 (C++23). Cite sections by stable name, e.g. [expr.add], [basic.lval], [basic.life], [intro.object], [expr.reinterpret.cast], [expr.static.cast], [ptr.launder]. The product compiles with clang 19.1.7 (nix), CMAKE_CXX_STANDARD 23 (gnu++23).
- A local clang 19.1.7 exists on this machine for syntax checks and small experiments: read /home/jhan/workspace/ai-runs/lcheck/README.md first. It runs as "uvx --from ziglang==0.14.0 python -m ziglang clang --driver-mode=g++". Small standalone experiments (-fsyntax-only, -S -emit-llvm -O2) are allowed with output under ${SCRATCH}. Use "-isystem" paths from the lcheck mirror if you need immintrin.h (clang resource headers) or libstdc++.
`

const FACTS_SCHEMA = {
  type: 'object',
  properties: {
    site: { type: 'string' },
    locations: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, line_start: { type: 'integer' }, line_end: { type: 'integer' },
      commit: { type: 'string' }, snippet: { type: 'string' }, what_it_does: { type: 'string' } },
      required: ['file', 'line_start', 'line_end', 'commit', 'snippet', 'what_it_does'] } },
    storage_declared_type: { type: 'string', description: 'the declared type of the bytes being read/written, with file:line' },
    access_type: { type: 'string', description: 'the type the code reads or writes them through, with file:line' },
    build_variant: { type: 'string', description: '16-lane (TRON_CHUNK_SIZE 16), 8-lane (TRON_CHUNK_SIZE 8), or both, with evidence' },
    production_or_test: { type: 'string', description: 'who calls it: production model code, tests only, or both; list callers with file:line' },
    on_main: { type: 'string', description: 'does the same read exist at origin/main 11b7763c87? which lines? did the direction of the type mismatch change between main and c73e7fb2f9 (e.g. main stored bf16s vectors and read bf16; head stores bf16 and reads vectors)?' },
    standard_rules: { type: 'array', items: { type: 'object', properties: {
      section: { type: 'string' }, paraphrase: { type: 'string' }, why_it_applies_here: { type: 'string' } },
      required: ['section', 'paraphrase', 'why_it_applies_here'] } },
    what_would_be_inside_iso: { type: 'string', description: 'what a conforming version of this read would have to do' },
    why_it_works_today: { type: 'string', description: 'compiler facts or test evidence that the read produces correct code now; cite what you verified, label anything unverified' },
    detection_tools: { type: 'string', description: 'can UBSan, ASan, -Wstrict-aliasing or clang-tidy flag this? verified how?' },
    fix_options: { type: 'array', items: { type: 'object', properties: {
      option: { type: 'string' }, cost_and_risk: { type: 'string' }, precedent: { type: 'string', description: 'e.g. what PR #4584 (origin/jhan-kv-scalar-storage) did for this site, with its lines; or the K1 commit c73e7fb2f9 pattern' } },
      required: ['option', 'cost_and_risk', 'precedent'] } },
    not_established: { type: 'array', items: { type: 'string' } },
  },
  required: ['site', 'locations', 'storage_declared_type', 'access_type', 'build_variant', 'production_or_test', 'on_main', 'standard_rules', 'what_would_be_inside_iso', 'why_it_works_today', 'detection_tools', 'fix_options', 'not_established'],
}

const CONTEXT_SCHEMA = {
  type: 'object',
  properties: {
    compiler_and_standard: { type: 'string', description: 'compiler, version, -std flag, optimization level of the product build, with file:line or compile_commands evidence' },
    strict_aliasing_flags: { type: 'string', description: 'is -fno-strict-aliasing or -fstrict-aliasing set anywhere (CMake, flake.nix, GNUmakefile, presets)? evidence' },
    eight_lane_build_status: { type: 'string', description: 'which preset/CI job builds with AVX512=OFF (8-lane); does the 8-lane build compile on main and on c73e7fb2f9 today? evidence (lcheck README, CI workflow files, compile logs)' },
    clang_vector_tbaa: { type: 'string', description: 'empirical result: with the local clang 19.1.7 at -O2 -S -emit-llvm, what TBAA metadata does a __m256i/__m512i load through a pointer cast from uint16_t* carry (omnipotent char, or a distinct type)? include the exact command and the relevant IR lines. Also whether a mismatched-type store then vector-load in one function is reordered or folded. Label anything you could not run.' },
    clang_aliasing_diagnostics: { type: 'string', description: 'does clang 19 warn for these casts with -Wall -Wextra -Wstrict-aliasing / -Wcast-align? empirical, with command' },
    sanitizer_coverage: { type: 'string', description: 'do the repo CI or 3bda test flows run UBSan/ASan on t_llama_unit? does UBSan have a check for strict aliasing or [expr.add] pointer arithmetic? evidence' },
    history: { type: 'string', description: 'how the declarations of kv_block::k and kv_block::v changed from origin/main 11b7763c87 through 633cb88896 (#4557) to c73e7fb2f9 (#4587): types per lane variant, with lines; which reads flipped direction' },
    pr4584_treatment: { type: 'string', description: 'what origin/jhan-kv-scalar-storage (closed PR #4584) did for scaled_v_expr, fill_storage_slot and the 8-lane V storage; lines' },
    other_non_iso_items_in_pr_body: { type: 'string', description: 'the PR #4587 body section "Still outside ISO C++ (unchanged here)" lists six items; list them verbatim and say which three the code comment names' },
    not_established: { type: 'array', items: { type: 'string' } },
  },
  required: ['compiler_and_standard', 'strict_aliasing_flags', 'eight_lane_build_status', 'clang_vector_tbaa', 'clang_aliasing_diagnostics', 'sanitizer_coverage', 'history', 'pr4584_treatment', 'other_non_iso_items_in_pr_body', 'not_established'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    claims: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'uncertain'] }, evidence: { type: 'string' }, correction: { type: 'string' } },
      required: ['claim', 'verdict', 'evidence', 'correction'] } },
    missing_facts: { type: 'array', items: { type: 'string' }, description: 'important facts about this site that the fact set left out, each with evidence' },
    overall: { type: 'string', enum: ['confirmed', 'partly_confirmed', 'refuted'] },
  },
  required: ['claims', 'missing_facts', 'overall'],
}

const SITES = [
  { key: 'scaled_v_expr', prompt: `Fact-find the read site "scaled_v_expr steps through V with vector pointers".
Read kv_cache.hpp around lines 2225-2440 and 2500-2540 at c73e7fb2f9 (namespace detail, struct scaled_v_expr, both the "#if TRON_CHUNK_SIZE == 16" constructor and the "#else" AVX2 constructor, and page::scaled_v which builds it). Establish: the declared type of the V storage it reads in each lane variant (16-lane: v_vnni_tensor::data_ in v_vnni.hpp; 8-lane: kv_block::v), the pointer type it steps with (const bf16s*, i.e. __m256i* or __m128i*), how the loads happen (tron_mm_load_bf16 = which intrinsic; any mm512 helper in simd/aligned.hpp), the pointer arithmetic (data + i * ... ) and which standard rules that arithmetic and those loads step outside. Compare with origin/main 11b7763c87 (there kv_block::v was a bf16s array, so check whether this read was inside the rules on main and became a mismatch only when #4557/#4587 changed the storage to bf16). Who calls scaled_v (production attention code? tests?) - grep h/, src/, t/. Look at what origin/jhan-kv-scalar-storage did to scaled_v_expr (git show origin/jhan-kv-scalar-storage:h/tron/models/kv_cache.hpp and grep scaled_v_expr) as a fix precedent. Also read the comment block above the 16-lane constructor ("The plane arrives as its typed view. This weighted sum is the one cache-side kernel that takes the plane address ...").` },
  { key: 'fill_storage_slot', prompt: `Fact-find the read site "fill_storage_slot walks one bf16 pointer across K and V".
Read kv_cache.hpp lines 1640-1660 (fill_storage_slot) and 1212-1232 (fill_random, its only caller) at c73e7fb2f9, and the kv_block definition around lines 2440-2500. Establish: it does "bf16* data = reinterpret_cast<bf16*>(&block); for i < sizeof(block)/sizeof(bf16): data[i] = ..." - so the pointer starts at the kv_block object, walks the k array (bf16[page_size*head_size] at head) and continues into v (16-lane: v_vnni_tensor with private bf16 data_[]; 8-lane: bf16s v[][]). Which standard rules does each part step outside ([expr.add] arithmetic beyond one array into another object, [basic.lval] access through a type that is not the object's type for the 8-lane bf16s case, writing a private member's storage through an outside pointer, etc.)? Is it test-only (fill_random callers: grep t/ and h/ src/; the comment says "For testing only")? Does the same code exist at origin/main 11b7763c87 (there k and v were both bf16s arrays; note what changed)? Which tests call fill_random (t/t_llama_unit.cpp lines ~1148, ~2376: what do they test)? Precedent: what origin/jhan-kv-scalar-storage did to fill_storage_slot / fill_random. Fix options: fill k through k_view()/k rows and v through the typed packed-V operations or a per-member loop; std::memcpy of a generated buffer per member; keep as is but document; etc. For each option say whether it preserves the test's intent (raw random bf16 bits into every element, bypassing the zero-init V slot invariant; see the fill_random comment).` },
  { key: 'eight_lane_v_accessors', prompt: `Fact-find the read site "the 8-lane V accessors read the bf16s (SIMD vector) array v as bf16 values".
The 8-lane build is TRON_CHUNK_SIZE == 8 (AVX2, AVX512=OFF). At c73e7fb2f9 kv_block declares, in the "#else" branch (kv_cache.hpp ~line 2462), "alignas(kv_block_alignment) bf16s v[page_size][head_size / chunk_size];" with bf16s = bf16x8 = __m128i. Find EVERY place in kv_cache.hpp (and v_vnni.hpp or elsewhere if any) that, under "#if TRON_CHUNK_SIZE == 16 ... #else" or "#if TRON_CHUNK_SIZE == 8", reads or writes kv_block::v as bf16 values: e.g. page::scaled_v's 8-lane branch "reinterpret_cast<const bf16*>(kv_block<geometry>(slot, kv_head).v)" (~line 2517), page::set_v / get_v / v_view / v_row / copy_v or similar 8-lane branches, the const_view<bf16,...> construction over v, any t/ code. For each: file, lines, snippet, what it reads/writes. Establish which standard rules the reads step outside: [basic.lval] (accessing an __m128i object's value through a bf16 glvalue), [expr.add] (bf16 pointer arithmetic over an array of __m128i). Compare with origin/main 11b7763c87: on main BOTH k and v were bf16s arrays in both lane variants and the accessors read them as bf16 - so was this read pattern pre-existing on main for k as well, and did the K1 commit c73e7fb2f9 ("Declare kv_block::k as a plain bf16 array") remove the same pattern for k? Read that commit's message and diff (git -C ${W} show c73e7fb2f9 --stat and the kv_cache.hpp hunks). Does the 8-lane build compile today (see /home/jhan/workspace/ai-runs/lcheck/README.md: it says the 8-lane tree fails on main in simd/fp32.hpp and kernels/wide.hpp) - cite that; do not claim more than the README and any logs you find show. Fix options: declare v in the 8-lane branch as bf16 v[page_size*head_size] like k (the K1 pattern) and build vector loads from bf16 addresses; or a v_vnni_tensor-like owner for 8-lane; or delete the 8-lane V code path if the build is dead (that is a maintainer decision, phrase it as an option). Precedent: what origin/jhan-kv-scalar-storage did for the 8-lane V storage.` },
]

phase('Facts')
log('Facts: 3 site readers + 1 build/compiler context reader')

const siteFacts = pipeline(
  SITES,
  s => agent(`${READONLY}\n\nTASK\n${s.prompt}\n\nReturn the structured fact set. Every location must be at commit c73e7fb2f9 unless you say otherwise. Do not write any file under /home/jhan/workspace.`,
    { label: `facts:${s.key}`, phase: 'Facts', schema: FACTS_SCHEMA }),
  (facts, s) => facts ? parallel([
    () => agent(`${READONLY}\n\nYou are a skeptical C++ language lawyer. Below is a fact set about one read site in the KV cache that a colleague claims "stays outside ISO C++ and relies on the compiler". Your job: try to REFUTE each claim about the C++ standard (which rule applies, whether the read is really undefined or merely unspecified/implementation-defined, whether a cited section says what the paraphrase claims, whether the "what would be inside ISO" statement is right). Check the code yourself in ${W} (do not trust the snippets). Where a claim is wrong, give the correction with the N4950 section that actually governs. Also list important facts the set left out. If you are uncertain, say uncertain, never confirmed.\n\nFACT SET (JSON):\n${JSON.stringify(facts, null, 1)}`,
      { label: `refute-law:${s.key}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'xhigh' }),
    () => agent(`${READONLY}\n\nYou are a skeptical code reviewer. Below is a fact set about one read site in the KV cache. Your job: try to REFUTE every CODE claim by reading the actual files in ${W} at c73e7fb2f9 and the other revisions named (origin/main 11b7763c87, origin/jhan-kv-typed-tensors 633cb88896, origin/jhan-kv-scalar-storage 9380012de5): are the file:line numbers exact, are the snippets verbatim, is the storage type and the access type right for each lane variant, is the caller list complete (grep again yourself), is the "on main" comparison right, is the production-vs-test claim right, is the fix-precedent description of PR #4584 accurate? Where a claim is wrong or a line number is off, give the correction. Also list important facts the set left out. If you are uncertain, say uncertain, never confirmed.\n\nFACT SET (JSON):\n${JSON.stringify(facts, null, 1)}`,
      { label: `refute-code:${s.key}`, phase: 'Verify', schema: VERDICT_SCHEMA }),
  ]).then(vs => ({ site: s.key, facts, verdicts: vs.filter(Boolean) })) : null,
)

const contextFacts = agent(`${READONLY}\n\nTASK\nEstablish the build and compiler context that decides how serious the three non-ISO reads are, and their history. Work through every field of the schema:\n- compiler_and_standard: read ${W}/CMakeLists.txt (CMAKE_CXX_STANDARD, flags), ${W}/CMakePresets.json, and /home/jhan/workspace/ai-runs/lcheck/flags.txt (real compile flags per tree captured from delphi-3bda compile_commands.json). Name the -std, -O level, -m flags for the 16-lane tree (gen) and the 8-lane tree (gen-avx2).\n- strict_aliasing_flags: grep CMakeLists.txt, cmake/, flake.nix, GNUmakefile, CMakePresets.json, lcheck/flags.txt for strict-aliasing. Report what you find, including "none found" with the grep command.\n- eight_lane_build_status: which preset has AVX512 OFF (CMakePresets.json ~line 64), which CI workflow or job (grep .github/workflows and ci/ and README.ci.md for AVX512, avx2, AVX512=OFF) builds it, and what lcheck/README.md says about the 8-lane tree failing on main. Do not claim the 8-lane build is dead or alive beyond that evidence.\n- clang_vector_tbaa: run an experiment with the local clang (read lcheck/README.md and lcheck.sh for the exact driver invocation and -isystem mirror paths; find immintrin.h under the mirror). Write a small C++ file under ${SCRATCH}/context/ that (a) has an aligned uint16_t array, stores some values through uint16_t*, then loads a __m256i through reinterpret_cast<const __m256i*> with _mm256_load_si256 and returns it; (b) the same with __m512i / _mm512_load_si512 under -mavx512f; compile with -O2 -S -emit-llvm -std=gnu++23 -mavx2 (and -mavx512f for b) and report the !tbaa metadata attached to the vector load (e.g. "omnipotent char" or a named type node) and whether the stores were kept before the load (not dead-store-eliminated or reordered). Include the exact commands and the relevant IR lines. If the compile fails, report the error verbatim and mark the field not established.\n- clang_aliasing_diagnostics: compile the same file with -fsyntax-only -Wall -Wextra -Wstrict-aliasing=2 -Wcast-align and report whether any diagnostic appears (clang accepts -Wstrict-aliasing but may not implement it; report what you observe).\n- sanitizer_coverage: does UBSan have any check that would fire on strict-aliasing violations or on pointer arithmetic that crosses an array boundary ([expr.add])? Answer from clang's UBSan documentation knowledge, marked as such, plus what the repo does: grep GNUmakefile, CMakeLists.txt, cmake/, .github/workflows, ci/, README.ci.md for sanitize/asan/ubsan and say which tests run under which sanitizer.\n- history: show the declarations of kv_block::k and kv_block::v at origin/main 11b7763c87, at 633cb88896 and at c73e7fb2f9 for both lane variants (git show <rev>:h/tron/models/kv_cache.hpp, grep "kv_block_alignment) "), with line numbers. Then state which reads flipped direction: on main the storage was vector (bf16s) and the bf16 accessors were the mismatch; at head in 16-lane the storage is bf16 and the vector-pointer read in scaled_v_expr is the mismatch; 8-lane v unchanged. Verify each part of that statement rather than copying it.\n- pr4584_treatment: git -C ${W} diff origin/jhan-kv-typed-tensors origin/jhan-kv-scalar-storage -- h/tron/models/kv_cache.hpp, then describe what it did to scaled_v_expr (both lane variants), fill_storage_slot/fill_random and the 8-lane V storage, with line refs into origin/jhan-kv-scalar-storage:h/tron/models/kv_cache.hpp. Also: gh pr view 4584 --json state,title,closedAt (it is CLOSED; give the date).\n- other_non_iso_items_in_pr_body: gh pr view 4587 --json body, quote the six bullets of "Still outside ISO C++ (unchanged here)" verbatim and mark which three the code comment names.\nReturn the structured result. Do not write any file under /home/jhan/workspace.`,
  { label: 'facts:context', phase: 'Facts', schema: CONTEXT_SCHEMA })
  .then(ctx => ctx ? agent(`${READONLY}\n\nYou are a skeptical reviewer. Below is a context fact set about the tron build, the compiler, and the history of kv_block declarations. Try to REFUTE each claim by re-running the greps and, for the clang experiment, re-running the compile yourself (read /home/jhan/workspace/ai-runs/lcheck/README.md; put your files under ${SCRATCH}/context-refute/). Check especially: the exact declaration lines per revision, the CI/preset claims about the 8-lane build, the PR #4584 description, the six verbatim bullets from the PR #4587 body, and whether the TBAA reading of the IR is right (a vector load through a cast pointer: which !tbaa node?). Where a claim is wrong, give the correction. List important facts left out. If uncertain, say uncertain.\n\nCONTEXT FACT SET (JSON):\n${JSON.stringify(ctx, null, 1)}`,
      { label: 'refute:context', phase: 'Verify', schema: VERDICT_SCHEMA }).then(v => ({ ctx, verdict: v })) : null)

const [sites, context] = await Promise.all([siteFacts, contextFacts])
const goodSites = sites.filter(Boolean)
log(`Verified fact sets: ${goodSites.length}/3 sites, context ${context ? 'ok' : 'missing'}`)

phase('Draft')

const DRAFT_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string', description: 'issue title, one line, no names, no @' },
    body_markdown: { type: 'string', description: 'the full GitHub issue body in Markdown' },
    labels_suggested: { type: 'array', items: { type: 'string' } },
    facts_dropped_as_unverified: { type: 'array', items: { type: 'string' } },
  },
  required: ['title', 'body_markdown', 'labels_suggested', 'facts_dropped_as_unverified'],
}

const draftInput = JSON.stringify({ sites: goodSites, context }, null, 1)

const draft = await agent(`${READONLY}

TASK: write a GitHub issue for positron-ai/tron that tracks the three reads named in the kv_cache.hpp comment quoted in CONTEXT (PR #4587, Note [KV block lifetime], lines 1459-1462 at c73e7fb2f9). The issue is a tracking / tech-debt issue: it records where each read is, which C++ rule it steps outside, why it works today, what would detect a break, and the fix options for the code owner to decide. It must NOT claim a bug exists today unless the verified facts say so.

Use ONLY facts marked confirmed by the refuters below, or facts you verify yourself in ${W}. Apply every correction the refuters gave. Anything a refuter marked refuted must be dropped or corrected; anything uncertain must either be verified by you now (read the code) or be labeled as a hypothesis with the measurement that would settle it. List what you dropped in facts_dropped_as_unverified.

FORMAT (follow the precedent of issue #4500 in this repo: run "gh issue view 4500" to see it):
1. "## Short version": at most three sentences a newcomer can follow.
2. "## Words used here": a two-column table defining every code name, acronym and standard term at first use (kv_block, book, page, K plane / V plane, packed V, bf16, bf16s, SIMD, 16-lane / 8-lane build, TRON_CHUNK_SIZE, ISO C++ / N4950, undefined behavior, strict aliasing / [basic.lval], [expr.add], TBAA if used, std::launder if used, scaled_v_expr, fill_storage_slot, v_vnni_tensor, PR numbers with one-line descriptions).
3. "## Where the note comes from": link the comment at https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1459-L1462 and the PR https://github.com/positron-ai/tron/pull/4587 ; quote the four comment lines verbatim in a code block; say that the PR body's "Still outside ISO C++ (unchanged here)" list names six items and that this issue tracks the three the code comment names, and list the other three as "not in this issue" with one line each.
4. "## The three reads": one subsection per read. For each: a table or short list with: code location (file:line at c73e7fb2f9, as a GitHub permalink https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/<path>#L<a>-L<b>), build variant, production or test-only (with callers), the declared storage type and the access type, the rule it steps outside (N4950 section + one plain sentence), whether it existed on main 11b7763c87 and how the direction changed (if it did), what a conforming version must do. Keep each subsection compact.
5. "## Why it works today, and what would show a break": the compiler/standard/flags facts (clang 19.1.7, -std, strict aliasing on/off, the TBAA experiment result if confirmed, no sanitizer check for aliasing, clang emits no diagnostic), and the test evidence (which tests exercise each read). One claim per sentence, each with its evidence.
6. "## Options (the code owner decides)": numbered options per read with cost/risk and precedent (PR #4584, closed draft, did X at lines Y; commit c73e7fb2f9 did the same for k). Do not pick one.
7. "## What is not affected": correctness of current builds as far as tested, the 16-lane K path after c73e7fb2f9, etc. - only what the facts support.
8. "## Related": #4525, #4557, #4587, #4584 with one line each.
9. End the body with the exact line: 🤖 Generated with [Claude Code](https://claude.com/claude-code)

WRITING RULES (mandatory):
- Plain English per the project rules: define every term at first use or in the Words table; one claim per sentence; no semicolons; no idioms or metaphors; short sentences; numbers carry units and a plain meaning; every citation follows a sentence that carries the claim.
- NEVER name or @-mention any person. Refer to people by role only ("the reviewing maintainer", "the PR author"). No first names, no GitHub handles. Do not put words in anyone's mouth.
- Never write "ctx N" for a prompt length (not relevant here, but keep to project naming).
- The title must be a plain sentence naming the component and the problem, e.g. "KV cache: three kv_block reads stay outside ISO C++ (scaled_v_expr, fill_storage_slot, 8-lane V accessors)". Improve it if you can, no names.
- Use only ASCII plus the one emoji in the footer.

VERIFIED INPUT (JSON: per-site fact sets with two refuter verdicts each, plus the context fact set with its refuter verdict):
${draftInput}`,
  { label: 'draft:issue', phase: 'Draft', schema: DRAFT_SCHEMA, effort: 'xhigh' })

if (!draft) return { error: 'draft agent returned null', sites: goodSites, context }
log(`Draft ready: ${draft.body_markdown.length} chars`)

phase('Check')

const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    violations: { type: 'array', items: { type: 'object', properties: {
      rule: { type: 'string' }, original: { type: 'string' }, fix: { type: 'string' } },
      required: ['rule', 'original', 'fix'] } },
    verdict: { type: 'string', enum: ['pass', 'fix_needed'] },
    notes: { type: 'string' },
  },
  required: ['violations', 'verdict', 'notes'],
}

const checks = await parallel([
  () => agent(`${READONLY}\n\nCheck mode of the plain-english skill. Check the GitHub issue TITLE and BODY below against these rules and list every violation with the exact phrase and a fix: (1) every code name, acronym, metric and standard term defined at first use or in the "Words used here" table; (2) one claim per sentence (split at "because", "since", "which means", "so that", semicolons); (3) every number has a unit and, where the reader cannot judge it, a plain-meaning clause, estimates labeled est.; (4) citations and links follow a sentence that carries the claim, never stand alone; (5) "Short version" at most three sentences a newcomer can follow; (6) no idioms, metaphors, wordplay, uncommon words; (7) bullets or blank lines separate distinct points; (8) short sentences, no semicolons. Also the banned words: convoy, refund, "in disguise", swept. Do not invent violations. Return the list; the verdict is "pass" only with zero violations.\n\nTITLE: ${draft.title}\n\nBODY:\n${draft.body_markdown}`,
    { label: 'check:english', phase: 'Check', schema: CHECK_SCHEMA }),
  () => agent(`${READONLY}\n\nFact-check the GitHub issue TITLE and BODY below against the code. For EVERY file:line, permalink line range, commit id, type name, function name, caller list, standard section, PR number/state and quoted text: open the file in ${W} (commit c73e7fb2f9; use git show for other revisions: origin/main 11b7763c87, origin/jhan-kv-typed-tensors 633cb88896, origin/jhan-kv-scalar-storage 9380012de5) or run the gh command, and confirm it. Permalinks of the form https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/<path>#L<a>-L<b> must point at the lines that hold the quoted construct: check with sed -n a,bp on the worktree file. Standard sections: check that the paraphrase matches N4950's rule (your knowledge of the standard, marked as such). Any claim you cannot confirm is a violation ("unverified: ..."). Report each wrong or unverified item with the exact phrase and the corrected text. The verdict is "pass" only with zero violations.\n\nTITLE: ${draft.title}\n\nBODY:\n${draft.body_markdown}`,
    { label: 'check:facts', phase: 'Check', schema: CHECK_SCHEMA, effort: 'xhigh' }),
  () => agent(`${READONLY}\n\nRules check of a GitHub issue TITLE and BODY. Check: (a) no person is named or @-mentioned anywhere (search for "@", and for first names or handles such as Ben, Wade, Bill, Rhys, Jeremy, Mitchell, Codex as an author, jhan, any GitHub login) - roles only; (b) the scope is exactly the three reads the code comment names, and the other three items of the PR body list appear only under "not in this issue"; (c) the issue does not assert a present-day bug without evidence, and every "rely on the compiler" claim is tied to a stated fact; (d) options are presented for the code owner to decide, none is picked; (e) the Words table covers every term used in the body (scan the body for code identifiers and acronyms and check each has a row or an inline definition); (f) the footer line is exactly: 🤖 Generated with [Claude Code](https://claude.com/claude-code) ; (g) the body is ASCII except that emoji; (h) the title names the component and the problem in plain words, with no names; (i) suggested labels are among the repo's labels (run gh label list -R positron-ai/tron --limit 100) and "Tech Debt" fits the repo definition. Report every violation with the exact phrase and a fix. Verdict "pass" only with zero violations.\n\nTITLE: ${draft.title}\n\nBODY:\n${draft.body_markdown}\n\nLABELS SUGGESTED: ${JSON.stringify(draft.labels_suggested)}`,
    { label: 'check:rules', phase: 'Check', schema: CHECK_SCHEMA }),
])

const okChecks = checks.filter(Boolean)
const total = okChecks.reduce((n, c) => n + c.violations.length, 0)
log(`Checks: ${okChecks.length}/3 returned, ${total} violations`)

let finalTitle = draft.title
let finalBody = draft.body_markdown
let revision = null
if (total > 0) {
  revision = await agent(`${READONLY}\n\nApply the checker findings below to the GitHub issue TITLE and BODY. Apply every fix that is correct; where a fact checker says a line number or claim is wrong, verify in ${W} yourself and correct it; where two checkers conflict, follow the fact checker for facts and the English checker for wording. Keep the structure and the footer line. Keep the writing rules: plain English, terms defined at first use, one claim per sentence, no semicolons, no names or @-mentions, ASCII only except the footer emoji. Return the full corrected title and body plus a list of the fixes you applied and any you rejected with the reason.\n\nTITLE: ${draft.title}\n\nBODY:\n${draft.body_markdown}\n\nCHECKER FINDINGS (JSON):\n${JSON.stringify(okChecks, null, 1)}`,
    { label: 'revise:issue', phase: 'Check', schema: {
      type: 'object',
      properties: {
        title: { type: 'string' }, body_markdown: { type: 'string' },
        applied: { type: 'array', items: { type: 'string' } },
        rejected: { type: 'array', items: { type: 'string' } },
      },
      required: ['title', 'body_markdown', 'applied', 'rejected'] }, effort: 'xhigh' })
  if (revision) { finalTitle = revision.title; finalBody = revision.body_markdown }
}

return {
  title: finalTitle,
  body: finalBody,
  labels_suggested: draft.labels_suggested,
  facts_dropped: draft.facts_dropped_as_unverified,
  checks: okChecks.map(c => ({ verdict: c.verdict, n: c.violations.length, notes: c.notes })),
  revision: revision ? { applied: revision.applied, rejected: revision.rejected } : null,
  site_overalls: goodSites.map(s => ({ site: s.site, verdicts: s.verdicts.map(v => v.overall) })),
  context_overall: context && context.verdict ? context.verdict.overall : null,
}