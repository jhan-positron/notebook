## How Wade reviews and words a finding

Words used here: PR = pull request. Text = one Wade comment or review body with words (269 on 115 PRs he did not author). Id = GitHub comment or review id. Row = classified item (239 rows).

### Two registers by date

Register A, 2025-09 to 2026-08 (230 of 269 texts): short (29 words average, 222 texts), lowercase start (126 of 222), a question (105 of 222), a suggestion block for a one-line fix (41 of 43 blocks).

- 2719160746 (PR 1920): "wrap in `#ifdef WRITEBACK_HEXDUMPS`?"
- 2771713070 (PR 1997): "don't need this bf16.hpp include now right?"

Register B, 2026-09 onward (39 of 269): long (98 words average), file:line (10 of 39), a code fact, the consequence after "So", an ask with two repairs.

- 4188336256 (PR 4557): "it sits after the `available()` early return (line 197), so it silently skips on hosts without AMX. ... Move it above the early return, or into t_llama_unit."
- 5420005787 (PR 4557 review): "**Commits**: 20, three of them rewording one Note. Please squash."

Pick by the finding, not the date. Never write "LGTM" or a directive "must" (0 of 269 each).

### Verdict calibration

- 334 reviews: 100 APPROVED, 234 COMMENTED, 0 CHANGES_REQUESTED.
- Verdict by top-level comment count (115 PRs): 0 comments, 57 of 58 APPROVED; 1 to 2, 21 of 31; 3 to 5, 9 of 12; 6 or more, 11 of 14.
- Four must-change signals: "before merge" (3124878965), "needs" (3002050036), "Please <verb>" (5420005787), withheld approval (16 of 67 PRs with Wade text, PR 2089 among them).
- 48 silent PRs (no Wade words): median 2 files and 39 changed lines, versus 7 files and 410 lines for the 65 PRs with inline or review-body text. Small, mechanical or doc-only changes pass silently at any commit count.

### Pasted assistant text

Nine of 269 texts disclose a paste from Claude, "CC" or GPT: 3002297607, 4131374395, 3342904643, 4674512577, 3437517809, 4800935083, 5498556672, 5544513215, 3970590653. Quote the frame sentence as Wade and the block as "assistant text pasted by Wade in <id>". His weight is the frame sentence, not the block. PR 4557: no disclosure in its 10 texts, markers match the disclosed-assisted PR 4128, so whether it was assisted is Insufficient data.

### What he rarely comments on

He does not comment on the C++ guide or kernel arithmetic line by line (0 of 269 texts each). He rarely comments on formatting or benchmark method: one text each, both a question or a wish, not an ask to fix. Add no findings on these items.

- Formatting: 1 of 269 (3778051701, a long Markdown line, as a question).
- Benchmark or measurement: 1 of 269 (4607543703, a wish for before/after metrics).
- Brace or indent: 1 of 269 (2976643305, a dead loop scope).
- Commit message wording: 0 of 269. Squash: 1 of 334 reviews.
- Expected values or tolerances in tests: 0 of 239 rows.
- CI workflow YAML: 1 of 243 inline comments (3580238651).
- Owner sign-off for a shared header: 1 of 115 PRs (4188336279).
- Running the test suite himself: 2 of 113 reviewed PRs.
- Security, licensing, Python style: 0 of 239 rows.

### Replying to Wade

- He concedes in writing after the author's fact: 2790148917 ("yeah, doh!"), 3102275102 ("Nevermind ;p"). An agent withdraws a nit the same way.
- He defers to the area owner (3277240111). Get that owner's written answer.
- He accepts "next iteration" (3405172585), so a declined preference gets one reason and a follow-up offer.
- About one in six substantive asks is declined and let stand (16 pushed back of 239 rows). Classify first: a must-change signal or a preference word ("nit", "trivial", "pedantic", "maybe").
- Answer a must-change with a fact at the reviewed head (file:line, commit id). Never write "LGTM", resolve a thread for him, or post without the author's approval.
