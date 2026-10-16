---
name: pr-description-skill
description: "2026-10-13 jhan's user skill ~/.claude/skills/PR-description (sections Short version, Background, Words used here, How to review this PR, Verification, Open items, The stack); whole body under 2,000 words (wc -w, set 2026-10-13); the review section answers 'What is the best case against merging?' with two Q-and-A lists; output checked by the plain-english skill"
metadata:
  type: project
---

State on 2026-10-13 ~19:30 UTC. jhan's end goal: a guideline for PR descriptions, starting from the
length review of PR 4868 (split-4424/PR1-4868/PR-desc-review.html). Decisions jhan made:

- "How to review this PR" replaces the by-file "The changes" section. jhan called the file list "noise".
- Rule chosen: version 8 of PR1-4868/review-guide-rule-versions.md (risk list + decisions list, at most
  three items each) under the version-7 question "What is the best case against merging?". Q-and-A format:
  each item is a bold question followed by its answer, with "Verification:" (jhan renamed it from "Pinned by:" on 2026-10-14, "weird phrase") or "Open." and who decides.
- The prose is processed by the plain-english skill (Write mode while writing, Check mode before posting).
- Sections so far: Short version (jhan's own goal line: a reader with no prior experience of the code base
  can understand what the PR is about), Background, Words used here (project terms used in more than one
  section only), How to review this PR. No word limits: jhan removed every budget on 2026-10-13 and will set
  limits later. Duplicates are removed always (an "After writing" step and a checklist item), not only when
  over budget.
- Files: ~/.claude/skills/PR-description/SKILL.md, references/example-how-to-review.md (PR 4868 worked
  example, 497 words), evals/evals.json (three draft test prompts, not run). Draft source:
  split-4424/PR1-4868/the-changes-as-review-guide.md (490 words, jhan liked its Q-and-A form).

**Why:** jhan is building the guideline section by section and wants later sessions to extend the same skill
rather than start another.
**How to apply:** when jhan adds sections (Measurements, Verification, Open items, The stack are the
candidates), extend SKILL.md under "Sections 5 and up" and keep the rules list and the self-check in step.
Related: [[pr1-split-execution]], [[vnni-packed-wording]].

UPDATE 2026-10-13 ~20:10 UTC: section 5 "Verification" added (jhan's spec): it answers "does the head build and
pass in every configuration, and are the tokens identical where they must be?" and, when the PR's goal is a
performance improvement (or the head costs performance), "how much does the PR improve performance, and why?".
Shape: one provenance paragraph, then subsections Builds and tests, Token identity, Performance (with the
decision rule and the mechanism), CI coverage. Measurements is not a separate section any more. Placeholder is
now "Sections 6 and up" (open items, the stack are the candidates). Self-check gained two items for section 5.

UPDATE 2026-10-13 ~21:3x UTC, jhan's edits to the skill: no word budgets ("I will decide the word limit later"); duplicates
removed always (After-writing step 3 + checklist item); Short version spec is jhan's goal line; section 6 = Open items,
section 7 = The stack (only when a big PR is split); CI coverage is optional (only when required CI misses the PR's paths);
the word "provenance" replaced everywhere by "where the results come from" (jhan: "I do not know what provenance mean").
First use of the skill: PR 4868 body v3 (4,096 words). Avoid "provenance" in anything written for jhan.

UPDATE 2026-10-13 ~23:30 UTC (jhan: "add budget, PR description needs to less than 2000 words"): the budget is
the whole body, tables included, under 2,000 words counted with `wc -w` on the posted file. Added in four places:
the skill's opening summary, a rule (with the calibration: last 60 merged tron bodies, median 300, longest 1,215
words), After-writing step 4 (count, then cut Verification tables, Open items numbers, Words meanings, in that
order, never section 4 or the token-identity rows), and a self-check item. No per-section budgets. Also fixed my
stale pointer "[Measurements]" to "[Verification]" in the rules. The live PR 4868 body (4,096 words) is over the
new limit. jhan has not asked to cut it.

UPDATE 2026-10-13 ~23:50 UTC (jhan): the "Words used here" section is EXCLUDED from the 2,000-word budget. Count with
`awk '/^## Words used here/{skip=1; next} /^## /{skip=0} !skip' body.md | wc -w`. The skill's rule, step 4, the section-3
text and the self-check say so. jhan also asked to apply the skill to all four stack PRs (4868 first, then 4887, 4898, 4901).


UPDATE 2026-10-14 00:40 UTC: the skill was applied to PRs 4898, 4887 and 4901 (posted; 4868 left to jhan). Lessons recorded in
the bodies' checks: a term in the Words table costs nothing, but parking facts there is a fault the checkers flag; markdown
table pipes count as words; section 4 runs about 550 to 600 words; a 10,000-word body lands at about 1,990 counted words only
after cutting per-binary tables (name the result record), inherited open items, and cross-head comparisons.

UPDATE 2026-10-14 ~01:45 UTC (jhan's reasons for his 4868 edits, file PR1-4868/user-edits-20261014.txt, abstracted and
approved): write "PR" never "pull request"; the Short version carries no section pointers; standard field terms (row-major,
cache line) stay out of the Words table and a row leaves with the last use of its term; section 4 = at most three bold risk
questions, each with bullets per file to read, per claim, and a last "Verification:" bullet (or "Open." + decider); NO best-case
sentence, NO sub-headings, NO decision list (choices reviewers must make go to Open items with "Reviewers decide.", else out);
an open item tracked by an issue is one sentence naming the issue; inherited items and items nobody must act on stay out; no
"why this shape" paragraph. The worked example references/example-how-to-review.md is jhan's bulleted section 4 of 4868.
jhan judged the leftover fragment and the orphaned kv_mul row in 4868 fine: do not touch them. The 4887/4898/4901 bodies
were posted under the previous section-4 shape (best-case sentence, two lists) and were not re-posted.

UPDATE 2026-10-14 01:59 UTC: the three stack bodies 4887/4898/4901 were reshaped to the updated skill and re-posted
(pr-body-v4.md in exec/pr2-20261011, pr3-20261012, pr4-20261012; counted 1,700 / 1,741 / 1,933). Record in split-status.md
"PRs 4887, 4898, 4901 reshaped". 4868 untouched (jhan's).

UPDATE 2026-10-14 20:55 UTC: jhan removed the Words row "temperature 0, `--pay-for-determinism`" that I had added to 4887 (his edit of
19:09 UTC, with rows for AMX/AVX-512/FPGA, required CI/preset/tp2, TPS/TTFT/decode/prefill), so the same row was removed from 4898
and never added to 4901. Lesson: do not add Words rows for run flags or field-standard terms; jhan trims the Words table by hand in
every body (4868, 4887, 4898, 4901). His standing cut shape for token identity: setup line, the must-match rule, "Issue #4444 tracks
every difference."; kill-switch open item = "Issue #4444 is tracking the token identity issue."
