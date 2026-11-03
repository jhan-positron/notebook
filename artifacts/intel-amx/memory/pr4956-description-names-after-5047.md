---
name: pr4956-description-names-after-5047
description: "jhan 2026-10-21 'please remember this': if PR 5047 merges into PR 4956's branch, the 'How to review this PR' bullets of PR 4956's body name page::k_packed, kv_block::k_view and the compile-time 'temporary gate', which PR 5047 removes; they need the new names (page::score_k, page::try_score_k_amx, set_k_row with an expression)"
metadata:
  type: project
---

If PR 5047 (bgamari/vnnik-1, the K-layout refactor) is merged into PR 4956's branch jhan-vnnik-1-layout, PR 4956's body goes stale: its "How to review this PR" bullets name `page::k_packed`, `kv_block::k_view` and the compile-time "temporary gate". PR 5047 removes all three. The new names are `page::score_k`, `page::try_score_k_amx` and `page::set_k_row` with an expression (the cache owns the layout).

**Why:** jhan asked to remember this on 2026-10-21 (item 6 of "What to tell Ben" in random/Ben-PR4956.html).
**How to apply:** when PR 5047 merges (or when jhan asks for the PR 4956 body), rewrite those bullets with the new names before anything else, and re-fetch the live body first [[pr-body-refetch-before-edit]]. Related: [[pr5047-ben-refactor-review]], [[ben-stack-reexpress-20261021]].
