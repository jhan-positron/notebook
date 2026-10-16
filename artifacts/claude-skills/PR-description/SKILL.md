---
name: PR-description
description: Write or rewrite the description (the body) of a pull request in a fixed section order - Short version, Background, Words used here, How to review this PR, Verification, Open items, and The stack when a large PR is split into smaller ones - in plain English. Use this skill whenever the user asks for a PR description, a PR body, "describe this PR", "write the body for PR N", or wants an existing description shortened, restructured or checked, and whenever a handoff or plan says to open a PR with a body, even if it does not name this skill. The output is checked with the plain-english skill before it is posted.
---

# PR-description

Short version: a PR description tells the reviewer what the change does, why it exists, which words it uses, and where to look to form a judgment. It is not a walk through every file. Write the sections below in that order, state every fact once, keep the body under 2,000 words not counting the Words used here section, and run the plain-english check on the result before posting.

## Before writing

Gather, and keep open while writing:

- The diff of the head against the base, and the commit list.
- The tests the PR adds or changes, with their case names.
- Every measurement the body will cite, with its commit id and date.
- The issues and PRs the body will cite.
- The code's Notes (named comments) that explain the mechanism, so the body can point to them instead of repeating them.
- The project's CLAUDE.md term list, to reuse its definitions verbatim.

Why: every sentence of the body must be checkable against one of these. A sentence with no source is the first thing a reviewer doubts.

## Rules for every section

- Present tense, written as of the head. No change history, no review-round narration, no "before" and "after". The commits and the review threads hold the history.
- Say where each result comes from with a commit id and a date, and nothing more. No clock times, no paths into the author's workspace, no comparison with another head's counts.
- Every fact in one place. When a later section needs a fact, point to the section that states it, in brackets: "[Verification]".
- No names of people. Roles, issue numbers and links only.
- Write "PR", never "pull request".
- When an issue or a result record holds a fact, the body names it and does not repeat it.
- The body stays under 2,000 words, tables included, not counting the Words used here section. Count with `wc -w` on the posted file with that section removed (the command is in step 4 under After writing). Why the limit: in the repository this skill was built on (positron-ai/tron), the last 60 merged bodies had a median of 300 words (half of them were shorter) and a longest of 1,215 words (counted 2026-10-13). A body of 2,000 words is already longer than every one of them. Aim well below the limit.
- Plain English in every sentence: write in the plain-english skill's Write mode. The project's CLAUDE.md names the terms that always need a definition.

## The sections, in order

### 1. Short version

Even a reader with no prior experience of the code base can understand what this PR is about. It carries no section pointers. The sections follow in a fixed order, so a pointer there is a duplicate.

### 2. Background

Why the change exists: the constraint or the problem, in present tense. One formula or diagram block is allowed when it carries the idea faster than prose. If a Note in the code explains the mechanism, name the Note and do not repeat it. Do not list what the PR provides. The Short version did.

### 3. Words used here

A two-column table: Term | Meaning. A term belongs in the table only when both hold:

- it is a project term (a code name, an option, a label, a build variant, a machine), an abbreviation, or a metric, and
- it is used in more than one section.

A term used in one section is defined inline there, in a parenthesis at first use. General engineering words (PR, token, CPU) and standard terms of the field (row-major, cache line) stay out unless the project's CLAUDE.md defines them. A row leaves the table with the last use of its term. Expect 5 to 10 rows. This section is not counted in the word budget.

Why: in one body the author removed 23 of 35 rows by hand after posting. The rows removed were general terms. The rows kept were project terms, each used in several sections.

### 4. How to review this PR

This section holds the questions a reviewer must answer to trust the change: at most three, each a place where the change could be wrong in a way that is hard to see (a pointer or value that crosses a boundary, a path selection, a type that must not leak, a count that must agree between a writer and a reader). No sub-headings. Each item:

- The question, in bold, on its own line.
- One bullet per file to read: the file, and what to check there.
- One bullet per claim that follows from those files.
- A last bullet "Verification:" naming the test, assertion, compile check or measurement that settles the question, or "Open." and who decides.

Choices a reviewer could make differently (a name, a boundary, a default, a tolerance, a contract) go to Open items with "Reviewers decide." when they must be decided before merging, and stay out otherwise. Omit everything a test or a code comment already settles. Do not walk through the diff by file: a file list is noise. One worked example: `references/example-how-to-review.md`.

### 5. Verification

This section answers one question: does the head build and pass in every configuration, and are the generated tokens identical where they must be? When the PR's goal is a performance improvement, it also answers a second question: how much does the PR improve performance, and why? A PR that costs performance at its head answers the second question too, because the reviewer weighs that cost.

Open with one paragraph that says where every result in the section comes from: the head and the base commit ids, the machine, the date, the build settings (environment, compiler, preset, build type), and the binaries or configurations compared, each with the short name the tables use. Why: every table below is read against this paragraph. A reviewer who finds these facts stated twice looks for the difference between the two.

Then subsections, each one table with at most two sentences around it:

- **Builds and tests.** One row per configuration (the options on or off) with what was built and the test results as assertions and cases. The checks that must be clean (format, whitespace, prohibited headers, a syntax-only compile across configurations) take one sentence each. A deliberate break that a test must catch (a mutation check) takes one sentence: what was changed, which case failed. A skipped or failed test carries its reason, never a summary such as "all pass".
- **Token identity.** One row per cell (model, attention, prompt length) with the result: "identical, N of N tokens" or "first difference at generated token K". Say which pairs must be identical (a repeat of the same binary, the kill switch against the same binary) and which comparison is informational (against the base).
- **Performance** (when the second question applies). The cells, the decision rule (for example, a band of twice the larger standard deviation and the paired t statistic over the repetitions), one table per binary with the standard deviation, one table per pair with the difference and whether it is inside or beyond the band. Then "what the tables say" in a few sentences: the size of the change and the mechanism that explains it, with a decomposition when more than one mechanism is in play. A loss at this head is stated here.

Keep out: wall-clock times, paths into the author's workspace, reconciliations of counts against another head, and setup lists that a script or result file already records (name the file instead). Why: those go stale at the next head, and the reviewer checklist deletes them on sight.

Why one section: measurements and test runs are both records at one head. Kept apart, they state the machine, the date and the commit ids twice and split the runtime runs (token identity under one heading, the kill-switch comparison under the other). Kept together, Performance stays a named subsection so a cost is never buried among counts.

### 6. Open items

What this PR leaves unresolved. Each item is a bold run-in heading followed by the facts a decider needs: what is unresolved, the measurement or decision that settles it, and who decides. Mark an item the reviewers must decide with "Reviewers decide." and cite the issue that tracks it. Pending measurements go in one list, each as the question and the measurement that would answer it. An item that section 4 already poses as a question is referenced from there, not restated. An item that an issue tracks is one sentence: the heading, the fact this head adds, and the issue number. An item inherited from an earlier PR that this PR does not change stays out. An item nobody must act on before merging stays out.

### 7. The stack

Only when a large PR is split into smaller ones. One paragraph says what the original PR is and that the stack replaces it. One table lists the PRs with the columns Order, PR #, PR branch and base, What it adds, and State ("ready for review", or "draft until PR #N merges"). One closing sentence says what stays disabled until the last PR merges.

### Sections 8 and up

To be added.

## After writing

1. Run the plain-english skill in Check mode on the whole body and apply every fix.
2. Check every number against its source, and that every commit id and issue number resolves.
3. Remove every duplicate: a fact stated in two sections stays in one, and the other section points to it.
4. Count the words without the Words used here section:

   ```
   awk '/^## Words used here/{skip=1; next} /^## /{skip=0} !skip' body.md | wc -w
   ```

   If the count is 2,000 or more, cut in this order, and stop as soon as the count is under 2,000:
   - Verification tables: keep the rows the decision rests on, and name the result file for the rest.
   - Open items: keep the question, the measurement that settles it, and the decider. The numbers go to the issue that tracks the item.

   Section 4 and the token-identity rows are not cut. They are what the reviewer decides on. Why this order: in the body this skill was built on, the Verification tables held 614 words and Open items 838 words, together 1,452 of the 3,582 counted words.
5. Post from a file with `gh pr create --body-file` or `gh pr edit --body-file`. Before editing an existing body, fetch the live body again: other sessions and the author edit bodies on GitHub. Never reinstate text the author deleted.

## Self-check before posting

- [ ] No fact is stated twice. A later section points to the section that states it.
- [ ] Under 2,000 words without the Words used here section, counted with the command in step 4.
- [ ] Every table term is a project term used in more than one section.
- [ ] Section 4 has at most three bold questions, bullets per file and per claim, and a Verification bullet or Open with a decider.
- [ ] No "pull request". No section pointer in the Short version. Every open item with an issue is one sentence.
- [ ] No file inventory anywhere.
- [ ] Section 5 says once, at its top, where its results come from. Every table names its configuration, and every skipped or failed test carries its reason.
- [ ] If the PR claims or costs performance, the Performance subsection has the decision rule, the tables, and the mechanism.
- [ ] Present tense, no history, no clock times, no workspace paths, no names of people.
- [ ] plain-english Check run and applied.
