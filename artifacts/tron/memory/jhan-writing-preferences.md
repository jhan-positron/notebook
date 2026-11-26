---
name: jhan-writing-preferences
description: "jhan's stated preferences (2026-11-20) on sentence length, bullets and labels, with the boundary that short simple sentences stay whole"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 59c0ff77-e70e-4ae6-800a-130e4fcb789d
  modified: 2026-11-20T18:55:18.754Z
---

jhan, 2026-11-20, in the prompt that asked for an inspection of the plain-english skill:

- "I prefer short sentences over long or complex main/sub sentence structure."
- "I prefer bullet pointing when consecutive sentences (may separated by comma) are about different perspectives of same thing, or there is an underlying sequence."

jhan, 2026-11-20 09:50 PST, replying to Codex's first inspection draft (found in the Codex session record):

- The draft was "towards right direction, but seems a little overkill".
- This sentence must stay whole: "The cache reduces repeated reads, it uses more memory, and it needs explicit invalidation." Each clause is "simple semantically and short, not necessary to break".
- Do not introduce bullet labels such as "Benefit", "Cost", "Requirement". They are "against smooth reading".

**Why:** the skill's rules did not deliver the first two points. A first rewording of mine over-corrected: in a test it turned the cache sentence into a list in 3 of 3 runs and added 22 labels.

**How to apply:** in every prose output for jhan:

- Fix long sentences (over about 20 to 25 words): split joined claims, or turn a list or sequence into bullets or a numbered list.
- Leave a short sentence alone when its clauses are short and simple, joins included.
- Start each bullet with its content. No category labels. A term followed by its definition is fine.
- Keep the Short version sentences short too.

The numbers (25 hard, 20 as the point below which nothing is forced, 3 sentences per paragraph or bullet) are my proposal. jhan has not confirmed them. Tools to check a file: [[plain-english-inspection-tools]].
