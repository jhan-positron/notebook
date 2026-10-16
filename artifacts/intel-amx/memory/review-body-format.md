---
name: review-body-format
description: "jhan's feedback on the mock-review verdict body (CHANGES_REQUESTED text) - paragraphs or bullets, and comment ids (R1-10 ...) instead of brief prose allusions"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 72fd1ccd-f69f-4237-958c-0f9519541d9b
  modified: 2026-08-27T05:01:10.436Z
---

For the Alexey mock-review deliverables (PR3879/alexey-review.html and the .md twin), the verdict body under
CHANGES_REQUESTED must be readable, not a single prose paragraph: separate paragraphs (progress / status of the big
items / new problems / declined items / what blocks / description + CI), and the "What still blocks from my side"
part as a bullet list where every item names its comment id (R1-10, R3-02, ...) with a short clause, not a
paraphrase like "the 16-row store claim" alone.

**Why:** jhan reads the body to decide what to fix next; brief allusions to comments cannot be matched to the
threads below without ids, and one dense paragraph in his voice (the 2026 Alexey writes prose, bullet lists in
5 of 365 bodies) is too hard to scan. jhan asked for this on 2026-08-26 after round 6.

**How to apply:** in roundN_data.py write BODY with "\n\n" between paragraphs and "- Rx-yy - <clause>" bullet
lines; gen_review6.py's render_body() turns them into <p>/<ul> in HTML (Markdown renders them natively). Keep his
voice inside each paragraph; note the format deviation from the persona once in the Method section. Apply the same
to any future reviewer persona's verdict body. See [[reviewer-personas]].
