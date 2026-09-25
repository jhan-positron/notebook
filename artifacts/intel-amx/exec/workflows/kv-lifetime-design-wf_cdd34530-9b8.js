export const meta = {
  name: 'kv-lifetime-design',
  description: 'Verify the facts behind construct_kv_blocks (PR 4557) and draft designs that need no placement new',
  phases: [
    { title: 'Verify', detail: '5 fact checkers: C++ rules, toolchain, storage map, reviewer constraints, prior pages' },
    { title: 'Design', detail: '3 independent designers with different priorities' },
  ],
}

const CTX = `
Context (read-only investigation; do NOT edit, commit, push, or build anything):
- Repository: tron (C++ inference program), worktree ~/workspace/ai-runs/tron-issue4525, branch jhan-kv-typed-tensors,
  head 633cb88896 = PR #4557 "Typed KV-cache tensors for packed V and native K" (base main 996f58ec82).
  Use git -C ~/workspace/ai-runs/tron-issue4525 show/diff/grep. main version: git show 996f58ec82:<path>.
- The function under discussion: book::construct_kv_blocks in h/tron/models/kv_cache.hpp (around lines 1421-1492), with
  Note [KV block lifetime]. It runs '::new (static_cast<void*>(base)) kv_block_t[n]' over raw DMA arena bytes right after
  allocation (allocate_retained_storage / allocate_reclaimable_chunk), because PR 4557 made kv_block::v a class type
  (v_vnni_tensor, h/tron/tensor/v_vnni.hpp) whose member function as_view() the cache calls. The returned pointer of ::new is
  discarded; accessors later use reinterpret_cast<kv_block_t*>(uint8_t*) (kv_cache.hpp ~1593, ~1602, ~1642).
- DMA allocation: h/system/memory.hpp try_make_unique_dma_for_overwrite<uint8_t[]> -> dma_allocate_aligned (custom pool,
  src/system/memory.cpp; fake backend src/pos/fake.cpp uses aligned_alloc). For trivially constructible U it only casts.
- Prior design notes (written earlier today by another Claude session and by Codex; treat as UNVERIFIED input):
  ~/workspace/intel-AMX/VNNIed-K-in-place/issue4525/status/remove-dummy-new-claude.html and remove-dummy-new-codex.html.
  (Extract text with python re/html.unescape; they are HTML.)
- Reviewer texts on the parent PR #4424 (the reviewing maintainer's review and API sketch):
  /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a726337-9373-4eb4-935f-269e8630de97/scratchpad/ben-comment-5765866077.md
  and .../ben-review-5270587330.md. Never name the reviewer in outputs; say "the reviewing maintainer".
- Agreed design page for PR 4557: ~/workspace/intel-AMX/VNNIed-K-in-place/issue4525/status/design-new-tensor-type.html.
- PR body: gh pr view 4557 --repo positron-ai/tron --json body.
- Build facts: the product builds with clang 19 inside nix on delphi-3bda, -std=c++23 (check CMake), libstdc++ 14.x.
Every claim you return must carry evidence: a file:line at 633cb88896 (or main 996f58ec82), a C++ draft section
(eel.is/c++draft or N4950 section id + paragraph, quote the key sentence), or a command + its output. If you cannot
verify something, return verdict "insufficient" and name the measurement or source that would settle it.`

const CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          claim: { type: 'string' },
          verdict: { type: 'string', enum: ['true', 'false', 'partly', 'insufficient'] },
          evidence: { type: 'array', items: { type: 'string' } },
          notes: { type: 'string' },
        },
        required: ['id', 'claim', 'verdict', 'evidence'],
      },
    },
    extra_findings: { type: 'array', items: { type: 'string' } },
  },
  required: ['claims'],
}

const VERIFIERS = [
  {
    key: 'cxx-rules',
    prompt: `${CTX}
Task: settle the C++ object-model questions with the C++ draft text (fetch eel.is/c++draft pages with WebFetch; quote the
sentences). Claims to check (add ids L1..):
L1. [intro.object] (C++20/23): which operations implicitly create objects. In particular: does ANY explicit invocation of a
    function named operator new / operator new[] (including a user-declared placement-form allocation function at global
    scope, e.g. void* operator new[](std::size_t, std::align_val_t, tron_dma_tag) ) implicitly create objects and return a
    pointer to a suitable created object? Quote the exact paragraph.
L2. Is a custom pool function returning void* (not malloc/operator new/etc.) an implicit-object-creating operation? (Expected: no.)
L3. Implicit-lifetime class definition ([class.prop]/[basic.types]); does detail::kv_block<64,128> at PR head qualify
    (read its definition, kv_cache.hpp ~2465-2525) and does v_vnni_tensor qualify (v_vnni.hpp ~245-270, private member)?
L4. [basic.life]: using a pointer to storage to access a non-static data member or call a member function of an object whose
    lifetime has not begun is UB, regardless of whether the member has class type. So main's kv_block member access through
    reinterpret_cast is in the same situation as the PR's v.as_view() call.
L5. After '::new (p) T[n]' with the result discarded, does reinterpret_cast<T*>(p) (p a uint8_t* into the arena) point to the
    new T objects, or is std::launder needed? Cite [basic.life] transparent replacement, [expr.static.cast] pointer-
    interconvertibility, [ptr.launder] example.
L6. Pointer arithmetic: walking an entire kv_block (k array followed by v member) through one bf16* (as fill_random /
    fill_storage_slot may do at PR head; find them) exceeds the array object bounds ([expr.add]). Check the actual code.
L7. If the arena is ONE bf16 array whose lifetime began (e.g. via a function named operator new[] or implicit creation), and
    every K/V plane address is bf16* arithmetic inside that array, then views built from those pointers are fully defined.
L8. std::start_lifetime_as_array (P2590R2, C++23) - what it does; and whether std::construct_at / placement new of a
    trivially-default-constructible type without () writes any bytes (default-initialization, [dcl.init]).
L9. Does placement new of an array need extra "array cookie" space for non-placement? Specifically is
    '::new (void*) T[n]' allowed to use more than n*sizeof(T) bytes (the array allocation overhead, [expr.new]) - for the
    standard non-allocating placement form, is the overhead required to be zero (CWG 2382 / P1971?). Cite.
Return claims with verdicts. Add extra_findings for anything else relevant to "which design needs no placement new and is
strictly defined".`,
  },
  {
    key: 'toolchain',
    prompt: `${CTX}
Task: toolchain facts. delphi-3bda is a shared CI machine: you may ONLY run read-only commands there (ssh delphi-3bda
'<grep/ls/cat>'), no builds, no nix develop, no process launches that load CPU, and nothing in /dev/hugepages.
T1. Which C++ standard does tron compile with (CMake: grep CMAKE_CXX_STANDARD / -std= in the worktree)?
T2. Which libstdc++ (or libc++) the nix clang 19 uses on delphi-3bda: find the include tree under /nix/store
    (e.g. ls -d /nix/store/*gcc*14*/include/c++/* or find the path from /var/tmp/jhan/tron-issue4525/gen/compile_commands.json
    -isystem flags, read-only). Does it declare start_lifetime_as / start_lifetime_as_array (grep -rl in that tree)?
T3. Does the same tree provide std::launder (it should, C++17) and does clang 19 support __builtin_launder?
T4. Is there any existing use in tron of std::launder, start_lifetime_as, placement new (::new / new (ptr)), std::construct_at,
    memmove-to-self idioms? grep h/ src/ t/ at PR head; list file:line and what each one does.
T5. Does any tron code define a custom global or class-specific operator new / operator new[] (grep "operator new")?
    List them: this tells whether a DMA-routed allocation function would be a new idiom.
T6. What does the PR's Step F evidence say about construct_kv_blocks codegen (instructions emitted)? Look in
    ~/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/3bda-first-test/ (grep -ri "rep stos\\|memset\\|placement")
    and the memory file ~/.claude/projects/-home-jhan-workspace-intel-AMX/memory/issue4525-implementation.md.
Return claims T1..T6 with evidence (commands + outputs).`,
  },
  {
    key: 'storage-map',
    prompt: `${CTX}
Task: complete map of the KV storage object model at PR head 633cb88896, so a designer can size a change.
List every site (file:line, 1-line description, category) in these categories:
 S-alloc: allocation of KV arenas/chunks and their owner types (retained_data, reclaimable_chunks_, chunk.data, x_data),
          and release/reclaim/restore paths (clear_kv_storage, restore, reserve, publish).
 S-cast: every reinterpret_cast/static_cast that turns arena bytes into kv_block*, bf16*, bf16s*, or other typed pointers
         (kv_block(), kv_block_at_storage(), slot_base, slot_page, kv_blocks_alias, fill_random, fill_storage_slot, etc.).
 S-member: every use of kv_block members: .k, .v, k_view(), k_at(), .v.as_view(), v_base, sizeof/alignof asserts.
 S-copy: every whole-block or byte copy of KV storage (memcpy, std::copy, copy_from, append, EAGLE copies).
 S-external: any code outside kv_cache.hpp that reads KV storage by address: model.hpp, self_attention.hpp, full.hpp,
            hardware staging / FPGA (gof::populate, hwattention, dmatensor), amx_attn_iface.hpp / amx_attn.cpp, tests.
 S-8lane: code paths for TRON_CHUNK_SIZE != 16 (8-lane build) that touch kv_block storage.
 S-layout: layout_t::storage_location / byte offsets / arena_sizes: are all slot offsets multiples of sizeof(bf16) and of
           64 bytes (so an element-offset (bf16) arena would work)? Cite the arena size computation.
Also answer: (a) does the EAGLE storage slot exist in heterogeneous layouts (eagle_compatible)? (b) does construct_kv_blocks
cover every block any accessor can reach (uniform vs heterogeneous, retained vs reclaimable, EAGLE slot)? (c) the list of
files a design "C" (each arena = one bf16 array, kv_block replaced by geometry constants + views built by the book) would
have to touch, with an est. changed-line count per file (label est.).
Return claims (ids M1..) for (a), (b), and one claim per category summarizing the count, with the full site list in
extra_findings (one string per site: "category | file:line | description").`,
  },
  {
    key: 'reviewer-constraints',
    prompt: `${CTX}
Task: what did the reviewing maintainer and the agreed design ask for, that constrains a redesign of KV storage?
Read the reviewer's sketch and review (paths above), the agreed design page (status/design-new-tensor-type.html; extract
text), and the PR body section "Response to the reviewer's comments on #4424" (gh pr view 4557 --repo positron-ai/tron
--json body -q .body). Return claims R1.. for each explicit constraint, quoted verbatim with its source, e.g.:
 - "Storage is an aligned array, not another allocation" (vnni_tensor holding std::array inside kv_block)
 - "The page arena must construct the actual storage type. We should not obtain typed storage by casting..."
 - "Views normally come from typed storage" / private pointer constructor / detail::vnni_access escape hatch
 - "we really don't want bf16_t* values floating around without any indication of how they are laid out"
 - initialization policy: no implicit clearing on hot allocation paths; keep V zero-init invariant
 - anything in the design page that chose v_vnni_tensor as the owner inside kv_block, and any recorded alternatives.
Then for each of these candidate designs, say whether it satisfies, partly satisfies, or contradicts each constraint
(put this matrix in extra_findings as lines "design | constraint id | satisfies/partly/contradicts | why"):
 P  = PR as is (owner v_vnni_tensor inside kv_block + construct_kv_blocks placement new)
 D1 = kv_block keeps plain bf16 arrays for V (like main) + kv_block::v_view() builds the packed view (like k_view()); no owner in storage
 A2 = PR's kv_block owner kept; arenas allocated through a DMA function named operator new[] (implicit object creation), std::launder at the 3 cast sites, no construct_kv_blocks
 C  = each arena is one bf16 array; kv_block replaced by geometry constants; book builds K/V views from bf16* (book-only factory)
 B  = one typed kv_block_t[] arena per block type`,
  },
  {
    key: 'prior-pages',
    prompt: `${CTX}
Task: adversarially verify the claims of the two prior design notes (remove-dummy-new-claude.html F1-F5, its designs A/B/C
and comparison table, and remove-dummy-new-codex.html's findings incl. its "Block -> scalar access: fill_storage_slot casts
an entire block to bf16*" row and its DMA-boundary section). For each claim, try to REFUTE it against the code at
633cb88896 / main 996f58ec82 and the C++ draft. Return one claim per checked statement (ids P1..; prefix C- for the Claude
page, X- for the Codex page) with verdict and evidence. Also list, in extra_findings, any design option neither page
considered (for example: an allocation function named operator new[] that routes to the DMA pool, which by [intro.object]
implicitly creates objects without any placement new; or reverting V storage to plain arrays with a view factory on kv_block
like k_view()), with a short assessment.`,
  },
]

phase('Verify')
const verified = await parallel(VERIFIERS.map(v => () =>
  agent(v.prompt, { label: `verify:${v.key}`, phase: 'Verify', schema: CLAIMS_SCHEMA })
    .then(r => ({ key: v.key, ...r }))))
const facts = verified.filter(Boolean)
log(`verifiers returned: ${facts.map(f => f.key + '=' + (f.claims || []).length).join(', ')}`)

const factsText = JSON.stringify(facts, null, 1)

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    one_line: { type: 'string' },
    storage_model: { type: 'string', description: 'what objects live in DMA pool memory, who owns the bytes' },
    lifetime_mechanism: { type: 'string', description: 'which operation starts each object lifetime, with C++ citation' },
    uses_placement_new: { type: 'boolean' },
    uses_launder: { type: 'boolean' },
    strictly_defined: { type: 'string', description: 'yes/no/partly + why, citing the verified facts' },
    files: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          change: { type: 'string' },
          est_lines: { type: 'number' },
        },
        required: ['file', 'change'],
      },
    },
    code_sketch: { type: 'string', description: 'C++ sketch of the key types and the accessor, compile-plausible' },
    reviewer_alignment: { type: 'string' },
    codegen_expectation: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
    test_plan: { type: 'array', items: { type: 'string' } },
    comparison_vs_pr: { type: 'string' },
    recommend_over_pr: { type: 'boolean' },
    recommend_reason: { type: 'string' },
  },
  required: ['name', 'one_line', 'storage_model', 'lifetime_mechanism', 'uses_placement_new', 'uses_launder',
    'strictly_defined', 'files', 'code_sketch', 'reviewer_alignment', 'risks', 'test_plan', 'comparison_vs_pr',
    'recommend_over_pr', 'recommend_reason'],
}

const ANGLES = [
  { key: 'minimal-strict', text: 'Priority: the SMALLEST change to PR 4557 that removes construct_kv_blocks and every placement new while leaving the program strictly defined under the C++ draft (not just "compiles to the same code"). Prefer keeping files outside the PR untouched unless strictly needed; if a change outside the PR is needed, keep it to one small function and say so.' },
  { key: 'ownership-first', text: 'Priority: the cleanest ownership model: exactly one owner of the arena bytes, typed from allocation, no overlaid objects, no second walk of the layout that must match the accessors. Type safety of K/V views at kernel boundaries must stay at least as strong as the PR. Size of change is secondary but must be stated honestly.' },
  { key: 'consistency-delivery', text: 'Priority: consistency with the existing codebase (native K path via kv_block::k_view on a plain array, dmatensor<bf16> buffers, the reviewing maintainer\'s requests) and delivery risk: PR 4557 is ready for review with green CI; weigh re-review cost, test churn, and the risk of changing arena addressing used by the sliding/reclaimable chunks and EAGLE. It is acceptable to conclude that the PR should proceed unchanged or with a small edit, if the facts support that.' },
]

phase('Design')
const designs = await parallel(ANGLES.map(a => () =>
  agent(`${CTX}

You are one of three independent designers. Verified facts from five checkers (JSON; trust verdict "true" items, treat
"partly"/"insufficient" with care, and re-check anything your design depends on):
${factsText}

Candidate designs already named (you may pick one, combine, or propose a new one):
 P  = PR as is (owner v_vnni_tensor inside kv_block + construct_kv_blocks placement new, pointer discarded)
 P' = PR + std::launder at the 3 cast sites
 D1 = kv_block keeps plain bf16 arrays for V (like main) + kv_block::v_view() builds the packed v_vnni_view (like k_view()); owner not in storage
 A  = the typed DMA factory starts lifetimes with ::new (raw) U[n] (placement new moved into memory.hpp) + typed arenas / launder
 A2 = arenas allocated through a DMA-routed function named operator new[] (implicit object creation per [intro.object]), std::launder at the cast sites, PR's kv_block owner kept
 B  = one typed kv_block_t[] arena per block type
 C  = each arena is one bf16 array; kv_block replaced by geometry constants; book builds K/V views from bf16* through a book-only factory; optionally with A or A2 at the allocator
${a.text}

Produce ONE fully specified design. The user's request: "construct_kv_blocks() spells some design level defect; scope the
software design and classes related to this PR; identify designs which do not need the ::new call; pick the best; compare
with the PR version; recommend proceeding with the PR or the new design." Be concrete: per-file change list with est.
changed lines (label est.), a compile-plausible C++ sketch of the storage types, the accessor, and the view factory, the
lifetime mechanism with a C++ citation, 16-lane and 8-lane builds, uniform and heterogeneous layouts, retained and
reclaimable chunks, EAGLE, fill_random/fill_storage_slot, scaled_v_expr, tests (t_llama_unit, t_amx_numerics,
t_amx_dispatch_dtype, heterogeneous_scheduler_compile). State honestly whether you recommend it over the PR.`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA })
    .then(d => d && ({ angle: a.key, ...d }))))

return { facts, designs: designs.filter(Boolean) }
