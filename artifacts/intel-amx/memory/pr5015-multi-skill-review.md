---
name: pr5015-multi-skill-review
description: "2026-10-18 PR 5015 (Glimmer kv_mul 16): review round (7 reviews/43 comments) + ROUND 3 DONE 2026-10-19 00:1x UTC (head 4c4b7b8864, 14 replies, 10 threads resolved, body patched; CI-enable thread 4308387058 deferred to #3997 by jhan, resolved) - reviewed with a general pass + 6 skills (ben, Wade, cpp-guide, positron, simplify-comments, tron): 7 reviews / 43 inline comments posted at head 5061623a34, each prefixed with the skill name; deduped against another agent's 3 earlier comments (CI coverage, lane masks, P-scratch comment)"
metadata:
  node_type: memory
  type: project
  originSessionId: 146c3a6e-a1e1-402b-a412-2cd6ec96fdfc
  modified: 2026-10-18T19:39:32.204Z
---

Review of positron-ai/tron PR #5015 at head 5061623a34, posted 2026-10-18 ~19:4x UTC as seven COMMENT reviews
(ids 5564633240 PR review, 5564633376 ben-review, 5564633518 Wade-code-review, 5564633664 cpp-coding-guide,
5564633747 positron-code-review, 5564633851 simplify-cpp-comments, 5564634294 tron-code-review) plus two
thread replies (r4308444255 SKIP remedy, r4308444338 uppercase PAIR_SEL/QUAD_SEL). Workflow wf_09f606f9-dc4
(278 agents: 12 finders, 3-lens adversarial verify per finding, critic per reviewer, composer per reviewer);
71 findings survived, 43 posted after pruning duplicates and pre-existing items.

Another agent had posted review 5564576364 with 3 inline comments (wade: CI omits TRON_AMX_DISPATCH so 16-head
cases never run in required CI + probe warning; cpp-guide: lane & 1 / lane & 2 masks, lane template args,
/*repeat=*/true; simplify: P scratch comment at amx_attn.cpp:283). Those topics were dropped from mine.

Main findings worth acting on (all nits/should-fix, no code defect found): PR body says wrong group size
"fails to link" (it fails to compile at the requires clause); body says "vshufps" (code is _mm512_shuffle_f32x4
= vshuff32x4); "2 sections skipped" is 2 test cases; "linker rewrites both to the same code" is unmeasured;
nightly run 38999609242 is in positron-ai/systems_test, not tron; raw-result file names unreadable from GitHub;
ben: alias the two page-view types, operation_kv_mul in packed_amx_query, derive lanes from group_heads;
Wade: `g` param name, check_qk/check_pv header comments, redundant inline, static_assert else branch at the
lane store, duplicate 16-head round 2; simplify: 22 comment cuts (store_transposed_rows block, tile-geometry
comment, dispatch comment shape list, s_pages static_assert restatement ...); tron: add KV_MUL_32 refusal row.

**How to apply:** scratchpad review/ dir of session 146c3a6e holds reviews-final.json and post_reviews.py.
If jhan asks to apply the comments, start with the PR-body wording items, then the code nits. Related:
[[glimmer-kvmul16-implementation]], [[wade-code-review-skill]], [[review-body-format]].

ROUND 3 (2026-10-18 23:4x - 2026-10-19 00:1x UTC, jhan: "act on all open comments; follow my comments where I left them,
else respond to the originals"): another agent had pushed a6b93f1f71 (22 simplify items) and 7e7f52d761 (accepted items:
unpacked-tile name, operation_kv_mul, `g` param, lanes = group_heads / ROWS_PER_LANE_4 with if constexpr, TILE_ROWS_16).
My commit 4c4b7b8864 (worktree ai-runs/tron-glimmer-amx): aliases const_k_row_major_plane_view / const_v_vnni_plane_view
(jhan's names) in amx_attn_iface.hpp:140-141 used by declarations/definitions/instantiations; dispatch test: group_heads =
geometry.kv_mul() for the three REQUIREs, named query-fill values, 16-head section one round (5,756 -> 3,694 assertions),
fakes+probe inside #ifdef TRON_AMX_DISPATCH (kills the CI "probe not needed" warning), codex credit deleted; numerics:
KV_MUL_32 refusal row (+1 assertion: 17,425 / kill switch 4,111), check_qk/check_pv comments, WARN+return -> Catch2 SKIP
(kill switch: "4 | 2 passed | 2 skipped", rc 0); CMakeLists comment "reported as skipped". Tests on 3bda our half
(tron-g16h, plain-shell clang-19, incremental 101 s) all pass. Object compare (lcheck-obj, clang 19.1.7 -O3): pack<4>/qk<4>
identical to main (509/204), pv<4> 121 opcodes same order (TLS + register picks differ); vs 5061623a34 all six kernels
identical except two adjacent adds swapped in qk<16>. Rejected by jhan (withdrawn, no change): lane masks (too nit),
`inline` (too nit), header "Issue #5021" wording (no issue numbers in source). Replies 4309345823..4309346810; PR comment
issuecomment-6256815414 answers the Wade review-body items (nightly row = positron-ai/systems_test run 38999609242, final
"Running averages: TTFT=3696, TPS=78.69" line -> TTFT cell 3696 not 3697; "our half" defined; raw-result files = author's
files on 3bda). Body patch script scratchpad round3/body_patch.py (re-fetches the live body; jhan's own edits kept).
OPEN for jhan: thread 4308387058 (Wade: enable TRON_AMX_DISPATCH in the required nix build) - my reply defers it to issue
#3997's PR because the flag adds the kernels to libtron and would route the lane's model tests through AMX on an AMX runner;
AGENTS.md:22-26 says an agent may not decide that exception, so jhan must confirm or overrule. Verification workflow
wf_93092d3d-4e2 (16 agents) caught: libtron not "test library", #3997 tracker, stale CMake comment, s -> s_amx, semicolon
comment, body "built the same way" (nix develop vs plain shell), "Every result" scope, nightly row source.
UPDATE 2026-10-19 00:3x UTC: jhan: "yes, good call to defer to 3997. Please proceed with your proposal" -> issue #3997 comment issuecomment-6257030210 (lane facts, one-line fix, two consequences for the CI owner, no names), thread 4308387058 replied and resolved. Nothing open on PR 5015 from the review rounds.


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): 2026-10-18: 7 reviews / 43 inline comments; ROUND 3 DONE 2026-10-19 head 4c4b7b8864 (14 replies, 10 resolved, body patched); CI-enable thread deferred to #3997 (issue comment posted 2026-10-19), all threads resolved
