# Consistency review of the v2 Wade-code-review skill (2026-10-06)

Count line: 16 contradictions, 24 cross-reference errors, 8 duplicate-ownership gaps, 14 precedent-honesty gaps, 1 description finding (1018 chars, one artifact), 15 id-less claims about Wade, 13 broken or fragile commands out of 61 run.

Versions reviewed: SKILL.md md5 a885eb639f7962060a845505b6e2ec61 (879 lines, mtime 2026-10-06 12:56:47 PDT; it changed during the review, so SKILL.md findings are anchored by quoted text, written "S:"). references/procedures.md md5 61f6a371d959f20762d1102b74501563 (723 lines, "P:<line>") and references/wade-style.md md5 f8d99249347b2d3c54d8a3c6f135c857 (199 lines, "W:<line>") were unchanged since 12:55:06 PDT, so their line numbers hold.

Commands were run in the read-only worktree /home/jhan/workspace/ai-runs/tron-issue4525 on PR 4596 (HEAD 0f784c44ff, BASE 66c7bb8db1), git show/grep/log/diff/merge-base/merge-tree and gh api/pr view/pr checks only.

## 1. Contradictions

C1. S: check 3B "Severity and precedent: a question or approval condition, never a block" (cites 4265644124) versus S: "Four must-change signals: 'before merge' (3124878965), 'needs' (3002050036), 'Please <verb>' (5420005787), withheld approval" and W:86 which lists 4265644124 ("Approved, but please run at least a subset of representative UTs against these changes before merging") under "before merge or before merging" as a must-change. Fix: drop "never a block" from 3B, or remove 4265644124 from the must-change list.

C2. S: check 3A widening "Severity and precedent: no 'nit'; questions, non-blocking; (d) 'Coverage gap:'" versus W:42 and W:88, which list 3960538177 ("Please extend an existing CI suite ...") as a "Please <verb>" must-change. Fix: "non-blocking except (d), which uses the must-change form (3960538177)".

C3. S: check 33 "Severity and precedent: normal, non-blocking" versus its own finding shape "Please extend an existing CI suite" (3960538961), which W:88 classes as a must-change. Fix: same as C2.

C4. S: check 11 "Never raise above hygiene" versus its finding shape "Please squash into <one unit per body heading ...>" and S: "a must-change is a sentence ('before merging', 'needs', 'Please <verb>')". Fix: reword the finding shape without "Please", or drop "Never raise above hygiene".

C5. S: check 19 "attributed (4125818552, pasted assistant text)" versus S: "Nine of 269 texts disclose a paste ...: 3002297607, 4131374395, 3342904643, 4674512577, 3437517809, 4800935083, 5498556672, 5544513215, 3970590653" and W:121-131. 4125818552 is not among the nine. Corpus pr/tron-2438.md:45: review 4125818552 is a hand-written APPROVED body ("sorry @hvaneenoo-positron, been heads down in AoF land lately. I think what we are doing here is a bit pedantic ... Approved.") with no assistant mention. Fix: delete "attributed (4125818552, pasted assistant text)"; keep the "a bit pedantic" quote and say it is a review body on PR 2438.

C6. S: check 18 "attributed (3907214892)" versus S: "Attributed text: a block Wade pasted from an AI assistant (nine disclosed cases ...)" and W:147 "In PR 4128 the inline comments of 2026-09-01 and 2026-09-08 (3907183627, 3907185740, 3907214892, ...) carry no disclosure." Fix: "undisclosed register B (3907214892; the disclosure sits in 5498556672)".

C7. S: check 29 "n=6 comments over 3 PRs (2499, 2906, 4128), 2026-04-21 to 2026-09-08, attributed." The ids it cites are 3120788282 (PR 2499, hand-written), 3960506641 (PR 4128, undisclosed) and 5498556672 (disclosed). Fix: "attributed (5498556672 only)".

C8. S: "Check 35 covers the one process habit the record shows on 14 PRs" versus S: check 35 "n = 14 comments over 11 PRs". Fix: "14 comments over 11 PRs".

C9. S: "238 of them are review remarks" and "Where most of his comments land (144 of the 238 classified review comments)" versus S: "Row = classified item (239 rows)" and W:5, W:158 "239 rows". Fix: choose 238 or 239 and say what the extra row is.

C10. S: "The checks for the FPGA attention, DMA and scheduler code he reviews most (38 comments)" versus the n values of checks 26 to 32 (8, 8, 6, 6, 4, 6, 6), which sum to 44. Fix: "44 comments (38 after removing comments counted under two checks)" or correct one side.

C11. S: "144 of the 238 classified review comments" for checks 14 to 25 versus the n values (21, 19, 18, 14, 13, 10, 9, 8, 8, 8, 7, 6, 5), which sum to 146. Fix: as C10.

C12. S: "Ordered by how often Wade raised each concern" versus the list that follows, which is in check-number order (check 1, n = 3, precedes check 14, n = 21). Fix: "In check-number order; the sections below are ordered by frequency".

C13. S: "## The thirty-five questions", frontmatter "35 checks", P:1 "Procedures for the thirty-five checks" versus the list, which has 36 numbered questions (3A and 3B). Fix: "thirty-six questions (35 numbers; check 3 is split into 3A and 3B)".

C14. S: check 17 step 2 "A token that is absent at HEAD but has a sibling with the same stem is a finding" versus check 17 do-not-fire "no-symbol tokens (check 15)". A token absent at HEAD is a no-symbol token. Fix: "a token absent at HEAD with no same-stem sibling (check 15)".

C15. S: check 20 step 3 "Report a finding when one spelling has ten times the hits of the other" versus check 20 do-not-fire "tokens with ten or more BASE hits". A short spelling with 12 hits against 200 fires by step 3 and is excluded by the clause. Fix: keep one rule.

C16. S: check 10 "Clear a candidate only if: the PR's functional change rewrites the same statement ...; a GitHub review thread of this PR asked for it ...; or a body sentence describes the hunk's added content" and S: check 25 "A commit message alone never clears this check" versus P:681 check 10 widening step 7 "Clear: rename map; thread id; body or subject naming the item" (a commit subject clears). Fix: remove "or subject" from P:681.

BASE definition differences (one subject, five recipes):
- S: Words used here "BASE: the merge base of HEAD and the PR's target branch (`gh pr view N --json baseRefName`)"; S: check 22 "BASE from `gh pr view N --json baseRefOid`"; S: 3A widening "BASE = merge-base(HEAD, PR base.sha)"; S: check 8 "BASE = merge-base of HEAD and the PR's baseRefOid".
- Merged-PR fallback in procedures.md: (i) `.base.sha` at P:22, P:40, P:71, P:350, P:428, P:457, P:487, P:631; (ii) merge-commit first parent at P:56, P:85, P:520, P:561, P:673; (iii) parent of the PR's first commit at P:226 (`$(gh pr view N --json commits -q '.commits[0].oid')^`), P:303, P:374 (`.[0].parents[0].sha`), P:503; (iv) second parent of the last merge on HEAD's first-parent line at P:191.
- P:148 "Never `<commit>~1`" while P:226, P:303, P:374, P:503 use `<first commit>^`, which is the same commit. Recipe (iii) returns the original fork point when the branch later merged main, so BASE..HEAD then contains main's commits.
- P:10 comment "for a merged PR merge-base returns HEAD" is wrong for BASEOID. Verified: `git merge-base 0f784c44ff 9b60b69dce` = 66c7bb8db1; only `git merge-base 0f784c44ff origin/main` returns HEAD.
- P:631 "0 merges in BASE..HEAD" is a PR 4596 observation written as a definition; PR 4557 had 2 merges (P:694 "21 commits (2 merges, 19 without)").
- Fix: one recipe in "Common setup" (merge-base of HEAD and baseRefOid; verified on PR 4596 to give 66c7bb8db1, the same as the parents[0] fallback there), and every check section refers to it.

Tension (not a strict contradiction): S: check 12 "Do not make every low-level change require new approval, and do not contact reviewers" versus S: "He defers to the area owner (3277240111). Get that owner's written answer." Fix: qualify "during the review" and "when replying".

## 2. Cross-reference errors

Procedures headings with the wrong number (headings are the "## Check N" lines):
- P:38 "## Check 14: spelling, wrong names and over-wide lines in added prose" -> Check 15.
- P:161 "## Check 14: explanation at the declaration" -> Check 21.
- P:189 "## Check 14: disabled code left in the tree" -> Check 23.
- P:224 "## Check 14: declaration, constant, include or growing function out of place" -> Check 24.
- P:331 "## Check 14: buffer lifetime and alignment follow the consumer" -> Check 29.
- P:440-451 repeat P:410-421 verbatim ("## Check 3: a layout-formula check must execute on the lane that gates the PR", both followed by "Widening (2026-10-06):"). Fix: delete P:440-453 and place "## Check 3B" directly after 3A, or rename the first copy "## Check 3 (2026-10-05 text)".
- P:40 "Scripts: references/check14/." and S: check 15 "prose.py (references/check14/)" name a directory that exists neither in out/references/ (procedures.md, wade-style.md only) nor in the installed skill (procedures.md, pr4557-misses.md). Fix: references/check15/ and ship prose.py, spell.py, step5.py, width.py.
- S: "The corpus boundary and the method are in [references/wade-corpus.md]" and "[references/pr4557-misses.md]": neither file is in out/references/.

Stale "check 3" (check 3 no longer exists; 3A and 3B do):
- S: check 4 "units under different build or hardware gates (then the finding is check 3)" -> 3A.
- S: check 4 widening "different inputs, calls or gates (check 3)" -> 3A.
- S: check 33 "fake paths (check 3)" -> 3A.

Wrong number:
- S: check 6 do-not-fire "CI (7); duplicates (13)": check 13 is numbers and constants; a twice-stated default belongs to check 22 (redundant) or 18 (duplicate logic). State which.

Lettered sub-items that the named check does not have:
- S: check 27 "count-constant failure value (check 13, E)": check 13's trigger is unlettered.
- S: check 27 "wait primitive (check 18, b)": check 18's trigger is unlettered.
- S: check 27 "stale-count exit (check 26, b)": check 26's trigger is unlettered.
- S: check 27 "test-only helper parameter (check 21, d)": check 21's trigger is unlettered.
- S: check 30 "second container walks (check 18 (h), 4029533521)": no (h) in check 18.
- S: check 32 "-detail promotions (check 16 (e))": check 16's trigger has four unlettered items.
- S: check 6 "stale messages (check 13 (C), 3350031805)": unlettered.
- S: check 10 widening "a one-line swap's behavior (check 25 (a))": check 25's trigger is unlettered.
- S: check 34 "The id goes on a TODO line, not in a Note (rule B1 of check 9, the code-comment part)": check 9 has no rule B1.
- Fix: letter the triggers of 13, 16, 18, 21, 25, 26 (a), (b), ... as 27, 31 and 33 already are, or drop the letters.

Mentions by label instead of number:
- S: check 22 "atomic or lock-free getters (concurrency check)" -> check 28.
- S: check 26 "token-index waits (concurrency)" -> check 28.
- S: check 29 "wait sets, readiness predicates (siblings)" -> checks 26 and 28.
- S: check 23 "check 10 only decides placement": "placement" is check 24's subject. Fix: "check 10 only decides whether the hunk belongs".

Description artifact: S: frontmatter "buffer lifetime, check 30 cost, instrumentation ownership" (a search-and-replace hit on "hot-path"). Fix: "hot-path cost".

## 3. Duplicate ownership (two checks fire on one hunk, no do-not-fire pointer either way)

D1. `[0]` / `.front()` reads. Check 26 trigger "a `get_device(0)` wait after a per-device loop, or a literal `[0]` device choice" (P:289 greps `\[0\]|\.front\(\)`) and check 6 trigger "(c) a [0]-read container's count" (P:566 greps `(\[0\]|\.front\(\))` on the same diff). Fix: 6 owns the sentence, 26 owns the code line; say so in both do-not-fire lists.

D2. Before/after figure. Check 30 "Before/after capture: a question, only when memory is traded for repeated work (4607543703)" and check 32 trigger "a perfetto::Category, TRACE_COUNTER ... or memory-for-work trade with no posted image, repository path or before/after figure" both own 4607543703, and S: "What he rarely comments on ... Add no findings on these items. Benchmark or measurement: 1 of 269 (4607543703, a wish for before/after metrics)". Fix: one owner or none.

D3. Over-wide Markdown line. Check 15 step 4 "width.py: a .md line over 1.25 times the width ..." and finding shape "a formatter question (3778051701)" versus S: "Add no findings on these items. Formatting: 1 of 269 (3778051701, a long Markdown line, as a question)".

D4. Dead loop scope. Check 22 trigger "bare block from a removed loop" (cites 2976643305) versus S: "Brace or indent: 1 of 269 (2976643305, a dead loop scope)" under "Add no findings".

D5. Workflow label casing. Check 20 trigger "miscases a repository label" (3580238651; P:149 diffs `.github/workflows`) versus S: "CI workflow YAML: 1 of 243 inline comments (3580238651)" under "Add no findings".

D6. Stale message after a constant change. Check 13 trigger "a stale message after a constant change" and check 25 trigger "changed threshold constant" fire on the same hunk; 25 defers "bare literal or stale message (check 13)" but 13 has no clause for the behavior half. Fix: add "the changed value's behavior (check 25)" to check 13.

D7. Non-const UPPER_CASE literal global. Check 19 trigger "(c) a non-const UPPER_CASE literal global" and check 13 trigger "an underived sizing constant"; neither points at the other (only check 20 points at both). Fix: check 13 do-not-fire "constness and initialization (check 19)".

D8. Absent comment token with a same-stem sibling: check 17 step 2 and check 15 step 3 ("a comment token that occurs once in the whole tree and is one letter edit away from a code identifier"); see C14.

## 4. Precedent honesty

Missing "Severity and precedent" paragraph: check 2 (ends at its finding shape "Keep the probes and drop the rest."), check 7 (ends at its finding shape "The setting entered it in <commit> via PR #<n>.").

Nonstandard form: check 11 "Precedent: one squash request in 334 reviews (5420005787) and two rebase asks" (no "n = k comments over m PRs"); check 12 "Precedent: n = 1 (4188336279)" (no PR count).

Severity paragraphs quoting fewer than two ids:
- 13: "nit (`non-blocking nit`, 6021333114). A design question for a sizing constant." (one id)
- 16: "The strongest form is 'can we comment this back out before merge?' (3124878965)." (one)
- 21: "nit or minor, never blocking. n = 8 comments over 6 PRs" (zero)
- 23: "none; one nit per file, never blocking. n = 7 comments over 5 PRs" (zero)
- 24: "nit ('just a nit' 3405003751)" (one)
- 25: "never blocking ('was this intentional?', 3463061252)" (one)
- 28: "normal. n = 6 comments over 5 PRs" (zero)
- 33: "normal, non-blocking. n = 4 comments over 4 PRs ...; 3960538961 attribution Insufficient data" (one)
- 8: "ask or approval clause, never blocking; n = 5 comments over 5 PRs" (one id in the finding shape, 5371062950)
- 3A widening: only 3960538177 (in the finding shape)
- 11: 5420005787 only; 12: 4188336279 only (n = 1, so unavoidable; say so).

All other checks give n and PR count (32 "n = k comments over m PRs" lines found).

## 5. Frontmatter description

1018 characters (limit 1024). It names the four families (code checks, test checks, claim checks, scope checks) and the main new checks (dead symbols, debug switches, comments contradicting code, magic literals, duplicated logic, types, names, silent fallbacks, wait sets, locks, buffer lifetime, instrumentation; skipped tests, duplicate coverage, test names, bypassed paths, workarounds; bot findings). It contains the artifact "check 30 cost" (see section 2). It does not mention the 3A/3B split.

## 6. Claims about Wade with no id or count

- S: "he asks one question of every added line: who consumes it, what guards it, and does the text beside it say what the code does."
- S: "He can name the right concern and still propose a remedy that removes protection."
- S: check 16 "He approves once answered."
- S: check 17 "One comment per stem, then approval."
- S: check 18 "copies kept at approval."
- S: check 19 "nit ('a bit pedantic', 4125818552), approved." ("approved" without the approval id)
- S: check 21 "nit or minor, never blocking."
- S: check 23 "none; one nit per file, never blocking."
- S: check 27 "normal (hidden wrong value), minor (spin, message), question (possibly defensive)."
- S: check 28 "normal."
- S: check 33 "normal, non-blocking."
- S: check 11 "Wade approved PR 4596 on 2026-09-30 at 26 non-merge commits without a squash request." (5371062950 is the id)
- W:161 "He never hand-formats a hunk."
- W:166 "He does not review runner tables, job matrices or caching."
- W:168 "No structure, formatting or completeness review of prose."

## 7. Commands in procedures.md that cannot work as written

61 commands run on PR 4596 in the read-only worktree. Broken or fragile:

B1. P:15 `for f in $(grep '^t/' prfiles.txt); do git -C WT show $HEAD:$f > full/$f; done` fails: "full/t/CMakeLists.txt: No such file or directory". Fix: `mkdir -p full/$(dirname $f)` inside the loop.

B2. P:276 `python3 -I - < pr-u0.diff <<'EOF'` prints nothing: the heredoc replaces the file on stdin, so the script sees EOF. Fix: save the script to a file and run `python3 -I script.py pr-u0.diff` with `open(sys.argv[1])`, or `python3 -I /dev/stdin pr-u0.diff <<'EOF'` with the same change.

B3. P:88 `step1-new.txt` is never created (step 1 writes step1.txt and step1-md.txt). Fix: name the file step 1 produces.

B4. P:88 `sed -n 'L,L+90p'` fails: "sed: -e expression #1, char 8: unknown command: `+'". Fix: `sed -n 'L,+90p'`.

B5. P:89 `sed -n 'L-15,Lp'` fails the same way. Fix: `sed -n "$((L-15)),${L}p"`.

B6. P:642 `sed -n 'L+2,ENDp'` fails the same way. Fix: `sed -n "$((L+2)),${END}p"`.

B7. P:603 `BASE=$(git -C WT merge-base $HEAD $BASEOID)` follows `read BASEREF BASEOID HEADOID < <(...)` at P:602: $HEAD is unset there (the read sets HEADOID). Fix: use $HEADOID or state that the common setup must run first.

B8. P:609 and P:610 `--since=LAST`: LAST is never defined. Fix: `LAST=$(gh pr view N --repo positron-ai/tron --json lastEditedAt -q .lastEditedAt)`.

B9. P:612 `origin/S`: S (the source branch of the ported file) is never defined. Fix: define S from the body's "ported from" sentence.

B10. P:191 `git -C WT log --first-parent --merges -1 --format=%P HEAD | cut -d" " -f2`: on a branch that never merged main, the nearest merge on the first-parent line lies before the fork point and its second parent is a foreign feature-branch tip. Fix: use the common-setup BASE.

B11. P:705 and S: check 12 "A comment counts only if its `commit_id` contains the introducing commit (`git merge-base --is-ancestor`)": GitHub rewrites commit_id to the latest head for comments that are not outdated. Verified: Wade's 2026-09-28T17:16 inline comments on PR 4596 carry commit_id 8c95514924 (the merge head), while his review submitted the same minute carries commit 1430736b2a. The ancestor test is therefore trivially true. Fix: use `.original_commit_id`.

B12. P:231 check 24 step 4 flags `assertion_signal.hpp` (a header the PR creates under t/) as "third-party quoted" because it tests only `h/$p` and `*.in`. Fix: also test `git -C WT cat-file -e HEAD:t/$p` and prfiles.txt.

B13. P:716 check 35 step 2 jq `(.body | split("<!-- DESCRIPTION START -->")[1] | split("<!-- DESCRIPTION END -->")[0] ...)` raises when a bot body lacks the marker (jq cannot split null). It worked on 4596 because every bot comment had it. Fix: add `select(.body|test("DESCRIPTION START"))`.

Minor:
- P:24 the constants regex yields the name "char" for `constexpr const char X[]` (it reads `const` as the type). Fix: `(const\s+)?` after `constexpr\s+`.
- P:8 `gh pr view N --json headRefOid` lacks `--repo` while P:9 has it; works only inside a tron checkout.
- P:435 and P:458 `commits/HEAD/check-runs`: a literal HEAD resolves on GitHub to the default-branch tip; the sha must be substituted (placeholder, acceptable).
- P:401, P:473, P:575 and other check 1-13 commands omit `-C WT` (they assume cwd = WT); the newer sections use `git -C WT`. Harmless, inconsistent.

Verified working (48): common setup (headRefOid, baseRefOid, merge-base, body, log, diff, name-only); check 14 steps 1, 2, 9; check 13 steps 1, 8; check 16 steps 2, 4; check 17 steps 1, 5; check 18 step 1; check 19 step 1; check 20 step 2 (line numbers verified against HEAD); check 22 steps 1-2; check 23 steps 1-4 (mawk 1.3.4 on this host accepts `\s`); check 24 step 2; check 25 step1.py ("kept 3"); check 27 `D` variable; check 28 steps 2, 5; check 30 step 1; check 31 step 0 loop (2.5 s, returns 66c7bb8db1); check 32 steps 4, 5 (`grep -P`); check 1 step 9; check 3A steps 9, 10, 11, 15; check 3B steps 2, 3, 5, 7, 8, 9; check 4 steps 4, 7; check 5 step 5 and its BASE fallback (parents[0] = 66c7bb8db1 here); check 33 step 2; check 34 steps 2, 3; check 6 widening step 4 graphql (7 body edits); check 7 steps 2, 4 (`gh pr checks N --json name,workflow,state,bucket` and `--required` both work on gh 2.97.0), 5; check 8 widening steps 7 (merge-tree, 1 marker, matches P:615) and 9; check 9 widening steps 6 (reproduces attn_stats.hpp:863-864 and t_attn_stats.cpp:306 as P:651 records), 7, 8; check 10 widening steps 3, 4, 6; check 11 step 1 (25 commits, 0 merges); check 12 steps 1, 4, 5, 6, 7; check 35 steps 1 (10 threads), 2.
