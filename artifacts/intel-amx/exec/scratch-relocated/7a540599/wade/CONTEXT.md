# Context for the Wade-code-review analysis (read fully before working)

## What this is
PR positron-ai/tron #4557 "Typed KV-cache tensors for VNNI packed V and native K" (issue 4525). Reviewer Wade (GitHub Wado-posi) posted review 5420005787 on 2026-10-05 20:18 UTC at PR head 96a6220ab6 (a merge of main e5fa372c19 into the branch). Our own agent reviews before his (listed below) did NOT raise his points. The job: for each Wade point, verify it against the code, explain WHY our reviews missed it, and derive a detection rule an agent can execute.

## Where the code is
- Worktree (READ ONLY, do not edit, do not run state-changing git): /home/jhan/workspace/ai-runs/tron-issue4525. Its HEAD is now c5d44bd86f (a later squash). The REVIEWED head is 96a6220ab6; read reviewed files with `git -C /home/jhan/workspace/ai-runs/tron-issue4525 show 96a6220ab6:t/t_llama_unit.cpp` etc. The main side of the merge is e5fa372c19. The PR diff as reviewed: /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade/pr4557-at-96a6220ab6.diff (git diff e5fa372c19 96a6220ab6, 14 files).
- Line numbers in Wade's comments are at 96a6220ab6.
- The PR description Wade read: /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade/pr4557-body-as-reviewed.md. The live body (edited after the review): /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade/pr4557-body-live.md.
- Repo test policy: AGENTS.md (section "Tests", lines ~35-56) and t/AGENTS.md in the worktree. NaN rule: AGENTS.md "Treat NaN as corruption".
- CI build flags: .github/workflows/cmake-single-platform.yml at e5fa372c19 (git show e5fa372c19:.github/workflows/cmake-single-platform.yml).

## Wade's review 5420005787 (verbatim)
Summary body:
- **Constant names with the value built in**: `V_ODD_TOKEN_LANE_MASK_0XFFFF0000`, `BF16_BITS_16`, `ACCUMULATOR_TILE_0..3`, `APPENDED_TOKENS_7`, `PATTERN_BASE_0X3C00`, etc. `ACCUMULATOR_TILE_0` reads no better than the `0 /* dest tile */` it replaces.
- **Unrelated changes**: the AMX tile-number constants (ec795fbce87cc89d2f0445a0eef8d3e7f4103260) and the `t_heap_v2` alignment check aren't part of typed tensors; please split them out.
- **Commits**: 20, three of them rewording one Note. Please squash.
- **PR description**:
  - It says the required CI builds AMX-off. `.github/workflows/cmake-single-platform.yml:355` builds with `-DTRON_AMX_DISPATCH=ON`.
  - The unit-test and token-identity results are from c12df586b6 / faf8ee42ca, before the merge of main. Please re-run them or mark them as pre-merge.
  - Assertion-count arithmetic, UTC build timestamps and log paths can go.

Inline comments: see /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade/wade-inline-4557.md (7 comments: 4188336250 t_llama_unit.cpp:3575 NaN->inf and rounding rows; 4188336256 t_amx_numerics.cpp:227 formula check behind available() early return; 4188336267 kv_cache_fwd.hpp:43 native_k_view alias; 4188336279 memory.hpp:192 global operator new[] overload needs maintainer sign-off; 4188336302 t_llama_unit.cpp:419 structure-only compile-time checks; 4188336316 t_llama_unit.cpp:3298 duplicate parity coverage; 4188336324 t_llama_unit.cpp:3293 section name says the opposite).

jhan's (the author's) answers so far: constant-name style is jhan's deliberate convention (his C++ guide: named constexpr with the value suffixed) introduced in PR #3879; "I do not see TRON coding guide prohibits such style" -> this point is a known taste disagreement, NOT a miss to fix. The memory.hpp thread: jhan replied that commit 39a6899 was the comment update Ben asked for (Ben's thread 4159939672), and resolved it.

## Our reviews of this PR BEFORE Wade (what existed and still missed his points)
1. 2026-09-22 workflow wf_d2b470ca-509: 8 finder lenses (behavior, compile, callers, includes, tests, adversarial, prose, design) -> 3 refuters per finding -> critic. The exact finder prompts: /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade/prior-0922-lenses.txt. What they found: /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade/prior-0922-results.txt. NOTE the tests lens prompt (a) already cited the test policy ("every new or changed assertion must protect a durable contract ... no testing of implementation details without a consumer") and asked to judge the packed-bits TEST_CASE and the STATIC_REQUIRE block.
2. 2026-09-23 guide checks (page status/pr4557-guide-checks.html): C++ coding guide (named constants, braces) + plain-English check of the description. Style only.
3. 2026-09-30 Ben's review (B1-B6) and our response analysis (page status/PR4557-respond-2-Ben.html): enums vs bool flags, Note rename, Note [DMA allocation creates objects] wording, non-ISO reads ticket, v_vnni_row without users (dropped), row-view helper dedup (#4697).
4. Standing skills in ~/.claude/skills: tron-code-review/SKILL.md (execution paths, counters, async ownership, test meaningfulness), ben-review/SKILL.md (missing domain abstractions, >4 params), positron-code-review/SKILL.md (review-round narration in comments), cpp-coding-guide/SKILL.md. Read them to say which one SHOULD have caught a point and why its wording let it through.
5. The most recent full review recipe (PR 4596, 2026-09-29): 12 lenses: forward-pass, visit-tallies, timers, fpga-path, async-ownership, worker-layer-index, off-state-cost, tests (test meaningfulness: calls the boundary? fake retains info? which semantic break fails it? which breaks NOT caught? test gaps), docs-exports, main-drift, cpp-guide, conditions. Script: /home/jhan/workspace/intel-AMX/exec/review-20260929/workflows/tron-review-pr4596-wf_9d1f4e76-619.js.

## Wade's earlier comments on other PRs (pattern source; memory notes in /home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/)
- PR 4265 (wade-move-test-question-pr4265.md): why a new test binary; extend t_llama_unit instead (test policy: extend the closest existing test).
- PR 4267 (wade-fuse-question-pr4267.md): asked for FUSE/env-var live counters.
- PR 4596 round 4 (wade-pr4596-review-response.md): W1 timer hook sits only on the FPGA join path while docs claim both modes (docs widened, hook never moved); W2 forward_scope placement at the single caller; W3 forward class semantics mixing prompt and decode; W4 nine guards dead in production -> asserts + fixtures; W5 rows keyed by pool index vs attention index.
- PR 4596 round 5 (wade-pr4596-round5-response.md): W6/W7 review-round narration in source comments ("scrub please"); W8 duplicate test case (drop it); W9 row key computed two ways -> one helper.
- Repo-wide corpus of his inline comments (if present): /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a540599-d50b-411e-aee6-c923ccb479ca/scratchpad/wade/wade-inline-corpus.jsonl.

## Ground rules for every agent
- Cite file:line at 96a6220ab6 with a short quote for every factual claim. Distinguish what you read from what you infer.
- Plain English: define a code name or acronym at first use, one claim per sentence.
- Return raw data in the schema; no human-facing prose.
