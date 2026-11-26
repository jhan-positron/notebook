---
name: review-replies-keep-simple
description: "jhan 2026-11-19 - answer a reviewer's process concern with the simplest change and the shortest explanation; hand tests on the CI machine count as CI-equivalent evidence; 2026-11-20 - no downgrading words such as 'only' or 'I accept' in replies"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5923dad0-d660-4ecb-a1a6-4f80f4865614
  modified: 2026-11-24T06:26:41.645Z
---

jhan, 2026-11-19, on reviewer Isaac's blocker for PR 5022 that no pull-request CI lane builds the AMX code (point D1, issue #3997): "I kind of think Issac and we are treating this too serious than what it deserves. We did the manual testing at CI machine delphi-3bda when we had the access, so all the tests were CI equivalent, but not run from CI process. I leave the decision to you, if you can think of a simpler change and explaination and without mentioning issue 3997 at all, that would be great; if you think what you current have is the best to move forward, please do."

My draft at that point had a 10-line CMake comment, an 18-line README paragraph, a promise of a separate one-line PR under #3997 and a five-paragraph reply.

**Why:** jhan judged the response heavier than the finding.

Correction of 2026-11-23 (my reading was wrong). I had written here that "the finding was one stale sentence in a comment and in a README". The finding had two halves. One half was the stale sentence, and round 2 fixed it. The other half was a coverage gap: `t_amx_dispatch_dtype` compiled to a placeholder case in the required CI lane. Round 2 left that half open. Isaac kept "changes requested" for it on 2026-11-24 and supplied the fix himself (PR 5606: the test target passes `DEFINES TRON_AMX_DISPATCH`, as `t_page_share_counters` does). A simpler reply does not close a finding. See [[declined-fix-leaves-finding-open]].

**How to apply (my reading):**
- Size the reply and the code change to the finding. Fix the stale text in the fewest lines, state the decision in one sentence, list the evidence in bullets.
- Do not cite a tracking issue or promise a follow-up PR in a reply unless jhan asks for it.
- Tests and performance data taken by hand on delphi-3bda count as CI-machine evidence: jhan calls it "*the* CI machine" (2026-11-19). Say so plainly in replies and PR bodies.
- For small edits made after a measurement, jhan accepts a stated low risk instead of a new measurement (2026-11-19: "I accept the risk that the PR perf numbers were not tested from latest CI"). Write that plainly: what was measured where, why the later edits are low risk, and that the nightly test follows the merge.
- When jhan delegates a wording decision, decide and proceed; do not come back with options. This covers wording only. A narrower code fix for a confirmed finding is not a wording option: show it to jhan (added 2026-11-23, my reading).

Tone, added 2026-11-20. jhan on my draft reply to an automated review of PR 5022 (card B2), about the sentence "I accept for this PR that they run in the legacy workflow only": "'legacy workflow only' reads unnecessary harsh to me". The sentence was my wording of jhan's decision to keep the AMX build flag out of the PR.

**How to apply (my reading):** in a reply, say where something runs or what was done, as a plain fact. Do not add words that grade it down ("only", "I accept that", "merely"). The reworded draft says: "They run in the CMake workflow (`cmake-single-platform.yml`), which builds with the option ON. README.ci.md describes its manual run on the final commit of a PR." jhan did not say whether the harsh part was "legacy", "only" or both, so I removed both from that reply. This is one comment on one sentence; do not rewrite approved or posted replies because of it.

Related: [[changes-need-system-tests]], [[isaac-reviews-are-agent-pipeline]].
