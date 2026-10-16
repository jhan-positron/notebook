---
name: wade-code-review
description: Review a positron-ai/tron pull request at its final head the way reviewer Wade does, before he sees it. Covers what author-side reviews miss - tests that pin incidental values or structure, checks that silently skip on CI hosts, duplicate coverage, test names that contradict assertions, PR-body claims wider or staler than the code, CI claims without a lane, unrelated hunks, fixup-commit clusters, shared-header changes with no owner sign-off, constant-name families without a role. Use before requesting review, after every review round, when replying to a reviewer, and whenever the PR body or commit history is part of what the reviewer reads.
---

# Wade-code-review

Short version: Review the PR as the reviewer reads it, not as the author built it. Read the PR body, the branch commit list, the CI configuration and the full test files at the final head, not only the diff. For every test row, every body claim and every hunk, ask one question: who depends on this, and does the code at this head enforce exactly what the sentence says?

Passing tests and a faithful implementation of a design do not establish that the design chose the right contract. The design document, earlier review findings and a test's own header comment are claims to check, never the oracle.

## Words used here

- PR: pull request. HEAD: the commit the reviewer will see. BASE: `git merge-base HEAD origin/main`.
- CI: continuous integration, the automated build-and-test jobs. A lane is one workflow file with its trigger block and configure line. The gating lane is the one whose jobs `gh pr checks N --required` lists.
- gh: the GitHub command-line tool.
- Catch2: the C++ test framework. TEST_CASE, SECTION and GENERATE are its test, sub-test and parameter macros. STATIC_REQUIRE is its compile-time assertion.
- Note: a named long comment in the code, written `Note [name]`.
- AMX: Intel's matrix instruction set. The AMX kernels run only on hosts that have it; `available()` is the runtime probe.
- NaN: not-a-number, the floating-point value for an invalid result.
- Oracle: the source of a test's expected value. Shared helper: a function both the expected and the actual side call.
- Fixup commit: a commit that exists only because an earlier commit of the same PR was wrong or badly worded.
- Value suffix: the project convention of ending a named constant with its value (`MAX_RETRIES_3`). It is the author's decided convention and is never a finding.

## The thirteen questions

1. Value row: name the production reader, format or repository rule that breaks if this exact expected value changes.
2. Compile-time shape check: which production line outside the probed type's own header would misbehave if it flipped, and is it not already fixed by a declaration or static_assert in a header?
3. Gated check: if the address helper were wrong, which assertion fails on the lane that gates the PR, on a runner without the hardware?
4. Two tests on one call: is there a deliberate code break that fails test A but passes test B?
5. Test name: reading the name, the setup and the REQUIRE lines, does the name's verb describe the state in which the assertions pass?
6. Guarantee sentence: for every subject it covers, which enforcement level does the code reach, and does the sentence say so?
7. CI sentence: which lanes set or omit this setting, with their triggers, and does the sentence name the lane it means?
8. Result row: is the cited commit the reviewed head, or is the row labelled with its older id and the reason it still applies?
9. Body passage: if the reviewer could only open GitHub, would deleting this clause change any decision about the head?
10. Hunk: if it alone were reverted, would any body sentence stop being true, or any PR symbol stop compiling or stop being tested?
11. Commit: does it exist only because an earlier commit of this PR was wrong or badly worded?
12. Shared-header hunk no test observes: has an owner of the file accepted the placement, in writing, at a head that contains it?
13. Constant family: with the value suffix removed, does the stem alone tell a reader at the use site which constant this is?

## Setup: read what the reviewer reads

1. Fix HEAD and BASE. Save the PR body (`gh pr view N --json body`), the branch log (`git log --no-merges BASE..HEAD`), the diff, and the full text of every test file the diff touches at HEAD. Line numbers in findings are HEAD lines.
2. Read the repository test policy in AGENTS.md ("Tests": assertions about values or structure need an identifiable consumer, no duplicate coverage, extend the closest existing test) and the NaN rule (AGENTS.md: treat NaN as corruption). Quote them by line in findings.
3. If the user limits the evidence (no network, no worktree), respect the limit and report what each check could not establish. Write `Insufficient data` and name the missing input. Never fetch or change state in a worktree you were told not to change.
4. Run every check at the final head, after each review round and before requesting review. A check that ran on an earlier diff does not count.
5. When the reviewer has already commented, run the checks on his comments before replying. A reviewer can name the right concern and still propose a remedy that removes protection. Concede the substance, correct the detail, and never post a replacement sentence the checks have not verified.

Exact commands for each check are in [references/procedures.md](references/procedures.md). The originating case, with the verified facts and the mechanism of each miss, is in [references/pr4557-misses.md](references/pr4557-misses.md).

## Checks on tests

### 1. Value-pinning rows need a consumer

Trigger: a test hunk adds a runtime assertion whose expected side is a literal or a table entry, and that value differs from the bits the same test wrote to that slot or read back from it earlier. The difference is a conversion, rounding (including an exact tie), flush, saturation, or a special value changing class (NaN to inf, denormal to zero). A pure widening (bf16 bits shifted into fp32) is not a difference. Compile-time rows belong to check 2.

Procedure: list the rows. Keep rows whose expected equals bits the same test put in or stored earlier (round trip, partner kept after an odd write, read-back), whatever the value. Keep rows whose discarded bits are zero, so that truncation and rounding agree. For each remaining row, name the accessor the row stores through and search `h/` and `src/` (excluding `t/`) for a reader, a documented format or an AGENTS.md line that depends on the exact bits. A comment that states the policy or its history ("exactly as set_v always did") is not a consumer. Then find the second policy: the generic converter for the same source type, or the function a test comment says "would" behave differently, and compute its output for the row's input.

Do not fire on:

- pair-invariant rows (expected 0 for the untouched partner after an even write) when the test, or the function it stores through, cites the Note that names the dependent path. If no citation is present, ask for the citation instead of dropping the row.
- regression rows for a failure seen on main or in the product.
- rows that pin a documented wire, file or hardware format.

The remedy is always on the test side. Never propose changing the numerical behavior to fit or unfit a test. Report a new contract problem separately from any pre-existing numerical issue. Respect any repository rule that restricts weakening existing tests.

Finding shape: "This row makes '<input> stores as <output>' a tested contract. <AGENTS.md:line '<rule>' | no reader in h/ or src/ depends on <policy>; the only statement is the test comment '<quote>'>. Suggest dropping <rows> and keeping <the round trip and the partner-zero checks>."

### 2. Structure-only compile-time checks

Trigger: a test hunk adds a STATIC_REQUIRE, STATIC_REQUIRE_FALSE or static_assert.

Procedure: split by what the expression names, not by whether it is true. A boundary probe calls, inside a requires-expression, a production function declared outside the probed type's own header (a kernel, a free function, a member of another class). Keep it. A shape check names only the probed type: a type trait, sizeof, alignof, or a requires-expression whose body calls only the probed type's own members or their absence (an accessor on a temporary, a write through at(), a missing operator). For each shape check: (a) search `h/` for the same trait on the same type or on an enclosing type that holds it as a member, resolving aliases; (b) check whether the probed type's own declaration already fixes the trait (alignas, `= delete`, an array member). Either one makes the check a repeat.

Question (shape checks only, never asked of a boundary probe): if this assertion flipped, which production line outside the probed type's own header would misbehave, and is that line not already protected by a declaration or static_assert in a header?

Do not fire on:

- boundary probes.
- trait probes that spell the PR's stated type-safety contract (a bare pointer or the other layout's view is not constructible). Treat them as boundary probes. A positive constructibility probe on an alias belongs to check 6.
- a trait production code relies on that no declaration or header fixes. The finding is then "move the static_assert into the header", not "drop the test".

Finding shape: "The kernel probes are the PR's real contract. These only document structure: <list>. <N> checks repeat header assertions: <test line -> header file:line, each>. Keep the probes and drop the rest."

### 3. A layout-formula check must execute on the lane that gates the PR

Trigger: a test adds a runtime assertion that compares stored bytes or indices with a literal table or a formula written out in the test, and between the start of the TEST_CASE and that assertion stands a runtime exit (`return`, SKIP, WARN plus return) conditioned on a hardware or environment probe (`available()`, a cpuinfo flag, FPGA presence, getenv). Test selection labels in t/CMakeLists.txt (min_slices_N) are a separate gate; list them under selection.

Procedure: record every early exit above the assertion and its condition. Check whether any statement between the exit and the assertion executes the probed instructions (for `available()`: a call into the AMX kernel namespace; AVX-512 intrinsics do not count, every runner has them). For each lane that can run the binary, record its trigger and whether its configure line sets the build flag the TEST_CASE needs; on a lane where the flag is off the whole case is compiled out. On a lane where it is on, check whether every runner the job can land on passes the probe (README.ci.md runner table). Find the oracle of the assertion. If a production accessor of the same storage produces the expected side, both sides share the helper. List every other non-gated assertion on the same storage and classify it: an independent formula substitutes; a route check through the same helper never does; a second reader with its own address arithmetic substitutes only when it covers both parities and a pair beyond the first.

Four separate facts, each stated: the target compiles on the lane; the test case is selected; the assertion is reachable on the runner; a log shows the path executed. If runner capability or a log is unavailable, write `Insufficient data` and name it.

Do not fire on: an assertion that consumes a kernel output produced above it, when a non-gated independent assertion covers the same contract elsewhere (name it).

Finding shape: "This is the only check of <contract> against a formula that does not go through <helper>, but it sits after the <probe> early return at :<line>, so it does not execute on <lane or runner class>. The <other section> does not cover it: both sides compute their address through <helper>. Move it above the early return, or into <closest non-gated test>."

### 4. Same experiment run twice

Trigger, all must hold: the PR adds or widens two test units (TEST_CASE, SECTION, GENERATE arm, template instantiation), or one new unit plus one it widens; both make the same production call as the operation under test; both feed it the same GENERATE list or named constants, the same token or size set and the same source value type; both reach the same leaf branches of a function the diff changed. A commit that answers several gap items at once raises the priority of its units. A comment claiming "covers N cases" is a separate nit.

Procedure: name the production call of each unit. Follow it to the leaf function with branches the diff changed and map every input (each GENERATE value, each token index) to the arm it reaches. Simulate the unit's write order: a slot counts as observed only if no later write in the same unit replaces it before an assertion reads it. Record for each unit the set of (branch, slot, reference, precision, read path) its assertions observe. Compare pairwise, among the triggered units and any pre-existing unit on the same call that the PR widened with new assertions.

If every break that fails A also fails B, drop A. If some break fails only A, name the (branch, slot) pair only A observes, give B that observation with one concrete edit, then drop A. Do not report the pair as complementary and leave both. A full-page copy can overwrite a partner slot before the assertion reads it, which is how a larger unit can observe less than a smaller one. Prefer small cases that keep the observation over either a redundant matrix or an unjustified deletion.

Do not fire on: units that feed different source value types or different token sets; units that make different production calls; a pre-existing unit changed only in API spelling; units under different build or hardware gates (then the finding is check 3).

Finding shape: "`<unit A>` and `<unit B>` (line <N>) run the same <inputs> through <call>, reaching <branches>. <B> already checks <what, against which reference, through which read path>; this one adds <nothing | the (branch, slot) pair B overwrites before reading>. The test policy rules out duplicate coverage that protects no distinct behavior: <drop this one | extend B by <edit> and drop this one>."

### 5. A test name states the enforced contract

Trigger, any one: the diff adds, removes or rewrites an assertion, a comment or the stimulus (the values written before the call under test) inside a TEST_CASE or SECTION body, whether the unit is new or its name is unchanged; or a comment inside a test flips a verb to its opposite (preserve/zero, keep/drop, accept/reject) while the name keeps the old verb. A hunk that only re-spells a call's arguments, with no added or removed assertion and no changed comment about what the code under test does, is an API migration and does not trigger.

Procedure: extract the verb and object from the name. Read the setup lines that put the object into its pre-call state. For every assertion that observes the object, directly or through a value computed from it, write "fails when <state>". The name must describe the passing state and agree with the verb the unit's own comments now use. Then grep the name in the file header comment and the PR body (and in commit messages only if the PR will not be squashed); list each hit as a rename site inside the one finding.

Do not fire on: a topic label without a verb; a name wrong on main inside a unit whose body the diff changes only by call re-spellings (mention once as pre-existing); an assertion the name does not mention (another check owns that hunk).

Finding shape: "Nit: the section is still named '<name>', but it now asserts that <opposite state> (REQUIRE at :<line>; the comment at :<line> says '<new verb>')."

## Checks on claims

### 6. Guarantee claim versus enforcing declaration

Trigger, all parts: a sentence in the PR body, a commit message, a Note or a comment names a rejected input ("bare pointer", "raw pointer", "the other plane's view", "cannot be passed", "cannot be handed in") and gives a compile-time reason (a mechanism word: "compile error", "rejected", "enforced", "STATIC_REQUIRE", "static_assert", or the parameter type as the reason: "passed as its typed view so that", "neither takes"). Expand every plural or "and" into its subjects.

Procedure: for each subject, find every parameter in the diff's added lines whose type names the subject and resolve that type through every `using` to its struct or class definition. Grade three levels and cite the line that decides each:

1. a bare pointer passed directly at the call is rejected (an `explicit` constructor gives this).
2. a pointer wrapped in one expression is rejected (needs a private or absent pointer constructor).
3. the parameter type is nominally distinct from any generic view of the same shape (needs a new class; a `using` alias of a generic template accepts every instantiation with the same arguments, from any buffer).

Read the cited tests for an assertion in the opposite direction. `std::is_constructible_v` true for a pointer means level 2 is open; it is not evidence that level 1 is open. Guarantees about direct argument matching, layout, ownership, lifetime, alignment and provenance are separate; do not infer one from another. If the project keeps a design record, quote the limitation it states for the subject. Group every location of the claim by subject and write one finding per failing subject, anchored at the alias definition, with the other locations as citations.

Do not fire on: a sentence whose own table row or own comment block names the limitation; the word "typed" alone; an `explicit` constructor as such. Report a documentation overclaim separately from an implementation defect, and preserve a deliberate staged limitation ("fine as a first step") once the text states it.

Finding shape: "`<alias>` (<file:line>) is an alias of the generic `<template>`, and <test:line> asserts it is constructible from `<pointer type>`. So any pointer wrapped in one line, or any same-shaped view, passes `<kernel>`; '<quoted claim>' holds at the call for every subject and beyond that for <subjects with a distinct type> only. Please say so in the description; a distinct type can come in <follow-up>."

### 7. CI claims name the lane, the trigger and the configure line

Trigger, all parts: a sentence in the PR body, a README hunk or a comment hunk has a CI subject ("CI", "the required checks", "the build job", "the nightly", a workflow name), asserts a setting or coverage (a CMake option, a preset, a platform feature, "AMX-on/off"), and is not about a build the author made (a named tree, machine or runtron arm is a measurement statement). Also a reviewer comment that cites a workflow file:line as proof of what gates the PR, and a PR number offered as the date a setting changed.

Procedure: list every file under `.github/workflows` and the keys of its `on:` block. For every file with none of `push`, `pull_request` or `merge_group`, find its callers and quote the caller's `if:` gate. Find every place the setting lives (`.github`, `nix/`, `flake.nix`, `CMakePresets.json`, `CMakeLists.txt` default, `GNUmakefile`, README.ci.md) and name each hit's consumer: a workflow `run:` line belongs to that job; a nix file belongs to the job whose `nix build` recipe imports it; a preset belongs to whatever runs it. Get the gating set from `gh pr checks N --required` on a finished run (no row in progress or queued) and record each job's workflow name. Date the setting per file with `git log -S` and map the commit to its PR.

A lane is named only by a workflow's `name:` string, its file name or a job name. "CI", "the required CI" and "the build job" are not lane names when the repository calls two lanes with opposite settings "CI".

Do not fire on: a sentence that names the lane and matches that lane's configure line; a generic "CI is green"; a runtime log or WARN string in code; a PR-label sentence that matches the documented label policy. README text is a claim to check, never evidence.

Finding shape: "'<quoted sentence>' names no lane. The checks that gate this PR are <workflow name> (<configure file:line>, <setting absent or present, default>). <Other workflow>:<line> passes <setting> but has no push or pull_request trigger since <commit, PR>; it runs from <caller:line> on <gate>. The setting entered it in <commit> via PR #<n>."

### 8. Result rows cite the reviewed head

Trigger: the PR body reports a measurement of the PR's code (unit-test counts, token identity, perf A/B, objdump, lint, build) in a Verification, Status, Tests or Results section.

Procedure: list every 7-to-40 character hex id in those sections that attaches to a measurement row, skipping the commit table and the review-outcome table. A row with no id takes the id of the nearest "Binary:" or "at <id>" line in its section. For each id run `git cat-file -t` and `git merge-base --is-ancestor ID HEAD`. An id that does not resolve, or that GitHub cannot show (`gh api repos/<org>/<repo>/commits/<id>` answers 422), is an amended, rebased or squashed twin: its row is a finding. For each ancestor id name the event between it and HEAD (a merge of main, a rebase, an amend) and list the PR files whose content differs between the id and HEAD. Also flag any present-tense phrase ("ran at the head X", "now", "current") next to an id that is not HEAD.

A label (pre-merge, pre-rebase, pre-amend) is accepted when it comes with the PR files unchanged between the cited id and HEAD, the date of the scheduled re-run, or a stated known difference.

Ask per kind. Unit tests, token identity, lint, build: re-run at HEAD, or delete the old rows when rows at HEAD already stand in the same table, or label with the reason. Perf A/B and objdump: add the id and a label; no re-run is demanded.

Do not fire on: ids in a commit table or a review-outcome table; the main-side baseline id; pass-rule definitions and reference bands from outside the PR.

Finding shape: "PR description, <section>: the <kind> rows cite <id>, <event>; <files> changed since then. Please <re-run at <HEAD> | delete them, the rows at <HEAD> replace them | mark them pre-merge and say which files did not change>."

### 9. PR-body passages a GitHub reader cannot use

Trigger: the PR body has a Status, Verification, Tests or Results section. A heading at any level whose text contains one of those words starts a section; it ends at the next heading of the same or a higher level. The procedure runs only inside those sections.

Procedure: grep for wall-clock times, machine-local paths and log names (`/var/tmp/`, `/home/`, `*.log`), and count reconciliations between two revisions ("N fewer assertions than at X", "4 + 8192 = 8196"). A dangling id that labels a result goes to check 8, not here. For each remaining hit ask the reader test. Bins: wall-clock times (keep the date only), machine paths and log names (delete), reconciliations against an earlier revision (delete; keep at most the one sentence "no production assertion was removed").

Do not fire on: a commit id plus a date that identifies the binary a result came from; the pass or fail outcome and the counts at the head; a path inside the repository; a duration stated as a number with units when that number is the claim ("TTFT 53.1 s"). A clock-time range is never a measurement.

Finding shape, once per section and phrased as an ask: "PR description, <section> lines <a>-<b>: the build timestamps, the log path on <host> and the <X = Y + Z> reconciliation against <sha> can go. Keep the rc/outcome clause and one result row per test and tree with the commit id and date."

## Checks on scope, history and ownership

### 10. Hunk-to-claim trace (unrelated changes)

Trigger: always. Cost: one `git log`, one `git show` per commit and one grep of `BASE:FILE` per hunk. Highest priority when a commit's author differs from the PR author, when a commit message or the body cites another PR number or says "folded", "stacked" or "fast-forward", when a commit subject starts with Name, Rename, Brace, Clean up, Shorten, Clarify, Reword or Tighten, or when a commit adds tests after a review round.

Procedure: write the identifier set: every backticked type, function, constant or Note title in "What changes", plus every name declared at namespace or class scope in a file the diff creates, minus any name that exists at BASE. Confirm each with `grep -c` over the diff. Bin commits: SIDE when the subject starts with one of the verbs above, or the commit changes only tests or comments, or its author is not the PR author; MAIN-FEATURE when the subject contains an identifier from the set verbatim; otherwise SIDE. Scan the hunks of every non-merge commit, SIDE first; a MAIN-FEATURE commit can carry a side hunk. A hunk is a candidate when at least half of its removed lines exist verbatim at BASE, at least one of them is not blank, brace-only or comment-only, and its added lines contain no PR identifier. A candidate in the same function or TEST_CASE as a hunk that carries an identifier inherits that hunk's status.

Clear a candidate only if: the PR's functional change rewrites the same statement (the removed line with the rename map applied equals the added line); a GitHub review thread of this PR asked for it (cite the id; an author-side agent review is not a reviewer); or a body sentence describes the hunk's added content. A sentence that only names the file or the callee does not clear. A sentence that says the opposite is quoted as a contradiction.

For a test hunk that is a candidate: name the callee. If the PR does not touch the callee, the hunk is unrelated. If the PR rewrote or moved the callee, the hunk is a regression guard; report at most a body gap ("the body never says <callee> keeps <contract>"), never "unrelated". A row inside a TEST_CASE the PR created is never a candidate here.

Do not fire on: a removed/added pair that differs only by the rename map; hunks whose removed lines are absent from BASE or comment-only; a cleanup the title or "What changes" lists as bundled.

Finding shape, one per hunk: "<file>:<lines> (commit <id>, '<subject>') changes <N> lines that exist at BASE and that <feature> does not touch: <what it does>. Reverting it alone keeps the body true (<body line> says '<sentence>') and nothing the PR introduces stops compiling or being tested. Not part of <title>; please split it into its own PR."

### 11. Commit history is reviewed content

Trigger: run on every review, at every push after a review round and at the final head. Confirm how the target branch lands PRs with `git log --first-parent -20 origin/main`: merge commits mean branch commits are permanent history.

Procedure: bin each non-merge commit. OTHER-AUTHOR: author differs from the PR author (keep as its own commit). FIXUP, both conditions: the hunks show no behavior change (comment, whitespace, brace or name-only edits, or an exact return to main's behavior on a path an earlier commit of this PR changed), and every removed non-comment line was added by an earlier commit of this PR. UNRELATED: a check 10 finding (excluded from the squash units, reported there). TOPICAL: the rest. A subject prefix alone never bins a commit. A CLUSTER is two or more FIXUP commits whose subjects or bodies name the same Note title, or whose diffs touch overlapping line ranges of one file at HEAD. Give both counts at HEAD (`git rev-list --count` with and without `--no-merges`) and, when answering a posted review, the with-merges count at the last push before the review.

Report a finding only for a CLUSTER or an UNRELATED commit. A long history with neither gets at most a one-line note: Wade approved PR 4596 on 2026-09-30 at 26 non-merge commits without a squash request. Never raise above hygiene.

Do not fire on: a target branch that squash-merges; a draft PR or an author who wrote that a squash is pending (judge the PR state, not a word grep); a merge commit; another author's commit; the commit table in the body (check 9).

Finding shape: "Commits: <N> (<M> merges, <K> without) at <head>, <k> of them rewording <Note> (<ids, oldest first>). Please squash into <one unit per body heading that names a code change>; keep <every other-author id> as its own commit."

### 12. A shared-header change no test observes needs a named owner's acceptance

Trigger, both halves. Placement: the hunk adds or changes a definition at global namespace in any header (operator new/delete overload, free function, macro, inline variable, struct), or adds non-comment lines to a header under h/system, h/pos, h/common or h/tron/hardware. Unobserved guarantee: a comment, Note or commit message of the hunk says a revert is undetectable ("no test fails if", "nothing can catch", "behave the same either way"), or every test on the path observes a by-product (alignment, non-null) and not the mechanism. A commit-message hit is attributed to the files that commit changes and tested per file.

Procedure: find global definitions by walking the header with a namespace depth counter and reporting added lines at depth zero that are not blank, comments or directives. Count includers: direct (files under h, src, t, bin, ingest whose `#include` names it) and transitive (closure over `#include` lines); report "N direct, M transitive of T". Classify the hunk's origin: owner-authored PR; fast-forward fold (`gh api repos/<org>/<repo>/commits/<sha>/pulls` lists another PR and the commit sits on the first-parent line with no merge commit of that PR); merge; side commit. Owner set: authors of the file at BASE by recency, plus every requested reviewer of the PR with a commit on the file (map logins to authors with `gh api users/<login>`, then by email local part). Read every PR comment on the file by an owner and class it: placement accepted (names the symbol or the header and says keep, fine, agree, LGTM, go ahead), diagnosis agreed, or wording only. Only the first counts; an APPROVED review by an owner at a head that contains the hunk also counts. A comment counts only if its `commit_id` contains the introducing commit (`git merge-base --is-ancestor`). Use dates only to say that a reply cites a commit older than the thread it answers.

State what the tests cannot prove: a fake that provides the behavior the production path lacks proves nothing about the production path.

Do not fire on: a hunk the owner authored; a change in a PR the owner approved after it landed; a change a test fails on when reverted; comment-only hunks. Do not make every low-level change require new approval, and do not contact reviewers; the finding is the unposted question.

Finding shape: "<file>:<line> adds a global `<symbol>` in a header that reaches <M> of <T> files. Line <L> says no test fails if the mechanism is reverted, and the tests that call it check <by-products> only. It came in <commit> (<origin>), and the owner's comments on this file <agree with the diagnosis | ask for a reword>; none accepts the placement. Please get <owner>'s explicit sign-off on the approach."

### 13. Role-bearing constant names (the suffix convention stays)

Trigger: the diff adds or renames a named constant with a value suffix (`_7`, `_0XFFFF0000`, `_TRUE`), or replaces an inline `literal /* comment */` argument with one. Never report the suffix or the uppercase style; report the stem.

Procedure: strip the suffix; group names by stem within one file. A family is two or more names with one stem. Every family is flagged unless exempt: index-suffixed members hold different data by construction, so write the per-member data from the use sites down as the evidence. The exemption is a scratch rotation: every member holds the same data at every use site and the comment above the family says so. For a single name: the guide allows a literal `0` for zero initialization, a reset, a zero comparison or an empty value when the surrounding code makes the meaning clear (the parameter name is visible at the call, or the statement is an init, reset or comparison), and a numeric literal inside a one-use `alignas`. For a production constant only, report a duplicate when an existing named constant states the same meaning, has the same value in every build and is reachable through the file's includes.

Do not fire on: a single constant whose stem names a role, even a short one (`BF16_BITS_16`); the required namings of `1`, `true` and `false`; test-local constants as duplicates.

Finding shape: "`<STEM>_0..3` (<file:line>) share one stem and differ only by the value; in <function A> member i holds <data>, in <function B> it holds <data>. The file already names <sibling> per kernel (`<ROLE>_TILE_4`); name these the same way per kernel, or keep the shared stem and state the per-kernel meaning at the use site. Nit; the author's call."

## How Wade words a finding

- A declarative fact first, the consequence second introduced by "So", the ask third. One to three sentences.
- Backticked identifiers with a location in the same clause: `(line 197)`, `file.yml:355`, a commit id, a PR number, a repository policy by name ("AGENTS.md treats NaN as corruption", "test policy").
- Every drop request names what to keep. Every text-versus-code mismatch offers both repairs: change the code, or narrow the text.
- Severity is stated: "Nit:", "Fine as a first step", "Not blocking", "Coverage gap:". A design concern is a question with two alternatives, not an order.
- He does not comment on formatting, brace style, benchmark method, the C++ guide, or kernel arithmetic line by line. Do not add such findings in his name.

## Report the result

- For each finding give the HEAD location, the check number, the fact, the consequence, the evidence (file:line and a short quote) and the smallest remedy.
- Separate correctness, coverage, description and preference findings. If a point is only a hypothesis, name the check that would resolve it.
- State the revision reviewed, which checks ran, which did not, and what evidence was unavailable.
- A review request authorizes analysis, not source edits, comment posting or history rewriting.
