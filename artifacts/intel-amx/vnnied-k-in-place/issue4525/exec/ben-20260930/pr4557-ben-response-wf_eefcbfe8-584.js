export const meta = {
  name: 'pr4557-ben-response',
  description: 'Verify Ben\'s six PR 4557 threads against the code, refute, draft replies and patches, build-check',
  phases: [
    { title: 'Analyse', detail: 'one analyst per review thread' },
    { title: 'Refute', detail: 'three lenses per analyst report' },
    { title: 'Apply', detail: 'patch in a scratch worktree + syntax/build checks' },
    { title: 'Critic', detail: 'what is missing' },
  ],
}

const REPO = '/home/jhan/workspace/ai-runs/tron-issue4525'
const HEAD = 'c73e7fb2f9'
const SCR = '/tmp/claude-644434775/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/5bd3203f-0cd9-4559-8bc6-0e0d2549cc9a/scratchpad/ben'

const COMMON = `
CONTEXT (verified by the lead on 2026-09-30 19:20 UTC):
- Repo worktree: ${REPO} (branch jhan-kv-typed-tensors, HEAD ${HEAD} = PR #4557 head, base main 996f58ec82). PR https://github.com/positron-ai/tron/pull/4557, state OPEN, reviewDecision CHANGES_REQUESTED.
- The reviewer (Ben, GitHub bgamari-positron, a maintainer) submitted review 5352791816 (CHANGES_REQUESTED, body "Looks good. Just a few minor tweaks needed.") on 2026-09-29 14:56 UTC at ${HEAD}, plus review 5354385317 (COMMENTED). Raw JSON: ${SCR}/review-comments.json, ${SCR}/reviews.json. Ben's PR #4697 body/diff: ${SCR}/pr4697.json, ${SCR}/pr4697.diff (branch bgamari-kv-typed-tensors-dedup, head 8bbbb7c82d, base jhan-kv-typed-tensors; fetched in the repo as origin/bgamari-kv-typed-tensors-dedup). Ben's earlier PR 4424 texts: ${SCR}/ben-review-5270587330.md (decision "typed tensors": follow the tensor/dtensor expr precedent, vnni_tensor rank-2 with the usual tensor operations) and ${SCR}/ben-comment-5765866077.md (API sketch: no operator[], private ctor, at() only). PR 4557 body: ${SCR}/pr4557-body.md. Issue #4588 (OPEN, label Tech Debt, filed 2026-09-24 by jhan's session) tracks the three non-ISO reads named in the kv_cache.hpp comment at ${HEAD}:1459-1462.
- Design page (codex, reviewed 4 rounds): /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/status/design-new-tensor-type.html (its Q3 says operator[] logical rows are required by the expression interface; "Proposed; reviewer answer not recorded").
- Earlier Claude response pages jhan liked: /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/respond-Wade-comments.html (structure reference only).

THE SIX THREADS (verbatim):
B1 (comment 4133613638, h/tron/tensor/kv_cache_fwd.hpp line 25, on VIEW_ALIGNED_TRUE / VIEW_DMA_FALSE): "A better solution for naming these may just be to make the arguments proper \`enum\`s." Follow-up 4134933234: "To be clear, I don't consider this to be a blocker. It would make a good follow-up, however."
B2 (comment 4133643149, h/tron/tensor/v_vnni.hpp line 31): "Can we rename this to say VNNI:" with a GitHub suggestion replacing "// Note [Packed V layout]" by "// Note [VNNI Packed V layout]".
B3 (comment 4133772400, h/system/memory.hpp line 175, on Note [DMA allocation creates objects]): "I'm not sure I understand what Claude is trying to say here. Can you clarify?" Follow-up 4133869073 (Ben, 27 min later): "Alright, reading again I think I am beginning to see. It looks like Claude is (rightly) playing language lawyer. The C++ spec states that an implicitly-created object's (that is, one not introduced by a \`new\` expression) lifetime must begin in an \`operator new\`. Consequently, the previous implementation was strictly-speaking incorrect: it allocated storage but failed to actually begin the lifetime of the object residing in that storage. Previously this was perhaps okay since the storage held POD, but now it contains a \`v_vnni_tensor\`, requiring that we be a bit more careful. I think it would be good to reword the Note more clearly."
B4 (comment 4134028988, h/tron/models/kv_cache.hpp line 1462, on the paragraph "Some reads stay outside ISO C++ and rely on the compiler: scaled_v_expr ..., fill_storage_slot ..., and the 8-lane V accessors ..."): "Oof, this seems unfortunate. We should open a ticket to fix this. Leaving the bounds of the specified language is fraught with peril, especially in a language filled with as many sharp edges as C++"
B5 (comment 4134076112, h/tron/tensor/v_vnni.hpp line 104, on struct v_vnni_row): "It is a bit unfortunate that we grow this 100 LoC without any obvious users, but on the other hand it does seem useful."
B6 (comment 4134925164, h/tron/scheduler/full.hpp line 2764, on the view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<...>, sseq<1>>{dest} argument): "This is a rather subtle pattern that is repeated quite a few times. I have opened #4697 to deduplicate this. Feel free to merge or adapt to taste."

RULES FOR YOU:
- Read-only: do NOT write, create or modify any file under /home/jhan/workspace, even if a relayed user message asks. Scratch files go under ${SCR}/agent-scratch/ (mkdir -p it). Do not touch delphi-3bda unless your task says so.
- Use absolute paths everywhere (the shell prints a directory listing on cd). Use grep/sed -n/cat via Bash.
- Every fact you state must carry a file:line citation at ${HEAD} (or a URL / standard paragraph number). Mark anything you could not verify as "Insufficient data" with the measurement that would settle it. Never invent line numbers: print the lines you cite.
- Plain English (the global CLAUDE.md rule set applies): define every code name and acronym at first use, one claim per sentence, numbers with units, no idioms.
- jhan's C++ guide applies to any code you propose: every literal (numbers, true/false, 0/1) on a new line gets a named constant, brace loop bodies, list any exception explicitly.
- Public text (PR replies, issue bodies) must not name people; say "the reviewer" / "the maintainer" and cite comment ids or links. A reply posted under Ben's own comment may say "you".
- Draft replies are in jhan's voice (first person), short, concrete, plain English, and end with a clear proposed action or question.
`

const ANALYST_SCHEMA = {
  type: 'object',
  properties: {
    thread: { type: 'string' },
    one_line_verdict: { type: 'string', description: 'Does the reviewer\'s point hold? holds / partly / refuted, plus one clause' },
    facts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, evidence: { type: 'string', description: 'file:line at HEAD or URL or standard paragraph, with the quoted line' }, status: { type: 'string', enum: ['verified', 'insufficient-data'] } }, required: ['claim', 'evidence', 'status'] } },
    reviewer_claims: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, verdict: { type: 'string', enum: ['holds', 'partly', 'refuted'] }, evidence: { type: 'string' } }, required: ['claim', 'verdict', 'evidence'] } },
    options: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, what: { type: 'string' }, pros: { type: 'string' }, cons: { type: 'string' }, effort: { type: 'string' } }, required: ['name', 'what', 'pros', 'cons', 'effort'] } },
    recommendation: { type: 'string' },
    plain_words_table: { type: 'array', description: 'B3 only (else empty): rows of {says, plain}', items: { type: 'object', properties: { says: { type: 'string' }, plain: { type: 'string' } }, required: ['says', 'plain'] } },
    draft_reply_markdown: { type: 'string', description: 'the GitHub reply text in jhan\'s voice' },
    code_change: { type: 'string', description: 'unified diff against HEAD (git diff format, exact context lines), or "" if none' },
    follow_up_issue: { type: 'object', properties: { title: { type: 'string' }, body_markdown: { type: 'string' } }, required: ['title', 'body_markdown'] },
    open_for_jhan: { type: 'array', items: { type: 'string' } },
    notes_for_page: { type: 'string', description: 'anything else the response page should carry: counts, tables, figures worth drawing' },
  },
  required: ['thread', 'one_line_verdict', 'facts', 'reviewer_claims', 'options', 'recommendation', 'plain_words_table', 'draft_reply_markdown', 'code_change', 'follow_up_issue', 'open_for_jhan', 'notes_for_page'],
}

const TASKS = [
  { id: 'B1', prompt: `THREAD B1 (enums instead of VIEW_ALIGNED_TRUE / VIEW_DMA_FALSE).
Tasks:
1. Show the constants at h/tron/tensor/kv_cache_fwd.hpp (print lines 1-60) and every use site (grep VIEW_ALIGNED_TRUE|VIEW_DMA_FALSE over h src t; give counts per file; note which lines are PR-added vs main, using git blame or git diff origin/main...HEAD).
2. Measure the scope of the reviewer's proposal: the template parameters "bool aligned" / "bool dma" in h/tron/tensor/view.hpp, views.hpp, slice.hpp, tensor.hpp, dmatensor.hpp, itensor.hpp and everywhere else (grep -rn "bool aligned\\|bool dma" h src t): count declarations, count call sites that pass a bare true/false (grep "view<[^>]*\\(true\\|false\\)" and similar over h src t), count static constexpr bool dma members (tensor.hpp:35/254, itensor.hpp:26, dmatensor.hpp). Explain what an enum conversion would touch on main code vs PR code. Find repo precedents for enum class as template argument or flag (h/common/malloc_category.hpp alloc_cat; any others).
3. Sketch the enum design in 10-20 lines of C++ (e.g. enum class alignment : bool { unaligned, aligned }; enum class memory { host, dma }; or names you justify), and show how one PR line would read after it. State whether the change can be made in the PR without touching main's view.hpp (answer: probably not; prove it).
4. Options: (a) accept as a follow-up issue, keep the constants now (the reviewer said not a blocker); (b) do it in this PR; (c) do it in PR 4424 or another child. Recommend one with reasons. Draft the follow-up issue (title + body, no names, cite comment 4133613638 by URL https://github.com/positron-ai/tron/pull/4557#discussion_r4133613638) and the reply.` },
  { id: 'B2', prompt: `THREAD B2 (rename Note [Packed V layout] to Note [VNNI Packed V layout]).
Tasks:
1. List EVERY occurrence of the string "Packed V layout" in the repo (grep -rn over h src t doc README* and the PR body ${SCR}/pr4557-body.md), with file:line and the full line. Also check other Note names in the PR that mention packed V (grep -rn "Note \\[" over the PR-added lines: git diff origin/main...HEAD | grep "^+.*Note \\[") so the rename is consistent.
2. Verify that "VNNI" is the right word: what VNNI means (Vector Neural Network Instructions; the pair-interleaved B-operand layout consumed by vdpbf16ps / AMX tdpbf16ps), where the repo already uses "vnni" for this V layout (file name v_vnni.hpp, types v_vnni_*, any "VNNI" in comments: grep -rni vnni h/tron/tensor/v_vnni.hpp h/tron/models/kv_cache.hpp h/tron/kernels/amx_attn_iface.hpp | head -40). Check that the Note text itself explains the pair interleave; if the Note never says "VNNI", propose the one sentence that defines VNNI at first use inside the Note (plain English rule).
3. Produce the unified diff for the rename at all sites (exact context lines from the files; run \`git diff --no-index\`-style formatting by actually applying sed to a COPY of the files under ${SCR}/agent-scratch/b2/ and diffing the copy against the original with \`diff -u\`; never modify the repo). Include the PR-body line that must change (quote it).
4. Check the clang-format line-length consequence (100 columns? read .clang-format ColumnLimit) for each changed line: the rename adds 5 characters; list any line that would exceed the limit.
5. Draft the reply (accept; say the rename is applied at N sites in commit "<pending>") and list what jhan must do (commit + push + PR body edit).` },
  { id: 'B3', prompt: `THREAD B3 (reword Note [DMA allocation creates objects], h/system/memory.hpp:167-183 at HEAD).
Tasks:
1. Print h/system/memory.hpp lines 150-190 and 350-380, h/tron/models/kv_cache.hpp lines 1440-1465 and 2440-2470 (kv_block, the static_asserts at 2455-2458 and 1554-1556/1597-1599, the std::launder at 1565/1574/1614), h/tron/tensor/v_vnni.hpp lines 240-300 (v_vnni_tensor). Also show what main had (git show origin/main:h/tron/models/kv_cache.hpp | grep -n "reinterpret_cast\\|construct_kv_blocks\\|dma_allocate" | head) and what the first PR commit (b951ba9b4c) and the folded 4587 commits (39a6899446, c73e7fb2f9) changed there (git log --oneline origin/main..HEAD; git show 39a6899446 --stat).
2. Check the C++ standard facts precisely (cite N4950 paragraph numbers; you may know them, but state them as "N4950 [x.y]/n" and quote the operative words): implicit object creation [intro.object]/10-11 ("some operations are described as implicitly creating objects ... the object representation ... implicit-lifetime types"), /13 ("Any implicit or explicit invocation of a function named operator new or operator new[] implicitly creates objects in the returned region of storage and returns a pointer to a suitable created object"); implicit-lifetime types [basic.types.general]/9 (scalar, implicit-lifetime class, array, cv-qualified versions) and implicit-lifetime class [class.prop]/9 (aggregate with no user-provided destructor, or at least one trivial eligible constructor and a trivial non-deleted destructor); [basic.life]/1; std::launder [ptr.launder]; which OTHER operations implicitly create objects (std::malloc, std::memcpy/memmove, std::bit_cast, creation of a char/unsigned char/std::byte array [intro.object]/3, std::start_lifetime_as in C++23 - note libstdc++ 14.3 lacks it as verified on 2026-09-24).
3. Grade the reviewer's three claims against those facts: (i) "an implicitly-created object's lifetime must begin in an operator new" (partly: operator new is ONE of the operations that implicitly create objects; the Note's point is that dma_allocate_aligned is none of them); (ii) "the previous implementation was strictly-speaking incorrect: it allocated storage but failed to begin the lifetime" (holds; say what the old code did: dma_allocate_aligned + reinterpret_cast, no object); (iii) "previously perhaps okay since the storage held POD, but now it contains a v_vnni_tensor, requiring more care" (refuted or partly: kv_block was already a class with bf16s arrays = implicit-lifetime, and v_vnni_tensor is also implicit-lifetime, pinned by the static_asserts at kv_cache.hpp:2455-2458; so the rule is the same before and after; what changed is that the PR makes the allocation satisfy it). Be exact and fair; cite.
4. Produce the two-column plain-words table for the CURRENT Note (one row per sentence: "the comment says" | "in plain words"). Then write the REPLACEMENT Note in the plain-words register: name the mechanism, say concretely what goes wrong without it (a member access on an object whose lifetime never started is undefined behaviour; today's compilers do not diagnose it), gloss the standard terms once ("implicit-lifetime type: a type C++ lets an allocation create without a constructor call"), keep identifiers exact, keep the three existing paragraphs' facts (new-expression extra bytes; unit-test allocator aligned_alloc in src/pos/fake.cpp), keep lines <= 80 columns in the comment, keep the Note title. Also check that Note [KV block lifetime] (kv_cache.hpp:1440-1462) still reads consistently with the new wording and propose minimal edits there if a sentence conflicts.
5. Provide the unified diff (apply to a copy under ${SCR}/agent-scratch/b3/, diff -u against the original), the reply (thank, agree with (ii), gently correct (iii) with the static_assert citation, say the Note is reworded), and open questions for jhan.` },
  { id: 'B4', prompt: `THREAD B4 (the "Some reads stay outside ISO C++" paragraph, kv_cache.hpp:1459-1462 at HEAD; reviewer: open a ticket).
Tasks:
1. Print kv_cache.hpp lines 1440-1465. Confirm the three reads still exist at HEAD with file:line: scaled_v_expr vector-pointer stepping (grep -n "reinterpret_cast<const bf16s\\*>" and the scaled_v_expr struct), fill_storage_slot (grep -n fill_storage_slot), 8-lane V accessors under #else (grep -n "bf16s v\\[page_size\\]" and the page::v / v_ptr accessors). Quote the lines.
2. Fetch issue #4588 (gh issue view 4588 --json title,body,state,url,labels,createdAt,assignees) and check that it covers exactly those three reads and nothing else; quote its Short version. Note the memory fact: the four-line comment was meant to be removed from the code on 2026-09-24 but HEAD still carries it (git log -S"Some reads stay outside ISO" --oneline; git status). Determine: was a removal ever committed? (answer from git; print evidence).
3. Options: (a) keep the paragraph and append "(tracked in issue #4588)" to it; (b) remove the paragraph and let the issue be the record (the 2026-09-24 intent); (c) keep as is and only reply with the issue link. For each: what a future reader of the code sees. Recommend one. Provide the unified diff for the recommended one (copy files under ${SCR}/agent-scratch/b4/, diff -u).
4. Draft the reply: the ticket exists (#4588, filed 2026-09-24, label Tech Debt), what it covers, what the fix precedents are (closed draft #4584 had the const bf16* stepping form for scaled_v_expr; the K1 pattern in commit c73e7fb2f9 is the cast-free model), and ask whether the reviewer wants any of the three fixed inside this PR or in the follow-up. Also note the reviewer's implicit question "is this new in the PR?": answer per read (scaled_v_expr's cast direction flipped in b951ba9b4c; fill_storage_slot byte-identical to main; 8-lane accessors same as main) with citations (git show origin/main:h/tron/models/kv_cache.hpp | grep -n ...).` },
  { id: 'B5', prompt: `THREAD B5 (v_vnni_row: ~100 lines without obvious users).
Tasks:
1. Measure: print h/tron/tensor/v_vnni.hpp lines 90-175 and count the lines of v_vnni_row (struct start to closing brace) and of its comment. List every user of v_vnni_row and of v_vnni_view::operator[] in the repo (grep -rn "v_vnni_row\\|\\]\\[\\|operator\\[\\]" over h src t; for each hit decide whether it is production code or test code, with file:line). Show the expression-interface chain that consumes rows: h/tron/kernels/expr.hpp (expr<B, d0, d1> operator[] at lines ~58-80 and chunk() forwarding at ~101-125) and h/tron/tensor/tensor.hpp (tensor(expr<B,d0,d1,...> const&) at ~272-290): print those lines and explain in plain words what a rank-2 expression must provide (operator[] returning a rank-1 expression with chunk()). Verify with the test t/t_llama_unit.cpp around lines 3453-3466 ("a host tensor reads the packed plane as logical rows") that \`tensor<page_size, HEAD_SIZE_64> host(plane)\` is the only consumer of v_vnni_row::chunk(), and whether any production path builds a tensor/dtensor from page::v_packed (grep -rn "v_packed" h src).
2. History: the reviewer's own PR 4424 review (${SCR}/ben-review-5270587330.md) asked for "a vnni_tensor type ... rank-2 tensor ... the usual operations that we expect of tensor types"; his sketch (${SCR}/ben-comment-5765866077.md) then excluded operator[] ("no data(), pointer conversion, or operator[] that suggests a contiguous row"); the design's Q3 chose operator[] logical rows for the expression interface and recorded "reviewer answer not recorded". Quote all three. So the row type exists because of the expression-interface reading of his first request; his sketch would drop it. State this fairly.
3. Options: (a) keep v_vnni_row (justify: it is what makes v_vnni_view a real expr; the test proves the logical-row read; PR 4424 or later consumers - check the 4424 branch jhan-amx-vnniK for any use: git grep -n "v_vnni_row\\|\\[token\\]\\[" origin/jhan-amx-vnniK -- h src t | head, Insufficient data if the branch does not contain the type); (b) drop v_vnni_row AND the expr base of v_vnni_view, keep at(), so v_vnni_view is a plain typed handle as the sketch had (count the lines removed, list the tests that must change: t_llama_unit 407-440 STATIC_REQUIREs and the host-tensor SECTION); (c) keep the row but move it under a narrower interface. For each, effect on the design contract (design page section on expression reads), on the PR 4424 child, and on the reviewer's two statements. Recommend one; this is jhan's decision, say so.
4. Draft the reply: name the users (the expression contract + the host-tensor test), name the line count exactly, say what dropping it would remove, and ask which he prefers (keep, or drop the expr base and rows). Keep it short.` },
  { id: 'B6', prompt: `THREAD B6 (PR #4697 by the reviewer: v_source_row / v_destination_row helpers shared across callers).
Tasks:
1. Read ${SCR}/pr4697.diff and ${SCR}/pr4697.json in full. Confirm in the repo: git log --oneline -3 origin/bgamari-kv-typed-tensors-dedup; git merge-base origin/bgamari-kv-typed-tensors-dedup HEAD (must be ${HEAD}); git diff --stat HEAD origin/bgamari-kv-typed-tensors-dedup.
2. Review the change for correctness, line by line, against HEAD: (a) the helper templates in v_vnni.hpp (template <size_t Cols, bool Dma = VIEW_DMA_FALSE, typename T> with T deduced; check each call site passes Cols explicitly and T deduces to the right constness: model.hpp v_source_row<geometry.kv.head_size, v_buffer_t::dma>(&vs[ix][...]) where vs element type is what? print model.hpp 2815-2850 at HEAD and on the 4697 branch; full.hpp 2755-2770; t/ call sites); (b) the helpers sit OUTSIDE the #if TRON_CHUNK_SIZE == 16 block: are they visible in the 8-lane build and are the aliases const_v_row_view / v_row_view used in the 8-lane page::set_v declarations (print kv_cache.hpp 1900-1940 at both revisions and check which #if guards enclose them)? (c) the t_llama_unit helpers removed at lines 94-107 had a comment "Every buffer wrapped here is declared alignas(64); wrapping does not make a pointer aligned": does the new header comment keep that warning? (d) the remaining VIEW_ALIGNED_TRUE use at t/t_llama_unit.cpp:159 and the 12 in kv_cache.hpp: which of them could also use the new aliases, and does the reviewer's change leave the PR consistent (some sites via alias, some spelled out)? List them with file:line. (e) the description says "Preserve the executor buffer DMA flag": verify model.hpp passes v_buffer_t::dma; (f) jhan's C++ guide: any new literal on the added lines? any unbraced loop? (g) clang-format: the reviewer says formatting passes; check line lengths of the added lines vs .clang-format ColumnLimit. (h) the new comment "Contiguous, aligned transfer rows for set_v/get_v, not packed V storage." and "The caller must provide Cols elements aligned to chunk_alignment." - is chunk_alignment the right constant (page::set_v requires what alignment? print the set_v/get_v implementation lines ~2547-2610 and the append_v_row/load_row loads: _mm512_load_si512 needs 64 bytes; chunk_alignment is 64 at 16 lanes and 32 at 8 lanes - is the 8-lane value adequate for the 8-lane set_v path?).
3. Integration options: (a) \`gh pr merge 4697 --rebase\` or --merge into jhan-kv-typed-tensors (marks #4697 merged, keeps the reviewer's authorship); (b) git cherry-pick 8bbbb7c82d onto the branch (linear, authorship kept, #4697 then closes as unmerged unless the same commit id lands); (c) adapt: same helpers but also convert the remaining spelled-out sites. Check the repository's merge settings if visible (gh api repos/positron-ai/tron --jq '{allow_merge_commit,allow_rebase_merge,allow_squash_merge}'); and whether #4557 itself will be squash-merged via merge queue (memory: PR3879 went through the merge queue). Recommend one.
4. Verification status: the reviewer wrote "The focused build was interrupted before completion; no test results are claimed." State which builds/tests must run before merging (t_llama_unit, t_amx_numerics, t_amx_dispatch_dtype, t_heterogeneous_scheduler on the 16-lane AMX-on and AMX-off trees; the model plugins compile full.hpp only in CI's Build Tron job). Do NOT run anything on delphi-3bda yourself; the Apply stage does that.
5. Draft the reply (thanks; merged/cherry-picked as commit <pending> after the tests listed; or adapted with these extra sites) and the code diff for option (c) if you recommend it (copy files under ${SCR}/agent-scratch/b6/, diff -u).` },
]

const REFUTE_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    items: { type: 'array', items: { type: 'object', properties: {
      target: { type: 'string', description: 'which fact / claim grade / option / sentence of the draft' },
      verdict: { type: 'string', enum: ['holds', 'refuted', 'partly'] },
      why: { type: 'string' }, correction: { type: 'string' }, evidence: { type: 'string' } },
      required: ['target', 'verdict', 'why', 'correction', 'evidence'] } },
    missed: { type: 'array', items: { type: 'string' }, description: 'facts or options the analyst should have covered' },
    reply_rewrite: { type: 'string', description: 'the draft reply rewritten if you found any defect in it, else ""' },
    code_change_verdict: { type: 'string', description: 'for a proposed diff: applies cleanly? compiles by inspection? guide-compliant? or "no diff"' },
  },
  required: ['lens', 'items', 'missed', 'reply_rewrite', 'code_change_verdict'],
}

const LENSES = [
  { key: 'facts', text: 'LENS = facts and citations. Re-open every cited file:line at HEAD and every quoted standard paragraph or URL. Refute any citation that does not say what the analyst claims, any count that is wrong (recount yourself), any line number that is off. Default to refuted=... only with evidence; print the lines you checked.' },
  { key: 'engineering', text: 'LENS = engineering consequences. For each option and the recommendation: what breaks (builds: 16-lane AMX-on, AMX-off, 8-lane; tests; PR 4424 child; the design contract; the reviewer\'s stated preferences), what the reviewer would object to next, whether the proposed diff would compile (inspect the surrounding code), whether the C++ guide (named literals incl. true/false/0/1, braces) is met on every added line. Try to find a better option than the recommended one.' },
  { key: 'english', text: 'LENS = plain English and reviewer etiquette of the draft reply, the follow-up issue text and any rewritten comment. Apply the plain-english rules: define terms at first use, one claim per sentence, units, no idioms, no semicolons, short sentences, no names in issue bodies, "you" allowed in a direct reply. Check the tone: factual, not defensive, no over-claiming ("fixed" only when the diff exists), and that the reply ends with the concrete action or the question. Provide the rewritten text.' },
]

phase('Analyse')
const analysed = await pipeline(
  TASKS,
  t => agent(`${COMMON}\nYOUR THREAD: ${t.id}\n${t.prompt}\nReturn the structured object. Be exhaustive on facts, terse in prose.`,
    { label: `analyse:${t.id}`, phase: 'Analyse', schema: ANALYST_SCHEMA }),
  (report, t) => report == null ? null : parallel(LENSES.map(l => () =>
    agent(`${COMMON}\nYOU ARE A REFUTER for thread ${t.id}. ${l.text}\nThe analyst's task was:\n${t.prompt}\n\nTHE ANALYST'S REPORT (JSON):\n${JSON.stringify(report, null, 1)}\n\nCheck every item. Return the structured verdicts.`,
      { label: `refute:${t.id}:${l.key}`, phase: 'Refute', schema: REFUTE_SCHEMA })))
    .then(votes => ({ id: t.id, report, votes: votes.filter(Boolean) })),
)
const threads = analysed.filter(Boolean)
log(`analysed ${threads.length}/${TASKS.length} threads`)

phase('Apply')
const forApply = threads.filter(x => ['B2', 'B3', 'B4', 'B6'].includes(x.id))
const applyResult = await agent(`${COMMON}
YOU ARE THE APPLY AGENT. You MAY write files, but ONLY inside a NEW git worktree you create at /home/jhan/workspace/ai-runs/tron-issue4525-ben (branch jhan-kv-typed-tensors-ben-r1 from ${HEAD}: run \`git -C ${REPO} worktree add -b jhan-kv-typed-tensors-ben-r1 /home/jhan/workspace/ai-runs/tron-issue4525-ben ${HEAD}\`; if the path exists already, reuse it and reset it hard to ${HEAD}), and on delphi-3bda ONLY under /var/tmp/jhan/tron-issue4525-ben (a local worktree there). Never push. Never modify ${REPO} or any other worktree. Never modify the PR.

Steps:
1. In the new worktree, apply the code changes in this order, one commit each (git commit --no-verify; end each message with "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"):
   (i) B6: \`git cherry-pick 8bbbb7c82d\` (the reviewer's PR #4697 commit; keep his authorship). If it conflicts, stop and report.
   (ii) B2: rename "Note [Packed V layout]" to "Note [VNNI Packed V layout]" at every site in the repo (grep -rn "Packed V layout" h src t) and add the VNNI definition sentence proposed by the B2 analyst (use the refuters' corrections if they found defects). Do not edit the PR body.
   (iii) B3: replace Note [DMA allocation creates objects] in h/system/memory.hpp with the analyst's rewritten Note as corrected by the refuters (take the 'english' refuter's rewrite when it exists), and apply any minimal consistency edit it proposes to Note [KV block lifetime] in kv_cache.hpp.
   (iv) B4: apply the recommended option for the "Some reads stay outside ISO C++" paragraph (add the issue #4588 reference, or remove the paragraph, as the analyst + refuters concluded).
2. Run in the worktree: \`git diff --check ${HEAD}\`; clang-format 19 via \`uvx --from clang-format==19.1.7 clang-format --dry-run --Werror <changed files>\` (then -i and re-commit as a fixup if needed); \`bin/lint-notes\` if it exists (ls bin | grep -i note); confirm no line over the .clang-format ColumnLimit in the changed comment blocks.
3. Local syntax check on claude-box: /home/jhan/workspace/ai-runs/lcheck/lcheck.sh <gen|gen-amxoff> <file> /home/jhan/workspace/ai-runs/tron-issue4525-ben for t/t_llama_unit.cpp, t/t_amx_numerics.cpp, t/t_amx_dispatch_dtype.cpp, t/heterogeneous_scheduler_compile.cpp, src/tron/kernels/amx_attn.cpp (read /home/jhan/workspace/ai-runs/lcheck/README.md first). Report rc and error counts before/after (run the same check on ${REPO} at HEAD for the baseline).
4. delphi-3bda build + tests (the real check; the lead confirmed at 19:19 UTC: people-check FREE, no CI lease, load average 130 from the serving engines). Procedure: ssh delphi-3bda '~/workspace/intel-AMX/exec/people-check.sh --claim "PR4557 Ben-round build+unit tests (claude)"'; if not FREE, skip and report. Then on 3bda: \`git -C /var/tmp/jhan/tron-issue4525 worktree add --detach /var/tmp/jhan/tron-issue4525-ben ${HEAD}\` is NOT possible for unpushed commits, so instead rsync the claude-box worktree: \`rsync -rlc --exclude=/.git --exclude=/gen --exclude=/gen-* --exclude=/ingest/traces --exclude=/ingest/dist-newstyle --exclude=/compile_commands.json /home/jhan/workspace/ai-runs/tron-issue4525-ben/ delphi-3bda:/var/tmp/jhan/tron-issue4525-ben/\` after first seeding /var/tmp/jhan/tron-issue4525-ben on 3bda as a copy of /var/tmp/jhan/tron-i4525rt2 (which is at ${HEAD} with built gen/ trees: check with \`ssh delphi-3bda 'ls /var/tmp/jhan/tron-i4525rt2; ls /var/tmp/jhan/tron-i4525rt2/gen | head'\`; use \`cp -a\` or \`rsync -a\` of that directory including gen/ so ninja rebuilds only the changed TUs; NEVER use --delete). Build inside nix on our half: \`ssh delphi-3bda 'cd /var/tmp/jhan/tron-issue4525-ben && taskset -c 72-143,216-287 nix develop --accept-flake-config --command cmake --build gen -j 48 --target t_llama_unit t_amx_numerics t_amx_dispatch_dtype t_heterogeneous_scheduler -- -k 0'\` (if gen/ was configured for a different source dir, re-run the cmake configure line from the memory: cmake --preset native -DAVX512=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_INGEST_MODELS=OFF -DBUILD_TEST_MODELS=OFF -DBUILD_PRODUCTION_MODELS=OFF inside nix develop; and gen-amxoff the same without -DTRON_AMX_DISPATCH=ON). Then run the four test binaries from the repo root on 3bda pinned to our half (env -u SYSTEM_CONFIG; run t_llama_unit fully and also the single cases "packed V rows keep their bits through set_v\\, get_v and expression reads" (escape the comma) and "Sliding KV chunks reserve and restore transactionally"), and the same four in gen-amxoff if that tree exists in the copy. Record assertion/case counts and compare with the known counts at ${HEAD}: t_llama_unit 44 cases / 252720 assertions, t_amx_numerics 12301 (real AMX), t_amx_dispatch_dtype 1559, t_heterogeneous_scheduler 1900. Release the claim at the end (people-check.sh --release if that flag exists; read the script's usage first). Log everything to /var/tmp/jhan/tron-issue4525-ben.log on 3bda and copy the log to ${SCR}/agent-scratch/apply/.
5. Report: commit ids in the scratch worktree with subjects, the full \`git diff ${HEAD}..HEAD --stat\`, the complete unified diff of the comment changes (B2/B3/B4) as text, every check's rc, the 3bda counts, and anything skipped with the reason.

THREAD REPORTS AND REFUTER VOTES:
${JSON.stringify(forApply, null, 1)}
`, { label: 'apply+build', phase: 'Apply', effort: 'high', schema: {
  type: 'object', properties: {
    worktree: { type: 'string' }, branch: { type: 'string' },
    commits: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, subject: { type: 'string' }, thread: { type: 'string' } }, required: ['id', 'subject', 'thread'] } },
    diffstat: { type: 'string' },
    comment_diffs: { type: 'string', description: 'unified diff text of B2/B3/B4 changes' },
    checks: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, rc: { type: 'string' }, detail: { type: 'string' } }, required: ['name', 'rc', 'detail'] } },
    bda_results: { type: 'array', items: { type: 'object', properties: { tree: { type: 'string' }, test: { type: 'string' }, result: { type: 'string' }, counts: { type: 'string' } }, required: ['tree', 'test', 'result', 'counts'] } },
    skipped: { type: 'array', items: { type: 'string' } },
    traps: { type: 'array', items: { type: 'string' } },
  }, required: ['worktree', 'branch', 'commits', 'diffstat', 'comment_diffs', 'checks', 'bda_results', 'skipped', 'traps'] } })

phase('Critic')
const critic = await agent(`${COMMON}
YOU ARE THE COMPLETENESS CRITIC. Read-only. Given the six thread reports, the refuter votes and the apply/build result below, answer: what is missing before jhan can respond to the review? Consider at least: (1) the review is CHANGES_REQUESTED: which threads block re-review and what re-requests review; (2) the PR body (${SCR}/pr4557-body.md): which sentences go stale after the changes (Note name, "Some reads" paragraph, commit count, the "Still outside ISO C++" list, the response-to-reviewer section) - quote each with its line; (3) PR #4697: what happens to it under each integration option; (4) the follow-up issue for enums: duplicates? (gh issue list --search "enum view aligned dma" --state all); (5) any reviewer claim graded by the analysts that the refuters disagreed on (list the disagreements verbatim); (6) tests: does any change need a new or changed unit test (Note-only changes do not; the 4697 helper does not; say so explicitly); (7) anything the analysts marked Insufficient data that a command could settle now (run it). Return findings as a list with severity (must / should / note) and the command or edit that closes each.

THREADS + VOTES: ${JSON.stringify(threads, null, 1)}
APPLY RESULT: ${JSON.stringify(applyResult, null, 1)}
`, { label: 'critic', phase: 'Critic', schema: { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['must', 'should', 'note'] }, what: { type: 'string' }, closes_with: { type: 'string' }, evidence: { type: 'string' } }, required: ['severity', 'what', 'closes_with', 'evidence'] } },
  disagreements: { type: 'array', items: { type: 'string' } },
  stale_pr_body_lines: { type: 'array', items: { type: 'string' } },
}, required: ['findings', 'disagreements', 'stale_pr_body_lines'] } })

return { threads, applyResult, critic }
