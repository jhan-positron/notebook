# Wade's review style: full reference

Short version: Wade (GitHub login Wado-posi) writes in two registers, a short hand-written question through 2026-08 and a long file:line finding from 2026-09 onward, and he never uses CHANGES_REQUESTED (0 of 334 reviews). A must-change is carried by the words "before merge", "needs", "Please <verb>" or by withheld approval. Nine of his 269 texts are disclosed pastes from an AI assistant and are quoted as attributed material, not as his words.

Words used here: PR = pull request. Corpus = the 115 PRs Wade reviewed and did not author (corpus.json plus pr/*.md under exec/wade-20261006/corpus/). Text = one Wade inline comment, review body with words, or conversation comment (269 texts: 243 inline, 11 conversation, 15 review bodies). Id = the GitHub comment or review id. Counts come from style-stats.json, merged-taxonomy.json and codex-factcheck.md; "recount" marks a count made for this document. Corrections against codex-factcheck.md are marked in place with the claim number.

## How Wade words a finding

Words used here: PR = pull request. Text = one Wade comment, review body or conversation comment in the corpus (269 texts on 115 PRs he did not author: 243 inline, 11 conversation, 15 review bodies with words). Top-level text = a text that is not a reply (232 of 269). Id = the GitHub comment or review id. Counts come from style-stats.json (computed by style_stats.py over corpus.json) unless marked "recount".

Two registers exist, split by date. Match the register to the date and the length of the finding.

### Register A: hand-written, 2025-09 to 2026-08 (230 of 269 texts)

- Short: average 29 words per text (2026-01 to 2026-08, 222 texts; recount). Median top-level text is 132 characters and 2 sentences (232 top-level texts). The 90th percentile is 548 characters.
- Lowercase start: 126 of 222 texts in 2026-01 to 2026-08 start with a lowercase letter (recount). 136 of 269 overall.
- Question form: 105 of 222 texts contain a question mark (recount). Over all top-level texts, 115 of 232 contain one and 82 of 232 end with one.
- He states his reading and asks for confirmation. 18 of 269 texts end a claim with "right?" (17 of them before 2026-09). 8 of 269 ask whether something was "intentional". 4 of 269 open with "I assume".
- Suggestion blocks for any one-line fix: 43 of 232 top-level texts carry a ```suggestion block. 41 of those 43 are before 2026-09. 0 of the 39 texts from 2026-09 onward carry one.
- Repeats are linked, not re-explained: "same here", "ditto" or "same comment as <link>" in 6 of 269 texts (2789796269, 2915281835, 3102603313, 3405974281, 3778058064, 2897211589). "and this?" twice (2737956124, 2737956568).
- Hedges over the 232 top-level texts: "should" 32, "would" 31, "maybe" 15, "seems" 16, "could" 11, "I think" 8, "IMO" 7. "please" only 6.
- Severity words, 232 top-level texts: "nit" 13, "trivial" 3, "minor" 3, "follow-up" 3, "non-blocking" 1. "LGTM" 0. "squash" 1.
- Humor markers ("lol", ";p", ":)") in 18 of 232 top-level texts. Ellipses "..." in 96 of 269 texts (recount).
- File:line citations: 1 of 222 texts in 2026-01 to 2026-08 (recount with a narrow pattern; codex-factcheck.md claim 7 counts 3 of 222 with a wider pattern).

Verbatim examples, register A:

- 2719160746 (PR 1920, 2026-01-23): "wrap in `#ifdef WRITEBACK_HEXDUMPS`?"
- 2771713070 (PR 1997, 2026-02-06): "don't need this bf16.hpp include now right?"
- 2737826254 (PR 1920, 2026-01-28): "do we need these in both the header and the impl file? This cpp file already includes `device.hpp` where they're also declared"
- 3307459854 (PR 2766, 2026-05-26): "was this intentional? If so, should probably note what's special about `1000` or define some meaningful variable for it. Or maybe use `timeout_ns / 10` instead with a note."
- 3029339639 (PR 2287, 2026-04-02), a suggestion block `auto dev = devs[0];` followed by: "... but is index 0 always the correct thing to use? What if we're doing TP2 or TP4?"
- 2915281835 (PR 2148, 2026-03-11): "same here"
- 3227529208 (PR 2713, 2026-05-12): "the spec says a pool can have \"one or more chunks\"... but we only ever look at `chunks[0]` here and below in heap_size. So is the spec wrong? Or are these functions insufficient?"

### Register B: 2026-09 onward, and in every assisted review (39 of 269 texts)

- Long: average 98 words per text (39 texts; recount). The six texts over 1500 characters are all in this group.
- File:line citations in 10 of 39 texts (codex-factcheck.md claim 7; recount with a narrower pattern gives 9). Forms used: `file.yml:355`, `(line 197)`, a commit id, a PR number, a repository policy by name ("AGENTS.md treats NaN as corruption").
- Order inside a finding: a declarative fact about the code, then the consequence introduced by "So", then the ask. The sentence-opening "So" appears in 16 of 269 texts (case-sensitive recount; the taxonomy counts 45 with a case-insensitive match).
- The ask offers two repairs or two alternatives: change the code, or narrow the text; key by A, or record B.
- "Please <verb>" as a directive: 3 of 269 texts, all in this register (3960538177, 3960538961, 5420005787).
- Question marks in 12 of 39 texts. Lowercase start in 8 of 39. "right?" 0 of 39. Humor markers 3 of 39 (one is the 2026-10-06 reply 6021333114, which returns to register A: "Fair enough", ";-p").
- Severity is still stated in words: "Nit:", "Fine as a first step", "Coverage gap:", "non-blocking nit".

Verbatim examples, register B:

- 4188336267 (PR 4557, 2026-10-05): "`native_k_view` is an alias of the generic row-major `view`, and t_llama_unit asserts it is constructible from `const bf16*`. So any pointer or row-major 64x128 bf16 view passes the QK kernel; \"a bare pointer is a compile error\" holds for V only. Fine as a first step, but please say so in the description and give K a distinct type in #4424."
- 4188336256 (PR 4557, 2026-10-05): "This is the only check of the packed layout against an independent formula, but it sits after the `available()` early return (line 197), so it silently skips on hosts without AMX. The `at()` section in t_llama_unit doesn't cover it: `at()` and `append_v_row` share `pair_base`, so a wrong formula passes both. Move it above the early return, or into t_llama_unit."
- 4188336324 (PR 4557, 2026-10-05): "Nit: the section is still named \"append_v preserves poison\", but it now asserts that the poison is zeroed."
- 4125033686 (PR 4596, 2026-09-28), opening and ask: "Design question on row sizing. Rows and `path_bits` are sized by `attn.size()`, the whole app pool (27 in your run), but rows are indexed by *attention* worker index (0..`n_attn_workers`), 20 in your run. So:" ... "Was keying by attention worker index (instead of pool worker index) deliberate? Keying by pool worker index would make per-worker rows stable per thread/core, and the fold could skip workers with no bits set in the forward."
- 5420005787 (PR 4557 review, 2026-10-05): "**Commits**: 20, three of them rewording one Note. Please squash."

### Rules for an agent writing in his name

- Pick the register by the finding, not by the date alone. A one-line fix gets a suggestion block and a short question (register A). A finding that needs a fact, a consequence and two repairs gets register B with file:line.
- Backticked identifiers, with the location in the same clause.
- Every drop request names what to keep. Every text-versus-code mismatch offers both repairs.
- A design concern is a question with two alternatives ("deliberate, or key by ..."), not an order.
- Never write "LGTM" (0 of 269 texts). Never write "must" as a directive (0 of 269; codex-factcheck.md claim 6).

## Verdict calibration

Words used here: PR = pull request. Review = one GitHub review event with a state (APPROVED, COMMENTED or CHANGES_REQUESTED). Silent PR = a PR where Wade left no words at all. Top-level comment = an inline comment that is not a reply, a conversation comment, or a non-APPROVED review body with words. Counts are from style-stats.json over 115 PRs and 334 reviews unless marked "recount".

### Review states

- 334 reviews: 100 APPROVED (30 percent), 234 COMMENTED (70 percent), 0 CHANGES_REQUESTED.
- 113 of 115 PRs have at least one review. Reviews per PR: 1 review on 59 PRs, 2 on 21, 3 to 5 on 17, 6 or more on 16 (maximum 23 on one PR).
- 0 of the 100 APPROVED reviews carry an inline comment. Inline comments go under a COMMENTED review. The approval is a separate, later review.
- 12 of 100 APPROVED reviews carry words. 4 of those 12 are 40 characters or shorter ("looks good to me", "nice catch...", "Looks sensible to me!").

### Final verdict by number of top-level comments (115 PRs)

- 0 comments: 57 APPROVED, 1 COMMENTED (58 PRs).
- 1 to 2 comments: 21 APPROVED, 8 COMMENTED, 2 with no review (31 PRs).
- 3 to 5 comments: 9 APPROVED, 3 COMMENTED (12 PRs).
- 6 or more comments: 11 APPROVED, 3 COMMENTED (14 PRs).

Reading: comment count does not predict the verdict. 11 of the 14 PRs with 6 or more comments ended APPROVED.

### How a must-change is signalled

He never uses CHANGES_REQUESTED. A must-change is carried by words, in four forms (ids and counts over 269 texts, from codex-factcheck.md claim 6 and a recount):

- "before merge" or "before merging": 2 texts by Wade. 3124878965 (PR 2499, 2026-04-22): "can we comment this back out before merge?". 4265644124 (PR 2698 review, 2026-05-11): "Approved, but please run at least a subset of representative UTs against these changes before merging." (A third hit, 5544513215, is pasted assistant text.)
- "needs": 4 texts. 3002050036 (PR 2233, 2026-03-27): "looks like this still needs fixed". 2897190682 (PR 2089, 2026-03-06): "the pre_attn scalar needs to come from the model... 1.0f is not the correct value, currently". 4373886636 (PR 2766 review, 2026-05-27): "Also needs rebased."
- "Please <verb>": 3 texts, all 2026-09 onward. 5420005787 (PR 4557 review, 2026-10-05): "please split them out", "Please squash", "Please re-run them or mark them as pre-merge". 3960538177 and 3960538961 (PR 4128, 2026-09-08): "Please extend an existing CI suite ...".
- Withheld approval: 16 of the 67 PRs with Wade text have no APPROVED review from him: tron 1485, 1860, 2089, 2233, 2287, 2426, 2674, 2695, 2777, 2872, 3016, 3738, 4128, 4258, 3879, 2898.
- "must" as a directive: 0 texts. "blocking": 0 texts, except the negation "non-blocking nit" in 6021333114.

### Conditional approvals (verbatim)

- 4373886636 (PR 2766, 2026-05-27, APPROVED): "Overall looks good to me. Approved, assuming you'll follow up on the remaining minor comments. Also needs rebased."
- 4265644124 (PR 2698, 2026-05-11, state COMMENTED, words say approved): "Approved, but please run at least a subset of representative UTs against these changes before merging." The GitHub state and the words disagree here. Read the words.
- 5156698046 (PR 4267, 2026-09-09, APPROVED): "I'm ok approving this as-is, although I'm wondering if you looked at the possibility of using FUSE for this?"
- 4800935083 (PR 3490, 2026-07-28, APPROVED): "I do think there's some merit to a few of them, but could be a follow-up if you prefer. I'll approve as-is."
- 5371062950 (PR 4596, 2026-09-30, APPROVED): "Approved... I think your PR description is stale at this point (after all the updates from reviews), and you currently have a merge conflict. But overall looks good."
- 5431977719 (PR 4557, 2026-10-06, APPROVED): "Approved. Updates look good and clean... left one response to coding style. Trivial nit though."

Reading: he approves with open nits, a stale description or a merge conflict still present. Approval is withheld for a correctness or coverage item, not for style.

### The 48 silent PRs

- 48 of 115 PRs have no Wade words. Each has exactly one review, state APPROVED (recount).
- Size (recount from corpus.json file lists, nearest-rank quantiles): median 2 files, 19 of 48 touch one file. Median 39 changed lines, 25th percentile 10 lines, 75th percentile 130 lines (merged-taxonomy.json reports 161 for the 75th percentile with a different quantile method). 27 of 48 change at most 50 lines.
- The 67 PRs with Wade words: median 8 files, median 426 changed lines. 9 of 67 change at most 50 lines. The 65 PRs with inline comments or review-body words (tron 3879 and 2898 carry conversation comments only): median 7 files, median 410 changed lines (recount from corpus.json file lists; merged-taxonomy.json reports the same 7 and 410).
- 15 of 48 silent PRs target the hwattention_sync branch. By author: mcherba 11, BillBaumann 10, bham0n 7, mitchelldalvirosen-positron 6, jeremyconner1975 5, others 9.
- What silent PRs look like (title, files, changed lines): "Fix activation slot counter comment" (tron-3799, 1 file, 2 lines); "Correct result stream sentinel width comment" (tron-4551, 1 file, 2 lines); "Remove redundant device index lookup" (tron-3741, 1 file, 21 lines); "Use process_device_id throughout POS" (tron-3756, 36 files, 498 lines, one commit, mechanical rename); "Apply here all the doc changes made on hamon-radix128" (tron-2203, 69 files, 5199 lines); "update register json file" (tron-3631, 4 files, 7237 lines); "Set up and switch to new bitfile" (tron-2180, 7 files, 6081 lines); "Split software attention pages across cores by query" (tron-4353, 5 files, 516 lines, 16 commits).
- Reading: small, mechanical, generated or doc-only changes pass in silence whatever their line count. Commit count alone does not draw a comment (tron-4353 at 16 commits, tron-1739 at 12 commits, both silent).

### Timing

- Median time from PR creation to his first review: 0.6 days (113 PRs with a review).
- 78 of 113 PRs have his last review at the PR's current head.

## Assisted text (pasted from an AI assistant)

Words used here: PR = pull request. Disclosed paste = a Wade text that says in its own words that an assistant (Claude, "CC" for Claude Code, or GPT) wrote the block that follows. Id = the GitHub comment or review id. Register B = the long, file:line, "So"-consequence form described under "How Wade words a finding".

### The nine disclosed pastes (9 of 269 texts; ids, dates and the disclosing sentence, verbatim)

1. 3002297607 (PR 2233, inline, 2026-03-27): "Claude had this to say about below:"
2. 4131374395 (PR 2461, APPROVED review, 2026-04-17): "I think CC is onto something with that `attn_launchers` finding."
3. 3342904643 (PR 2872, inline, 2026-06-02): "(which I let Claude summarize for me below)"
4. 4674512577 (PR 2906, conversation, 2026-06-10): "So I asked Claude to summarize my concern (cuz it often words things better than I can):"
5. 3437517809 (PR 3008, inline, 2026-06-18): "GPT had this to say about `first_desc`:"
6. 4800935083 (PR 3490, APPROVED review, 2026-07-28): "I did ask claude to do a review as well. Below are the items it came up with. I do think there's some merit to a few of them, but could be a follow-up if you prefer. I'll approve as-is."
7. 5498556672 (PR 4128, conversation, 2026-09-01): "So I prompted Claude with that (and told it to look at the PR overall). I also asked it to evaluate any collateral concurrency risks... below are those results:"
8. 5544513215 (PR 3879, conversation, 2026-09-04): "below is Claude's evaluation of this PR:"
9. 3970590653 (PR 4191, inline reply, 2026-09-09): "I asked GPT to evaluate this... it agrees:"

The earliest disclosure is 2026-03-27 (CONTEXT.md says the first is in PR 2233; codex-factcheck.md claim 7 confirms the date). Two further texts mention an assistant without pasting analysis: 3227565141 (PR 2713) and 3463077403 (PR 3016).

### How to treat a paste

- The pasted block is the assistant's claim. Wade's own words are the frame sentence around it. Quote the frame as Wade; quote the block as "assistant text pasted by Wade in <id>".
- Wade's weight on a pasted item is the frame sentence, not the block. "I think CC is onto something" (4131374395), "I do think there's some merit to a few of them" (4800935083) and "it agrees" (3970590653) are endorsements. "could be a follow-up if you prefer" (4800935083) and "Maybe it won't materialize" (4674512577) are not must-changes.
- A paste can carry words Wade never uses himself. "Blocking" in 5544513215 is in the pasted block; Wade's own texts never use "blocking" except as "non-blocking" (6021333114). "must" as a directive appears only inside pasted text.
- A pasted list is answered item by item, with a fact per item, and the reply is addressed to Wade.
- A paste is not independent verification. When a pasted item cites a line, re-check the line at the reviewed head before conceding it.

### PR 4557: register B, no disclosure (Insufficient data)

- PR 4557 has 10 Wade texts: review 5420005787, inline 4188336250, 4188336256, 4188336267, 4188336279, 4188336302, 4188336316, 4188336324, reply 6021333114, approval 5431977719. None of the 10 mentions an assistant (codex-factcheck.md claim 7).
- The style markers of the 2026-10-05 texts match the disclosed-assisted PR 4128: "So" consequence in 4188336267, backticked file:line in 5420005787 ("`.github/workflows/cmake-single-platform.yml:355` builds with `-DTRON_AMX_DISPATCH=ON`"), "(line 197)" in 4188336256, "Please" three times in 5420005787.
- In PR 4128 the inline comments of 2026-09-01 and 2026-09-08 (3907183627, 3907185740, 3907214892, 3960506641, 3960538177, 3960538961; 762 to 1486 characters each) carry no disclosure. The disclosure sits in the same-day conversation comment 5498556672. In PR 4596 the 2026-09-28 inline comments (4125033634 to 4125033686, 548 to 946 characters) carry no disclosure anywhere.
- The 2026-10-06 reply 6021333114 returns to the hand-written register: "Fair enough for the AMX kernel files", "This is simply a non-blocking nit though ;-p."
- Verdict: whether PR 4557 was assisted is Insufficient data. A statement from Wade, or a disclosure sentence in the PR, would resolve it. Treat the PR 4557 findings as Wade's own words (he posted them under his name and approved on them), and treat the register as what he now writes, whatever the tool.

### Rule for an agent

- Record for every quoted text whether it is hand-written, disclosed paste, or undisclosed register B. Never cite a pasted block as "Wade said".
- When drafting in his name, write in the register, but never add a disclosure sentence he did not write and never remove one he did.

## Negative space: what he does not comment on

Words used here: PR = pull request. Loud PR = a PR with at least one Wade text (67 of 115). Silent PR = a PR with no Wade words (48 of 115). Row = one classified review item in merged-taxonomy.json (239 rows). Counts come from merged-taxonomy.json negative_space, style-stats.json and codex-factcheck.md claim 1 unless marked "recount". Each item names its source.

- File types. Inline comments by extension (243 inline): hpp 126, cpp 103, md 10, py 1, txt 1, yml 1, gitkeep 1. Over the loud PRs, files touched versus files commented: .py 46 touched / 1 comment, .txt 37 / 1, .json 12 / 0, .hs 4 / 0, .yaml 2 / 0, .sh 1 / 0, .cfg 1 / 0 (merged-taxonomy.json). Register-map regenerations (tron-3631, tron-2180) and CMake test registration (tron-2844) passed silently.
- Formatting and style policy. 0 rows about brace style, clang-format or whitespace as such. 1 text touches indentation, 2976643305 (PR 2223, 2026-03-23), whose subject is a dead loop scope: "and perhaps get rid of the extra scope (remove enclosing curly brackets, un-indent this block)" (codex-factcheck.md claim 1). 0 texts name the C++ coding guide (codex-factcheck.md claim 1; nearest is 2789768975 asking "Do we have an official guideline for tha[t]"). The only style nits: include brackets (3405979630) and a redundant `public` (3391446464: "minor nit: `public` is redundant in a struct (members are public by default)"). Exception, 1 text: 3778051701 (PR 3386, 2026-08-13, a Markdown file): "hmmm... our formatter didn't catch this extra-long line ;p? Maybe it doesn't process MD docs." plus "same here" (3778058064) on a second Markdown line. He never hand-formats a hunk.
- Kernel and SIMD arithmetic. 0 of 269 texts check a kernel line, mask value, shift, intrinsic choice or bf16 rounding policy (codex-factcheck.md claim 1). The AMX kernel files in PR 4557 drew naming comments only (5420005787, 6021333114). The one alignment finding (3960506641) sits on the disclosed-assisted PR 4128.
- Numeric expected values in tests. 0 rows recompute an expected value or dispute a tolerance. Test rows are questioned for consumer, provenance or placeholder status (merged-taxonomy.json).
- Benchmark numbers in PR bodies. 0 rows question a measurement method, a TPS or TTFT number or a benchmark table. Exception, 1 text: 4607543703 (PR 2898, conversation, 2026-06-02): "I do think that we should have some before/after Perfetto metrics captured, so we can see the cost of this JIT GoF-rebuilding overhead." This asks for a measurement to exist; it does not dispute one. A second trace suggestion is marked "No action needed" (3235915961).
- Commit messages and history. 0 rows about the wording of a commit message. 1 squash request in 334 reviews (5420005787, which names a rewording cluster, not the count alone). "rebase" in 2 texts. PR 4596 was approved at 26 non-merge commits; tron-4353 (16 commits) and tron-1739 (12 commits) were approved silently.
- CI workflow YAML. 1 inline comment on .github in 243 (3580238651, label casing: "just a trivial nit: our current `benchmark` labels use lower-case 'b'."). The CI-lane finding in 5420005787 is register B on PR 4557. He does not review runner tables, job matrices or caching.
- Missing tests on small PRs. 20 of 48 silent PRs change h/ or src/ with no file under t/ (recount). Test-existence asks appear only for a new primitive or a hardware-path change: 4614385493 (PR 2903, 2026-06-03): "Are you going to build a unit-test for this? Seems it should warrant one... verifying multi-producer ordering, wrap-around, etc"; also PRs 4128, 2698, 2565, 2148.
- Documentation. 10 of 13 PRs in the doc and skill repositories (aps-claude-files, asimov-os, asim, terminus) were approved with no text. doc/ accounts for 69 of the files in silent PRs. His doc comments are typos (4 rows on PR 2233), an undefined term, an ambiguous clause, a retirement plan and a digest's provenance. No structure, formatting or completeness review of prose.
- Reconciling the PR body against the code. Only PRs 4557 and 4596 (register B). For the other 111 PRs, no row questions a body claim about CI or result provenance.
- Owner sign-off for shared headers. Asked once (4188336279, PR 4557). 58 of 115 PRs touch h/system, h/pos, h/common or h/tron/hardware headers (codex-factcheck.md claim 2). tron-2646, tron-2648 and tron-2774 were approved silently.
- Running the test suite himself. 2 of 113 reviewed PRs (4131374395, 4422833076). Otherwise he asks the author (4265644124, 3156090573, 2915270383).
- Security, licensing, Python style, dependency versions, user-facing error wording, input validation, API documentation generation: 0 rows.
- Verdict forms. CHANGES_REQUESTED 0 of 334. "LGTM" 0 of 269 texts.

Rule for an agent: do not add findings in his name on any item above. The two exceptions (3778051701, 4607543703) are one text each in 269 and are both phrased as questions or wishes, not as asks to fix.

## When replying to Wade

Words used here: PR = pull request. Ask = a Wade text that proposes a change. Row = one classified review item in merged-taxonomy.json (239 rows, each with an outcome). Id = the GitHub comment id.

### How he reacts to pushback (verbatim)

- He concedes in writing when the author supplies a fact. 2790148917 (PR 2011, 2026-02-10, after his own zero-initialization suggestion): "yeah, doh! I still tend to forget these are **C++** structs and not simple C structs lol." 3102275102 (PR 2461, 2026-04-17): "You'd still have to iterate and set them to `std::make_unique<v_stars_row_t>()`, so wouldn't be gaining anything. Nevermind ;p". 3769729340 (PR 3733, 2026-08-12): "I guess I see why you renamed the way you did... you want existing clients of the original `drain_reserves` function to transparently inherit the new tracing option." 2709806008 (PR 1860, 2026-01-20): "nevermind the above Mike... thanks for the phone clarification ;)!"
- He defers to the owner of the area. 3277240111 (PR 2777, 2026-05-20), after a long lock-placement argument: "I would still ultimately defer to @mcherba 's input/insight on this matter." 2949458908 (PR 2176, 2026-03-17): "sorry, just saw Cherba's request to move these into config.hpp... which works too". 4188336279 (PR 4557, 2026-10-05) asks for "@bgamari-positron's explicit sign-off on the approach" instead of deciding himself.
- He accepts "next iteration" and offers to do the work himself. 3405172585 (PR 2980, 2026-06-12): "Next iteration would be fine though..." 3307412051 (PR 2766, 2026-05-26): "Just seems a bit dangerous, but probably a 'next iteration/enhancement' effort." 2636393495 (PR 1730, 2025-12-19): "Clean-up item for a to-do list once things settle." 2948027543 (PR 2176, 2026-03-17): "That's something I could take on in a later iteration though." 2771720147 (PR 1997, 2026-02-06): "else I can do it after you merge this I guess (I already have those changes staged)".
- He accepts the kernel-file exception after the author explains, and still approves. 6021333114 (PR 4557, 2026-10-06): "Fair enough for the AMX kernel files: they already use this style throughout, so the tile constants are consistent there." ... "This is simply a non-blocking nit though ;-p. Not stopping approval."
- Outcomes over the 239 rows (merged-taxonomy.json): changed 120, accepted 35, discussed 20, pushed back 16, unknown 48. The taxonomy reads this as about one in six substantive asks declined and let stand. Examples declined and not pursued: 2719158416 (mwaitx helper), 2789826297 (default parameter values repeated in the implementation, self-labelled "kinda pedantic"), 3102601258 ("if this isn't useful, should get rid of it"), the constant-name item of 5420005787.

### What an agent drafting a reply does

1. Classify the ask by its wording. "before merge", "needs", "Please <verb>" or withheld approval (see Verdict calibration) is a must-change. "nit", "trivial", "minor", "pedantic", "next iteration", "no action needed", "maybe" is a preference.
2. For a must-change, answer with a fact at the reviewed head: what changed, the file:line, and the commit id. If the ask names two repairs, say which one was taken and why.
3. For a correct ask, concede the substance in one sentence and state the change. Do not restate his finding back to him.
4. For an ask that is wrong in a detail, correct the detail with the line that decides it (he conceded on 2790148917 and 3102275102; for 2790148917 the author's intervening reply was not read, so the deciding line is inferred, codex-factcheck.md claim 8 item 11). Keep the substance if it holds. Never post a replacement sentence that the checks have not verified (SKILL.md setup item 5).
5. For a preference that the author declines, give the reason in one sentence and offer a follow-up or "next iteration". He accepts both (3405172585, 2948027543). Do not argue style.
6. For a pasted assistant list, reply item by item with a fact each, addressed to Wade. Weight each item by his frame sentence ("merit", "could be a follow-up", "it agrees"), not by the block's own severity words.
7. Match his register. A one-line question gets a one-line answer. A register B finding gets a fact, the consequence and the chosen repair, with file:line.
8. When he defers to a named owner, get that owner's written answer and cite it in the reply. Do not answer on the owner's behalf.
9. Never write "LGTM", never mark the thread resolved on his behalf, and never post a reply the author has not approved. A review request authorizes analysis, not comment posting.
