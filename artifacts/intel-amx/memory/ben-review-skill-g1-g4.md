---
name: ben-review-skill-g1-g4
description: "2026-10-21: ~/.claude/skills/ben-review/SKILL.md gained the section 'Where a representation decision lives' with G1-G4 (one owner per representation decision, no raw storage views leave the owner, one control flow per function, the call site asks and takes the answer), abstracted from PR 5047's P1-P4; G3 is subordinate to G1 and needs a measurement on a hot loop (issue #5097)"
metadata:
  type: project
---

The four guidelines were drafted in chat from the "five lessons of PR 5047" section of random/Ben-stack-PR4957-4959.html, reviewed by jhan, and inserted before "Calibrate the recommendation". Order of checks: G1 count first (layout identifiers per non-owner file, target 0), then G2 accessors, G4 call sites, G3 loops. jhan's question that shaped G3: P3 (the loop split, commit e17a12ff09, 15:03 UTC Oct 20) came before P1 (commit ade89a9d9c, 16:18 UTC) and stands alone for readability, but P1's `score_k(.., live, ..)` signature exists only because of P3, and the +2.9 % kill-switch prefill cost (#5097) belongs to P3's split. So G3 serves G1 and is "should fix" without a measurement.

**How to apply:** run G1-G4 in every Ben-style review of a layout/encoding change. Related: [[ben-stack-reexpress-20261021]], [[issue-5097-killswitch-prefill]], [[pr5047-ben-refactor-review]].
