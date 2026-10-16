---
name: wade-code-review
description: Review a positron-ai/tron pull request at its final head the way reviewer Wade does, before he sees it. 35 checks derived from his whole review record (115 PRs, 273 comments, 2025-09 to 2026-10). Code checks (dead symbols and includes, debug switches left on, comments that contradict code, magic literals, duplicated logic, type and initialization choices, names, silent fallbacks, index and wait-set mismatches, lock placement, buffer lifetime, hot-path cost, instrumentation ownership), test checks (value rows without a consumer, hardware-gated or silently skipped tests, duplicate coverage, test names, tests that bypass the changed path, workaround tracking), claim checks (guarantees wider than the code, CI lanes, stale result rows, PR-body passages, stale descriptions), and scope checks (unrelated hunks, fixup clusters, shared-header ownership, bot findings). Use before requesting review, after every review round, when replying to Wade, and whenever the PR body or commit history is part of what he reads.
---

# Wade-code-review

Short version: Review the PR as the reviewer reads it, not as the author built it. Wade reads production code first (203 of 243 inline comments sit in h/ and src/, the header and source directories), and he asks one question of every added line: who consumes it, what guards it, and does the text beside it say what the code does. Read the diff, the full files it touches, the PR body, the branch commit list and the CI configuration at the final head, and ask that question of every hunk, every test row and every body sentence.

Passing tests and a faithful implementation of a design do not establish that the design chose the right contract. The design document, earlier review findings, a test's own header comment and a pasted bot finding (a comment from an automated review tool) are claims to check, never the oracle.

## Words used here

- PR: pull request. HEAD: the commit the reviewer will see. BASE: the merge base of HEAD and the PR's target branch (`gh pr view N --json baseRefName`). 42 of the 115 PRs in Wade's record targeted a branch other than main. So never assume origin/main.
- CI: continuous integration, the automated build-and-test jobs. A lane is one workflow file with its trigger block and configure line. The gating lane is the one whose jobs `gh pr checks N --required` lists.
- gh: the GitHub command-line tool. Catch2: the C++ test framework. TEST_CASE, SECTION and GENERATE are its test, sub-test and parameter macros. REQUIRE is its run-time assertion, and STATIC_REQUIRE is its compile-time assertion.
- Note: a named long comment in the code, written `Note [name]`. TRON_ASSERT: the project's abort-on-false assertion macro. TRACE_EVENT: a Perfetto (the tracing tool) trace span.
- AMX: Intel's matrix instruction set. Its kernels run only on hosts that have it, and `available()` is the runtime probe. FPGA attention: the attention path that runs on the FPGA card (the hardware accelerator). DMA: a hardware memory transfer that can outlive the function that issued it. GOF: a group of KV pages (blocks of the key/value cache) transferred to the FPGA.
- Lift PR: a PR that carries a step of a long-lived branch (hwattention_sync, the FPGA attention branch) into main; its title or body says "step N", "phase N", "lifts" or "pulls in". Hunk: one contiguous block of changed lines in a diff. "fwiw": for what it is worth, Wade's marker for an informational remark.
- Comment totals used here: 273 texts were classified (243 inline comments, 11 conversation comments, 15 review bodies with words, 4 texts counted twice as replies); 238 of them are review remarks and 35 are answers, praise or self-notes; the per-check counts below sum to more than 238 where one comment carries two concerns.
- NaN: not-a-number, the floating-point value for an invalid result. Oracle: the source of a test's expected value. Shared helper: a function both the expected and the actual side call.
- Fixup commit: a commit that exists only because an earlier commit of the same PR was wrong or badly worded.
- Value suffix: the author's convention of ending a named constant with its value (`MAX_RETRIES_3`). Wade accepts it inside the AMX kernel files (amx_attn.cpp, amx_attn_iface.hpp); in a shared file he asks for the file's existing idiom (6021333114, check 13). jhan decided the same on 2026-10-06: new or moved code in a shared file matches that file's spelling, and `NAME_<value>` constants stay in the AMX kernel files.
- Attributed text: a block Wade pasted from an AI assistant (nine disclosed cases, listed in references/wade-style.md). It is the assistant's claim, framed by Wade's sentence. A check that rests only on such text says so.
- Id: a bare number in parentheses, such as (5371062950), is a GitHub comment or review id.
- Precedent "n = k comments over m PRs": how many of Wade's comments the check was derived from. A check with n = 1 is a hypothesis about him, not a habit.

## Setup: read what the reviewer reads

1. Determine HEAD and BASE. Save the PR body (`gh pr view N --json body`), the branch log (`git log --no-merges BASE..HEAD`), the diff, and the full text at HEAD of every file the diff touches, tests included. Line numbers in findings are HEAD lines.
2. Read the complete discussion over the three paginated endpoints (`pulls/N/reviews`, `pulls/N/comments`, `issues/N/comments`), including later replies. A retracted objection is not precedent. An author's answer can close a question before you ask it.
3. Read the repository test policy in AGENTS.md ("Tests": assertions about values or structure need an identifiable consumer, no duplicate coverage, extend the closest existing test) and the NaN rule (treat NaN as corruption). Quote them by line in findings.
4. If the user limits the evidence (no network, no worktree), respect the limit and report what each check could not establish. Write `Insufficient data` and name the missing input. Never fetch or change state in a worktree you were told not to change.
5. Run every check at the final head, after each review round and before requesting review. A check that ran on an earlier diff does not count. A hunk outside the diff gets at most an informational "fwiw" line.
6. When Wade has already commented, run the checks on his comments before replying. He can name the right concern and still propose a remedy that removes protection. Concede the substance, correct the detail, and never post a replacement sentence the checks have not verified.

Exact commands for each check are in [references/procedures.md](references/procedures.md). How he words findings, how he decides verdicts and what he never comments on are in [references/wade-style.md](references/wade-style.md). The corpus boundary and the method are in [references/wade-corpus.md](references/wade-corpus.md). The originating PR 4557 case is in [references/pr4557-misses.md](references/pr4557-misses.md).

## The thirty-six questions (35 check numbers; check 3 is split into 3A and 3B)

In check-number order; the sections below are ordered by how often Wade raised each concern. Checks 1 to 13 come from the 2026-10-05 skill (PR 4557) and keep their numbers. Checks 14 to 35 come from the whole record.

1. Value row, fixture literal or opaque literal: name what depends on this exact value (reader, exercised field read) or where it came from (command, date, revision).
2. Compile-time shape check: which production line outside the probed type's own header would misbehave if it flipped, and is it not already fixed by a declaration or static_assert in a header?
3A. Gated or blind test: were the code wrong as the test claims, which assertion fails on the gating lane, without hardware, on a second run?
3B. Named run: which run, by binary or command, build configuration and commit, executed the changed path at this head, and where does the PR say so?
4. Duplicate coverage: which deliberate code break fails test A but passes test B, and, for a new test binary, which existing binary already executes the function under test?
5. Test label: next to the setup, the REQUIRE lines and the sibling units, does the name, tag string or result print describe the passing state and follow the siblings' pattern?
6. Claim sentence: for every subject it covers (each type, path, element count, build path), which code line reaches what it says, and does it say where it stops?
7. CI sentence: which lanes set or omit this setting, with their triggers, and does the sentence name the lane it means?
8. Result row, body sentence, branch: do the result ids, the sentences the review-round commits touched, the merge state, a ported file and the reviewer's open suggestions all match this head?
9. Body passage, comment or Note: would deleting it change a decision about the head, or cost a reader with only the code a fact the code must honor?
10. Hunk, file row, removed comment or flag: reverted alone, would any body sentence stop being true or any PR symbol stop compiling, and can the author say where it came from?
11. Commit: does it exist only because an earlier commit of this PR was wrong or badly worded?
12. Shared-header hunk no test observes: has an owner of the file accepted the placement, in writing, at a head that contains it?
13. Number or constant: can a reader say what this number measures, from a name in reach, a derivation comment or the stem alone, and why did any former name leave?
14. Dead symbol: which line at HEAD, other than its own declaration, reads, calls, includes or compiles this, and if none does, what is it in the PR for?
15. Added prose line: does it hold a word neither the dictionary nor the code knows, a name one letter from a real symbol, or an over-wide Markdown line?
16. Debug switch, dump, include or trace: is it meant to ship enabled in the target branch, and under which guard the file already uses should it sit?
17. Comment or label: does every identifier, placeholder, path, label, tense and negation in it match the code line it describes at HEAD?
18. Existing helper: does a function at HEAD or on the base branch already compute, decide, wait for or order this, with no difference the output depends on?
19. Declaration types: can this value be negative or change after startup, and does the surrounding code already use the unsigned, const or initialized form at HEAD?
20. Identifier: at the use site, does the name say what it holds and match its comment, siblings and repository spelling?
21. Declaration: can a reader of this file alone at HEAD learn what the new parameter, variable, routine, helper, default or term is for and why it has this shape?
22. Redundant code: if this statement, member, branch, specifier or scope were deleted, would any state, type or build change, or does the language or nearby code already give it?
23. Disabled code: does any build compile this `#if 0` block or commented-out statement, and if not, why is it kept rather than deleted or marked as reference?
24. Placement: does a reader find this declaration, constant, include or helper in the file whose name owns it, or must they search a file about something else?
25. Silent behavior change: on which input do the removed line and the added line behave differently, and does the PR body say that difference is intended?
26. Count, index or wait set: on every path, does this count, index or completion wait cover exactly the set it stands for, and who reads the result otherwise?
27. Silent fallback: can a bug-free caller reach this clamp, early return or spin, and if not, why is it not an assert that names the value?
28. Shared state: what protects mutation, which thread writes, which reads at HEAD, and does the lock, atomic or wait live in the object that owns the state?
29. Buffer: after the line that frees, submits or reallocates it, who still reads it, and does its declared alignment reach the consumer's widest aligned store?
30. Hot path: does every call on a spin, layer, token or poll path do work the sibling or BASE avoided, unneeded in the common case?
31. State ownership: who owns this record, does every call into the subsystem sit under its guard, and does the row key name one thread in every forward?
32. Operator view: can an operator see, measure or switch on the new state, counter, trace or option through the debug dump, Perfetto, FUSE (the file-system interface that exposes live stats) or the launcher?
33. Changed path: which test enters the changed code at its production entry, and which assertion fails if that code is wrong?
34. Workaround: is this workaround temporary or permanent, and if temporary, which story tracks the root cause and where is the TODO that says so?
35. Bot finding: which HEAD line (initializer, caller, or PR title) decides the claim, does it agree with the bot, and is it quoted?

## Checks on code: hygiene

Where most of his comments land (146 of the 238 classified review remarks; one comment can carry two concerns). Each check asks of an added line: who uses it, does the text beside it match it, and does the project already have it.

### 14. Added symbol, include, parameter, branch or header needs a consumer at HEAD

Trigger: diff adds a name, an `#include`, a parameter, an `if` an enclosing guard decides, a second `TRACE_EVENT_END` (span end), or a header nothing includes.

Procedure:
1. `git grep -n -w NAME HEAD -- h src t bin ingest`, minus its declaration. Zero hits is a finding.
2. Zero callers: a comment promising an action ("clear", "called between") leads to the lifecycle code.
3. Include X in F: grep F for X's names at HEAD and BASE.

Question: Which line at HEAD uses this, or what is it for?

Do not fire on: test-only helpers (ask for a label, 3866590750); author-declared kept-for-later code; dead code outside the diff ("fwiw", 3866653656); an include used only under an off debug switch (check 16 owns it); lift-PR minor items (one "fwiw" line).

Finding shape: "I don't see where `<name>` is used? (<file:line>) Just for completion/future enhancement?"

Severity and precedent: never "nit" (his label for a trivial finding). Minor when the leftover compiles to nothing. Normal when a consumer or definition is missing (3029165954). n = 21 comments over 12 PRs, 2026-01-26 to 2026-08-26.

### 15. Spelling, wrong names and over-wide lines in added prose

Trigger: added C++ comment or string literal (h/, src/, t/ (the test directory), doc/), or .md line outside a fence.

Procedure:
1. prose.py (references/check15/) on `git diff BASE HEAD`.
2. spell.py (pyspellchecker dictionary) against a `git grep` allow list (BASE words, HEAD identifiers, basenames). Read the hits the allow list did not remove.
3. step5.py: a comment token that occurs once in the whole tree and is one letter edit away from a code identifier.
4. width.py: a .md line over 1.25 times the width of the widest unchanged hunk line. Read such lines for repeated words.

Question: does the line hold an unknown word, a name one letter from a symbol, or an over-wide Markdown line?

Do not fire on: context lines; commit subjects, PR body; tokens that match a code symbol; lowercase sentence start; new .md files, tables, fences, URLs; grammar.

Finding shape: one GitHub ```suggestion block (a comment whose text the author can apply with one click) holding the corrected line (3307296300). For an over-wide line: a formatter question (3778051701), repeated as "same here" (3778058064).

Severity and precedent: nit, usually unstated (16 of 19 bare blocks), never blocking (3125494616 one minute before APPROVED 4156364038). n = 19 comments over 8 PRs (tron 2011, 2078, 2148, 2233, 2499, 2766, 2903, 3386), 2026-02-10 to 2026-08-13.

### 13. A number in production code carries its role

Trigger: in h/ or src/: a bare literal above 1 in a changed function; a literal in a removed name's slot; a stale message after a constant change (the changed value's behavior belongs to check 25); an underived sizing constant (its constness and initialization belong to check 19); a count constant as failure value; a suffixed constant in shared code beside a partner's named local.

Procedure:
1. Grep added lines, comments stripped, for literals above 1 the removed line lacked.
2. Grep the file, h/pos/config.hpp and includes for that value.
3. Pair removed names with added lines. `git log -m -S` finds merge artifacts.

Question: what does this number measure, and why did its name leave?

Do not fire on: 0, 1; unchanged lines unless the diff touches their replacing constant; `/ 2` still explained; t/; SIMD (vector instruction) code, diagnostics; accessor-computed values (check 18); clamp bounds (check 27); suffixes inside the AMX kernel files (amx_attn.cpp, amx_attn_iface.hpp); deferrals (items the author has already marked as deferred).

Finding shape: "`<expr>` (<file:line>) hard-codes <N>; <config:line> names it `<name>`. Use it? Nit."

Severity and precedent: nit (`non-blocking nit`, 6021333114). A design question for a sizing constant. n = 18 comments over 13 PRs, 2025-12-15 to 2026-10-06.

### 16. Debug switch, dump, include, print or trace promotion that ships on

Trigger: a commented-out `// #define NAME` debug switch flipped on; an added dump, `dbg_*_log` macro call or `#include` outside its sibling's guard or on the wrong switch; a TRACE_EVENT moved off `<cat>-detail` (the detail-level trace category); an always-on debug print.

Procedure:
1. Grep the diff against BASE (merge base with the PR's base branch) for `#define` flips and added dump, log, trace, include lines.
2. Grep HEAD for each flipped NAME's `#ifdef` blocks and added calls' guards.
3. Read perfetto/apponly.cfg (the production trace configuration) and the PR body.

Question: Should this ship enabled in the target branch or sit under which guard the file already has?

Do not fire on: a commented define, a value edit inside a guarded block, a switch on at BASE, a std::terminate path, t/.

Finding shape: "`NAME` is now `#define NAME` at <file:line>, so its blocks ship; intend to leave this enabled in <branch>?"

Severity and precedent: a lowercase question. The strongest form is "can we comment this back out before merge?" (3124878965). He approves once answered. n = 14 comments over 8 PRs, 2026-01-23 to 2026-06-23.

### 17. Comment, log label or doc clause matches the line it describes

Trigger: an added comment, label or doc clause tying a claim verb (set by) to an identifier, carrying a placeholder, path, `Q.61` (a fixed-point format label), negation or `?`, labelling a format argument (3405930260), or naming a new option's owning program (5106398334).

Procedure:
1. Map added lines to HEAD; drop moved text.
2. Read the subject's first assignment or call within 90 lines. A token that is absent at HEAD but has a sibling with the same stem is a finding here; a token with no same-stem sibling belongs to check 15.
3. Grep the src/ formatter; pair label with argument.
4. Check paths (`git cat-file -e`), tense (removed lines), negation (function body), option owner (parser).

Question: does each identifier, placeholder, path, label, tense and negation match the described line?

Do not fire on: no-symbol tokens (check 15); guarantee sentences with a compile-time mechanism word (check 6); default, plural or `or` subjects (same). Never block.

Finding shape: "`<text>` says X but line N uses `Y` ... right?" (3405930260).

Severity and precedent: nit to minor, by form. One comment per stem, then approval. n = 13 comments over 12 PRs, 2026-02-06 to 2026-09-24. None attributed.

### 18. New code re-derives what an existing helper already provides

Trigger: added h/ or src/ code repeats an existing function: an environment read a helper decides, a busy-wait where mwaitx (the wait primitives) exists, a model-derived literal or formula, a copied commit sequence, a second container walk.

Procedure:
1. Grep `git diff -U0 BASE HEAD -- h src` per kind.
2. Grep h/, src/ at HEAD and BASE for owner and callers.
3. If none, `git log -S` the base branch, `--not HEAD`.
4. Diff both sides.

Question: Does an existing function already compute, decide, wait for or order this, with no difference the output depends on?

Do not fire on: inputs the helper cannot accept (PRs 1920, 2461), never a second option (PR 2287); same-scope locals; bare literals (check 13); spin-loop bounds (check 27); functions that differ in a detail the output depends on (PR 2693); copies kept at approval.

Finding shape: "`<expression>` (<file:line>) re-derives what `<helper>` (<file:line>) computes. One helper, so copies can't drift."

Severity and precedent: "Nit:" (4147010638). A question for a primitive (2719158416). A statement for his own helper (3029194687). n = 10 comments over 10 PRs, 2026-01-23 to 2026-09-30. Member 3907214892 is an undisclosed PR 4128 comment in the long register (the disclosure is in 5498556672).

### 19. Declaration types and initializers (counts, struct locals, literal globals, sweeps)

Trigger: a hunk adds a signed count with an unsigned producer, field or cast; an uninitialized local of a diff-touched, constructor-less struct; a non-const UPPER_CASE literal global; or an initializer change that the PR body says was applied across files.

Procedure:
1. Grep the diff for signed counts, then the HEAD file for types and casts.
2. Print the struct at HEAD, count initializers; grep global writes except the definition.
3. Grep `new T`, T's constructor, AGENTS.md and the project's C++ coding guide (no written rule). Read later replies.

Question: can the value be negative or change after startup, and does surrounding code already use the unsigned, const or initialized form?

Do not fire on: initializer-only hunks; scalar locals; function-initialized globals; fully initialized structs (withdrawn, 2790148917); placement (check 24); spelling (check 15).

Finding shape: "`<name>` (<file>:<line>) is `int` while `<anchor>` (:<line>) is `uint64_t`: never negative, right, so wouldn't `uint64_t` make more sense?"

Severity and precedent: nit ("a bit pedantic", 4125818552, the approving review itself). n = 9 comments over 5 PRs (tron 1485, 2011, 2193, 2438, 3008), 2025-09-25 to 2026-06-18. No member is pasted assistant text; 4125818552 is a hand-written review body on PR 2438.

### 20. An identifier states its role

Trigger: an added identifier drops what its removed line or comment states, abbreviates a repository spelling, repeats a sibling flag's stem, claims an absolute (for example "all" or "never") that the PR body itself limits, or miscases a repository label.

Procedure:
1. Map added lines to HEAD (procedures.md). Grep comments, `-`/`+` pairs, short parameters, absolutes, labels.
2. Read comment, removed line, call site and function at HEAD. Run `gh label list`.
3. `git grep -w -c` both spellings at BASE. Report a finding when one spelling has ten times the hits of the other. Propose the change in a GitHub suggestion block.

Question: at the use site, does the name say what it holds and match its comment, siblings and repository spelling?

Do not fire on: tokens with ten or more BASE hits; defining comments; role-typed parameters; a wrapper split the private declaration explains (3769729340); a promised move (3001991780); constants and initialization (check 13 (magic literal), 6021333114; check 19 (type and initialization)); unbounded wait loops (check 27 (silent fallback)).

Finding shape: "`<name>` (<file:line>) holds <quantity>, but says <generic word>. Nit: `<proposed name>`?"

Severity and precedent: nit, never blocking ("just a trivial nit", 3580238651). n = 8 comments over 7 tron PRs, 2025-09-25 to 2026-08-12.

### 21. Explanation at the declaration

Trigger: a new parameter, getenv (environment-variable read), 20+ line function, t/-only helper, moved default or design-spec term that nothing at HEAD explains, or prose demoting a document with no retirement plan.

Procedure:
1. Grep the diff for defaulted parameters and getenv reads, then HEAD for each name.
2. List uncommented new functions of 20 or more lines.
3. For a t/-only helper, read its `return CALLEE(` line and the production arguments.
4. Prose: grep the glossary and status sections.

Question: can a reader of this file alone learn what the new thing is for and why it has this shape?

Do not fire on: a bug fix (no Note, 3866668853), a default some caller keeps, a getenv that a log line, an assertion or an existing accessor already covers (check 18 owns the last case), a helper whose callee varies in production.

Finding shape: "can we document `<name>` (e.g. why is it a 'hint')? a comment at the declaration would do."

Severity and precedent: nit or minor, never blocking. n = 8 comments over 6 PRs, 2026-02-10 to 2026-09-24.

### 22. Redundant statement, member, branch, specifier or scope (nit)

Trigger: pass-through lambda in a slot (a callback field the caller fills); `else` repeating initializers; `public:` first in a struct; call repeated where a local holds it; id member a pointee already holds (new struct); count beside `std::vector`; bare block from a removed loop; cast to the element type.

Procedure:
1. Grep each shape (references/procedures.md) in the BASE..HEAD diff, BASE from `gh pr view N --json baseRefOid`.
2. Read the whole function at HEAD.
3. Read the slot alias, callee, pointee writers or typedef chain.

Question: deleted, would state, type or build change, or is it already given?

Do not fire on: capturing or converting lambdas; counts beside `std::array`; atomic or lock-free getters (check 28); branches an enclosing guard decides, members with no reader (check 14); explicit `= 0`. Withdraw after an author fact (2790148917).

Finding shape: "minor nit: `<x>` is redundant here, <reason>. Would it be clearer to just do `<y>`?"

Severity and precedent: nit, never blocking: 'minor nit:' (3391446464), 'a bit pedantic but' (2976643305). n = 8 comments over 8 PRs, 2026-01-17 to 2026-06-10.

### 23. Disabled code left in the tree (`#if 0` blocks, commented-out statements)

Trigger: the diff adds `#if 0` (a block no build compiles) or a commented-out statement in h/ or src/, or an old `#if 0` sits near a hunk.

Procedure:
1. Run procedures.md steps 1-3.
2. Grep the block's first statement at BASE. If the statement is present there, the block was live code.
3. Grep HEAD for a live twin of the commented call.
4. Read the two lines above for a reason.

Question: does any build compile this, and if not, why keep it?

Do not fire on: a stated reason above; commented log, dump or exit calls; t/ (tests); `#ifdef NAME` (check 16 (debug switch)); a commented wait live at BASE (check 25, 3307473806); a block kept on purpose (3102946251); check 10 only decides whether the hunk belongs.

Finding shape: "`<file>:<line>` is <a commented-out `<call>` | an `#if 0` block of N lines> that nothing compiles. can this go away, or is it a reference?"

Severity and precedent: none; one nit per file, never blocking. n = 7 comments over 5 PRs (tron 1666, 1920, 1997, 2148, 2461), 2025-12-15 to 2026-04-17.

### 24. Declaration, constant block, include or growing function sits out of place

Trigger: a hunk removes a pre-existing `constexpr` (compile-time constant) below a header's first struct, class or function body; a declaration is placed in a header other than its definition's own; a quoted include missing under h/; 30 added lines grow both branches of a 400-line function; dump_ helpers kept on request.

Procedure:
1. grep touched headers: first body line, deleted constexpr lines below it.
2. grep src/ for each declaration's column-0 definition. Resolve quoted includes at HEAD. Measure the growth of each hunked function.
3. Read the threads and the body. A move request or a scheduled split closes the item.

Question: Does a reader find this in the file whose name owns it?

Do not fire on: blocks or headers the PR creates; a constant above its first user; re-spelled declarations; duplicated stanzas (check 18); check 12's owner question; PRs under 51 lines.

Finding shape: "Nit: `<symbol>` (<file:line>) sits in <header>, about <topic>; maybe `<candidate>`?"

Severity and precedent: nit ("just a nit" 3405003751). n=6 comments over 3 PRs (tron-1980, tron-2176, tron-2980), 2026-02-03 to 2026-06-12. None attributed.

### 25. Behavior change presented as a refactor, cleanup or debug-value revert

Trigger: a hunk in production code (h/, src/), unexplained in the body: same-type expression swap; removed NaN check beside a new tolerance helper; commented-out sleep, wait or assert; changed threshold constant; build default flipped, comment unchanged.

Procedure:
1. Pre-filter hunks (procedures.md).
2. At HEAD read both definitions, the NaN return or every reader. Name an input on which the old and new code differ.
3. Grep the diff for a re-added call and the body for both spellings.

Question: on which input do old and new differ, unstated in the body?

Do not fire on: a body or in-hunk sentence naming it; a stated change with a fatal reader; re-added call (check 23); bare literal or stale message (check 13); `#define` flip (check 16); belonging (check 10); test-row NaN rule (check 1). A commit message alone never clears this check.

Finding shape: "`<file:line>` changes `<old>` to `<new>`. So on <input> it now <behavior>; the body omits this. Was this intentional?"

Severity and precedent: never blocking ("was this intentional?", 3463061252). n = 5 comments over 5 PRs (1997, 2176, 2698, 2766, 3016), 2026-02-06 to 2026-06-23.


## Checks on code: lifetime, concurrency, cost and observability

The checks for the FPGA attention, DMA and scheduler code he reviews most (44 comment memberships). They trace who still reads a buffer, which set a wait covers, what a lock guards, and what a new path costs per token.

### 26. Count, index or completion wait must cover its set

Trigger: added h/ or src/ lines: a runtime count indexing a fixed-capacity array, a `break` after a caller-read count was set, a one-branch sentinel out-value, a `get_device(0)` wait after a per-device loop, or a literal `[0]` device choice. A body or comment sentence about a [0]-read count belongs to check 6; this check owns the code line.

Procedure:
1. Read the array's CAP (compile-time capacity). `git grep` the count writers for a prior assert.
2. Read loop exits and sentinel branches. `git grep` their consumers.
3. Read the per-iteration callee and the wait definition (what the completion check reads).
4. Grep tp2/tp4 (multi-device) aliases in common.hpp and replies for a written deferral.

Question: Does this count, index or completion wait cover exactly the set it stands for?

Do not fire on: asserted counts; count-resetting exits; exits leaving no stale count (check 27, b); last-handle waits (PR 1722); consumer-tested sentinels; written deferrals; token-index waits (check 28); capacity-less containers (check 31).

Finding shape: "`<count|wait>` at <file:line> misses <member>. As is, `<caller>` reads the wrong value."

Severity and precedent: normal, unlabelled. n = 8 comments over 4 PRs (2011, 2233, 2287, 3008), 2026-02-10 to 2026-06-18, attributed (3002297607, 3437517809).

### 27. Silent fallback where an assert belongs

Trigger: new production code that (a) clamps a shape or index, (b) exits silently on an index a callee asserts, or beside a "tests" comment, (c) guards self-move, (d) tests a sentinel before a device command, (e) spins unbounded, (f) asserts a shape parameter without `{}`.

Procedure:
1. Run the procedures.md greps.
2. Grep the limit and next callee for TRON_ASSERT (project assert) or a bool screen.
3. Grep who clears a spun-on flag; count assert placeholders.

Question: Can a bug-free caller reach this? If not, why not assert, naming the value?

Do not fire on: feature switches, planner filters, chunk bounds; count-constant failure value (check 13); wait primitive (check 18); stale-count exit (check 26); test-only helper parameter (check 21); "just defensive coding" (2825161209).

Finding shape: "should we just assert this? `<guard>` <clamps|returns|spins>, but <callee> asserts (<file:line>). A wrong <value> quietly <truncates|goes uncounted|hangs>."

Severity and precedent: normal (hidden wrong value), minor (spin, message), question (possibly defensive). n = 8 comments over 7 PRs, 2026-01-08 to 2026-09-28, attributed (3342904643).

### 28. Shared state: new thread, misplaced lock, double read, or dropped wait

Trigger: added h/ or src/ lines that (a) parallelize a BASE-serial call; (b) add a mutex away from its member; (c) add atomic plus plain members one function writes; (d) read an atomic getter twice; (e) narrow a readiness predicate (attributed: assistant text pasted by Wade in 3970590653).

Procedure:
1. Grep the diff for parallel_for (the pool loop), mutex, lock_guard, atomic, _needed.
2. Read each callee body and owner header. List the written members and their locks.
3. Grep every acquirer and other mutator. Split the mutating call from the wait.

Question: which thread writes this state, which reads it at HEAD, and does the lock, atomic or wait live in the owner?

Do not fire on: a mutex whose comment names same-file state; thread_local objects; atomics matching cross-thread readers (3406007619); repeated plain-accessor calls (check 22 (d)); memory order.

Finding shape: "I assume you lock `<mutex>` for the entire loop because someone could update `<structure>` during the gather?" (2983867856).

Severity and precedent: normal. n = 6 comments over 5 PRs, 2026-03-24 to 2026-09-09. One member (3970590653) is a disclosed assistant paste; the sentence built on it is marked attributed.

### 29. A buffer's lifetime and alignment follow its consumer

Trigger: an added line frees or submits a DMA buffer (DMA: hardware copier), reserves a literal beside a held reference, or hands SIMD (single-instruction-multiple-data vector code) an unaligned array.

Procedure:
1. Grep added lines for free, submit and destructors. Classify the drop paths (wait, leak, free). Count the copies of the commit-then-push ownership handoff sequence.
2. Grep literal reserves, held references and growth calls. Trace each to the next read.
3. Grep the consumer overload for aligned intrinsics, compare element alignment, and grep t/. Run UBSan (the undefined-behavior sanitizer) or write `Insufficient data`.

Question: after the free, submit or reallocation, who reads it, and is it aligned for the consumer?

Do not fire on: never-freed buffers (PR 1722); PR 2906 machinery (Note reworded, 3350285744); unaligned consumers; no literal reserve (PR 4353); wait sets and readiness predicates (checks 26 and 28); `alignas` literals (check 13).

Finding shape: "`<buffer>` freed at :<n>. `<reader>` reads it. Fix: <release unless completed | alignas(<CONST>) like <sibling>> and a real-consumer test."

Severity and precedent: "Nit" (3120788282); "Fix:" (3960506641); "Top robustness item" (attributed: assistant text pasted by Wade in 5498556672); n=6 comments over 3 PRs (2499, 2906, 4128), 2026-04-21 to 2026-09-08. 5498556672 is the only disclosed paste among them; 3960506641 carries no disclosure.

### 30. Avoidable per-call work on a per-token, per-layer or spin path

Trigger: a new production line allocates, zeroes, sorts, re-gathers, re-asserts, precomputes before a wait branch, or frees at zero count, on a spin (atomic re-read), layer, token or poll path.

Procedure:
1. Grep the diff for the patterns, then their callers. Classify the loop.
2. Count calls from loop bounds, with units.
3. Read how the sibling or BASE avoids it.

Question: does every call do work the sibling or BASE avoided, unneeded in the common case?

Do not fire on: startup, teardown, t/, once-per-forward code unless BASE allocated nothing, containers sized after the empty check, live-transfer frees (check 29), second container walks (check 18, 4029533521), wrong-key per-token folds (check 31 (c), 4125033686). Before/after capture: a question, only when memory is traded for repeated work (4607543703 is owned here; check 32 asks only for a sample image or trace path).

Finding shape: "`<fn>` runs <count> per <path>, doing <work> every call where `<sibling>` avoids it. So <consequence>. Should we <remedy>?"

Severity and precedent: nit (3350064944); normal with the count (3907183627, 3907185740); minor, not blocking, rebuild-after-free (4674512577). n = 4 comments over 3 PRs, 2026-06-03 to 2026-09-01, attributed.

### 31. One owner per record, one gate per subsystem, one stable row key

Trigger: (a) a published record (struct exported whole) written from two layers; (b) a call outside its subsystem's configure guard; (c) a cumulative table keyed by a per-forward offset, or its key spelled twice; (d) a class or budget from one whole-forward predicate.

Procedure:
1. Grep the diff for atomic record-member writes. Note the writer and the layer.
2. Grep HEAD for each writer's production callers and each gated call's guard.
3. Compare table size, index formula and leaf names. Read compute_forward_args (the scheduler function in full.hpp that builds each forward pass's per-token arguments).

Question: who owns this record, is every call guarded, does the key name one thread every forward?

Do not fire on: scoped ownership; counter with reset (3406007619); per-forward table; README-named limitation; zero-caller clear (check 14); correct-key fold (check 30); two-variable gate (check 18).

Finding shape: "Any other caller of `<inner>` gives `<field> == 0` next to nonzero `<field>`" (4125033653); keys: "Design question on".

Severity and precedent: "Consider", "Design question", "Nit:" (4147010638), endorsement (2948090978). Never blocking. n = 6 comments over 3 PRs (tron-2176, tron-4128, tron-4596), 2026-03-17 to 2026-09-30. Comment 3907185740 follows an assistant disclosure (5498556672).

### 32. New path, state, counter or option visible through existing operator tools

Trigger: the diff adds members unprinted by their type's debug_string (print helper); a lock-held loop in a src/ file whose siblings lack TRACE_EVENT (Perfetto's macro); a build-gated exit-time counter outside FUSE (live counter files); a new runtron option that the perfetto/tronperf launcher script does not forward; a perfetto::Category, TRACE_COUNTER (Perfetto's counter macro) or memory-for-work trade with no posted image, repository path or before/after figure.

Procedure:
1. Grep each added member in the helper body.
2. Count TRACE_EVENT per sibling. List the loop-under-lock functions, not register_/init_/setup_.
3. Grep the diff for option(TRON_ and exit reports, the launchers for both flags, and the body for images, paths and figures.

Question: can an operator see, measure or switch on the addition via debug dump, Perfetto, FUSE (live counter files) or launcher, without rebuilding?

Do not fire on: FUSE-registered counters; environment variables; merge steps; -detail promotions (check 16); machine-local paths (check 9).

Finding shape: "add these to the `debug_string` utility for printing?" (3405051930).

Severity and precedent: nit; "No action needed, just inquiring." (3235915961); PRs 4267, 2713 approved regardless. n = 6 comments over 6 PRs, 2026-05-13 to 2026-08-12.


## Checks on tests

Checks 1 to 5 keep their 2026-10-05 text. The widenings from the whole record are appended under each. Test files receive 11 percent of his inline comments.

### 1. Value-pinning rows, fixture placeholders and opaque literals need a consumer or provenance

Trigger: (a) an expected literal differs from the written bits by conversion or rounding; (b) a t/ hunk assigns an uncommented round literal to a parameter-struct field; (c) an equality assertion expects an unexplained digest or table.

Procedure:
1. (a) Grep h/ and src/ for a reader of these bits.
2. (b) Grep the hardware callee, not the stub src/pos/fake.cpp, for field reads. A field that is unread and unequal to the producer's value is a placeholder.
3. (c) Read the comment block above for generator, date or revision. Grep docs and AGENTS.md for a register.

Question: what depends on this exact value, or where did it come from?

Do not fire on: Note-cited or format-pinned rows; read, producer-equal or commented fixture literals; authority-lined constants; golden-lookup digests; removed isnan checks (check 25); surviving NaN scrubs (check 34 (workaround tracking)); fake-boundary/shared-helper assertions (3A, 3B).

Finding shape: "This row makes "a float NaN stores as +inf" a tested contract." (4188336250).

Severity and precedent: no severity word, non-blocking (4188336250, 2948257220, 4020335622). n = 3 comments over 3 PRs (tron#2176, tron#4557, asim#244), 2026-03-17 to 2026-10-05.

### 2. Structure-only compile-time checks

Trigger: a test hunk adds a STATIC_REQUIRE, STATIC_REQUIRE_FALSE or static_assert.

Procedure: split by what the expression names, not by whether it is true.

- A boundary probe calls, inside a requires-expression (the C++20 construct that tests whether an expression compiles), a production function declared outside the probed type's own header (a kernel, a free function, a member of another class). Keep it.
- A shape check names only the probed type: a type trait, sizeof, alignof, or a requires-expression whose body calls only the probed type's own members or their absence (an accessor on a temporary, a write through at(), a missing operator).
- For each shape check: (a) search `h/` for the same trait on the same type or on an enclosing type that holds it as a member, resolving aliases; (b) check whether the probed type's own declaration already fixes the trait (alignas, `= delete`, an array member). Either one makes the check a repeat.

Question (shape checks only, never asked of a boundary probe): if this assertion flipped, which production line outside the probed type's own header would misbehave, and is that line not already protected by a declaration or static_assert in a header?

Do not fire on:

- boundary probes.
- trait probes that spell the PR's stated type-safety contract (a bare pointer or the other layout's view is not constructible). Treat them as boundary probes. A positive constructibility probe on an alias belongs to check 6.
- a trait that production code relies on, and that no declaration or header fixes. The finding is then "move the static_assert into the header", not "drop the test".

Severity and precedent: a question with the probes named as the ones to keep; n = 1 comment (4188336302, PR 4557).

Finding shape: "The kernel probes are the PR's real contract. These only document structure: <list>. <N> checks repeat header assertions: <test line -> header file:line, each>. Keep the probes and drop the rest."

### 3A. A test must run, reach its assertion and observe the defect

Trigger: a test adds a runtime assertion that compares stored bytes or indices with a literal table or a formula written out in the test. Between the start of the TEST_CASE and that assertion stands a runtime exit (`return`, SKIP, WARN plus return, where SKIP and WARN are Catch2 macros) conditioned on a hardware or environment probe (`available()`, a cpuinfo flag, FPGA presence, getenv). Test selection labels in t/CMakeLists.txt (min_slices_N) are a separate gate. List them under selection.

Procedure:
1. Record every early exit above the assertion and its condition.
2. Check whether any statement between the exit and the assertion executes the probed instructions. For `available()` that means a call into the AMX kernel namespace. AVX-512 (the vector instruction set every runner has) intrinsics do not count.
3. For each lane that can run the binary, record its trigger and whether its configure line sets the build flag the TEST_CASE needs. On a lane where the flag is off, the whole case is compiled out.
4. On a lane where the flag is on, check whether every runner the job can land on passes the probe (README.ci.md runner table).
5. Find the oracle of the assertion. If a production accessor of the same storage produces the expected side, both sides share the helper.
6. List every other non-gated assertion on the same storage and classify it. An independent formula substitutes. A route check through the same helper never does. A second reader with its own address arithmetic substitutes only when it covers both parities and a pair beyond the first.

State four separate facts: (1) the target compiles on the lane, (2) the test case is selected, (3) the assertion is reachable on the runner, (4) a log shows the path executed. If runner capability or a log is unavailable, write `Insufficient data` and name it.

Do not fire on: an assertion that consumes a kernel output produced above it, when a non-gated independent assertion covers the same contract elsewhere (name it).

Finding shape: "This is the only check of <contract> against a formula that does not go through <helper>, but it sits after the <probe> early return at :<line>, so it does not execute on <lane or runner class>. The <other section> does not cover it: both sides compute their address through <helper>. Move it above the early return, or into <closest non-gated test>."

Widening from the whole record (2026-10-06):

Trigger: in t/, (a) a formula assertion below a probe exit; (b) an added `return;` under TEST_CASE with REQUIRE lines below it; (c) a tag gaining a leading `.` (a hidden tag: Catch2 leaves the test out of a default run); (d) a count assertion behind a discarding fake (a fake is the test stand-in for hardware in src/pos/fake.cpp; a discarding fake drops what it is given, a recording fake keeps it); (e) an added fixed path reread, never removed.

Procedure:
1. BASE = merge-base(HEAD, PR base.sha).
2. Map added exits and tags to HEAD; owner line; REQUIREs below.
3. Follow (d) calls into src/pos/fake.cpp; pair (e) writes with read-backs.

Question: were the code wrong, which assertion fails on the gating lane, without hardware, on a second run?

Do not fire on: a covered gated assertion; a hidden tag at BASE or explained; fpga/DISABLED binaries; a recording fake; `return;` under `if constexpr`/helper; a writer at BASE; a run as remedy (move the assertion; missing run: 3B).

Finding shape: the fact and its line, then "so it skips on <lane>", then the move. For a fake, say what "would still pass" (3960538177).

Severity and precedent: no 'nit'. Questions, non-blocking, except form (d), which opens with 'Coverage gap:' and asks in the must-change form 'Please extend an existing CI suite' (3960538177). n = 5 comments over 4 PRs (tron 1920, 2011, 4128, 4557), 2026-01-28 to 2026-10-05.

### 3B. A run on the changed path is named at the reviewed head

Trigger, all three: (1) the diff changes h/pos/, src/pos/, h/tron/scheduler/, self_attention.hpp, a production constant, or a macro region whose `#else` twin reads the hunk's writes; (2) no ctest (CMake's test runner) success row at HEAD; (3) the PR's test statement misses it.

Procedure:
1. Read the GitHub check runs (the per-commit CI job list) at HEAD; find the job with the ctest step.
2. Grep changed files for `#if` (regions, twins) and t/CMakeLists.txt for `pos` binaries.
3. Grep body, commits, comments, bot findings for test statements; with a host, paste the run (4131374395).

Question: Which run, by configuration and commit, executed the changed path at HEAD, and where is it stated?

Do not fire on: no test statement; untested paths (check 33 (b)); lane sentences (check 7); older-id runs (check 8); formatting-only hunks.

Finding shape: "please run at least a subset of representative UTs against these changes before merging" (4265644124; UTs: unit tests).

Severity and precedent: a question, or a condition attached to an approval ("please run at least a subset of representative UTs against these changes before merging", 4265644124, is one of his four must-change forms). n = 5 comments over 4 PRs, 2026-03-11 to 2026-05-11; 4131374395 attributed, ctest paragraph Wade's own.

### 4. Same experiment run twice, or run in a new place

Trigger, all must hold:
- the PR adds or widens two test units (TEST_CASE, SECTION, GENERATE arm, template instantiation), or one new unit plus one it widens;
- both make the same production call as the operation under test;
- both feed it the same GENERATE list or named constants, the same token or size set and the same source value type;
- both reach the same leaf branches of a function the diff changed.

A commit that answers several gap items at once raises the priority of its units. A comment claiming "covers N cases" is a separate nit.

Procedure:
1. Name the production call of each unit.
2. Follow it to the leaf function with branches the diff changed and map every input (each GENERATE value, each token index) to the arm it reaches.
3. Simulate the unit's write order: a slot counts as observed only if no later write in the same unit replaces it before an assertion reads it.
4. Record for each unit the set of (branch, slot, reference, precision, read path) its assertions observe.
5. Compare pairwise, among the triggered units and any pre-existing unit on the same call that the PR widened with new assertions.

If every break that fails A also fails B, drop A. If some break fails only A, name the (branch, slot) pair only A observes, give B that observation with one concrete edit, then drop A. Do not report the pair as complementary and leave both. A full-page copy can overwrite a partner slot before the assertion reads it. That is how a larger unit can observe less than a smaller one. Prefer small cases that keep the observation over either a redundant matrix or an unjustified deletion.

Do not fire on: units that feed different source value types or different token sets; units that make different production calls; a pre-existing unit changed only in API spelling; units under different build or hardware gates (then the finding is check 3A).

Finding shape: "`<unit A>` and `<unit B>` (line <N>) run the same <inputs> through <call>, reaching <branches>. <B> already checks <what, against which reference, through which read path>; this one adds <nothing | the (branch, slot) pair B overwrites before reading>. The test policy rules out duplicate coverage that protects no distinct behavior: <drop this one | extend B by <edit> and drop this one>."

Widening from the whole record (2026-10-06):

Trigger: A: two added units make one call with equal inputs and reach the same branches. B: unit B REQUIREs the pairs unit A asserts on a branchless function, then an effect. C: a new registered t/*.cpp calls a function an existing binary already reaches, even via a constructor.

Procedure:
1. Grep the diff for added units and calls.
2. Read the leaf function's branches.
3. Read both units at HEAD; list observations.
4. C: grep t/ for the function and aliases; read both registrations.
5. Date body cost passages; ask to measure.

Question: Which break fails A but passes B; which binary already runs it?

Do not fire on: different inputs, calls or gates (check 3A); API re-spelling; abort cases; a binary needing a library, a lock or a MODEL_REQUIREMENTS entry (the add_catch_test property in t/CMakeLists.txt that lists the model files a test needs); registration-only edits (tron-2844).

Finding shape: "This one adds only the arithmetic of a one-line function, so it could be dropped." (4146998951)

Severity and precedent: none, "Nit:" or a question (3970127694); n = 3 comments over 3 PRs (#4265, #4596, #4557), 2026-09-09 to 2026-10-05.

### 5. Test name, tags and result print agree with assertions and file convention

Trigger (any): (A) a test body's assertion, comment or stimulus changes while the name keeps its verb. (B) a new unit's tags break the file's convention. (C) an unguarded counter print precedes a zero REQUIRE; siblings are guarded.

Procedure:
1. Grep the diff for test macros; units at BASE are moved.
2. (A) Read setup and REQUIREs; grep the name in header and PR body.
3. (B) Tabulate name and tags at HEAD.
4. (C) Grep sibling summary prints with the line above.

Question: does the label describe the passing state and match its siblings?

Do not fire on: a verbless label; pre-existing tags; a hidden `[.name]`; no shared tag count; an unasserted print; unconditional siblings; fixture-versus-production comments (check 27, silent fallback).

Finding shape: "Nit: the section is still named '<name>', but it now asserts that <opposite state>" (4188336324), or a suggestion block and question (2620236334).

Severity and precedent: "Nit:" for A, none for B and C, never blocking; n = 3 comments over 3 PRs (tron#1666, #2078, #4557), 2025-12-15 to 2026-10-05.

### 33. A changed path needs a test through its production entry

Trigger: (a) new h/ (headers) type with state, invariant Note, no t/ (tests) hit; (b) changed branching function F on a production chain to added code, no t/ hit within three caller levels; (c) changed field formula mirrored in untouched t/; (d) unexplained test accessor swap.

Procedure:
1. Changed functions: added definitions plus each hunk's enclosing function, never `@@` text.
2. Grep t/ per name; walk callers three levels, callees to the first t/ hit; read that TEST_CASE.
3. Grep t/ for the field or accessor; substitute locals; grep body, commits.

Question: Which test enters the changed code at its production entry, and which assertion fails if wrong?

Do not fire on: other missing tests; names in existing headers; merged-branch code; equivalent formulas; element respelling; fake paths (check 3A); run statements (3B).

Finding shape: "Please extend an existing CI suite" (3960538961), naming what wrong behavior would still pass; observed bugs separate.

Severity and precedent: normal. The finding shape 'Please extend an existing CI suite' (3960538961) is one of his must-change forms; the other members are questions. n = 4 comments over 4 PRs, 2026-01-28 to 2026-09-08. Attribution of 3960538961 is Insufficient data.

### 34. A workaround for an unexplained defect needs a tracked exit

Trigger: an added comment, commit or body calls code a workaround for an unknown cause; a test unit the diff adds or widens guards a workaround; a commit retires a helper for a hardware version while a sibling survives in t/.

Procedure:
1. BASE = merge base against the PR's base branch. Grep added lines, commits and body.md (the PR body saved in Setup step 1) for workaround words.
2. Grep each hit's 31-line window (15 lines above and below), adding commit and body for a tracker id.
3. Read the guarding test header for a consumer or TODO.
4. Grep surviving siblings and `TRON_*_WORKAROUND` gates.

Question: temporary or permanent? Which story tracks it? The id goes on a TODO line, not in a Note (check 9, the code-comment part).

Do not fire on: workarounds that name their defect (3036997452); id-less TODOs; unwidened units; an id in a Note (3350285744).

Finding shape: "`<function>` (<file>:<line>) works around an unidentified bug: do we have a ticket/story tracking this?"

Severity and precedent: plain question, never blocking; nit for obsolete helper (2948238427). n = 3 comments over 2 PRs, 2026-03-17 to 2026-05-12.


## Checks on claims and the PR body

Checks 6 to 9. Wade read the body against the code only on PRs 4557 and 4596. Before that, his body comments were "stale after the review rounds" (5371062950) and mislabeled options (5106398334).

### 6. Claim wider than the code: guarantees, timed paths, element counts and defaults

Trigger: a body, commit, Note or doc sentence claiming (a) a compile-time type guarantee, (b) a timer or counter's scope, (c) a [0]-read container's count (the sentence; the code line itself is check 26), or (d) a twice-stated default; one subject per row.

Procedure:
1. (a) Resolve types through every `using`; grade explicit, pointer constructor, distinct class.
2. (b) Per path list selector, wait, stamps: start, stop or untimed.
3. (c), (d) Grep the count sentence and growers, or literals bound to the setting.

Question: Which line reaches each subject's claim, and does the sentence say where it stops?

Do not fire on: stated limitations; loops over every part; .back(), arrays, strings, tests; an OFF-path `#define S 0` (ask instead of reporting); stale messages (check 13, 3350031805); CI sentences (check 7); a default stated twice (check 22); misnamed flags (check 17, 5106398334).

Finding shape: "`X` is only <timed | enforced> at <file:line>; '<claim>' holds for <subject>: widen code or narrow text."

Severity and precedent: "Fine as a first step" (4188336267); questions for (c)-(d); never blocking. n = 4 comments over 4 PRs (tron 2713, 3093, 4557, 4596), 2026-05-12 to 2026-10-05.

### 7. CI claims name the lane, the trigger and the configure line

Trigger, all parts:
- a sentence in the PR body, a README hunk or a comment hunk has a CI subject ("CI", "the required checks", "the build job", "the nightly", a workflow name);
- it asserts a setting or coverage (a CMake option, a preset, a platform feature, "AMX-on/off");
- it is not about a build the author made (a named tree, machine or runtron (tron's command-line tool) arm is a measurement statement).

Also a reviewer comment that cites a workflow file:line as proof of what gates the PR, and a PR number offered as the date a setting changed.

Procedure:
1. List every file under `.github/workflows` and the keys of its `on:` block.
2. For every file with none of `push`, `pull_request` or `merge_group`, find its callers and quote the caller's `if:` gate.
3. Find every place the setting lives (`.github`, `nix/`, `flake.nix`, `CMakePresets.json`, `CMakeLists.txt` default, `GNUmakefile`, README.ci.md) and name each hit's consumer: a workflow `run:` line belongs to that job; a nix file belongs to the job whose `nix build` recipe imports it; a preset belongs to whatever runs it.
4. Get the gating set from `gh pr checks N --required` on a finished run (no row in progress or queued) and record each job's workflow name.
5. Date the setting per file with `git log -S` and map the commit to its PR.

A lane is named only by a workflow's `name:` string, its file name or a job name. "CI", "the required CI" and "the build job" are not lane names when the repository calls two lanes with opposite settings "CI".

Do not fire on: a sentence that names the lane and matches that lane's configure line; a generic "CI is green"; a runtime log or WARN string in code; a PR-label sentence that matches the documented label policy. README text is a claim to check, never evidence.

Severity and precedent: a statement in the review body; n = 1 comment (5420005787, PR 4557), where Wade's own CI citation was itself wrong about the gating lane (references/pr4557-misses.md).

Finding shape: "'<quoted sentence>' names no lane. The checks that gate this PR are <workflow name> (<configure file:line>, <setting absent or present, default>). <Other workflow>:<line> passes <setting> but has no push or pull_request trigger since <commit, PR>; it runs from <caller:line> on <gate>. The setting entered it in <commit> via PR #<n>."

### 8. Result rows, body sentences and the branch state match the reviewed head

Trigger: a result row in a results section; an author commit after the body's last edit; CONFLICTING at approval; a ported file; an open suggestion thread at a push.

Procedure:
1. BASE = merge-base of HEAD and the PR's baseRefOid.
2. Hex ids in those sections: cat-file, is-ancestor, files changed since.
3. Body edits (GitHub userContentEdits); grep later commit subjects' identifiers and TEST_CASE counts at HEAD.
4. gh mergeable, else `git merge-tree BASE HEAD baseRefOid` markers; diff a ported file against its source head; grep open suggestions' original lines at HEAD.

Question: Do result ids, touched sentences, merge state, ported file and suggestions match HEAD?

Do not fire on: commit tables; BEHIND with a clean merge-tree; a ported copy lacking source symbols or differing as the body states; agreed follow-ups; bot threads.

Finding shape: "I think your PR description is stale at this point" (5371062950), followed by "<clause> is now <value>". A merge conflict is reported in the same shape.

Severity and precedent: ask or approval clause, never blocking; n = 5 comments over 5 PRs, 2026-03-27 to 2026-10-05.

### 9. Passages a later reader cannot use: PR-body sections, code comments and Notes

Trigger: the PR body has a Status, Verification, Tests or Results section. A heading at any level whose text contains one of those words starts a section. The section ends at the next heading of the same or a higher level. The procedure runs only inside those sections.

Procedure:
1. Grep for wall-clock times, machine-local paths and log names (`/var/tmp/`, `/home/`, `*.log`), and count reconciliations between two revisions ("N fewer assertions than at X", "4 + 8192 = 8196").
2. A dangling id that labels a result goes to check 8, not here.
3. For each remaining hit ask the reader test (question 9: would deleting it change a decision about the head, or cost a reader with only the code a fact the code must honor?).
4. Bins: wall-clock times (keep the date only), machine paths and log names (delete), reconciliations against an earlier revision (delete; keep at most the one sentence "no production assertion was removed").

Do not fire on: a commit id plus a date that identifies the binary a result came from; the pass or fail outcome and the counts at the head; a path inside the repository; a duration stated as a number with units when that number is the claim ("TTFT 53.1 s"). A clock-time range is never a measurement.

Finding shape, once per section and phrased as an ask: "PR description, <section> lines <a>-<b>: the build timestamps, the log path on <host> and the <X = Y + Z> reconciliation against <sha> can go. Keep the rc/outcome clause and one result row per test and tree with the commit id and date."

Widening from the whole record (2026-10-06):

Trigger: a diff comment carries a review label, a tracker id (h/ or src/), a new `// Note [name]`, or links this PR's Note to a trace, log or assert.

Procedure:
1. grep added comment lines for labels and ids per file.
2. Reread each hit without the reference; keep only facts.
3. grep a new Note for story words (NaN, crash, bug) the body repeats: history; ask for five lines at the cited declaration.
4. git grep the statement's tokens at BASE; all present: drop the comment only.
5. Recheck HEAD.

Question: in two years, with only the code, does deleting this lose a fact the code must honor?

Do not fire on: titles or commit subjects; a mechanism Note or its cites; a tracker id under t/ or on a workaround TODO.

Finding shape: "probably don't want to reference 'PR review round blah comment blah' like this" (4146947611).

Severity and precedent: minor ("Scrub please", 4146959502), never blocking; n = 5 comments over 3 PRs (2906, 4007, 4596), 2026-06-03 to 2026-09-30.


## Checks on scope, history, ownership and automated findings

Checks 10 to 12 keep their text, plus the cross-references to the new checks added on 2026-10-06. Check 35 covers the one process habit the record shows in 14 comments over 11 PRs: he verifies a bot finding before endorsing it.

### 10. Hunk-to-claim trace (unrelated, unexplained or merge-dropped changes)

Trigger: always. Cost: one `git log`, one `git show` per commit and one grep of `BASE:FILE` per hunk. Highest priority when:
- a commit's author differs from the PR author;
- a commit message or the body cites another PR number or says "folded", "stacked" or "fast-forward";
- a commit subject starts with Name, Rename, Brace, Clean up, Shorten, Clarify, Reword or Tighten;
- a commit adds tests after a review round.

Procedure:
1. Write the identifier set: every backticked type, function, constant or Note title in "What changes", plus every name declared at namespace or class scope in a file the diff creates, minus any name that exists at BASE. Confirm each with `grep -c` over the diff.
2. Bin commits: SIDE when the subject starts with one of the verbs above, or the commit changes only tests or comments, or its author is not the PR author; MAIN-FEATURE when the subject contains an identifier from the set verbatim; otherwise SIDE.
3. Scan the hunks of every non-merge commit, SIDE first; a MAIN-FEATURE commit can carry a side hunk.
4. A hunk is a candidate when at least half of its removed lines exist verbatim at BASE, at least one of them is not blank, brace-only or comment-only, and its added lines contain no PR identifier.
5. A candidate in the same function or TEST_CASE as a hunk that carries an identifier inherits that hunk's status.

Clear a candidate only if: the PR's functional change rewrites the same statement (the removed line with the rename map applied equals the added line); a GitHub review thread of this PR asked for it (cite the id; an author-side agent review is not a reviewer); or a body sentence describes the hunk's added content. A sentence that only names the file or the callee does not clear. A sentence that says the opposite is quoted as a contradiction.

For a test hunk that is a candidate: name the callee. If the PR does not touch the callee, the hunk is unrelated. If the PR rewrote or moved the callee, the hunk is a regression guard; report at most a body gap ("the body never says <callee> keeps <contract>"), never "unrelated". A row inside a TEST_CASE the PR created is never a candidate here.

Do not fire on: a removed/added pair that differs only by the rename map; hunks whose removed lines are absent from BASE or comment-only; a cleanup the title or "What changes" lists as bundled; a hunk that leaves a symbol, include or parameter with no consumer (check 14 owns it; check 10 asks only whether the hunk belongs); a #define flip (check 16), a commented-out statement (check 23) or a commented-out wait (check 25): those checks own the hunk.

Finding shape, one per hunk: "<file>:<lines> (commit <id>, '<subject>') changes <N> lines that exist at BASE and that <feature> does not touch: <what it does>. Reverting it alone keeps the body true (<body line> says '<sentence>') and nothing the PR introduces stops compiling or being tested. Not part of <title>; please split it into its own PR."

Widening from the whole record (2026-10-06):

Trigger: always; code hunks (removed lines at BASE, no PR identifier added) and: (a) deleted or renamed files the body never names; (b) removed comments naming an outside reader (packaging/CMake); (c) merge lines from no source, or lines a merge dropped; (d) CMake hunks adding compile options or `-m` flags.

Procedure:
1. Grep deleted/renamed file stems in body.md and log.txt (the branch log saved in Setup step 1).
2. Grep removed comments for reader words; `git log -m -S` finds the dropper.
3. Grep added lines in source tips; keep pure removals of `diff -U0 M^2 M` (M: merge).
4. Grep sibling CMakeLists.txt for the flags.

Question: reverted alone, is any body sentence false, and what is its origin?

Do not fire on: rename-map pairs; lines absent at BASE; items the body or a sibling target explains; test accessor swaps (check 33 (d), 2737853978); a one-line swap's behavior (check 25); includes, literals (other checks).

Finding shape: "<file>:<lines> (commit <id>) <deletes|removes|adds what>; <fact>. Was this intentional?"

Severity and precedent: questions (3197414598), then approval. n = 4 comments over 4 PRs, 2025-12-18 to 2026-09-09.

### 11. Commit history is reviewed content

Trigger: run on every review, at every push after a review round and at the final head. Confirm how the target branch lands PRs with `git log --first-parent -20 origin/main`. If that log shows merge commits, branch commits are permanent history.

Procedure: bin each non-merge commit.
- OTHER-AUTHOR: author differs from the PR author (keep as its own commit).
- FIXUP, both conditions: the hunks show no behavior change (comment, whitespace, brace or name-only edits, or an exact return to main's behavior on a path an earlier commit of this PR changed), and every removed non-comment line was added by an earlier commit of this PR.
- UNRELATED: a check 10 finding (excluded from the squash units, reported there).
- TOPICAL: the rest.

A subject prefix alone never bins a commit. A CLUSTER is two or more FIXUP commits whose subjects or bodies name the same Note title, or whose diffs touch overlapping line ranges of one file at HEAD. Give both counts at HEAD (`git rev-list --count` with and without `--no-merges`) and, when answering a posted review, the with-merges count at the last push before the review.

Report a finding only for a CLUSTER or an UNRELATED commit. A long history with neither gets at most a one-line note: Wade approved PR 4596 on 2026-09-30 (5371062950) at 26 non-merge commits without a squash request. Never raise above hygiene, and never make the finding a condition of approval. A review-round commit later than the body's last edit also triggers check 8. Report the stale body there and the cluster here. Precedent: one squash request in 334 reviews (5420005787) and two rebase asks; PR 4596 was approved at 26 non-merge commits.

Do not fire on: a target branch that squash-merges; a draft PR or an author who wrote that a squash is pending (judge the PR state, not a word grep); a merge commit; another author's commit; the commit table in the body (check 9).

Finding shape: "Commits: <N> (<M> merges, <K> without) at <head>, <k> of them rewording <Note> (<ids, oldest first>). Please squash into <one unit per body heading that names a code change>; keep <every other-author id> as its own commit."

### 12. A shared-header change no test observes needs a named owner's acceptance

Trigger, both halves. Placement: the hunk adds or changes a definition at global namespace in any header (operator new/delete overload, free function, macro, inline variable, struct), or adds non-comment lines to a header under h/system, h/pos, h/common or h/tron/hardware. Unobserved guarantee: a comment, Note or commit message of the hunk says a revert is undetectable ("no test fails if", "nothing can catch", "behave the same either way"), or every test on the path observes a by-product (alignment, non-null) and not the mechanism. A commit-message hit is attributed to the files that commit changes and tested per file.

Procedure:
1. Find global definitions by walking the header with a namespace depth counter and reporting added lines at depth zero that are not blank, comments or directives.
2. Count includers: direct (files under h, src, t, bin, ingest whose `#include` names it) and transitive (closure over `#include` lines); report "N direct, M transitive of T".
3. Classify the hunk's origin: owner-authored PR; fast-forward fold (`gh api repos/<org>/<repo>/commits/<sha>/pulls` lists another PR and the commit sits on the first-parent line with no merge commit of that PR); merge; side commit.
4. Owner set: authors of the file at BASE by recency, plus every requested reviewer of the PR with a commit on the file (map logins to authors with `gh api users/<login>`, then by email local part).
5. Read every PR comment on the file by an owner and class it: placement accepted (names the symbol or the header and says keep, fine, agree, LGTM, go ahead), diagnosis agreed, or wording only. Only the first counts; an APPROVED review by an owner at a head that contains the hunk also counts.
6. A comment counts only if its `original_commit_id` contains the introducing commit (`git merge-base --is-ancestor`; GitHub rewrites `commit_id` to the latest head for comments that are not outdated). Use dates only to say that a reply cites a commit older than the thread it answers.

State what the tests cannot prove: a fake that provides the behavior the production path lacks proves nothing about the production path.

Do not fire on: a hunk the owner authored; a change in a PR the owner approved after it landed; a change a test fails on when reverted; comment-only hunks. Do not make every low-level change require new approval, and do not contact reviewers. The finding is the unposted question. Precedent: n = 1 (4188336279). Its stated reasons are the commit's origin (a fold rather than the owner's PR) and the line "nothing can catch a regression here". The placement half alone matches 57 of the 115 PRs in his record where he asked nothing, so both halves are required.

Finding shape: "<file>:<line> adds a global `<symbol>` in a header that reaches <M> of <T> files. Line <L> says no test fails if the mechanism is reverted, and the tests that call it check <by-products> only. It came in <commit> (<origin>), and the owner's comments on this file <agree with the diagnosis | ask for a reword>; none accepts the placement. Please get <owner>'s explicit sign-off on the approach."

### 35. Bot finding traced to the deciding line before any reply

Trigger: a cursor[bot] (automated reviewer) thread (unresolved, unanswered) on a C++ line the diff changes under h/, src/ or t/, or a reviewer-run agent review.

Procedure:
1. Fetch thread state (resolved, outdated, first author), bot bodies.
2. Bin: SENTINEL (`-1` default reaches a callee), UNREACHABLE, UNUSED, DUPLICATE-CONSTANT, CONCURRENCY.
3. SENTINEL: grep the initializer and every production constructor call.
4. UNREACHABLE: table the gate's states; read the title and body.
5. Others: owning check; a narrowed readiness predicate on shared storage confirms (attributed: assistant text pasted by Wade in 3970590653).
6. Verdict with the deciding file:line.

Question: which HEAD line decides the claim, and is it quoted?

Do not fire on: author reply (2879602159); outdated thread; numeric claim (2879962155); duplicate-constant claim (2948416014); the PR's stated goal (3659990818); optional forwarded agent items, never a blocker.

Finding shape: "false positive... `<member>` is initialized like this: <initializer file:line>".

Severity and precedent: none for a refutation; a confirmed claim is "a legit concern" (3156090573). n = 14 comments over 11 PRs, 2026-03-11 to 2026-09-09, attributed (3970590653, 4800935083).

## How Wade reviews and words a finding

Words used here: PR = pull request. Text = one Wade comment or review body with words (269 on 115 PRs he did not author). Id = GitHub comment or review id. Row = classified item (239 rows).

### Two registers (writing styles) by date

Register A, 2025-09 to 2026-08 (230 of 269 texts; the counts below use the 222 texts dated 2026-01 to 2026-08): short (29 words average), lowercase start (126 of 222), a question (105 of 222), a suggestion block for a one-line fix (41 of 43 blocks).

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

Nine of 269 texts disclose a paste from Claude, "CC" or GPT: 3002297607, 4131374395, 3342904643, 4674512577, 3437517809, 4800935083, 5498556672, 5544513215, 3970590653. Quote the frame sentence as Wade and the block as "assistant text pasted by Wade in <id>". His weight is the frame sentence, not the block. PR 4557 has no disclosure in its 10 texts. Its file:line citations, "So" consequences and "Please <verb>" asks match the disclosed-assisted PR 4128. So whether it was assisted is Insufficient data.

### What he rarely comments on

He does not comment on the C++ guide or kernel arithmetic line by line (0 of 269 texts each). He rarely comments on formatting or benchmark method: one text each, both a question or a wish, not an ask to fix. Treat these as never more than a nit, and only in the form the one precedent shows (checks 15, 30, 22 and 20 carry those single cases).

- Formatting: 1 of 269 (3778051701, a long Markdown line, as a question; check 15).
- Benchmark or measurement: 1 of 269 (4607543703, a wish for before/after metrics; check 30).
- Brace or indent: 1 of 269 (2976643305, a dead loop scope; check 22).
- Commit message wording: 0 of 269. Squash: 1 of 334 reviews.
- Expected values or tolerances in tests: 0 of 239 rows.
- CI workflow YAML: 1 of 243 inline comments (3580238651, a label spelling; check 20).
- Owner sign-off for a shared header: 1 of 115 PRs (4188336279).
- Running the test suite himself: 2 of 113 reviewed PRs.
- Security, licensing, Python style: 0 of 239 rows.

### Replying to Wade

- He concedes in writing after the author's fact: 2790148917 ("yeah, doh!"), 3102275102 ("Nevermind ;p"). An agent withdraws a nit the same way.
- He defers to the area owner (3277240111). Get that owner's written answer.
- He accepts "next iteration" (3405172585), so a declined preference gets one reason and a follow-up offer.
- About one in six substantive asks is declined and left unchanged (16 of 239 rows were pushed back by the author). Classify first: a must-change signal or a preference word ("nit", "trivial", "pedantic", "maybe").
- Answer a must-change with a fact at the reviewed head (file:line, commit id). Never write "LGTM", resolve a thread for him, or post without the author's approval.

## Report the result

- For each finding give the HEAD location, the check number, the fact, the consequence, the evidence (file:line and a short quote) and the smallest remedy. Write it in the register the check names (a short question for the code checks; fact, "So" consequence, ask for the claim checks).
- Separate correctness, coverage, description and preference findings. If a point is only a hypothesis, name the check that would resolve it.
- State the revision reviewed, which checks ran, which did not, and what evidence was unavailable.
- A review request authorizes analysis, not source edits, comment posting or history rewriting.
- Order findings by Wade's severity: a missing consumer, a wrong wait set, a race or a silent fallback before a typo or a name. Put typo and naming nits into suggestion blocks.
- Never emit CHANGES_REQUESTED or a bare LGTM in his name; a must-change is a sentence ("before merging", "needs", "Please <verb>").
