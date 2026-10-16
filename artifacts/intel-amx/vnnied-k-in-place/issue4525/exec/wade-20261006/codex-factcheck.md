# Fact-check of the codex Wade-skill claims against the corpus (2026-10-06)

Short version: Eight codex claims that contradict or qualify the Claude skill were checked against corpus.json (115 PRs, 269 Wade texts: 243 inline, 11 conversation, 15 review bodies). Four hold, four hold partly, none is refuted outright. Two Claude-skill sentences are refuted by the corpus: the "never a finding" rule for value suffixes (check 13) and the BASE definition against origin/main.

Words used here: PR = pull request. Corpus = /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/wade-20261006/corpus/ (corpus.json plus pr/*.md). Claude skill = /home/jhan/.claude/skills/Wade-code-review/SKILL.md. Codex skill = codex-skill-snapshot-1026/SKILL.md plus references/review-history.md and references/pr4557-misses.md. Ids are GitHub comment ids (inline, conversation or review). Quotes are verbatim from corpus.json. No file in the corpus or the skills was edited.

Counts used throughout: review states APPROVED 100, COMMENTED 234, CHANGES_REQUESTED 0. PRs with any Wade text: 67. PRs with base_ref != main: 42.

---

## Claim 1. "The old claim that Wade never reviews formatting or benchmark methods is contradicted by his line-length nits (#3386 r3778051701) and measurement requests (#2898 issuecomment-4607543703)."

Claude sentence under test (SKILL.md:229): "He does not comment on formatting, brace style, benchmark method, the C++ guide, or kernel arithmetic line by line."

- verdict: partly
- evidence:
  - 3778051701 (#3386, 2026-08-13, path .claude/skills/analyze-tron-perfetto-trace/references/capture.md): "hmmm... our formatter didn't catch this extra-long line ;p? Maybe it doesn't process MD docs."
  - 4607543703 (#2898, 2026-06-02, conversation): "I do think that we should have some before/after Perfetto metrics captured, so we can see the cost of this JIT GoF-rebuilding overhead."
  - 2976643305 (#2223, 2026-03-23, t/t_mwaitx.cpp): "a bit pedantic but you're no longer running a loop, so this isn't necessary... and perhaps get rid of the extra scope (remove enclosing curly brackets, un-indent this block)"
  - 3391446464 (#2906, 2026-06-10, h/tron/gof.hpp): "minor nit: `public` is redundant in a struct (members are public by default)"
  - 3235915961 (#2713, 2026-05-13, src/system/heap_v2.cpp): "wouldn't it be useful to have some TRACE_EVENTs we can gather metrics across these memory paths? ... No action needed"
  - 3156090573 (#2565, 2026-04-28): "did you run any multi-user tests to see if you encounter this 'duplicate' issue?"
  - 4265644124 (#2698 review, 2026-05-11): "Approved, but please run at least a subset of representative UTs against these changes before merging."
  - 2789768975 (#2011, 2026-02-10): "we're pretty inconsistent with variable initialization in our code. Do we have an official guideline for tha[t]"
  - 3580238651 (#3302, 2026-07-14, .github/workflows/benchmark-only-pr.yml): "just a trivial nit: our current `benchmark` labels use lower-case 'b'. Maybe it would be more intuitive if we made this label `dev-benchmark-only`?"
- counts (of 269 texts):
  - Formatting proper (line length, whitespace, include order): 1 (3778051701, a Markdown doc line, phrased as a question about the formatter).
  - Brace or indent: 1 (2976643305, whose subject is a dead loop scope).
  - Include order: 0. Brace style as such: 0.
  - "C++ guide" named: 0. Nearest: 2789768975 asks whether a guideline exists.
  - Benchmark method: 0. 3580238651 is about the spelling of a label.
  - Explicit measurement or trace request: 1 (4607543703).
  - Trace-instrumentation suggestion marked "No action needed": 1 (3235915961).
  - Requests to run tests: 2 (3156090573, 4265644124).
  - Kernel arithmetic line by line: 0.
- consequence_for_claude_skill: SKILL.md:229 overstates on "formatting" and "benchmark method" by one comment each and holds for the C++ guide and kernel arithmetic, so change "does not comment" to "rarely comments" and cite 3778051701 and 4607543703.

---

## Claim 2. "Do not invent an owner-approval gate from file authorship; report an explicit unresolved request or repository requirement when one exists." (codex, against Claude check 12)

- verdict: partly
- evidence:
  - 4188336279 (#4557, 2026-10-05, h/system/memory.hpp): "As this line says, nothing can catch a regression here, and it adds a global `operator new[]` overload in a widely included header. It's a correct reading of [intro.object], but since it came from 39a68994465f3fb753623eec18378544be806862 rather than #4698, it'd be good to get @bgamari-positron's explicit sign-off on the approach."
  - 3277240111 (#2777, 2026-05-20, h/tron/hardware/tensor.hpp): "At the end of the day this is probably 'fine' just because I don't think we're actually parallelizing across the **same device**, right? Ergo, this approach may be acceptable. I would still ultimately defer to @mcherba 's input/insight on this matter."
  - PR 2193 (author hvaneenoo-positron, base main): adds two global-namespace `extern` declarations (`pos_heap_available`, `pos_heap_active_allocations`) to the same h/system/memory.hpp. Wade's reviews: COMMENTED, COMMENTED, APPROVED, APPROVED. His two inline comments are on h/pos files. No sign-off request.
- counts:
  - Comments asking the author to obtain a named person's sign-off: 1 (4188336279).
  - Comments where Wade defers his own decision to a named person: 1 (3277240111).
  - Other @-mentions: 9, all questions or pointers: 2380263378, 2941308844, 2983833171, 3125517302, 3156090573, 3215036804, 3206111074, 3236579299, 4125818552.
  - PRs whose file list touches h/system, h/pos, h/common or h/tron/hardware headers: 58 of 115. Check 12's placement half therefore fires in 57 PRs where Wade did not ask for sign-off.
  - Unobserved-guarantee half across those 57: Insufficient data. The corpus holds file lists and comment text, not diffs or test files. One spot check (PR 2193 memory.hpp hunk via gh pr diff) shows declarations only, with no "nothing can catch" claim.
- consequence_for_claude_skill: check 12 rests on one comment whose stated reasons are the commit's origin (a fold rather than the owner's PR) and the line "nothing can catch a regression here", so keep the check, require both facts, and state that the precedent is n=1.

---

## Claim 3. "Commit count alone does not justify squash." (codex, versus Claude check 11)

- verdict: holds
- evidence:
  - 5420005787 (#4557 review, 2026-10-05): "**Commits**: 20, three of them rewording one Note. Please squash."
  - 4373886636 (#2766 review, 2026-05-27): "Overall looks good to me. Approved, assuming you'll follow up on the remaining minor comments. Also needs rebased."
  - 3206111074 (#2676, 2026-05-08, h/tron/gof.hpp): "@BillBaumann this is an old version. Be sure you are rebased to latest `hwattention_sync`... gof/shard stuff changed up when I moved away from the 'singleton' hw_attn_params"
- counts: squash requests 1; rebase mentions 2; other comments about commit history 0 (grep squash|rebase|\bcommits\b over 269 texts). The one squash request names both the count and a rewording cluster.
- consequence_for_claude_skill: check 11 already reports only clusters or unrelated commits and cites the 26-commit approval of PR 4596, so the two skills agree; add that the evidence is one comment.

---

## Claim 4. "His later acceptance of value suffixes in established kernel code does not prescribe them for shared code." (codex, #4557 issuecomment-6021333114, versus Claude check 13 "the suffix convention stays / never a finding")

- verdict: holds, and it refutes the Claude wording
- evidence, 6021333114 (#4557 conversation, 2026-10-06) in full:
  - "Fair enough for the AMX kernel files: they already use this style throughout, so the tile constants are consistent there."
  - "Outside your own files, though, the codebase does not use value-suffixed names, and the `_0X...` mask names are new."
  - "In shared code I care most about local consistency: `scaled_v_expr` in kv_cache.hpp still writes `_mm512_set1_epi32(0xffff0000)` as `hi_16_of_32`, while its partner code in v_vnni.hpp spells the same mask `V_ODD_TOKEN_LANE_MASK_0XFFFF0000`."
  - "Could the v_vnni.hpp masks follow the existing literal-plus-named-local idiom?"
  - "This is simply a non-blocking nit though ;-p. Not stopping approval."
  - 5420005787 (#4557 review, 2026-10-05): "**Constant names with the value built in**: `V_ODD_TOKEN_LANE_MASK_0XFFFF0000`, `BF16_BITS_16`, `ACCUMULATOR_TILE_0..3`, `APPENDED_TOKENS_7`, `PATTERN_BASE_0X3C00`, etc. `ACCUMULATOR_TILE_0` reads no better than the `0 /* dest tile */` it replaces."
  - 5431977719 (#4557 review, 2026-10-06): "Approved. Updates look good and clean... left one response to coding style. Trivial nit though."
- what Wade asks, exactly: accept the suffix style inside the AMX kernel files. In shared code (the v_vnni.hpp masks that pair with kv_cache.hpp) follow the existing literal-plus-named-local idiom instead of the suffixed constant. Severity: non-blocking nit.
- counts, naming comments 18 of 269:
  - magic numbers to name (6): 2620219338 (#1666), 2636393495 (#1730), 2897211589 (#2089), 2915246595 (#2148), 2947992404 (#2176), 3235796275 (#2713).
  - identifier or constant names (12): 2380263378 (#1485), 2771718489 (#1997), 2897235803 (#2089), 3075717295 (#2287), 3001991780 (#2233), 2828707534 (#2078), 3580238651 (#3302), 3769684790 (#3733), 3769729340 (#3733), 4188336324 (#4557), 5420005787 (#4557), 6021333114 (#4557).
  - Pattern: 2025-12 to 2026-03 he asks for named constants instead of magic numbers (2620219338: "I see a fair amount of 'magic numbers' like this scattered about (4, 8, 32, 128 etc). IMO we should #define them in a common location."); 2026-10 he objects to names that only encode the value. Both ask for names that carry meaning.
- consequence_for_claude_skill: check 13 and the "Words used here" entry ("It is the author's decided convention and is never a finding") contradict Wade's actual ask, so add a shared-code branch: a suffixed constant in shared code whose partner site uses a literal plus a named local is a non-blocking nit asking for the local idiom.

---

## Claim 5. "Resolve the comparison from the actual target branch... Do not hardcode origin/main." (codex procedures, versus Claude SKILL.md:14 BASE = `git merge-base HEAD origin/main`)

- verdict: holds
- evidence: corpus.json base_ref per PR.
- counts: 42 of 115 PRs have base_ref != main.
  - hwattention_sync (40): 1666, 1804, 1807, 1827, 1860, 1920, 1973, 1978, 1980, 1985, 1997, 1998, 2008, 2011, 2078, 2089, 2103, 2135, 2148, 2176, 2180, 2200, 2203, 2233, 2277, 2287, 2302, 2469, 2475, 2499, 2545, 2565, 2592, 2593, 2602, 2659, 2674, 2698, 2713, 2898.
  - bill-hwsync1 (1): 2426.
  - wm-bill-hwsync1 (1): 2461.
- consequence_for_claude_skill: the BASE definition is wrong for 37 percent of the corpus, so define BASE as the merge base against the PR's base_ref.

---

## Claim 6. "Approval can coexist with follow-ups" and "0 CHANGES_REQUESTED."

- verdict: holds
- evidence:
  - Review states from corpus.json: APPROVED 100, COMMENTED 234, CHANGES_REQUESTED 0.
  - 4800935083 (#3490 review, 2026-07-28): "I do think there's some merit to a few of them, but could be a follow-up if you prefer. I'll approve as-is."
  - 4373886636 (#2766 review, 2026-05-27): "Approved, assuming you'll follow up on the remaining minor comments. Also needs rebased."
  - 5371062950 (#4596 review, 2026-09-30): "Approved... I think your PR description is stale at this point (after all the updates from reviews), and you currently have a merge conflict. But overall looks good."
- how Wade signals a must-change (ids with the phrase):
  - "before merge/merging": 3124878965 (#2499) "can we comment this back out before merge?"; 4265644124 (#2698) "please run at least a subset of representative UTs against these changes before merging."
  - "needs": 3002050036 (#2233) "looks like this still needs fixed"; 2897190682 (#2089) "the pre_attn scalar needs to come from the model... 1.0f is not the correct value, currently"; 4373886636 (#2766) "Also needs rebased."
  - "Please <verb>": 5420005787 (#4557) "please split them out", "Please squash", "Please re-run them or mark them as pre-merge"; 3960538177 and 3960538961 (#4128) "Please extend an existing CI suite".
  - "must" as a directive by Wade: 0 (2670498736 reads "must be been getting"; 3001866834 is doc text inside a suggestion block).
  - "blocking": 0 by Wade except the negation in 6021333114 "non-blocking nit"; the word "Blocking" in 5544513215 is pasted Claude text.
  - Withheld approval: 16 of the 67 PRs with Wade text have no APPROVED review: 1485, 1860, 2089, 2233, 2287, 2426, 2674, 2695, 2777, 2872, 3016, 3738, 4128, 4258, 3879, 2898.
- consequence_for_claude_skill: the severity vocabulary at SKILL.md:228 matches the corpus; add that a must-change is signalled by "before merge", "needs", "Please <verb>" or withheld approval, never by CHANGES_REQUESTED.

---

## Claim 7. "Wade sometimes posts analysis from an AI assistant. Treat it as attributed review material, not independent verification."

- verdict: holds for the disclosed cases; whether PR 4557 was assisted is Insufficient data
- evidence, explicit assistant use (9 texts):
  - 3002297607 (#2233, 2026-03-27): "Claude had this to say about below:"
  - 4131374395 (#2461 review, 2026-04-17): "I think CC is onto something with that `attn_launchers` finding."
  - 3342904643 (#2872, 2026-06-02): "which I let Claude summarize for me below"
  - 4674512577 (#2906, 2026-06-10): "So I asked Claude to summarize my concern (cuz it often words things better than I can)"
  - 3437517809 (#3008, 2026-06-18): "GPT had this to say about `first_desc`:"
  - 4800935083 (#3490 review, 2026-07-28): "I did ask claude to do a review as well. Below are the items it came up with."
  - 5498556672 (#4128, 2026-09-01): "So I prompted Claude with that (and told it to look at the PR overall). I also asked it to evaluate any collateral concurrency risks..."
  - 5544513215 (#3879, 2026-09-04): "below is Claude's evaluation of this PR:"
  - 3970590653 (#4191, 2026-09-09): "I asked GPT to evaluate this... it agrees:"
  - Non-analysis mentions (2): 3227565141 (#2713, 2026-05-12) "`for_claude/heap-profile.log` probably won't exist for anybody else but you ;p?"; 3463077403 (#3016, 2026-06-23) "the new variables Claude introduced in my WIP PR".
  - Earliest disclosure is 2026-03-27, not 2026-07 as CONTEXT.md states.
- PR 4557 (review 5420005787 plus inline 4188336250, 4188336256, 4188336267, 4188336279, 4188336302, 4188336316, 4188336324, reply 6021333114, approval 5431977719): none of the 10 texts mentions an assistant.
  - Style markers present: "So" in 4188336267 ("So any pointer or row-major 64x128 bf16 view passes the QK kernel"); backticked file:line in 5420005787 ("`.github/workflows/cmake-single-platform.yml:355` builds with `-DTRON_AMX_DISPATCH=ON`"); "(line 197)" in 4188336256; "Please" three times in 5420005787.
  - The same markers appear in the PR 4128 inline comments of 2026-09-01 and 2026-09-08 (3907183627, 3907185740, 3907214892, 3960506641, 3960538177, 3960538961: no inline disclosure; disclosure in the same-day conversation comment 5498556672) and in PR 4596 (4125033634 to 4147010638: no disclosure).
  - The 2026-10-06 reply 6021333114 returns to the older register: "Fair enough", ";-p".
- style counts by period (texts / average words / slang or emoticon / question mark / file:line):
  - 2025: 8 / 25 / 4 / 5 / 0
  - 2026-01 to 2026-08: 222 / 29 / 31 / 105 / 3
  - 2026-09 onward: 39 / 98 / 4 / 12 / 10
- three verbatim 2026-01..06 examples: 2719160746 (#1920, 2026-01-23) "wrap in `#ifdef WRITEBACK_HEXDUMPS`?"; 2771713070 (#1997, 2026-02-06) "don't need this bf16.hpp include now right?"; 2737826254 (#1920, 2026-01-28) "do we need these in both the header and the impl file? This cpp file already includes `device.hpp` where they're also declared".
- three verbatim PR 4557 examples: 4188336250 "This row makes "a float NaN stores as +inf" a tested contract. AGENTS.md treats NaN as corruption; this pins the path that hides it."; 4188336324 "Nit: the section is still named "append_v preserves poison", but it now asserts that the poison is zeroed."; 5420005787 "**Commits**: 20, three of them rewording one Note. Please squash."
- consequence_for_claude_skill: "How Wade words a finding" (SKILL.md:225-228) describes only the 2026-09 onward register, so label it by date, add the earlier short-question register, and state that the assisted-review hypothesis for PR 4557 is unverified (no disclosure; markers match the disclosed-assisted PR 4128).

---

## Claim 8. Codex precedent citations (review-history.md "Representative evidence" and "Counterexamples", pr4557-misses.md) checked against the comment text

Holds as worded, checked verbatim (40 ids): 2789792758, 3120788282, 3342904643, 3307412051, 3036995239, 3907183627, 3907185740, 4607543703, 4674512577, 2771743559, 2771718489, 3960538177, 3960538961, 3350173837, 4188336250, 4188336256, 4146998951, 3970127694, 4125033634, 4125033653, 4125033664, 4125033686, 4125033677, 3456320516, 3907214892, 4147010638, 3454460758, 5106398334, 4146947611, 4020335622, 2790148917, 3769729340, 6021333114, 5544513215, 4800935083, 4188336302, 4188336316, 4188336324, 4188336267, 4188336279.

Supporting quotes for a few that could be doubted:
- 2789792758 (#2011): "As is, we aren't actually waiting 'after the last xfer', we'll be waiting on the 'first' device's xfer (`get_device(0)`)"
- 3307412051 (#2766): "all of these `ck_pr_stall` loops are unbounded... Just seems a bit dangerous, but probably a 'next iteration/enhancement' effort."
- 3350173837 (#2903): "At a minimum that would allow tests to instantiate smaller queues and cover wrap-around / full behaviors without having to build 2048 jobs ;p."
- 3456320516 (#3016): "we're getting so many events these days it's overflowing our Perfetto buffer pretty quickly and it just discards the rest"
- 4125033664 (#4596): "The runtron validation can't show this because prefill and decode forwards are separate there."
- 2771718489 (#1997): "why are you calling this `HW O` if you're printing the Ra value? We don't have an `O` until we divide Ra by SUME, right?"
- 4188336279 (#4557): asks for "@bgamari-positron's explicit sign-off on the approach" (pr4557-misses.md "Ben Gamari's explicit acceptance").

Partly supported or unsupported as worded:

1. 3277240111 (#2777), codex: "distinguished an allocator's existing lock from an unprotected transfer queue... explicitly qualifying the safest lock interval".
   - verdict: partly. No allocator lock is mentioned. Text: "it co-locates the lock with the thing it's protecting... in this case (critically) the `load_weight_q` which is mutated inside that function". The interval qualification holds: "it's really only the `xfer_blocks` we need to span with protection." The comment also ends "this approach may be acceptable. I would still ultimately defer to @mcherba 's input/insight on this matter."
2. 3866568650 (#4007), codex: "He distinguished hardware storage width from model width and a test-only helper's parameters."
   - verdict: partly as precedent. The content holds, but it is a reply in which Wade explains his own earlier code: "this is left over from evolution, after I had to start supporting gpt-oss heads that are only 64 wide." It is not a finding against the author.
3. 3227468540 (#2713), codex: "A temporary workaround test needed a tracking and replacement plan."
   - verdict: partly. Text: "so are we enshrining this work-around forever? Or will be create a story to pursue/understand/address it further? If so we should probably call that out here with a TODO or something." Tracking holds; a replacement condition is not asked.
4. 3973917755 (#3738), codex: "retention of useful compatibility rationale".
   - verdict: partly, Insufficient data. Text: "why did this comment get removed? It's still relevant AFAIK (and `copatible` should get updated to `compatible`)". The removed comment's content is not in the corpus; "compatibility rationale" is inferred from the typo. Resolving it needs the PR 3738 diff of h/pos/config.hpp.
5. 4095262504 (asimovsw-docs #64), codex: "a plan for conflicting specifications".
   - verdict: partly. Text: "what is our retirement plan for these older docs? It's confusing (esp. for newer folks) to come across multiple specs in multiple locations". "Conflicting" is not said.
6. 5420005787 (#4557), codex: "He asked for current or explicitly labeled older results and a description matching the final code."
   - verdict: partly. The results half holds: "Please re-run them or mark them as pre-merge." The description half is a paraphrase of "It says the required CI builds AMX-off. `.github/workflows/cmake-single-platform.yml:355` builds with `-DTRON_AMX_DISPATCH=ON`." The direct support is uncited: 5371062950 (#4596 review, 2026-09-30) "I think your PR description is stale at this point (after all the updates from reviews)".
7. 3970590653 (#4191), codex: "a vectorized reader still consumed masked values from an unfinished shared page".
   - verdict: holds in substance. The GPT text says "scaled_v() still reads every V entry in the page, including invisible entries with zero weights"; "vectorized" is not in the text.
8. 3960506641 (#4128), codex: "reported a misaligned scratch buffer by following it into the real vector store and checking a sanitizer reproducer".
   - verdict: holds as text: "A small UBSan reproducer using the gather's exact intrinsics fails with that alignment and passes with an aligned destination." Attribution is open: it sits on the PR where Wade disclosed Claude use one week earlier (5498556672, 2026-09-01).
9. 3778051701 (#3386), codex: "line-length nits" (plural).
   - verdict: partly. One comment, about the formatter's Markdown coverage, phrased as a question.
10. 3640191012 (#3385), codex: "retracted a proposed assertion after finding that zero tracked layers represented a software-only model".
    - verdict: Insufficient data. The id is not in the corpus (PR 3385 is Wade-authored and excluded). Codex itself labels it author-side.
11. 2790148917 (#2011), codex: "withdrew a zero-initialization suggestion after learning the type supplied its own defaults".
    - verdict: holds for the retraction. Parent is Wade's own suggestion "dma_xfer_state xfer_state = {0};" and the reply is "yeah, doh! I still tend to forget these are **C++** structs and not simple C structs lol." The reason is inferred from the author's intervening reply, which was not read.
12. pr4557-misses.md: "Wade cited `cmake-single-platform.yml` as evidence that CI enabled AMX."
    - verdict: holds. 5420005787: "It says the required CI builds AMX-off. `.github/workflows/cmake-single-platform.yml:355` builds with `-DTRON_AMX_DISPATCH=ON`."

- consequence_for_claude_skill: when the Claude skill cites codex's review-history.md, use the partly-supported citations (items 1 to 6, 9) only with the verbatim quote, prefer 5371062950 for "description stale", and do not cite 3640191012 or 3866568650 as review precedent.

---

## Summary by verdict

| Claim | Verdict |
|---|---|
| 1 formatting and benchmark | partly |
| 2 owner-approval gate | partly |
| 3 squash on count alone | holds |
| 4 value suffixes in shared code | holds (refutes Claude check 13 wording) |
| 5 target branch not origin/main | holds (refutes Claude BASE definition) |
| 6 approval with follow-ups, 0 CHANGES_REQUESTED | holds |
| 7 assisted reviews attributed | holds for disclosed cases; PR 4557 Insufficient data |
| 8 citation wording | partly (40 hold, 7 partly, 1 not in corpus) |
