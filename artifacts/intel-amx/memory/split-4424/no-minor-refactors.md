---
name: no-minor-refactors
description: "jhan rejects small refactors of working code (moving a call into a helper, shortening call lines); answer the question, do not churn the code"
metadata:
  node_type: memory
  type: feedback
  originSessionId: e6f04fce-1790-4fc0-8220-267a113c6ec1
  modified: 2026-10-15T03:05:55.089Z
---

On 2026-10-15 jhan asked, about PR #4901, whether a repeated `if (k_block_is_vnni(k_state_ix(slot), i_page))`
branch should become a small function. The answer moved the `k_state_ix` call into the predicate (5 lines, three
call sites shortened). jhan: "please undo the change, it is unnecessary to change this minor stuff". The change
was reverted.

**Why:** A change that only moves a call or shortens lines adds review and commit noise without a behaviour or
readability gain he values. His "consider" questions ask for an assessment, not for a change.

**How to apply:** When jhan asks "consider X" or "why not Y" about working code, answer with the count and the
assessment, and put any edit forward as an option that he picks, not as a change already in the tree. Make a
helper only when the whole snippet (condition and body) repeats verbatim. Same for spelling choices such as
`~uint64_t{}` vs `~uint64_t{0}`: recommend, do not apply. See [[pr4-split-execution]]. (jhan installed the simplify-cpp-comments skill on 2026-10-15 in his own
revision: rule 0 "do diff only" added, the helper rule removed. The cpp-coding-guide bool rule is his wording since the
same day: a named constexpr bool only as a call argument, a default argument takes the literal.)
