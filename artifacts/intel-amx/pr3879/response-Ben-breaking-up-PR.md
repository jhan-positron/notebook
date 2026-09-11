# Response to Ben's request to break up PR 3879

## Context for a reviewer of this document

- **What this is.** An internal analysis note for jhan (Jibin Han, author of PR 3879), written by Claude on 2026-09-04 and revised the same day after Ben's direct message (section 1, Ask D). Nothing in it has been posted to Slack or GitHub, and no split has been performed. The document's job is to answer: is Ben's request to split the PR justified, what would the split contain, what does it cost, and what should jhan decide.
- **Who is who.** Ben Gamari (GitHub bgamari-positron) is one of five requested reviewers of the PR and the only one who has reviewed it; he has 357 commits on tron's main, mostly in the ingestion code. Alexey (axch) is the top author of the two headers the PR changes most. Wade posted an agent-generated review. Jeremy is the manager asking for the PR to land. Bill Baumann wrote the earlier AMX PR #2934 from which the mirror formulation originates.
- **What Ben asked, in order.** Slack #intel-amx 11:04 to 11:23 PDT: the PR is a "2.5kLoC monolith"; split at the kernel / K-mirror seam and at the page-sharing instrumentation. GitHub 11:56: CHANGES_REQUESTED with ten inline comments. Slack 11:58: also squash and rebuild the commit history topically. Direct message 13:28, after jhan asked him to write down what he had proposed in the gpt-oss meeting: "First introduce the page sharing counters. Then introduce the AMX kernel without the K mirror. Then introduce the K mirror." The direct message is the operative request and this document follows its order.
- **How the numbers were produced.** The per-concern line counts in section 4 come from an 18-file, hunk-by-hunk classification of the PR diff against its base (main at 1407f48ddb), each file re-checked by an independent second pass; counts are non-blank added lines (git's +2,538 includes about 144 blank lines). Dependency claims in section 5 were checked against the diff and the worktree ~/workspace/tron-amx at head 60d66d9c04. Repository statistics in section 3 come from the GitHub API on 2026-09-04. Effort figures are estimates and are marked est.
- **What a reviewer of this note should check.** (1) That the three-PR shape in section 9 matches Ben's order and the dependency direction in section 5. (2) That the counters PR (section 9, PR 0) has a credible answer to the repository test policy and to Wade's "move it out of tree" item, since those two pull in opposite directions from Ben's request. (3) That the cost and "what is lost" statements are not understated. (4) The open decisions in section 10 are the ones jhan actually has to make.

## Short version

Ben is right on the facts: the PR is in the largest 4% of recent tron merges, its history is chronological rather than topical, and the seams he named are real (the K mirror depends on the kernel and dispatch but not the other way round; the page-share counters depend on nothing). His direct message fixes the order: counters first, then the AMX kernel without the mirror, then the mirror. The recommendation is to follow that order as a three-PR stack built by subtraction from the rebased tree, with the kernel PR keeping the number 3879 (eleven of the fourteen inline review threads sit on its lines) and topical commits inside each PR; estimated cost 7 to 12 author-hours with agent help (est.), of which the rebase and about half of Ben's review items are owed on any path.

## Words used here

- **PR 3879**: positron-ai/tron pull request "AMX software attention (default-off): QK/PV tile kernels + K-mirror arena", branch jhan-amx-p0, head 60d66d9c04, 35 commits, 18 files, +2,538 / -52 lines against main at 1407f48ddb.
- **tron**: the inference program under test. **rinzler**: its production server.
- **AMX**: Intel Advanced Matrix Extensions, the CPU tile-matrix instructions the change uses. **AVX**: the older vector instructions the existing attention code uses.
- **kernel**: the AMX tile routines in src/tron/kernels/amx_attn.cpp and their intrinsics-free header h/tron/kernels/amx_attn_iface.hpp (runtime detection, tile configuration, the QK and PV multiplies, Q packing).
- **dispatch**: the code in h/tron/models/self_attention.hpp that decides, per KV page, whether to call the AMX kernels or the existing AVX path, plus the gate predicates (shape, activation scalar) and the PV epilogue. "The AMX kernel without the K mirror" in Ben's message means kernel plus dispatch: the kernel is useless without the code that calls it.
- **canonical**: K kept in today's original single-copy storage and read as stored. This is the supported default (TRON_AMX_DISPATCH on, TRON_AMX_K_MIRROR off).
- **K mirror** (or **mirror**): a second copy of K in the AMX-friendly interleaved layout, kept in a parallel arena of ordinary RAM, written through on every K store, opt-in via TRON_AMX_K_MIRROR. The mirror formulation originates from Bill's PR #2934; the implementation and every number here are ours.
- **page-share counters**: h/tron/kernels/page_share_counters.hpp plus five guarded blocks in self_attention.hpp; instrumentation that counts how many query tokens visit the same KV page in one pass (the achievable batching width for AMX). Compiled only when -DTRON_PAGE_SHARE_COUNTERS=1 is passed by hand today. No CMake option, no test.
- **PR stack**: a chain of PRs where each is based on the previous one. tron's AGENTS.md rule: only the PR based on main may be marked ready for review; descendants stay draft until the parent merges.
- **squash / topical history**: collapsing many commits into one change, then re-cutting it into commits that each cover one topic instead of one point in time.
- **CHANGES_REQUESTED**: the GitHub review state that blocks merging until the reviewer re-approves.
- **p90 / p95**: the value that 90% (95%) of the population is below.
- **est.**: an estimate, not a measurement.

## 1. What Ben asked, in his words

Six Slack messages are top-level posts in #intel-amx on 2026-09-04; the seventh is a direct message (times PDT).

| Time | Where | Ben wrote |
|---|---|---|
| 11:04 | #intel-amx | "I'll admit, this is a remarkably large PR" |
| 11:05 | #intel-amx | "I can have a look but I do wonder whether there isn't a way to factor this that isn't a 2.5kLoC monolith" |
| 11:11 | #intel-amx | "one obvious split-point is between the AMX attention kernel itself and the K matrix mirror" |
| 11:11 | #intel-amx | "It would have really helped the review if these hadn't been conflated" |
| 11:23 | #intel-amx | "the page-sharing instrumentation would be another obvious cut-point" |
| 11:58 | #intel-amx | "can I suggest that we while my review is addressed that we also squash and rebuild the history with a slightly more topical structure? I have found agents to be quite good at this; it shouldn't take more than a few minutes of prompting followed by an hour of waiting." |
| 13:28 | DM to jhan | "right, I think it would break-down roughly as follows: • First introduce the page sharing counters • Then introduce the AMX kernel without the K mirror • Then introduce the K mirror" |

jhan answered in the channel at 12:00 ("Yes, I am looking into separating it to individual concerns, will update shortly") and at 13:24 asked Ben by direct message to write down what he had suggested in the gpt-oss meeting; the 13:28 message is the answer.

Between the 11:23 and 11:58 messages Ben also reviewed the PR on GitHub: CHANGES_REQUESTED at 11:56 PDT, ten inline comments between 11:19 and 12:19 PDT (section 7).

There are four asks.

- **Ask A (11:04 to 11:23): separate PRs.** Cut at two seams: the AMX kernel versus the K mirror, and the page-share instrumentation versus everything else.
- **Ask B (11:58): rebuilt commit history.** "Squash" means collapse the 35 commits into one combined change. "Rebuild the history with a more topical structure" means re-cut that change into commits that each cover one topic, with every later review fix-up folded into the commit it belongs to. Within a PR this keeps the number and URL; only the commit list changes, so a reviewer can read commit by commit.
- **Ask C (GitHub, 11:56): the review itself.** Two naming requests in the body (the kernel namespace is too general for one attention shape; "mirror" should be "amx_k_mirror") and ten inline items (section 7).
- **Ask D (DM, 13:28): the order of the split.** Three PRs, introduced in this order: page-share counters; AMX kernel without the K mirror; K mirror. This supersedes the earlier idea (in the first version of this note) of deleting the counters instead of landing them.

## 2. The situation the ask landed in

- At 09:40 jhan posted that PR 3879 was still looking for review. At 09:57 Jeremy wrote "Team, please review, we need this in."
- At 11:02 Wade posted a Claude-generated review as a GitHub comment [tron#3879, issuecomment-5544513215]. Ben's first Slack message came two minutes later. Wade's review found no functional bug and named three blocking items: no CI run on the current head (the last run was on commit bbb55ae5 of 2026-08-25), the repository test policy (four of the five new tests reduce to a no-op in every CI lane, and t_amx_logit_ab is registered DISABLED), and the mirror arena's RAM being outside the memory-pressure governor. One of its should-fix items concerns Ben's first PR: "page_share_counters.hpp: 91 lines of investigation instrumentation ... Move this to the notebook repo too." Section 9 says how the counters PR answers that.
- Review state today: five requested reviewers (Alexey, Mike, Bill, Wade, Ben); one CHANGES_REQUESTED (Ben); fourteen inline comments in the 14 days since the PR left draft on 2026-08-31 (ten by Ben today, two by Jeremy via Codex, two by jhan); zero approvals. GitHub marks the PR CONFLICTING against main, which has moved 987 commits since the PR's base. The PR carries no labels.

## 3. Is "remarkably large" a fair description? Measured

We measured the 300 most recently merged tron PRs (merged 2026-07-22 to 2026-09-04) through the GitHub API.

| Statistic (added lines per merged PR) | Value |
|---|---|
| median | 105 |
| p90 | 1,024 |
| p95 | 1,798 |
| PRs with 2,000 or more added lines | 12 of 300 (4%) |
| PR 3879 | 2,538 added, 52 removed, 18 files |

So PR 3879 is in the largest 4% of recent merges. It is not unprecedented: seven merged PRs since July added between 2,100 and 2,600 lines, including the hardware-attention stage-3 PR (#3385, +2,112) and today's rinzler reasoning-budget PR (#4137, +2,582).

Ben's own working unit is much smaller. He has 73 open PRs, 58 of them stacked on another PR rather than on main, with a median of 112 added lines per stacked PR; his current model-grouping series alone is about 27 stacked draft PRs (#4211 to #4232). The repository supports this style explicitly (the AGENTS.md stack rule quoted above), and a stacking tool (Graphite) is in use: 154 open PRs have a base other than main.

One more data point. Bill's earlier AMX attention PR (#2934, "Granite Rapids AMX attention: +11.7% TPS on gpt-oss-120b") is +2,911 lines in 24 files, has Ben as its only requested reviewer, and has had no human review comment since it opened on 2026-06-08 (last update 2026-07-23). Nobody asked Bill to split it. We do not know why it stalled, but a second 2,500-line AMX PR assigned to the same reviewer starts from the same place.

Meaning: by the repository's numbers the PR is large but not unusual; by Ben's personal standard it is about twenty times his unit of review. His reaction is consistent with how he works, and the request is legitimate.

## 4. What the 2,538 lines actually are, by concern

Counts below are non-blank added lines (2,394 in total; git's +2,538 also counts about 144 blank lines). Every hunk of every file was labelled with one concern; where one hunk mixed concerns it was split line by line.

| Concern | Code lines | Test lines | Total | Share | Where the code lives |
|---|---|---|---|---|---|
| K mirror | 600 | 572 | 1,172 | 49% | kv_cache.hpp 370, amx_attn_iface.hpp 70, amx_attn.cpp 37, self_attention.hpp 30, model.hpp 25, scheduler/full.hpp 24, rinzler.cpp 20, memory-governor doc 13, FUSE manifest 11; tests t_llama_unit 263, t_amx_arena_leak 168, t_amx_mirror 75, t_amx_numerics 50, others 16 |
| Kernel | 347 | 156 | 503 | 21% | amx_attn.cpp 214, amx_attn_iface.hpp 133; test t_amx_numerics 155 |
| Dispatch | 242 | 306 | 548 | 23% | self_attention.hpp 175, amx_attn_iface.hpp 48, kv_cache.hpp 19 (two V accessors); tests t_amx_dispatch_dtype 181, t_amx_logit_ab 61, t_amx_numerics 27, t_llama_unit 27, CMake 10 |
| Page-share counters | 101 | 0 | 101 | 4% | page_share_counters.hpp 85, self_attention.hpp 16 |
| Build (CMake options, -mamx unit, defines) | 28 | 0 | 28 | 1% | src/tron/CMakeLists.txt |
| Shared test scaffolding | 0 | 42 | 42 | 2% | includes and helpers in t_amx_numerics used by all three test groups; two comment lines in t_llama_unit |

Three observations.

- Half of the PR is the mirror. Ben's kernel / mirror cut removes 49% of the lines from the PR that carries the supported default.
- Half of what remains is tests: kernel plus dispatch code is 589 lines; their tests are 462 lines plus the 42 shared lines.
- The page-share counters are 4% of the PR and today the only part with no test, no CMake option, and no CI path. That is why a counters-first PR needs the additions listed in section 9.

## 5. Do Ben's cut points match the code's seams?

Yes. The compile and link dependencies run in one direction, so the concerns stack cleanly, and Ben's order (counters, kernel, mirror) is a valid bottom-up order.

```
"A <-- B" means B depends on A (B cannot compile without A).

build flags <-- kernel <-- dispatch <-- K mirror
                 |          |            |
                 |          |            +-- tests: t_amx_mirror,
                 |          |                t_amx_arena_leak,
                 |          |                t_llama_unit (mirror)
                 |          +-- tests: t_amx_dispatch_dtype,
                 |              t_amx_logit_ab
                 +-- tests: t_amx_numerics (kernel cases)

page-share counters: no arrows in either direction
(its hooks anchor on code that is unchanged on main)
```

- **Dispatch needs the kernel.** self_attention.hpp includes the kernel header outside any #ifdef and calls the kernel entry points [self_attention.hpp:19, :1360-1661 at head 60d66d9c04].
- **The mirror needs dispatch.** kv_cache.hpp has `#error "TRON_AMX_K_MIRROR requires TRON_AMX_DISPATCH"` [kv_cache.hpp:551-552]; the mirror's eligibility predicate calls the dispatch gate; the mirror read branch sits inside the dispatch's fast path and hands its result to the dispatch's PV epilogue.
- **Nothing needs the mirror.** No kernel or dispatch code symbol references a mirror symbol outside `#ifdef TRON_AMX_K_MIRROR`. What does cross the seam is prose: about twelve comment sentences in kernel and dispatch lines mention the mirror (for example Note [Tile stores write 16 rows] names the mirror kernel; the CMake TODO says "these two options"). In a kernel-only PR those sentences are reworded; the mirror PR restores them.
- **The mirror kernel lives in the kernel file.** qk_mirror_128x4 and pack_q_rows_128x4 are 37 lines at the tail of amx_attn.cpp (lines 43 and 232-269) and 70 lines of the interface header. They compile in every dispatch build today because the header has no #ifdef; their only callers are under `#ifdef TRON_AMX_K_MIRROR`. A mechanical split deletes those lines from the kernel PR.
- **The page-share counters are independent.** All five hook sites in self_attention.hpp anchor on lines that exist unchanged on main; the header compiles to nothing without the define. They can be the first PR, as Ben asks, with no dependency on anything else. Two adjacency points exist, not dependencies: the counters' include line sits next to the kernel header include, and the counters' flush block sits right after the kernel PR's end-of-region call. In the counters PR the flush follows the page loop directly; the kernel PR then rebases over it with a trivial merge.
- **Tests split cleanly except two files.** t_amx_numerics.cpp holds kernel (155), dispatch (27) and mirror (50) cases plus 40 shared lines; t_llama_unit.cpp holds 263 mirror lines and 27 dispatch lines, and one comment mentions both. Both files carry the kernel/dispatch part in the kernel PR and receive the mirror cases in the mirror PR.

So Ben's seams are exactly where the `#ifdef TRON_AMX_K_MIRROR` and `#ifdef TRON_PAGE_SHARE_COUNTERS` guards already are. The only design work is the full.hpp conflict described in section 9, and that is mirror-only.

## 6. Why the concerns were combined in the first place

This is a fair criticism, and it is better answered honestly than defended.

- The kernel, the dispatch, the mirror, and the counters were built as one measurement program over three days (2026-08-17 to 08-19): the counters measured the batching width that justified the kernels (prefill averages 110.9 query tokens per page visit; private decode 1.02; decode with a shared 1,024-token system prompt 5.06), increment 1 added the AMX QK kernel, increment 1b the PV kernel, increment 2 the in-block K mirror, increment 3 moved the mirror into the parallel arena. Each increment was measured against the previous one on the same machine, so the code grew in one tree.
- The PR was opened on 2026-08-19 as a draft with one commit of +1,506 lines that already contained all four concerns plus a 622-line benchmark harness and a design document. The harness and the document were later removed from the PR after review (commits ff7269a9 and 234c02bd).
- The 34 commits since then are review fix-ups. About half of them touch a single concern (roughly ten mirror-only, five kernel-only, four test-only; the exact count depends on how commits that touch mirror prose inside kernel files are classified), but the rest mix concerns, and none of them is a "here is the mirror" commit. The history is chronological, not topical. That is exactly what Ben's 11:58 message points at.
- The decision that the mirror is opt-in was made on 2026-08-19. Once the mirror was opt-in, the case for landing it in the same PR as the canonical path was convenience, not necessity.

## 7. Ben's review, mapped to where each item would go

Ben's review body: the kernel namespace `amx_attn` is "really a kernel implementing one very specific attention shape" and should be named for it; "mirror" should be `amx_k_mirror` or similar; "I trust that the AMX kernel itself is sound and didn't look too carefully at the math itself."

| Ben's comment (GitHub id) | File:line | In plain words | Goes to |
|---|---|---|---|
| global `inline` atomics (3936847383, 3937150401) | page_share_counters.hpp:27 | Why inline globals rather than extern? His second comment withdraws the objection (C++17 inline variables). | PR 0 (counters) |
| env var not documented (3936807517) | amx_attn_iface.hpp:39 | Where is TRON_AMX_DISABLE documented besides the source? Prefers a flag or a central doc. | PR 1 (kernel) |
| thread_local vector allocation (3936949728) | self_attention.hpp:1369 | The Q-pack slots allocate at runtime; amortized so probably fine, but why not attach to attn_accum, or a fixed array since max_minibatch_size is static? | PR 1 (dispatch) |
| move block to a helper (3936963481) | self_attention.hpp:1451 | The lazy Q-pack block should be its own function; apply_page_range is near 200 lines. | PR 1 (dispatch) |
| use mask_t (3936968255) | self_attention.hpp:1374 | The packed-mask bit array should reuse the existing mask type. | PR 1 (dispatch) |
| two control-flow paths (3936986164) | self_attention.hpp:1505 | apply_page_tok now has two distinct paths; make two functions with shared helpers. | PR 1 (dispatch) |
| syscall constants comment (3937013971) | amx_attn.cpp:17 | XFEATURE_XTILEDATA and friends need a short comment. | PR 1 (kernel) |
| memory_order_release on a load (3937077542) | kv_cache.hpp:487 | Pre-existing code ("I know you didn't write this"); release on a load is meaningless. | any PR, or a separate one-line fix |
| `tron::bf16` (3937239431) | self_attention.hpp:1419 | The packed Q pointer is typed uint16_t; should be the bf16 type. | PR 1 (dispatch) |
| namespace too general (body) | all kernel files | Name the kernel for its shape (128-wide heads, 4 query heads per KV head), not "AMX attention". | PR 1, decision needed (section 10) |
| `amx_k_mirror` (body) | all mirror files | Rename the mirror so a reader knows it exists for the AMX kernel. | PR 2 (mirror) |

Eleven of the fourteen inline threads on the PR (Ben's seven kernel/dispatch items, Jeremy's two, jhan's two) sit on lines of the kernel PR. That decides which branch should keep the PR number.

## 8. Options

| Option | What happens | Answers Ask A / D | Answers Ask B | Author cost (est.) | What it does not solve |
|---|---|---|---|---|---|
| Ben's order: three-PR stack (recommended) | Rebase; PR 0 = counters (base main); PR 1 = PR 3879 retitled: kernel + dispatch + build + their tests, topical commits; PR 2 = draft mirror PR stacked on PR 1 | yes, in the order he gave | yes, inside each PR | 7-12 h | PR 1 is still about 1,050 lines, ten times Ben's unit; PR 0 must be made policy-compliant (section 9) |
| Two-PR stack, counters deleted (first version of this note) | As above but the counters leave the tree | at both seams, but not in Ben's order | yes | 6-10 h | Contradicts Ask D; loses the measurement tool that justified the kernels |
| Four-PR stack | counters / kernel only / dispatch / mirror (or counters / kernel+dispatch / mirror arena / mirror reader) | yes, more finely | yes | 12-16 h to open; longer to merge (serial review) | A kernel-only PR has no caller (dead code until dispatch lands); the interface header's main Note must be split sentence by sentence; one more serial review round |
| One PR, topical commits only | Squash, re-cut into 5 or 6 topical commits, rebase, push to PR 3879 | no | yes | 3-5 h | Ignores Ask A and Ask D after a CHANGES_REQUESTED; the PR page still shows 2,500 lines |

Why not the four-PR stack now: a kernel-only PR is 555 lines of code nobody calls, and its review question ("are the tile contracts right") is the part Ben said he did not check. If Alexey later finds PR 2 too large, the arena-writer versus mirror-reader cut (about 1,020 versus 170 lines) can be made then; the reader is a contiguous block, so that later cut is cheap.

Why not topical commits alone: producing topical commits needs the same subtraction work as the split (section 9), so it costs about the same and shrinks nothing on the PR page.

## 9. Recommendation and how to do it

**Shape, in Ben's order.**

```
main --> PR 0 (new): page-share counters
         ~101 non-blank lines, plus a CMake option and a small test
         ready for review at once; independent of everything else

main --> PR 1 (= #3879, retitled): AMX kernel + dispatch (canonical)
  (or   ~1,050 non-blank lines; TRON_AMX_DISPATCH, default off
  PR 0) evidence: the "canonical" arm of every existing measurement

PR 1 --> PR 2 (new, draft): K mirror
         ~1,185 non-blank lines; TRON_AMX_K_MIRROR, default off
         evidence: the "mirror" arm of every existing measurement

Parked outside the tree: t_amx_logit_ab (61 lines, DISABLED test)
```

Reading order and merge order follow Ben's list. Whether PR 1's git base is main or PR 0's branch is a decision (section 10): the code does not need PR 0, so basing PR 1 on main lets Ben review PR 0 and PR 1 at the same time (AGENTS.md allows only main-based PRs to be marked ready); basing it on PR 0 follows his "first ... then" literally but keeps PR 1 a draft until the counters merge.

**PR 0, the counters, and the two objections it must answer.** Ben asks for it first; Wade's review asks for it to leave the tree; AGENTS.md says every committed test must run in CI and, read strictly, a header that no build compiles is dead code. Three additions make PR 0 defensible without changing what the counters do:

1. A CMake option (`option(TRON_PAGE_SHARE_COUNTERS ...)`, default OFF, adding the define) so the instrumentation is a documented build configuration rather than a hand-passed flag. A few lines in src/tron/CMakeLists.txt.
2. A small host-only test of the pure logic (`local::page()` bucket assignment and `flush()` sums), compiled with the option on in the CMake lane. About 40 lines; runs on any runner, needs no AMX.
3. A PR description that states the purpose and the record it produced: the batching widths measured on 2026-08-19 (prefill 110.9 query tokens per page visit, private decode 1.02, shared-prompt decode 5.06), which are the numbers that justified the AMX kernels. That answers Wade's "investigation instrumentation" point with the reason it should stay: the measurement is repeatable in-tree.

Ben's two inline comments on the header (inline globals) go here; his second comment already withdrew the objection, so a one-line comment in the header settles it.

**Steps.**

1. Rebase the full tree onto origin/main once, in a new worktree under ~/workspace/ai-runs/. Ten files were also changed on main; four have real conflicts (5 blocks). Three are trivial: an include line in self_attention.hpp, the test registrations in t/CMakeLists.txt, and two new test cases in t_llama_unit.cpp landing next to a test main added. One is real and mirror-only: main rewrote book creation in scheduler/full.hpp (max_book_pages_for_dma_allocation, try_create_book_with_retry, commit 9076993a), so the mirror-eligibility flag must be threaded through main's new helper. Also required by the rebase: main now makes the attention scale a mandatory field (static_assert in h/tron/plugins/llama.hpp:180), so the two new test configurations at t/t_amx_dispatch_dtype.cpp:54 and t/t_llama_unit.cpp:1041 need an `.attention_scale` entry or they do not compile.
2. Subtract, do not cherry-pick. The first commit already mixed every concern, so no subset of commits gives a per-concern tree; the single-concern fix-up commits are useful only as commit-message sources. From the rebased tree, produce three patch sets by the line map in section 4: (a) the counters (header plus five hooks; in this PR the flush block follows the page loop directly); (b) the kernel PR: everything minus the mirror lines (kv_cache.hpp mirror blocks, model.hpp, full.hpp, rinzler.cpp, the FUSE manifest, the governor doc, amx_attn.cpp 43 and 232-269, the header's mirror section, the two `#ifdef TRON_AMX_K_MIRROR / #else / #endif` wrappers in self_attention.hpp so the canonical calls become unconditional, the mirror test cases) and minus the counters, with the roughly twelve mirror-mentioning comment sentences reworded and the 3-argument book constructor in t_amx_dispatch_dtype.cpp; (c) the mirror PR: the deleted mirror lines re-applied on top of (b). Check: PR 0 + PR 1 + PR 2 applied together must reproduce the rebased full tree minus t_amx_logit_ab.
3. Rebuild each PR's history as topical commits (PR 1: kernel unit and header; dispatch integration; build option and CI flag; tests). These are the same per-concern patch files as step 2, so Ask B costs nothing extra.
4. Apply the renames while re-authoring, because a rename touches every file and is cheapest before the trees diverge: `amx_k_mirror` in PR 2 (Ben's request; 387 of PR 2's lines are in kv_cache.hpp); the kernel namespace in PR 1 needs jhan's decision (section 10).
5. CI. Add `-DTRON_AMX_DISPATCH=ON` to the CMake lane's configure step in PR 1 (.github/workflows/cmake-single-platform.yml line 365; this is issue #3997 option 1). The test pool `[self-hosted, fpga, test, avx512]` has six runners, three of them Intel Granite Rapids with AMX (delphi-17cf, delphi-3bd6, delphi-3bda) [README.ci.md, Runner Inventory], so the kernel and dispatch tests execute on runs that land on those hosts and skip with a warning on the Genoa hosts. Issue #3997's sentence "no CI host is known to have AMX" is out of date. PR 0 adds its own option to the same configure line; PR 2 adds `-DTRON_AMX_K_MIRROR=ON`. This removes Wade's first two blocking items for PR 1.
6. Park t_amx_logit_ab.cpp and its DISABLED registration outside the tree (for example on jhan-dd-debug). AGENTS.md: "A test that does not execute in CI must not be committed, except in extremely rare cases explicitly approved by the user." Wade marked this policy blocking.
7. Open PR 0 (ready for review, `Skip benchmarks`). Force-push PR 1 to jhan-amx-p0 and retitle PR 3879 ("AMX software attention, canonical path: kernel + dispatch, default-off"); GitHub keeps Ben's and Jeremy's threads as "outdated" where lines moved. Open PR 2 as a draft with base jhan-amx-p0. `Skip benchmarks` on all three (AGENTS.md: adding it needs no approval; none of them changes a default build). Post in PR 3879 a map from each of the fourteen inline threads to PR 0, PR 1, or PR 2.
8. Verify on delphi-3bda outside the CI window under the campaign guard: build PR 0 with its option on; PR 1 with the options OFF and with DISPATCH ON; PR 2 with both ON; run the new counters test, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit (PR 1) and t_amx_mirror, t_amx_arena_leak, t_llama_unit (PR 2).

**Evidence carries over.** Every measurement in the PR description and in the in-flight systems-test round compares three arms: AMX off, canonical (DISPATCH on, mirror off), mirror (both on). PR 1 is the canonical arm; PR 2 is the mirror arm; PR 0 changes no built configuration and needs no performance evidence. Each PR description takes its own column of the existing tables (qwen-3-4b-tp2 decode at 8 users, prompt 8192: canonical +17.5%, mirror +28.1%). One caveat to state in the descriptions: those binaries were built from the pre-rebase head, and the canonical binary also contained the then-uncalled mirror kernel.

**Cost (est.).** 7 to 12 author-hours with agent assistance, about one and a half calendar days: rebase and the five conflict blocks 1-2 h; subtraction into three patch sets, rewording, un-wrapping 2-4 h; PR 0's CMake option, test, and description 1-2 h; builds and test runs on delphi-3bda 1 h; GitHub plumbing, descriptions, thread map 1-2 h. Ben's review items are not counted; they are owed on every path. Assumptions: delphi-3bda is free outside the nightly CI window; no new review comments arrive mid-split.

**What is lost.** The 35-commit history (of little value: it records review rounds, not design); the four earlier inline anchors and Ben's ten become "outdated" threads that he has to re-read against the new lines; the PR description is rewritten in three; the systems-test round 1 binaries (built from 60d66d9c04, 1 of 12 cells done) no longer correspond to any PR tip, so the canonical and mirror cells should be re-run on the new tips if that round is to be quoted as PR evidence.

## 10. Decisions only jhan can make

1. PR 1's base: main (PR 0 and PR 1 reviewable at the same time; recommended) or PR 0's branch (follows Ben's "first ... then" literally; PR 1 stays draft until PR 0 merges)?
2. PR 0's answer to the test policy: add the CMake option plus the small host test (recommended), or ask for the AGENTS.md "extremely rare cases" exception explicitly in the PR?
3. Force-push PR 3879 as PR 1 (keeps the review, marks Ben's anchors outdated) or open a fresh PR 1 and leave PR 3879 as an archive? This note assumes force-push.
4. The kernel namespace: rename now in PR 1 (Ben's body comment; touches every file) or keep `amx_attn` and settle the name in review? A shape-specific name would look like `amx_attn_h128g4` or similar. `amx_k_mirror` goes to PR 2 either way.
5. Squash each PR into topical commits (recommended) or keep the rebased commits plus one subtraction commit?
6. The CI flags: does the CI team (issue #3997) need to acknowledge before PR 0 and PR 1 change the CMake lane's configure line, and is coverage only on the three Granite Rapids runners acceptable?
7. The in-flight systems-test round: stop it now and re-run canonical on PR 1's tip and mirror on PR 2's tip, or let it finish as evidence for the combined tree?
8. Wade's "ungoverned mirror arena RAM": open a design thread with Wade inside PR 2 (recommended), or pre-build an admission check (refuse the arena when available memory is below the arena size plus a margin) before he weighs in?

## 11. The strongest case against this recommendation

Two objections, stated fairly.

- **It answers Ben's words, not his complaint.** PR 1 stays at about 1,050 lines with kernel and dispatch together; Ben's merged PRs are 4 to 321 lines. PR 2 at about 1,185 lines is itself a "remarkably large PR", and its 387 kv_cache.hpp lines, the re-implemented full.hpp threading, and Wade's RAM-governance question all land on Alexey at once. A four-PR stack gives each PR one owner and confines the governance argument to about 500 non-test lines. Force-pushing under an active CHANGES_REQUESTED also makes Ben re-read his own anchors. If reviewer routing matters more than calendar time, the four-PR stack is the better choice; the three-PR stack is the cheaper one and can still be cut further later.
- **Counters first puts the least valuable code on the critical path.** Jeremy wants the canonical AMX path in; PR 0 is measurement instrumentation that no production build compiles. Wade's review asked for it to leave the tree, and making it policy-compliant costs an extra option, an extra test, and a review round of its own. The mitigation is to base PR 1 on main so PR 0 does not gate it (section 10, decision 1); if Ben insists on a literal stack, PR 0's small size (about 150 lines with the additions) should make its review short.

## 12. Draft reply to Ben (Slack, not posted)

> Agreed, and thanks for writing the order down. Plan: (1) a small PR with the page-sharing counters, made a proper build option with a host-only test so it meets the test policy; (2) #3879 retitled to the canonical path: kernel + dispatch + tests, about 1,050 lines, rebuilt as four topical commits after the rebase onto main; (3) the K mirror as a stacked draft on top, about 1,185 lines, with the amx_k_mirror rename applied while re-authoring. The mirror is 49% of today's diff (600 code + 572 test lines) and depends on the kernel and dispatch but not the other way round, so the cut is clean. On the kernel namespace, do you have a name in mind for the 128-wide / 4-query-head shape? Your inline comments all fall in the counters and canonical PRs, so they keep their threads (GitHub will mark them outdated where lines move). One question: do you want (2) based on (1), or on main so you can review both at once? Target: new push by [date].
