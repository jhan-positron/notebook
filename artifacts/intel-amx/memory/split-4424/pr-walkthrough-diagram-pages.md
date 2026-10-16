---
name: pr-walkthrough-diagram-pages
description: 2026-10-14 four walk-through pages for Ben (one per split PR 4868/4887/4898/4901) built from the PR 4424 base diagrams; where they are, how they were verified, how to rebuild
metadata:
  type: project
---

jhan asked (2026-10-14) for one HTML page per split PR to walk Ben through the stack, using the base diagrams of the three PR 4424 pages (merge-4737-2-4424/diagramming-code-changes-{kv_cache,k_vnni,model}.hpp.html) to introduce the data models and main algorithms. jhan wrote "4824" in the list; 4824 is the draft review copy of the whole PR 4424, so the fourth page was built for PR-3 #4898 (assumption stated to jhan, not yet confirmed).

Delivered: split-4424/diagrams-PR1-4868.html, diagrams-PR2-4887.html, diagrams-PR3-4898.html, diagrams-PR4-4901.html (480-760 KB each). Each page: Short version, Words, "What this PR adds" table (PR-head file:line), walk-through order, the involved base diagrams copied verbatim (h3..</figure> blocks, SVG, legend, caption, box list) with four status boxes (in this PR / already there / lands in PR-n / not in the stack), the source pages' change sections (C0-C10, K0-K9, M0-M7) that land in the PR with links, gaps. Diagram line numbers cite PR 4424 head 9d5c7a389b; page prose cites the split PR heads.

Record and rebuild: exec/pr-diagram-pages-20261014/ (README.md, tools/build_pr_page.py + check_pages.py, spec/*.json, blocks/ = the 16 extracted diagram blocks, the two Workflow scripts). Rebuilt pages are byte-identical to the delivered ones.

Verification done: map workflow (4 mappers, 12 adversarial verifiers in 3 lenses, 4 revisers: 175 of 186 corrections applied), qa workflow (4 reader checks, 4 citation checks over every PR-head file:line, 4 fixers: 214 applied, 0 rejected), structural checks (figures verbatim, anchors, cross-page links, tag balance). No headless browser on claude-box, so no screenshot check.

Gap jhan may want: PR-2's AMX kernel qk_vnni_128x4 and the query packer have no base diagram in the sources (listed under "What the diagrams do not show").

**Why:** jhan wants the diagrams as the backbone of the talk with Ben; the pages tell which part of each diagram belongs to which PR.
**How to apply:** when jhan asks to change a page, edit spec/pr<n>-<number>.json in the record dir and rebuild with tools/build_pr_page.py, then run tools/check_pages.py; do not hand-edit the HTML. See [[pr1-split-execution]], [[pr2-split-execution]], [[pr3-split-execution]], [[pr4-split-execution]].
