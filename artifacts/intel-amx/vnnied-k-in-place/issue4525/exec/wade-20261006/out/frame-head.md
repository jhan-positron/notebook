---
name: Wade-code-review
description: Review a positron-ai/tron pull request at its final head the way reviewer Wade does, before he sees it. 35 checks derived from his whole review record (115 PRs, 273 comments, 2025-09 to 2026-10). Code checks (dead symbols and includes, debug switches left on, comments that contradict code, magic literals, duplicated logic, type and initialization choices, names, silent fallbacks, index and wait-set mismatches, lock placement, buffer lifetime, hot-path cost, instrumentation ownership), test checks (value rows without a consumer, hardware-gated or silently skipped tests, duplicate coverage, test names, tests that bypass the changed path, workaround tracking), claim checks (guarantees wider than the code, CI lanes, stale result rows, PR-body passages, stale descriptions), and scope checks (unrelated hunks, fixup clusters, shared-header ownership, bot findings). Use before requesting review, after every review round, when replying to Wade, and whenever the PR body or commit history is part of what he reads.
---

# Wade-code-review

Short version: Review the PR as the reviewer reads it, not as the author built it. Wade reads production code first (203 of 243 inline comments sit in h/ and src/), and he asks one question of every added line: who consumes it, what guards it, and does the text beside it say what the code does. Read the diff, the full files it touches, the PR body, the branch commit list and the CI configuration at the final head, and ask that question of every hunk, every test row and every body sentence.

Passing tests and a faithful implementation of a design do not establish that the design chose the right contract. The design document, earlier review findings, a test's own header comment and a pasted bot finding are claims to check, never the oracle.

## Words used here

- PR: pull request. HEAD: the commit the reviewer will see. BASE: the merge base of HEAD and the PR's target branch (`gh pr view N --json baseRefName`); 42 of the 115 PRs in Wade's record targeted a branch other than main, so never assume origin/main.
- CI: continuous integration, the automated build-and-test jobs. A lane is one workflow file with its trigger block and configure line. The gating lane is the one whose jobs `gh pr checks N --required` lists.
- gh: the GitHub command-line tool. Catch2: the C++ test framework; TEST_CASE, SECTION and GENERATE are its test, sub-test and parameter macros; STATIC_REQUIRE is its compile-time assertion.
- Note: a named long comment in the code, written `Note [name]`. TRON_ASSERT: the project's abort-on-false assertion macro. TRACE_EVENT: a Perfetto trace span.
- AMX: Intel's matrix instruction set; its kernels run only on hosts that have it, and `available()` is the runtime probe. FPGA attention: the hardware attention path; DMA: a hardware memory transfer that can outlive the function that issued it; GOF: a group of KV pages transferred to the FPGA.
- NaN: not-a-number, the floating-point value for an invalid result. Oracle: the source of a test's expected value. Shared helper: a function both the expected and the actual side call.
- Fixup commit: a commit that exists only because an earlier commit of the same PR was wrong or badly worded.
- Value suffix: the author's convention of ending a named constant with its value (`MAX_RETRIES_3`). Accepted inside the author's own kernel files; in shared code Wade asks for the file's existing idiom (check 13).
- Attributed text: a block Wade pasted from an AI assistant (nine disclosed cases, listed in references/wade-style.md). It is the assistant's claim, framed by Wade's sentence; a check that rests only on such text says so.
- Precedent "n = k comments over m PRs": how many of Wade's comments the check was derived from. A check with n = 1 is a hypothesis about him, not a habit.

## Setup: read what the reviewer reads

1. Fix HEAD and BASE. Save the PR body (`gh pr view N --json body`), the branch log (`git log --no-merges BASE..HEAD`), the diff, and the full text at HEAD of every file the diff touches, tests included. Line numbers in findings are HEAD lines.
2. Read the complete discussion over the three paginated endpoints (`pulls/N/reviews`, `pulls/N/comments`, `issues/N/comments`), including later replies. A retracted objection is not precedent; an author's answer can close a question before you ask it.
3. Read the repository test policy in AGENTS.md ("Tests": assertions about values or structure need an identifiable consumer, no duplicate coverage, extend the closest existing test) and the NaN rule (treat NaN as corruption). Quote them by line in findings.
4. If the user limits the evidence (no network, no worktree), respect the limit and report what each check could not establish. Write `Insufficient data` and name the missing input. Never fetch or change state in a worktree you were told not to change.
5. Run every check at the final head, after each review round and before requesting review. A check that ran on an earlier diff does not count. A hunk outside the diff gets at most an informational "fwiw" line.
6. When Wade has already commented, run the checks on his comments before replying. He can name the right concern and still propose a remedy that removes protection. Concede the substance, correct the detail, and never post a replacement sentence the checks have not verified.

Exact commands for each check are in [references/procedures.md](references/procedures.md). How he words findings, how he decides verdicts and what he never comments on are in [references/wade-style.md](references/wade-style.md). The corpus boundary and the method are in [references/wade-corpus.md](references/wade-corpus.md). The originating PR 4557 case is in [references/pr4557-misses.md](references/pr4557-misses.md).

## The thirty-five questions

Ordered by how often Wade raised each concern. Checks 1 to 13 come from the 2026-10-05 skill (PR 4557) and keep their numbers; 14 to 35 come from the whole record.
